from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
import pygame
from collections import deque
import threading
import socket
import segno
# Many User Experience things to do.. too many to list at the moment.



app = Flask(__name__)

# Initialize pygame mixer
pygame.mixer.init()

# Create a deque to hold the playlist
playlist = deque()

# Lock to synchronize access to the playlist
playlist_lock = threading.Lock()

# Event to signal the play_songs thread to stop
stop_event = threading.Event()

# Variable to hold the current playing song
current_song = None

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


# Function to create a QR code on run for scan-able link.
def create_qr_code():
    # get the client IP
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    # create qr code image that goes to localhost
    qrcode = segno.make_qr("http://" + str(ip_address) + ":5000")
    qrcode.save("./static/qrcode.png", scale=10)

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
                return f"Added '{video_title}' to the playlist."
    except Exception as e:
        return f"Error adding video: {e}"

# Function to view the current playlist
def view_playlist():
    with playlist_lock:
        playlist_content = list(playlist)
    return playlist_content

# Function to play songs in a separate thread
def play_songs():
    global current_song
    while not stop_event.is_set():
        if not pygame.mixer.music.get_busy():
            with playlist_lock:
                if playlist:
                    current_song = playlist.popleft()
                    pygame.mixer.music.load(current_song)
                    pygame.mixer.music.play()
                else:
                    current_song = None
        stop_event.wait(1)  # Sleep for a short duration to avoid busy-waiting


# Create our QR Code Before run
create_qr_code()

# Start the play_songs thread
play_songs_thread = threading.Thread(target=play_songs)
play_songs_thread.start()

@app.route('/add', methods=['POST'])
def add_song():
    video_url = request.form.get('url')
    message = add_to_playlist(video_url)
    return jsonify({'message': message})

@app.route('/playlist', methods=['GET'])
def get_playlist():
    current_playlist = view_playlist()
    return jsonify({'playlist': current_playlist, 'current_song': current_song})

@app.route('/')
def index():
    return '''
        <center>    
        <img src="/static/qrcode.png" alt="QR Code">
        <form id="add-song-form" action="/add" method="post">
            YouTube URL: <input type="text" name="url" id="url-input"><br>
            <input type="submit" value="Add Song">
        </form>
        <br>
        <form id="view-playlist-form" action="/playlist" method="get">
            <input type="submit" value="View Playlist">
        </form>
        <div id="current-song"></div>
        <div id="playlist"></div>
        <div id="message"></div>
        <script>
            document.getElementById('add-song-form').onsubmit = function(event) {
                event.preventDefault();
                let formData = new FormData(this);
                fetch('/add', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('message').innerText = data.message;
                });
            };

            document.getElementById('view-playlist-form').onsubmit = function(event) {
                event.preventDefault();
                fetch('/playlist')
                    .then(response => response.json())
                    .then(data => {
                        let playlistDiv = document.getElementById('playlist');
                        let currentSongDiv = document.getElementById('current-song');
                        if (data.current_song) {
                            currentSongDiv.innerHTML = `<h2>Now Playing: ${data.current_song}</h2>`;
                        } else {
                            currentSongDiv.innerHTML = `<h2>No song is currently playing</h2>`;
                        }
                        playlistDiv.innerHTML = "<h2>Current Playlist</h2>";
                        data.playlist.forEach((song, index) => {
                            playlistDiv.innerHTML += `<p>${index + 1}. ${song}</p>`;
                        });
                    });
            };
        </script>
    </center>
    '''

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        stop_event.set()
        play_songs_thread.join()
        pygame.quit()
