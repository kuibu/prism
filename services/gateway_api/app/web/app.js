const SESSION_KEY = "prism_web_session_v3";
const LANGUAGE_KEY = "prism_web_language_v1";

const I18N = {
  zh: {
    app_title: "仿微信联调控制台",
    account_title: "账号登录",
    rooms_title: "会话房间",
    chat_title: "聊天窗口",
    agent_title: "智能体与授权",
    audit_title: "审计与验证",
    label_homeserver: "Homeserver 地址",
    label_gateway: "Gateway API 地址",
    label_username: "用户名（localpart）",
    label_password: "密码",
    label_invite: "邀请用户（可选）",
    label_room_id: "当前房间 ID",
    label_message: "消息内容",
    label_upload: "文件",
    label_agent_id: "Agent ID",
    label_purpose: "用途 Purpose",
    label_rate_limit: "每分钟限流",
    label_grant_id: "授权 ID",
    label_audit_actor: "Actor ID",
    label_audit_action: "动作类型",
    placeholder_username: "例如 grandma_demo",
    placeholder_password: "例如 Passw0rd!",
    placeholder_invite: "@bob:localhost",
    placeholder_room: "!room:localhost",
    placeholder_message: "在这里输入消息，点击发送",
    placeholder_grant: "grant_xxx",
    placeholder_audit_actor: "agent.summary.web",
    placeholder_audit_action: "agent_summarize",
    btn_register: "注册",
    btn_login: "登录",
    btn_logout: "退出",
    btn_refresh: "刷新状态",
    btn_create_room: "创建房间",
    btn_sync: "同步消息",
    btn_send: "发送",
    btn_upload: "上传文件",
    btn_grant: "授权",
    btn_list_grants: "查看授权",
    btn_revoke: "撤权",
    btn_summarize: "摘要",
    btn_summarize_send: "摘要并发回房间",
    btn_audit_query: "查询审计",
    btn_audit_verify: "验证审计链",
    btn_run_demo: "一键演示",
    status_logged_out: "未登录。请先注册或登录。",
    status_logged_in: "已登录",
    status_file_uploaded: "文件发送成功",
    error_no_session: "当前未登录，请先登录。",
    error_need_credentials: "请输入用户名和密码。",
    error_need_room_message: "请先填写房间 ID 和消息内容。",
    error_need_room: "请先填写房间 ID。",
    error_need_file: "请先选择文件。",
    error_need_agent_purpose: "请填写 Agent ID 和 Purpose。",
    error_need_grant: "请填写授权 ID。",
    error_demo_credentials: "演示需要先填写用户名和密码。",
    error_demo_deny_expected: "撤权后应被拒绝，但接口返回了允许。",
    error_audit_verify_failed: "审计链校验未通过。",
    demo_start: "开始执行仿微信一键演示...",
    demo_done: "演示完成：消息、授权、撤权、拒绝验证、审计校验全部通过。",
    demo_messages: [
      "今天我们先试一下仿微信聊天",
      "请总结今天讨论要点",
      "撤权后应该拒绝智能体读取消息",
    ],
    bubble_you: "我",
  },
  en: {
    app_title: "WeChat-Like Integration Console",
    account_title: "Account",
    rooms_title: "Rooms",
    chat_title: "Conversation",
    agent_title: "Agent + Policy",
    audit_title: "Audit + Verify",
    label_homeserver: "Homeserver URL",
    label_gateway: "Gateway API URL",
    label_username: "Username (localpart)",
    label_password: "Password",
    label_invite: "Invite User (optional)",
    label_room_id: "Active Room ID",
    label_message: "Message",
    label_upload: "File",
    label_agent_id: "Agent ID",
    label_purpose: "Purpose",
    label_rate_limit: "Rate Limit / Minute",
    label_grant_id: "Grant ID",
    label_audit_actor: "Actor ID",
    label_audit_action: "Action Type",
    placeholder_username: "e.g. grandma_demo",
    placeholder_password: "e.g. Passw0rd!",
    placeholder_invite: "@bob:localhost",
    placeholder_room: "!room:localhost",
    placeholder_message: "Type a message here and click send",
    placeholder_grant: "grant_xxx",
    placeholder_audit_actor: "agent.summary.web",
    placeholder_audit_action: "agent_summarize",
    btn_register: "Register",
    btn_login: "Login",
    btn_logout: "Logout",
    btn_refresh: "Refresh",
    btn_create_room: "Create Room",
    btn_sync: "Sync",
    btn_send: "Send",
    btn_upload: "Upload",
    btn_grant: "Grant",
    btn_list_grants: "List Grants",
    btn_revoke: "Revoke",
    btn_summarize: "Summarize",
    btn_summarize_send: "Summarize + Send",
    btn_audit_query: "Query Audit",
    btn_audit_verify: "Verify Chain",
    btn_run_demo: "Run Demo",
    status_logged_out: "No active session. Please register or login.",
    status_logged_in: "Logged in",
    status_file_uploaded: "File sent successfully",
    error_no_session: "No active session. Please login first.",
    error_need_credentials: "Username and password are required.",
    error_need_room_message: "Room ID and message are required.",
    error_need_room: "Room ID is required.",
    error_need_file: "Please choose a file first.",
    error_need_agent_purpose: "Agent ID and purpose are required.",
    error_need_grant: "Grant ID is required.",
    error_demo_credentials: "Demo requires username and password first.",
    error_demo_deny_expected: "Expected deny after revoke, but request was allowed.",
    error_audit_verify_failed: "Audit chain verification failed.",
    demo_start: "Running WeChat-like demo flow...",
    demo_done:
      "Demo complete: messaging, grant, revoke, deny check and audit verification all passed.",
    demo_messages: [
      "Let's test the WeChat-like chat flow",
      "Please summarize today's conversation",
      "After revoke, agent access should be denied",
    ],
    bubble_you: "Me",
  },
};

