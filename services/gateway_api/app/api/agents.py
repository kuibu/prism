from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.agent.assistant_models import (
    AgentKind,
    AgentListResponse,
    AgentLLMConfig,
    AgentLLMProvider,
    AgentMemoryEntry,
    AgentProfile,
    AgentStatus,
    AgentUpdateRequest,
    AgentUpsertRequest,
    AssistantInsightListResponse,
    BootstrapResponse,
    MemoryCollectRequest,
    MemoryNoteRequest,
    MemorySearchResponse,
    MemorySourceType,
    SecretaryRoomMode,
    SecretaryRoomModeListResponse,
    SecretaryRoomModeRecord,
    SecretaryRoomModeUpsertRequest,
    SecretarySuggestionActionRequest,
    SecretarySuggestionActionResponse,
    SecretarySuggestionCreateRequest,
    SecretarySuggestionListResponse,
    SecretarySuggestionStatus,
    SkillManifestView,
    SkillRunRequest,
    SkillRunResponse,
)
from app.agent.llm_gateway import AgentLLMError, chat_completion
from app.agent.memory_backends import (
    OPADocumentMemoryBackend,
    OpenVikingConfig,
    OpenVikingMemoryBackend,
)
from app.agent.memory_store import AgentNotFoundError, AgentStoreError, OPAAgentStore
from app.agent.secretary_runtime import (
    SECRETARY_AUTO_REPLY_MARKER,
    build_secretary_response_bundle,
)
from app.agent.skills import SkillExecutionContext, SkillExecutor, SkillRegistry, SkillRouter
from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.core.deps import (
    AuthenticatedUser,
    get_authenticated_user,
    get_immudb_client,
    get_opa_client,
)
from app.matrix.admin import AgentBotManager, AgentBotManagerError
from app.matrix.client import MatrixClient, MatrixClientError
from app.policy.opa_client import OPAClient

router = APIRouter(prefix="/agents", tags=["agents", "memory", "skills"])


def _build_default_agent_llm_config(request: Request) -> AgentLLMConfig | None:
    settings = request.app.state.settings
    if not bool(settings.agent_default_llm_enabled):
        return None

    provider_raw = str(settings.agent_default_llm_provider).strip().lower()
    if provider_raw == "":
        provider_raw = AgentLLMProvider.OPENAI_COMPATIBLE.value
    try:
        provider = AgentLLMProvider(provider_raw)
    except ValueError:
        provider = AgentLLMProvider.OPENAI_COMPATIBLE

    api_key_raw = str(settings.agent_default_llm_api_key).strip()
    base_url_raw = str(settings.agent_default_llm_base_url).strip()
    api_path_raw = str(settings.agent_default_llm_api_path).strip()

    return AgentLLMConfig(
        enabled=True,
        provider=provider,
        model=str(settings.agent_default_llm_model).strip() or "qwen2.5-32b",
        api_key=api_key_raw or None,
        base_url=base_url_raw or None,
        api_path=api_path_raw or "/chat/completions",
        temperature=float(settings.agent_default_llm_temperature),
        max_tokens=int(settings.agent_default_llm_max_tokens),
        timeout_seconds=float(settings.agent_default_llm_timeout_seconds),
    )


def _agent_store(request: Request, opa_client: OPAClient) -> OPAAgentStore:
    settings = request.app.state.settings
    local_memory_backend = OPADocumentMemoryBackend(
        opa_client=opa_client,
        opa_data_root=settings.opa_data_root,
    )
    backend_name = str(settings.agent_memory_backend).strip().lower()
    memory_backend = local_memory_backend
    if backend_name == "openviking":
        memory_backend = OpenVikingMemoryBackend(
            primary=local_memory_backend,
            config=OpenVikingConfig(
                base_url=settings.openviking_base_url,
                api_key=settings.openviking_api_key,
                agent_id=settings.openviking_agent_id,
                timeout_seconds=settings.openviking_timeout_seconds,
                retry_attempts=settings.openviking_retry_attempts,
            ),
        )

    return OPAAgentStore(
        opa_client=opa_client,
        opa_data_root=settings.opa_data_root,
        default_llm_config=_build_default_agent_llm_config(request),
        memory_backend=memory_backend,
    )


def _skill_registry(request: Request) -> SkillRegistry:
    registry = getattr(request.app.state, "agent_skill_registry", None)
    if isinstance(registry, SkillRegistry):
        return registry
    created = SkillRegistry.default()
    request.app.state.agent_skill_registry = created
    return created


def _matrix_client(request: Request) -> MatrixClient:
    return cast(MatrixClient, request.app.state.matrix_client)


def _bot_manager(request: Request) -> AgentBotManager:
    return cast(AgentBotManager, request.app.state.agent_bot_manager)


async def _append_audit(
    *,
    immudb_client: ImmudbClient,
    event: AuditEventCreate,
) -> None:
    try:
        await immudb_client.append_audit_event(event)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"agent_audit_failed: {exc}") from exc


async def _evaluate_policy(
    *,
    request: Request,
    opa_client: OPAClient,
    user_id: str,
    agent_id: str,
    room_id: str,
    purpose: str,
    action: str,
    data_category: str,
) -> tuple[bool, str, int]:
    settings = request.app.state.settings
    rate_counter = request.app.state.agent_rate_counter
    rate_key = f"{user_id}:{agent_id}:{room_id}:{purpose}:{action}"
    request_count = rate_counter.increment_and_count(rate_key)

    payload = {
        "agent_id": agent_id,
        "user_id": user_id,
        "room_id": room_id,
        "action": action,
        "data_category": data_category,
        "purpose": purpose,
        "request_count_per_minute": request_count,
        "ts": datetime.now(UTC).isoformat(),
    }
    decision = await opa_client.evaluate(settings.opa_policy_path, payload)
    allow = bool(decision.get("allow", False))
    reason = str(decision.get("reason", "policy_decision_missing"))
    return allow, reason, request_count


