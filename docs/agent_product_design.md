# 数字秘书联动产品设计对照（Agent Product Alignment）

## 1) 目标要求整理（来自你的要求）

### 1.1 Agent 结构
- 每个用户默认有且只有一个数字秘书 Agent（Secretary）。
- 每个用户可以创建多个专用 Agent（Specialists）。
- 所有专用 Agent 都由数字秘书管理。

### 1.2 房间联动行为
- 在聊天房间里，数字秘书收到新消息后支持三种模式：
  - `auto`：全自动回复。
  - `semi`：半自动建议（用户确认后发送）。
  - `off`：不进行回复辅助。

### 1.3 右侧秘书功能区
- 右侧侧栏展示秘书分析能力：
  - 实时分析
  - 深度思考
  - 言外之意
  - 吐槽

### 1.4 记忆与模型接入
- 数字秘书要收集与用户相关的信息和房间消息，沉淀到记忆中。
- 数字秘书与专用 Agent 都支持接入大模型（兼容千问 / OpenRouter / OpenAI-compatible）。

---

## 2) 当前实现对照（最新代码状态）

| 需求 | 状态 | 说明 |
|---|---|---|
| 默认秘书 Agent | 已实现 | `ensure_secretary` 自动兜底创建；前端加载 Agent 时会确保存在秘书。 |
| 多专用 Agent | 已实现 | 支持创建多个 `kind=specialist`。 |
| 专用 Agent 受秘书管理 | 已实现（基础） | 专用 Agent 创建时默认绑定 `manager_agent_id` 到秘书，并校验 manager 必须是秘书。 |
| 三种秘书模式 `auto/semi/off` | 已实现 | 后端有房间模式模型与 API；前端有模式下拉和保存。 |
| `auto` 自动回复 + 尾部标记 | 已实现 | 自动发送内容尾部带 `数字秘书自动回复` 标记。 |
| `semi` 生成建议并可确认发送 | 已实现 | 生成 pending suggestion；支持 approve/reject；建议可预填到快捷发送区。 |
| `off` 不回复辅助 | 已实现 | 返回 `ignored`，不自动回消息。 |
| 右侧分析四通道 | 已实现 | insights 支持四类通道并在右侧展示。 |
| LLM 配置（秘书+专用） | 已实现 | 前端可配置 provider/model/key/base_url/api_path；后端已打通。 |
| 默认 LLM 配置 | 已实现 | 支持环境变量默认注入（当前默认 qwen openai-compatible 端点）。 |
| 消息沉淀记忆 | 已补齐 | 联动处理时会自动将来源消息入秘书记忆（包含审计）。 |

---

## 3) 本轮补齐内容（修正项）

### 3.1 自动记忆沉淀补齐
- 文件：`services/gateway_api/app/api/agents.py`
- 在 `POST /api/v1/agents/secretary/suggestions/generate` 中新增：
  - 对来源消息创建 `MemorySourceType.MATRIX_ROOM_MESSAGE` 记忆条目；
  - append 到秘书 memory；
  - 写入审计事件 `agent_memory_collect`（reason: `secretary_auto_ingest`）；
  - 响应增加 `memory_ingest.stored_count/skipped_count`。

### 3.2 `off` 模式联动触发改造
- 文件：`services/gateway_api/app/web/app.js`
- 自动同步发现新外部消息时，不再只限 `auto/semi` 才触发联动。
- 统一交给后端按房间模式判定：
  - `off` 仍不发回复，但可完成“仅分析/仅记忆沉淀”。

### 3.3 测试补齐
- 文件：`services/gateway_api/app/tests/test_agents_hub.py`
- 增加/强化断言：
  - `semi` 建议生成时包含 `memory_ingest`；
  - `off` 模式下不创建建议，但能入记忆；
  - 同一 `source_event_id` 重复处理时，记忆去重正确（stored=0, skipped>=1）。

---

## 4) 仍需持续优化的点（真实差距）

1. 目前“自动联动”主要发生在前端打开会话并触发 `/sync` 的房间，不是独立后端消息总线。
2. “秘书管理专用 Agent”已实现关系绑定，但更细粒度的策略继承/覆盖规则（`inherit/custom` 的严格执行）仍可继续增强。
3. 记忆是结构化持久化（非向量检索），复杂语义召回能力可在后续迭代引入。
4. Agent 页仍保留一些 legacy 操作入口，后续可继续做“秘书优先”的信息架构收敛。

---

## 5) 验收要点（当前可验证）

- 登录后加载 Agent，默认可见秘书。
- 可创建多个专用 Agent，且 manager 指向秘书。
- 房间内切换 `auto/semi/off`：
  - `auto` 自动回消息并带秘书标记；
  - `semi` 产生建议，可批准/拒绝；
  - `off` 不自动回复，但会记录分析与记忆沉淀。
- 右侧可见秘书四类分析。
- 审计可看到策略检查、建议生成/审批、记忆沉淀等关键动作。
