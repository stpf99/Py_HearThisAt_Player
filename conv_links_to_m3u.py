# Wczytaj dane z pliku tekstowego
with open('playlist.txt', 'r') as file:
    lines = file.readlines()

# Otwórz plik M3U do zapisu
with open('Playlist.m3u', 'w') as m3u_file:
    # Iteruj przez linie w pliku tekstowym
    for line in lines:
        # Podziel linię na nazwę i adres URL
        parts = line.split('\t')
        if len(parts) == 2:
            name, url = parts
            # Zapisz do pliku M3U
            m3u_file.write(f'#EXTINF:-1,{name.strip()}\n{url.strip()}\n')

