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
        try:
            results = sp.album_tracks(playlist_id)
            print(results)
        except:
            return None
        else:
            return results
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
    if playlist is None:
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
            info = dl.extract_info(url, download=False)
            dl.download(url)
    except:
        return False
    else:
        return info['title']
    
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
            info = dl.extract_info(f"ytsearch1:{term}", download=False)
    except:
        return False
    else:
        if info['entries']:
            url = "https://www.youtube.com/watch?v="+info['entries'][0]['id']
            return get_from_url_youtube(url, path)
        else:
            return False

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
                for idx, track in enumerate(result):
                    status = get_from_search_youtube(track, path+'-'+str(idx))
                    if status:
                        yield (path+'-'+str(idx), status)
                    else:
                        yield None
            else:
                yield None
        else:
            content = is_playlist(term)
            if content:
                for idx, entry in enumerate(content['entries']):
                    if get_from_url_youtube("https://www.youtube.com/watch?v="+entry['id'], path+'-'+str(idx)):
                        yield (path+'-'+str(idx), entry['title'])
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