def _extract_messages_from_sync(
    *,
    sync_payload: dict[str, Any],
    room_ids: set[str],
    include_self_messages: bool,
    self_user_id: str,
    limit_per_room: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    joined_rooms = sync_payload.get("rooms", {}).get("join", {})
    if not isinstance(joined_rooms, dict):
        return out

    for room_id, room_data in joined_rooms.items():
        if room_id not in room_ids:
            continue
        if not isinstance(room_data, dict):
            continue
        timeline = room_data.get("timeline", {})
        events = timeline.get("events", []) if isinstance(timeline, dict) else []
        if not isinstance(events, list):
            continue

        room_rows: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "m.room.message":
                continue
            sender = event.get("sender")
            if not isinstance(sender, str) or sender == "":
                continue
            if not include_self_messages and sender == self_user_id:
                continue
            content = event.get("content")
            if not isinstance(content, dict):
                continue
            body = content.get("body")
            if not isinstance(body, str):
                continue
            text = body.strip()
            if text == "":
                continue
            event_id = event.get("event_id")
            source_id = event_id if isinstance(event_id, str) and event_id != "" else str(uuid4())
            room_rows.append(
                {
                    "source_id": source_id,
                    "room_id": room_id,
                    "sender_id": sender,
                    "content": text,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "msgtype": content.get("msgtype"),
                }
            )

        if len(room_rows) > limit_per_room:
            room_rows = room_rows[-limit_per_room:]
        out.extend(room_rows)

    return out


def _collect_secretary_agent(profiles: list[AgentProfile]) -> AgentProfile:
    for item in profiles:
        if item.kind == AgentKind.SECRETARY:
            return item
    raise HTTPException(status_code=404, detail="secretary_not_found")


async def _ensure_secretary_agent(
    *,
    request: Request,
    opa_client: OPAClient,
    user_id: str,
) -> AgentProfile:
    store = _agent_store(request, opa_client)
    try:
        await store.ensure_secretary(user_id)
        profiles = await store.list_agents(user_id)
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc
    return _collect_secretary_agent(profiles)


async def _send_agent_message_to_room(
    *,
    request: Request,
    user_access_token: str,
    agent_id: str,
    room_id: str,
    body: str,
) -> tuple[str | None, str | None]:
    matrix_client = _matrix_client(request)
    bot_manager = _bot_manager(request)
    try:
        bot_identity = await bot_manager.ensure_identity(agent_id=agent_id)
        bot_user_id = bot_identity.user_id
        try:
            await matrix_client.join_room(access_token=bot_identity.access_token, room_id=room_id)
        except MatrixClientError:
            await matrix_client.invite_user(
                access_token=user_access_token,
                room_id=room_id,
                user_id=bot_identity.user_id,
            )
            await matrix_client.join_room(access_token=bot_identity.access_token, room_id=room_id)

        send_payload = await matrix_client.send_text_message(
            access_token=bot_identity.access_token,
            room_id=room_id,
            body=body,
        )
    except (AgentBotManagerError, MatrixClientError) as exc:
        raise HTTPException(status_code=502, detail=f"matrix_send_failed: {exc}") from exc

    event_id_raw = send_payload.get("event_id")
    room_event_id = event_id_raw if isinstance(event_id_raw, str) and event_id_raw != "" else None
    return room_event_id, bot_user_id


async def _send_user_message_to_room(
    *,
    request: Request,
    user_access_token: str,
    room_id: str,
    body: str,
) -> str | None:
    matrix_client = _matrix_client(request)
    try:
        send_payload = await matrix_client.send_text_message(
            access_token=user_access_token,
            room_id=room_id,
            body=body,
        )
    except MatrixClientError as exc:
        raise HTTPException(status_code=502, detail=f"matrix_send_failed: {exc}") from exc
    event_id_raw = send_payload.get("event_id")
    return event_id_raw if isinstance(event_id_raw, str) and event_id_raw != "" else None


def _is_generated_assistant_message(body: str) -> bool:
    cleaned = body.strip()
    if cleaned == "":
        return False
    return (
        cleaned.startswith("[Secretary:")
        or cleaned.startswith("[Agent:")
        or SECRETARY_AUTO_REPLY_MARKER in cleaned
    )


async def _load_recent_room_context(
    *,
    request: Request,
    user_access_token: str,
    room_id: str,
    limit: int = 12,
) -> list[str]:
    matrix_client = _matrix_client(request)
    try:
        payload = await matrix_client.sync(
            access_token=user_access_token,
            since=None,
            timeout_ms=0,
            full_state=False,
        )
    except MatrixClientError:
        return []

    joined_rooms = payload.get("rooms", {}).get("join", {})
    if not isinstance(joined_rooms, dict):
        return []
    room_data = joined_rooms.get(room_id)
    if not isinstance(room_data, dict):
        return []
    timeline = room_data.get("timeline", {})
    events = timeline.get("events", []) if isinstance(timeline, dict) else []
    if not isinstance(events, list):
        return []

    out: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("type") != "m.room.message":
            continue
        content = event.get("content")
        if not isinstance(content, dict):
            continue
        body = content.get("body")
        if not isinstance(body, str):
            continue
        text = body.strip()
        if text == "" or _is_generated_assistant_message(text):
            continue
        sender_raw = event.get("sender")
        sender = sender_raw if isinstance(sender_raw, str) and sender_raw.strip() else "unknown"
        out.append(f"{sender}: {text}")

    if limit <= 0:
        return []
    return out[-limit:]


async def _refine_skill_output_with_llm(
    *,
    profile: AgentProfile,
    skill_id: str,
    query: str,
    room_messages: list[str],
    memory_snippets: list[str],
    output_text: str,
) -> tuple[str, dict[str, Any]]:
    llm = profile.llm
    if llm is None or not llm.enabled:
        return output_text, {}

    compact_room_messages = "\n".join(
        [f"- {' '.join(item.strip().split())[:220]}" for item in room_messages[-8:] if item.strip()]
    )
    compact_memory_snippets = "\n".join(
        [
            f"- {' '.join(item.strip().split())[:220]}"
            for item in memory_snippets[-8:]
            if item.strip()
        ]
    )
    system_prompt = (
        "You are an enterprise assistant result refiner. "
        "Preserve facts. Return concise actionable text. Do not invent new claims."
    )
    user_prompt = (
        f"Agent: {profile.agent_id}\n"
        f"Purpose: {profile.purpose}\n"
        f"Skill: {skill_id}\n"
        f"Query: {query}\n\n"
        f"Recent room context:\n{compact_room_messages or '(none)'}\n\n"
        f"Memory context:\n{compact_memory_snippets or '(none)'}\n\n"
        f"Draft output:\n{output_text}\n\n"
        "Rewrite the draft output to be clearer and directly executable. "
        "Keep it under 1200 characters."
    )
    try:
        rewritten = await chat_completion(
            config=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    except AgentLLMError as exc:
        return output_text, {"status": "fallback", "error": str(exc)}

    cleaned = rewritten.strip()
    if cleaned == "":
        return output_text, {"status": "fallback", "error": "empty_llm_response"}
    if len(cleaned) > 1200:
        cleaned = f"{cleaned[:1197]}..."
    return cleaned, {"status": "ok", "provider": llm.provider.value, "model": llm.model}


@router.get("/skills")
async def list_skills(request: Request) -> dict[str, list[SkillManifestView]]:
    registry = _skill_registry(request)
    skills = [
        SkillManifestView(
            skill_id=item.skill_id,
            display_name=item.display_name,
            description=item.description,
            triggers=list(item.triggers),
            permissions=list(item.permissions),
            risk_level=item.risk_level,
        )
        for item in registry.all()
    ]
    return {"skills": skills}


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_agents(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> BootstrapResponse:
    store = _agent_store(request, opa_client)
    try:
        secretary = await store.ensure_secretary(authenticated_user.user_id)
        profiles = await store.list_agents(authenticated_user.user_id)
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    specialists = [profile for profile in profiles if profile.kind == AgentKind.SPECIALIST]

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="agent_bootstrap_profiles",
            resource_type="agent",
            resource_id=secretary.agent_id,
            decision=DecisionType.ALLOW,
            reason_code="bootstrap_ok",
            user_id=authenticated_user.user_id,
            metadata={"specialist_count": len(specialists)},
        ),
    )

    return BootstrapResponse(secretary=secretary, specialists=specialists)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    request: Request,
    include_disabled: bool = Query(default=False),
    ensure_secretary: bool = Query(default=True),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> AgentListResponse:
    store = _agent_store(request, opa_client)
    try:
        if ensure_secretary:
            await store.ensure_secretary(authenticated_user.user_id)
        profiles = await store.list_agents(authenticated_user.user_id)
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    if include_disabled:
        return AgentListResponse(agents=profiles)

    active = [profile for profile in profiles if profile.status == AgentStatus.ACTIVE]
    return AgentListResponse(agents=active)


@router.get("/secretary", response_model=dict[str, Any])
async def get_secretary(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> dict[str, Any]:
    secretary = await _ensure_secretary_agent(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
    )
    return secretary.model_dump(mode="json")


@router.post("", response_model=dict[str, Any], status_code=201)
async def create_agent(
    payload: AgentUpsertRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _agent_store(request, opa_client)
    try:
        profile = await store.upsert_agent(authenticated_user.user_id, payload)
    except AgentStoreError as exc:
        detail = str(exc)
        if detail == "secretary_already_exists":
            raise HTTPException(status_code=409, detail=detail) from exc
        if detail in {
            "invalid_parent_policy_mode",
            "secretary_required_for_specialist",
            "manager_must_be_secretary",
            "manager_agent_not_found",
        }:
            raise HTTPException(status_code=422, detail=detail) from exc
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="agent_profile_upsert",
            resource_type="agent",
            resource_id=profile.agent_id,
            decision=DecisionType.ALLOW,
            reason_code="profile_saved",
            user_id=authenticated_user.user_id,
            metadata={"kind": profile.kind.value, "purpose": profile.purpose},
        ),
    )
    return profile.model_dump(mode="json")


@router.patch("/{agent_id}", response_model=dict[str, Any])
async def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _agent_store(request, opa_client)
    try:
        profile = await store.update_agent(authenticated_user.user_id, agent_id, payload)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        detail = str(exc)
        if detail in {
            "invalid_parent_policy_mode",
            "manager_agent_only_for_specialist",
            "manager_agent_id_empty",
            "manager_must_be_secretary",
            "manager_agent_not_found",
        }:
            raise HTTPException(status_code=422, detail=detail) from exc
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="agent_profile_update",
            resource_type="agent",
            resource_id=profile.agent_id,
            decision=DecisionType.ALLOW,
            reason_code="profile_updated",
            user_id=authenticated_user.user_id,
            metadata={"status": profile.status.value, "purpose": profile.purpose},
        ),
    )
    return profile.model_dump(mode="json")


