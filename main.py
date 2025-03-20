import os
import shutil
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
#current_song_message = {}
currently_downloading = {}

def channel_watcher(guild, thread_message):
    global session_channels
    global currently_downloading
    proto = session_channels[guild][2]
    timeout = time.time() + 1800
    while True:
        time.sleep(0.01)
        if time.time() > timeout and timeout != 0:
            if currently_downloading[guild.id] > 0:
                timeout = time.time() + 1800
            else:
                asyncio.run_coroutine_threadsafe(coro=proto.disconnect(), loop=client.loop)
                asyncio.run_coroutine_threadsafe(coro=session_channels[guild][0].send("No songs played in the last 30 minutes, disconnected!\nStart a new session to keep playing"), loop=client.loop)
                on_session_end(guild)
                asyncio.run_coroutine_threadsafe(coro=thread_message.edit(view=MusicActionsDisabled), loop=client.loop) # If the message was sent over 15 minutes ago, this may not work. At least me try, though
                return
        try:
            session_channels[guild]
        except:
            return
        if session_channels[guild][3] != []:
            #if session_channels[guild][3][0] == True:
            #    timeout = 0 # prevent disconnecting after a download has been initiated
            #    session_channels[guild][3].pop(0)
            #else:
            song = session_channels[guild][3][0].song
            song_message = session_channels[guild][3][0].message
            source = discord.FFmpegOpusAudio(song[0]+".mp3", bitrate=256)
            session_channels[guild][2].play(source)
            asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick="Playing " + song[1][:24]), loop=client.loop)
            #try:
            #    asyncio.run_coroutine_threadsafe(coro=add_next_button(current_song_message[guild.id][0][0], guild), loop=client.loop)
            #except: pass # the song message may not have been sent yet
            asyncio.run_coroutine_threadsafe(coro=add_next_button(song_message, guild),
                                             loop=client.loop)
            proto = session_channels[guild][2]
            try:
                while proto.is_playing() or proto.is_paused():
                    time.sleep(0.01)
            except:
                if not proto.is_connected():
                    asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick=None), loop=client.loop)
                    on_session_end(guild)
                    asyncio.run_coroutine_threadsafe(coro=thread_message.edit(view=MusicActionsDisabled),
                                                     loop=client.loop)  # If the message was sent over 15 minutes ago, this may not work. At least me try, though
                return
            if not proto.is_connected():
                asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick=None), loop=client.loop)
                on_session_end(guild)
                asyncio.run_coroutine_threadsafe(coro=thread_message.edit(view=MusicActionsDisabled),
                                                 loop=client.loop)  # If the message was sent over 15 minutes ago, this may not work. At least me try, though
                return
            os.remove(song[0]+".mp3")
            session_channels[guild][3].pop(0)
            timeout = time.time() + 1800
            if session_channels[guild][3] == []:
                asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick=None), loop=client.loop)
            #try:
            #    asyncio.run_coroutine_threadsafe(coro=remove_view(current_song_message[guild.id][0][0]), loop=client.loop)
            #    current_song_message[guild.id].pop(0)
            #except: # the song message still may not have been sent yet
            #    pass
            asyncio.run_coroutine_threadsafe(coro=remove_view(song_message), loop=client.loop)

class MusicActionsDisabled(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)
    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red, disabled=True)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, disabled=True)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass
    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary, disabled=True)
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

class MusicActions(discord.ui.View):
    def __init__(self, *, timeout=None, guild):
        super().__init__(timeout=timeout)
        self.guild = guild
    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = True
        button.label = "Stopped"
        await interaction.response.edit_message(view=self)
        on_session_end(self.guild)
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global session_channels
        proto = session_channels[self.guild][2]
        proto.stop()
        await interaction.response.pong()
    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary)
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        global session_channels
        proto = session_channels[self.guild][2]
        if not proto.is_paused():
            proto.pause()
            button.label = "Resume"
            await interaction.response.edit_message(view=self)
        else:
            proto.resume()
            button.label = "Pause"
            await interaction.response.edit_message(view=self)

