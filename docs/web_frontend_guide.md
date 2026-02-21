# Prism Web Frontend Guide (Telegram-Like Vue App)

## 1. 页面定位
- 这是一个 **Telegram 风格 + Vue 单页前端**，用于快速验证 Matrix 聊天、Agent 授权/撤权、不可变审计链。
- 页面入口：`http://localhost:8080/web/`
- 顶部有语言按钮：`中文` / `EN`。

## 2. 页面分区说明

### 左侧
- 会话状态卡片（支持打开第二个客户端窗口）
- Tab 菜单（每个页面一个 Tab）
- 房间列表（可点击切换当前聊天房间）

### 右侧主区域（Tab 页面）
- `注册/登录`：账号与会话页面
- `创建房间`：创建、加入、同步房间
- `邀请好友`：调用邀请接口邀请指定用户进房间
- `创建 Agent`：创建本地 Agent 资料、授权、撤权、摘要调用
- `聊天页面`：Telegram 风格消息气泡、发消息、传文件
- `审计页面`：查询审计、验证链、运行一键演示

### 弹窗提示（Toast）
- 每个按钮操作都会弹出成功/失败/提示消息。
- 适合调试：看一眼就知道按钮是否执行成功。

## 3. 快速上手（5分钟）
1. 启动服务：`docker compose up -d --build`
2. 打开页面：`http://localhost:8080/web/`
3. 在 `注册/登录` Tab 里注册账号并登录
4. 切到 `创建房间` Tab，创建一个房间
5. 切到 `聊天页面` Tab，发消息并同步
6. 切到 `创建 Agent` Tab，执行授权、摘要、撤权
7. 切到 `审计页面` Tab，查询并验证审计链

## 4. 一键演示做了什么
点击 `审计页面` 里的 `一键双人联调演示` 后，页面会自动执行：
1. 注册或登录
2. 创建房间
3. 发送多条测试消息
4. 同步消息
5. 创建 Agent 授权
6. 调用总结并把摘要消息发回房间
7. 撤销授权
8. 再次调用总结并检查 403 拒绝
9. 校验审计链 `verified=true`

## 5. 双窗口双用户聊天测试
1. 在第一个窗口登录用户 A。
2. 点击“打开第二个客户端窗口”。
3. 在第二个窗口登录用户 B。
4. 用户 A 在“创建房间”中创建房间并邀请用户 B（可在创建时邀请，或在“邀请好友”页邀请）。
5. 用户 B 在“创建房间”页输入房间 ID 并点击“加入房间”。
6. 两边都切到“聊天页面”，发消息并点击“同步消息”即可互相看到消息。

## 6. 常见问题
- `No active session`：先登录再操作。
- `403` 出现在总结接口：如果已撤权，这是预期行为。
- 聊天区没消息：先确认房间 ID 是否正确，再点击 `同步消息`。
- 审计验证失败：先执行一次完整流程再验证，确认 `actor_id` 使用了正确的 Agent ID。

---

## English Quick Notes
- This is a Telegram-like Vue frontend for Matrix + Agent + Audit integration.
- Every button action emits toast feedback (success/error/info).
- Tabs map to pages: Auth, Room, Invite, Agent, Chat, Audit.
- Use “Open Second Client Window” to login another user and run two-user chat tests.
