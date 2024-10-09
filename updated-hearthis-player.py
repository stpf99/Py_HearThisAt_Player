import sys
import random
from concurrent.futures import ThreadPoolExecutor
import requests
from PyQt5.QtCore import Qt, QUrl, QTime, pyqtSignal, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                             QLineEdit, QLabel, QPushButton, QFileDialog, QToolBar, QSlider, QAction)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QIcon

class Signal(QObject):
    update_playlist_signal = pyqtSignal(list)

class HearThisPlayer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HearThis Player")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.artist_input = QLineEdit(self)
        self.artist_input.setPlaceholderText("Enter artist username")

        self.load_button = QPushButton("Load Tracks", self)
        self.load_button.clicked.connect(self.load_tracks)

        self.load_playlist_button = QPushButton("Load Playlist", self)
        self.load_playlist_button.clicked.connect(self.load_playlist)

        self.playlist = QListWidget(self)
        self.playlist.currentItemChanged.connect(self.play_track)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search playlist")
        self.search_input.textChanged.connect(self.filter_playlist)

        self.progress_bar = QSlider(Qt.Horizontal)
        self.progress_bar.sliderMoved.connect(self.set_position)

        self.time_label = QLabel("00:00 / 00:00")

        self.save_button = QPushButton("Save Playlist", self)
        self.save_button.clicked.connect(self.save_playlist)

        self.page_label = QLabel(self)
        self.page_label.setAlignment(Qt.AlignCenter)

        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

        self.artist_username = ""
        self.page = 1
        self.local_playlist = []
        self.filtered_playlist = []

        self.repeat_mode = 0  # 0: No repeat, 1: Repeat one, 2: Repeat all
        self.shuffle_mode = False

        self.signal = Signal()
        self.signal.update_playlist_signal.connect(self.update_playlist)

        self.create_toolbar()
        self.create_layout()

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.prev_action = QAction(QIcon.fromTheme("media-skip-backward"), "Previous", self)
        self.prev_action.triggered.connect(self.previous_track)
        toolbar.addAction(self.prev_action)

        self.play_pause_action = QAction(QIcon.fromTheme("media-playback-start"), "Play/Pause", self)
        self.play_pause_action.triggered.connect(self.toggle_play)
        toolbar.addAction(self.play_pause_action)

        self.stop_action = QAction(QIcon.fromTheme("media-playback-stop"), "Stop", self)
        self.stop_action.triggered.connect(self.stop_play)
        toolbar.addAction(self.stop_action)

        self.next_action = QAction(QIcon.fromTheme("media-skip-forward"), "Next", self)
        self.next_action.triggered.connect(self.next_track)
        toolbar.addAction(self.next_action)

        self.repeat_action = QAction(QIcon.fromTheme("media-playlist-repeat"), "Repeat", self)
        self.repeat_action.triggered.connect(self.toggle_repeat)
        toolbar.addAction(self.repeat_action)

        self.shuffle_action = QAction(QIcon.fromTheme("media-playlist-shuffle"), "Shuffle", self)
        self.shuffle_action.triggered.connect(self.toggle_shuffle)
        toolbar.addAction(self.shuffle_action)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        toolbar.addWidget(self.volume_slider)

        self.mute_action = QAction(QIcon.fromTheme("audio-volume-muted"), "Mute", self)
        self.mute_action.triggered.connect(self.toggle_mute)
        toolbar.addAction(self.mute_action)

    def create_layout(self):
        layout = QVBoxLayout(self.central_widget)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.artist_input)
        input_layout.addWidget(self.load_button)
        input_layout.addWidget(self.load_playlist_button)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.time_label)

        layout.addLayout(input_layout)
        layout.addLayout(search_layout)
        layout.addWidget(self.playlist)
        layout.addLayout(progress_layout)
        layout.addWidget(self.page_label)
        layout.addWidget(self.save_button)

    def load_tracks(self):
        self.artist_username = self.artist_input.text().strip()

        if not self.artist_username:
            print("Please enter an artist username.")
            return

        self.page = 1
        self.playlist.clear()
        self.local_playlist.clear()
        self.filtered_playlist.clear()

        self.load_pages()

    def load_page(self, page):
        hearthis_api_url = "https://api-v2.hearthis.at/search/"

        params = {
            "t": self.artist_username,
            "page": page,
            "count": 20
        }

        response = requests.get(hearthis_api_url, params=params)

        if response.status_code == 200:
            data = response.json()

            if data:
                tracks = data
                playlist_data = []

                for track in tracks:
                    title = track["title"]
                    url = track["stream_url"]

                    item = QListWidgetItem(title)
                    media_content = QMediaContent(QUrl(url))
                    item.setData(Qt.UserRole, media_content)
                    playlist_data.append((title, media_content))

                self.signal.update_playlist_signal.emit(playlist_data)

                print(f"Loaded page {page} for {self.artist_username}")
                self.page_label.setText(f"Page: {page}")

                return playlist_data

            else:
                print(f"No more tracks found for {self.artist_username} on page {page}.")

        else:
            print(f"Failed to load tracks for {self.artist_username} on page {page}. Status code: {response.status_code}")

        return []

    def load_pages(self):
        with ThreadPoolExecutor() as executor:
            while True:
                playlist_data = self.load_page(self.page)

                if not playlist_data:
                    break

                self.local_playlist.extend(playlist_data)
                self.filtered_playlist = self.local_playlist.copy()

                self.page += 1

    def update_playlist(self, data):
        for title, _ in data:
            item = QListWidgetItem(title)
            self.playlist.addItem(item)

    def play_track(self, item):
        if item:
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.stop()

            media_content = item.data(Qt.UserRole)
            self.player.setMedia(media_content)
            self.player.play()
            self.play_pause_action.setIcon(QIcon.fromTheme("media-playback-pause"))

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_pause_action.setIcon(QIcon.fromTheme("media-playback-start"))
        else:
            self.player.play()
            self.play_pause_action.setIcon(QIcon.fromTheme("media-playback-pause"))

    def stop_play(self):
        self.player.stop()
        self.play_pause_action.setIcon(QIcon.fromTheme("media-playback-start"))

    def previous_track(self):
        current_row = self.playlist.currentRow()
        if current_row > 0:
            self.playlist.setCurrentRow(current_row - 1)
        elif self.repeat_mode == 2:  # Repeat all
            self.playlist.setCurrentRow(self.playlist.count() - 1)

    def next_track(self):
        current_row = self.playlist.currentRow()
        if current_row < self.playlist.count() - 1:
            self.playlist.setCurrentRow(current_row + 1)
        elif self.repeat_mode == 2:  # Repeat all
            self.playlist.setCurrentRow(0)

    def toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        repeat_icons = ["media-playlist-repeat", "media-playlist-repeat-song", "media-playlist-repeat"]
        self.repeat_action.setIcon(QIcon.fromTheme(repeat_icons[self.repeat_mode]))

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            random.shuffle(self.filtered_playlist)
        else:
            self.filtered_playlist.sort(key=lambda x: self.local_playlist.index(x))
        self.update_playlist_view()
        self.shuffle_action.setIcon(QIcon.fromTheme("media-playlist-shuffle" if self.shuffle_mode else "media-playlist-normal"))

    def set_volume(self, value):
        self.player.setVolume(value)

    def toggle_mute(self):
        self.player.setMuted(not self.player.isMuted())
        self.mute_action.setIcon(QIcon.fromTheme("audio-volume-muted" if self.player.isMuted() else "audio-volume-high"))

    def set_position(self, position):
        self.player.setPosition(position)

    def position_changed(self, position):
        self.progress_bar.setValue(position)
        self.update_time_label()

    def duration_changed(self, duration):
        self.progress_bar.setRange(0, duration)
        self.update_time_label()

    def update_time_label(self):
        duration = self.player.duration()
        position = self.player.position()
        self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")

    def format_time(self, ms):
        time = QTime(0, 0).addMSecs(ms)
        return time.toString("mm:ss")

    def filter_playlist(self):
        search_text = self.search_input.text().lower()
        self.filtered_playlist = [item for item in self.local_playlist if search_text in item[0].lower()]
        self.update_playlist_view()

    def update_playlist_view(self):
        self.playlist.clear()
        for title, media_content in self.filtered_playlist:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, media_content)
            self.playlist.addItem(item)

    def save_playlist(self):
        if not self.local_playlist:
            print("Playlist is empty. Load tracks first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Playlist", "", "Text Files (*.txt);;All Files (*)")

        if file_path:
            with open(file_path, "w") as file:
                for title, media_content in self.local_playlist:
                    file.write(f"{title}\t{media_content.canonicalUrl().toString()}\n")

            print(f"Playlist saved to {file_path}")

    def load_playlist(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Playlist", "", "Text Files (*.txt);;All Files (*)")

        if file_path:
            self.playlist.clear()
            self.local_playlist.clear()
            self.filtered_playlist.clear()

            with open(file_path, "r") as file:
                for line in file:
                    title, url = line.strip().split("\t")
                    media_content = QMediaContent(QUrl(url))
                    self.local_playlist.append((title, media_content))

            self.filtered_playlist = self.local_playlist.copy()
            self.update_playlist_view()
            print(f"Playlist loaded from {file_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = HearThisPlayer()
    player.show()
    sys.exit(app.exec_())
