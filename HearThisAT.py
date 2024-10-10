import sys
import requests
from qtpy.QtCore import Qt, QUrl, Signal, QTimer, QTime
from qtpy.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QLabel, QPushButton,
    QSlider, QComboBox, QTextBrowser, QTabWidget, QToolBar, QAction
)
from qtpy.QtMultimedia import QMediaPlayer, QMediaContent
from qtpy.QtGui import QIcon, QPixmap, QTextDocument, QTextOption
from concurrent.futures import ThreadPoolExecutor

class GenreSelector(QWidget):
    genre_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.genre_combo = QComboBox(self)
        self.genre_combo.currentIndexChanged.connect(self.emit_genre_selected)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select Genre:"))
        layout.addWidget(self.genre_combo)

    def set_genres(self, genres):
        self.genre_combo.clear()
        self.genre_combo.addItems(genres)

    def emit_genre_selected(self):
        selected_genre = self.genre_combo.currentText()
        self.genre_selected.emit(selected_genre)

class HearThisPlayer(QMainWindow):
    update_playlist_signal = Signal(list)
    update_genres_signal = Signal(list)
    update_artist_info_signal = Signal(dict)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HearThis Player")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Create a main layout for the central widget
        self.main_layout = QVBoxLayout(self.central_widget)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search Artist")
        self.search_button = QPushButton("Search Artist", self)
        self.search_button.clicked.connect(self.search_artist)
        self.search_on_button = QPushButton("Search On", self)
        self.search_on_button.clicked.connect(self.search_on_hearthis)

        self.playlist = QListWidget(self)
        self.playlist.currentItemChanged.connect(self.play_track)

        self.selected_tracks = QListWidget(self)
        self.selected_tracks.currentItemChanged.connect(self.play_track)

        self.add_to_selected_button = QPushButton("Add to Selected Tracks", self)
        self.add_to_selected_button.clicked.connect(self.add_to_selected)

        self.page_label = QLabel(self)
        self.page_label.setAlignment(Qt.AlignCenter)

        self.artist_avatar_label = QLabel(self)
        self.artist_avatar_label.setScaledContents(True)

        self.artist_info_label = QTextBrowser(self)
        self.artist_info_label.setOpenExternalLinks(True)
        self.artist_info_label.setOpenLinks(True)
        self.artist_info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.artist_info_label.setLineWrapMode(QTextBrowser.WidgetWidth)
        self.artist_info_label.setFixedHeight(100)

        self.player = QMediaPlayer()
        self.artist_username = ""
        self.page = 1
        self.local_playlist = []
        self.selected_playlist = []
        self.current_track_index = 0

        self.signal = Signal()
        update_playlist_signal = Signal(list)
        update_genres_signal = Signal(list)
        update_artist_info_signal = Signal(dict)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_duration)
        self.current_track_duration = QTime(0, 0)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.playlist, "All Tracks")
        self.tab_widget.addTab(self.selected_tracks, "Selected Tracks")

        self.genre_selector = GenreSelector()
        self.genre_selector.genre_selected.connect(self.load_tracks_by_genre)

        self.load_artist_tracks_button = self.create_load_button("Load Artist Tracks", track_type='tracks')
        self.load_artist_likes_button = self.create_load_button("Load Artist Likes", track_type='likes')
        self.load_artist_reshares_button = self.create_load_button("Load Artist Reshares", track_type='reshares')

        self.load_genre_button = QPushButton("Load Genre", self)
        self.load_genre_button.clicked.connect(self.load_genre_tracks)

        self.prev_page_button = QPushButton("<", self)
        self.prev_page_button.clicked.connect(self.load_prev_page)

        self.next_page_button = QPushButton(">", self)
        self.next_page_button.clicked.connect(self.load_next_page)

        self.create_toolbar()
        self.create_media_controls()

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.search_on_button)

        load_buttons_layout = QHBoxLayout()
        load_buttons_layout.addWidget(self.load_artist_tracks_button)
        load_buttons_layout.addWidget(self.load_artist_likes_button)
        load_buttons_layout.addWidget(self.load_artist_reshares_button)

        genre_layout = QHBoxLayout()
        genre_layout.addWidget(self.genre_selector)
        genre_layout.addWidget(self.load_genre_button)
        genre_layout.addWidget(self.prev_page_button)
        genre_layout.addWidget(self.next_page_button)

        info_layout = QVBoxLayout()
        info_layout.addWidget(self.artist_info_label)

        # Add all layouts and widgets to the main layout
        self.main_layout.addLayout(search_layout)
        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(self.add_to_selected_button)
        self.main_layout.addWidget(self.page_label)
        self.main_layout.addLayout(genre_layout)
        self.main_layout.addLayout(info_layout)
        self.main_layout.addLayout(load_buttons_layout)



        self.signal = self
        self.signal.update_playlist_signal.connect(self.update_playlist)
        self.signal.update_genres_signal.connect(self.update_genres)
        self.signal.update_artist_info_signal.connect(self.update_artist_info)
        self.load_genres()

    def create_media_controls(self):
        self.time_label = QLabel("00:00 / 00:00")
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)

        media_controls_layout = QHBoxLayout()
        media_controls_layout.addWidget(self.time_label)
        media_controls_layout.addWidget(self.position_slider)

        # Add the media controls to the main layout
        self.main_layout.addLayout(media_controls_layout)

    def create_toolbar(self):
        self.toolbar = QToolBar("Media Controls")
        self.toolbar.setMovable(True)
        self.toolbar.setFloatable(True)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.play_pause_action = QAction(QIcon.fromTheme("media-playback-start"), "Play/Pause", self)
        self.play_pause_action.triggered.connect(self.toggle_play)
        self.toolbar.addAction(self.play_pause_action)

        self.stop_action = QAction(QIcon.fromTheme("media-playback-stop"), "Stop", self)
        self.stop_action.triggered.connect(self.stop_play)
        self.toolbar.addAction(self.stop_action)

        self.toolbar.addSeparator()

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.toolbar.addWidget(self.volume_slider)

        self.mute_action = QAction(QIcon.fromTheme("audio-volume-high"), "Mute", self)
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(self.toggle_mute)
        self.toolbar.addAction(self.mute_action)

    def create_load_button(self, text, track_type):
        button = QPushButton(text, self)
        button.clicked.connect(lambda: self.load_artist_tracks(track_type=track_type, page=1, count=20))
        return button

    def search_artist(self):
        artist_username = self.search_input.text().strip()
        if artist_username:
            self.artist_username = artist_username
            self.page = 1
            self.playlist.clear()
            self.selected_tracks.clear()
            self.local_playlist.clear()
            self.selected_playlist.clear()
            self.current_track_index = 0

            self.load_artist_info()
            self.load_pages()

    def search_on_hearthis(self):
        search_query = self.search_input.text().strip()
        if search_query:
            search_url = f"https://api-v2.hearthis.at/search"
            params = {
                "t": search_query,
                "page": 1,
                "count": 5,
            }

            try:
                response = requests.get(search_url, params=params)
                response.raise_for_status()
                search_results = response.json()

                tracks = []
                for track in search_results:
                    title = track["title"]
                    uri = track["uri"]
                    stream_url = track["stream_url"]
                    duration = track["duration"]

                    track_data = {
                        "title": title,
                        "uri": uri,
                        "stream_url": stream_url,
                        "duration": duration,
                    }

                    tracks.append(track_data)

                self.update_playlist(tracks)

            except requests.RequestException as e:
                print(f"Error performing search on hearthis.at: {e}")

    def load_artist_info(self):
        artist_api_url = f"https://api-v2.hearthis.at/{self.artist_username}/"
        try:
            response = requests.get(artist_api_url)
            response.raise_for_status()
            artist_info = response.json()

            avatar_url = artist_info.get("avatar_url")
            description = artist_info.get("description")

            self.signal.update_artist_info_signal.emit({"avatar_url": avatar_url, "description": description})

        except requests.RequestException as e:
            print(f"Error loading artist info: {e}")

    def load_artist_tracks(self, track_type='tracks', page=1, count=5):
        if not self.artist_username:
            print("Please select an artist.")
            return

        artist_api_url = f"https://api-v2.hearthis.at/{self.artist_username}/"
        tracks_api_url = f"{artist_api_url}?type={track_type}&page={page}&count={count}"

        try:
            response_artist = requests.get(artist_api_url)
            response_artist.raise_for_status()
            artist_info = response_artist.json()
            self.signal.update_artist_info_signal.emit(artist_info)

            response_tracks = requests.get(tracks_api_url)
            response_tracks.raise_for_status()
            artist_tracks = response_tracks.json()

            self.playlist.clear()
            self.selected_tracks.clear()
            self.local_playlist.clear()
            self.selected_playlist.clear()
            self.current_track_index = 0

            for track in artist_tracks:
                title = track["title"]
                track_data = {
                    "id": track["id"],
                    "uri": track["uri"],
                    "stream_url": track["stream_url"],
                    "duration": track["duration"],
                }

                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, track_data)
                self.local_playlist.append((title, track_data))
                self.playlist.addItem(item)

            self.page_label.setText(f"Loaded artist {track_type} for {self.artist_username}")

        except requests.RequestException as e:
            print(f"Error loading artist {track_type}: {e}")


    def update_genres(self, genres):
        print("Updated genres:", genres)

    def load_genre_tracks(self):
        selected_genre = self.genre_selector.genre_combo.currentText()

        if not selected_genre:
            print("Please select a genre.")
            return

        genre_api_url = f"https://api-v2.hearthis.at/categories/{selected_genre}/"
        params = {
            "page": self.page,
            "count": 20,
        }

        try:
            response = requests.get(genre_api_url, params=params)
            response.raise_for_status()
            genre_tracks = response.json()

            self.playlist.clear()
            self.selected_tracks.clear()
            self.local_playlist.clear()
            self.selected_playlist.clear()
            self.current_track_index = 0

            for track in genre_tracks:
                title = track["title"]
                track_data = {
                    "id": track["id"],
                    "uri": track["uri"],
                    "stream_url": track["stream_url"],
                    "duration": track["duration"],
                }

                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, track_data)
                self.local_playlist.append((title, track_data))
                self.playlist.addItem(item)

        except requests.RequestException as e:
            print(f"Error loading genre tracks: {e}")

    def load_prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_genre_tracks()

    def load_next_page(self):
        self.page += 1
        self.load_genre_tracks()

    def load_genres(self):
        hearthis_api_url = "https://api-v2.hearthis.at/categories/"
        response = requests.get(hearthis_api_url)

        if response.status_code == 200:
            genres_data = response.json()
            genres = [genre["id"] for genre in genres_data]
            self.genre_selector.set_genres(genres)
            self.signal.update_genres_signal.emit(genres)

    def load_pages(self):
        executor = ThreadPoolExecutor(max_workers=5)
        executor.map(self.load_page, range(1, 36))

    def load_page(self, page):
        hearthis_api_url = f"https://api-v2.hearthis.at/{self.artist_username}/?page={page}&count=5"
        response = requests.get(hearthis_api_url)

        if response.status_code == 200:
            data = response.json()
            tracks = data["data"]

            if not tracks:
                print(f"No more tracks found for {self.artist_username} on page {page}.")
                return

            self.signal.update_playlist_signal.emit(tracks)

    def update_playlist(self, tracks):
        for track in tracks:
            title = track["title"]
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, track)
            self.local_playlist.append((title, track))
            self.playlist.addItem(item)

        self.page_label.setText(f"Loaded page {self.page} for {self.artist_username}")
        self.page += 1

    def play_track(self, item):
        if not item:
            return

        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.stop()

        track = item.data(Qt.UserRole)
        media_content = QMediaContent(QUrl(track["stream_url"]))
        self.player.setMedia(media_content)
        self.player.play()

        duration = int(track["duration"]) // 1000
        self.current_track_duration = QTime().fromMSecsSinceStartOfDay(duration * 1000)
        self.position_slider.setRange(0, duration * 1000)
        self.timer.start(1000)

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
        self.time_label.setText("00:00 / 00:00")
        self.position_slider.setValue(0)

    def set_volume(self, volume):
        self.player.setVolume(volume)
        if volume > 0:
            self.mute_action.setIcon(QIcon.fromTheme("audio-volume-high"))
        else:
            self.mute_action.setIcon(QIcon.fromTheme("audio-volume-muted"))

    def toggle_mute(self, checked):
        if checked:
            self.player.setMuted(True)
            self.mute_action.setIcon(QIcon.fromTheme("audio-volume-muted"))
        else:
            self.player.setMuted(False)
            self.mute_action.setIcon(QIcon.fromTheme("audio-volume-high"))

    def set_position(self, position):
        self.player.setPosition(position)

    def update_duration(self):
        duration = self.player.duration()
        position = self.player.position()

        if duration > 0:
            self.position_slider.setMaximum(duration)

        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)

        current_time = QTime(0, 0).addMSecs(position)
        total_time = QTime(0, 0).addMSecs(duration)
        time_format = "mm:ss"
        self.time_label.setText(f"{current_time.toString(time_format)} / {total_time.toString(time_format)}")

    def add_to_selected(self):
        current_item = self.playlist.currentItem()

        if current_item:
            title = current_item.text()
            track = current_item.data(Qt.UserRole)

            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, track)

            self.selected_playlist.append((title, track))
            self.selected_tracks.addItem(item)

    def load_tracks_by_genre(self, selected_genre):
        self.artist_username = selected_genre
        self.page = 1
        self.playlist.clear()
        self.selected_tracks.clear()
        self.local_playlist.clear()
        self.selected_playlist.clear()
        self.current_track_index = 0

        self.load_pages()

    def update_genres(self, genres):
        print("Updated genres:", genres)

    def update_artist_info(self, artist_info):
        avatar_url = artist_info.get("avatar_url")
        description = artist_info.get("description")

        if avatar_url:
            avatar_pixmap = QPixmap()
            avatar_pixmap.loadFromData(requests.get(avatar_url).content)
            self.artist_info_label.document().addResource(
                QTextDocument.ImageResource,
                QUrl(avatar_url),
                avatar_pixmap
            )
            self.artist_info_label.insertHtml(f'<img src="{avatar_url}" width="100" height="100"/>')

        if description:
            self.artist_info_label.append(f"<b>Description:</b><br>{description}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = HearThisPlayer()
    player.show()
    sys.exit(app.exec_())
