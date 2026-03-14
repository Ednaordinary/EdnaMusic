import os
import re
import sys
import json
import time
import spotipy
import requests
import threading
import concurrent.futures
from yt_dlp import YoutubeDL
from spotipy.oauth2 import SpotifyOAuth
playlist_downloads = {}

executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

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
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
    except:
        try:
            results = sp.album_tracks(playlist_id)
            tracks = results['items']
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])
            tracks = [{'track': x} for x in tracks]
        except:
            return None
        else:
            return tracks
    else:
        return tracks

def read_spotify_track(sp, song_id):
    try:
        results = sp.track(song_id)
    except:
        return None
    else:
        return results

def get_from_url_spotify(url, sp):
    playlist = read_spotify_playlist(sp, url)
    if playlist is None:
        track = read_spotify_track(sp, url)
    tracks = []
    if playlist is not None:
        for i in playlist:
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
        #'cookiefile': 'cookies.txt'
    }
    try:
        with YoutubeDL(YTDL_OPTIONS) as dl:
            info = dl.extract_info(url, download=True)
            #dl.download(url)
    except:
        return False
    else:
        return info['title']
    
def get_from_search_youtube(term, path):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': path + ".mp3",
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        #'extract_flat': True,
    }
    try:
        with YoutubeDL(YTDL_OPTIONS) as dl:
            info = dl.extract_info(f"ytsearch1:{term}", download=True)
            return info['title']
    except:
        return False

def is_playlist(url):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': False,
        'audioformat': 'mp3',
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

class fake_response:
    status_code = 404

async def get_from_term(term, path, sp):
    try:
        response = requests.options(term)
    except:
        response = fake_response
    if response.status_code != 404:
        if re.compile(r"((?:www|open)\.)?((?:spotify\.com))").search(term):
            result = get_from_url_spotify(term, sp)
            if result:
                print(result)
                downloads = executor.map(get_from_search_youtube, result, [path+'-'+str(idx) for idx in range(len(result))])
                for idx, status in enumerate(downloads):
                    if status:
                        yield (path + '-'+str(idx), status)
                    else:
                        yield None
            else:
                yield None
        else:
            content = is_playlist(term)
            if content:
                title_map = [entry['title'] for entry in content['entries']]
                downloads = executor.map(get_from_url_youtube, ["https://www.youtube.com/watch?v="+entry["id"] for entry in content['entries']], [path+'-'+str(idx) for idx in range(len(content))])
                for idx, status in enumerate(downloads):
                    if status:
                        yield (path + '-'+str(idx), title_map[idx])
                    else:
                        yield None
            else:
                status = get_from_url_youtube(term, path)
                if status:
                    yield (path, status)
                else:
                    yield None
    else:
        status = get_from_search_youtube(term, path)
        if status:
            yield (path, status)
        else:
            yield None
