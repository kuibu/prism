from __future__ import annotations

from typing import Any, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel, Field

from app.audit.immudb_client import ImmudbClient, ImmudbOperationError
from app.audit.schemas import ActorType, AuditEventCreate, DecisionType
from app.core.deps import AuthenticatedUser, get_authenticated_user
from app.matrix.client import MatrixClientError

router = APIRouter(prefix="/matrix", tags=["matrix"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class MatrixAuthResponse(BaseModel):
    user_id: str
    device_id: str | None = None
    access_token: str


class MatrixWhoamiResponse(BaseModel):
    user_id: str


class CreateRoomRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    invite: list[str] = Field(default_factory=list, max_length=50)
    preset: str = Field(default="private_chat", max_length=64)


class CreateRoomResponse(BaseModel):
    room_id: str


class JoinRoomResponse(BaseModel):
    room_id: str


class InviteUserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)


class InviteUserResponse(BaseModel):
    room_id: str
    user_id: str


class RoomMembersResponse(BaseModel):
    room_id: str
    joined_count: int
    joined_user_ids: list[str]


class RoomSummaryResponse(BaseModel):
    room_id: str
    room_name: str | None = None
    creator_user_id: str | None = None
    joined_count: int
    joined_user_ids: list[str]


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class SendMessageResponse(BaseModel):
    room_id: str
    event_id: str


class SendFileResponse(BaseModel):
    room_id: str
    event_id: str
    content_uri: str
    filename: str
    size_bytes: int


async def _write_audit_or_raise(
    *,
    immudb_client: ImmudbClient,
    event: AuditEventCreate,
) -> None:
    try:
        await immudb_client.append_audit_event(event)
    except ImmudbOperationError as exc:
        raise HTTPException(status_code=503, detail=f"audit_write_failed: {exc}") from exc


def _map_matrix_error_status(exc: MatrixClientError) -> int:
    status_code = exc.status_code
    if isinstance(status_code, int):
        if status_code in {400, 401, 403, 404, 409, 429}:
            return status_code
        if 500 <= status_code < 600:
            return 502
    lowered = str(exc).lower()
    if "timed out" in lowered or "timeout" in lowered:
        return 504
    return 502


def _ordered_members(
    *,
    joined_user_ids: list[str],
    creator_user_id: str | None,
) -> list[str]:
    deduplicated = sorted({user_id for user_id in joined_user_ids if user_id != ""})
    if creator_user_id is None or creator_user_id == "":
        return deduplicated
    if creator_user_id in deduplicated:
        others = [item for item in deduplicated if item != creator_user_id]
        return [creator_user_id, *others]
    return deduplicated


@router.post("/register", response_model=MatrixAuthResponse, status_code=201)
async def matrix_register(request: RegisterRequest, http_request: Request) -> MatrixAuthResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        payload = await matrix_client.register(username=request.username, password=request.password)
    except MatrixClientError as exc:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=request.username,
            action_type="matrix_register",
            resource_type="user",
            resource_id=request.username,
            decision=DecisionType.DENY,
            reason_code="matrix_register_failed",
            metadata={"error": str(exc)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        raise HTTPException(status_code=502, detail=f"matrix_register_failed: {exc}") from exc

    user_id = payload.get("user_id")
    access_token = payload.get("access_token")
    device_id = payload.get("device_id")
    if not isinstance(user_id, str) or user_id == "" or not isinstance(access_token, str):
        raise HTTPException(status_code=502, detail="matrix_register_invalid_response")

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=user_id,
        action_type="matrix_register",
        resource_type="user",
        resource_id=user_id,
        decision=DecisionType.ALLOW,
        reason_code="register_ok",
        user_id=user_id,
        metadata={"device_id": device_id},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)
    return MatrixAuthResponse(user_id=user_id, device_id=device_id, access_token=access_token)


@router.post("/login", response_model=MatrixAuthResponse)
async def matrix_login(request: LoginRequest, http_request: Request) -> MatrixAuthResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        payload = await matrix_client.login(username=request.username, password=request.password)
    except MatrixClientError as exc:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=request.username,
            action_type="matrix_login",
            resource_type="user_session",
            resource_id=request.username,
            decision=DecisionType.DENY,
            reason_code="matrix_login_failed",
            metadata={"error": str(exc)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        raise HTTPException(status_code=502, detail=f"matrix_login_failed: {exc}") from exc

    user_id = payload.get("user_id")
    access_token = payload.get("access_token")
    device_id = payload.get("device_id")
    if not isinstance(user_id, str) or user_id == "" or not isinstance(access_token, str):
        raise HTTPException(status_code=502, detail="matrix_login_invalid_response")

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=user_id,
        action_type="matrix_login",
        resource_type="user_session",
        resource_id=user_id,
        decision=DecisionType.ALLOW,
        reason_code="login_ok",
        user_id=user_id,
        metadata={"device_id": device_id},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)
    return MatrixAuthResponse(user_id=user_id, device_id=device_id, access_token=access_token)


@router.get("/whoami", response_model=MatrixWhoamiResponse)
async def matrix_whoami(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> MatrixWhoamiResponse:
    return MatrixWhoamiResponse(user_id=authenticated_user.user_id)


@router.post("/rooms", response_model=CreateRoomResponse, status_code=201)
async def matrix_create_room(
    payload: CreateRoomRequest,
    http_request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CreateRoomResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        result = await matrix_client.create_room(
            access_token=authenticated_user.access_token,
            name=payload.name,
            invite=payload.invite,
            preset=payload.preset,
        )
    except MatrixClientError as exc:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_create_room",
            resource_type="room",
            resource_id="new_room",
            decision=DecisionType.DENY,
            reason_code="matrix_create_room_failed",
            user_id=authenticated_user.user_id,
            metadata={"error": str(exc), "invite_count": len(payload.invite)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        raise HTTPException(status_code=502, detail=f"matrix_create_room_failed: {exc}") from exc

    room_id = result.get("room_id")
    if not isinstance(room_id, str) or room_id == "":
        raise HTTPException(status_code=502, detail="matrix_create_room_invalid_response")

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_create_room",
        resource_type="room",
        resource_id=room_id,
        decision=DecisionType.ALLOW,
        reason_code="create_room_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        metadata={"invite_count": len(payload.invite)},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)
    return CreateRoomResponse(room_id=room_id)


@router.post("/rooms/{room_id}/join", response_model=JoinRoomResponse)
async def matrix_join_room(
    http_request: Request,
    room_id: str = Path(min_length=1, max_length=255),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JoinRoomResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        result = await matrix_client.join_room(
            access_token=authenticated_user.access_token,
            room_id=room_id,
        )
    except MatrixClientError as exc:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_join_room",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_join_room_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={"error": str(exc)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        raise HTTPException(status_code=502, detail=f"matrix_join_room_failed: {exc}") from exc

    joined_room_id = result.get("room_id", room_id)
    if not isinstance(joined_room_id, str) or joined_room_id == "":
        joined_room_id = room_id

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_join_room",
        resource_type="room",
        resource_id=joined_room_id,
        decision=DecisionType.ALLOW,
        reason_code="join_room_ok",
        user_id=authenticated_user.user_id,
        room_id=joined_room_id,
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)
    return JoinRoomResponse(room_id=joined_room_id)


@router.post("/rooms/{room_id}/invite", response_model=InviteUserResponse)
async def matrix_invite_user(
    payload: InviteUserRequest,
    http_request: Request,
    room_id: str = Path(min_length=1, max_length=255),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> InviteUserResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        await matrix_client.invite_user(
            access_token=authenticated_user.access_token,
            room_id=room_id,
            user_id=payload.user_id,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_invite_user",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_invite_user_forbidden"
            if mapped_status == 403
            else "matrix_invite_user_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            input_data={"invitee_user_id": payload.user_id},
            metadata={
                "error": str(exc),
                "status_code": mapped_status,
            },
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        if mapped_status == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "matrix_invite_user_forbidden: inviter must be in room and have invite "
                    f"permission ({exc})"
                ),
            ) from exc
        raise HTTPException(
            status_code=mapped_status,
            detail=f"matrix_invite_user_failed: {exc}",
        ) from exc

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_invite_user",
        resource_type="room",
        resource_id=room_id,
        decision=DecisionType.ALLOW,
        reason_code="invite_user_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        input_data={"invitee_user_id": payload.user_id},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)

    return InviteUserResponse(room_id=room_id, user_id=payload.user_id)


@router.get("/rooms/{room_id}/members", response_model=RoomMembersResponse)
async def matrix_room_members(
    http_request: Request,
    room_id: str = Path(min_length=1, max_length=255),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> RoomMembersResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        payload = await matrix_client.get_joined_members(
            access_token=authenticated_user.access_token,
            room_id=room_id,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_get_joined_members",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_get_joined_members_forbidden"
            if mapped_status == 403
            else "matrix_get_joined_members_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "error": str(exc),
                "status_code": mapped_status,
            },
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        if mapped_status == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "matrix_get_joined_members_forbidden: join the room before viewing members "
                    f"({exc})"
                ),
            ) from exc
        raise HTTPException(
            status_code=mapped_status,
            detail=f"matrix_get_joined_members_failed: {exc}",
        ) from exc

    joined = payload.get("joined")
    if not isinstance(joined, dict):
        joined = {}
    joined_user_ids = [user_id for user_id in joined.keys() if isinstance(user_id, str) and user_id != ""]
    joined_user_ids.sort()

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_get_joined_members",
        resource_type="room",
        resource_id=room_id,
        decision=DecisionType.ALLOW,
        reason_code="get_joined_members_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        metadata={"joined_count": len(joined_user_ids)},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)

    return RoomMembersResponse(
        room_id=room_id,
        joined_count=len(joined_user_ids),
        joined_user_ids=joined_user_ids,
    )


@router.get("/rooms/{room_id}/summary", response_model=RoomSummaryResponse)
async def matrix_room_summary(
    http_request: Request,
    room_id: str = Path(min_length=1, max_length=255),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> RoomSummaryResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        members_payload = await matrix_client.get_joined_members(
            access_token=authenticated_user.access_token,
            room_id=room_id,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_get_room_summary",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_get_room_summary_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "error": str(exc),
                "status_code": mapped_status,
            },
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        if mapped_status == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "matrix_get_room_summary_forbidden: join the room before viewing summary "
                    f"({exc})"
                ),
            ) from exc
        raise HTTPException(
            status_code=mapped_status,
            detail=f"matrix_get_room_summary_failed: {exc}",
        ) from exc

    joined_raw = members_payload.get("joined")
    joined_user_ids = (
        [user_id for user_id in joined_raw.keys() if isinstance(user_id, str)]
        if isinstance(joined_raw, dict)
        else []
    )

    room_name: str | None = None
    creator_user_id: str | None = None
    try:
        name_payload = await matrix_client.get_room_state_event(
            access_token=authenticated_user.access_token,
            room_id=room_id,
            event_type="m.room.name",
        )
        name_value = name_payload.get("name")
        if isinstance(name_value, str) and name_value.strip() != "":
            room_name = name_value.strip()
    except MatrixClientError as exc:
        if exc.status_code not in {404}:
            mapped_status = _map_matrix_error_status(exc)
            deny_event = AuditEventCreate(
                actor_type=ActorType.USER,
                actor_id=authenticated_user.user_id,
                action_type="matrix_get_room_summary",
                resource_type="room",
                resource_id=room_id,
                decision=DecisionType.DENY,
                reason_code="matrix_get_room_summary_failed",
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={"error": str(exc), "status_code": mapped_status},
            )
            await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
            raise HTTPException(
                status_code=mapped_status,
                detail=f"matrix_get_room_summary_failed: {exc}",
            ) from exc

    try:
        create_payload = await matrix_client.get_room_state_event(
            access_token=authenticated_user.access_token,
            room_id=room_id,
            event_type="m.room.create",
        )
        creator_value = create_payload.get("creator")
        if isinstance(creator_value, str) and creator_value.strip() != "":
            creator_user_id = creator_value.strip()
    except MatrixClientError as exc:
        if exc.status_code not in {404}:
            mapped_status = _map_matrix_error_status(exc)
            deny_event = AuditEventCreate(
                actor_type=ActorType.USER,
                actor_id=authenticated_user.user_id,
                action_type="matrix_get_room_summary",
                resource_type="room",
                resource_id=room_id,
                decision=DecisionType.DENY,
                reason_code="matrix_get_room_summary_failed",
                user_id=authenticated_user.user_id,
                room_id=room_id,
                metadata={"error": str(exc), "status_code": mapped_status},
            )
            await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
            raise HTTPException(
                status_code=mapped_status,
                detail=f"matrix_get_room_summary_failed: {exc}",
            ) from exc

    ordered_user_ids = _ordered_members(
        joined_user_ids=joined_user_ids,
        creator_user_id=creator_user_id,
    )

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_get_room_summary",
        resource_type="room",
        resource_id=room_id,
        decision=DecisionType.ALLOW,
        reason_code="get_room_summary_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        metadata={
            "joined_count": len(ordered_user_ids),
            "room_name": room_name,
            "creator_user_id": creator_user_id,
        },
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)

    return RoomSummaryResponse(
        room_id=room_id,
        room_name=room_name,
        creator_user_id=creator_user_id,
        joined_count=len(ordered_user_ids),
        joined_user_ids=ordered_user_ids,
    )


