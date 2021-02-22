# Chromey McChromeface
![](https://media.discordapp.net/attachments/688121419980341282/787792406443458610/gggggggir.png)

Moderation bot for r/ChromeOS

### Prerequisites for setup
- Python
- `poetry`
- `pyenv`
- MongoDB server

### Setup
1. `pyenv install 3.9.1`
2. `pyenv shell`
3. `poetry install` (use flag `--no-dev` for prod)
4. `poetry shell`
5. Create a file called `.env`. in the root of the project and define the following:
```
CHROMEY_TOKEN      = "DISCORD TOKEN"
CHROMEY_OWNER      = OWNER ID (int)
CHROMEY_MAINGUILD  = MAIN GUILD ID (int)
```

6. Set up mongodb on your system (and see *First time use* to populate the database with initial data)
7. `python main.py` - if everything was set up properly you're good to go!

### First time use

If you don't have any baseline data for the bot to work, I wrote a short script `setup.py` which you should fill in with data from your own server, then run `python setup.py`
