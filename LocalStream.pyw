"""
LocalStream - Native Music Player
A high-quality music player with Spotify-like features
"""

import sys
import os
import csv
import json
import random
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, 
                             QListWidget, QListWidgetItem, QLineEdit, QSplitter,
                             QFileDialog, QMessageBox, QFrame, QInputDialog, QMenu)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QUrl, QByteArray, QPoint, QMimeData
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter, QAction, QDrag
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocalStream - Your Music Library")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create SVG icons
        self.create_icons()
        
        # Audio setup with high quality
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)
        
        # Music library
        self.music_folder = Path(__file__).parent / "AnimeOpenings"
        self.current_playlist = []
        self.current_playlist_name = None
        self.current_index = -1
        self.is_playing = False
        self.is_shuffle = False
        self.repeat_mode = 0  # 0: no repeat, 1: repeat all, 2: repeat one
        self.queue = []
        self.play_history = []
        
        # Playlists storage
        self.playlists = {}
        self.playlists_file = Path(__file__).parent / "playlists.json"
        
        # Settings storage
        self.settings_file = Path(__file__).parent / "settings.json"
        
        # Setup UI
        self.setup_ui()
        self.apply_dark_theme()
        
        # Load settings AFTER UI is created so slider exists
        self.load_settings()
        
        # Load music library first, then playlists
        self.load_music_library()
        self.load_playlists()
        self.load_spotify_playlist()
        self.refresh_playlist_sidebar()
        
        # Display Spotify playlist by default if it exists, otherwise show library
        if "Anime Openings (Spotify)" in self.playlists:
            self.current_playlist_name = "Anime Openings (Spotify)"
            self.view_label.setText("Anime Openings (Spotify)")
            self.display_songs(self.playlists["Anime Openings (Spotify)"]["songs"])
        else:
            self.current_playlist_name = None
            self.view_label.setText("Your Library")
            self.display_songs(self.all_songs)
        
        # Connect player signals
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        # Update timer for smooth UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)
    
    def create_icons(self):
        """Create SVG icons for the UI"""
        self.icons = {}
        
        # Play icon
        play_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'''
        
        # Pause icon
        pause_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>'''
        
        # Next icon
        next_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 4l10 8-10 8V4zm12 0v16h2V4h-2z"/></svg>'''
        
        # Previous icon
        prev_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 4v16l-10-8 10-8zM6 4h2v16H6V4z"/></svg>'''
        
        # Shuffle icon
        shuffle_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/></svg>'''
        
        # Repeat icon
        repeat_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>'''
        
        # Repeat one icon
        repeat_one_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4zm-6-2h2V9h-2v2h-1v2h1v4z"/></svg>'''
        
        # Volume icon
        volume_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>'''
        
        # Search icon
        search_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>'''
        
        # Home icon
        home_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>'''
        
        # Library icon
        library_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>'''
        
        # Playlist icon
        playlist_svg = '''<svg viewBox="0 0 24 24" fill="currentColor"><path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18c-.31-.11-.65-.18-1-.18-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3V8h3V6h-5z"/></svg>'''
        
        self.icons = {
            'play': self.svg_to_icon(play_svg, 20, "#000000"),
            'pause': self.svg_to_icon(pause_svg, 20, "#000000"),
            'next': self.svg_to_icon(next_svg, 20, "#b3b3b3"),
            'prev': self.svg_to_icon(prev_svg, 20, "#b3b3b3"),
            'shuffle': self.svg_to_icon(shuffle_svg, 20, "#b3b3b3"),
            'repeat': self.svg_to_icon(repeat_svg, 20, "#b3b3b3"),
            'repeat_one': self.svg_to_icon(repeat_one_svg, 20, "#b3b3b3"),
            'volume': self.svg_to_icon(volume_svg, 18, "#b3b3b3"),
            'search': self.svg_to_icon(search_svg, 18, "#b3b3b3"),
            'home': self.svg_to_icon(home_svg, 18, "#b3b3b3"),
            'library': self.svg_to_icon(library_svg, 18, "#b3b3b3"),
            'playlist': self.svg_to_icon(playlist_svg, 18, "#b3b3b3"),
        }
    
    def svg_to_icon(self, svg_string, size, color="#b3b3b3"):
        """Convert SVG string to QIcon with specified color"""
        # Replace currentColor with actual color
        svg_string = svg_string.replace('fill="currentColor"', f'fill="{color}"')
        
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer = QSvgRenderer(QByteArray(svg_string.encode()))
        renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    
    def setup_ui(self):
        """Create the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for sidebar and main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === LEFT SIDEBAR ===
        sidebar = self.create_sidebar()
        splitter.addWidget(sidebar)
        
        # === MAIN CONTENT ===
        main_content = self.create_main_content()
        splitter.addWidget(main_content)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 1150])
        
        main_layout.addWidget(splitter)
        
        # === BOTTOM PLAYER CONTROLS ===
        player_control = self.create_player_controls()
        main_layout.addWidget(player_control)
    
    def create_sidebar(self):
        """Create the left sidebar with navigation"""
        sidebar = QFrame()
        sidebar.setMaximumWidth(250)
        sidebar.setStyleSheet("background-color: #000000; border-right: 1px solid #282828;")
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 20, 10, 10)
        
        # Logo/Title
        title = QLabel("LocalStream")
        title.setStyleSheet("color: #1DB954; font-size: 28px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Home", "home", self.icons['home']),
            ("Search", "search", self.icons['search']),
            ("Library", "library", self.icons['library']),
        ]
        
        for text, key, icon in nav_items:
            btn = QPushButton(icon, f"  {text}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #b3b3b3;
                    text-align: left;
                    padding: 10px 15px;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background-color: #282828;
                }
                QPushButton:pressed {
                    background-color: #181818;
                }
            """)
            btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(lambda checked, k=key: self.switch_view(k))
            layout.addWidget(btn)
            self.nav_buttons[key] = btn
        
        layout.addSpacing(20)
        
        # Playlists section
        playlists_label = QLabel("PLAYLISTS")
        playlists_label.setStyleSheet("color: #b3b3b3; font-size: 12px; font-weight: bold; padding: 10px;")
        layout.addWidget(playlists_label)
        
        # Create playlist button
        self.create_playlist_btn = QPushButton("+ Create Playlist")
        self.create_playlist_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b3b3b3;
                text-align: left;
                padding: 8px 15px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.create_playlist_btn.clicked.connect(self.create_new_playlist)
        layout.addWidget(self.create_playlist_btn)
        
        # Import playlist button
        self.import_playlist_btn = QPushButton("📁 Import Folder")
        self.import_playlist_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b3b3b3;
                text-align: left;
                padding: 8px 15px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.import_playlist_btn.clicked.connect(self.import_playlist_from_folder)
        layout.addWidget(self.import_playlist_btn)
        
        # Playlist list
        self.playlist_list = QListWidget()
        self.playlist_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #b3b3b3;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 15px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #282828;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #282828;
                color: #ffffff;
            }
        """)
        self.playlist_list.itemClicked.connect(self.on_playlist_selected)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self.show_playlist_context_menu)
        self.playlist_list.setAcceptDrops(True)
        self.playlist_list.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.playlist_list.dragEnterEvent = self.playlist_drag_enter
        self.playlist_list.dropEvent = self.playlist_drop
        layout.addWidget(self.playlist_list)
        
        layout.addStretch()
        
        return sidebar
    
    def create_main_content(self):
        """Create the main content area"""
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #121212;")
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for songs, artists...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #242424;
                color: #ffffff;
                border: none;
                border-radius: 20px;
                padding: 12px 20px;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: #2a2a2a;
            }
        """)
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        layout.addSpacing(20)
        
        # Current view label
        self.view_label = QLabel("Your Library")
        self.view_label.setStyleSheet("color: #ffffff; font-size: 32px; font-weight: bold;")
        layout.addWidget(self.view_label)
        
        layout.addSpacing(10)
        
        # Song list with custom styling
        self.song_list = QListWidget()
        self.song_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #b3b3b3;
            }
            QListWidget::item {
                border-bottom: 1px solid #1a1a1a;
                background-color: transparent;
            }
            QListWidget::item:hover {
                background-color: #282828;
            }
            QListWidget::item:selected {
                background-color: #3e3e3e;
            }
        """)
        self.song_list.itemDoubleClicked.connect(self.on_song_item_double_clicked)
        self.song_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.song_list.customContextMenuRequested.connect(self.show_song_context_menu)
        self.song_list.setDragEnabled(True)
        self.song_list.setAcceptDrops(True)
        self.song_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.song_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.song_list.model().rowsMoved.connect(self.on_songs_reordered)
        
        layout.addWidget(self.song_list)
        
        return main_widget
    
    def create_player_controls(self):
        """Create the bottom player control bar"""
        player_widget = QFrame()
        player_widget.setFixedHeight(90)
        player_widget.setStyleSheet("background-color: #181818; border-top: 1px solid #282828;")
        
        layout = QVBoxLayout(player_widget)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Top row: Now playing info, controls, volume
        top_row = QHBoxLayout()
        
        # === NOW PLAYING INFO ===
        now_playing = QHBoxLayout()
        self.album_art = QLabel()
        self.album_art.setFixedSize(56, 56)
        self.album_art.setStyleSheet("background-color: #282828; border-radius: 4px;")
        self.album_art.setScaledContents(True)
        now_playing.addWidget(self.album_art)
        
        track_info = QVBoxLayout()
        track_info.setSpacing(2)
        self.track_title = QLabel("No track playing")
        self.track_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        self.track_artist = QLabel("")
        self.track_artist.setStyleSheet("color: #b3b3b3; font-size: 12px;")
        track_info.addWidget(self.track_title)
        track_info.addWidget(self.track_artist)
        now_playing.addLayout(track_info)
        now_playing.addStretch()
        
        top_row.addLayout(now_playing, 1)
        
        # === PLAYER CONTROLS ===
        controls = QHBoxLayout()
        controls.setSpacing(15)
        
        # Control buttons
        self.shuffle_btn = QPushButton(self.icons['shuffle'], "")
        self.prev_btn = QPushButton(self.icons['prev'], "")
        self.play_btn = QPushButton(self.icons['play'], "")
        self.next_btn = QPushButton(self.icons['next'], "")
        self.repeat_btn = QPushButton(self.icons['repeat'], "")
        
        control_buttons = [self.shuffle_btn, self.prev_btn, self.play_btn, 
                          self.next_btn, self.repeat_btn]
        
        for btn in control_buttons:
            btn.setFixedSize(36, 36)
            btn.setIconSize(QSize(20, 20))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #b3b3b3;
                    border: none;
                    border-radius: 18px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background-color: #282828;
                }
                QPushButton:pressed {
                    background-color: #3e3e3e;
                }
            """)
            controls.addWidget(btn)
        
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: none;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #1DB954;
            }
        """)
        self.play_btn.setIconSize(QSize(18, 18))
        
        # Connect control signals
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)
        self.prev_btn.clicked.connect(self.play_previous)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.play_next)
        self.repeat_btn.clicked.connect(self.toggle_repeat)
        
        top_row.addLayout(controls, 1)
        
        # === VOLUME CONTROL ===
        volume_layout = QHBoxLayout()
        volume_layout.addStretch()
        volume_icon = QLabel()
        volume_icon.setPixmap(self.icons['volume'].pixmap(18, 18))
        volume_layout.addWidget(volume_icon)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #4d4d4d;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #1DB954;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 2px;
            }
        """)
        volume_layout.addWidget(self.volume_slider)
        
        top_row.addLayout(volume_layout, 1)
        layout.addLayout(top_row)
        
        # === PROGRESS BAR ===
        progress_layout = QHBoxLayout()
        
        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet("color: #b3b3b3; font-size: 11px;")
        self.time_label.setFixedWidth(40)
        progress_layout.addWidget(self.time_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderMoved.connect(self.on_seek)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #4d4d4d;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #1DB954;
            }
            QSlider::sub-page:horizontal {
                background: #ffffff;
                border-radius: 2px;
            }
        """)
        progress_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet("color: #b3b3b3; font-size: 11px;")
        self.duration_label.setFixedWidth(40)
        progress_layout.addWidget(self.duration_label)
        
        layout.addLayout(progress_layout)
        
        return player_widget
    
    def apply_dark_theme(self):
        """Apply Spotify-like dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #000000;
            }
            QScrollBar:vertical {
                background: #121212;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #4d4d4d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5d5d5d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
    
    def load_music_library(self):
        """Scan and load all music files from the folder"""
        self.all_songs = []
        
        if not self.music_folder.exists():
            QMessageBox.warning(self, "Music Folder Not Found", 
                              f"Could not find folder: {self.music_folder}")
            return
        
        # Scan for MP3 files
        for file in self.music_folder.glob("*.mp3"):
            try:
                audio = MP3(file)
                duration = int(audio.info.length)
                
                # Try to get metadata
                title = file.stem
                artist = "Unknown Artist"
                album = "Unknown Album"
                
                if audio.tags:
                    title = str(audio.tags.get("TIT2", title))
                    artist = str(audio.tags.get("TPE1", artist))
                    album = str(audio.tags.get("TALB", album))
                
                # Extract album art
                album_art_data = None
                try:
                    if audio.tags:
                        for tag in audio.tags.values():
                            if hasattr(tag, 'mime') and tag.mime.startswith('image/'):
                                album_art_data = tag.data
                                break
                except:
                    pass
                
                song_info = {
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration": duration,
                    "path": str(file),
                    "filename": file.name,
                    "album_art": album_art_data
                }
                self.all_songs.append(song_info)
            except Exception as e:
                print(f"Error loading {file.name}: {e}")
        
        self.all_songs.sort(key=lambda x: x["title"])
        # Don't auto-display here - let main init handle it
    
    def load_spotify_playlist(self):
        """Load the Spotify playlist from CSV and match with local files"""
        csv_path = Path(__file__).parent / "AnimeOpenings.csv"
        
        if not csv_path.exists():
            return
        
        # Check if already loaded
        if "Anime Openings (Spotify)" in self.playlists:
            return
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                spotify_tracks = list(reader)
            
            # Create lookup by path for fast duplicate checking
            matched_paths = set()
            matched_songs = []
            unmatched_tracks = []
            
            # Manual mappings for files with missing metadata or romanization issues
            manual_mappings = {
                "境界線": "86 EIGHTY-SIX - Opening 2 ｜ Kyoukaisen [0U6JUTWas8c].mp3",
                "太陽が昇らない世界 - A World Where the Sun Never Rises": "Aimer「太陽が昇らない世界」Music Video（『劇場版「鬼滅の刃」無限城編 』第一章 猗窩座再来』 主題歌） [DJOf0XtVpkI].mp3"
            }
            
            for track in spotify_tracks:
                track_name = track.get("Track Name", "")
                artist_name = track.get("Artist Name(s)", "")
                album_name = track.get("Album Name", "")
                
                # Check manual mappings first
                if track_name in manual_mappings:
                    target_filename = manual_mappings[track_name]
                    for song in self.all_songs:
                        if song["filename"] == target_filename and song["path"] not in matched_paths:
                            matched_paths.add(song["path"])
                            matched_songs.append(song)
                            print(f"✓ Manual match: '{track_name}' -> '{target_filename}'")
                            break
                    continue
                
                # Try to find best match with local files
                best_match = None
                best_score = 0
                
                for song in self.all_songs:
                    # Skip if already matched
                    if song["path"] in matched_paths:
                        continue
                    
                    # Calculate match score with multiple strategies
                    score = 0
                    
                    # Clean up track name - handle both ASCII and fullwidth characters
                    track_lower = track_name.lower()
                    # Remove special characters (both ASCII and fullwidth versions)
                    for char in ['-', '_', '(', ')', '[', ']', '.mp3', ',', '|', ':', '!', '?', '"', "'", 
                                '＂', '（', '）', '｜', '：', '！', '？', '～', '〜', '/', '＃']:
                        track_lower = track_lower.replace(char, ' ')
                    track_words = set(track_lower.split())
                    
                    # Check if metadata exists (for files with missing ID3 tags)
                    has_metadata = bool(song["title"].strip() and song["artist"].strip())
                    
                    # Strategy 1: Title match from metadata (HIGHEST PRIORITY when available)
                    title_lower = song["title"].lower()
                    for char in ['-', '_', '(', ')', '[', ']', ',', '|', ':', '!', '?', '"', "'",
                                '＂', '（', '）', '｜', '：', '！', '？', '～', '〜', '/', '＃']:
                        title_lower = title_lower.replace(char, ' ')
                    
                    title_words = set(title_lower.split())
                    if track_words and title_words and has_metadata:
                        title_overlap = len(track_words & title_words) / len(track_words)
                        score += title_overlap * 15
                        
                        # Bonus for very close matches
                        if title_overlap > 0.8:
                            score += 5
                    
                    # Strategy 2: Filename match (CRITICAL for files without metadata)
                    filename_lower = song["filename"].lower()
                    for char in ['-', '_', '(', ')', '[', ']', '.mp3', ',', '|', ':', '!', '?', '"', "'",
                                '＂', '（', '）', '｜', '：', '！', '？', '～', '〜', '/', '＃']:
                        filename_lower = filename_lower.replace(char, ' ')
                    
                    filename_words = set(filename_lower.split())
                    if track_words and filename_words:
                        word_overlap = len(track_words & filename_words) / len(track_words)
                        # Give MUCH higher weight to filename if no metadata
                        filename_weight = 20 if not has_metadata else 8
                        score += word_overlap * filename_weight
                    
                    # Strategy 3: Artist match (only if metadata exists)
                    if has_metadata:
                        artist_lower = song["artist"].lower()
                        csv_artist_lower = artist_name.lower()
                        
                        # Handle multiple artists (separated by ; or ,)
                        csv_artists = [a.strip() for a in csv_artist_lower.replace(';', ',').split(',')]
                        
                        for csv_artist in csv_artists:
                            if len(csv_artist) > 2:
                                if csv_artist in artist_lower or artist_lower in csv_artist:
                                    score += 5
                                    break
                    
                    # Strategy 4: Album match bonus (only if metadata exists)
                    if has_metadata:
                        album_lower = song["album"].lower()
                        if album_name and len(album_name) > 3:
                            if album_name.lower() in album_lower or album_lower in album_name.lower():
                                score += 3
                    
                    # Strategy 5: Check if track name is substring (good for files without metadata)
                    if len(track_lower) > 5:
                        # For files without metadata, check filename more thoroughly
                        check_target = filename_lower if not has_metadata else filename_lower
                        if track_lower in check_target:
                            substring_bonus = 8 if not has_metadata else 3
                            score += substring_bonus
                    
                    if score > best_score:
                        best_score = score
                        best_match = song
                
                # Add if we found a reasonable match
                if best_match and best_score >= 8:  # High confidence match
                    matched_paths.add(best_match["path"])
                    matched_songs.append(best_match)
                elif best_match and best_score >= 3.5:  # Medium confidence - check more carefully
                    # For lower scores, require either good title match OR artist match
                    track_lower = track_name.lower()
                    title_lower = best_match["title"].lower()
                    artist_lower = best_match["artist"].lower()
                    csv_artist_lower = artist_name.lower()
                    
                    # Clean for comparison
                    for char in ['-', '_', '(', ')', '[', ']', ',', '|', ':', '!', '?', '.']:
                        track_lower = track_lower.replace(char, ' ')
                        title_lower = title_lower.replace(char, ' ')
                    
                    track_words = set(track_lower.split())
                    title_words = set(title_lower.split())
                    
                    # Accept if at least 50% of track words are in title
                    if track_words and title_words:
                        overlap = len(track_words & title_words) / len(track_words)
                        if overlap >= 0.5:  # 50% word overlap
                            matched_paths.add(best_match["path"])
                            matched_songs.append(best_match)
                            print(f"✓ Medium match: '{track_name}' -> '{best_match['title']}' (score: {best_score:.1f})")
                            continue
                    
                    # Or if artist matches well
                    csv_artists = [a.strip() for a in csv_artist_lower.replace(';', ',').split(',')]
                    for csv_artist in csv_artists:
                        if len(csv_artist) > 2 and csv_artist in artist_lower:
                            matched_paths.add(best_match["path"])
                            matched_songs.append(best_match)
                            print(f"✓ Artist match: '{track_name}' by '{artist_name}' -> '{best_match['filename']}' (score: {best_score:.1f})")
                            break
                    else:
                        # Didn't match, add to unmatched
                        unmatched_tracks.append({
                            "track": track_name,
                            "artist": artist_name,
                            "best_score": best_score,
                            "best_match": best_match["filename"] if best_match else "None",
                            "best_match_title": best_match["title"] if best_match else "None"
                        })
                else:
                    # Track unmatched for reporting
                    unmatched_tracks.append({
                        "track": track_name,
                        "artist": artist_name,
                        "best_score": best_score,
                        "best_match": best_match["filename"] if best_match else "None",
                        "best_match_title": best_match["title"] if best_match else "None"
                    })
            
            # Show unmatched tracks
            if unmatched_tracks:
                print("\n=== UNMATCHED TRACKS ===")
                for um in unmatched_tracks:
                    print(f"❌ {um['track']} - {um['artist']}")
                    print(f"   Best: {um['best_match']} | Title: {um['best_match_title']} (score: {um['best_score']:.1f})")
                print("========================\n")
            
            # Add to playlists
            if matched_songs:
                self.playlists["Anime Openings (Spotify)"] = {
                    "songs": matched_songs,
                    "created": "imported",
                    "persistent": True
                }
                self.save_playlists()
                
                # Show summary
                unmatched = len(spotify_tracks) - len(matched_songs)
                unused_local = len(self.all_songs) - len(matched_paths)
                
                return
                if unmatched > 0 or unused_local > 0:
                    msg = f"Playlist imported:\n\n"
                    msg += f"✓ Matched: {len(matched_songs)} songs\n"
                    if unmatched > 0:
                        msg += f"⚠ CSV tracks not matched: {unmatched}\n"
                    if unused_local > 0:
                        msg += f"⚠ Local files not in playlist: {unused_local}\n\n"
                    msg += f"Check 'Your Library' to see all {len(self.all_songs)} local songs."
                    
                    QMessageBox.information(self, "Spotify Playlist Imported", msg)
            
        except Exception as e:
            print(f"Error loading Spotify playlist: {e}")
    
    def load_playlists(self):
        """Load playlists from JSON file"""
        if not self.playlists_file.exists():
            return
        
        try:
            with open(self.playlists_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create a lookup dictionary for faster matching
            songs_by_path = {song["path"]: song for song in self.all_songs}
            
            # Reconstruct playlists with actual song objects
            for name, playlist_data in data.items():
                song_paths = playlist_data.get("song_paths", [])
                songs = []
                
                # Match paths to loaded songs - PRESERVE ORDER
                for path in song_paths:
                    if path in songs_by_path:
                        songs.append(songs_by_path[path])
                
                if songs:
                    self.playlists[name] = {
                        "songs": songs,
                        "created": playlist_data.get("created", "unknown"),
                        "persistent": playlist_data.get("persistent", False)
                    }
        except Exception as e:
            print(f"Error loading playlists: {e}")
    
    def save_playlists(self):
        """Save playlists to JSON file"""
        try:
            data = {}
            for name, playlist in self.playlists.items():
                # Save only song paths (lightweight)
                data[name] = {
                    "song_paths": [song["path"] for song in playlist["songs"]],
                    "created": playlist.get("created", "unknown"),
                    "persistent": playlist.get("persistent", False)
                }
            
            with open(self.playlists_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving playlists: {e}")
    
    def refresh_playlist_sidebar(self):
        """Refresh the playlist list in sidebar"""
        self.playlist_list.clear()
        
        for name in sorted(self.playlists.keys()):
            playlist_item = QListWidgetItem(self.icons['playlist'], name)
            self.playlist_list.addItem(playlist_item)
    
    def create_new_playlist(self):
        """Create a new empty playlist"""
        name, ok = QInputDialog.getText(self, "Create Playlist", "Playlist name:")
        
        if ok and name:
            if name in self.playlists:
                QMessageBox.warning(self, "Playlist Exists", f"A playlist named '{name}' already exists.")
                return
            
            self.playlists[name] = {
                "songs": [],
                "created": "user",
                "persistent": False
            }
            self.save_playlists()
            self.refresh_playlist_sidebar()
            QMessageBox.information(self, "Playlist Created", f"Playlist '{name}' created successfully!")
    
    def import_playlist_from_folder(self):
        """Import a playlist from a folder containing MP3 files"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with MP3 Files")
        
        if not folder:
            return
        
        folder_path = Path(folder)
        folder_name = folder_path.name
        
        # Ask for playlist name
        name, ok = QInputDialog.getText(self, "Import Playlist", 
                                       "Playlist name:", text=folder_name)
        
        if not ok or not name:
            return
        
        if name in self.playlists:
            reply = QMessageBox.question(self, "Playlist Exists", 
                                        f"A playlist named '{name}' already exists. Replace it?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Scan folder for MP3 files
        songs = []
        mp3_files = list(folder_path.glob("*.mp3"))
        
        for file in mp3_files:
            try:
                audio = MP3(file)
                duration = int(audio.info.length)
                
                title = file.stem
                artist = "Unknown Artist"
                album = "Unknown Album"
                
                if audio.tags:
                    title = str(audio.tags.get("TIT2", title))
                    artist = str(audio.tags.get("TPE1", artist))
                    album = str(audio.tags.get("TALB", album))
                
                # Extract album art
                album_art_data = None
                try:
                    if audio.tags:
                        for tag in audio.tags.values():
                            if hasattr(tag, 'mime') and tag.mime.startswith('image/'):
                                album_art_data = tag.data
                                break
                except:
                    pass
                
                song_info = {
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration": duration,
                    "path": str(file),
                    "filename": file.name,
                    "album_art": album_art_data
                }
                songs.append(song_info)
            except Exception as e:
                print(f"Error loading {file.name}: {e}")
        
        if not songs:
            QMessageBox.warning(self, "No Songs Found", "No MP3 files found in the selected folder.")
            return
        
        # Sort by filename
        songs.sort(key=lambda x: x["filename"])
        
        # Add to library if not already there
        for song in songs:
            if song["path"] not in [s["path"] for s in self.all_songs]:
                self.all_songs.append(song)
        
        # Create playlist
        self.playlists[name] = {
            "songs": songs,
            "created": "imported",
            "persistent": False
        }
        self.save_playlists()
        self.refresh_playlist_sidebar()
        
        QMessageBox.information(self, "Import Complete", 
                               f"Imported {len(songs)} songs into playlist '{name}'!")
    
    def playlist_drag_enter(self, event):
        """Handle drag enter event for playlist list"""
        if event.mimeData().hasFormat("application/x-song-index"):
            event.acceptProposedAction()
    
    def playlist_drop(self, event):
        """Handle drop event on playlist list"""
        if not event.mimeData().hasFormat("application/x-song-index"):
            return
        
        # Get the playlist item at drop position
        item = self.playlist_list.itemAt(event.position().toPoint())
        if not item:
            return
        
        playlist_name = item.text()
        
        # Get the song index being dragged
        song_index = int(event.mimeData().data("application/x-song-index").data().decode())
        if song_index < 0 or song_index >= len(self.current_playlist):
            return
        
        song = self.current_playlist[song_index]
        
        # Add to target playlist
        self.add_song_to_playlist(playlist_name, song)
        event.acceptProposedAction()
    
    def on_songs_reordered(self):
        """Handle when songs are reordered via drag and drop"""
        if not self.current_playlist_name or self.current_playlist_name not in self.playlists:
            return
        
        playlist = self.playlists[self.current_playlist_name]
        if playlist.get("persistent", False):
            QMessageBox.warning(self, "Cannot Reorder", "This is a persistent playlist and cannot be reordered.")
            # Refresh to undo the move
            self.display_songs(playlist["songs"])
            return
        
        # Rebuild the playlist order based on current list widget order
        new_order = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            original_index = item.data(Qt.ItemDataRole.UserRole)
            if original_index < len(self.current_playlist):
                new_order.append(self.current_playlist[original_index])
        
        # Update playlist
        playlist["songs"] = new_order
        self.current_playlist = new_order
        self.save_playlists()
        
        # Update indices in list items
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            item.setData(Qt.ItemDataRole.UserRole, i)
    
    def show_playlist_context_menu(self, position: QPoint):
        """Show context menu for playlist"""
        item = self.playlist_list.itemAt(position)
        if not item:
            return
        
        playlist_name = item.text()
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #282828;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #3e3e3e;
            }
        """)
        
        # Only allow deletion of non-persistent playlists
        if not self.playlists[playlist_name].get("persistent", False):
            delete_action = QAction("Delete Playlist", self)
            delete_action.triggered.connect(lambda: self.delete_playlist(playlist_name))
            menu.addAction(delete_action)
        
        rename_action = QAction("Rename Playlist", self)
        rename_action.triggered.connect(lambda: self.rename_playlist(playlist_name))
        menu.addAction(rename_action)
        
        menu.exec(self.playlist_list.mapToGlobal(position))
    
    def delete_playlist(self, name):
        """Delete a playlist"""
        reply = QMessageBox.question(self, "Delete Playlist", 
                                     f"Are you sure you want to delete '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.playlists[name]
            self.save_playlists()
            self.refresh_playlist_sidebar()
            
            # If currently viewing, switch to library
            if self.current_playlist_name == name:
                self.view_label.setText("Your Library")
                self.display_songs(self.all_songs)
    
    def rename_playlist(self, old_name):
        """Rename a playlist"""
        new_name, ok = QInputDialog.getText(self, "Rename Playlist", 
                                            "New name:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            if new_name in self.playlists:
                QMessageBox.warning(self, "Playlist Exists", 
                                   f"A playlist named '{new_name}' already exists.")
                return
            
            # Rename
            self.playlists[new_name] = self.playlists.pop(old_name)
            self.save_playlists()
            self.refresh_playlist_sidebar()
            
            # Update current view if needed
            if self.current_playlist_name == old_name:
                self.current_playlist_name = new_name
                self.view_label.setText(new_name)
    
    def show_song_context_menu(self, position: QPoint):
        """Show context menu for song"""
        item = self.song_list.itemAt(position)
        if not item:
            return
        
        index = item.data(Qt.ItemDataRole.UserRole)
        song = self.current_playlist[index]
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #282828;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #3e3e3e;
            }
            QMenu::separator {
                height: 1px;
                background: #3e3e3e;
                margin: 5px 0;
            }
        """)
        
        play_action = QAction("Play", self)
        play_action.triggered.connect(lambda: self.play_song(index))
        menu.addAction(play_action)
        
        play_next_action = QAction("Play Next", self)
        play_next_action.triggered.connect(lambda: self.add_to_queue(index, next=True))
        menu.addAction(play_next_action)
        
        add_queue_action = QAction("Add to Queue", self)
        add_queue_action.triggered.connect(lambda: self.add_to_queue(index))
        menu.addAction(add_queue_action)
        
        menu.addSeparator()
        
        # Add to playlist submenu
        add_to_menu = QMenu("Add to Playlist", self)
        add_to_menu.setStyleSheet(menu.styleSheet())
        
        for playlist_name in sorted(self.playlists.keys()):
            action = QAction(playlist_name, self)
            action.triggered.connect(lambda checked, name=playlist_name, s=song: self.add_song_to_playlist(name, s))
            add_to_menu.addAction(action)
        
        menu.addMenu(add_to_menu)
        
        # Remove from playlist if in a user playlist
        if self.current_playlist_name and self.current_playlist_name in self.playlists:
            if not self.playlists[self.current_playlist_name].get("persistent", False):
                menu.addSeparator()
                remove_action = QAction("Remove from Playlist", self)
                remove_action.triggered.connect(lambda: self.remove_song_from_playlist(index))
                menu.addAction(remove_action)
        
        menu.addSeparator()
        
        # Show file info
        info_action = QAction("Song Info", self)
        info_action.triggered.connect(lambda: self.show_song_info(song))
        menu.addAction(info_action)
        
        menu.exec(self.song_list.mapToGlobal(position))
    
    def add_to_queue(self, index, next=False):
        """Add song to play queue"""
        if next:
            self.queue.insert(0, index)
            QMessageBox.information(self, "Added to Queue", "Song will play next!")
        else:
            self.queue.append(index)
            QMessageBox.information(self, "Added to Queue", f"Song added to queue ({len(self.queue)} songs)")
    
    def show_song_info(self, song):
        """Show detailed song information"""
        info = f"""
<b>Title:</b> {song['title']}<br>
<b>Artist:</b> {song['artist']}<br>
<b>Album:</b> {song['album']}<br>
<b>Duration:</b> {self.format_time(song['duration'])}<br>
<b>File:</b> {song['filename']}<br>
<b>Path:</b> {song['path']}
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Song Information")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(info)
        msg.exec()
    
    def add_song_to_playlist(self, playlist_name, song):
        """Add a song to a playlist"""
        if song not in self.playlists[playlist_name]["songs"]:
            self.playlists[playlist_name]["songs"].append(song)
            self.save_playlists()
            QMessageBox.information(self, "Added", f"Added to '{playlist_name}'")
        else:
            QMessageBox.information(self, "Already in Playlist", f"Song already in '{playlist_name}'")
    
    def remove_song_from_playlist(self, index):
        """Remove a song from current playlist"""
        if not self.current_playlist_name or self.current_playlist_name not in self.playlists:
            return
        
        playlist = self.playlists[self.current_playlist_name]
        if playlist.get("persistent", False):
            QMessageBox.warning(self, "Cannot Modify", "This is a persistent playlist.")
            return
        
        song = self.current_playlist[index]
        playlist["songs"].remove(song)
        self.save_playlists()
        
        # Refresh view
        self.display_songs(playlist["songs"])
        self.current_playlist_name = self.current_playlist_name
    
    def fuzzy_match(self, str1, str2):
        """Simple fuzzy matching for song names"""
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        # Remove common characters
        for char in ['-', '_', '(', ')', '[', ']', '.mp3', ',']:
            str1 = str1.replace(char, ' ')
            str2 = str2.replace(char, ' ')
        
        # Check if most words match
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return False
        
        # If at least 60% of words match
        matches = len(words1.intersection(words2))
        return matches / max(len(words1), len(words2)) > 0.4
    
    def display_songs(self, songs):
        """Display songs in the list"""
        self.current_playlist = songs
        self.song_list.clear()
        
        for i, song in enumerate(songs):
            item = QListWidgetItem()
            
            # Create custom widget for song item
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(12)
            
            # Album art thumbnail
            art_label = QLabel()
            art_label.setFixedSize(48, 48)
            
            if song.get("album_art"):
                pixmap = QPixmap()
                pixmap.loadFromData(song["album_art"])
                art_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, 
                                                  Qt.TransformationMode.SmoothTransformation))
            else:
                # Default album art
                art_label.setStyleSheet("background-color: #282828; border-radius: 4px;")
            
            layout.addWidget(art_label)
            
            # Track info
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            # Track number and title
            title_layout = QHBoxLayout()
            title_layout.setSpacing(8)
            
            track_num = QLabel(f"{i + 1:02d}")
            track_num.setStyleSheet("color: #b3b3b3; font-size: 12px; min-width: 25px;")
            title_layout.addWidget(track_num)
            
            title_label = QLabel(song["title"])
            title_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            
            info_layout.addLayout(title_layout)
            
            # Artist and duration
            subtitle_label = QLabel(f"{song['artist']}  •  {self.format_time(song['duration'])}")
            subtitle_label.setStyleSheet("color: #b3b3b3; font-size: 12px;")
            info_layout.addWidget(subtitle_label)
            
            layout.addLayout(info_layout, 1)
            
            # Set widget
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            self.song_list.addItem(item)
            self.song_list.setItemWidget(item, widget)
    
    def on_song_item_double_clicked(self, item):
        """Play song when double-clicked from list"""
        index = item.data(Qt.ItemDataRole.UserRole)
        self.play_song(index)
    
    def play_song(self, index):
        """Play a specific song from current playlist"""
        if 0 <= index < len(self.current_playlist):
            self.current_index = index
            song = self.current_playlist[index]
            
            # Load and play
            self.player.setSource(QUrl.fromLocalFile(song["path"]))
            self.player.play()
            self.is_playing = True
            self.play_btn.setIcon(self.icons['pause'])
            
            # Update UI
            self.track_title.setText(song["title"])
            self.track_artist.setText(song["artist"])
            
            # Update album art in player
            if song.get("album_art"):
                pixmap = QPixmap()
                pixmap.loadFromData(song["album_art"])
                self.album_art.setPixmap(pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                                       Qt.TransformationMode.SmoothTransformation))
            else:
                self.album_art.clear()
                self.album_art.setStyleSheet("background-color: #282828; border-radius: 4px;")
            
            # Add to history
            self.play_history.append(index)
            if len(self.play_history) > 50:
                self.play_history.pop(0)
            
            # Highlight in list
            if 0 <= index < self.song_list.count():
                self.song_list.setCurrentRow(index)
    
    def toggle_play(self):
        """Toggle play/pause"""
        if self.current_index < 0 and self.current_playlist:
            self.play_song(0)
        elif self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.play_btn.setIcon(self.icons['play'])
        else:
            self.player.play()
            self.is_playing = True
            self.play_btn.setIcon(self.icons['pause'])
    
    def play_next(self):
        """Play next song"""
        if not self.current_playlist:
            return
        
        if self.queue:
            # Play from queue
            next_index = self.queue.pop(0)
            self.play_song(next_index)
        elif self.is_shuffle:
            # Random song
            next_index = random.randint(0, len(self.current_playlist) - 1)
            self.play_song(next_index)
        else:
            # Next in order
            next_index = (self.current_index + 1) % len(self.current_playlist)
            self.play_song(next_index)
    
    def play_previous(self):
        """Play previous song"""
        if not self.current_playlist:
            return
        
        if self.is_shuffle and len(self.play_history) > 1:
            # Go back in history
            self.play_history.pop()  # Remove current
            prev_index = self.play_history[-1]
            self.play_history.pop()  # Will be re-added in play_song
            self.play_song(prev_index)
        else:
            # Previous in order
            prev_index = (self.current_index - 1) % len(self.current_playlist)
            self.play_song(prev_index)
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.is_shuffle = not self.is_shuffle
        self.update_shuffle_button()
    
    def update_shuffle_button(self):
        """Update shuffle button appearance"""
        if self.is_shuffle:
            self.shuffle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #282828;
                    color: #1DB954;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #3e3e3e;
                }
            """)
        else:
            self.shuffle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #b3b3b3;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background-color: #282828;
                }
                QPushButton:pressed {
                    background-color: #3e3e3e;
                }
            """)
    
    def toggle_repeat(self):
        """Cycle through repeat modes"""
        self.repeat_mode = (self.repeat_mode + 1) % 3
        self.update_repeat_button()
    
    def update_repeat_button(self):
        """Update repeat button icon and appearance"""
        if self.repeat_mode == 0:
            # No repeat
            self.repeat_btn.setIcon(self.icons['repeat'])
            self.repeat_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #b3b3b3;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background-color: #282828;
                }
                QPushButton:pressed {
                    background-color: #3e3e3e;
                }
            """)
        elif self.repeat_mode == 1:
            # Repeat all
            self.repeat_btn.setIcon(self.icons['repeat'])
            self.repeat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #282828;
                    color: #1DB954;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #3e3e3e;
                }
            """)
        else:
            # Repeat one
            self.repeat_btn.setIcon(self.icons['repeat_one'])
            self.repeat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #282828;
                    color: #1DB954;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #3e3e3e;
                }
            """)
    
    def on_media_status_changed(self, status):
        """Handle when media finishes"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repeat_mode == 2:
                # Repeat one
                self.play_song(self.current_index)
            elif self.repeat_mode == 1 or self.is_shuffle:
                # Repeat all or shuffle
                self.play_next()
            elif self.current_index < len(self.current_playlist) - 1:
                # Play next
                self.play_next()
            else:
                # End of playlist
                self.is_playing = False
                self.play_btn.setIcon(self.icons['play'])
    
    def update_position(self, position):
        """Update progress bar position"""
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position)
        self.time_label.setText(self.format_time(position // 1000))
    
    def update_duration(self, duration):
        """Update progress bar maximum"""
        self.progress_slider.setRange(0, duration)
        self.duration_label.setText(self.format_time(duration // 1000))
    
    def on_seek(self, position):
        """Handle seeking"""
        self.player.setPosition(position)
    
    def on_volume_changed(self, value):
        """Handle volume change"""
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        # Save immediately so we don't lose it
        self.save_settings()
    
    def on_search(self, text):
        """Filter songs based on search"""
        if not text:
            self.display_songs(self.all_songs)
            return
        
        text = text.lower()
        filtered = [s for s in self.all_songs 
                   if text in s["title"].lower() or 
                      text in s["artist"].lower() or 
                      text in s["album"].lower()]
        self.display_songs(filtered)
    
    def on_playlist_selected(self, item):
        """Load selected playlist"""
        playlist_name = item.text()
        if playlist_name in self.playlists:
            self.current_playlist_name = playlist_name
            self.view_label.setText(playlist_name)
            songs = self.playlists[playlist_name]["songs"]
            self.display_songs(songs)
    
    def switch_view(self, view):
        """Switch between different views"""
        if view == "library":
            self.current_playlist_name = None
            self.view_label.setText("Your Library")
            self.display_songs(self.all_songs)
        elif view == "home":
            self.current_playlist_name = None
            self.view_label.setText("Home")
            # Could show recommendations, recently played, etc.
        elif view == "search":
            self.search_input.setFocus()
    
    def format_time(self, seconds):
        """Format seconds to MM:SS"""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    
    def update_ui(self):
        """Periodic UI updates"""
        pass
    
    def load_settings(self):
        """Load saved settings"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    # Restore volume
                    volume = settings.get('volume', 0.7)
                    self.audio_output.setVolume(volume)
                    # Update slider to match (convert 0.0-1.0 to 0-100)
                    self.volume_slider.setValue(int(volume * 100))
                    # Restore window position and size
                    if 'window_geometry' in settings:
                        geom = settings['window_geometry']
                        self.setGeometry(geom['x'], geom['y'], geom['width'], geom['height'])
                    # Restore shuffle and repeat
                    self.is_shuffle = settings.get('shuffle', False)
                    self.repeat_mode = settings.get('repeat_mode', 0)
            except:
                pass
    
    def save_settings(self):
        """Save settings"""
        geom = self.geometry()
        settings = {
            'volume': self.audio_output.volume(),
            'window_geometry': {
                'x': geom.x(),
                'y': geom.y(),
                'width': geom.width(),
                'height': geom.height()
            },
            'shuffle': self.is_shuffle,
            'repeat_mode': self.repeat_mode,
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    
    def closeEvent(self, event):
        """Handle window close"""
        self.save_settings()
        self.save_playlists()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LocalStream")
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = MusicPlayer()
    player.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
