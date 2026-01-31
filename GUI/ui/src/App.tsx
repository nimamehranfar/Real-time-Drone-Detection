import { useState, useEffect, useRef } from 'react'

const API_URL = 'http://localhost:8000'
const WS_URL = 'ws://localhost:8000/ws/video'

// SVG Icons
const DroneIcon = () => (
    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm-1.06 13.54L7.4 12l1.41-1.41 2.12 2.12 4.24-4.24 1.41 1.41-5.64 5.66z" />
    </svg>
)

const CameraIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
)

const FolderIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
)

const PlayIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M8 5v14l11-7z" />
    </svg>
)

const PauseIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
)

const StopIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M6 6h12v12H6z" />
    </svg>
)

const SkipBackwardIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
    </svg>
)

const SkipForwardIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
    </svg>
)

const AlertIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
    </svg>
)

const DownloadIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
)

const WifiIcon = () => (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z" />
    </svg>
)

const SettingsIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
)

interface Stats {
    fps: number
    frame: number
    detections: number
    alerts: number
    warnings: number
}

interface Settings {
    cascade_mode: string
    temporal_roi_enabled: boolean
    infer_fps: number
    show_gate: boolean
    show_troi: boolean
    show_cascade: boolean
    log_mode: string
    save_video: boolean
    save_alert_frames: boolean
    warning_cooldown: number
    alert_cooldown: number
    detect_conf: number
    cascade_trigger_conf: number
    cascade_accept_conf: number
    roi_size: number
}

