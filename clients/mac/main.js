const path = require("node:path");
const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = require("electron");
const log = require("electron-log/main");
const { autoUpdater } = require("electron-updater");

const DEFAULT_WEB_URL = "http://localhost:8080/web/";
const UPDATE_POLL_INTERVAL_MS = 6 * 60 * 60 * 1000;

let mainWindow = null;
let updatePollTimer = null;
const updateState = {
  status: "idle",
  message: "",
  progress: 0,
  currentVersion: app.getVersion(),
  targetVersion: null,
  checkedAt: null
};

function resolveWebUrl() {
  const raw = String(process.env.PRISM_WEB_URL || "").trim();
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }
  return DEFAULT_WEB_URL;
}

function buildOfflinePageUrl(webUrl, reason) {
  const offlinePath = path.join(__dirname, "offline.html");
  const url = new URL(`file://${offlinePath}`);
  url.searchParams.set("webUrl", webUrl);
  url.searchParams.set("reason", reason || "load_failed");
  return url.toString();
}

function parseOrigin(rawUrl) {
  try {
    return new URL(rawUrl).origin;
  } catch (_error) {
    return null;
  }
}

function isTrustedNavigation(targetUrl) {
  const safeTarget = String(targetUrl || "").trim();
  if (!safeTarget || safeTarget.startsWith("about:")) {
    return true;
  }
  const trustedOrigin = parseOrigin(resolveWebUrl());
  const targetOrigin = parseOrigin(safeTarget);
  return Boolean(trustedOrigin && targetOrigin && trustedOrigin === targetOrigin);
}

function setUpdateState(nextState) {
  Object.assign(updateState, nextState);
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("desktop:update-event", { ...updateState });
  }
}

async function loadWebApp(windowRef = mainWindow) {
  if (!windowRef || windowRef.isDestroyed()) {
    return;
  }
  const webUrl = resolveWebUrl();
  try {
    await windowRef.loadURL(webUrl);
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    await windowRef.loadURL(buildOfflinePageUrl(webUrl, reason));
  }
}

function buildAppMenu() {
  const template = [
    {
      label: app.name,
      submenu: [
        { role: "about" },
        {
          label: "Check for Updates...",
          accelerator: "CmdOrCtrl+U",
          click: () => {
            checkForUpdates(true).catch(() => undefined);
          }
        },
        { type: "separator" },
        { role: "services" },
        { type: "separator" },
        { role: "hide" },
        { role: "hideOthers" },
        { role: "unhide" },
        { type: "separator" },
        { role: "quit" }
      ]
    },
    {
      label: "File",
      submenu: [
        {
          label: "Reload Web App",
          accelerator: "CmdOrCtrl+Shift+R",
          click: () => {
            loadWebApp().catch(() => undefined);
          }
        },
        { type: "separator" },
        { role: "close" }
      ]
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" }
      ]
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        {
          role: "toggleDevTools",
          accelerator: "Alt+CommandOrControl+I"
        },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" }
      ]
    },
    {
      label: "Navigate",
      submenu: [
        {
          label: "Back",
          accelerator: "CmdOrCtrl+[",
          click: () => {
            if (mainWindow?.webContents.canGoBack()) {
              mainWindow.webContents.goBack();
            }
          }
        },
        {
          label: "Forward",
          accelerator: "CmdOrCtrl+]",
          click: () => {
            if (mainWindow?.webContents.canGoForward()) {
              mainWindow.webContents.goForward();
            }
          }
        }
      ]
    },
    {
      label: "Window",
      submenu: [{ role: "minimize" }, { role: "zoom" }, { role: "front" }]
    },
    {
      role: "help",
      submenu: [
        {
          label: "Prism Docs",
          click: () => {
            shell.openExternal("https://github.com/kuibu/prism").catch(() => undefined);
          }
        },
        {
          label: "Open Web Client in Browser",
          click: () => {
            shell.openExternal(resolveWebUrl()).catch(() => undefined);
          }
        }
      ]
    }
  ];
  return Menu.buildFromTemplate(template);
}

function createMainWindow() {
  const windowRef = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    title: "Prism Desktop",
    backgroundColor: "#F5F6F7",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  windowRef.webContents.setWindowOpenHandler(({ url }) => {
    const safeUrl = String(url || "");
    if (safeUrl.startsWith("http://") || safeUrl.startsWith("https://")) {
      shell.openExternal(safeUrl).catch(() => undefined);
    }
    return { action: "deny" };
  });

  windowRef.webContents.on(
    "will-navigate",
    (event, targetUrl) => {
      if (isTrustedNavigation(targetUrl)) {
        return;
      }
      event.preventDefault();
      if (targetUrl.startsWith("http://") || targetUrl.startsWith("https://")) {
        shell.openExternal(targetUrl).catch(() => undefined);
      }
    }
  );

  windowRef.webContents.on(
    "did-fail-load",
    async (_event, errorCode, errorDescription, validatedUrl, isMainFrame) => {
      if (!isMainFrame || !windowRef || windowRef.isDestroyed()) {
        return;
      }
      if (String(validatedUrl).startsWith("file://")) {
        return;
      }
      const reason = `${errorCode}:${errorDescription || "load_failed"}`;
      await windowRef.loadURL(buildOfflinePageUrl(resolveWebUrl(), reason));
    }
  );

  windowRef.once("ready-to-show", () => {
    windowRef.show();
  });

  windowRef.on("closed", () => {
    if (mainWindow === windowRef) {
      mainWindow = null;
    }
  });

  return windowRef;
}