@router.get("/secretary/modes", response_model=SecretaryRoomModeListResponse)
async def list_secretary_room_modes(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> SecretaryRoomModeListResponse:
    store = _agent_store(request, opa_client)
    secretary = await _ensure_secretary_agent(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
    )
    try:
        modes = await store.list_room_modes(
            user_id=authenticated_user.user_id,
            secretary_agent_id=secretary.agent_id,
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc
    return SecretaryRoomModeListResponse(modes=modes)


@router.put("/secretary/modes/{room_id}", response_model=SecretaryRoomModeRecord)
async def upsert_secretary_room_mode(
    room_id: str,
    payload: SecretaryRoomModeUpsertRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> SecretaryRoomModeRecord:
    room_id_clean = room_id.strip()
    if room_id_clean == "":
        raise HTTPException(status_code=422, detail="room_id_required")

    store = _agent_store(request, opa_client)
    secretary = await _ensure_secretary_agent(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
    )
    try:
        record = await store.set_room_mode(
            user_id=authenticated_user.user_id,
            secretary_agent_id=secretary.agent_id,
            room_id=room_id_clean,
            mode=payload.mode,
            updated_by=authenticated_user.user_id,
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="secretary_room_mode_upsert",
            resource_type="policy",
            resource_id=room_id_clean,
            decision=DecisionType.ALLOW,
            reason_code="room_mode_saved",
            user_id=authenticated_user.user_id,
            room_id=room_id_clean,
            metadata={"mode": payload.mode.value, "secretary_agent_id": secretary.agent_id},
        ),
    )
    return record


@router.get("/secretary/suggestions", response_model=SecretarySuggestionListResponse)
async def list_secretary_suggestions(
    request: Request,
    room_id: str | None = Query(default=None),
    status: SecretarySuggestionStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> SecretarySuggestionListResponse:
    store = _agent_store(request, opa_client)
    secretary = await _ensure_secretary_agent(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
    )
    room_filter = room_id.strip() if isinstance(room_id, str) and room_id.strip() else None
    try:
        suggestions = await store.list_suggestions(
            user_id=authenticated_user.user_id,
            room_id=room_filter,
            secretary_agent_id=secretary.agent_id,
            status=status,
            limit=limit,
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc
    return SecretarySuggestionListResponse(suggestions=suggestions)


@router.get("/secretary/insights", response_model=AssistantInsightListResponse)
async def list_secretary_insights(
    request: Request,
    room_id: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=600),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> AssistantInsightListResponse:
    store = _agent_store(request, opa_client)
    secretary = await _ensure_secretary_agent(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
    )
    room_filter = room_id.strip() if isinstance(room_id, str) and room_id.strip() else None
    try:
        insights = await store.list_insights(
            user_id=authenticated_user.user_id,
            room_id=room_filter,
            secretary_agent_id=secretary.agent_id,
            limit=limit,
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc
    return AssistantInsightListResponse(insights=insights)


@router.post("/secretary/suggestions/generate", response_model=dict[str, Any])
async def generate_secretary_suggestion(
    payload: SecretarySuggestionCreateRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    room_id = payload.room_id.strip()
    if room_id == "":
        raise HTTPException(status_code=422, detail="room_id_required")

    store = _agent_store(request, opa_client)
    secretary = await _ensure_secretary_agent(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
    )

    try:
        mode_record = await store.get_room_mode(
            user_id=authenticated_user.user_id,
            secretary_agent_id=secretary.agent_id,
            room_id=room_id,
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc
    room_mode = mode_record.mode if mode_record is not None else SecretaryRoomMode.OFF

    allow, reason, request_count = await _evaluate_policy(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
        agent_id=secretary.agent_id,
        room_id=room_id,
        purpose=payload.purpose,
        action="run_skill",
        data_category="room_messages",
    )
    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=secretary.agent_id,
            action_type="agent_policy_check",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.ALLOW if allow else DecisionType.DENY,
            reason_code=reason,
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "purpose": payload.purpose,
                "action": "run_skill",
                "request_count_per_minute": request_count,
            },
        ),
    )
    if not allow:
        raise HTTPException(status_code=403, detail={"status": "denied", "reason": reason})

    source_sender_id = (
        payload.source_sender_id.strip()
        if isinstance(payload.source_sender_id, str) and payload.source_sender_id.strip()
        else None
    )
    source_event_id = (
        payload.source_event_id.strip()
        if isinstance(payload.source_event_id, str) and payload.source_event_id.strip()
        else ""
    )
    try:
        source_memory_entry = await store.create_memory_entry(
            user_id=authenticated_user.user_id,
            agent_id=secretary.agent_id,
            source_type=MemorySourceType.MATRIX_ROOM_MESSAGE,
            source_id=source_event_id,
            content=payload.source_text,
            room_id=room_id,
            sender_id=source_sender_id,
            tags=["secretary_auto_ingest", "incoming_message"],
            importance=0.66,
            metadata={
                "source": "secretary_suggestion_generate",
                "purpose": payload.purpose,
                "room_mode": room_mode.value,
            },
        )
        memory_append_result = await store.append_memory_entries(
            user_id=authenticated_user.user_id,
            agent_id=secretary.agent_id,
            entries=[source_memory_entry],
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=secretary.agent_id,
            action_type="agent_memory_collect",
            resource_type="memory",
            resource_id=secretary.agent_id,
            decision=DecisionType.ALLOW,
            reason_code="secretary_auto_ingest",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "purpose": payload.purpose,
                "room_mode": room_mode.value,
                "source_event_id": source_event_id or None,
                "stored_count": memory_append_result.stored_count,
                "skipped_count": memory_append_result.skipped_count,
            },
        ),
    )

    context_messages = await _load_recent_room_context(
        request=request,
        user_access_token=authenticated_user.access_token,
        room_id=room_id,
        limit=12,
    )
    suggestion_text, insights, generation_source = await build_secretary_response_bundle(
        source_text=payload.source_text,
        context_messages=context_messages,
        llm_config=secretary.llm,
    )
    try:
        persisted_insights = await store.append_insights(
            user_id=authenticated_user.user_id,
            secretary_agent_id=secretary.agent_id,
            room_id=room_id,
            source_event_id=payload.source_event_id,
            insights=insights,
            metadata={
                "purpose": payload.purpose,
                "generation_source": generation_source,
                "context_message_count": len(context_messages),
            },
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    if room_mode == SecretaryRoomMode.OFF:
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.AGENT,
                actor_id=secretary.agent_id,
                action_type="secretary_suggestion_generate",
                resource_type="room",
                resource_id=room_id,
                decision=DecisionType.ALLOW,
                reason_code="room_mode_off",
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={"mode": room_mode.value},
            ),
        )
        return {
            "status": "ignored",
            "mode": room_mode.value,
            "reason": "room_mode_off",
            "generation_source": generation_source,
            "context_message_count": len(context_messages),
            "memory_ingest": {
                "stored_count": memory_append_result.stored_count,
                "skipped_count": memory_append_result.skipped_count,
            },
            "insights": [item.model_dump(mode="json") for item in persisted_insights],
        }

    try:
        suggestion = await store.create_suggestion(
            user_id=authenticated_user.user_id,
            secretary_agent_id=secretary.agent_id,
            room_id=room_id,
            source_text=payload.source_text,
            suggested_text=suggestion_text,
            source_event_id=payload.source_event_id,
            source_sender_id=payload.source_sender_id,
            metadata={
                "purpose": payload.purpose,
                "mode": room_mode.value,
                "generation_source": generation_source,
                "context_message_count": len(context_messages),
            },
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    room_event_id: str | None = None
    bot_user_id: str | None = None
    final_suggestion = suggestion
    if room_mode == SecretaryRoomMode.AUTO:
        try:
            room_event_id = await _send_user_message_to_room(
                request=request,
                user_access_token=authenticated_user.access_token,
                room_id=room_id,
                body=f"{suggestion.suggested_text}\n\n{SECRETARY_AUTO_REPLY_MARKER}",
            )
            bot_user_id = authenticated_user.user_id
            final_suggestion = await store.update_suggestion_status(
                user_id=authenticated_user.user_id,
                suggestion_id=suggestion.suggestion_id,
                status=SecretarySuggestionStatus.POSTED,
                metadata_patch={
                    "room_event_id": room_event_id,
                    "bot_user_id": bot_user_id,
                    "auto_reply_marker": SECRETARY_AUTO_REPLY_MARKER,
                },
            )
        except HTTPException as exc:
            await _append_audit(
                immudb_client=immudb_client,
                event=AuditEventCreate(
                    actor_type=ActorType.AGENT,
                    actor_id=secretary.agent_id,
                    action_type="secretary_suggestion_send",
                    resource_type="room",
                    resource_id=room_id,
                    decision=DecisionType.DENY,
                    reason_code="matrix_send_failed",
                    user_id=authenticated_user.user_id,
                    room_id=room_id,
                    metadata={"suggestion_id": suggestion.suggestion_id, "error": str(exc.detail)},
                ),
            )
            raise
        except AgentStoreError as exc:
            raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=secretary.agent_id,
            action_type="secretary_suggestion_generate",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.ALLOW,
            reason_code="suggestion_generated",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "mode": room_mode.value,
                "suggestion_id": final_suggestion.suggestion_id,
                "status": final_suggestion.status.value,
                "insight_count": len(persisted_insights),
                "generation_source": generation_source,
                "context_message_count": len(context_messages),
            },
        ),
    )
    return {
        "status": "ok",
        "mode": room_mode.value,
        "generation_source": generation_source,
        "context_message_count": len(context_messages),
        "memory_ingest": {
            "stored_count": memory_append_result.stored_count,
            "skipped_count": memory_append_result.skipped_count,
        },
        "suggestion": final_suggestion.model_dump(mode="json"),
        "room_event_id": room_event_id,
        "bot_user_id": bot_user_id,
        "insights": [item.model_dump(mode="json") for item in persisted_insights],
    }


