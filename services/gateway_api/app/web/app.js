const SESSION_KEY = "prism_web_session_v1";

const state = {
  session: null,
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
  messageRows: document.getElementById("messageRows"),
  agentId: document.getElementById("agentId"),
  purpose: document.getElementById("purpose"),
  rateLimit: document.getElementById("rateLimit"),
  revokeGrantId: document.getElementById("revokeGrantId"),
  grantBtn: document.getElementById("grantBtn"),
  listGrantBtn: document.getElementById("listGrantBtn"),
  revokeBtn: document.getElementById("revokeBtn"),
  summarizeBtn: document.getElementById("summarizeBtn"),
  agentOutput: document.getElementById("agentOutput"),
  auditActorId: document.getElementById("auditActorId"),
  auditActionType: document.getElementById("auditActionType"),
  auditQueryBtn: document.getElementById("auditQueryBtn"),
  auditVerifyBtn: document.getElementById("auditVerifyBtn"),
  auditOutput: document.getElementById("auditOutput"),
};

function init() {
  const saved = loadSession();
  if (saved) {
    state.session = saved;
    el.homeserverUrl.value = saved.homeserver;
  }

  if (!el.gatewayUrl.value) {
    el.gatewayUrl.value = `${window.location.origin}/api/v1`;
  }

  bindEvents();
  renderSessionStatus();
}

function bindEvents() {
  el.registerBtn.addEventListener("click", () => handleRegister().catch(handleUiError));
  el.loginBtn.addEventListener("click", () => handleLogin().catch(handleUiError));
  el.logoutBtn.addEventListener("click", () => handleLogout());
  el.statusBtn.addEventListener("click", () => renderSessionStatus());

  el.createRoomBtn.addEventListener("click", () => handleCreateRoom().catch(handleUiError));
  el.sendBtn.addEventListener("click", () => handleSend().catch(handleUiError));
  el.uploadBtn.addEventListener("click", () => handleUploadFile().catch(handleUiError));
  el.syncBtn.addEventListener("click", () => handleSync().catch(handleUiError));

  el.grantBtn.addEventListener("click", () => handleGrant().catch(handleUiError));
  el.listGrantBtn.addEventListener("click", () => handleListGrants().catch(handleUiError));
  el.revokeBtn.addEventListener("click", () => handleRevoke().catch(handleUiError));
  el.summarizeBtn.addEventListener("click", () => handleSummarize().catch(handleUiError));

  el.auditQueryBtn.addEventListener("click", () => handleAuditQuery().catch(handleUiError));
  el.auditVerifyBtn.addEventListener("click", () => handleAuditVerify().catch(handleUiError));
}

function requireSession() {
  if (!state.session) {
    throw new Error("No active session. Please login first.");
  }
  return state.session;
}

function normalizeUsername(raw) {
  const value = raw.trim();
  if (!value) {
    return "";
  }

  if (value.startsWith("@")) {
    const tail = value.slice(1);
    const colonIdx = tail.indexOf(":");
    return colonIdx >= 0 ? tail.slice(0, colonIdx) : tail;
  }

  return value;
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

function mask(secret) {
  if (!secret) {
    return "";
  }
  if (secret.length <= 6) {
    return "*".repeat(secret.length);
  }
  return `${"*".repeat(secret.length - 6)}${secret.slice(-6)}`;
}

function writeJson(target, payload) {
  target.textContent = JSON.stringify(payload, null, 2);
}

function renderSessionStatus() {
  if (!state.session) {
    writeJson(el.sessionStatus, {
      status: "logged_out",
      hint: "Use Register or Login to start a Matrix session.",
    });
    return;
  }

  writeJson(el.sessionStatus, {
    status: "logged_in",
    user_id: state.session.userId,
    device_id: state.session.deviceId,
    homeserver: state.session.homeserver,
    access_token: mask(state.session.accessToken),
    next_batch: state.session.nextBatch || null,
    known_rooms: state.roomSet.size,
  });
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
  const roomIds = Array.from(state.roomSet.values()).sort();
  for (const roomId of roomIds) {
    const button = document.createElement("button");
    button.className = `pill${el.roomId.value.trim() === roomId ? " active" : ""}`;
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
  el.messageRows.innerHTML = "";
  const activeRoomId = el.roomId.value.trim();
  const rows = [];

  if (activeRoomId) {
    for (const entry of roomEventList(activeRoomId)) {
      rows.push(entry);
    }
  } else {
    for (const roomId of state.roomSet.values()) {
      for (const entry of roomEventList(roomId)) {
        rows.push(entry);
      }
    }
    rows.sort((a, b) => a.timestampMs - b.timestampMs);
  }

  for (const row of rows.slice(-200)) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(row.roomId)}</td>
      <td>${escapeHtml(row.sender)}</td>
      <td>${escapeHtml(row.body)}</td>
      <td>${escapeHtml(row.timestamp)}</td>`;
    el.messageRows.appendChild(tr);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function requestJson(url, options = {}) {
  const resp = await fetch(url, options);
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_err) {
    data = { raw: text };
  }

  if (!resp.ok) {
    const detail = data?.error || data?.detail || JSON.stringify(data);
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`);
  }
  return data;
}

async function gatewayRequest(path, options = {}) {
  const base = el.gatewayUrl.value.trim().replace(/\/+$/, "");
  if (!base) {
    throw new Error("Gateway URL is required.");
  }
  const headers = { "content-type": "application/json" };
  if (options.auth !== false) {
    const session = requireSession();
    headers.authorization = `Bearer ${session.accessToken}`;
  }
  return requestJson(`${base}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
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

  const resp = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { authorization: `Bearer ${session.accessToken}` },
    body: formData,
  });

  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_err) {
    data = { raw: text };
  }

  if (!resp.ok) {
    const detail = data?.error || data?.detail || JSON.stringify(data);
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`);
  }
  return data;
}

