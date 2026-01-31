"""
Drone Detection GUI (Legacy Backup)
Full-featured GUI with all modules integrated.
Run this as a backup if the web interface is unavailable.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
from src import DroneDetectionSystem


class DroneDetectorGUI:
    """Main GUI Application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Drone Detection System")
        self.root.geometry("1400x800")
        self.root.configure(bg='#1a1a2e')
        
        # Initialize system
        self.system = DroneDetectionSystem()
        
        # State
        self.is_playing = False
        self.update_thread = None
        
        # Setup UI
        self._setup_styles()
        self._create_layout()
        self._create_control_panel()  # Right side controls first
        self._create_log_panel()      # Log panel second (right side)
        self._create_video_panel()    # Video panel last (takes remaining space)
        self._create_status_bar()
        
        # Callbacks
        self.system.detection_callback = self._on_detection
        self.system.alert_callback = self._on_alert
        
        # Start status update loop
        self._update_status()
        
    def _setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Header.TLabel', 
                       background='#1a1a2e', 
                       foreground='#00d4ff',
                       font=('Helvetica', 12, 'bold'))
        
        style.configure('Status.TLabel',
                       background='#16213e',
                       foreground='white',
                       font=('Helvetica', 10))
        
        style.configure('Alert.TButton',
                       background='#ff4757',
                       foreground='white')
        
    def _create_layout(self):
        """Create main layout"""
        # Header
        header = tk.Frame(self.root, bg='#16213e', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title = tk.Label(header, text="🛸 Drone Detection System", 
                        font=('Helvetica', 20, 'bold'),
                        bg='#16213e', fg='#00d4ff')
        title.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Alert indicator
        self.alert_label = tk.Label(header, text="", 
                                   font=('Helvetica', 14, 'bold'),
                                   bg='#16213e', fg='#ff4757')
        self.alert_label.pack(side=tk.RIGHT, padx=20)
        
        # Main content area - use PanedWindow for resizable panels
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, 
                                         bg='#1a1a2e', sashwidth=10,
                                         sashrelief=tk.RAISED, sashpad=2)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side: Video + Log (vertical paned)
        self.left_paned = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL,
                                         bg='#00d4ff', sashwidth=8,
                                         sashrelief=tk.RIDGE, sashpad=2)
        
        # Video container
        self.video_container = tk.Frame(self.left_paned, bg='#1a1a2e')
        self.left_paned.add(self.video_container, minsize=300, stretch='always')
        
        # Right side: Controls only (no log)
        self.right_panel = tk.Frame(self.main_paned, bg='#1a1a2e')
        
        # Add scrollable canvas for controls
        self.control_canvas = tk.Canvas(self.right_panel, bg='#1a1a2e', highlightthickness=0)
        self.control_scrollbar = tk.Scrollbar(self.right_panel, orient="vertical", command=self.control_canvas.yview)
        self.control_frame = tk.Frame(self.control_canvas, bg='#1a1a2e')
        
        self.control_canvas.configure(yscrollcommand=self.control_scrollbar.set)
        self.control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.control_canvas.create_window((0, 0), window=self.control_frame, anchor='nw')
        self.control_frame.bind('<Configure>', lambda e: self.control_canvas.configure(scrollregion=self.control_canvas.bbox('all')))
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            self.control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.control_canvas.bind_all("<MouseWheel>", on_mousewheel)
        self.control_frame.bind("<MouseWheel>", on_mousewheel)
        
        # Add to main paned window
        self.main_paned.add(self.left_paned, minsize=500, stretch='always')
        self.main_paned.add(self.right_panel, minsize=320, stretch='never')
        
        # Keep references for compatibility
        self.main_frame = self.video_container
        self.right_paned = self.left_paned  # For log panel to add itself
        
    def _create_video_panel(self):
        """Create video display panel"""
        video_frame = tk.LabelFrame(self.main_frame, text="Video Feed",
                                   bg='#1a1a2e', fg='#00d4ff',
                                   font=('Helvetica', 11, 'bold'))
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Video canvas
        self.canvas = tk.Canvas(video_frame, bg='black', 
                               width=800, height=500)
        self.canvas.pack(padx=10, pady=10)
        
        # Placeholder text
        self.canvas.create_text(400, 250, text="Select a video source",
                               fill='gray', font=('Helvetica', 16))
        
    def _create_control_panel(self):
        """Create control panel"""
        # Use the scrollable control frame from layout
        right_panel = self.control_frame
        
        # Video Source Section
        source_frame = tk.LabelFrame(right_panel, text="Video Source",
                                    bg='#1a1a2e', fg='#00d4ff',
                                    font=('Helvetica', 11, 'bold'))
        source_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # File button
        file_btn = tk.Button(source_frame, text="📁 Open Video File",
                            command=self._open_file,
                            bg='#4a69bd', fg='white',
                            font=('Helvetica', 10))
        file_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Webcam button
        webcam_btn = tk.Button(source_frame, text="📹 Open Webcam",
                              command=self._open_webcam,
                              bg='#4a69bd', fg='white',
                              font=('Helvetica', 10))
        webcam_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # YouTube section
        yt_frame = tk.Frame(source_frame, bg='#1a1a2e')
        yt_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.yt_entry = tk.Entry(yt_frame, width=25)
        self.yt_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.yt_entry.insert(0, "YouTube URL...")
        self.yt_entry.bind('<FocusIn>', lambda e: self.yt_entry.delete(0, tk.END))
        
        yt_btn = tk.Button(yt_frame, text="▶ YouTube",
                          command=self._open_youtube,
                          bg='#eb3b5a', fg='white')
        yt_btn.pack(side=tk.LEFT)
        
        # Playback Controls
        control_frame = tk.LabelFrame(right_panel, text="Playback",
                                     bg='#1a1a2e', fg='#00d4ff',
                                     font=('Helvetica', 11, 'bold'))
        control_frame.pack(fill=tk.X, pady=5, padx=5)
        
        btn_frame = tk.Frame(control_frame, bg='#1a1a2e')
        btn_frame.pack(pady=10)
        
        self.play_btn = tk.Button(btn_frame, text="▶ Play",
                                 command=self._toggle_play,
                                 bg='#20bf6b', fg='white',
                                 font=('Helvetica', 12, 'bold'),
                                 width=10)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(btn_frame, text="⬛ Stop",
                            command=self._stop,
                            bg='#ff4757', fg='white',
                            font=('Helvetica', 12, 'bold'),
                            width=10)
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Video Navigation (NEW)
        nav_frame = tk.Frame(control_frame, bg='#1a1a2e')
        nav_frame.pack(pady=5)
        
        back_10_btn = tk.Button(nav_frame, text="⏪ -10s",
                               command=lambda: self._seek_video(-300),
                               bg='#4a69bd', fg='white', width=8)
        back_10_btn.pack(side=tk.LEFT, padx=2)
        
        back_btn = tk.Button(nav_frame, text="◀ -1s",
                            command=lambda: self._seek_video(-30),
                            bg='#4a69bd', fg='white', width=6)
        back_btn.pack(side=tk.LEFT, padx=2)
        
        fwd_btn = tk.Button(nav_frame, text="+1s ▶",
                           command=lambda: self._seek_video(30),
                           bg='#4a69bd', fg='white', width=6)
        fwd_btn.pack(side=tk.LEFT, padx=2)
        
        fwd_10_btn = tk.Button(nav_frame, text="+10s ⏩",
                              command=lambda: self._seek_video(300),
                              bg='#4a69bd', fg='white', width=8)
        fwd_10_btn.pack(side=tk.LEFT, padx=2)
        
        # Post Processing Settings
        filter_frame = tk.LabelFrame(right_panel, text="Post Processing",
                                    bg='#1a1a2e', fg='#00d4ff',
                                    font=('Helvetica', 11, 'bold'))
        filter_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Confidence slider (0.20 - 1.00)
        conf_frame = tk.Frame(filter_frame, bg='#1a1a2e')
        conf_frame.pack(fill=tk.X, padx=10, pady=3)
        
        tk.Label(conf_frame, text="Confidence:", bg='#1a1a2e', fg='white',
                font=('Consolas', 9)).pack(side=tk.LEFT)
        
        self.conf_var = tk.DoubleVar(value=0.40)
        self.conf_slider = tk.Scale(
            conf_frame, from_=0.20, to=1.00, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.conf_var,
            command=self._on_conf_change,
            bg='#2d2d44', fg='#00d4ff', highlightthickness=0,
            troughcolor='#1a1a2e', length=140
        )
        self.conf_slider.pack(side=tk.LEFT, padx=5)
        
        self.conf_label = tk.Label(conf_frame, text="0.40", bg='#1a1a2e', 
                                  fg='#00ff00', font=('Consolas', 9), width=4)
        self.conf_label.pack(side=tk.LEFT)
        
        # Gap tolerance checkbox (30 frames)
        self.gap_var = tk.BooleanVar(value=True)
        self.gap_cb = tk.Checkbutton(
            filter_frame, text="Gap Tolerance (30 frames)",
            variable=self.gap_var, command=self._on_gap_change,
            bg='#1a1a2e', fg='#00ff00', selectcolor='#2d2d44',
            activebackground='#1a1a2e'
        )
        self.gap_cb.pack(anchor='w', padx=10, pady=2)
        
        # Temporal persistence checkbox
        self.temporal_var = tk.BooleanVar(value=False)
        self.temporal_cb = tk.Checkbutton(
            filter_frame, text="Temporal Persistence (10 frames)",
            variable=self.temporal_var, command=self._on_temporal_change,
            bg='#1a1a2e', fg='#00d4ff', selectcolor='#2d2d44',
            activebackground='#1a1a2e'
        )
        self.temporal_cb.pack(anchor='w', padx=10, pady=2)
        
        # Velocity/Size normalization checkbox
        self.vel_size_var = tk.BooleanVar(value=False)
        self.vel_size_cb = tk.Checkbutton(
            filter_frame, text="Velocity/Size Filter",
            variable=self.vel_size_var, command=self._on_vel_size_change,
            bg='#1a1a2e', fg='#00d4ff', selectcolor='#2d2d44',
            activebackground='#1a1a2e'
        )
        self.vel_size_cb.pack(anchor='w', padx=10, pady=2)
        
        self.filter_status = tk.Label(filter_frame,
                                     text="Tracking: 0 objects",
                                     bg='#1a1a2e', fg='#00d4ff',
                                     font=('Consolas', 9))
        self.filter_status.pack(anchor='w', padx=10, pady=5)
        
        # Alert Controls
        alert_frame = tk.LabelFrame(right_panel, text="Alert Control",
                                   bg='#1a1a2e', fg='#00d4ff',
                                   font=('Helvetica', 11, 'bold'))
        alert_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.dismiss_btn = tk.Button(alert_frame, 
                                    text="🔕 Dismiss Alert",
                                    command=self._dismiss_alert,
                                    bg='#ff4757', fg='white',
                                    font=('Helvetica', 11, 'bold'),
                                    state=tk.DISABLED)
        self.dismiss_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # ESP32 Connection
        esp_frame = tk.LabelFrame(right_panel, text="ESP32",
                                bg='#1a1a2e', fg='#00d4ff',
                                font=('Helvetica', 11, 'bold'))
        esp_frame.pack(fill=tk.X, pady=5, padx=5)
        
        esp_addr_frame = tk.Frame(esp_frame, bg='#1a1a2e')
        esp_addr_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(esp_addr_frame, text="Address:", 
                bg='#1a1a2e', fg='white').pack(side=tk.LEFT)
        
        self.esp_entry = tk.Entry(esp_addr_frame, width=20)
        self.esp_entry.pack(side=tk.LEFT, padx=5)
        self.esp_entry.insert(0, "http://192.168.1.100:5000")
        
        connect_btn = tk.Button(esp_frame, text="Connect",
                               command=self._connect_esp32,
                               bg='#4a69bd', fg='white')
        connect_btn.pack(fill=tk.X, padx=10, pady=5)
        
        self.esp_status = tk.Label(esp_frame, text="Not connected",
                                 bg='#1a1a2e', fg='gray')
        self.esp_status.pack(pady=5)
        
        # Statistics
        stats_frame = tk.LabelFrame(right_panel, text="Statistics",
                                   bg='#1a1a2e', fg='#00d4ff',
                                   font=('Helvetica', 11, 'bold'))
        stats_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.stats_labels = {}
        for stat in ['FPS', 'Frame', 'Detections', 'Alerts']:
            row = tk.Frame(stats_frame, bg='#1a1a2e')
            row.pack(fill=tk.X, padx=10, pady=2)
            
            tk.Label(row, text=f"{stat}:", 
                    bg='#1a1a2e', fg='gray', width=12, anchor='w').pack(side=tk.LEFT)
            
            lbl = tk.Label(row, text="0", 
                          bg='#1a1a2e', fg='white', anchor='w')
            lbl.pack(side=tk.LEFT)
            self.stats_labels[stat] = lbl
            
    def _create_log_panel(self):
        """Create detection log panel (resizable)"""
        # Create log frame and add to right paned window
        log_frame = tk.LabelFrame(self.right_paned, text="Detection Log",
                                 bg='#1a1a2e', fg='#00d4ff',
                                 font=('Helvetica', 11, 'bold'))
        # Smaller minsize so controls above are visible
        self.right_paned.add(log_frame, minsize=80, stretch='always')
        
        # Log listbox with scrollbar
        log_container = tk.Frame(log_frame, bg='#0f0f23')
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox
        self.log_listbox = tk.Listbox(log_container, bg='#0f0f23', fg='#00ff00',
                                     font=('Consolas', 9))
        self.log_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbar
        self.log_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_listbox.yview)
        
    def _create_status_bar(self):
        """Create status bar"""
        status_bar = tk.Frame(self.root, bg='#16213e', height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(status_bar, text="Ready",
                                    bg='#16213e', fg='white',
                                    font=('Helvetica', 9))
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.source_label = tk.Label(status_bar, text="No source",
                                    bg='#16213e', fg='gray',
                                    font=('Helvetica', 9))
        self.source_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
    # === Event Handlers ===
    
    def _open_file(self):
        """Open video file dialog"""
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov")]
        )
        
        if path:
            if self.system.video.open_file(path):
                self._log(f"Opened: {path}")
                self.source_label.config(text=f"File: {path.split('/')[-1]}")
                self.status_label.config(text="Video loaded - Press Play")
            else:
                messagebox.showerror("Error", "Failed to open video file")
                
    def _open_webcam(self):
        """Open webcam"""
        if self.system.video.open_webcam(0):
            self._log("Webcam opened")
            self.source_label.config(text="Webcam 0")
            self.status_label.config(text="Webcam active")
            # Auto-start playback for webcam
            self.system.start()
            self.is_playing = True
            self.play_btn.config(text="⏸ Pause", bg='#f39c12')
            self._start_video_loop()
        else:
            messagebox.showerror("Error", "Failed to open webcam")
            
    def _open_youtube(self):
        """Open YouTube video from URL entry field"""
        url = self.yt_entry.get().strip()
        
        # Check for valid URL
        if not url or url == "YouTube URL..." or not url.startswith("http"):
            messagebox.showwarning("Warning", "Please enter a valid YouTube URL")
            return
            
        self.status_label.config(text="Downloading YouTube video...")
        self.root.update()
        
        if self.system.video.open_youtube(url):
            self._log(f"YouTube: {url}")
            self.source_label.config(text="YouTube")
            self.status_label.config(text="YouTube ready - Press Play")
        else:
            messagebox.showerror(
                "YouTube Error", 
                "Failed to open YouTube video.\n\n"
                "For clips, ffmpeg is required.\n"
                "Install: https://ffmpeg.org/download.html"
            )
            self.status_label.config(text="YouTube failed")
            
    def _toggle_play(self):
        """Toggle play/pause"""
        if not self.system.video.is_opened():
            messagebox.showwarning("Warning", "No video source selected")
            return
            
        if self.is_playing:
            self.is_playing = False
            self.play_btn.config(text="▶ Play", bg='#20bf6b')
            self.status_label.config(text="Paused")
        else:
            self.is_playing = True
            self.play_btn.config(text="⏸ Pause", bg='#f39c12')
            self.status_label.config(text="Playing")
            self.system.start()
            self._start_video_loop()
            
    def _stop(self):
        """Stop playback"""
        self.is_playing = False
        self.system.stop()
        self.system.video.close()
        self.play_btn.config(text="▶ Play", bg='#20bf6b')
        self.status_label.config(text="Stopped")
        self.source_label.config(text="No source")
    
    def _on_conf_change(self, value):
        """Realtime confidence threshold change"""
        conf = float(value)
        self.system.filter.confirm_confidence = conf
        self.conf_label.config(text=f"{conf:.2f}")
    
    def _on_gap_change(self):
        """Toggle gap tolerance (30 frames vs 10 frames)"""
        enabled = self.gap_var.get()
        if enabled:
            self.system.filter.post_confirm_gap = 30
            self.system.filter.pre_confirm_gap = 10
        else:
            self.system.filter.post_confirm_gap = 10
            self.system.filter.pre_confirm_gap = 5
        self._log(f"Gap tolerance: {'30f' if enabled else '10f'}")
    
    def _on_temporal_change(self):
        """Toggle temporal persistence filter"""
        enabled = self.temporal_var.get()
        self.system.filter.set_temporal_persistence(enabled)
        self._log(f"Temporal persistence: {'ON' if enabled else 'OFF'}")
    
    def _on_vel_size_change(self):
        """Toggle velocity/size normalization filter"""
        enabled = self.vel_size_var.get()
        self.system.filter.set_vel_size_filter(enabled)
        self._log(f"Velocity/Size filter: {'ON' if enabled else 'OFF'}")
        
    def _start_video_loop(self):
        """Start video processing loop"""
        def loop():
            while self.is_playing and self.system.video.is_opened():
                ret, frame = self.system.video.read_frame()
                if not ret:
                    self.is_playing = False
                    self.root.after(0, lambda: self.status_label.config(text="Video ended"))
                    break
                    
                # Process frame
                annotated, confirmed = self.system.process_frame(frame)
                
                # Display
                self._display_frame(annotated)
                
                # Control speed for all sources
                fps = self.system.video.fps or 30
                time.sleep(1.0 / fps)
                    
        self.update_thread = threading.Thread(target=loop, daemon=True)
        self.update_thread.start()
        
    def _display_frame(self, frame):
        """Display frame on canvas"""
        # Resize to fit canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w > 1 and canvas_h > 1:
            h, w = frame.shape[:2]
            scale = min(canvas_w/w, canvas_h/h)
            new_w, new_h = int(w*scale), int(h*scale)
            
            frame = cv2.resize(frame, (new_w, new_h))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.canvas.delete("all")
            self.canvas.create_image(canvas_w//2, canvas_h//2, image=imgtk)
            self.canvas._image = imgtk  # Keep reference
            
    def _dismiss_alert(self):
        """Dismiss current alert"""
        self.system.acknowledge_alert()
        self.alert_label.config(text="")
        self.dismiss_btn.config(state=tk.DISABLED)
        self._log("Alert dismissed")
        
    def _connect_esp32(self):
        """Connect to ESP32"""
        address = self.esp_entry.get()
        from drone_system import CommunicationModule
        
        self.system.comm = CommunicationModule(address)
        
        if self.system.comm.test_connection():
            self.esp_status.config(text="✓ Connected", fg='#20bf6b')
            self._log(f"Connected to ESP32: {address}")
        else:
            self.esp_status.config(text="✗ Failed", fg='#ff4757')
            self._log(f"ESP32 connection failed: {self.system.comm.last_error}")
            
    def _on_detection(self, tracks):
        """Callback for detections"""
        for track in tracks:
            self._log(f"Detection: Track #{track.track_id} ({track.confidence:.2f})")
            
    def _on_alert(self, track, alert_id):
        """Callback for alerts"""
        self.alert_label.config(text="⚠ DRONE DETECTED!")
        self.dismiss_btn.config(state=tk.NORMAL)
        self._log(f"ALERT #{alert_id}: Drone confirmed!")
        
    def _log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_listbox.insert(0, f"[{timestamp}] {message}")
        
        # Keep only last 100 entries
        while self.log_listbox.size() > 100:
            self.log_listbox.delete(tk.END)
            
    def _update_status(self):
        """Update status periodically"""
        stats = self.system.stats
        
        self.stats_labels['FPS'].config(text=f"{stats['current_fps']:.1f}")
        self.stats_labels['Frame'].config(text=str(self.system.video.frame_idx))
        self.stats_labels['Detections'].config(text=str(len(self.system.confirmed_track_ids)))
        self.stats_labels['Alerts'].config(text=str(stats['total_alerts']))
        
        # Schedule next update
        self.root.after(500, self._update_status)
    
    def _seek_video(self, frames: int):
        """Seek video by specified number of frames (thread-safe)"""
        if self.system.video.cap is None:
            return
        
        # Pause playback first to avoid threading issues
        was_playing = self.is_playing
        if was_playing:
            self.is_playing = False
            time.sleep(0.15)  # Wait for video thread to pause
        
        try:
            current = self.system.video.frame_idx
            new_pos = max(0, current + frames)
            
            if self.system.video.total_frames > 0:
                new_pos = min(new_pos, self.system.video.total_frames - 1)
            
            self.system.video.cap.set(cv2.CAP_PROP_POS_FRAMES, new_pos)
            self.system.video.frame_idx = int(new_pos)
            
            # Read and display the new frame using cap directly
            ret, frame = self.system.video.cap.read()
            if ret:
                self.system.video.frame_idx += 1
                annotated, _ = self.system.process_frame(frame)
                self._display_frame(annotated)
            
            self._log(f"Seeked to frame {new_pos}")
        except Exception as e:
            self._log(f"Seek error: {e}")
        finally:
            # Resume if was playing
            if was_playing:
                self.is_playing = True
                self._start_video_loop()
    
    def _toggle_filter(self, filter_name: str):
        """Toggle an advanced filter on/off"""
        enabled = self.filter_vars[filter_name].get()
        
        # Update the advanced filters if they exist
        if hasattr(self.system, 'advanced_filters'):
            self.system.advanced_filters.set_filter(filter_name, enabled)
        
        status = "enabled" if enabled else "disabled"
        self._log(f"Filter '{filter_name}' {status}")
        
    def on_closing(self):
        """Handle window close"""
        self.is_playing = False
        self.system.stop()
        self.system.video.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = DroneDetectorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
