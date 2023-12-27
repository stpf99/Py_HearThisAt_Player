import sys
import requests
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import Qt, QUrl, QMetaObject, pyqtSignal, QObject, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, \
    QLineEdit, QLabel, QPushButton, QFileDialog
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

        self.play_button = QPushButton(self)
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_button.clicked.connect(self.toggle_play)

        self.stop_button = QPushButton(self)
        self.stop_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_button.clicked.connect(self.stop_play)

        self.save_button = QPushButton("Save Playlist", self)
        self.save_button.clicked.connect(self.save_playlist)

        self.page_label = QLabel(self)
        self.page_label.setAlignment(Qt.AlignCenter)

        self.player = QMediaPlayer()
        self.artist_username = ""
        self.page = 1
        self.local_playlist = []
        self.current_playlist_index = 0

        self.signal = Signal()
        self.signal.update_playlist_signal.connect(self.update_playlist)

        layout = QVBoxLayout(self.central_widget)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.artist_input)
        input_layout.addWidget(self.load_button)
        input_layout.addWidget(self.load_playlist_button)

        control_layout = QVBoxLayout()
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.stop_button)

        page_layout = QHBoxLayout()
        page_layout.addWidget(self.page_label)

        layout.addLayout(input_layout)
        layout.addLayout(control_layout)
        layout.addWidget(self.playlist)
        layout.addLayout(page_layout)
        layout.addWidget(self.save_button)

        # Ustawienie sygnału zakończenia odtwarzania
        self.player.mediaStatusChanged.connect(self.media_status_changed)

    def load_tracks(self):
        self.artist_username = self.artist_input.text().strip()

        if not self.artist_username:
            print("Please enter an artist username.")
            return

        self.page = 1
        self.playlist.clear()
        self.local_playlist.clear()

        # Rozpocznij wczytywanie utworów równolegle
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

                # Emituj sygnał do aktualizacji listy
                self.signal.update_playlist_signal.emit(playlist_data)

                print(f"Loaded page {page} for {self.artist_username}")

                # Aktualizacja etykiety strony
                self.page_label.setText(f"Page: {page}")

                return playlist_data

            else:
                print(f"No more tracks found for {self.artist_username} on page {page}.")

        else:
            print(f"Failed to load tracks for {self.artist_username} on page {page}. Status code: {response.status_code}")

        return []

    def load_pages(self):
        # Utwórz pulę wątków
        with ThreadPoolExecutor() as executor:
            # Uruchom zadania wczytywania stron, aż do momentu, gdy dostaniemy pustą odpowiedź
            while True:
                # Sprawdź, czy strona jest pusta
                playlist_data = self.load_page(self.page)

                if not playlist_data:
                    break

                # Dodaj dane do lokalnej playlisty
                self.local_playlist.extend(playlist_data)

                # Przejdź do następnej strony
                self.page += 1

    def update_playlist(self, data):
        for title, _ in data:
            item = QListWidgetItem(title)
            self.playlist.addItem(item)

    def play_track(self, item):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.stop()

        self.current_playlist_index = self.playlist.row(item)
        media_content = item.data(Qt.UserRole)
        self.player.setMedia(media_content)
        self.player.play()

    def toggle_play(self):
        if self.player:
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.pause()
            else:
                self.player.play()

    def stop_play(self):
        if self.player:
            self.player.stop()

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

            with open(file_path, "r") as file:
                for line in file:
                    title, url = line.strip().split("\t")
                    media_content = QMediaContent(QUrl(url))
                    item = QListWidgetItem(title)
                    item.setData(Qt.UserRole, media_content)
                    self.local_playlist.append((title, media_content))
                    self.playlist.addItem(item)

            print(f"Playlist loaded from {file_path}")

    def media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            # Przechodź do następnego utworu po zakończeniu odtwarzania
            self.play_next_track()

    def play_next_track(self):
        next_index = self.current_playlist_index + 1

        if 0 <= next_index < self.playlist.count():
            item = self.playlist.item(next_index)
            self.playlist.setCurrentItem(item)
            self.play_track(item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = HearThisPlayer()
    player.show()
    sys.exit(app.exec_())

