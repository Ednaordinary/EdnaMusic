import os
import re
import sys
import json
import time
import spotipy
import requests
import threading
from yt_dlp import YoutubeDL
from spotipy.oauth2 import SpotifyOAuth
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
        'outtmpl': path+".mp3",
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
            print("getting info")
            info = dl.extract_info(f"ytsearch1:{term}", download=False)['entries']
            print("done")
    except:
        return False
    else:
        if info:
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

def playlist_assembler_spotify(term, path_local, path_global):
    print("assembler started")
    global playlist_downloads
    content = get_from_search_youtube(term, path_local)
    print("search done")
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
        content = dl.extract_info(url, download=False)
    if 'entries' in content:
        return content
    else:
        return False

def get_from_url(url, path):
    #try:
    content = is_playlist(url)
    if content:
        global playlist_downloads
        playlist_downloads[path] = []
        threads = []
        paths = []
        for idx, entry in enumerate(content['entries']):
            threads.append(threading.Thread(target=playlist_assembler, args=["https://www.youtube.com/watch?v="+entry['id'], path+'-'+str(idx), path]))
            paths.append(path+'-'+str(idx))
        for thread in threads:
            thread.start()
            time.sleep(0.5)
        for thread in threads:
            thread.join()
        return_value = []
        for value in paths: # sort them to be in order
            if value in playlist_downloads[path]:
                return_value.append(value)
            else:
                return_value.append(None)
        del playlist_downloads[path]
        return return_value
    else:
        status = get_from_url_youtube(url, path_local)
        if status:
            return [path]
        else:
            return [None]
    #except:
    #    return [None]

class fake_response:
    status_code = 404

def get_from_term(term, path, sp):
    try:
        response = requests.options(term)
    except:
        response = fake_response
    if response.status_code != 404:
        if re.compile(r"((?:www|open)\.)?((?:spotify\.com))").search(term):
            result = get_from_url_spotify(term, sp)
            if result:
                threads = []
                paths = []
                global playlist_downloads
                playlist_downloads[path] = []
                for idx, track in enumerate(result):
                    threads.append(threading.Thread(target=playlist_assembler_spotify, args=[track, path+'-'+str(idx), path]))
                    paths.append(path+'-'+str(idx))
                for thread in threads:
                    thread.start()
                    time.sleep(0.1)
                for thread in threads:
                    thread.join()
                return_value = []
                for value in paths: # sort them to be in order
                    if value in playlist_downloads[path]:
                        return_value.append(value)
                    else:
                        return_value.append(None)
                del playlist_downloads[path]
                return return_value
            else:
                return None
            return spotify_handler(term, interaction, channel)
        else:
            return get_from_url(term, path)
    else:
        if get_from_search_youtube(term, path):
            return [path]
        else:
            return [None]
