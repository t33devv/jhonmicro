## the one and only JhonMicro 🤖

a discord.py bot for my itch.io game jam [Micro Jam](https://discord.com/servers/micro-jam-1190868995226730616), where anyone can help with development!

### Installation (cloning the repo)

```bash
git clone https://github.com/t33devv/jhonmicro.git
```

## How to help with Development/Contribution

1. Fork the repository

Start by clicking the "fork" button on github

```bash
git clone https://github.com/your_username/jhonmicro.git
cd jhonmicro
```

2. Create a new feature branch
```bash
git checkout -b feat/your-feature-name
```

3. Commit your changes
```bash
# check where you made edits
git status

# stage changes
git add main.py           # or anywhere else you made changes

# write a good commit message
git commit -m "added slash command to view all micro jams"
```

4. Push to the branch
```bash
git push origin feat/your-feature-name
```

5. Open a Pull Request from Github

## Quick Start the Bot (E.G. if you want to use this as a template for your own bot)
1. Create a Discord bot from the [Discord Developer Portal](https://discord.com/developers/applications)
  - Add the bot to any server you like (create a new one for testing purposes)

2. Create a .env file:
  - Create a file in the jhonmicro folder called .env
  - Add these lines in the file, replacing the token and guild (server) ID with your bot token and server id respectively
```bash
TOKEN = your_token_here
GUILD_ID = your_discord_server_id_here
```
*to get the guild_id you'll need discord developer mode which can be turned on in your profile settings*

3. If you don't have UV, run:
```bash
pip install uv
uv version
```

4. Navigate to your project folder, and run:
```bash
uv run main.py
```

5. Now the bot should be live in the server you put as the GUILD_ID, have fun testing!

## Documentation

This bot was made with discord.py, so to help with development, please refer to the [Discord.py documentation](https://discordpy.readthedocs.io/en/stable/).
They have tons of examples of code for existing features.

## Support

If you have any questions about this, feel free to join our [Discord Server](https://discord.com/servers/micro-jam-1190868995226730616) and ping me (@t33dev) or any other staff!

## Made with ❤️ by Tommy and the Micro Jam community