async function checkForUpdates(isManual) {
  const allowDevUpdater = String(process.env.PRISM_ENABLE_DEV_UPDATES || "").trim() === "1";
  if (!app.isPackaged && !allowDevUpdater) {
    const message = "Development build: updater is disabled.";
    setUpdateState({ status: "skipped", message });
    if (isManual && mainWindow && !mainWindow.isDestroyed()) {
      await dialog.showMessageBox(mainWindow, {
        type: "info",
        buttons: ["OK"],
        title: "Auto Update",
        message
      });
    }
    return { status: "skipped", message };
  }

  try {
    await autoUpdater.checkForUpdates();
    return { status: "ok" };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    log.error("checkForUpdates failed", message);
    setUpdateState({ status: "error", message });
    if (isManual && mainWindow && !mainWindow.isDestroyed()) {
      await dialog.showMessageBox(mainWindow, {
        type: "error",
        buttons: ["OK"],
        title: "Auto Update Error",
        message: "Failed to check updates",
        detail: message
      });
    }
    return { status: "error", message };
  }
}

function initializeAutoUpdater() {
  const allowDevUpdater = String(process.env.PRISM_ENABLE_DEV_UPDATES || "").trim() === "1";
  log.initialize();
  log.transports.file.level = "info";
  autoUpdater.logger = log;
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("checking-for-update", () => {
    setUpdateState({
      status: "checking",
      message: "Checking for updates...",
      checkedAt: new Date().toISOString()
    });
  });

  autoUpdater.on("update-available", async (info) => {
    setUpdateState({
      status: "available",
      message: `Version ${info.version} is available`,
      targetVersion: info.version,
      checkedAt: new Date().toISOString()
    });
    if (!mainWindow || mainWindow.isDestroyed()) {
      return;
    }
    const result = await dialog.showMessageBox(mainWindow, {
      type: "info",
      title: "Update Available",
      message: `Prism Desktop ${info.version} is available.`,
      detail: "Download now and install after restart?",
      buttons: ["Download", "Later"],
      defaultId: 0,
      cancelId: 1
    });
    if (result.response === 0) {
      autoUpdater.downloadUpdate().catch((error) => {
        const message = error instanceof Error ? error.message : String(error);
        log.error("downloadUpdate failed", message);
        setUpdateState({ status: "error", message });
      });
    }
  });

  autoUpdater.on("update-not-available", (info) => {
    setUpdateState({
      status: "latest",
      message: "Already on the latest version.",
      targetVersion: info.version || app.getVersion(),
      checkedAt: new Date().toISOString(),
      progress: 0
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    const percent = Math.round(progress.percent || 0);
    setUpdateState({
      status: "downloading",
      progress: percent,
      message: `Downloading update (${percent}%)`
    });
  });

  autoUpdater.on("update-downloaded", async (info) => {
    setUpdateState({
      status: "downloaded",
      progress: 100,
      targetVersion: info.version,
      message: `Update ${info.version} downloaded.`
    });
    if (!mainWindow || mainWindow.isDestroyed()) {
      return;
    }
    const result = await dialog.showMessageBox(mainWindow, {
      type: "info",
      title: "Update Ready",
      message: "A new version has been downloaded.",
      detail: "Restart now to install the update?",
      buttons: ["Restart Now", "Later"],
      defaultId: 0,
      cancelId: 1
    });
    if (result.response === 0) {
      autoUpdater.quitAndInstall();
    }
  });

  autoUpdater.on("error", (error) => {
    const message = error instanceof Error ? error.message : String(error);
    log.error("autoUpdater error", message);
    setUpdateState({
      status: "error",
      message
    });
  });

  if (app.isPackaged || allowDevUpdater) {
    checkForUpdates(false).catch(() => undefined);
    updatePollTimer = setInterval(() => {
      checkForUpdates(false).catch(() => undefined);
    }, UPDATE_POLL_INTERVAL_MS);
  } else {
    setUpdateState({
      status: "skipped",
      message: "Development build: updater is disabled."
    });
  }
}

ipcMain.handle("desktop:get-config", async () => {
  return {
    webUrl: resolveWebUrl(),
    platform: process.platform,
    appVersion: app.getVersion(),
    isPackaged: app.isPackaged
  };
});

ipcMain.handle("desktop:reload-web", async () => {
  await loadWebApp();
  return { status: "ok" };
});

ipcMain.handle("desktop:open-external", async (_event, url) => {
  const safeUrl = String(url || "").trim();
  if (!safeUrl.startsWith("http://") && !safeUrl.startsWith("https://")) {
    return { status: "ignored" };
  }
  await shell.openExternal(safeUrl);
  return { status: "ok" };
});

ipcMain.handle("desktop:check-for-updates", async () => {
  return checkForUpdates(true);
});

ipcMain.handle("desktop:get-update-state", async () => {
  return { ...updateState };
});

app.whenReady().then(async () => {
  Menu.setApplicationMenu(buildAppMenu());
  mainWindow = createMainWindow();
  initializeAutoUpdater();
  await loadWebApp(mainWindow);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    mainWindow = createMainWindow();
    await loadWebApp(mainWindow);
  }
});

app.on("before-quit", () => {
  if (updatePollTimer) {
    clearInterval(updatePollTimer);
    updatePollTimer = null;
  }
});