async function handleRegister() {
  const username = normalizeUsername(el.username.value);
  const password = el.password.value;
  if (!username || !password) {
    throw new Error("Username and password are required.");
  }

  const payload = await gatewayRequest("/matrix/register", {
    method: "POST",
    auth: false,
    body: {
      username,
      password,
    },
  });

  state.session = {
    homeserver: el.homeserverUrl.value.trim(),
    userId: payload.user_id,
    deviceId: payload.device_id,
    accessToken: payload.access_token,
    nextBatch: null,
  };
  saveSession(state.session);
  renderSessionStatus();
}

async function handleLogin() {
  const username = normalizeUsername(el.username.value);
  const password = el.password.value;
  if (!username || !password) {
    throw new Error("Username and password are required.");
  }

  const payload = await gatewayRequest("/matrix/login", {
    method: "POST",
    auth: false,
    body: {
      username,
      password,
    },
  });

  state.session = {
    homeserver: el.homeserverUrl.value.trim(),
    userId: payload.user_id,
    deviceId: payload.device_id,
    accessToken: payload.access_token,
    nextBatch: null,
  };
  saveSession(state.session);
  renderSessionStatus();
}

function handleLogout() {
  clearSession();
  state.session = null;
  state.messagesByRoom.clear();
  state.roomSet.clear();
  renderRoomPills();
  renderMessages();
  renderSessionStatus();
}

async function handleCreateRoom() {
  requireSession();
  const invite = el.inviteUserId.value.trim();
  const body = {
    preset: "private_chat",
    name: `prism-web-${Date.now()}`,
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
  renderSessionStatus();
}

async function handleSend() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const message = el.messageBody.value.trim();
  if (!roomId || !message) {
    throw new Error("Room ID and message are required.");
  }

  await gatewayRequest(`/matrix/rooms/${encodeURIComponent(roomId)}/messages`, {
    method: "POST",
    body: { body: message },
  });
  state.roomSet.add(roomId);
  el.messageBody.value = "";
  renderRoomPills();
}

async function handleUploadFile() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const file = el.fileInput.files?.[0];

  if (!roomId) {
    throw new Error("Room ID is required.");
  }
  if (!file) {
    throw new Error("Please choose a file first.");
  }

  const payload = await gatewayUpload(`/matrix/rooms/${encodeURIComponent(roomId)}/files`, file);
  writeJson(el.sessionStatus, {
    status: "file_uploaded",
    room_id: payload.room_id,
    event_id: payload.event_id,
    filename: payload.filename,
    size_bytes: payload.size_bytes,
  });
}

function parseTimestamp(originServerTs) {
  if (typeof originServerTs !== "number") {
    return { iso: "-", ms: 0 };
  }
  const date = new Date(originServerTs);
  return {
    iso: date.toISOString(),
    ms: date.getTime(),
  };
}

function ingestSync(syncPayload) {
  const joined = syncPayload?.rooms?.join || {};
  for (const [roomId, roomData] of Object.entries(joined)) {
    state.roomSet.add(roomId);
    const timeline = roomData?.timeline?.events || [];
    let roomMap = state.messagesByRoom.get(roomId);
    if (!roomMap) {
      roomMap = new Map();
      state.messagesByRoom.set(roomId, roomMap);
    }

    for (const event of timeline) {
      if (event?.type !== "m.room.message") {
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

async function handleSync() {
  const session = requireSession();
  let path = "/_matrix/client/v3/sync?timeout=3000";
  if (session.nextBatch) {
    path += `&since=${encodeURIComponent(session.nextBatch)}`;
  }

  const payload = await gatewayRequest(`/matrix${path.replace("/_matrix/client/v3", "")}`, {
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

async function handleGrant() {
  const session = requireSession();
  const agentId = el.agentId.value.trim();
  const purpose = el.purpose.value.trim();
  const rateLimit = Number(el.rateLimit.value || "60");
  if (!agentId || !purpose) {
    throw new Error("Agent ID and purpose are required.");
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
  const payload = await gatewayRequest(`/policy/grants${query}`);
  writeJson(el.agentOutput, payload);
}

async function handleRevoke() {
  const session = requireSession();
  const grantId = el.revokeGrantId.value.trim();
  if (!grantId) {
    throw new Error("Grant ID is required.");
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
  const rows = roomEventList(roomId);
  return rows.map((x) => x.body).filter((x) => x.trim().length > 0);
}

async function handleSummarize() {
  requireSession();
  const roomId = el.roomId.value.trim();
  const agentId = el.agentId.value.trim();
  const purpose = el.purpose.value.trim();

  if (!roomId || !agentId || !purpose) {
    throw new Error("Room ID, Agent ID and purpose are required.");
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

async function handleAuditQuery() {
  const actorId = el.auditActorId.value.trim();
  const actionType = el.auditActionType.value.trim();
  const params = new URLSearchParams();
  params.set("limit", "50");
  if (actorId) {
    params.set("actor_id", actorId);
  }
  if (actionType) {
    params.set("action_type", actionType);
  }
  const payload = await gatewayRequest(`/audit/events?${params.toString()}`, { auth: false });
  writeJson(el.auditOutput, payload);
}

async function handleAuditVerify() {
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
  const payload = await gatewayRequest(`/audit/verify?${params.toString()}`, { auth: false });
  writeJson(el.auditOutput, payload);
}

function handleUiError(error) {
  const message = error instanceof Error ? error.message : String(error);
  writeJson(el.sessionStatus, { status: "error", message });
  console.error(error);
}

init();