@router.post(
    "/secretary/suggestions/{suggestion_id}/approve",
    response_model=SecretarySuggestionActionResponse,
)
async def approve_secretary_suggestion(
    suggestion_id: str,
    payload: SecretarySuggestionActionRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> SecretarySuggestionActionResponse:
    store = _agent_store(request, opa_client)
    try:
        suggestion = await store.get_suggestion(
            user_id=authenticated_user.user_id,
            suggestion_id=suggestion_id,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    if suggestion.status != SecretarySuggestionStatus.PENDING:
        raise HTTPException(status_code=409, detail="suggestion_not_pending")

    allow, reason, request_count = await _evaluate_policy(
        request=request,
        opa_client=opa_client,
        user_id=authenticated_user.user_id,
        agent_id=suggestion.secretary_agent_id,
        room_id=suggestion.room_id,
        purpose=payload.purpose,
        action="run_skill",
        data_category="room_messages",
    )
    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=suggestion.secretary_agent_id,
            action_type="agent_policy_check",
            resource_type="room",
            resource_id=suggestion.room_id,
            decision=DecisionType.ALLOW if allow else DecisionType.DENY,
            reason_code=reason,
            user_id=authenticated_user.user_id,
            room_id=suggestion.room_id,
            metadata={
                "purpose": payload.purpose,
                "action": "run_skill",
                "request_count_per_minute": request_count,
            },
        ),
    )
    if not allow:
        raise HTTPException(status_code=403, detail={"status": "denied", "reason": reason})

    try:
        updated = await store.update_suggestion_status(
            user_id=authenticated_user.user_id,
            suggestion_id=suggestion.suggestion_id,
            status=SecretarySuggestionStatus.APPROVED,
            metadata_patch={"approved_by": authenticated_user.user_id},
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    room_event_id: str | None = None
    bot_user_id: str | None = None
    if payload.send_to_room:
        room_event_id, bot_user_id = await _send_agent_message_to_room(
            request=request,
            user_access_token=authenticated_user.access_token,
            agent_id=suggestion.secretary_agent_id,
            room_id=suggestion.room_id,
            body=f"[Secretary:{suggestion.secretary_agent_id}]\n{suggestion.suggested_text}",
        )
        try:
            updated = await store.update_suggestion_status(
                user_id=authenticated_user.user_id,
                suggestion_id=suggestion.suggestion_id,
                status=SecretarySuggestionStatus.POSTED,
                metadata_patch={"room_event_id": room_event_id, "bot_user_id": bot_user_id},
            )
        except AgentStoreError as exc:
            raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="secretary_suggestion_approve",
            resource_type="tool",
            resource_id=suggestion.suggestion_id,
            decision=DecisionType.ALLOW,
            reason_code="suggestion_approved",
            user_id=authenticated_user.user_id,
            room_id=suggestion.room_id,
            metadata={"send_to_room": payload.send_to_room, "room_event_id": room_event_id},
        ),
    )
    return SecretarySuggestionActionResponse(
        suggestion=updated,
        room_event_id=room_event_id,
        bot_user_id=bot_user_id,
    )


