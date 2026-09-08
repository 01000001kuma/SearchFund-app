const { app, BrowserWindow, shell, ipcMain, session } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const isDev = !app.isPackaged;
let backendProcess = null;
let mainWindow = null;

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

function getBackendPath() {
  if (isDev) {
    return {
      cwd: path.join(__dirname, "..", ".."),
      python: path.join(__dirname, "..", "..", ".venv", "bin", "python"),
    };
  }
  return {
    cwd: path.join(process.resourcesPath, "backend"),
    python: "python3",
  };
}

function startBackend() {
  const { cwd, python } = getBackendPath();
  backendProcess = spawn(python, [
    "-m", "uvicorn", "backend.main:app",
    "--host", "127.0.0.1",
    "--port", String(BACKEND_PORT),
  ], {
    cwd,
    stdio: "pipe",
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });

  backendProcess.stderr.on("data", (data) => {
    const msg = data.toString();
    if (msg.includes("Uvicorn running on")) {
      console.log("Backend ready");
    }
  });

  backendProcess.on("error", (err) => {
    console.error("Backend spawn error:", err.message);
  });

  backendProcess.on("exit", (code) => {
    console.log("Backend exited with code:", code);
    backendProcess = null;
  });
}

function waitForBackend(timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/health`);
        if (res.ok) return resolve();
      } catch {}
      if (Date.now() - start > timeoutMs) return reject(new Error("Backend timeout"));
      setTimeout(check, 300);
    };
    check();
  });
}

function applyCSP() {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [
          "default-src 'self'; " +
          "script-src 'self'; " +
          "style-src 'self' 'unsafe-inline'; " +
          `connect-src 'self' ${BACKEND_URL}; ` +
          "img-src 'self' data:; " +
          "font-src 'self'",
        ],
      },
    });
  });
}

function createWindow() {
  console.log("Creating window...");
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "Search Fund Tool",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.on("did-finish-load", () => console.log("Page loaded OK"));
    if (process.env.DEBUG_DEVTOOLS === "1") {
      mainWindow.webContents.openDevTools({ mode: "detach" });
    }
  } else {
    applyCSP();
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.on("close", (e) => {
    console.log("Window closing, reason:", e.defaultPrevented ? "prevented" : "default");
  });
  mainWindow.on("closed", () => console.log("Window closed"));
  mainWindow.webContents.on("crashed", () => console.log("RENDERER CRASHED"));
  mainWindow.webContents.on("unresponsive", () => console.log("RENDERER UNRESPONSIVE"));

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
}

if (isDev) {
  app.disableHardwareAcceleration();
  app.commandLine.appendSwitch("disable-gpu");
  app.commandLine.appendSwitch("disable-gpu-sandbox");
  app.commandLine.appendSwitch("disable-software-rasterizer");
  app.commandLine.appendSwitch("in-process-gpu");
  app.commandLine.appendSwitch("ozone-platform=wayland");
  app.commandLine.appendSwitch("no-zygote");
}

app.whenReady().then(async () => {
  if (!isDev) {
    startBackend();
    try {
      await waitForBackend();
    } catch (err) {
      console.error("Backend failed to start:", err.message);
    }
  }
  createWindow();
});

app.on("before-quit", () => {
  stopBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

ipcMain.handle("get-api-base", () => BACKEND_URL);
ipcMain.handle("get-platform", () => process.platform);
