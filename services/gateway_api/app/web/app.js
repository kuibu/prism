(() => {
  const I18N = {
    zh: {
      app_title: "前端测试页面",
      sidebar_account: "当前会话",
      sidebar_inbox: "消息中心",
      sidebar_rooms: "房间列表",
      sidebar_compose: "快捷发送区",
      tab_auth: "注册 / 登录",
      tab_room: "创建房间",
      tab_invite: "邀请好友",
      tab_inbox: "消息中心",
      tab_agent: "创建 Agent",
      tab_chat: "聊天页面",
      tab_audit: "审计页面",
      status_logged_out: "未登录（建议打开两个窗口分别登录两个用户进行联调）。",
      status_logged_out_short: "未登录",
      empty_rooms: "暂无已知房间。创建或加入房间后会显示。",
      empty_inbox: "暂无消息。",
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
      label_member_count: "房间成员",
      label_member_ids: "成员 ID",
      label_creator: "创建人",
      label_target_room_name: "发送目标房间",
      label_target_room_id: "发送目标房间 ID",
      label_sender_id: "发送者 ID",
      label_selected_file: "已选文件",
      placeholder_username: "例如 tg_user_a",
      placeholder_password: "至少8位，例如 Passw0rd!",
      placeholder_room_name: "例如 Team Chat",
      placeholder_invite: "支持 username 或 @username:localhost",
      placeholder_room_id: "!room:localhost",
      placeholder_agent_id: "agent.summary.demo",
      placeholder_purpose: "daily_summary",
      placeholder_grant: "grant_xxx",
      placeholder_message: "输入消息后点击发送，消息会自动实时刷新",
      placeholder_actor: "agent.summary.demo",
      placeholder_action: "agent_summarize",
      hint_invite_auto: "可直接输入用户名（如 alice），系统会自动补全为 @alice:localhost",
      hint_invite_preview: "将发送邀请给：",
      hint_chat_room_required: "请先在房间列表选择一个房间，再发送消息或上传文件。",
      hint_need_login: "请先登录，再使用发送区发消息或上传文件。",
      btn_open_second: "打开第二个客户端窗口",
      btn_register: "注册",
      btn_login: "登录",
      btn_logout: "退出",
      btn_refresh: "刷新状态",
      btn_create_room: "创建房间",
      btn_join_room: "加入房间",
      btn_sync: "立即同步",
      btn_invite_user: "邀请好友",
      btn_clear_inbox: "清空消息中心",
      btn_view_detail: "查看详情",
      btn_close: "关闭",
      btn_go_room: "进入房间",
      btn_accept_invite: "接受邀请并加入",
      btn_create_agent: "创建 Agent 资料",
      btn_grant: "授权 Agent",
      btn_revoke: "撤销授权",
      btn_summarize: "摘要（仅返回）",
      btn_summarize_send: "摘要并发送到房间",
      btn_send: "发送消息",
      btn_pick_file: "选择文件",
      btn_upload: "上传文件",
      btn_download: "下载文件",
      btn_query_audit: "查询审计",
      btn_verify_audit: "验证审计链",
      btn_run_demo: "一键双人联调演示",
      btn_refresh_members: "刷新成员",
      col_time: "时间",
      col_type: "类型",
      col_line: "消息",
      col_action: "操作",
      dialog_inbox_title: "消息中心详情",
      inbox_type_invite: "邀请",
      inbox_type_message: "新消息",
      inbox_type_system: "系统",
      inbox_type_file: "文件",
      inbox_invite_line: "收到邀请：{inviter} 邀请你加入 {room}",
      inbox_message_line: "{room} 有新消息：{sender} 说「{preview}」",
      inbox_file_line: "{room} 有新文件：{sender} 上传了「{preview}」",
      inbox_join_hint: "你已加入房间 {room}",
      empty_chat: "暂无消息，系统正在自动同步。",
      self_name: "我",
      msg_switch_tab: "已切换页面",
      msg_language: "语言已切换",
      msg_open_second: "已打开新窗口，可在新窗口登录另一个用户。",
      msg_status_refreshed: "状态已刷新",
      msg_sync_ok: "同步成功：新增消息 {messages} 条，新增邀请 {invites} 条。",
      msg_members_ok: "房间成员已刷新，共 {count} 人。",
      msg_download_started: "开始下载文件：{name}",
      msg_download_failed: "下载文件失败",
      msg_file_selected: "已选择文件：{name}",
      msg_profile_created: "Agent 资料已创建（本地），可继续授权。",
      msg_inbox_cleared: "消息中心已清空",
      msg_joined_from_invite: "已加入房间，可以发送消息与文件。",
      err_no_session: "当前未登录，请先注册或登录。",
      err_need_credentials: "请输入用户名和密码。",
      err_password_short: "密码至少 8 位。",
      err_need_room: "请先填写房间 ID。",
      err_need_room_message: "请先填写房间 ID 和消息内容。",
      err_members_need_join: "你还没有加入这个房间，请先在“创建房间”页点击“加入房间”。",
      err_need_invite: "请填写房间 ID 和好友用户 ID。",
      err_need_agent: "请填写 Agent ID 和 Purpose。",
      err_need_grant: "请填写授权 ID。",
      err_need_file: "请先选择文件。",
      err_demo_need_creds: "先填写用户名和密码，再执行演示。",
      err_demo_deny_expected: "撤权后应返回 403 deny，但本次未拒绝。",
      err_demo_audit_verify: "审计链验证失败。",
      err_api: "请求失败",
      demo_start: "开始演示：注册/登录 -> 建房 -> 发消息 -> 授权 -> 摘要 -> 撤权 -> 验证。",
      demo_done: "演示完成：流程全部通过。",
      demo_messages: [
        "你好，这是第1条测试消息",
        "你好，这是第2条测试消息",
        "请帮我总结今天聊天重点",
      ],
    },
    en: {
      app_title: "Frontend Test Page",
      sidebar_account: "Current Session",
      sidebar_inbox: "Message Center",
      sidebar_rooms: "Rooms",
      sidebar_compose: "Quick Composer",
      tab_auth: "Register / Login",
      tab_room: "Create Room",
      tab_invite: "Invite Friend",
      tab_inbox: "Message Center",
      tab_agent: "Create Agent",
      tab_chat: "Chat",
      tab_audit: "Audit",
      status_logged_out: "Logged out. Use two windows with two users for end-to-end chat tests.",
      status_logged_out_short: "Logged out",
      empty_rooms: "No known rooms yet. Create or join a room first.",
      empty_inbox: "No messages yet.",
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
      label_member_count: "Members",
      label_member_ids: "Member IDs",
      label_creator: "Creator",
      label_target_room_name: "Target Room Name",
      label_target_room_id: "Target Room ID",
      label_sender_id: "Sender ID",
      label_selected_file: "Selected File",
      placeholder_username: "e.g. tg_user_a",
      placeholder_password: "at least 8 chars, e.g. Passw0rd!",
      placeholder_room_name: "e.g. Team Chat",
      placeholder_invite: "username or @username:localhost",
      placeholder_room_id: "!room:localhost",
      placeholder_agent_id: "agent.summary.demo",
      placeholder_purpose: "daily_summary",
      placeholder_grant: "grant_xxx",
      placeholder_message: "Type and send. New messages appear automatically.",
      placeholder_actor: "agent.summary.demo",
      placeholder_action: "agent_summarize",
      hint_invite_auto: "You can type only username (alice). It auto-completes to @alice:localhost",
      hint_invite_preview: "Invite target:",
      hint_chat_room_required: "Select a room first, then send messages or upload files.",
      hint_need_login: "Login first to send messages or upload files from the composer.",
      btn_open_second: "Open Second Client Window",
      btn_register: "Register",
      btn_login: "Login",
      btn_logout: "Logout",
      btn_refresh: "Refresh",
      btn_create_room: "Create Room",
      btn_join_room: "Join Room",
      btn_sync: "Sync Now",
      btn_invite_user: "Invite User",
      btn_clear_inbox: "Clear Message Center",
      btn_view_detail: "View",
      btn_close: "Close",
      btn_go_room: "Go to Room",
      btn_accept_invite: "Accept and Join",
      btn_create_agent: "Create Agent Profile",
      btn_grant: "Grant Agent",
      btn_revoke: "Revoke Grant",
      btn_summarize: "Summarize",
      btn_summarize_send: "Summarize and Send",
      btn_send: "Send",
      btn_pick_file: "Pick File",
      btn_upload: "Upload File",
      btn_download: "Download File",
      btn_query_audit: "Query Audit",
      btn_verify_audit: "Verify Chain",
      btn_run_demo: "Run Demo Flow",
      btn_refresh_members: "Refresh Members",
      col_time: "Time",
      col_type: "Type",
      col_line: "Message",
      col_action: "Action",
      dialog_inbox_title: "Message Center Details",
      inbox_type_invite: "Invite",
      inbox_type_message: "New Message",
      inbox_type_system: "System",
      inbox_type_file: "File",
      inbox_invite_line: "Invitation received: {inviter} invited you to {room}",
      inbox_message_line: "{room} has a new message: {sender} said \"{preview}\"",
      inbox_file_line: "{room} has a new file: {sender} uploaded \"{preview}\"",
      inbox_join_hint: "You joined room {room}",
      empty_chat: "No messages yet. Auto-sync is running.",
      self_name: "Me",
      msg_switch_tab: "Page switched",
      msg_language: "Language switched",
      msg_open_second: "Second window opened. Login another user there.",
      msg_status_refreshed: "Status refreshed",
      msg_sync_ok: "Sync done: {messages} new messages, {invites} new invites.",
      msg_members_ok: "Room members refreshed: {count}",
      msg_download_started: "Downloading file: {name}",
      msg_download_failed: "File download failed",
      msg_file_selected: "File selected: {name}",
      msg_profile_created: "Agent profile created locally.",
      msg_inbox_cleared: "Message center cleared",
      msg_joined_from_invite: "Joined room. You can now send messages and files.",
      err_no_session: "No active session. Please register or login.",
      err_need_credentials: "Username and password are required.",
      err_password_short: "Password must be at least 8 characters.",
      err_need_room: "Room ID is required.",
      err_need_room_message: "Room ID and message are required.",
      err_members_need_join: "You are not in this room yet. Join the room first.",
      err_need_invite: "Room ID and friend user ID are required.",
      err_need_agent: "Agent ID and purpose are required.",
      err_need_grant: "Grant ID is required.",
      err_need_file: "Please pick a file first.",
      err_demo_need_creds: "Enter username/password before running demo.",
      err_demo_deny_expected: "Expected 403 deny after revoke, but request was allowed.",
      err_demo_audit_verify: "Audit verification failed.",
      err_api: "Request failed",
      demo_start: "Running demo: auth -> room -> message -> grant -> summarize -> revoke -> verify.",
      demo_done: "Demo finished successfully.",
      demo_messages: [
        "Hello, this is test message #1",
        "Hello, this is test message #2",
        "Please summarize today's discussion",
      ],
    },
  };

  const query = new URLSearchParams(window.location.search);
  const clientScope = query.get("client") || "default";
  const SESSION_KEY = `prism_frontend_session_v2_${clientScope}`;
  const LANGUAGE_KEY = "prism_frontend_lang_v2";
  const HISTORY_KEY_PREFIX = "prism_frontend_history_v1";
  const ANIMAL_AVATAR_COUNT = 100;
  const ANIMAL_AVATAR_VERSION = "20260222a";
  const ANIMAL_AVATAR_SLUGS = [
    "cat", "tiger", "leopard", "lynx", "cheetah", "dog", "wolf", "husky", "coyote", "dingo",
    "rabbit", "hare", "pika", "jackrabbit", "angora", "brown_bear", "black_bear", "polar_bear", "panda", "koala",
    "red_fox", "fennec", "arctic_fox", "raccoon", "red_panda", "lion", "cougar", "jaguar", "hyena", "boar",
    "sparrow", "robin", "swallow", "eagle", "falcon", "owl", "snowy_owl", "barn_owl", "crow", "raven",
    "penguin", "puffin", "auk", "seagull", "albatross", "duck", "goose", "swan", "flamingo", "parrot",
    "goldfish", "clownfish", "tuna", "salmon", "shark", "frog", "toad", "newt", "salamander", "gecko",
    "turtle", "tortoise", "crocodile", "alligator", "lizard", "elephant", "mammoth", "rhino", "hippo", "tapir",
    "monkey", "gorilla", "chimpanzee", "orangutan", "lemur", "pig", "wild_boar", "peccary", "hamster", "guinea_pig",
    "cow", "yak", "buffalo", "bison", "goat", "deer", "elk", "moose", "reindeer", "antelope",
    "horse", "zebra", "donkey", "mule", "camel", "seal", "walrus", "otter", "beaver", "platypus",
  ];

  const { createApp } = window.Vue;

  function hashString(value) {
    let hash = 2166136261;
    for (let i = 0; i < value.length; i += 1) {
      hash ^= value.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  createApp({
    data() {
      return {
        language: "zh",
        activeTab: "auth",
        tabs: [
          { id: "auth", label: "tab_auth" },
          { id: "room", label: "tab_room" },
          { id: "invite", label: "tab_invite" },
          { id: "inbox", label: "tab_inbox" },
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
        roomMembers: {},
        roomDetails: {},
        selectedFile: null,
        sessionOutput: {},
        roomOutput: {},
        inviteOutput: {},
        agentOutput: {},
        auditOutput: {},
        inboxItems: [],
        inboxSeen: {},
        inboxDialogVisible: false,
        selectedInboxItem: null,
        syncInFlight: false,
        autoSyncEnabled: false,
        syncTimer: null,
        historyPersistTimer: null,
        avatarCache: {},
        lastSilentSyncErrorTs: 0,
      };
    },
    computed: {
      knownRooms() {
        return [...this.roomSet];
      },
      sidebarInboxItems() {
        return this.inboxItems.slice(0, 8);
      },
      normalizedInviteUserId() {
        return this.normalizeUserId(this.forms.inviteUserId);
      },
      activeRoomMessages() {
        const roomId = this.forms.activeRoomId.trim();
        if (!roomId) {
          return [];
        }
        return this.roomMessages[roomId] || [];
      },
      activeRoomDisplayName() {
        const roomId = this.forms.activeRoomId.trim();
        if (!roomId) {
          return "-";
        }
        return this.roomDisplayName(roomId);
      },
      activeRoomMemberCount() {
        const roomId = this.forms.activeRoomId.trim();
        if (!roomId) {
          return 0;
        }
        const roomDetail = this.roomDetails[roomId];
        if (roomDetail && Number.isFinite(roomDetail.joinedCount)) {
          return roomDetail.joinedCount;
        }
        const detail = this.roomMembers[roomId];
        if (detail && Number.isFinite(detail.count)) {
          return detail.count;
        }
        const senders = new Set((this.roomMessages[roomId] || []).map((msg) => msg.sender));
        return senders.size;
      },
      activeRoomMemberIds() {
        const roomId = this.forms.activeRoomId.trim();
        if (!roomId) {
          return [];
        }
        const roomDetail = this.roomDetails[roomId];
        if (roomDetail && Array.isArray(roomDetail.joinedUserIds)) {
          return [...roomDetail.joinedUserIds];
        }
        const detail = this.roomMembers[roomId];
        if (detail && Array.isArray(detail.users)) {
          return [...detail.users];
        }
        return [];
      },
    },
    mounted() {
      this.language = this.loadLanguage() || "zh";
      document.documentElement.lang = this.language === "zh" ? "zh-CN" : "en";
      if (!this.config.gatewayUrl.trim()) {
        this.config.gatewayUrl = `${window.location.origin}/api/v1`;
      }
      const session = this.loadSession();
      if (session) {
        this.session = session;
        if (session.homeserver) {
          this.config.homeserverUrl = session.homeserver;
        }
        this.restoreHistoryCache(session.userId);
      }
      this.refreshSessionStatus();
      if (this.session) {
        this.startAutoSync();
        this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false }).catch(() => undefined);
      }
    },
    beforeUnmount() {
      this.stopAutoSync();
      if (this.historyPersistTimer) {
        window.clearTimeout(this.historyPersistTimer);
        this.historyPersistTimer = null;
      }
    },
    methods: {
      tt(key) {
        const dict = I18N[this.language] || I18N.en;
        return dict[key] || I18N.en[key] || key;
      },
      ttf(key, vars) {
        let text = this.tt(key);
        if (!vars || typeof vars !== "object") {
          return text;
        }
        for (const [name, value] of Object.entries(vars)) {
          text = text.replaceAll(`{${name}}`, String(value));
        }
        return text;
      },
      pretty(payload) {
        return JSON.stringify(payload || {}, null, 2);
      },
      notify(type, message) {
        const normalized = type === "error" || type === "warning" || type === "success" ? type : "info";
        window.ElementPlus.ElMessage({
          type: normalized,
          message,
          showClose: true,
          duration: 2600,
        });
      },
      setLanguage(lang, withToast = false) {
        if (lang !== "zh" && lang !== "en") {
          return;
        }
        this.language = lang;
        document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
        this.saveLanguage(lang);
        if (withToast) {
          this.notify("info", this.tt("msg_language"));
        }
      },
      onTabChanged(tabName) {
        if (typeof tabName === "string") {
          this.activeTab = tabName;
        }
        this.notify("info", this.tt("msg_switch_tab"));
        if (this.activeTab === "chat") {
          this.scrollMainContentTop();
          this.scrollChatToBottom();
          this.refreshRoomSummary(undefined, { silent: true }).catch(() => undefined);
        }
      },
      switchTab(tabId) {
        this.activeTab = tabId;
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
      avatarForUser(userId) {
        const key = userId && String(userId).trim() ? String(userId).trim() : "guest";
        if (!this.avatarCache[key]) {
          const hash = hashString(key);
          const index = (hash % ANIMAL_AVATAR_COUNT) + 1;
          const indexText = String(index).padStart(3, "0");
          const slug = ANIMAL_AVATAR_SLUGS[index - 1] || ANIMAL_AVATAR_SLUGS[0];
          this.avatarCache[key] = `/web/animal_avatars/avatar_${indexText}_${slug}.svg?v=${ANIMAL_AVATAR_VERSION}`;
        }
        return this.avatarCache[key];
      },
      openSecondClient() {
        window.open(`/web/?client=${Date.now()}`, "_blank", "noopener,noreferrer");
        this.notify("info", this.tt("msg_open_second"));
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
        } catch (_error) {
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
      historyStorageKey(userId) {
        const normalized = String(userId || "").trim();
        if (!normalized) {
          return null;
        }
        return `${HISTORY_KEY_PREFIX}_${encodeURIComponent(normalized)}`;
      },
      normalizeHistoryMessages(rawMap, perRoomLimit = 200) {
        const normalized = {};
        if (!rawMap || typeof rawMap !== "object") {
          return normalized;
        }
        for (const [roomId, messages] of Object.entries(rawMap)) {
          if (typeof roomId !== "string" || !Array.isArray(messages)) {
            continue;
          }
          const validMessages = messages
            .filter((item) => item && typeof item === "object" && typeof item.eventId === "string")
            .slice(-perRoomLimit);
          normalized[roomId] = validMessages;
        }
        return normalized;
      },
      scheduleHistoryPersist() {
        if (!this.session || !this.session.userId) {
          return;
        }
        if (this.historyPersistTimer) {
          window.clearTimeout(this.historyPersistTimer);
        }
        this.historyPersistTimer = window.setTimeout(() => {
          this.historyPersistTimer = null;
          this.saveHistoryCache();
        }, 120);
      },
      saveHistoryCache() {
        if (!this.session || !this.session.userId) {
          return;
        }
        const key = this.historyStorageKey(this.session.userId);
        if (!key) {
          return;
        }
        const payload = {
          user_id: this.session.userId,
          updated_at: Date.now(),
          active_room_id: this.forms.activeRoomId.trim() || null,
          room_set: this.roomSet.slice(0, 300),
          room_messages: this.normalizeHistoryMessages(this.roomMessages, 200),
          room_members: this.roomMembers || {},
          room_details: this.roomDetails || {},
          inbox_items: Array.isArray(this.inboxItems) ? this.inboxItems.slice(0, 500) : [],
          inbox_seen: this.inboxSeen || {},
        };
        try {
          window.localStorage.setItem(key, JSON.stringify(payload));
        } catch (_error) {
          return;
        }
      },
      loadHistoryCache(userId) {
        const key = this.historyStorageKey(userId);
        if (!key) {
          return null;
        }
        const raw = window.localStorage.getItem(key);
        if (!raw) {
          return null;
        }
        try {
          const payload = JSON.parse(raw);
          if (!payload || typeof payload !== "object") {
            return null;
          }
          return payload;
        } catch (_error) {
          return null;
        }
      },
      restoreHistoryCache(userId) {
        const payload = this.loadHistoryCache(userId);
        if (!payload) {
          return;
        }
        const roomSet = Array.isArray(payload.room_set)
          ? payload.room_set.filter((roomId) => typeof roomId === "string" && roomId.trim() !== "")
          : [];
        const roomMessages = this.normalizeHistoryMessages(payload.room_messages, 200);
        const roomMembers =
          payload.room_members && typeof payload.room_members === "object" ? payload.room_members : {};
        const roomDetails =
          payload.room_details && typeof payload.room_details === "object" ? payload.room_details : {};
        const inboxItems = Array.isArray(payload.inbox_items)
          ? payload.inbox_items.filter((item) => item && typeof item === "object").slice(0, 500)
          : [];
        const inboxSeen =
          payload.inbox_seen && typeof payload.inbox_seen === "object" ? payload.inbox_seen : {};
        const activeRoomId =
          typeof payload.active_room_id === "string" && payload.active_room_id.trim() !== ""
            ? payload.active_room_id.trim()
            : "";

        this.roomSet = roomSet;
        this.roomMessages = roomMessages;
        this.roomMembers = roomMembers;
        this.roomDetails = roomDetails;
        this.inboxItems = inboxItems;
        this.inboxSeen = inboxSeen;
        if (activeRoomId) {
          this.forms.activeRoomId = activeRoomId;
        }
      },
      resetInMemoryState() {
        this.roomMessages = {};
        this.roomSet = [];
        this.roomMembers = {};
        this.roomDetails = {};
        this.inboxItems = [];
        this.inboxSeen = {};
        this.forms.activeRoomId = "";
        this.forms.joinRoomId = "";
        this.forms.messageBody = "";
        this.selectedFile = null;
      },
      normalizeUsername(raw) {
        const value = String(raw || "").trim();
        if (!value) {
          return "";
        }
        if (!value.startsWith("@")) {
          return value;
        }
        const stripped = value.slice(1);
        const split = stripped.indexOf(":");
        return split >= 0 ? stripped.slice(0, split) : stripped;
      },
      normalizeUserId(raw) {
        const value = String(raw || "").trim();
        if (!value) {
          return "";
        }
        if (value.startsWith("@")) {
          return value.includes(":") ? value : `${value}:localhost`;
        }
        if (value.includes(":")) {
          return `@${value}`;
        }
        return `@${value}:localhost`;
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
      normalizeError(error) {
        if (error instanceof Error) {
          return error.message;
        }
        return String(error);
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
        } catch (_error) {
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
        } catch (_error) {
          data = { raw: text };
        }

        if (!response.ok) {
          const detail = this.formatApiDetail(data?.error ?? data?.detail ?? data);
          throw new Error(`${response.status} ${response.statusText}: ${detail}`);
        }

        return data;
      },
      parseTimestamp(originServerTs) {
        if (typeof originServerTs !== "number") {
          return { iso: "-", ms: 0 };
        }
        const date = new Date(originServerTs);
        return {
          iso: date.toLocaleString(),
          ms: date.getTime(),
        };
      },
      formatNow() {
        return new Date().toLocaleString();
      },
      extractRoomNameFromInvite(roomData, fallbackRoomId) {
        const events = roomData?.invite_state?.events || [];
        for (const event of events) {
          if (!event || event.type !== "m.room.name") {
            continue;
          }
          const name = event?.content?.name;
          if (typeof name === "string" && name.trim()) {
            return name.trim();
          }
        }
        return fallbackRoomId;
      },
      extractInviterFromInvite(roomData) {
        const events = roomData?.invite_state?.events || [];
        for (const event of events) {
          if (!event || event.type !== "m.room.member") {
            continue;
          }
          const membership = event?.content?.membership;
          if (membership === "invite" && typeof event.sender === "string") {
            return event.sender;
          }
        }
        return "unknown";
      },
      addInboxItem(item) {
        if (!item || !item.id) {
          return;
        }
        if (this.inboxSeen[item.id]) {
          return;
        }
        this.inboxSeen[item.id] = true;
        this.inboxItems = [item, ...this.inboxItems].slice(0, 500);
        this.scheduleHistoryPersist();
      },
      clearInbox() {
        this.inboxItems = [];
        this.inboxSeen = {};
        this.scheduleHistoryPersist();
        this.notify("info", this.tt("msg_inbox_cleared"));
      },
      inboxTypeLabel(type) {
        if (type === "invite") {
          return this.tt("inbox_type_invite");
        }
        if (type === "file") {
          return this.tt("inbox_type_file");
        }
        if (type === "message") {
          return this.tt("inbox_type_message");
        }
        return this.tt("inbox_type_system");
      },
      displaySender(sender) {
        if (this.session && sender === this.session.userId) {
          return this.tt("self_name");
        }
        return sender;
      },
      isSelfMessage(message) {
        return Boolean(this.session) && message.sender === this.session.userId;
      },
      isFileMessage(message) {
        if (!message || typeof message !== "object") {
          return false;
        }
        return message.msgtype === "m.file" || Boolean(message.fileMxcUri);
      },
      roomDisplayName(roomId) {
        const detail = this.roomDetails[roomId];
        if (detail && typeof detail.roomName === "string" && detail.roomName.trim() !== "") {
          return detail.roomName.trim();
        }
        return roomId;
      },
      roomMemberPreview(roomId) {
        const detail = this.roomDetails[roomId];
        const members =
          detail && Array.isArray(detail.joinedUserIds) ? detail.joinedUserIds.filter((id) => Boolean(id)) : [];
        if (members.length === 0) {
          return `${this.tt("label_member_count")}: -`;
        }
        const preview = members.slice(0, 3).join(", ");
        const extra = members.length > 3 ? ` +${members.length - 3}` : "";
        return `${this.tt("label_member_count")}: ${preview}${extra}`;
      },
      memberCountText(roomId) {
        const detail = this.roomDetails[roomId];
        if (detail && Number.isFinite(detail.joinedCount)) {
          return `${this.tt("label_member_count")}: ${detail.joinedCount}`;
        }
        const memberLegacy = this.roomMembers[roomId];
        if (memberLegacy && Number.isFinite(memberLegacy.count)) {
          return `${this.tt("label_member_count")}: ${memberLegacy.count}`;
        }
        return `${this.tt("label_member_count")}: -`;
      },
      mergeRoomId(roomId) {
        if (!roomId) {
          return;
        }
        if (!this.roomSet.includes(roomId)) {
          this.roomSet = [...this.roomSet, roomId].sort();
          this.scheduleHistoryPersist();
        }
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
          inbox_count: this.inboxItems.length,
        };
      },
      refreshStatusAndToast() {
        this.refreshSessionStatus();
        this.notify("info", this.tt("msg_status_refreshed"));
      },
      setSessionFromPayload(payload) {
        const nextUserId = typeof payload?.user_id === "string" ? payload.user_id : "";
        if (!nextUserId) {
          throw new Error("invalid_session_payload");
        }
        const currentUserId = this.session && typeof this.session.userId === "string" ? this.session.userId : "";
        if (!currentUserId || currentUserId !== nextUserId) {
          this.resetInMemoryState();
        }
        this.session = {
          homeserver: this.config.homeserverUrl.trim(),
          userId: nextUserId,
          deviceId: payload.device_id || null,
          accessToken: payload.access_token,
          nextBatch: null,
        };
        this.restoreHistoryCache(nextUserId);
        this.saveSession(this.session);
        this.refreshSessionStatus();
        this.scheduleHistoryPersist();
        this.startAutoSync();
      },
      startAutoSync() {
        this.stopAutoSync();
        if (!this.session) {
          return;
        }
        this.autoSyncEnabled = true;

        const loop = async () => {
          if (!this.autoSyncEnabled || !this.session) {
            return;
          }
          await this.syncMessages({
            silent: true,
            timeoutMs: 12000,
            showErrors: false,
          });
          if (!this.autoSyncEnabled) {
            return;
          }
          this.syncTimer = window.setTimeout(loop, 600);
        };

        loop().catch(() => undefined);
      },
      stopAutoSync() {
        this.autoSyncEnabled = false;
        if (this.syncTimer) {
          window.clearTimeout(this.syncTimer);
          this.syncTimer = null;
        }
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
          this.notify("success", `${this.tt("btn_register")} OK`);
          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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
          this.notify("success", `${this.tt("btn_login")} OK`);
          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      logoutUser() {
        this.stopAutoSync();
        this.saveHistoryCache();
        this.clearSession();
        this.session = null;
        this.resetInMemoryState();
        this.refreshSessionStatus();
        this.notify("info", this.tt("btn_logout"));
      },
      selectRoom(roomId) {
        this.forms.activeRoomId = roomId;
        this.scheduleHistoryPersist();
        this.activeTab = "chat";
        this.scrollMainContentTop();
        this.refreshRoomSummary(roomId, { silent: true }).catch(() => undefined);
        this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false }).catch(() => undefined);
        this.scrollChatToBottom();
      },
      onChatRoomChanged(roomId) {
        this.forms.activeRoomId = String(roomId || "").trim();
        this.scheduleHistoryPersist();
        this.scrollMainContentTop();
        this.refreshRoomSummary(this.forms.activeRoomId, { silent: true }).catch(() => undefined);
        this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false }).catch(() => undefined);
        this.scrollChatToBottom();
      },
      ingestSync(syncPayload) {
        const joinedRooms = syncPayload?.rooms?.join || {};
        const invitedRooms = syncPayload?.rooms?.invite || {};

        const nextMessages = { ...this.roomMessages };
        let newMessages = 0;
        let newInvites = 0;

        for (const [roomId, roomData] of Object.entries(joinedRooms)) {
          this.mergeRoomId(roomId);
          const existingMap = new Map((nextMessages[roomId] || []).map((item) => [item.eventId, item]));
          const timelineEvents = roomData?.timeline?.events || [];

          for (const event of timelineEvents) {
            if (!event || event.type !== "m.room.message") {
              continue;
            }
            const eventId = event.event_id;
            if (!eventId || existingMap.has(eventId)) {
              continue;
            }

            const content = event?.content || {};
            const msgtype = typeof content.msgtype === "string" ? content.msgtype : "m.text";
            const body = typeof content.body === "string" ? content.body : "";
            const sender = typeof event?.sender === "string" ? event.sender : "unknown";
            const ts = this.parseTimestamp(event?.origin_server_ts);
            const isFile = msgtype === "m.file";
            const fileMxcUri = typeof content.url === "string" ? content.url : "";
            const messagePreview = body.trim() || (isFile ? "file" : "(empty)");

            const message = {
              eventId,
              roomId,
              sender,
              body,
              timestamp: ts.iso,
              timestampMs: ts.ms,
              msgtype,
              fileMxcUri,
              fileName: body || "download.bin",
              fileSize: Number(content?.info?.size) || 0,
              mimeType:
                typeof content?.info?.mimetype === "string"
                  ? content.info.mimetype
                  : "application/octet-stream",
            };
            existingMap.set(eventId, message);
            newMessages += 1;

            if (this.session && sender !== this.session.userId) {
              this.addInboxItem({
                id: `${isFile ? "file" : "message"}:${eventId}`,
                type: isFile ? "file" : "message",
                roomId,
                time: ts.iso,
                line: isFile
                  ? this.ttf("inbox_file_line", {
                      room: this.roomDisplayName(roomId),
                      sender,
                      preview: messagePreview.slice(0, 60),
                    })
                  : this.ttf("inbox_message_line", {
                      room: this.roomDisplayName(roomId),
                      sender,
                      preview: messagePreview.slice(0, 60),
                    }),
                detail: message,
              });
            }
          }

          nextMessages[roomId] = Array.from(existingMap.values()).sort((a, b) => a.timestampMs - b.timestampMs);
          this.refreshRoomSummary(roomId, { silent: true }).catch(() => undefined);
        }

        for (const [roomId, roomData] of Object.entries(invitedRooms)) {
          const inviter = this.extractInviterFromInvite(roomData);
          const roomName = this.extractRoomNameFromInvite(roomData, roomId);
          const inviteId = `invite:${roomId}:${inviter}`;
          if (!this.inboxSeen[inviteId]) {
            newInvites += 1;
          }
          this.addInboxItem({
            id: inviteId,
            type: "invite",
            roomId,
            time: this.formatNow(),
            line: this.ttf("inbox_invite_line", {
              inviter,
              room: roomName,
            }),
            detail: roomData,
          });
        }

        this.roomMessages = nextMessages;
        this.scheduleHistoryPersist();
        return {
          newMessages,
          newInvites,
        };
      },
      async syncMessages(options = {}) {
        const silent = Boolean(options.silent);
        const showErrors = options.showErrors !== false;
        const timeoutMs = Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : 3000;

        if (this.syncInFlight) {
          return null;
        }

        try {
          const session = this.ensureSession();
          this.syncInFlight = true;

          const params = new URLSearchParams();
          params.set("timeout_ms", String(Math.max(0, timeoutMs)));
          if (session.nextBatch) {
            params.set("since", session.nextBatch);
          }

          const payload = await this.request(`/matrix/sync?${params.toString()}`, {
            method: "GET",
          });

          session.nextBatch = payload.next_batch || session.nextBatch;
          this.saveSession(session);

          const stats = this.ingestSync(payload);

          if (!this.forms.activeRoomId.trim() && this.roomSet.length > 0) {
            this.forms.activeRoomId = this.roomSet[0];
            this.scheduleHistoryPersist();
          }

          this.roomOutput = {
            synced_rooms: Object.keys(payload?.rooms?.join || {}).length,
            invited_rooms: Object.keys(payload?.rooms?.invite || {}).length,
            next_batch: session.nextBatch || null,
            stats,
          };

          this.refreshSessionStatus();
          if (this.forms.activeRoomId.trim()) {
            await this.refreshRoomSummary(this.forms.activeRoomId.trim(), { silent: true });
          }
          this.scrollChatToBottom();

          if (!silent) {
            this.notify(
              "success",
              this.ttf("msg_sync_ok", {
                messages: stats.newMessages,
                invites: stats.newInvites,
              })
            );
          }

          return payload;
        } catch (error) {
          if (showErrors) {
            this.notify("error", this.normalizeError(error));
          } else {
            const now = Date.now();
            if (now - this.lastSilentSyncErrorTs > 10000) {
              this.lastSilentSyncErrorTs = now;
              this.notify("warning", this.normalizeError(error));
            }
          }
          return null;
        } finally {
          this.syncInFlight = false;
        }
      },
      async createRoom() {
        try {
          this.ensureSession();
          const inviteRaw = this.forms.inviteOnCreate.trim();
          const inviteUserId = inviteRaw ? this.normalizeUserId(inviteRaw) : "";

          const body = {
            preset: "private_chat",
            name: this.forms.roomName.trim() || `room-${Date.now()}`,
            invite: inviteUserId ? [inviteUserId] : [],
          };

          const payload = await this.request("/matrix/rooms", {
            method: "POST",
            body,
          });

          this.forms.activeRoomId = payload.room_id;
          this.scheduleHistoryPersist();
          this.mergeRoomId(payload.room_id);
          this.roomOutput = payload;
          await this.refreshRoomMembers(payload.room_id, { silent: true });
          this.refreshSessionStatus();
          this.notify("success", `${this.tt("btn_create_room")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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

          const joinedRoomId = payload.room_id || roomId;
          this.forms.activeRoomId = joinedRoomId;
          this.scheduleHistoryPersist();
          this.mergeRoomId(joinedRoomId);
          this.roomOutput = payload;

          this.addInboxItem({
            id: `system:join:${joinedRoomId}:${Date.now()}`,
            type: "system",
            roomId: joinedRoomId,
            time: this.formatNow(),
            line: this.ttf("inbox_join_hint", { room: joinedRoomId }),
            detail: payload,
          });

          await this.refreshRoomMembers(joinedRoomId, { silent: true });
          this.notify("success", `${this.tt("btn_join_room")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      async inviteFriend() {
        try {
          this.ensureSession();
          const roomId = this.forms.activeRoomId.trim();
          const userId = this.normalizeUserId(this.forms.inviteUserId);
          if (!roomId || !userId) {
            throw new Error(this.tt("err_need_invite"));
          }

          const payload = await this.request(`/matrix/rooms/${encodeURIComponent(roomId)}/invite`, {
            method: "POST",
            body: { user_id: userId },
          });

          this.inviteOutput = payload;
          this.notify("success", `${this.tt("btn_invite_user")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      applyRoomSummary(roomId, payload) {
        const joinedUserIds = Array.isArray(payload?.joined_user_ids)
          ? payload.joined_user_ids.filter((item) => typeof item === "string" && item.trim() !== "")
          : [];
        const roomName =
          typeof payload?.room_name === "string" && payload.room_name.trim() !== ""
            ? payload.room_name.trim()
            : null;
        const creatorUserId =
          typeof payload?.creator_user_id === "string" && payload.creator_user_id.trim() !== ""
            ? payload.creator_user_id.trim()
            : null;

        this.roomDetails = {
          ...this.roomDetails,
          [roomId]: {
            roomId,
            roomName,
            creatorUserId,
            joinedCount: Number(payload?.joined_count) || joinedUserIds.length,
            joinedUserIds,
          },
        };
        this.roomMembers = {
          ...this.roomMembers,
          [roomId]: {
            count: Number(payload?.joined_count) || joinedUserIds.length,
            users: joinedUserIds,
          },
        };
        this.scheduleHistoryPersist();
      },
      async refreshRoomSummary(roomIdInput, options = {}) {
        const silent = Boolean(options.silent);
        try {
          this.ensureSession();
          const roomId = (roomIdInput || this.forms.activeRoomId || "").trim();
          if (!roomId) {
            if (!silent) {
              throw new Error(this.tt("err_need_room"));
            }
            return null;
          }

          const payload = await this.request(`/matrix/rooms/${encodeURIComponent(roomId)}/summary`, {
            method: "GET",
          });

          this.applyRoomSummary(roomId, payload);

          if (!silent) {
            this.notify("success", this.ttf("msg_members_ok", { count: Number(payload.joined_count) || 0 }));
          }
          return payload;
        } catch (error) {
          const message = this.normalizeError(error);
          if (message.includes("matrix_get_room_summary_forbidden")) {
            if (!silent) {
              this.notify("warning", this.tt("err_members_need_join"));
            }
            return null;
          }
          if (!silent) {
            this.notify("error", message);
          }
          return null;
        }
      },
      async refreshRoomMembers(roomIdInput, options = {}) {
        return this.refreshRoomSummary(roomIdInput, options);
      },
      async ensureRoomReady(roomIdInput, options = {}) {
        this.ensureSession();
        const autoJoin = options.autoJoin !== false;
        const roomId = (roomIdInput || this.forms.activeRoomId || "").trim();
        if (!roomId) {
          throw new Error(this.tt("err_need_room"));
        }

        const sessionUserId = this.session && typeof this.session.userId === "string" ? this.session.userId : "";
        let joined = false;
        const summary = await this.refreshRoomSummary(roomId, { silent: true });
        if (summary && Array.isArray(summary.joined_user_ids) && sessionUserId) {
          joined = summary.joined_user_ids.includes(sessionUserId);
        } else if (
          this.roomDetails[roomId] &&
          Array.isArray(this.roomDetails[roomId].joinedUserIds) &&
          sessionUserId
        ) {
          joined = this.roomDetails[roomId].joinedUserIds.includes(sessionUserId);
        }

        if (joined) {
          this.mergeRoomId(roomId);
          if (this.forms.activeRoomId.trim() !== roomId) {
            this.forms.activeRoomId = roomId;
            this.scheduleHistoryPersist();
          }
          return roomId;
        }

        if (!autoJoin) {
          throw new Error(this.tt("err_members_need_join"));
        }

        await this.request(`/matrix/rooms/${encodeURIComponent(roomId)}/join`, {
          method: "POST",
        });
        this.mergeRoomId(roomId);
        this.forms.activeRoomId = roomId;
        this.scheduleHistoryPersist();
        await this.refreshRoomSummary(roomId, { silent: true });
        this.notify("success", this.tt("msg_joined_from_invite"));
        return roomId;
      },
      async sendMessage() {
        try {
          const roomId = await this.ensureRoomReady(this.forms.activeRoomId, { autoJoin: true });
          const body = this.forms.messageBody.trim();
          if (!body) {
            throw new Error(this.tt("err_need_room_message"));
          }

          const payload = await this.request(`/matrix/rooms/${encodeURIComponent(roomId)}/messages`, {
            method: "POST",
            body: { body },
          });

          this.forms.messageBody = "";
          this.roomOutput = payload;
          this.notify("success", `${this.tt("btn_send")} OK`);
          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      onFilePicked(file) {
        const picked = file?.raw || file;
        this.selectedFile = picked || null;
        if (this.selectedFile) {
          this.notify("info", this.ttf("msg_file_selected", { name: this.selectedFile.name || "upload.bin" }));
        }
      },
      onFileExceed() {
        this.notify("warning", this.tt("err_need_file"));
      },
      async uploadFile() {
        try {
          const roomId = await this.ensureRoomReady(this.forms.activeRoomId, { autoJoin: true });
          if (!this.selectedFile) {
            throw new Error(this.tt("err_need_file"));
          }

          const payload = await this.upload(`/matrix/rooms/${encodeURIComponent(roomId)}/files`, this.selectedFile);
          this.roomOutput = payload;
          this.notify("success", `${this.tt("btn_upload")} OK`);
          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      async downloadMessageFile(message) {
        try {
          const session = this.ensureSession();
          const mxcUri = typeof message?.fileMxcUri === "string" ? message.fileMxcUri.trim() : "";
          if (!mxcUri) {
            throw new Error("missing_file_uri");
          }

          const filename =
            typeof message?.fileName === "string" && message.fileName.trim() !== ""
              ? message.fileName.trim()
              : "matrix-file.bin";
          this.notify("info", this.ttf("msg_download_started", { name: filename }));

          const base = this.config.gatewayUrl.trim().replace(/\/+$/, "");
          const params = new URLSearchParams({
            mxc_uri: mxcUri,
            filename,
          });
          const response = await fetch(`${base}/matrix/media/download?${params.toString()}`, {
            method: "GET",
            headers: {
              authorization: `Bearer ${session.accessToken}`,
            },
          });

          if (!response.ok) {
            const text = await response.text();
            let detail = text;
            try {
              const parsed = text ? JSON.parse(text) : {};
              detail = this.formatApiDetail(parsed?.error ?? parsed?.detail ?? parsed);
            } catch (_error) {
              detail = text || `${response.status} ${response.statusText}`;
            }
            throw new Error(`${response.status} ${response.statusText}: ${detail}`);
          }

          const blob = await response.blob();
          const objectUrl = window.URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = objectUrl;
          anchor.download = filename;
          anchor.style.display = "none";
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          window.URL.revokeObjectURL(objectUrl);
        } catch (error) {
          const reason = this.normalizeError(error);
          this.notify("error", `${this.tt("msg_download_failed")}: ${reason}`);
          throw error;
        }
      },
      createAgentProfile() {
        this.agentOutput = {
          status: "agent_profile_created",
          agent_id: this.forms.agentId.trim(),
          purpose: this.forms.purpose.trim(),
        };
        this.notify("info", this.tt("msg_profile_created"));
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
          this.notify("success", `${this.tt("btn_grant")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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
          this.notify("success", `${this.tt("btn_revoke")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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
          this.notify("success", `${this.tt("btn_summarize")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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
          this.notify("success", `${this.tt("btn_summarize_send")} OK`);
          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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
          this.notify("success", `${this.tt("btn_query_audit")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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
          this.notify("success", `${this.tt("btn_verify_audit")} OK`);
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      openInboxDetail(row) {
        this.selectedInboxItem = row;
        this.inboxDialogVisible = true;
      },
      openInboxFromSidebar(row) {
        this.activeTab = "inbox";
        this.openInboxDetail(row);
      },
      jumpToInboxRoom() {
        if (!this.selectedInboxItem || !this.selectedInboxItem.roomId) {
          return;
        }
        this.forms.activeRoomId = this.selectedInboxItem.roomId;
        this.scheduleHistoryPersist();
        this.activeTab = "chat";
        this.inboxDialogVisible = false;
        this.scrollMainContentTop();
        this.refreshRoomMembers(this.forms.activeRoomId, { silent: true }).catch(() => undefined);
        this.scrollChatToBottom();
      },
      async acceptInviteFromInbox() {
        try {
          this.ensureSession();
          const roomId =
            this.selectedInboxItem && typeof this.selectedInboxItem.roomId === "string"
              ? this.selectedInboxItem.roomId.trim()
              : "";
          if (!roomId) {
            throw new Error(this.tt("err_need_room"));
          }
          await this.ensureRoomReady(roomId, { autoJoin: true });
          this.activeTab = "chat";
          this.inboxDialogVisible = false;
          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
          this.scrollChatToBottom();
        } catch (error) {
          this.notify("error", this.normalizeError(error));
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

          this.notify("info", this.tt("demo_start"));

          try {
            await this.registerUser();
          } catch (_error) {
            await this.loginUser();
          }

          await this.createRoom();

          const messages = I18N[this.language]?.demo_messages || I18N.en.demo_messages;
          for (const msg of messages) {
            this.forms.messageBody = msg;
            await this.sendMessage();
          }

          await this.syncMessages({ silent: true, timeoutMs: 0, showErrors: false });
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

          this.notify("success", this.tt("demo_done"));
        } catch (error) {
          this.notify("error", this.normalizeError(error));
          throw error;
        }
      },
      scrollMainContentTop() {
        this.$nextTick(() => {
          const mainContent = this.$el?.querySelector?.(".main-tabs .el-tabs__content") || null;
          if (mainContent && typeof mainContent.scrollTop === "number") {
            mainContent.scrollTop = 0;
          }
        });
      },
      scrollChatToBottom() {
        this.$nextTick(() => {
          const feed = this.$refs.chatFeed;
          if (!feed) {
            return;
          }
          const wrap = feed.wrapRef || feed.$el?.querySelector?.(".el-scrollbar__wrap") || null;
          if (wrap && typeof wrap.scrollTop === "number") {
            wrap.scrollTop = wrap.scrollHeight;
          }
        });
      },
    },
  })
    .use(window.ElementPlus)
    .mount("#app");
})();
