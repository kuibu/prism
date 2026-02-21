(() => {
  const I18N = {
    zh: {
      app_title: "仿 Telegram 多页面联调台",
      sidebar_account: "当前会话",
      sidebar_tabs: "功能页面",
      sidebar_rooms: "房间列表",
      tab_auth: "注册 / 登录",
      tab_room: "创建房间",
      tab_invite: "邀请好友",
      tab_agent: "创建 Agent",
      tab_chat: "聊天页面",
      tab_audit: "审计页面",
      status_logged_out: "未登录（可在另一个窗口登录另一个用户）。",
      btn_open_second: "打开第二个客户端窗口",
      label_homeserver: "Homeserver URL",
      label_gateway: "Gateway API URL",
      label_username: "用户名（localpart）",
      label_password: "密码",
      label_room_name: "新房间名称",
      label_invite_on_create: "创建时邀请（可选）",
      label_active_room: "当前房间 ID",
      label_join_room_id: "加入房间 ID",
      label_invite_user_id: "好友用户 ID",
      label_agent_id: "Agent ID",
      label_purpose: "用途 Purpose",
      label_rate_limit: "每分钟限流",
      label_grant_id: "授权 ID",
      label_message: "消息内容",
      label_actor_id: "Actor ID",
      label_action_type: "动作类型",
      placeholder_username: "例如 tg_user_a",
      placeholder_password: "至少8位，例如 Passw0rd!",
      placeholder_room_name: "例如 Team Chat",
      placeholder_invite: "@tg_user_b:localhost",
      placeholder_room_id: "!room:localhost",
      placeholder_agent_id: "agent.summary.demo",
      placeholder_purpose: "daily_summary",
      placeholder_grant: "grant_xxx",
      placeholder_message: "输入消息后点击发送",
      placeholder_actor: "agent.summary.demo",
      placeholder_action: "agent_summarize",
      btn_register: "注册",
      btn_login: "登录",
      btn_logout: "退出",
      btn_refresh: "刷新状态",
      btn_create_room: "创建房间",
      btn_join_room: "加入房间",
      btn_sync: "同步消息",
      btn_invite_user: "邀请好友",
      btn_create_agent: "创建 Agent 资料",
      btn_grant: "授权 Agent",
      btn_revoke: "撤销授权",
      btn_summarize: "摘要（仅返回）",
      btn_summarize_send: "摘要并发送到房间",
      btn_send: "发送消息",
      btn_upload: "上传文件",
      btn_query_audit: "查询审计",
      btn_verify_audit: "验证审计链",
      btn_run_demo: "一键双人联调演示",
      empty_chat: "暂无消息。先发送或同步一次。",
      self_name: "我",
      toast_success: "成功",
      toast_error: "失败",
      toast_info: "提示",
      info_open_second: "已打开新窗口。你可以在新窗口登录另一个用户。",
      info_profile_created: "Agent 资料已创建（本地），可继续授权。",
      info_language_changed: "语言已切换。",
      info_tab_switched: "已切换页面。",
      info_status_refreshed: "状态已刷新。",
      err_no_session: "当前未登录，请先注册或登录。",
      err_need_credentials: "请输入用户名和密码。",
      err_password_short: "密码至少 8 位。",
      err_need_room: "请先填写房间 ID。",
      err_need_room_message: "请先填写房间 ID 和消息内容。",
      err_need_invite: "请填写房间 ID 和好友用户 ID。",
      err_need_agent: "请填写 Agent ID 和 Purpose。",
      err_need_grant: "请填写授权 ID。",
      err_demo_need_creds: "先填写用户名和密码，再执行演示。",
      err_demo_deny_expected: "撤权后应返回 403 deny，但本次未拒绝。",
      err_demo_audit_verify: "审计链验证失败。",
      demo_start: "开始演示：注册/登录 -> 建房 -> 发消息 -> 授权 -> 摘要 -> 撤权 -> 验证。",
      demo_done: "演示完成：流程全部通过。",
      demo_messages: [
        "你好，这是第1条测试消息",
        "你好，这是第2条测试消息",
        "请帮我总结今天聊天重点",
      ],
    },
    en: {
      app_title: "Telegram-Like Multi-Page Test Console",
      sidebar_account: "Current Session",
      sidebar_tabs: "Pages",
      sidebar_rooms: "Rooms",
      tab_auth: "Register / Login",
      tab_room: "Create Room",
      tab_invite: "Invite Friend",
      tab_agent: "Create Agent",
      tab_chat: "Chat",
      tab_audit: "Audit",
      status_logged_out: "Logged out (you can login another user in a second window).",
      btn_open_second: "Open Second Client Window",
      label_homeserver: "Homeserver URL",
      label_gateway: "Gateway API URL",
      label_username: "Username (localpart)",
      label_password: "Password",
      label_room_name: "New Room Name",
      label_invite_on_create: "Invite on Create (optional)",
      label_active_room: "Active Room ID",
      label_join_room_id: "Join Room ID",
      label_invite_user_id: "Friend User ID",
      label_agent_id: "Agent ID",
      label_purpose: "Purpose",
      label_rate_limit: "Rate Limit / Minute",
      label_grant_id: "Grant ID",
      label_message: "Message",
      label_actor_id: "Actor ID",
      label_action_type: "Action Type",
      placeholder_username: "e.g. tg_user_a",
      placeholder_password: "at least 8 chars, e.g. Passw0rd!",
      placeholder_room_name: "e.g. Team Chat",
      placeholder_invite: "@tg_user_b:localhost",
      placeholder_room_id: "!room:localhost",
      placeholder_agent_id: "agent.summary.demo",
      placeholder_purpose: "daily_summary",
      placeholder_grant: "grant_xxx",
      placeholder_message: "Type message and click Send",
      placeholder_actor: "agent.summary.demo",
      placeholder_action: "agent_summarize",
      btn_register: "Register",
      btn_login: "Login",
      btn_logout: "Logout",
      btn_refresh: "Refresh",
      btn_create_room: "Create Room",
      btn_join_room: "Join Room",
      btn_sync: "Sync",
      btn_invite_user: "Invite User",
      btn_create_agent: "Create Agent Profile",
      btn_grant: "Grant Agent",
      btn_revoke: "Revoke Grant",
      btn_summarize: "Summarize",
      btn_summarize_send: "Summarize and Send",
      btn_send: "Send",
      btn_upload: "Upload File",
      btn_query_audit: "Query Audit",
      btn_verify_audit: "Verify Chain",
      btn_run_demo: "Run Demo Flow",
      empty_chat: "No messages yet. Send or sync first.",
      self_name: "Me",
      toast_success: "Success",
      toast_error: "Error",
      toast_info: "Info",
      info_open_second: "Second window opened. Login another user there.",
      info_profile_created: "Agent profile created locally. You can now grant permission.",
      info_language_changed: "Language switched.",
      info_tab_switched: "Page switched.",
      info_status_refreshed: "Status refreshed.",
      err_no_session: "No active session. Please register or login.",
      err_need_credentials: "Username and password are required.",
      err_password_short: "Password must be at least 8 characters.",
      err_need_room: "Room ID is required.",
      err_need_room_message: "Room ID and message are required.",
      err_need_invite: "Room ID and friend user ID are required.",
      err_need_agent: "Agent ID and purpose are required.",
      err_need_grant: "Grant ID is required.",
      err_demo_need_creds: "Enter username/password before running demo.",
      err_demo_deny_expected: "Expected 403 deny after revoke, but request was allowed.",
      err_demo_audit_verify: "Audit verification failed.",
      demo_start: "Running demo: auth -> room -> message -> grant -> summarize -> revoke -> verify.",
      demo_done: "Demo finished successfully.",
      demo_messages: [
        "Hello, this is test message #1",
        "Hello, this is test message #2",
        "Please summarize today's discussion",
      ],
    },
  };

  const SESSION_KEY = "prism_telegram_vue_session_v1";
  const LANGUAGE_KEY = "prism_telegram_vue_lang_v1";

  const { createApp } = window.Vue;

  createApp({
    data() {
      return {
        language: "zh",
        activeTab: "auth",
        tabs: [
          { id: "auth", label: "tab_auth" },
          { id: "room", label: "tab_room" },
          { id: "invite", label: "tab_invite" },
          { id: "agent", label: "tab_agent" },
          { id: "chat", label: "tab_chat" },
          { id: "audit", label: "tab_audit" },
        ],
        config: {
          homeserverUrl: "http://localhost:8008",
          gatewayUrl: "http://localhost:8080/api/v1",
        },
        forms: {
          username: "",
          password: "",
          roomName: "",
          inviteOnCreate: "",
          activeRoomId: "",
          joinRoomId: "",
          inviteUserId: "",
          agentId: "agent.summary.demo",
          purpose: "daily_summary",
          rateLimit: 60,
          grantId: "",
          messageBody: "",
          auditActorId: "",
          auditActionType: "",
        },
        session: null,
        roomMessages: {},
        roomSet: [],
        selectedFile: null,
        sessionOutput: {},
        roomOutput: {},
        inviteOutput: {},
        agentOutput: {},
        auditOutput: {},
        toasts: [],
        toastSeq: 1,
      };
    },
    computed: {
      knownRooms() {
        return [...this.roomSet];
      },
      activeRoomMessages() {
        const roomId = this.forms.activeRoomId.trim();
        if (!roomId) {
          return [];
        }
        return this.roomMessages[roomId] || [];
      },
    },
    mounted() {
      this.language = this.loadLanguage() || "zh";
      const session = this.loadSession();
      if (session) {
        this.session = session;
        if (session.homeserver) {
          this.config.homeserverUrl = session.homeserver;
        }
      }
      if (!this.config.gatewayUrl.trim()) {
        this.config.gatewayUrl = `${window.location.origin}/api/v1`;
      }
      this.refreshSessionStatus();
    },
    methods: {
      tt(key) {
        const dict = I18N[this.language] || I18N.en;
        return dict[key] || I18N.en[key] || key;
      },
      pretty(payload) {
        return JSON.stringify(payload || {}, null, 2);
      },
      setLanguage(lang, withToast = false) {
        if (lang !== "zh" && lang !== "en") {
          return;
        }
        this.language = lang;
        this.saveLanguage(lang);
        document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
        if (withToast) {
          this.pushToast("info", this.tt("info_language_changed"));
        }
      },
      switchTab(tabId) {
        this.activeTab = tabId;
        this.pushToast("info", this.tt("info_tab_switched"));
      },
      mask(secret) {
        if (!secret) {
          return "";
        }
        if (secret.length <= 6) {
          return "*".repeat(secret.length);
        }
        return `${"*".repeat(secret.length - 6)}${secret.slice(-6)}`;
      },
      pushToast(type, message) {
        const id = this.toastSeq++;
        this.toasts.push({
          id,
          type,
          title: this.tt(
            type === "success" ? "toast_success" : type === "error" ? "toast_error" : "toast_info"
          ),
          message,
        });
        window.setTimeout(() => {
          this.toasts = this.toasts.filter((toast) => toast.id !== id);
        }, 3600);
      },
      openSecondClient() {
        window.open(`/web/?client=${Date.now()}`, "_blank", "noopener,noreferrer");
        this.pushToast("info", this.tt("info_open_second"));
      },
      saveSession(session) {
        window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
      },
      loadSession() {
        const raw = window.sessionStorage.getItem(SESSION_KEY);
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
      },
      clearSession() {
        window.sessionStorage.removeItem(SESSION_KEY);
      },
      saveLanguage(lang) {
        window.localStorage.setItem(LANGUAGE_KEY, lang);
      },
      loadLanguage() {
        const lang = window.localStorage.getItem(LANGUAGE_KEY);
        if (lang === "zh" || lang === "en") {
          return lang;
        }
        return null;
      },
      normalizeUsername(raw) {
        const value = raw.trim();
        if (!value) {
          return "";
        }
        if (!value.startsWith("@")) {
          return value;
        }
        const stripped = value.slice(1);
        const index = stripped.indexOf(":");
        return index >= 0 ? stripped.slice(0, index) : stripped;
      },
      ensureSession() {
        if (!this.session) {
          throw new Error(this.tt("err_no_session"));
        }
        return this.session;
      },
      formatValidationIssue(issue) {
        if (!issue || typeof issue !== "object") {
          return String(issue);
        }
        const loc = Array.isArray(issue.loc) ? issue.loc.join(".") : "";
        const msg = typeof issue.msg === "string" ? issue.msg : JSON.stringify(issue);
        return loc ? `${loc}: ${msg}` : msg;
      },
      formatApiDetail(detail) {
        if (typeof detail === "string") {
          return detail;
        }
        if (Array.isArray(detail)) {
          return detail.map((issue) => this.formatValidationIssue(issue)).join("; ");
        }
        if (detail && typeof detail === "object") {
          if (typeof detail.msg === "string") {
            return detail.msg;
          }
          return JSON.stringify(detail);
        }
        return String(detail);
      },
      async request(path, options = {}) {
        const base = this.config.gatewayUrl.trim().replace(/\/+$/, "");
        if (!base) {
          throw new Error("Gateway URL is required.");
        }

        const headers = {};
        if (options.body !== undefined) {
          headers["content-type"] = "application/json";
        }
        if (options.auth !== false) {
          const session = this.ensureSession();
          headers.authorization = `Bearer ${session.accessToken}`;
        }

        const response = await fetch(`${base}${path}`, {
          method: options.method || "GET",
          headers,
          body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
        });
        const text = await response.text();
        let data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch (_err) {
          data = { raw: text };
        }

        if (!response.ok) {
          const detail = this.formatApiDetail(data?.error ?? data?.detail ?? data);
          throw new Error(`${response.status} ${response.statusText}: ${detail}`);
        }
        return data;
      },
      async upload(path, file) {
        const base = this.config.gatewayUrl.trim().replace(/\/+$/, "");
        if (!base) {
          throw new Error("Gateway URL is required.");
        }
        const session = this.ensureSession();
        const formData = new FormData();
        formData.append("file", file, file.name || "upload.bin");

        const response = await fetch(`${base}${path}`, {
          method: "POST",
          headers: {
            authorization: `Bearer ${session.accessToken}`,
          },
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
          const detail = this.formatApiDetail(data?.error ?? data?.detail ?? data);
          throw new Error(`${response.status} ${response.statusText}: ${detail}`);
        }
        return data;
      },
      refreshSessionStatus() {
        if (!this.session) {
          this.sessionOutput = {
            status: "logged_out",
            hint: this.tt("status_logged_out"),
          };
          return;
        }
        this.sessionOutput = {
          status: "logged_in",
          user_id: this.session.userId,
          device_id: this.session.deviceId,
          homeserver: this.session.homeserver,
          access_token: this.mask(this.session.accessToken),
          next_batch: this.session.nextBatch || null,
          room_count: this.roomSet.length,
        };
      },
      refreshStatusAndToast() {
        this.refreshSessionStatus();
        this.pushToast("info", this.tt("info_status_refreshed"));
      },
      setSessionFromPayload(payload) {
        this.session = {
          homeserver: this.config.homeserverUrl.trim(),
          userId: payload.user_id,
          deviceId: payload.device_id || null,
          accessToken: payload.access_token,
          nextBatch: null,
        };
        this.saveSession(this.session);
        this.refreshSessionStatus();
      },
      async registerUser() {
        try {
          const username = this.normalizeUsername(this.forms.username);
          const password = this.forms.password;
          if (!username || !password) {
            throw new Error(this.tt("err_need_credentials"));
          }
          if (password.length < 8) {
            throw new Error(this.tt("err_password_short"));
          }
          const payload = await this.request("/matrix/register", {
            method: "POST",
            auth: false,
            body: { username, password },
          });
          this.setSessionFromPayload(payload);
          this.pushToast("success", `${this.tt("btn_register")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async loginUser() {
        try {
          const username = this.normalizeUsername(this.forms.username);
          const password = this.forms.password;
          if (!username || !password) {
            throw new Error(this.tt("err_need_credentials"));
          }
          if (password.length < 8) {
            throw new Error(this.tt("err_password_short"));
          }
          const payload = await this.request("/matrix/login", {
            method: "POST",
            auth: false,
            body: { username, password },
          });
          this.setSessionFromPayload(payload);
          this.pushToast("success", `${this.tt("btn_login")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      logoutUser() {
        this.clearSession();
        this.session = null;
        this.roomMessages = {};
        this.roomSet = [];
        this.forms.activeRoomId = "";
        this.forms.joinRoomId = "";
        this.refreshSessionStatus();
        this.pushToast("info", this.tt("btn_logout"));
      },
      mergeRoomId(roomId) {
        if (!roomId) {
          return;
        }
        if (!this.roomSet.includes(roomId)) {
          this.roomSet = [...this.roomSet, roomId].sort();
        }
      },
      selectRoom(roomId) {
        this.forms.activeRoomId = roomId;
        this.activeTab = "chat";
      },
      parseTimestamp(originServerTs) {
        if (typeof originServerTs !== "number") {
          return { iso: "-", ms: 0 };
        }
        const date = new Date(originServerTs);
        return {
          iso: date.toISOString(),
          ms: date.getTime(),
        };
      },
      ingestSync(syncPayload) {
        const joinedRooms = syncPayload?.rooms?.join || {};
        const nextMessages = { ...this.roomMessages };
        for (const [roomId, roomData] of Object.entries(joinedRooms)) {
          this.mergeRoomId(roomId);
          const timelineEvents = roomData?.timeline?.events || [];
          const roomMap = new Map(
            (nextMessages[roomId] || []).map((item) => [item.eventId, item])
          );
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
            const ts = this.parseTimestamp(event?.origin_server_ts);
            roomMap.set(eventId, {
              eventId,
              roomId,
              sender,
              body,
              timestamp: ts.iso,
              timestampMs: ts.ms,
            });
          }
          const list = Array.from(roomMap.values()).sort((a, b) => a.timestampMs - b.timestampMs);
          nextMessages[roomId] = list;
        }
        this.roomMessages = nextMessages;
      },
      async createRoom() {
        try {
          this.ensureSession();
          const invite = this.forms.inviteOnCreate.trim();
          const body = {
            preset: "private_chat",
            name: this.forms.roomName.trim() || `tg-room-${Date.now()}`,
          };
          if (invite) {
            body.invite = [invite];
          }
          const payload = await this.request("/matrix/rooms", {
            method: "POST",
            body,
          });
          const roomId = payload.room_id;
          this.forms.activeRoomId = roomId;
          this.mergeRoomId(roomId);
          this.roomOutput = payload;
          this.refreshSessionStatus();
          this.pushToast("success", `${this.tt("btn_create_room")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async joinRoom() {
        try {
          this.ensureSession();
          const roomId = this.forms.joinRoomId.trim() || this.forms.activeRoomId.trim();
          if (!roomId) {
            throw new Error(this.tt("err_need_room"));
          }
          const payload = await this.request(`/matrix/rooms/${encodeURIComponent(roomId)}/join`, {
            method: "POST",
          });
          this.forms.activeRoomId = payload.room_id || roomId;
          this.mergeRoomId(this.forms.activeRoomId);
          this.roomOutput = payload;
          this.pushToast("success", `${this.tt("btn_join_room")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async inviteFriend() {
        try {
          this.ensureSession();
          const roomId = this.forms.activeRoomId.trim();
          const userId = this.forms.inviteUserId.trim();
          if (!roomId || !userId) {
            throw new Error(this.tt("err_need_invite"));
          }
          const payload = await this.request(`/matrix/rooms/${encodeURIComponent(roomId)}/invite`, {
            method: "POST",
            body: { user_id: userId },
          });
          this.inviteOutput = payload;
          this.pushToast("success", `${this.tt("btn_invite_user")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async syncMessages() {
        try {
          const session = this.ensureSession();
          const params = new URLSearchParams();
          params.set("timeout_ms", "3000");
          if (session.nextBatch) {
            params.set("since", session.nextBatch);
          }
          const payload = await this.request(`/matrix/sync?${params.toString()}`, {
            method: "GET",
          });
          session.nextBatch = payload.next_batch || session.nextBatch;
          this.saveSession(session);
          this.ingestSync(payload);
          if (!this.forms.activeRoomId.trim() && this.roomSet.length > 0) {
            this.forms.activeRoomId = this.roomSet[0];
          }
          this.roomOutput = {
            synced_rooms: Object.keys(payload?.rooms?.join || {}).length,
            next_batch: session.nextBatch || null,
          };
          this.refreshSessionStatus();
          this.scrollChatToBottom();
          this.pushToast("success", `${this.tt("btn_sync")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async sendMessage() {
        try {
          this.ensureSession();
          const roomId = this.forms.activeRoomId.trim();
          const body = this.forms.messageBody.trim();
          if (!roomId || !body) {
            throw new Error(this.tt("err_need_room_message"));
          }
          const payload = await this.request(
            `/matrix/rooms/${encodeURIComponent(roomId)}/messages`,
            {
              method: "POST",
              body: { body },
            }
          );
          this.forms.messageBody = "";
          this.mergeRoomId(roomId);
          this.roomOutput = payload;
          this.pushToast("success", `${this.tt("btn_send")} OK`);
          await this.syncMessages();
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      onFileSelected(event) {
        this.selectedFile = event.target.files?.[0] || null;
      },
      async uploadFile() {
        try {
          this.ensureSession();
          const roomId = this.forms.activeRoomId.trim();
          if (!roomId) {
            throw new Error(this.tt("err_need_room"));
          }
          if (!this.selectedFile) {
            throw new Error("Please choose a file first.");
          }
          const payload = await this.upload(
            `/matrix/rooms/${encodeURIComponent(roomId)}/files`,
            this.selectedFile
          );
          this.roomOutput = payload;
          this.pushToast("success", `${this.tt("btn_upload")} OK`);
          await this.syncMessages();
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      createAgentProfile() {
        this.pushToast("info", this.tt("info_profile_created"));
        this.agentOutput = {
          status: "agent_profile_created",
          agent_id: this.forms.agentId.trim(),
          purpose: this.forms.purpose.trim(),
        };
      },
      async grantAgent() {
        try {
          const session = this.ensureSession();
          const agentId = this.forms.agentId.trim();
          const purpose = this.forms.purpose.trim();
          if (!agentId || !purpose) {
            throw new Error(this.tt("err_need_agent"));
          }
          const payload = await this.request("/policy/grants", {
            method: "POST",
            body: {
              user_id: session.userId,
              agent_id: agentId,
              data_category: "room_messages",
              purpose,
              rate_limit_per_minute: Math.max(1, Number(this.forms.rateLimit || 60)),
            },
          });
          if (payload?.grant_id) {
            this.forms.grantId = payload.grant_id;
          }
          this.agentOutput = payload;
          this.pushToast("success", `${this.tt("btn_grant")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async revokeAgent() {
        try {
          const session = this.ensureSession();
          const grantId = this.forms.grantId.trim();
          if (!grantId) {
            throw new Error(this.tt("err_need_grant"));
          }
          const payload = await this.request("/policy/revoke", {
            method: "POST",
            body: {
              user_id: session.userId,
              grant_id: grantId,
              reason: "web_revoke",
            },
          });
          this.agentOutput = payload;
          this.pushToast("success", `${this.tt("btn_revoke")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async summarizeOnly() {
        try {
          this.ensureSession();
          const roomId = this.forms.activeRoomId.trim();
          const agentId = this.forms.agentId.trim();
          const purpose = this.forms.purpose.trim();
          if (!roomId) {
            throw new Error(this.tt("err_need_room"));
          }
          if (!agentId || !purpose) {
            throw new Error(this.tt("err_need_agent"));
          }
          const payload = await this.request("/agent/summarize", {
            method: "POST",
            body: {
              agent_id: agentId,
              room_id: roomId,
              purpose,
              recent_message_limit: 50,
              max_items: 10,
            },
          });
          this.agentOutput = payload;
          this.pushToast("success", `${this.tt("btn_summarize")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async summarizeAndSend() {
        try {
          this.ensureSession();
          const roomId = this.forms.activeRoomId.trim();
          const agentId = this.forms.agentId.trim();
          const purpose = this.forms.purpose.trim();
          if (!roomId) {
            throw new Error(this.tt("err_need_room"));
          }
          if (!agentId || !purpose) {
            throw new Error(this.tt("err_need_agent"));
          }
          const payload = await this.request("/agent/summarize-and-send", {
            method: "POST",
            body: {
              agent_id: agentId,
              room_id: roomId,
              purpose,
              recent_message_limit: 50,
              max_items: 10,
            },
          });
          this.agentOutput = payload;
          this.pushToast("success", `${this.tt("btn_summarize_send")} OK`);
          await this.syncMessages();
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async queryAudit() {
        try {
          this.ensureSession();
          const params = new URLSearchParams();
          params.set("limit", "120");
          if (this.forms.auditActorId.trim()) {
            params.set("actor_id", this.forms.auditActorId.trim());
          }
          if (this.forms.auditActionType.trim()) {
            params.set("action_type", this.forms.auditActionType.trim());
          }
          const payload = await this.request(`/audit/events?${params.toString()}`, {
            method: "GET",
          });
          this.auditOutput = payload;
          this.pushToast("success", `${this.tt("btn_query_audit")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async verifyAudit() {
        try {
          this.ensureSession();
          const params = new URLSearchParams();
          params.set("limit", "600");
          if (this.forms.auditActorId.trim()) {
            params.set("actor_id", this.forms.auditActorId.trim());
          }
          if (this.forms.auditActionType.trim()) {
            params.set("action_type", this.forms.auditActionType.trim());
          }
          const payload = await this.request(`/audit/verify?${params.toString()}`, {
            method: "GET",
          });
          this.auditOutput = payload;
          this.pushToast("success", `${this.tt("btn_verify_audit")} OK`);
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      async runDemoFlow() {
        try {
          const username = this.normalizeUsername(this.forms.username);
          const password = this.forms.password;
          if (!username || !password) {
            throw new Error(this.tt("err_demo_need_creds"));
          }
          this.pushToast("info", this.tt("demo_start"));

          try {
            await this.registerUser();
          } catch (_err) {
            await this.loginUser();
          }

          await this.createRoom();

          const messages = I18N[this.language]?.demo_messages || I18N.en.demo_messages;
          for (const message of messages) {
            this.forms.messageBody = message;
            await this.sendMessage();
          }

          await this.syncMessages();
          await this.grantAgent();
          await this.summarizeAndSend();
          await this.revokeAgent();

          let denied = false;
          try {
            await this.summarizeOnly();
          } catch (error) {
            if (this.normalizeError(error).includes("403")) {
              denied = true;
            } else {
              throw error;
            }
          }
          if (!denied) {
            throw new Error(this.tt("err_demo_deny_expected"));
          }

          this.forms.auditActorId = this.forms.agentId.trim();
          await this.verifyAudit();
          if (this.auditOutput?.verified !== true) {
            throw new Error(this.tt("err_demo_audit_verify"));
          }
          this.pushToast("success", this.tt("demo_done"));
        } catch (error) {
          this.pushToast("error", this.normalizeError(error));
          throw error;
        }
      },
      normalizeError(error) {
        if (error instanceof Error) {
          return error.message;
        }
        return String(error);
      },
      isSelfMessage(message) {
        return Boolean(this.session) && message.sender === this.session.userId;
      },
      displaySender(sender) {
        if (this.session && sender === this.session.userId) {
          return this.tt("self_name");
        }
        return sender;
      },
      scrollChatToBottom() {
        this.$nextTick(() => {
          const feed = this.$refs.chatFeed;
          if (feed && typeof feed.scrollTop === "number") {
            feed.scrollTop = feed.scrollHeight;
          }
        });
      },
    },
  }).mount("#app");
})();
