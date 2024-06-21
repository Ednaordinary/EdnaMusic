import os
import time
import asyncio
import threading
import nextcord as discord
from dotenv import load_dotenv
from downloader import authenticate_spotify, get_from_term
load_dotenv()
SPOTIFY_ID = os.getenv('SPOTIFY_ID')
SPOTIFY_TOKEN = os.getenv('SPOTIFY_TOKEN')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
client = discord.Client(intents=intents)

sp = authenticate_spotify(SPOTIFY_ID, SPOTIFY_TOKEN)
os.makedirs("./music", exist_ok=True)

session_channels = {}

def channel_watcher(guild):
    global session_channels
    proto = session_channels[guild][2]
    timeout = time.time() + 300
    while True:
        time.sleep(0.01)
        if time.time() > timeout and timeout != 0:
            asyncio.run_coroutine_threadsafe(coro=proto.disconnect(), loop=client.loop)
            asyncio.run_coroutine_threadsafe(coro=session_channels[0].send("No songs played in the last 5 minutes, disconnected!\nStart a new session to keep playing"), loop=client.loop)
            del session_channels[guild]
            return
        try:
            session_channels[guild]
        except:
            return
        if session_channels[guild][3] != []:
            if session_channels[guild][3][0] == True:
                timeout = 0 # prevent disconnecting after a download has been initiated
                session_channels[guild][3].pop(0)
            else:
                source = discord.FFmpegOpusAudio(session_channels[guild][3][0][0]+".mp3", bitrate=256)
                session_channels[guild][2].play(source)
                asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick="Playing " + session_channels[guild][3][0][1][-24:]), loop=client.loop)
                while session_channels[guild][2].is_playing():
                    time.sleep(0.01)
                session_channels[guild][3].pop(0)
                timeout = time.time() + 300
                asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick=None), loop=client.loop)

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

@client.slash_command(description="Starts a music session")
async def session(
        interaction: discord.Interaction,
        channel: discord.VoiceChannel, #discord.abc.GuildChannel,
):
    global session_channels
    try:
        session_channels[interaction.guild]
    except:
        session_running = False
    else:
        session_running = True
    if not session_running:
        original_message = await interaction.response.send_message("Starting a session in " + channel.name)
        original_message = await original_message.fetch()
        thread = await original_message.create_thread(name="Music Session")
        await thread.send("Send a link or search term here to start!")
        proto = await channel.connect()
        session_channels[interaction.guild] = (thread, channel, proto, [])
        threading.Thread(target=channel_watcher, args=[interaction.guild]).start()
    else:
        await interaction.response.send_message("This guild already has a session in progress!\n" + str(session_channels[interaction.guild][0].jump_url))

@client.event
async def on_message(message):
    global session_channels
    try:
        session = session_channels[message.guild]
    except:
        pass
    else:
        if message.channel == session[0] and message.author.id != client.user.id:
            session_channels[message.guild][3].append(True)
            async for song in get_from_term(message.content, "music/" + str(message.id), sp):
                if song is not None:
                    session_channels[message.guild][3].append(song)
                    await message.channel.send(song[1], fp=discord.File(song[0]+".mp3"), filename=song[1]+".mp3")
                else:
                    await message.channel.send("Something went wrong while downloading a song!")

client.run(DISCORD_TOKEN)