@router.post("/rooms/{room_id}/messages", response_model=SendMessageResponse, status_code=201)
async def matrix_send_message(
    payload: SendMessageRequest,
    http_request: Request,
    room_id: str = Path(min_length=1, max_length=255),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> SendMessageResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client

    try:
        result = await matrix_client.send_text_message(
            access_token=authenticated_user.access_token,
            room_id=room_id,
            body=payload.body,
        )
    except MatrixClientError as exc:
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_send_message",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_send_message_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            input_data={"message_length": len(payload.body)},
            metadata={"error": str(exc)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        raise HTTPException(status_code=502, detail=f"matrix_send_message_failed: {exc}") from exc

    event_id = result.get("event_id")
    if not isinstance(event_id, str) or event_id == "":
        raise HTTPException(status_code=502, detail="matrix_send_message_invalid_response")

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_send_message",
        resource_type="message",
        resource_id=event_id,
        decision=DecisionType.ALLOW,
        reason_code="send_message_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        input_data={"message_length": len(payload.body)},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)
    return SendMessageResponse(room_id=room_id, event_id=event_id)


@router.post("/rooms/{room_id}/files", response_model=SendFileResponse, status_code=201)
async def matrix_send_file(
    http_request: Request,
    room_id: str = Path(min_length=1, max_length=255),
    file: UploadFile = File(...),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> SendFileResponse:
    matrix_client = http_request.app.state.matrix_client
    immudb_client = http_request.app.state.immudb_client
    settings = http_request.app.state.settings

    filename = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"
    max_bytes = int(settings.matrix_upload_max_bytes)
    content = await file.read(max_bytes + 1)
    size_bytes = len(content)

    if size_bytes == 0:
        raise HTTPException(status_code=422, detail="empty_file")
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail="file_too_large")

    try:
        upload_result = await matrix_client.upload_media(
            access_token=authenticated_user.access_token,
            filename=filename,
            content_type=content_type,
            content=content,
        )
    except MatrixClientError as exc:
        deny_upload_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_upload_media",
            resource_type="media",
            resource_id=filename,
            decision=DecisionType.DENY,
            reason_code="matrix_upload_media_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            input_data={
                "filename": filename,
                "size_bytes": size_bytes,
                "mime_type": content_type,
            },
            metadata={"error": str(exc)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_upload_event)
        raise HTTPException(status_code=502, detail=f"matrix_upload_media_failed: {exc}") from exc

    content_uri = upload_result.get("content_uri")
    if not isinstance(content_uri, str) or content_uri == "":
        raise HTTPException(status_code=502, detail="matrix_upload_media_invalid_response")

    allow_upload_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_upload_media",
        resource_type="media",
        resource_id=content_uri,
        decision=DecisionType.ALLOW,
        reason_code="upload_media_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        input_data={
            "filename": filename,
            "size_bytes": size_bytes,
            "mime_type": content_type,
        },
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_upload_event)

    try:
        send_result = await matrix_client.send_file_message(
            access_token=authenticated_user.access_token,
            room_id=room_id,
            filename=filename,
            content_uri=content_uri,
            content_type=content_type,
            size_bytes=size_bytes,
        )
    except MatrixClientError as exc:
        deny_send_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_send_file_message",
            resource_type="room",
            resource_id=room_id,
            decision=DecisionType.DENY,
            reason_code="matrix_send_file_message_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            input_data={"filename": filename, "content_uri": content_uri},
            metadata={"error": str(exc)},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_send_event)
        raise HTTPException(
            status_code=502,
            detail=f"matrix_send_file_message_failed: {exc}",
        ) from exc

    event_id = send_result.get("event_id")
    if not isinstance(event_id, str) or event_id == "":
        raise HTTPException(status_code=502, detail="matrix_send_file_message_invalid_response")

    allow_send_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_send_file_message",
        resource_type="message",
        resource_id=event_id,
        decision=DecisionType.ALLOW,
        reason_code="send_file_message_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        input_data={"filename": filename, "content_uri": content_uri},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_send_event)

    return SendFileResponse(
        room_id=room_id,
        event_id=event_id,
        content_uri=content_uri,
        filename=filename,
        size_bytes=size_bytes,
    )


