# Agent Product Design Review (Create Agent Page)

## 1. Scope
This document organizes the current Create Agent design, lists key issues, and checks the gap against our target product:
- Each user has one default digital secretary agent.
- Each user can create multiple specialist agents.
- Specialist agents are managed by the secretary agent.
- In room chat, secretary supports three modes:
  - fully automatic reply
  - semi-automatic suggestion with user confirmation
  - no reply assistance
- Chat page right sidebar shows secretary insights:
  - realtime analysis
  - deep thinking
  - implied meaning
  - roast/commentary

## 2. Current State (As-Is)
Current implementation mainly lives in:
- Frontend:
  - `services/gateway_api/app/web/index.html`
  - `services/gateway_api/app/web/app.js`
- Backend:
  - `services/gateway_api/app/api/agents.py`
  - `services/gateway_api/app/agent/assistant_models.py`
  - `services/gateway_api/app/agent/memory_store.py`
  - `services/gateway_api/app/agent/skills/*`

Current Create Agent page supports:
- Bootstrap secretary + list agents + list skills.
- Secretary profile save, grant, collect memory, run digest.
- Specialist creation, quick run, collect memory.
- Memory search/recent/manual note.
- Skill run panel with optional send-to-room.

## 3. What Works Today
- Default secretary bootstrap is available (`ensure_secretary`).
- Multiple specialist agents can be created.
- Memory entries are persisted and searchable.
- Skill pipeline works end-to-end:
  - `SkillRegistry -> SkillRouter -> SkillExecutor`
- OPA policy decisions are integrated for memory collect and skill run.
- Audit events are written around profile changes, policy checks, memory collect/write, and skill runs.

## 4. Main Problems in Current Create Agent Design

### 4.1 Information architecture is overloaded
- One tab mixes too many responsibilities:
  - lifecycle, authorization, memory operations, and execution controls.
- The user mental model is weak:
  - "who manages whom" and "what runs automatically" are not clear.

### 4.2 Secretary-specialist management relation is missing
- Specialist agents are only same-level records with `kind="specialist"`.
- No explicit ownership link to secretary:
  - missing `manager_agent_id` or equivalent governance relation.
- "Secretary manages specialists" cannot be enforced.

### 4.3 Reply-mode product capability is missing
- No room-level mode model for:
  - auto reply
  - semi-auto suggestion
  - off
- No trigger loop for incoming room messages to mode-based assistant behavior.

### 4.4 No structured suggestion/approval workflow
- Semi-auto requires "generate suggestion -> user confirm -> post" flow.
- Current API only supports direct skill run; no queue/state for pending suggestions.

### 4.5 Chat right sidebar intelligence area is missing
- No dedicated data model or API for:
  - realtime analysis
  - deep thinking
  - implied meaning
  - roast/commentary
- Current right side is a fixed composer, not an assistant insight workspace.

### 4.6 Product and API still include legacy overlap
- Legacy "Create Agent Profile / Grant / Revoke / Run Skill" controls coexist with secretary-specialist controls.
- Creates duplicated pathways and inconsistent behavior expectations.

### 4.7 Automation semantics are weak
- Memory collect and skill execution are mostly manual button actions.
- Missing default background orchestration policy:
  - message ingestion cadence
  - summarization cadence
  - safe send guards

## 5. Gap vs Target

### 5.1 Agent structure
- Target: one secretary + many specialists managed by secretary.
- Current: one secretary + many specialists exists, but no secretary governance relation.
- Gap: add explicit hierarchy and enforcement.

### 5.2 Chat behavior modes
- Target: per-room `auto / semi / off`.
- Current: not implemented.
- Gap: add config model + runtime decision loop.

### 5.3 Right sidebar intelligence
- Target: realtime analysis/deep thinking/implied meaning/roast.
- Current: not implemented as structured outputs.
- Gap: add insight generation pipeline and UI panels.

### 5.4 Human-in-the-loop safety
- Target: semi-auto suggestion with confirmation.
- Current: direct run/send without suggestion queue.
- Gap: add suggestion state machine and approval APIs.

### 5.5 Management UX
- Target: secretary is the control plane for specialists.
- Current: specialist actions are independent in the same form panel.
- Gap: redesign to "secretary-first" management console.

## 6. Target Product Design (Next Version)

### 6.1 Agent hierarchy
- `secretary`:
  - per-user singleton.
  - can supervise specialist execution.
- `specialist`:
  - must reference a manager secretary.
  - execution policy and room scope inherited or constrained by secretary policy.

Suggested model additions:
- `AgentProfile.manager_agent_id: str | None`
- `AgentProfile.parent_policy_mode: "inherit" | "custom"`

### 6.2 Secretary room mode
Introduce per-room mode config:
- `auto`:
  - secretary can post automatically under policy/rate limits.
- `semi`:
  - secretary creates reply suggestions; user approves/rejects.
- `off`:
  - secretary does not assist with replies, can still keep memory if allowed.

Suggested object:
- `SecretaryRoomMode`:
  - `owner_user_id`, `secretary_agent_id`, `room_id`, `mode`, `updated_at`

### 6.3 Suggestion workflow
Add suggestion queue:
- states:
  - `pending`, `approved`, `rejected`, `expired`, `posted`
- core APIs:
  - create suggestion from incoming room event
  - list pending suggestions
  - approve/reject suggestion
  - post approved suggestion to room

### 6.4 Right sidebar assistant insights
Add insight channels:
- realtime analysis
- deep thinking
- implied meaning
- roast/commentary

Suggested object:
- `AssistantInsight`:
  - `insight_id`, `room_id`, `agent_id`, `channel`, `content`, `source_event_id`, `created_at`

### 6.5 UI redesign direction
- Keep `Create Agent` focused on:
  - secretary profile
  - specialist creation and attachment to secretary
  - permission scope
- Move runtime interaction to chat page:
  - room mode switch
  - suggestion approval queue
  - right sidebar insight cards

## 7. Recommended Backend API Additions
- `GET /api/v1/agents/secretary`
- `PATCH /api/v1/agents/{agent_id}`:
  - support `manager_agent_id` updates for specialists.
- `PUT /api/v1/agents/secretary/modes/{room_id}`
- `GET /api/v1/agents/secretary/modes`
- `POST /api/v1/agents/secretary/suggestions/{id}/approve`
- `POST /api/v1/agents/secretary/suggestions/{id}/reject`
- `GET /api/v1/agents/secretary/suggestions`
- `GET /api/v1/agents/secretary/insights?room_id=...`

All write paths must:
- pass OPA check where applicable
- write immutable audit event (allow and deny)

## 8. Recommended Execution Plan
1. Data model upgrade:
   - add manager relation + room mode + suggestion + insight schema.
2. API upgrade:
   - add room mode and suggestion endpoints first.
3. Runtime upgrade:
   - add incoming message hook to secretary mode dispatcher.
4. Frontend upgrade:
   - chat right sidebar for insights + suggestion review.
5. Safety and audit completion:
   - deny reasons, rate limits, and full event coverage.

## 9. Definition of Done for This Target
- User sees default secretary after login.
- User can create multiple specialists and bind each to secretary.
- In each room, user can switch secretary mode:
  - auto / semi / off.
- Semi mode produces pending suggestions and requires explicit approval.
- Right sidebar shows the 4 insight channels in near realtime.
- Every key action writes immutable audit record with allow/deny reason.
