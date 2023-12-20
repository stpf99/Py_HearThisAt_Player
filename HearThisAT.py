import sys
import requests
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QObject, QTime, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QLabel, QPushButton,
    QFileDialog, QSlider, QSizePolicy, QComboBox
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTabWidget

class Signal(QObject):
    update_playlist_signal = pyqtSignal(list)
    update_genres_signal = pyqtSignal(list)

class GenreSelector(QWidget):
    genre_selected = pyqtSignal(str)

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
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HearThis Player")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)


        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search in Playlist")
        self.search_input.textChanged.connect(self.search_playlist)

        self.playlist = QListWidget(self)
        self.playlist.currentItemChanged.connect(self.play_track)

        self.selected_tracks = QListWidget(self)
        self.selected_tracks.currentItemChanged.connect(self.play_track)

        self.play_button = QPushButton(self)
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_button.clicked.connect(self.toggle_play)

        self.stop_button = QPushButton(self)
        self.stop_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_button.clicked.connect(self.stop_play)

        self.add_to_selected_button = QPushButton("Add to Selected Tracks", self)
        self.add_to_selected_button.clicked.connect(self.add_to_selected)

        self.page_label = QLabel(self)
        self.page_label.setAlignment(Qt.AlignCenter)

        self.player = QMediaPlayer()
        self.artist_username = ""
        self.page = 1
        self.local_playlist = []
        self.selected_playlist = []
        self.current_track_index = 0

        self.signal = Signal()
        self.signal.update_playlist_signal.connect(self.update_playlist)
        self.signal.update_genres_signal.connect(self.update_genres)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_duration)
        self.current_track_duration = QTime(0, 0)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.playlist, "All Tracks")
        self.tab_widget.addTab(self.selected_tracks, "Selected Tracks")

        self.genre_selector = GenreSelector()
        self.genre_selector.genre_selected.connect(self.load_tracks_by_genre)

        self.page = 1  # Dodana zmienna przechowująca aktualną stronę wyników

        self.load_genre_button = QPushButton("Load Genre", self)
        self.load_genre_button.clicked.connect(self.load_genre_tracks)
        
        self.prev_page_button = QPushButton("<", self)
        self.prev_page_button.clicked.connect(self.load_prev_page)

        self.next_page_button = QPushButton(">", self)
        self.next_page_button.clicked.connect(self.load_next_page)

        self.duration_label = QLabel("Duration: 00:00", self)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 0)
        self.slider.setSingleStep(1000)
        self.slider.sliderMoved.connect(self.set_position)

        layout = QVBoxLayout(self.central_widget)



        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)

        control_layout = QVBoxLayout()
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.add_to_selected_button)

        page_layout = QHBoxLayout()
        page_layout.addWidget(self.page_label)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(self.duration_label)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider)

        genre_layout = QVBoxLayout()
        genre_layout.addWidget(self.genre_selector)
        genre_layout.addWidget(self.load_genre_button)
        genre_layout.addWidget(self.prev_page_button)
        genre_layout.addWidget(self.next_page_button)

        layout.addLayout(search_layout)
        layout.addWidget(self.tab_widget)
        layout.addLayout(control_layout)
        layout.addLayout(page_layout)
        layout.addLayout(duration_layout)
        layout.addLayout(slider_layout)
        layout.addLayout(genre_layout)

        self.load_genres()  # Wczytanie dostępnych gatunków muzycznych

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
                    # ... (dodaj inne potrzebne informacje)
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

        duration = int(track["duration"]) // 1000  # Konwertuj na sekundy
        self.current_track_duration = QTime().fromMSecsSinceStartOfDay(duration * 1000)
        self.duration_label.setText(f"Duration: {self.current_track_duration.toString('mm:ss')}")

        self.slider.setRange(0, duration * 1000)
        self.timer.start(1000)


    def toggle_play(self):
        if self.player:
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.pause()
            else:
                if self.current_track_index < len(self.local_playlist):
                    next_item = self.playlist.item(self.current_track_index)
                    self.playlist.setCurrentItem(next_item)
                    self.current_track_index += 1
                    self.play_track(next_item)
                else:
                    self.stop_play()

    def stop_play(self):
        if self.player:
            self.player.stop()
            self.timer.stop()

    def set_position(self, position):
        self.player.setPosition(position)

    def update_duration(self):
        position = self.player.position()
        self.slider.setValue(position)

    def search_playlist(self):
        search_text = self.search_input.text().strip().lower()

        for index in range(self.playlist.count()):
            item = self.playlist.item(index)
            item_text = item.text().lower()

            if search_text in item_text:
                item.setHidden(False)
            else:
                item.setHidden(True)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = HearThisPlayer()
    player.show()
    sys.exit(app.exec_())