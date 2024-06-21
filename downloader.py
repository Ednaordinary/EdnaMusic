import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import requests
import threading
yt_dlp.utils.bug_reports_message = lambda: ''
playlist_downloads = {}

def authenticate_spotify(spotify_id, spotify_secret):
    sp_oauth = SpotifyOAuth(
        client_id=spotify_id,
        client_secret=spotify_secret,
        redirect_uri='https://localhost:8888/callback',
        scope='',
        open_browser=True
    )
    return spotipy.Spotify(auth_manager=sp_oauth)

def read_spotify_playlist(sp, playlist_id):
    try:
        results = sp.playlist(playlist_id)
    except:
        return None
    else:
        return results

def read_spotify_track(sp, song_id):
    try:
        results = sp.track(song_id)
    except:
        return None
    else:
        return results

def get_from_url_spotify(url, sp):
    playlist = read_spotify_playlist(sp, url)
    track = read_spotify_track(sp, url)
    tracks = []
    if playlist is not None:
        for i in playlist["tracks"]["items"]:
            artists = ""
            for x in i["track"]["artists"]:
                artists = artists + " " + x["name"]
            tracks.append(i["track"]["name"] + artists)
    elif track is not None:
        artists = ""
        for i in track["artists"]:
            artists = artists + " " + i["name"]
        tracks.append(track["name"] + artists)
    if len(tracks) == 0:
        return None
    else:
        return tracks

def get_from_url_youtube(url, path):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'best',
        'outtmpl': path,
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }
    try:
        with YoutubeDL(YTDL_OPTIONS) as dl:
            dl.download(url)
    except:
        return False
    else:
        return True
    
def get_from_search_youtube(term, path):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': False,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': False,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extract_flat': True,
    }
    try:
        with YoutubeDL(YTDL_OPTIONS) as dl:
            info = dl.extract_info(f"ytsearch1:{arg}", download=False)['entries']
    except:
        return False
    else:
        return True
    if info is not None:
        url = "https://www.youtube.com/watch?v="+info[0]['id']
        return get_from_url_youtube(url, path)
    else:
        return False

def playlist_assembler(url, path_local, path_global):
    global playlist_downloads
    content = get_from_url_youtube(url, path_local)
    if content:
        playlist_downloads[path_global].append(path_local)
    else:
        playlist_downloads[path_global].append(None)

def is_playlist(url):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': False,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': False,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'skip_download': True,
        'extract_flat': True,
    }
    with YoutubeDL(YTDL_OPTIONS) as dl:
        content = ydl.extract_info(arg, download=False)
    if 'entries' in content:
        return True
    else:
        return False

def get_from_url(url, path, playlist):
    if playlist:
        global playlist_downloads
        playlist_downloads[path] = []
        threads = []
        for idx, entry in enumerate(content['entries']):
            threads.append(threading.Thread(target=playlist_assembler, args=["https://www.youtube.com/watch?v="+entry['id'], path+'-'+str(idx), path]))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return playlist_downloads[path]
    else:
        status = get_from_url_youtube(url, path_local)
        if status:
            return [path]
        else:
            return [None]

def get_from_term(term, path):
    response = requests.options(term)
    