@router.post(
    "/secretary/suggestions/{suggestion_id}/reject",
    response_model=SecretarySuggestionActionResponse,
)
async def reject_secretary_suggestion(
    suggestion_id: str,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> SecretarySuggestionActionResponse:
    store = _agent_store(request, opa_client)
    try:
        suggestion = await store.get_suggestion(
            user_id=authenticated_user.user_id,
            suggestion_id=suggestion_id,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    if suggestion.status != SecretarySuggestionStatus.PENDING:
        raise HTTPException(status_code=409, detail="suggestion_not_pending")

    try:
        updated = await store.update_suggestion_status(
            user_id=authenticated_user.user_id,
            suggestion_id=suggestion.suggestion_id,
            status=SecretarySuggestionStatus.REJECTED,
            metadata_patch={"rejected_by": authenticated_user.user_id},
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc
    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="secretary_suggestion_reject",
            resource_type="tool",
            resource_id=suggestion.suggestion_id,
            decision=DecisionType.ALLOW,
            reason_code="suggestion_rejected",
            user_id=authenticated_user.user_id,
            room_id=suggestion.room_id,
        ),
    )
    return SecretarySuggestionActionResponse(
        suggestion=updated,
        room_event_id=None,
        bot_user_id=None,
    )


@router.post("/{agent_id}/memory/notes", response_model=dict[str, Any], status_code=201)
async def append_memory_note(
    agent_id: str,
    payload: MemoryNoteRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _agent_store(request, opa_client)
    try:
        await store.get_agent(authenticated_user.user_id, agent_id)
        entry = await store.create_memory_entry(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            source_type=MemorySourceType.MANUAL_NOTE,
            source_id=f"manual_note:{uuid4().hex}",
            content=payload.content,
            room_id=None,
            sender_id=authenticated_user.user_id,
            tags=payload.tags,
            importance=payload.importance,
            metadata={"source": "manual"},
        )
        append_result = await store.append_memory_entries(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            entries=[entry],
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="agent_memory_write",
            resource_type="agent",
            resource_id=agent_id,
            decision=DecisionType.ALLOW,
            reason_code="manual_note_saved",
            user_id=authenticated_user.user_id,
            metadata={"stored_count": append_result.stored_count},
        ),
    )

    return {
        "entry": entry.model_dump(mode="json"),
        "stored_count": append_result.stored_count,
        "skipped_count": append_result.skipped_count,
    }


@router.get("/{agent_id}/memory", response_model=MemorySearchResponse)
async def search_memory(
    agent_id: str,
    request: Request,
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=200),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
) -> MemorySearchResponse:
    store = _agent_store(request, opa_client)
    try:
        await store.get_agent(authenticated_user.user_id, agent_id)
        if q.strip() == "":
            hits = await store.list_memory_entries(
                user_id=authenticated_user.user_id,
                agent_id=agent_id,
                limit=limit,
            )
        else:
            hits = await store.search_memory_entries(
                user_id=authenticated_user.user_id,
                agent_id=agent_id,
                query=q,
                limit=limit,
            )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    return MemorySearchResponse(hits=hits)


