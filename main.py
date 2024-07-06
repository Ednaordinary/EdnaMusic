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
current_song_message = {}

def channel_watcher(guild):
    global session_channels
    global current_song_message
    proto = session_channels[guild][2]
    timeout = time.time() + 300
    while True:
        time.sleep(0.01)
        if time.time() > timeout and timeout != 0:
            asyncio.run_coroutine_threadsafe(coro=proto.disconnect(), loop=client.loop)
            asyncio.run_coroutine_threadsafe(coro=session_channels[guild].send("No songs played in the last 5 minutes, disconnected!\nStart a new session to keep playing"), loop=client.loop)
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
                asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick="Playing " + session_channels[guild][3][0][1][:24]), loop=client.loop)
                try:
                    asyncio.run_coroutine_threadsafe(coro=add_next_button(current_song_message[guild.id][0][0], guild), loop=client.loop)
                except: pass # the song message may not have been sent yet
                try:
                    while session_channels[guild][2].is_playing():
                        time.sleep(0.01)
                except: return
                os.remove(session_channels[guild][3][0][0]+".mp3")
                session_channels[guild][3].pop(0)
                timeout = time.time() + 300
                asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick=None), loop=client.loop)
                try:
                    asyncio.run_coroutine_threadsafe(coro=remove_view(current_song_message[guild.id][0][0]), loop=client.loop)
                    current_song_message[guild.id].pop(0)
                except: # the song message still may not have been sent yet
                    pass

class MusicActions(discord.ui.View):
    def __init__(self, *, timeout=None, guild):
        super().__init__(timeout=timeout)
        self.guild = guild
    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global session_channels
        global current_song_message
        thread = session_channels[self.guild][0]
        proto = session_channels[self.guild][2]
        queue = session_channels[self.guild][3]
        del session_channels[self.guild]
        await proto.disconnect()
        try:
            await thread.send("Session ended.")
        except: pass # thread may no longer exist
        for child in self.children:
            child.disabled = True
        button.label = "Stopped"
        await interaction.response.edit_message(view=self)
        await self.guild.me.edit(nick=None)
        for path, name in [x for x in queue if x is not True]:
            os.remove(path+".mp3")
        for message in [x[0] for x in current_song_message[self.guild.id]]:
            try:
                await message.edit(view=None)
            except: pass # messages may no longer exist
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global session_channels
        proto = session_channels[self.guild][2]
        queue = session_channels[self.guild][3]
        proto.stop()
        await interaction.response.pong()

class NextButton(discord.ui.View):
    def __init__(self, *, timeout=None, guild):
        super().__init__(timeout=timeout)
        self.guild = guild
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global session_channels
        proto = session_channels[self.guild][2]
        queue = session_channels[self.guild][3]
        proto.stop()
        await interaction.response.edit_message(view=None)

class RemoveButton(discord.ui.View):
    def __init__(self, *, timeout=None, song, guild):
        super().__init__(timeout=timeout)
        self.song = song
        self.guild = guild
    @discord.ui.button(label="Remove", style=discord.ButtonStyle.red)
    async def remove_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global session_channels
        global current_song_message
        try:
            song_index = session_channels[self.guild][3].index(self.song)
            if song_index:
                session_channels[self.guild][3].pop(song_index)
                button.disabled = True
                await interaction.response.edit_message(content="Removed " + str(self.song[1]) + " from the queue.", view=self)
                try:
                    song_index = [x[1] for x in current_song_message[self.guild.id]].index(self.song)
                except:
                    pass
            else:
                await interaction.response.edit_message(content="Song not found in the queue.")
        except:
            await interaction.response.edit_message(content="Song not found in the queue.")

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')
    for guild in client.guilds:
        if guild.me.nick != None:
            await guild.me.edit(nick=None)

@client.slash_command(description="Starts a music session")
async def session(
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
):
    global session_channels
    global current_song_message
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
        current_song_message[interaction.guild.id] = []
        threading.Thread(target=channel_watcher, args=[interaction.guild]).start()
        await original_message.edit(view=MusicActions(guild=interaction.guild))
    else:
        await interaction.response.send_message("This guild already has a session in progress!\n" + str(session_channels[interaction.guild][0].jump_url))

async def song_send(message, name, path, delete, song, guild):
    global current_song_message
    if current_song_message[guild.id] == []:
        current_song_message[guild.id].append((await message.channel.send(name, file=discord.File(fp=path+".mp3", filename=name+".mp3"), view=NextButton(guild=guild)), song))
    else:
        current_song_message[guild.id].append((await message.channel.send(name, file=discord.File(fp=path + ".mp3", filename=name + ".mp3"), view=RemoveButton(song=song, guild=guild)), song))
    if delete: os.remove(path+".mp3")

async def add_next_button(message, guild):
    await message.edit(view=NextButton(guild=guild))

async def remove_view(message):
    await message.edit(view=None)

async def async_downloader(term, path, message):
    global session_channels
    continue_queue = True
    async for song in get_from_term(term, path, sp):
        if song is not None:
            try:
                if continue_queue:
                    session_channels[message.guild][3].append(song)
            except:
                continue_queue = False
                asyncio.run_coroutine_threadsafe(coro=song_send(message, song[1], song[0], True, song, message.guild), loop=client.loop)
                pass
            else:
                if continue_queue:
                    asyncio.run_coroutine_threadsafe(coro=song_send(message, song[1], song[0], False, song, message.guild), loop=client.loop)
                else:
                    asyncio.run_coroutine_threadsafe(coro=song_send(message, song[1], song[0], True, song, message.guild), loop=client.loop)
        else:
            asyncio.run_coroutine_threadsafe(coro=message.channel.send("Something went wrong while downloading a song!"), loop=client.loop)

def threaded_downloader(term, path, message):
    #Ensures the downloading happens outside of the bot event loop so stuff doesn't block
    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_downloader(term, path, message))

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
            threading.Thread(target=threaded_downloader, args=[message.content, "music/" + str(message.id), message]).start()


client.run(DISCORD_TOKEN)
