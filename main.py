from yt_dlp import YoutubeDL
import pygame
from collections import deque
import threading

# Initialize pygame mixer
pygame.mixer.init()

# Create a deque to hold the playlist
playlist = deque()

# Lock to synchronize access to the playlist
playlist_lock = threading.Lock()

# Event to signal the play_songs thread to stop
stop_event = threading.Event()

# Set options for downloading as MP3
file_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': '%(title)s.%(ext)s',  # Save the file with the video title as the filename
}


# Function to add a song to the playlist
def add_to_playlist(video_url):
    try:
        with YoutubeDL(file_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            video_title = info_dict.get('title', None)

            if video_title:
                mp3_filename = f"{video_title}.mp3"
                ydl.download([video_url])
                with playlist_lock:
                    playlist.append(mp3_filename)
                print(f"Added '{video_title}' to the playlist.")
    except Exception as e:
        print(f"Error adding video: {e}")


# Function to view the current playlist
def view_playlist():
    with playlist_lock:
        print("\nCurrent Playlist:")
        for idx, song in enumerate(playlist, start=1):
            print(f"{idx}. {song}")
        print()


# Function to play songs in a separate thread
def play_songs():
    while not stop_event.is_set():
        if not pygame.mixer.music.get_busy():
            with playlist_lock:
                if playlist:
                    song = playlist.popleft()
                    pygame.mixer.music.load(song)
                    pygame.mixer.music.play()
        stop_event.wait(1)  # Sleep for a short duration to avoid busy-waiting


# Start the play_songs thread
play_songs_thread = threading.Thread(target=play_songs)
play_songs_thread.start()

# Continuous loop for user input and playlist handling
try:
    while True:
        print('Give me a YouTube Link to a song you want to add to the playlist (or type "exit" to quit):')
        print('Type "view" to see the current playlist.')
        user_input = input()

        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'view':
            view_playlist()
        else:
            add_to_playlist(user_input)
finally:
    stop_event.set()
    play_songs_thread.join()
    pygame.quit()
