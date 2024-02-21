#!/bin/bash

input_file=playlist.txt
output_file=playlist.m3u

# Tworzenie nowego pliku M3U lub nadpisanie istniejącego
echo "#EXTM3U" > "$output_file"

# Pętla odczytująca każdą linię z pliku wejściowego
while IFS= read -r line; do
    # Wyciągnięcie nazwy streamu i adresu URL
    stream_name=$(echo "$line" | cut -d$'\t' -f1)
    stream_url=$(echo "$line" | cut -d$'\t' -f2-)

    # Dodanie wpisu do pliku M3U
    echo "#EXTINF:-1,$stream_name" >> "$output_file"
    echo "$stream_url" >> "$output_file"
done < "$input_file"

echo "Plik M3U został wygenerowany: $output_file"
