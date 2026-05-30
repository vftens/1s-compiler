/**
 * 1S: ERP Free Edition — Electron main process.
 *
 * Starts the Python/Flask backend on a free port,
 * then opens a BrowserWindow pointing at it.
 * Shows a splash screen while Python starts.
 */
const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const { spawn } = require('child_process');
const path  = require('path');
const http  = require('http');

const PORT   = 5174;          // default port (changes if busy)
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

let mainWindow = null;
let tray       = null;
let pyProcess  = null;

// ── Find project root (works both in dev and packaged) ────────────────────────
function projectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath);
  }
  return path.join(__dirname, '..');
}

// ── Wait until Flask responds ─────────────────────────────────────────────────
function waitForFlask(port, timeout = 15000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    function attempt() {
      if (Date.now() - start > timeout) {
        return reject(new Error('Flask startup timeout'));
      }
      const req = http.get(`http://127.0.0.1:${port}/login`, (res) => {
        if (res.statusCode < 500) resolve();
        else setTimeout(attempt, 300);
      });
      req.on('error', () => setTimeout(attempt, 300));
      req.end();
    }
    attempt();
  });
}

// ── Start Flask backend ───────────────────────────────────────────────────────
function startPython() {
  const root = projectRoot();
  const env  = { ...process.env, PYTHONPATH: root, PYTHONUTF8: '1' };

  pyProcess = spawn(PYTHON, ['-m', 'src.cli', 'serve', '--port', String(PORT)], {
    cwd: root,
    env,
    windowsHide: true,
  });

  pyProcess.stdout.on('data', d => console.log('[py]', d.toString().trim()));
  pyProcess.stderr.on('data', d => console.error('[py-err]', d.toString().trim()));

  pyProcess.on('exit', (code) => {
    console.log(`[py] exited with code ${code}`);
    pyProcess = null;
  });
}

// ── Create main window ────────────────────────────────────────────────────────
async function createWindow() {
  mainWindow = new BrowserWindow({
    width:  1280,
    height: 800,
    minWidth:  900,
    minHeight: 600,
    title: '1S: ERP Free Edition',
    icon: path.join(projectRoot(), 'gui', 'assets', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: false,   // show after load
    backgroundColor: '#0d2137',
  });

  // Show splash while waiting
  mainWindow.loadURL(`data:text/html,
    <body style="background:#0d2137;color:#fff;font-family:sans-serif;
                 display:flex;align-items:center;justify-content:center;
                 height:100vh;flex-direction:column;gap:16px">
      <div style="font-size:48px">1S</div>
      <div style="font-size:18px;opacity:.7">ERP Free Edition</div>
      <div style="font-size:13px;opacity:.4">запуск сервера…</div>
    </body>`);
  mainWindow.show();

  // Open external links in the system browser, not Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Wait for Flask, then navigate
  try {
    await waitForFlask(PORT);
    mainWindow.loadURL(`http://127.0.0.1:${PORT}/`);
  } catch (err) {
    mainWindow.loadURL(`data:text/html,
      <body style="background:#1e1e1e;color:#f48771;font-family:monospace;padding:40px">
        <h2>Ошибка запуска сервера</h2>
        <pre>${err.message}</pre>
        <p>Убедитесь, что Python установлен: <code>python --version</code></p>
      </body>`);
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Tray icon ─────────────────────────────────────────────────────────────────
function createTray() {
  const iconPath = path.join(projectRoot(), 'gui', 'assets', 'icon.png');
  const img = nativeImage.createFromPath(iconPath).resize({ width: 22, height: 22 });
  tray = new Tray(img);

  const menu = Menu.buildFromTemplate([
    { label: '1S: ERP Free Edition', enabled: false },
    { type: 'separator' },
    { label: '📂 Открыть',  click: () => mainWindow ? mainWindow.show() : createWindow() },
    { label: '✏️ Редактор', click: () => mainWindow?.loadURL(`http://127.0.0.1:${PORT}/editor`) },
    { type: 'separator' },
    { label: '✖ Закрыть',  click: () => app.quit() },
  ]);

  tray.setContextMenu(menu);
  tray.setToolTip('1S: ERP Free Edition');
  tray.on('double-click', () => mainWindow?.show());
}

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startPython();
  createWindow();
  createTray();
});

app.on('window-all-closed', () => {
  // Keep running in tray on macOS/Windows (don't quit)
  if (process.platform !== 'darwin') {
    // just hide, don't quit — app stays in tray
  }
});

app.on('activate', () => {
  if (!mainWindow) createWindow();
});

app.on('before-quit', () => {
  if (pyProcess) {
    pyProcess.kill();
    pyProcess = null;
  }
});
