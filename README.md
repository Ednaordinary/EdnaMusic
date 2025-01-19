# EdnaMusic

## One command, endless music

![image](https://github.com/user-attachments/assets/4724f7cf-3e42-4bf9-b02d-b1f08522fab7)

Supports both YouTube and Spotify songs and playlists.
Demystifing music bots by giving you a single command: /session

Want more songs? Send a link or search term in the thread

Want to skip, pause, or disconnect? Buttons!

### Run

`git clone https://github.com/Ednaordinary/EdnaMusic`

`cd EdnaMusic`

Make and enter a virtual environment of your choice.

Place the following tokens in a .env:

"DISCORD_TOKEN": The token for your discord bot

"SPOTIFY_ID": A developer spotify api id

"SPOTIFY_TOKEN": The token for that id

`pip install -r requirements.txt`

`python3 ./main.py`

### Use

Run /session with your desired channel

In the thread it creates, send youtube links, spotify links, or search terms for the bot to play