const state = {
  session: null,
  language: "zh",
  messagesByRoom: new Map(),
  roomSet: new Set(),
};

const el = {
  homeserverUrl: document.getElementById("homeserverUrl"),
  gatewayUrl: document.getElementById("gatewayUrl"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  registerBtn: document.getElementById("registerBtn"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  statusBtn: document.getElementById("statusBtn"),
  sessionStatus: document.getElementById("sessionStatus"),
  inviteUserId: document.getElementById("inviteUserId"),
  roomId: document.getElementById("roomId"),
  createRoomBtn: document.getElementById("createRoomBtn"),
  syncBtn: document.getElementById("syncBtn"),
  messageBody: document.getElementById("messageBody"),
  sendBtn: document.getElementById("sendBtn"),
  fileInput: document.getElementById("fileInput"),
  uploadBtn: document.getElementById("uploadBtn"),
  roomPills: document.getElementById("roomPills"),
  messageFeed: document.getElementById("messageFeed"),
  activeRoomDisplay: document.getElementById("activeRoomDisplay"),
  agentId: document.getElementById("agentId"),
  purpose: document.getElementById("purpose"),
  rateLimit: document.getElementById("rateLimit"),
  revokeGrantId: document.getElementById("revokeGrantId"),
  grantBtn: document.getElementById("grantBtn"),
  listGrantBtn: document.getElementById("listGrantBtn"),
  revokeBtn: document.getElementById("revokeBtn"),
  summarizeBtn: document.getElementById("summarizeBtn"),
  summarizeSendBtn: document.getElementById("summarizeSendBtn"),
  agentOutput: document.getElementById("agentOutput"),
  auditActorId: document.getElementById("auditActorId"),
  auditActionType: document.getElementById("auditActionType"),
  auditQueryBtn: document.getElementById("auditQueryBtn"),
  auditVerifyBtn: document.getElementById("auditVerifyBtn"),
  runDemoBtn: document.getElementById("runDemoBtn"),
  auditOutput: document.getElementById("auditOutput"),
  langZhBtn: document.getElementById("langZhBtn"),
  langEnBtn: document.getElementById("langEnBtn"),
};

function init() {
  const savedSession = loadSession();
  if (savedSession) {
    state.session = savedSession;
    el.homeserverUrl.value = savedSession.homeserver || el.homeserverUrl.value;
  }

  const savedLanguage = loadLanguage();
  if (savedLanguage) {
    state.language = savedLanguage;
  }

  if (!el.gatewayUrl.value.trim()) {
    el.gatewayUrl.value = `${window.location.origin}/api/v1`;
  }

  bindEvents();
  applyLanguage();
  renderSessionStatus();
  renderRoomPills();
  renderMessages();
}

function bindEvents() {
  el.registerBtn.addEventListener("click", () => handleRegister().catch(handleUiError));
  el.loginBtn.addEventListener("click", () => handleLogin().catch(handleUiError));
  el.logoutBtn.addEventListener("click", () => handleLogout());
  el.statusBtn.addEventListener("click", () => renderSessionStatus());

  el.createRoomBtn.addEventListener("click", () => handleCreateRoom().catch(handleUiError));
  el.syncBtn.addEventListener("click", () => handleSync().catch(handleUiError));
  el.sendBtn.addEventListener("click", () => handleSend().catch(handleUiError));
  el.uploadBtn.addEventListener("click", () => handleUploadFile().catch(handleUiError));

  el.grantBtn.addEventListener("click", () => handleGrant().catch(handleUiError));
  el.listGrantBtn.addEventListener("click", () => handleListGrants().catch(handleUiError));
  el.revokeBtn.addEventListener("click", () => handleRevoke().catch(handleUiError));
  el.summarizeBtn.addEventListener("click", () => handleSummarize().catch(handleUiError));
  el.summarizeSendBtn.addEventListener("click", () => handleSummarizeAndSend().catch(handleUiError));

  el.auditQueryBtn.addEventListener("click", () => handleAuditQuery().catch(handleUiError));
  el.auditVerifyBtn.addEventListener("click", () => handleAuditVerify().catch(handleUiError));
  el.runDemoBtn.addEventListener("click", () => runDemo().catch(handleUiError));

  el.langZhBtn.addEventListener("click", () => setLanguage("zh"));
  el.langEnBtn.addEventListener("click", () => setLanguage("en"));
}

function setLanguage(language) {
  if (language !== "zh" && language !== "en") {
    return;
  }
  state.language = language;
  saveLanguage(language);
  applyLanguage();
  renderSessionStatus();
  renderMessages();
}

function applyLanguage() {
  document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
  el.langZhBtn.classList.toggle("active", state.language === "zh");
  el.langEnBtn.classList.toggle("active", state.language === "en");

  for (const node of document.querySelectorAll("[data-i18n]")) {
    const key = node.getAttribute("data-i18n");
    if (!key) {
      continue;
    }
    node.textContent = t(key);
  }

  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) {
    const key = node.getAttribute("data-i18n-placeholder");
    if (!key) {
      continue;
    }
    node.setAttribute("placeholder", t(key));
  }
}

function t(key) {
  const dict = I18N[state.language] || I18N.en;
  return dict[key] || I18N.en[key] || key;
}

function defaultDemoMessages() {
  const dict = I18N[state.language] || I18N.en;
  const messages = dict.demo_messages;
  if (Array.isArray(messages)) {
    return messages;
  }
  return I18N.en.demo_messages;
}

function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function loadSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    const payload = JSON.parse(raw);
    if (!payload || typeof payload !== "object") {
      return null;
    }
    return payload;
  } catch (_err) {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

function saveLanguage(language) {
  localStorage.setItem(LANGUAGE_KEY, language);
}

function loadLanguage() {
  const value = localStorage.getItem(LANGUAGE_KEY);
  if (value === "zh" || value === "en") {
    return value;
  }
  return null;
}

function requireSession() {
  if (!state.session) {
    throw new Error(t("error_no_session"));
  }
  return state.session;
}

function normalizeUsername(raw) {
  const value = raw.trim();
  if (!value) {
    return "";
  }
  if (!value.startsWith("@")) {
    return value;
  }
  const stripped = value.slice(1);
  const separator = stripped.indexOf(":");
  return separator >= 0 ? stripped.slice(0, separator) : stripped;
}

function mask(secret) {
  if (!secret) {
    return "";
  }
  if (secret.length <= 6) {
    return "*".repeat(secret.length);
  }
  return `${"*".repeat(secret.length - 6)}${secret.slice(-6)}`;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_err) {
    data = { raw: text };
  }
  if (!response.ok) {
    const detail = data?.error || data?.detail || JSON.stringify(data);
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return data;
}

async function gatewayRequest(path, options = {}) {
  const base = el.gatewayUrl.value.trim().replace(/\/+$/, "");
  if (!base) {
    throw new Error("Gateway URL is required.");
  }

  const headers = {};
  if (options.body !== undefined) {
    headers["content-type"] = "application/json";
  }

  if (options.auth !== false) {
    const session = requireSession();
    headers.authorization = `Bearer ${session.accessToken}`;
  }

  return requestJson(`${base}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
}

async function gatewayUpload(path, file) {
  const base = el.gatewayUrl.value.trim().replace(/\/+$/, "");
  if (!base) {
    throw new Error("Gateway URL is required.");
  }
  const session = requireSession();

  const formData = new FormData();
  formData.append("file", file, file.name || "upload.bin");

  const response = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { authorization: `Bearer ${session.accessToken}` },
    body: formData,
  });

  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_err) {
    data = { raw: text };
  }

  if (!response.ok) {
    const detail = data?.error || data?.detail || JSON.stringify(data);
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return data;
}

function writeJson(target, payload) {
  target.textContent = JSON.stringify(payload, null, 2);
}

function renderSessionStatus() {
  if (!state.session) {
    writeJson(el.sessionStatus, { status: "logged_out", hint: t("status_logged_out") });
    return;
  }

  writeJson(el.sessionStatus, {
    status: t("status_logged_in"),
    user_id: state.session.userId,
    device_id: state.session.deviceId,
    homeserver: state.session.homeserver,
    access_token: mask(state.session.accessToken),
    next_batch: state.session.nextBatch || null,
    room_count: state.roomSet.size,
  });
}

function parseTimestamp(originServerTs) {
  if (typeof originServerTs !== "number") {
    return { iso: "-", ms: 0 };
  }
  const date = new Date(originServerTs);
  return { iso: date.toISOString(), ms: date.getTime() };
}

function ingestSync(syncPayload) {
  const joinedRooms = syncPayload?.rooms?.join || {};
  for (const [roomId, roomData] of Object.entries(joinedRooms)) {
    state.roomSet.add(roomId);

    const timelineEvents = roomData?.timeline?.events || [];
    let roomMap = state.messagesByRoom.get(roomId);
    if (!roomMap) {
      roomMap = new Map();
      state.messagesByRoom.set(roomId, roomMap);
    }

    for (const event of timelineEvents) {
      if (!event || event.type !== "m.room.message") {
        continue;
      }
      const eventId = event.event_id;
      if (!eventId || roomMap.has(eventId)) {
        continue;
      }
      const body = event?.content?.body ?? "";
      const sender = event?.sender ?? "unknown";
      const timestamp = parseTimestamp(event?.origin_server_ts);
      roomMap.set(eventId, {
        eventId,
        roomId,
        sender,
        body,
        timestamp: timestamp.iso,
        timestampMs: timestamp.ms,
      });
    }
  }
}

function roomEventList(roomId) {
  const map = state.messagesByRoom.get(roomId);
  if (!map) {
    return [];
  }
  return Array.from(map.values()).sort((a, b) => a.timestampMs - b.timestampMs);
}

function renderRoomPills() {
  el.roomPills.innerHTML = "";
  const activeRoomId = el.roomId.value.trim();
  const roomIds = Array.from(state.roomSet.values()).sort();
  for (const roomId of roomIds) {
    const button = document.createElement("button");
    button.className = `room-pill${roomId === activeRoomId ? " active" : ""}`;
    button.textContent = roomId;
    button.addEventListener("click", () => {
      el.roomId.value = roomId;
      renderRoomPills();
      renderMessages();
    });
    el.roomPills.appendChild(button);
  }
}

function renderMessages() {
  const activeRoomId = el.roomId.value.trim();
  el.activeRoomDisplay.textContent = activeRoomId || "-";
  el.messageFeed.innerHTML = "";

  if (!activeRoomId) {
    return;
  }

  const rows = roomEventList(activeRoomId);
  for (const row of rows.slice(-300)) {
    const isSelf = Boolean(state.session) && row.sender === state.session.userId;

    const wrapper = document.createElement("div");
    wrapper.className = `bubble-row${isSelf ? " self" : ""}`;

    const bubble = document.createElement("article");
    bubble.className = `bubble ${isSelf ? "self" : "other"}`;

    const meta = document.createElement("div");
    meta.className = "bubble-meta";
    meta.textContent = `${isSelf ? t("bubble_you") : row.sender} · ${row.timestamp}`;

    const body = document.createElement("div");
    body.className = "bubble-body";
    body.textContent = row.body;

    bubble.appendChild(meta);
    bubble.appendChild(body);
    wrapper.appendChild(bubble);
    el.messageFeed.appendChild(wrapper);
  }

  el.messageFeed.scrollTop = el.messageFeed.scrollHeight;
}

async function registerOrLogin() {
  const username = normalizeUsername(el.username.value);
  const password = el.password.value;
  if (!username || !password) {
    throw new Error(t("error_need_credentials"));
  }

  try {
    const payload = await gatewayRequest("/matrix/register", {
      method: "POST",
      auth: false,
      body: { username, password },
    });
    return { mode: "register", payload };
  } catch (_registerError) {
    const payload = await gatewayRequest("/matrix/login", {
      method: "POST",
      auth: false,
      body: { username, password },
    });
    return { mode: "login", payload };
  }
}

function applyAuthPayload(payload) {
  state.session = {
    homeserver: el.homeserverUrl.value.trim(),
    userId: payload.user_id,
    deviceId: payload.device_id || null,
    accessToken: payload.access_token,
    nextBatch: null,
  };
  saveSession(state.session);
  renderSessionStatus();
}

async function handleRegister() {
  const username = normalizeUsername(el.username.value);
  const password = el.password.value;
  if (!username || !password) {
    throw new Error(t("error_need_credentials"));
  }
  const payload = await gatewayRequest("/matrix/register", {
    method: "POST",
    auth: false,
    body: { username, password },
  });
  applyAuthPayload(payload);
}

async function handleLogin() {
  const username = normalizeUsername(el.username.value);
  const password = el.password.value;
  if (!username || !password) {
    throw new Error(t("error_need_credentials"));
  }
  const payload = await gatewayRequest("/matrix/login", {
    method: "POST",
    auth: false,
    body: { username, password },
  });
  applyAuthPayload(payload);
}

function handleLogout() {
  clearSession();
  state.session = null;
  state.messagesByRoom.clear();
  state.roomSet.clear();
  el.roomId.value = "";
  renderSessionStatus();
  renderRoomPills();
  renderMessages();
  writeJson(el.agentOutput, { status: "logged_out" });
  writeJson(el.auditOutput, { status: "logged_out" });
}

async function handleCreateRoom() {
  requireSession();
  const invite = el.inviteUserId.value.trim();
  const body = {
    preset: "private_chat",
    name: `prism-wx-${Date.now()}`,
  };
  if (invite) {
    body.invite = [invite];
  }
  const payload = await gatewayRequest("/matrix/rooms", {
    method: "POST",
    body,
  });
  const roomId = payload.room_id;
  el.roomId.value = roomId;
  state.roomSet.add(roomId);
  renderRoomPills();
  renderMessages();
  renderSessionStatus();
}

async function handleSync() {
  const session = requireSession();
  const params = new URLSearchParams();
  params.set("timeout_ms", "3000");
  if (session.nextBatch) {
    params.set("since", session.nextBatch);
  }

  const payload = await gatewayRequest(`/matrix/sync?${params.toString()}`, {
    method: "GET",
  });

  session.nextBatch = payload.next_batch || session.nextBatch;
  saveSession(session);
  ingestSync(payload);

  if (!el.roomId.value.trim()) {
    const firstRoom = Array.from(state.roomSet.values()).sort()[0];
    if (firstRoom) {
      el.roomId.value = firstRoom;
    }
  }

  renderRoomPills();
  renderMessages();
  renderSessionStatus();
}

async function handleSend() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const message = el.messageBody.value.trim();
  if (!roomId || !message) {
    throw new Error(t("error_need_room_message"));
  }

  await gatewayRequest(`/matrix/rooms/${encodeURIComponent(roomId)}/messages`, {
    method: "POST",
    body: { body: message },
  });
  el.messageBody.value = "";
  state.roomSet.add(roomId);
  renderRoomPills();
}

async function handleUploadFile() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const file = el.fileInput.files?.[0];
  if (!roomId) {
    throw new Error(t("error_need_room"));
  }
  if (!file) {
    throw new Error(t("error_need_file"));
  }

  const payload = await gatewayUpload(`/matrix/rooms/${encodeURIComponent(roomId)}/files`, file);
  writeJson(el.sessionStatus, {
    status: t("status_file_uploaded"),
    room_id: payload.room_id,
    event_id: payload.event_id,
    filename: payload.filename,
    size_bytes: payload.size_bytes,
  });
}

async function handleGrant() {
  const session = requireSession();
  const agentId = el.agentId.value.trim();
  const purpose = el.purpose.value.trim();
  const rateLimit = Number(el.rateLimit.value || "60");
  if (!agentId || !purpose) {
    throw new Error(t("error_need_agent_purpose"));
  }

  const payload = await gatewayRequest("/policy/grants", {
    method: "POST",
    body: {
      user_id: session.userId,
      agent_id: agentId,
      data_category: "room_messages",
      purpose,
      rate_limit_per_minute: Math.max(1, Math.floor(rateLimit)),
    },
  });
  if (payload?.grant_id) {
    el.revokeGrantId.value = payload.grant_id;
  }
  writeJson(el.agentOutput, payload);
}

async function handleListGrants() {
  const session = requireSession();
  const query = `?user_id=${encodeURIComponent(session.userId)}&include_revoked=true`;
  const payload = await gatewayRequest(`/policy/grants${query}`, { method: "GET" });
  writeJson(el.agentOutput, payload);
}

async function handleRevoke() {
  const session = requireSession();
  const grantId = el.revokeGrantId.value.trim();
  if (!grantId) {
    throw new Error(t("error_need_grant"));
  }
  const payload = await gatewayRequest("/policy/revoke", {
    method: "POST",
    body: {
      user_id: session.userId,
      grant_id: grantId,
      reason: "web_client_revoke",
    },
  });
  writeJson(el.agentOutput, payload);
}

function currentRoomMessages(roomId) {
  return roomEventList(roomId)
    .map((item) => item.body)
    .filter((body) => body.trim().length > 0);
}

async function handleSummarize() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const agentId = el.agentId.value.trim();
  const purpose = el.purpose.value.trim();
  if (!roomId) {
    throw new Error(t("error_need_room"));
  }
  if (!agentId || !purpose) {
    throw new Error(t("error_need_agent_purpose"));
  }

  const knownMessageCount = currentRoomMessages(roomId).length;
  const payload = await gatewayRequest("/agent/summarize", {
    method: "POST",
    body: {
      agent_id: agentId,
      room_id: roomId,
      purpose,
      recent_message_limit: 50,
      max_items: 10,
    },
  });
  payload.local_known_message_count = knownMessageCount;
  writeJson(el.agentOutput, payload);
}

async function handleSummarizeAndSend() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const agentId = el.agentId.value.trim();
  const purpose = el.purpose.value.trim();
  if (!roomId) {
    throw new Error(t("error_need_room"));
  }
  if (!agentId || !purpose) {
    throw new Error(t("error_need_agent_purpose"));
  }

  const payload = await gatewayRequest("/agent/summarize-and-send", {
    method: "POST",
    body: {
      agent_id: agentId,
      room_id: roomId,
      purpose,
      recent_message_limit: 50,
      max_items: 10,
    },
  });
  writeJson(el.agentOutput, payload);
}

async function handleAuditQuery() {
  requireSession();
  const actorId = el.auditActorId.value.trim();
  const actionType = el.auditActionType.value.trim();

  const params = new URLSearchParams();
  params.set("limit", "60");
  if (actorId) {
    params.set("actor_id", actorId);
  }
  if (actionType) {
    params.set("action_type", actionType);
  }
  const payload = await gatewayRequest(`/audit/events?${params.toString()}`, { method: "GET" });
  writeJson(el.auditOutput, payload);
}

async function handleAuditVerify() {
  requireSession();
  const actorId = el.auditActorId.value.trim();
  const actionType = el.auditActionType.value.trim();

  const params = new URLSearchParams();
  params.set("limit", "500");
  if (actorId) {
    params.set("actor_id", actorId);
  }
  if (actionType) {
    params.set("action_type", actionType);
  }

  const payload = await gatewayRequest(`/audit/verify?${params.toString()}`, {
    method: "GET",
  });
  writeJson(el.auditOutput, payload);
}

async function runDemo() {
  const username = normalizeUsername(el.username.value);
  const password = el.password.value;
  if (!username || !password) {
    throw new Error(t("error_demo_credentials"));
  }

  writeJson(el.auditOutput, { status: t("demo_start") });

  const authResult = await registerOrLogin();
  applyAuthPayload(authResult.payload);

  const roomPayload = await gatewayRequest("/matrix/rooms", {
    method: "POST",
    body: {
      preset: "private_chat",
      name: `prism-demo-${Date.now()}`,
    },
  });
  const roomId = roomPayload.room_id;
  el.roomId.value = roomId;
  state.roomSet.add(roomId);

  for (const message of defaultDemoMessages()) {
    await gatewayRequest(`/matrix/rooms/${encodeURIComponent(roomId)}/messages`, {
      method: "POST",
      body: { body: message },
    });
  }

  await handleSync();

  const session = requireSession();
  const agentId = el.agentId.value.trim();
  const purpose = el.purpose.value.trim();
  const rateLimit = Number(el.rateLimit.value || "60");

  const grantPayload = await gatewayRequest("/policy/grants", {
    method: "POST",
    body: {
      user_id: session.userId,
      agent_id: agentId,
      data_category: "room_messages",
      purpose,
      rate_limit_per_minute: Math.max(1, Math.floor(rateLimit)),
    },
  });
  const grantId = grantPayload.grant_id;
  el.revokeGrantId.value = grantId;
  el.auditActorId.value = agentId;

  const summaryPayload = await gatewayRequest("/agent/summarize-and-send", {
    method: "POST",
    body: {
      agent_id: agentId,
      room_id: roomId,
      purpose,
      recent_message_limit: 50,
      max_items: 10,
    },
  });

  await handleSync();

  await gatewayRequest("/policy/revoke", {
    method: "POST",
    body: {
      user_id: session.userId,
      grant_id: grantId,
      reason: "web_demo_revoke",
    },
  });

  let denyReceived = false;
  try {
    await gatewayRequest("/agent/summarize", {
      method: "POST",
      body: {
        agent_id: agentId,
        room_id: roomId,
        purpose,
        recent_message_limit: 50,
        max_items: 10,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes("403")) {
      denyReceived = true;
    } else {
      throw error;
    }
  }
  if (!denyReceived) {
    throw new Error(t("error_demo_deny_expected"));
  }

  const verifyPayload = await gatewayRequest(
    `/audit/verify?actor_id=${encodeURIComponent(agentId)}&limit=500`,
    {
      method: "GET",
    }
  );
  if (verifyPayload.verified !== true) {
    throw new Error(t("error_audit_verify_failed"));
  }

  writeJson(el.agentOutput, {
    auth_mode: authResult.mode,
    room_id: roomId,
    grant_id: grantId,
    summary_event: summaryPayload.event_id || null,
    audit_verified: verifyPayload.verified,
    audit_checked_events: verifyPayload.checked_events,
  });
  writeJson(el.auditOutput, { status: t("demo_done"), verify: verifyPayload });
}

function handleUiError(error) {
  const message = error instanceof Error ? error.message : String(error);
  writeJson(el.sessionStatus, { status: "error", message });
  console.error(error);
}

init();
