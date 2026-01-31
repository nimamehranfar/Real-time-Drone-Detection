const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let mainWindow;
let backendProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 800,
        minHeight: 600,
        icon: path.join(__dirname, 'icon.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        },
        autoHideMenuBar: true,
        title: 'Drone Detection System'
    });

    // Wait for backend then load frontend (try multiple ports)
    setTimeout(async () => {
        const ports = [5173, 5174, 5175];
        for (const port of ports) {
            try {
                const response = await fetch(`http://localhost:${port}`);
                if (response.ok) {
                    mainWindow.loadURL(`http://localhost:${port}`);
                    return;
                }
            } catch { }
        }
        // Fallback to 5173
        mainWindow.loadURL('http://localhost:5173');
    }, 3000);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startBackend() {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    // Project root is two levels up from ui/electron/
    const projectPath = app.isPackaged
        ? path.join(process.resourcesPath)
        : path.join(__dirname, '..', '..');

    // Kill any existing process on port 8000 first (Windows)
    if (process.platform === 'win32') {
        const { execSync } = require('child_process');
        try {
            execSync('netstat -ano | findstr :8000 | findstr LISTENING', { encoding: 'utf8' })
                .split('\n')
                .filter(line => line.trim())
                .forEach(line => {
                    const pid = line.trim().split(/\s+/).pop();
                    if (pid && !isNaN(pid)) {
                        try { execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' }); } catch { }
                    }
                });
        } catch { } // No process on port, that's fine
    }

    backendProcess = spawn(pythonPath, [
        '-m', 'uvicorn', 'wrapper.api:app', '--host', '127.0.0.1', '--port', '8000'
    ], {
        cwd: projectPath,
        shell: true
    });

    backendProcess.stdout?.on('data', (data) => {
        console.log(`Backend: ${data}`);
    });

    backendProcess.stderr?.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
    });
}

app.whenReady().then(() => {
    startBackend();
    createWindow();
});

app.on('window-all-closed', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
    app.quit();
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});