export default function App() {
    const [connected, setConnected] = useState(false)
    const [streaming, setStreaming] = useState(false)
    const [alertActive, setAlertActive] = useState(false)
    const [warningActive, setWarningActive] = useState(false)
    const [stats, setStats] = useState<Stats>({ fps: 0, frame: 0, detections: 0, alerts: 0, warnings: 0 })
    const [source, setSource] = useState('')
    const [logs, setLogs] = useState<string[]>(() => {
        const saved = localStorage.getItem('droneDetectionLogs')
        return saved ? JSON.parse(saved) : []
    })
    const [showSettings, setShowSettings] = useState(false)
    const [settings, setSettings] = useState<Settings>({
        cascade_mode: 'None',
        temporal_roi_enabled: true,
        infer_fps: 5,
        show_gate: false,
        show_troi: false,
        show_cascade: false,
        log_mode: 'windows_big',
        save_video: false,
        save_alert_frames: true,
        warning_cooldown: 3.0,
        alert_cooldown: 3.0,
        detect_conf: 0.25,
        cascade_trigger_conf: 0.40,
        cascade_accept_conf: 0.40,
        roi_size: 640
    })

    useEffect(() => {
        localStorage.setItem('droneDetectionLogs', JSON.stringify(logs))
    }, [logs])

    const [youtubeUrl, setYoutubeUrl] = useState('')
    const [baseDir, setBaseDir] = useState(() => localStorage.getItem('droneBaseDir') || '')
    const [selectedFile, setSelectedFile] = useState('')
    const [esp32Addr, setEsp32Addr] = useState('http://drone-alert.local:5000')
    const [streamQuality, setStreamQuality] = useState('480p')
    const [device, setDevice] = useState('cpu')

    const imgRef = useRef<HTMLImageElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const wsRef = useRef<WebSocket | null>(null)

    useEffect(() => {
        localStorage.setItem('droneBaseDir', baseDir)
    }, [baseDir])

    const fullPath = baseDir && selectedFile ?
        `${baseDir}${baseDir.endsWith('\\') || baseDir.endsWith('/') ? '' : '\\'}${selectedFile}` : ''

    // Load settings on mount
    useEffect(() => {
        fetch(`${API_URL}/api/settings`)
            .then(res => res.json())
            .then(data => setSettings(data))
            .catch(() => { })
    }, [])

    useEffect(() => {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
            setConnected(true)
            addLog('Connected to backend')
        }

        ws.onclose = () => {
            setConnected(false)
            addLog('Disconnected')
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            if (data.type === 'frame' && imgRef.current) {
                imgRef.current.src = `data:image/jpeg;base64,${data.data}`
                setStats(data.stats)
                setAlertActive(data.alert_active)
                setWarningActive(data.warning_active || false)
            }
        }

        return () => ws.close()
    }, [])

    // Auto-connect to ESP32
    useEffect(() => {
        const autoConnect = async () => {
            try {
                await fetch(`${API_URL}/api/esp32/connect`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ address: 'http://drone-alert.local:5000' })
                })
            } catch { }
        }
        const timer = setTimeout(autoConnect, 2000)
        return () => clearTimeout(timer)
    }, [])

    const addLog = (msg: string) => {
        const time = new Date().toLocaleTimeString()
        setLogs(prev => [`[${time}] ${msg}`, ...prev.slice(0, 99)])
    }

    const exportLog = () => {
        const content = logs.join('\n')
        const blob = new Blob([content], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `drone_detection_log_${new Date().toISOString().slice(0, 10)}.txt`
        a.click()
        URL.revokeObjectURL(url)
    }

    const clearLogs = () => {
        setLogs([])
        localStorage.removeItem('droneDetectionLogs')
    }

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) setSelectedFile(file.name)
    }

    const openFile = async (path: string) => {
        if (!path) { addLog('Please enter a file path'); return }
        try {
            const res = await fetch(`${API_URL}/api/source/file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            })
            if (res.ok) {
                setSource(path.split(/[\\/]/).pop() || 'File')
                addLog('File opened')
            } else {
                addLog('Failed to open file')
            }
        } catch { addLog('Failed to open file') }
    }

    const openWebcam = async () => {
        try {
            const res = await fetch(`${API_URL}/api/source/webcam`, { method: 'POST' })
            if (res.ok) {
                setSource('Webcam')
                addLog('Webcam opened')
                startStream()
            }
        } catch { addLog('Failed to open webcam') }
    }

    const openYoutube = async () => {
        if (!youtubeUrl) return
        addLog('Downloading...')
        try {
            const res = await fetch(`${API_URL}/api/source/youtube`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: youtubeUrl })
            })
            if (res.ok) {
                setSource('YouTube')
                addLog('Video loaded')
            }
        } catch { addLog('Download failed') }
    }

    const startStream = async () => {
        await fetch(`${API_URL}/api/control/start`, { method: 'POST' })
        setStreaming(true)
        addLog('Started')
    }

    const stopStream = async () => {
        await fetch(`${API_URL}/api/control/stop`, { method: 'POST' })
        setStreaming(false)
        addLog('Stopped')
    }

    const seekVideo = async (frames: number) => {
        try {
            await fetch(`${API_URL}/api/control/seek`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frames })
            })
        } catch { }
    }

    const dismissAlert = async () => {
        await fetch(`${API_URL}/api/alert/dismiss`, { method: 'POST' })
        setAlertActive(false)
        addLog('Alert dismissed')
    }

    const updateSettings = async (updates: Partial<Settings>) => {
        const newSettings = { ...settings, ...updates }
        setSettings(newSettings)
        await fetch(`${API_URL}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        })
    }

    const connectEsp32 = async () => {
        try {
            const res = await fetch(`${API_URL}/api/esp32/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address: esp32Addr })
            })
            addLog(res.ok ? 'ESP32 connected' : 'ESP32 failed')
        } catch { addLog('ESP32 failed') }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
            {/* Header */}
            <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50 px-6 py-4">
                <div className="flex justify-between items-center max-w-7xl mx-auto">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-cyan-500/20 rounded-lg">
                            <DroneIcon />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                                Drone Detection System
                            </h1>
                            <p className="text-xs text-slate-400">Real-time AI-powered surveillance</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        {alertActive && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 border border-red-500/50 rounded-full animate-pulse">
                                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                                <span className="text-sm font-medium text-red-400">ALERT</span>
                            </div>
                        )}
                        {warningActive && !alertActive && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/20 border border-amber-500/50 rounded-full animate-pulse">
                                <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                                <span className="text-sm font-medium text-amber-400">WARNING</span>
                            </div>
                        )}
                        <button onClick={() => setShowSettings(true)} className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
                            <SettingsIcon />
                        </button>
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${connected ? 'bg-emerald-500/20 border border-emerald-500/50' : 'bg-red-500/20 border border-red-500/50'}`}>
                            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                            <span className={`text-sm ${connected ? 'text-emerald-400' : 'text-red-400'}`}>
                                {connected ? 'Connected' : 'Disconnected'}
                            </span>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-4">
                {/* Video Feed + Controls */}
                <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 overflow-hidden">
                        <div className="aspect-video bg-slate-900 flex items-center justify-center relative">
                            <img ref={imgRef} className="w-full h-full object-contain" alt="" />
                            {!streaming && (
                                <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
                                    <p className="text-slate-500">Select a source and press Play</p>
                                </div>
                            )}
                        </div>
                        <div className="px-4 py-3 bg-slate-800/80 border-t border-slate-700/50 flex items-center justify-between">
                            <span className="text-sm text-slate-400">Source: <span className="text-white">{source || 'None'}</span></span>
                            <div className="flex items-center gap-1">
                                <button onClick={() => seekVideo(-150)} className="bg-slate-700 hover:bg-slate-600 p-2 rounded-lg"><SkipBackwardIcon /></button>
                                <button onClick={streaming ? stopStream : startStream} className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${streaming ? 'bg-amber-500' : 'bg-emerald-500'}`}>
                                    {streaming ? <><PauseIcon /> Pause</> : <><PlayIcon /> Play</>}
                                </button>
                                <button onClick={() => seekVideo(150)} className="bg-slate-700 hover:bg-slate-600 p-2 rounded-lg"><SkipForwardIcon /></button>
                                <button onClick={stopStream} className="bg-slate-700 hover:bg-slate-600 p-2 rounded-lg"><StopIcon /></button>
                            </div>
                            <div className="flex items-center gap-4 text-sm">
                                <select value={streamQuality}
                                    onChange={e => { setStreamQuality(e.target.value); fetch(`${API_URL}/api/stream/quality?quality=${e.target.value}`, { method: 'POST' }) }}
                                    className="bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-xs">
                                    <option value="360p">360p</option>
                                    <option value="480p">480p</option>
                                    <option value="720p">720p</option>
                                    <option value="1080p">1080p</option>
                                </select>
                                <button
                                    onClick={async () => {
                                        const newDevice = device === 'cpu' ? 'gpu' : 'cpu';
                                        const res = await fetch(`${API_URL}/api/device?device=${newDevice}`, { method: 'POST' });
                                        if (res.ok) setDevice(newDevice);
                                    }}
                                    className={`px-2 py-1 rounded-lg text-xs font-medium ${device === 'gpu' ? 'bg-emerald-600' : 'bg-slate-600'}`}>
                                    {device.toUpperCase()}
                                </button>
                                <span className="text-slate-400">FPS: <span className="text-cyan-400 font-mono w-8 inline-block">{stats.fps}</span></span>
                                <span className="text-slate-400">Frame: <span className="text-cyan-400 font-mono w-16 inline-block">{stats.frame}</span></span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Alert + Video Source */}
                    <div className="flex flex-col gap-4">
                        <div className={`backdrop-blur-sm rounded-2xl border p-4 ${alertActive ? 'bg-red-900/30 border-red-500/50 animate-pulse' : warningActive ? 'bg-amber-900/30 border-amber-500/50' : 'bg-slate-800/50 border-slate-700/50'}`}>
                            <h3 className="text-sm font-semibold text-slate-400 mb-3">Alert Control</h3>
                            <button onClick={dismissAlert} disabled={!alertActive}
                                className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold ${alertActive ? 'bg-gradient-to-r from-red-500 to-rose-600' : 'bg-slate-700 text-slate-500 cursor-not-allowed'}`}>
                                <AlertIcon /> Dismiss Alert
                            </button>
                        </div>

                        <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-4 flex-1">
                            <h3 className="text-sm font-semibold text-slate-400 mb-3">Video Source</h3>
                            <div className="space-y-2">
                                <button onClick={openWebcam} className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 py-2 rounded-xl font-medium">
                                    <CameraIcon /> Webcam
                                </button>
                                <input value={baseDir} onChange={e => setBaseDir(e.target.value)} placeholder="Base directory"
                                    className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-2 py-1.5 text-xs" />
                                <div className="flex gap-2">
                                    <input ref={fileInputRef} type="file" accept="video/*" onChange={handleFileSelect} className="hidden" />
                                    <input value={selectedFile} readOnly placeholder="Select file..."
                                        className="flex-1 bg-slate-900/50 border border-slate-700 rounded-xl px-2 py-1.5 text-xs text-slate-400" />
                                    <button onClick={() => fileInputRef.current?.click()} className="bg-purple-600 px-3 rounded-xl"><FolderIcon /></button>
                                </div>
                                <button onClick={() => openFile(fullPath)} disabled={!fullPath}
                                    className="w-full bg-gradient-to-r from-purple-600 to-violet-600 disabled:opacity-50 py-1.5 rounded-xl text-sm font-medium">
                                    Load File
                                </button>
                                <div className="flex gap-2">
                                    <input value={youtubeUrl} onChange={e => setYoutubeUrl(e.target.value)} placeholder="YouTube URL"
                                        className="flex-1 bg-slate-900/50 border border-slate-700 rounded-xl px-2 py-1.5 text-xs" />
                                    <button onClick={openYoutube} className="bg-red-600 px-3 rounded-xl"><PlayIcon /></button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Statistics */}
                <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-4">
                        <h3 className="text-sm font-semibold text-slate-400 mb-3">Statistics</h3>
                        <div className="grid grid-cols-5 gap-3">
                            <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                                <div className="text-2xl font-bold text-cyan-400">{stats.fps}</div>
                                <div className="text-xs text-slate-500">FPS</div>
                            </div>
                            <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                                <div className="text-2xl font-bold text-cyan-400">{stats.frame}</div>
                                <div className="text-xs text-slate-500">Frames</div>
                            </div>
                            <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                                <div className="text-2xl font-bold text-emerald-400">{stats.detections}</div>
                                <div className="text-xs text-slate-500">Detections</div>
                            </div>
                            <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                                <div className="text-2xl font-bold text-amber-400">{stats.warnings}</div>
                                <div className="text-xs text-slate-500">Warnings</div>
                            </div>
                            <div className="bg-slate-900/50 rounded-xl p-3 text-center">
                                <div className="text-2xl font-bold text-red-400">{stats.alerts}</div>
                                <div className="text-xs text-slate-500">Alerts</div>
                            </div>
                        </div>
                    </div>

                    {/* ESP32 */}
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-4">
                        <h3 className="text-sm font-semibold text-slate-400 mb-3">ESP32 / Raspberry Pi</h3>
                        <div className="space-y-3">
                            <input value={esp32Addr} onChange={e => setEsp32Addr(e.target.value)}
                                className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-3 py-2 text-sm" />
                            <button onClick={connectEsp32} className="w-full flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 py-2.5 rounded-xl font-medium">
                                <WifiIcon /> Connect
                            </button>
                        </div>
                    </div>
                </div>

                {/* Detection Log */}
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-4">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-slate-400">Detection Log</h3>
                        <div className="flex gap-2">
                            <button onClick={clearLogs} className="text-xs bg-slate-700 hover:bg-red-600 px-2 py-1 rounded-lg">Clear</button>
                            <button onClick={exportLog} className="flex items-center gap-1 text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded-lg">
                                <DownloadIcon /> Export
                            </button>
                        </div>
                    </div>
                    <div className="h-32 overflow-y-auto font-mono text-xs space-y-1">
                        {logs.map((log, i) => (
                            <div key={i} className={log.includes('DRONE') ? 'text-red-400 font-semibold' : log.includes('WARNING') ? 'text-amber-400' : 'text-emerald-400 opacity-90'}>{log}</div>
                        ))}
                        {logs.length === 0 && <span className="text-slate-600">No events yet</span>}
                    </div>
                </div>
            </div>

            {/* Settings Modal */}
            {showSettings && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold">Settings</h2>
                            <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white text-2xl">&times;</button>
                        </div>

                        <div className="space-y-6">
                            {/* Detection Settings */}
                            <div>
                                <h3 className="text-sm font-semibold text-cyan-400 mb-3">Detection</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-slate-400">Cascade Mode</label>
                                        <p className="text-xs text-slate-600 mb-1">Re-verify detections with focused crop</p>
                                        <select value={settings.cascade_mode}
                                            onChange={e => updateSettings({ cascade_mode: e.target.value })}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2">
                                            <option value="None">None</option>
                                            <option value="Low-Small">Low-Small</option>
                                            <option value="All">All</option>
                                            <option value="Alert-Window">Alert-Window</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-slate-400">Inference FPS</label>
                                        <p className="text-xs text-slate-600 mb-1">Frames processed per second</p>
                                        <input type="number" min="1" max="30" value={settings.infer_fps}
                                            onChange={e => updateSettings({ infer_fps: parseInt(e.target.value) })}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" />
                                    </div>
                                    <div>
                                        <label className="text-xs text-slate-400">Detection Confidence</label>
                                        <p className="text-xs text-slate-600 mb-1">Minimum YOLO confidence</p>
                                        <input type="number" min="0.1" max="1" step="0.05" value={settings.detect_conf}
                                            onChange={e => updateSettings({ detect_conf: parseFloat(e.target.value) })}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" />
                                    </div>
                                    <div>
                                        <label className="text-xs text-slate-400">ROI Size</label>
                                        <p className="text-xs text-slate-600 mb-1">Crop size for focused inference</p>
                                        <input type="number" min="320" max="1280" step="64" value={settings.roi_size}
                                            onChange={e => updateSettings({ roi_size: parseInt(e.target.value) })}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" />
                                    </div>
                                </div>
                            </div>

                            {/* Features */}
                            <div>
                                <h3 className="text-sm font-semibold text-cyan-400 mb-3">Features</h3>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="flex items-center gap-3 cursor-pointer">
                                            <input type="checkbox" checked={settings.temporal_roi_enabled}
                                                onChange={e => updateSettings({ temporal_roi_enabled: e.target.checked })}
                                                className="w-4 h-4 rounded" />
                                            <span className="text-sm">Temporal ROI</span>
                                        </label>
                                        <p className="text-xs text-slate-600 ml-7">Track detections across frames</p>
                                    </div>
                                    <div>
                                        <label className="flex items-center gap-3 cursor-pointer">
                                            <input type="checkbox" checked={settings.save_video}
                                                onChange={e => updateSettings({ save_video: e.target.checked })}
                                                className="w-4 h-4 rounded" />
                                            <span className="text-sm">Save Video</span>
                                        </label>
                                        <p className="text-xs text-slate-600 ml-7">Record annotated output</p>
                                    </div>
                                    <div>
                                        <label className="flex items-center gap-3 cursor-pointer">
                                            <input type="checkbox" checked={settings.save_alert_frames}
                                                onChange={e => updateSettings({ save_alert_frames: e.target.checked })}
                                                className="w-4 h-4 rounded" />
                                            <span className="text-sm">Save Alert Frames</span>
                                        </label>
                                        <p className="text-xs text-slate-600 ml-7">Capture frames when alert triggers</p>
                                    </div>
                                </div>
                            </div>

                            {/* Overlays */}
                            <div>
                                <h3 className="text-sm font-semibold text-cyan-400 mb-3">Overlays</h3>
                                <div className="grid grid-cols-3 gap-3">
                                    <label className="flex items-center gap-3 cursor-pointer">
                                        <input type="checkbox" checked={settings.show_gate}
                                            onChange={e => updateSettings({ show_gate: e.target.checked })}
                                            className="w-4 h-4 rounded" />
                                        <span className="text-sm">Show Gate</span>
                                    </label>
                                    <label className="flex items-center gap-3 cursor-pointer">
                                        <input type="checkbox" checked={settings.show_troi}
                                            onChange={e => updateSettings({ show_troi: e.target.checked })}
                                            className="w-4 h-4 rounded" />
                                        <span className="text-sm">Show TROI</span>
                                    </label>
                                    <label className="flex items-center gap-3 cursor-pointer">
                                        <input type="checkbox" checked={settings.show_cascade}
                                            onChange={e => updateSettings({ show_cascade: e.target.checked })}
                                            className="w-4 h-4 rounded" />
                                        <span className="text-sm">Show Cascade</span>
                                    </label>
                                </div>
                            </div>

                            {/* Cooldowns */}
                            <div>
                                <h3 className="text-sm font-semibold text-cyan-400 mb-1">Cooldowns</h3>
                                <p className="text-xs text-slate-600 mb-3">Warning = any detection. Alert = large drone confirmed.</p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-slate-400">Warning Cooldown (s)</label>
                                        <p className="text-xs text-slate-600 mb-1">Pause after warning triggers</p>
                                        <input type="number" min="0" max="60" step="0.5" value={settings.warning_cooldown}
                                            onChange={e => updateSettings({ warning_cooldown: parseFloat(e.target.value) })}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" />
                                    </div>
                                    <div>
                                        <label className="text-xs text-slate-400">Alert Cooldown (s)</label>
                                        <p className="text-xs text-slate-600 mb-1">Pause after alert triggers</p>
                                        <input type="number" min="0" max="60" step="0.5" value={settings.alert_cooldown}
                                            onChange={e => updateSettings({ alert_cooldown: parseFloat(e.target.value) })}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2" />
                                    </div>
                                </div>
                            </div>

                            {/* Log Mode */}
                            <div>
                                <h3 className="text-sm font-semibold text-cyan-400 mb-3">Display</h3>
                                <div>
                                    <label className="text-xs text-slate-400">Log Mode</label>
                                    <select value={settings.log_mode}
                                        onChange={e => updateSettings({ log_mode: e.target.value })}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 mt-1">
                                        <option value="off">Off</option>
                                        <option value="full">Full</option>
                                        <option value="windows_big">Windows Big</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <button onClick={() => setShowSettings(false)}
                            className="w-full mt-6 bg-gradient-to-r from-cyan-500 to-blue-500 py-3 rounded-xl font-semibold">
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