class SongRequest:
    def __init__(self, song, message):
        self.song = song
        self.message = message

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
        try:
            song_index = [x.song for x in session_channels[self.guild][3]].index(self.song)
            if song_index:
                session_channels[self.guild][3].pop(song_index)
                button.disabled = True
                await interaction.response.edit_message(content="Removed " + str(self.song[1]) + " from the queue.", view=self)
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
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Can't start a session in this channel")
        return
    global session_channels
    #global current_song_message
    global currently_downloading
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
        #current_song_message[interaction.guild.id] = []
        currently_downloading[interaction.guild.id] = 0
        threading.Thread(target=channel_watcher, args=[interaction.guild, original_message]).start()
        await original_message.edit(view=MusicActions(guild=interaction.guild))
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
            #session_channels[message.guild][3].append(True)
            threading.Thread(target=threaded_downloader, args=[message.content, "music/" + str(message.guild.id) + "/" + str(message.id), message]).start()

def on_session_end(guild):
    global session_channels
    try:
        thread = session_channels[guild][0]
        proto = session_channels[guild][2]
        queue = session_channels[guild][3]
        del session_channels[guild]
        asyncio.run_coroutine_threadsafe(coro=proto.disconnect(), loop=client.loop)
        try:
            asyncio.run_coroutine_threadsafe(coro=thread.send("Session ended."), loop=client.loop)
        except:
            pass  # thread may no longer exist
        asyncio.run_coroutine_threadsafe(coro=guild.me.edit(nick=None), loop=client.loop)
        for file in os.listdir("music/" + str(guild.id)): # Prevent deleting music that is still downloading
            if file.endswith(".mp3"):
                os.remove(os.path.join("music/"+ str(guild.id) + "/" + file))
        for message in [x.message for x in queue]:
            try:
                asyncio.run_coroutine_threadsafe(coro=message.edit(view=None), loop=client.loop)
            except:
                pass  # messages may no longer exist
    except Exception as e:
        print(repr(e))
        # This method may be called by multiple places on a session end

async def send_song_message(message, song, button):
    name = song[1]
    guild = message.guild
    global session_channels
    if button:
        sent_message = await message.channel.send(name, view=RemoveButton(song=song, guild=guild))
        return sent_message
    else:
        sent_message = await message.channel.send(name)
        return sent_message

async def edit_song_message(message, song):
    name = song[1]
    path = song[0]
    #global current_song_message
    try:
        await message.edit(file=discord.File(fp=path + ".mp3", filename=name + ".mp3"))
    except Exception as e:
        print(repr(e))

async def add_next_button(message, guild):
    await message.edit(view=NextButton(guild=guild))

async def remove_view(message):
    await message.edit(view=None)

async def async_downloader(term, path, message):
    global session_channels
    global currently_downloading
    add_to_queue = True #
    currently_downloading[message.guild.id] += 1
    async for song in get_from_term(term, path, sp):
        if song is not None:
            if add_to_queue:
                sent_message = asyncio.run_coroutine_threadsafe(coro=send_song_message(message, song, True), loop=client.loop).result()
                try:
                    session_channels[message.guild][3].append(SongRequest(song=song, message=sent_message))
                except:
                    add_to_queue = False
                    pass
            else:
                sent_message = asyncio.run_coroutine_threadsafe(coro=send_song_message(message, song, False),
                                                                loop=client.loop).result()
            asyncio.run_coroutine_threadsafe(coro=edit_song_message(sent_message, song), loop=client.loop)
        else:
            asyncio.run_coroutine_threadsafe(coro=message.channel.send("Something went wrong while downloading a song!"), loop=client.loop)
    currently_downloading[message.guild.id] -= 1

def threaded_downloader(term, path, message):
    #Ensures the downloading happens outside of the bot event loop so stuff doesn't block
    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_downloader(term, path, message))


client.run(DISCORD_TOKEN)
