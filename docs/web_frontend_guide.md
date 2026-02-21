# Prism Web Frontend Guide (微信风格)

## 1. 页面定位
- 这是一个 **WeChat 风格的联调前端**，用于快速验证 Matrix 聊天、Agent 授权/撤权、不可变审计链。
- 页面入口：`http://localhost:8080/web/`
- 顶部有语言按钮：`中文` / `EN`。

## 2. 页面分区说明

### 左侧：账号与房间
- `注册`：调用 `/matrix/register`
- `登录`：调用 `/matrix/login`
- `创建房间`：调用 `/matrix/rooms`
- `同步消息`：调用 `/matrix/sync`
- `当前房间 ID`：决定中间聊天窗口读取和发送到哪个房间

### 中间：聊天窗口（仿微信）
- 会显示消息气泡（自己的消息在右侧绿色气泡，他人消息在左侧白色气泡）。
- `发送`：调用 `/matrix/rooms/{room_id}/messages`
- `上传`：调用 `/matrix/rooms/{room_id}/files`

### 右侧：智能体与审计
- `授权`：调用 `/policy/grants`
- `撤权`：调用 `/policy/revoke`
- `摘要`：调用 `/agent/summarize`
- `摘要并发回房间`：调用 `/agent/summarize-and-send`
- `查询审计`：调用 `/audit/events`
- `验证审计链`：调用 `/audit/verify`
- `一键演示`：自动串联完整 MVP 流程

## 3. 快速上手（5分钟）
1. 启动服务：`docker compose up -d --build`
2. 打开页面：`http://localhost:8080/web/`
3. 左上填写用户名/密码，点击 `注册` 或 `登录`
4. 点击 `创建房间`，在中间输入消息并点击 `发送`
5. 点击 `同步消息`，确认聊天区出现气泡消息
6. 右侧执行 `授权 -> 摘要并发回房间 -> 撤权 -> 查询审计 -> 验证审计链`

## 4. 一键演示做了什么
点击 `一键演示` 后，页面会自动执行：
1. 注册或登录
2. 创建房间
3. 发送多条测试消息
4. 同步消息
5. 创建 Agent 授权
6. 调用总结并把摘要消息发回房间
7. 撤销授权
8. 再次调用总结并检查 403 拒绝
9. 校验审计链 `verified=true`

## 5. 常见问题
- `No active session`：先登录再操作。
- `403` 出现在总结接口：如果已撤权，这是预期行为。
- 聊天区没消息：先确认房间 ID 是否正确，再点击 `同步消息`。
- 审计验证失败：先执行一次完整流程再验证，确认 `actor_id` 使用了正确的 Agent ID。

---

## English Quick Notes
- This web page is a WeChat-like test console for Matrix + Agent + Audit.
- Use `ZH/EN` buttons in the top-right corner to switch language.
- Recommended flow:
  1. Register/Login
  2. Create room
  3. Send messages
  4. Sync
  5. Grant
  6. Summarize + Send
  7. Revoke
  8. Verify audit chain
- `Run Demo` automates the whole flow and checks deny-after-revoke + audit verification.
