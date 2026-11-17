const { app, BrowserWindow, Menu, dialog, ipcMain, shell, session } = require("electron");
const path = require("node:path");

const DEFAULT_URL = "http://127.0.0.1:5174";

function isAllowedLocalUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
  } catch {
    return false;
  }
}

function appUrl() {
  const fromArg = process.argv.find((arg) => arg.startsWith("--video-os-url="));
  const candidate = fromArg ? fromArg.replace("--video-os-url=", "") : process.env.VIDEO_OS_DESKTOP_URL || DEFAULT_URL;
  return isAllowedLocalUrl(candidate) ? candidate : DEFAULT_URL;
}

function sameOrigin(url, expectedUrl) {
  try {
    const current = new URL(url);
    const expected = new URL(expectedUrl);
    return current.origin === expected.origin;
  } catch {
    return false;
  }
}

function isPathInsideApp(targetPath) {
  try {
    const appRoot = path.resolve(__dirname, "..", "..");
    const resolved = path.resolve(targetPath);
    return resolved === appRoot || resolved.startsWith(appRoot + path.sep);
  } catch {
    return false;
  }
}

function isTrustedSender(event) {
  return Boolean(event.senderFrame?.url && sameOrigin(event.senderFrame.url, appUrl()));
}

function createWindow() {
  const targetUrl = appUrl();
  const iconPath = path.join(__dirname, "..", "public", "icon.ico");
  const window = new BrowserWindow({
    width: 1480,
    height: 980,
    minWidth: 1120,
    minHeight: 720,
    title: "Video OS",
    icon: iconPath,
    backgroundColor: "#0b0d10",
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false
    }
  });

  window.once("ready-to-show", () => window.show());
  window.loadURL(targetUrl);

  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  window.webContents.on("will-navigate", (event, url) => {
    if (!sameOrigin(url, targetUrl)) {
      event.preventDefault();
    }
  });
  window.webContents.on("will-attach-webview", (event, webPreferences) => {
    delete webPreferences.preload;
    webPreferences.nodeIntegration = false;
    event.preventDefault();
  });

  if (process.env.VIDEO_OS_ENABLE_DEVTOOLS === "1") {
    window.webContents.on("before-input-event", (event, input) => {
      if (input.key === "F12" || (input.control && input.shift && input.key.toLowerCase() === "i")) {
        window.webContents.toggleDevTools();
        event.preventDefault();
      }
    });
  }

  return window;
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => {
    callback(false);
  });
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

ipcMain.handle("video-os:pick-files", async (event) => {
  if (!isTrustedSender(event)) return [];
  const result = await dialog.showOpenDialog({
    title: "Selecionar videos",
    properties: ["openFile", "multiSelections"],
    filters: [{ name: "Videos", extensions: ["mp4", "mov", "m4v", "webm", "mkv"] }]
  });
  return result.canceled ? [] : result.filePaths;
});

ipcMain.handle("video-os:pick-folder", async (event) => {
  if (!isTrustedSender(event)) return null;
  const result = await dialog.showOpenDialog({
    title: "Selecionar pasta",
    properties: ["openDirectory"]
  });
  return result.canceled ? null : result.filePaths[0] || null;
});

ipcMain.handle("video-os:open-path", async (event, targetPath) => {
  if (!isTrustedSender(event)) return false;
  if (!targetPath || typeof targetPath !== "string") return false;
  if (!isPathInsideApp(targetPath)) return false;
  const error = await shell.openPath(targetPath);
  return !error;
});