@router.post("/{agent_id}/memory/collect", response_model=dict[str, Any])
async def collect_memory(
    agent_id: str,
    payload: MemoryCollectRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> dict[str, Any]:
    store = _agent_store(request, opa_client)
    try:
        profile = await store.get_agent(authenticated_user.user_id, agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    if profile.status != AgentStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="agent_inactive")

    matrix_client = _matrix_client(request)
    try:
        sync_payload = await matrix_client.sync(
            access_token=authenticated_user.access_token,
            since=None,
            timeout_ms=0,
            full_state=True,
        )
    except MatrixClientError as exc:
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.AGENT,
                actor_id=agent_id,
                action_type="agent_memory_collect",
                resource_type="memory",
                resource_id=agent_id,
                decision=DecisionType.DENY,
                reason_code="matrix_sync_failed",
                user_id=authenticated_user.user_id,
                metadata={"error": str(exc)},
            ),
        )
        raise HTTPException(status_code=502, detail=f"matrix_sync_failed: {exc}") from exc

    joined_rooms = sync_payload.get("rooms", {}).get("join", {})
    all_room_ids = set(joined_rooms.keys()) if isinstance(joined_rooms, dict) else set()
    requested_room_ids = set(payload.room_ids or [])
    room_ids = requested_room_ids if requested_room_ids else all_room_ids

    denied_rooms: list[dict[str, str]] = []
    allowed_rooms: set[str] = set()
    for room_id in sorted(room_ids):
        allow, reason, request_count = await _evaluate_policy(
            request=request,
            opa_client=opa_client,
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            room_id=room_id,
            purpose=payload.purpose,
            action="collect_messages",
            data_category="room_messages",
        )
        decision = DecisionType.ALLOW if allow else DecisionType.DENY
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.AGENT,
                actor_id=agent_id,
                action_type="agent_policy_check",
                resource_type="room",
                resource_id=room_id,
                decision=decision,
                reason_code=reason,
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={
                    "purpose": payload.purpose,
                    "request_count_per_minute": request_count,
                    "action": "collect_messages",
                },
            ),
        )
        if allow:
            allowed_rooms.add(room_id)
        else:
            denied_rooms.append({"room_id": room_id, "reason": reason})

    if room_ids and not allowed_rooms:
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.AGENT,
                actor_id=agent_id,
                action_type="agent_memory_collect",
                resource_type="memory",
                resource_id=agent_id,
                decision=DecisionType.DENY,
                reason_code="no_authorized_room",
                user_id=authenticated_user.user_id,
                metadata={
                    "purpose": payload.purpose,
                    "denied_rooms": denied_rooms,
                },
            ),
        )
        raise HTTPException(
            status_code=403,
            detail={
                "status": "denied",
                "reason": "no_authorized_room",
                "denied_rooms": denied_rooms,
            },
        )

    extracted = _extract_messages_from_sync(
        sync_payload=sync_payload,
        room_ids=allowed_rooms,
        include_self_messages=payload.include_self_messages,
        self_user_id=authenticated_user.user_id,
        limit_per_room=payload.limit_per_room,
    )

    entries: list[AgentMemoryEntry] = []
    for row in extracted:
        try:
            entries.append(
                await store.create_memory_entry(
                    user_id=authenticated_user.user_id,
                    agent_id=agent_id,
                    source_type=MemorySourceType.MATRIX_ROOM_MESSAGE,
                    source_id=str(row["source_id"]),
                    content=str(row["content"]),
                    room_id=str(row["room_id"]),
                    sender_id=str(row["sender_id"]),
                    tags=["matrix", "room_message"],
                    importance=0.55,
                    metadata={
                        "event_id": row.get("event_id"),
                        "msgtype": row.get("msgtype"),
                    },
                )
            )
        except AgentStoreError:
            continue

    try:
        append_result = await store.append_memory_entries(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            entries=entries,
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=agent_id,
            action_type="agent_memory_collect",
            resource_type="memory",
            resource_id=agent_id,
            decision=DecisionType.ALLOW,
            reason_code="collect_ok",
            user_id=authenticated_user.user_id,
            metadata={
                "kind": profile.kind.value,
                "purpose": payload.purpose,
                "allowed_room_count": len(allowed_rooms),
                "denied_rooms": denied_rooms,
                "stored_count": append_result.stored_count,
                "skipped_count": append_result.skipped_count,
            },
        ),
    )

    return {
        "agent_id": agent_id,
        "stored_count": append_result.stored_count,
        "skipped_count": append_result.skipped_count,
        "allowed_room_count": len(allowed_rooms),
        "denied_rooms": denied_rooms,
    }