@router.get("/media/download")
async def matrix_download_media(
    request: Request,
    mxc_uri: str = Query(min_length=8, max_length=1024),
    filename: str | None = Query(default=None, max_length=255),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> Response:
    matrix_client = request.app.state.matrix_client
    immudb_client = request.app.state.immudb_client

    safe_filename = (filename or "matrix-file.bin").strip() or "matrix-file.bin"
    safe_filename = safe_filename.replace("\"", "_").replace("\\", "_").replace("\n", "_")

    try:
        content, header_map = await matrix_client.download_media(
            access_token=authenticated_user.access_token,
            mxc_uri=mxc_uri,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_download_media",
            resource_type="media",
            resource_id=mxc_uri,
            decision=DecisionType.DENY,
            reason_code="matrix_download_media_failed",
            user_id=authenticated_user.user_id,
            input_data={"mxc_uri": mxc_uri},
            metadata={"error": str(exc), "status_code": mapped_status},
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)
        raise HTTPException(
            status_code=mapped_status,
            detail=f"matrix_download_media_failed: {exc}",
        ) from exc

    media_type = header_map.get("content-type") or "application/octet-stream"
    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_download_media",
        resource_type="media",
        resource_id=mxc_uri,
        decision=DecisionType.ALLOW,
        reason_code="download_media_ok",
        user_id=authenticated_user.user_id,
        metadata={"size_bytes": len(content), "media_type": media_type},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.get("/sync")
async def matrix_sync(
    request: Request,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    room_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    timeout_ms: int = Query(default=0, ge=0, le=60000),
    full_state: bool = Query(default=False),
) -> dict[str, Any]:
    matrix_client = request.app.state.matrix_client
    immudb_client = request.app.state.immudb_client

    try:
        payload = await matrix_client.sync(
            access_token=authenticated_user.access_token,
            since=since,
            timeout_ms=timeout_ms,
            full_state=full_state,
        )
    except MatrixClientError as exc:
        mapped_status = _map_matrix_error_status(exc)
        deny_event = AuditEventCreate(
            actor_type=ActorType.USER,
            actor_id=authenticated_user.user_id,
            action_type="matrix_sync",
            resource_type="room",
            resource_id=room_id or "all_rooms",
            decision=DecisionType.DENY,
            reason_code="matrix_sync_timeout" if mapped_status == 504 else "matrix_sync_failed",
            user_id=authenticated_user.user_id,
            room_id=room_id,
            metadata={
                "since": since,
                "timeout_ms": timeout_ms,
                "status_code": mapped_status,
                "error": str(exc),
            },
        )
        await _write_audit_or_raise(immudb_client=immudb_client, event=deny_event)

        if mapped_status == 504:
            raise HTTPException(
                status_code=504,
                detail=(
                    "matrix_sync_timeout: homeserver sync request timed out, "
                    f"please retry ({exc})"
                ),
            ) from exc
        raise HTTPException(status_code=mapped_status, detail=f"matrix_sync_failed: {exc}") from exc

    allow_event = AuditEventCreate(
        actor_type=ActorType.USER,
        actor_id=authenticated_user.user_id,
        action_type="matrix_sync",
        resource_type="room",
        resource_id=room_id or "all_rooms",
        decision=DecisionType.ALLOW,
        reason_code="sync_ok",
        user_id=authenticated_user.user_id,
        room_id=room_id,
        metadata={"since": since, "timeout_ms": timeout_ms},
    )
    await _write_audit_or_raise(immudb_client=immudb_client, event=allow_event)

    return cast(dict[str, Any], payload)