@router.post("/{agent_id}/skills/run", response_model=SkillRunResponse)
async def run_agent_skill(
    agent_id: str,
    payload: SkillRunRequest,
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    opa_client: OPAClient = Depends(get_opa_client),
    immudb_client: ImmudbClient = Depends(get_immudb_client),
) -> SkillRunResponse:
    store = _agent_store(request, opa_client)
    try:
        profile = await store.get_agent(authenticated_user.user_id, agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    if profile.status != AgentStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="agent_inactive")

    room_messages: list[str] = []
    room_id = payload.room_id.strip() if isinstance(payload.room_id, str) else ""

    if room_id != "":
        if profile.room_ids and room_id not in profile.room_ids:
            raise HTTPException(status_code=403, detail="room_not_in_agent_scope")

        allow, reason, request_count = await _evaluate_policy(
            request=request,
            opa_client=opa_client,
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            room_id=room_id,
            purpose=payload.purpose,
            action="run_skill",
            data_category="room_messages",
        )

        policy_decision = DecisionType.ALLOW if allow else DecisionType.DENY
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.AGENT,
                actor_id=agent_id,
                action_type="agent_policy_check",
                resource_type="room",
                resource_id=room_id,
                decision=policy_decision,
                reason_code=reason,
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={
                    "purpose": payload.purpose,
                    "request_count_per_minute": request_count,
                    "action": "run_skill",
                },
            ),
        )

        if not allow:
            raise HTTPException(status_code=403, detail={"status": "denied", "reason": reason})

        matrix_client = _matrix_client(request)
        try:
            room_messages = await matrix_client.read_room_messages(
                access_token=authenticated_user.access_token,
                room_id=room_id,
                limit=payload.room_message_limit,
            )
        except MatrixClientError as exc:
            await _append_audit(
                immudb_client=immudb_client,
                event=AuditEventCreate(
                    actor_type=ActorType.AGENT,
                    actor_id=agent_id,
                    action_type="agent_skill_run",
                    resource_type="room",
                    resource_id=room_id,
                    decision=DecisionType.DENY,
                    reason_code="matrix_read_messages_failed",
                    user_id=authenticated_user.user_id,
                    room_id=room_id,
                    metadata={"error": str(exc)},
                ),
            )
            raise HTTPException(
                status_code=502, detail=f"matrix_read_messages_failed: {exc}"
            ) from exc

    if payload.query.strip() == "":
        memory_entries = await store.list_memory_entries(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            limit=payload.memory_limit,
        )
    else:
        memory_entries = await store.search_memory_entries(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            query=payload.query,
            limit=payload.memory_limit,
        )

    memory_snippets = [entry.content for entry in memory_entries]

    registry = _skill_registry(request)
    router = SkillRouter(registry)
    chosen_skill_id = payload.skill_id.strip() if isinstance(payload.skill_id, str) else ""

    if chosen_skill_id == "":
        route = router.route(payload.query)
        if route is not None:
            chosen_skill_id = route.manifest.skill_id
        elif profile.skill_ids:
            chosen_skill_id = profile.skill_ids[0]
        else:
            chosen_skill_id = "secretary.daily_digest"

    manifest = registry.get(chosen_skill_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"skill_not_found:{chosen_skill_id}")

    if profile.skill_ids and manifest.skill_id not in profile.skill_ids:
        raise HTTPException(status_code=403, detail="skill_not_in_agent_profile")

    run_id = f"skillrun_{uuid4().hex[:16]}"
    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=agent_id,
            action_type="agent_skill_run_start",
            resource_type="skill",
            resource_id=manifest.skill_id,
            decision=DecisionType.ALLOW,
            reason_code="skill_run_started",
            user_id=authenticated_user.user_id,
            room_id=room_id or None,
            metadata={
                "run_id": run_id,
                "query": payload.query,
                "memory_count": len(memory_entries),
                "room_message_count": len(room_messages),
            },
        ),
    )

    executor = SkillExecutor()
    try:
        result = executor.execute(
            manifest.skill_id,
            SkillExecutionContext(
                query=payload.query,
                room_messages=room_messages,
                memory_snippets=memory_snippets,
            ),
        )
    except ValueError as exc:
        await _append_audit(
            immudb_client=immudb_client,
            event=AuditEventCreate(
                actor_type=ActorType.AGENT,
                actor_id=agent_id,
                action_type="agent_skill_run",
                resource_type="skill",
                resource_id=manifest.skill_id,
                decision=DecisionType.DENY,
                reason_code="skill_execution_failed",
                user_id=authenticated_user.user_id,
                room_id=room_id or None,
                metadata={"run_id": run_id, "error": str(exc)},
            ),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    final_output_text, llm_metadata = await _refine_skill_output_with_llm(
        profile=profile,
        skill_id=manifest.skill_id,
        query=payload.query,
        room_messages=room_messages,
        memory_snippets=memory_snippets,
        output_text=result.output_text,
    )
    final_output_data: dict[str, Any] = dict(result.output_data)
    if llm_metadata:
        final_output_data["llm"] = llm_metadata

    try:
        output_entry = await store.create_memory_entry(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            source_type=MemorySourceType.SKILL_OUTPUT,
            source_id=f"{run_id}:{manifest.skill_id}",
            content=final_output_text,
            room_id=room_id or None,
            sender_id=agent_id,
            tags=["skill_output", manifest.skill_id],
            importance=0.65,
            metadata={"output_data": final_output_data},
        )
        await store.append_memory_entries(
            user_id=authenticated_user.user_id,
            agent_id=agent_id,
            entries=[output_entry],
        )
    except AgentStoreError as exc:
        raise HTTPException(status_code=503, detail=f"agent_store_failed: {exc}") from exc

    room_event_id: str | None = None
    bot_user_id: str | None = None
    if payload.send_to_room:
        if room_id == "":
            raise HTTPException(status_code=422, detail="room_id_required_for_send")

        try:
            room_event_id, bot_user_id = await _send_agent_message_to_room(
                request=request,
                user_access_token=authenticated_user.access_token,
                agent_id=agent_id,
                room_id=room_id,
                body=f"[Agent:{agent_id}]\n{final_output_text}",
            )
        except HTTPException as exc:
            await _append_audit(
                immudb_client=immudb_client,
                event=AuditEventCreate(
                    actor_type=ActorType.AGENT,
                    actor_id=agent_id,
                    action_type="agent_skill_send",
                    resource_type="room",
                    resource_id=room_id,
                    decision=DecisionType.DENY,
                    reason_code="matrix_send_failed",
                    user_id=authenticated_user.user_id,
                    room_id=room_id,
                    metadata={"run_id": run_id, "error": str(exc.detail)},
                ),
            )
            raise exc

    await _append_audit(
        immudb_client=immudb_client,
        event=AuditEventCreate(
            actor_type=ActorType.AGENT,
            actor_id=agent_id,
            action_type="agent_skill_run",
            resource_type="skill",
            resource_id=manifest.skill_id,
            decision=DecisionType.ALLOW,
            reason_code="skill_run_finished",
            user_id=authenticated_user.user_id,
            room_id=room_id or None,
            metadata={
                "run_id": run_id,
                "output_length": len(final_output_text),
                "room_event_id": room_event_id,
                "llm": llm_metadata,
            },
        ),
    )

    return SkillRunResponse(
        status="ok",
        agent_id=agent_id,
        skill_id=manifest.skill_id,
        output_text=final_output_text,
        output_data=final_output_data,
        room_event_id=room_event_id,
        bot_user_id=bot_user_id,
    )
