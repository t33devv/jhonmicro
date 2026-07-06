import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import math
import random
import sqlite3
import time

# loads the bot token from .env (create your own bot if you want to help with development)
load_dotenv()
token = os.getenv('TOKEN')

# loads the guild token from .env (create your own guild if you want to help with development)
guildObj = discord.Object(id=os.getenv('GUILD_ID'))

# connect to "database.sqlite"
database = sqlite3.connect('database.sqlite')
cursor = database.cursor()

# create table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS levels(
    user_id INTEGER,
    guild_id INTEGER,
    exp INTEGER,
    level INTEGER,
    last_lvl INTEGER,
    coins INTEGER DEFAULT 0,
    last_daily INTEGER DEFAULT 0
)
""") 

try:
    cursor.execute("ALTER TABLE levels ADD COLUMN coins INTEGER DEFAULT 0") # COINS
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE levels ADD COLUMN last_daily INTEGER DEFAULT 0") # DAILY SYS
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE levels ADD COLUMN messages INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE levels ADD COLUMN characters INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

database.commit()

class Client(commands.Bot):
    welcome_channel:discord.TextChannel = None
    leave_channel:discord.TextChannel = None
    levels_channel:discord.TextChannel = None
    log_channel: discord.TextChannel = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.leaderboard_cache = {}
        self.leaderboard_cache_time = {}

    async def on_ready(self):
        """
            Prints the bot's username and syncs slash commands
            (called automatically)
        """
        print(f"ready when you are, {self.user.name}")

        print("Fetching channels")
        self.welcome_channel = await client.fetch_channel(os.getenv("WELCOME_CHANNEL_ID"))
        self.leave_channel = await client.fetch_channel(os.getenv("LEAVE_CHANNEL_ID"))
        self.levels_channel = await client.fetch_channel(os.getenv("LEVEL_CHANNEL_ID"))

        self.log_channel = await client.fetch_channel(os.getenv("LOG_CHANNEL_ID"))

        # sync the slash commands
        try:
            guild = discord.Object(id=os.getenv('GUILD_ID'))
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')


    # ranking system
async def on_message(self, message):

    emoji = self.get_emoji(1380162985263366184)

    if message.author.bot:
        return

    # Remove spaces and keep only letters/numbers
    clean = "".join(c for c in message.content if c.isalnum())

    char_count = len(clean)

    cursor.execute(
        """
        SELECT exp, level, last_lvl, messages, characters
        FROM levels
        WHERE user_id = ? AND guild_id = ?
        """,
        (message.author.id, message.guild.id)
    )

    result = cursor.fetchone()

    if result is None:

        messages = 1
        characters = char_count

        exp = int(
            messages * 15
            + math.sqrt(characters) * 6
            + math.log2(messages + 1) * 75
        )

        level = 0.1 * math.sqrt(exp)

        cursor.execute(
            """
            INSERT INTO levels
            (
                user_id,
                guild_id,
                exp,
                level,
                last_lvl,
                coins,
                last_daily,
                messages,
                characters
            )
            VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?)
            """,
            (
                message.author.id,
                message.guild.id,
                exp,
                level,
                messages,
                characters
            )
        )

        database.commit()
        return

    exp, level, last_lvl, messages, characters = result

    messages += 1
    characters += char_count

    exp = int(
        messages * 15
        + math.sqrt(characters) * 6
        + math.log2(messages + 1) * 75
    )

    level = 0.1 * math.sqrt(exp)

    cursor.execute(
        """
        UPDATE levels
        SET
            exp = ?,
            level = ?,
            messages = ?,
            characters = ?
        WHERE user_id = ? AND guild_id = ?
        """,
        (
            exp,
            level,
            messages,
            characters,
            message.author.id,
            message.guild.id
        )
    )

    database.commit()

    if int(level) > last_lvl:

        await self.levels_channel.send(
            f"{message.author.mention} has reached level {int(level)}! {emoji}"
        )

        cursor.execute(
            """
            UPDATE levels
            SET last_lvl = ?
            WHERE user_id = ? AND guild_id = ?
            """,
            (
                int(level),
                message.author.id,
                message.guild.id
            )
        )

        database.commit()

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = Client(command_prefix='!', intents=intents)

def get_balance(user_id, guild_id):
    cursor.execute(
        "SELECT coins FROM levels WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id)
    )
    result = cursor.fetchone()

    if result is None:
        return 0

    return result[0]

# slash commands

@client.tree.command(name='cookie', description='Cookie.', guild=guildObj)
async def cookie(interaction: discord.Interaction):
    """
        Send a hidden message saying just a Cookie
        (called when a slash command is used)

        Args:
            interaction(discord.Interaction):
                The interaction that triggered this slash command
    """

    await interaction.response.send_message(
        "https://klipy.com/gifs/rickroll-never-gonna-give-you-up-9",
        ephemeral=True
    )

@client.tree.command(name='themes', description='Suggest a theme for all following events!', guild=guildObj)
async def themes(interaction: discord.Interaction):
    """
        Send a link to the theme suggestion form
        (called when a slash command is used)

        Args:
            interaction (discord.Interaction):
                The interaction that triggered this slash command
    """
    embed = discord.Embed(
        description=(
            "# 📋 Theme Suggestion!\n"
            "### Suggest *your* **theme** here:\n"
            "### https://forms.gle/HeGESheR1Pb7fPeu9"
        ),
        color=discord.Color.yellow(),
    )
    embed.set_thumbnail(url=interaction.guild.icon.url)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"Suggest for {interaction.guild.name}", icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)

@client.tree.command(name='prerequisites', description='Suggest a prerequisite for all following events!', guild=guildObj)
async def prerequisites(interaction: discord.Interaction):
    """
        Send a link to the prerequisite suggestion form
        (called when a slash command is used)

        Args:
            interaction (discord.Interaction):
                The interaction that triggered this slash command
    """
    embed = discord.Embed(
        description=(
            "# 📋 Prerequisite Suggestion!\n"
            "### Suggest *your* **prerequisite** here:\n"
            "### https://forms.gle/eEyGmjeVzFXoed3c6"
        ),
        color=discord.Color.yellow(),
    )

    embed.set_thumbnail(url=interaction.guild.icon.url)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"Suggest for {interaction.guild.name}", icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)

@client.tree.command(name='rules', description='Read Jam rules!', guild=guildObj)
async def rules(interaction: discord.Interaction):
    """
        Send an embedded message with the server's jam rules
        (called when a slash command is used)

        Args:
            interaction (discord.Interaction):
                The interaction that triggered this slash command
    """
    embed = discord.Embed(
        description=(
            "# 📜 Micro Jam Rules! \n"
            "### Please follow these rules to ensure a fun and fair jam for everyone!"
        ),
        color=discord.Color.orange()
    )
    embed.add_field(name="1. *Keep* the game content **clean**", value="> **No** *explicit, NSFW* or *disturbing graphics.*", inline=False)
    embed.add_field(name="2. *Keep* the game in **English**", value="> *Only* the **title** can be a *different* **language**", inline=True)
    embed.add_field(name="3. Add *late* **submissions**", value="> You are *allowed* to submit an **entry**, *6 hours* after the Jam **ends**", inline=False)
    embed.add_field(name="4. **No changes** after the jam *ends*", value="> *Game files* are **locked** after the jam *ends*", inline=True)
    embed.add_field(name="5. *Submissions* in a **category**", value="> You *can't* win *2 prizes* in the *same* **category**", inline=False)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"Rules for {interaction.guild.name}", icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)

@client.tree.command(name='rank', description='Check your rank!', guild=guildObj)
async def rank(interaction: discord.Interaction):
    """
        Display your rank, level, XP progress and Coins.
    """

    cursor.execute(
        "SELECT exp, level, last_lvl, coins FROM levels WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id, interaction.guild.id,)
    )
    result = cursor.fetchone()

    if result is None:
        await interaction.response.send_message("You haven't earned any XP yet.")
        return

    exp = result[0]
    level = int(result[1])
    coins = result[3]

    # Talking leaderboard
    cursor.execute(
        "SELECT user_id, exp, level FROM levels WHERE guild_id = ? ORDER BY level DESC, exp DESC",
        (interaction.guild.id,)
    )
    leaderboard = cursor.fetchall()

    rank = 1
    for row in leaderboard:
        if row[0] == interaction.user.id:
            break
        rank += 1

    total_users = len(leaderboard)

    # XP calculations
    previous_level_xp = int((level / 0.1) ** 2)
    next_level_xp = int(((level + 1) / 0.1) ** 2)

    current_level_xp = exp - previous_level_xp
    needed_xp = next_level_xp - previous_level_xp

    progress = current_level_xp / needed_xp if needed_xp > 0 else 1

    BAR_LENGTH = 30

    filled = int(progress * BAR_LENGTH)
    filled = max(0, min(BAR_LENGTH, filled))

    bar = "█" * filled + "░" * (BAR_LENGTH - filled)

    embed = discord.Embed(
        description=(
            f"# 🏆 {interaction.user.mention}'s Rank\n"
            f"> 🪙 **Coins**: {coins:,} · 🏅 **Rank:** #{rank}\n"
            f"### ⭐ **Progress**\n"
            f"### `{bar}` **{progress * 100:.0f}% (LEVEL {level})**\n"
            f"> **{exp:,} / {next_level_xp:,}**"
        ),
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"Continue talking in {interaction.guild.name}", icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)

@client.tree.command(name='leaderboard', description='View the server leaderboards!', guild=guildObj)
@app_commands.describe(type="Which leaderboard would you like to view?")
@app_commands.choices(type=[
    app_commands.Choice(name="🏅 Talking", value="talking"),
    app_commands.Choice(name="🪙 Richest", value="richest"),
])
async def leaderboard(
    interaction: discord.Interaction,
    type: app_commands.Choice[str] = None
):
    
    if type is None:
        leaderboard_type = "talking"
    else:
        leaderboard_type = type.value

    CACHE_DURATION = 300
    current_time = time.time()

    cache_key = leaderboard_type

    if (
        client.leaderboard_cache
        and client.leaderboard_cache_time
        and cache_key in client.leaderboard_cache
        and current_time - client.leaderboard_cache_time.get(cache_key, 0) < CACHE_DURATION
    ):
        await interaction.response.send_message(
            embed=client.leaderboard_cache[cache_key]
        )
        return

    await interaction.response.defer()

    if leaderboard_type == "talking":
        cursor.execute(
            """
            SELECT *
            FROM levels
            WHERE guild_id = ?
            ORDER BY level DESC, exp DESC
            LIMIT 10
            """,
            (interaction.guild.id,)
        )

        title = "# 🏅 Talking Leaderboard"

    else:
        cursor.execute(
            """
            SELECT *
            FROM levels
            WHERE guild_id = ?
            ORDER BY coins DESC
            LIMIT 10
            """,
            (interaction.guild.id,)
        )

        title = "# 🪙 Richest Leaderboard"

    result = cursor.fetchall()

    if not result:
        await interaction.followup.send("Nobody is on the leaderboard yet.")
        return

    medals = ["🥇", "🥈", "🥉"]

    lines = []

    for i, row in enumerate(result):

        try:
            user = await client.fetch_user(row[0])
            name = user.mention
        except:
            name = "Unknown User"

        if i < 3:
            prefix = medals[i]
        else:
            prefix = f"**{i+1}.**"

        if leaderboard_type == "talking":
            lines.append(
                f"{prefix} {name} ┃ Level **{int(row[3])}** • **{row[2]:,} XP** "
            )
        else:
            lines.append(
                f"{prefix} {name} ┃ 🪙 **{row[5]:,} Coins**"
            )

    embed = discord.Embed(
        description=(
            f"{title}\n"
            + "\n\n".join(lines)
        ),
        color=discord.Color.gold()
    )

    try:
        top_user = await client.fetch_user(result[0][0])
        embed.set_thumbnail(url=top_user.display_avatar.url)
    except:
        pass

    embed.set_footer(text="Updates every 5 minutes.")

    if client.leaderboard_cache is None:
        client.leaderboard_cache = {}

    if not isinstance(client.leaderboard_cache_time, dict):
        client.leaderboard_cache_time = {}

    client.leaderboard_cache[cache_key] = embed
    client.leaderboard_cache_time[cache_key] = time.time()

    await interaction.followup.send(embed=embed)

@client.tree.command(name='daily', description='Claim your daily Coins!', guild=guildObj)
async def daily(interaction: discord.Interaction):
    """
        Claim a daily reward every 16 hours.

        Args:
            interaction (discord.Interaction):
                The interaction that triggered this slash command
    """

    cursor.execute(
        "SELECT coins, last_daily FROM levels WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id, interaction.guild.id,)
    )
    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            """
            INSERT INTO levels
            (user_id, guild_id, exp, level, last_lvl, coins, last_daily)
            VALUES (?, ?, 0, 0, 0, 0, 0)
            """,
            (interaction.user.id, interaction.guild.id,)
        )
        database.commit()

        coins = 0
        last_daily = 0
    else:
        coins = result[0]
        last_daily = result[1]

    current_time = int(time.time())
    cooldown = 16 * 60 * 60

    if current_time - last_daily < cooldown:
        remaining = cooldown - (current_time - last_daily)

        next_claim = last_daily + cooldown

        titles = [
            "Doofus.",
            "Already?",
            "Seriously?",
            "Slow down.",
            "Nice try."
        ]

        embed = discord.Embed(
            description=(
                f"# ❌ {random.choice(titles)}\n"
                "> You've already **claimed** your *daily reward*.\n"
                f"## ⏰ Claim again <t:{next_claim}:R>"
            ),
            color=discord.Color.red()
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        if interaction.guild and interaction.guild.icon:
            embed.set_footer(
                text=f"{interaction.user.display_name}'s Daily Reward",
                icon_url=interaction.guild.icon.url
            )

        await interaction.response.send_message(embed=embed)
        return

    chance = random.randint(1, 100)

    if chance <= 2:
        reward = random.randint(4000, 5000)

        description = random.choice([
            "# 🎊 JACKPOT! \n> *We* ***love*** **gambling.**",
            "# 🍀 Beginner's Luck \n> *Unless* you're **not** a *beginner.*",
            "# 🍶 Potion of Luck IV \n> *Ever* heard of ***minecraft?***",
            "# 🎊 NO WAY! \n> I *really* **dont** know how **you** do it."
        ])

        color = discord.Color.gold()

    elif chance <= 22:
        reward = random.randint(200, 600)

        description = random.choice([
            "# 😔 Could've been worse.\n> Could've been *better...*",
            "# 👍 Not bad. \n> At least it's **free.**",
            "# 🫶 Better luck next time! \n> Every Coin *counts.*"
        ])

        color = discord.Color.orange()

    else:
        reward = random.randint(600, 1000)

        description = random.choice([
            "# ☀️ Daily!\n> *Here* is your **everyday** *daily.*",
            "# 💸 Payday!\n> ***Job? Job? Job?***",
            "# 🍀 Lucky!\n> *Luck* is on *your* **side!**",
            "# 🤑 Money!\n> We ***LOVE*** *money*."
        ])

        color = discord.Color.green()

    coins += reward

    cursor.execute(
        """
        UPDATE levels
        SET coins = ?, last_daily = ?
        WHERE user_id = ? AND guild_id = ?
        """,
        (
            coins,
            current_time,
            interaction.user.id,
            interaction.guild.id
        )
    )

    remaining = cooldown - (current_time - last_daily)

    next_claim = last_daily + cooldown

    database.commit()

    embed = discord.Embed(
        description=(
            f"{description} *You've* gained **{reward:,} coins**\n"
            f"## **New Balance:** 🪙 {coins:,} Coins \n"
            f"> Claim again <t:{next_claim}:R>"
        ),
        color=color
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"Continue gambling in {interaction.guild.name}", icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)

@client.tree.command(name="coin", description="Get ten coins if you are BROKE", guild=guildObj)
async def coin(interaction: discord.Interaction):

    cursor.execute(
        "SELECT coins FROM levels WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id, interaction.guild.id)
    )

    result = cursor.fetchone()

    if result is None:
        await interaction.response.send_message(
            "You don't have an account yet. Try **/daily** first.",
            ephemeral=True
        )
        return

    coins = result[0]

    if coins > 0:
        embed = discord.Embed(
            description=(
                "# 💸 Nice try.\n"
                "> You can only use ***`/coin`*** when *you're* **completely** **broke**.\n"
                f"## 🏦 Balance: {coins:,} Coins"
            ),
            color=discord.Color.red()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_footer(
                text=f"Go back to gambling in {interaction.guild.name}", icon_url=interaction.guild.icon.url
            )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        return

    coins = 10

    cursor.execute(
        """
        UPDATE levels
        SET coins = ?
        WHERE user_id = ? AND guild_id = ?
        """,
        (coins, interaction.user.id, interaction.guild.id)
    )

    database.commit()

    embed = discord.Embed(
        description=(
            "# 🪙 Charity\n"
            "> Here's ***10 coins***. *Now* go back to **gambling!** \n"
            f"## 🏦 Balance: {coins:,} Coins"
        ),
        color=discord.Color.green()
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(
            text=f"Continue gambling in {interaction.guild.name}", icon_url=interaction.guild.icon.url
        )

    await interaction.response.send_message(embed=embed)

@client.tree.command(name="gamble", description="Gamble your Coins!", guild=guildObj)
@app_commands.describe(amount="Amount of Coins to gamble. (e.g. 500, 50.5, max, all, half)")
async def gamble(interaction: discord.Interaction, amount: str):

    cursor.execute(
        "SELECT coins FROM levels WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id, interaction.guild.id)
    )

    data = cursor.fetchone()

    if data is None:
        await interaction.response.send_message(
            "Use **/daily** first.",
            ephemeral=True
        )
        return

    coins = data[0]

    amount = amount.lower().strip()

    # Special words
    if amount in ("max", "all"):
        amount = coins

    elif amount == "half":
        amount = coins / 2

    else:
        try:
            amount = float(amount)
        except ValueError:
            await interaction.response.send_message(
                "❌ ***Invalid amount***",
                ephemeral=True
            )
            return

    amount = int(amount)

    if amount <= 0:
        await interaction.response.send_message(
            "❌ ***Invalid amount***",
            ephemeral=True
        )
        return

    if amount > coins:
        await interaction.response.send_message(
            "❌ ***Invalid amount***",
            ephemeral=True
        )
        return

    # Find talking rank
    cursor.execute(
        "SELECT user_id FROM levels WHERE guild_id = ? ORDER BY level DESC, exp DESC",
        (interaction.guild.id,)
    )

    users = cursor.fetchall()

    rank = 1
    for i, user in enumerate(users):
        if user[0] == interaction.user.id:
            rank = i + 1
            break

    total = len(users)

    multiplier = 1.0

    if total > 0:
        percent = rank / total

        if percent <= 0.10:
            multiplier = 2.0
        elif percent <= 0.25:
            multiplier = 1.75
        elif percent <= 0.50:
            multiplier = 1.5
        elif percent <= 0.75:
            multiplier = 1.25

    if random.randint(1, 2) == 1:

        winnings = int(amount * multiplier)
        coins += winnings

        title = "🎉 You Won!"
        result = f"+{winnings:,} Coins"
        colour = discord.Color.green()

    else:

        coins -= amount

        title = "💔 You Lost!"
        result = f"-{amount:,} Coins"
        colour = discord.Color.red()

    cursor.execute(
        "UPDATE levels SET coins = ? WHERE user_id = ? AND guild_id = ?",
        (coins, interaction.user.id, interaction.guild.id)
    )

    database.commit()

    embed = discord.Embed(
        description=(
            f"# {title}\n## {result}\n"
            f"> 🏆 Talking Rank: **#{rank}/{total}**\n"
            f"> ⭐ Win Multiplier: **{multiplier:.2f}x**\n"
            f"## 🏦 Balance: **{coins:,} Coins**"
        ),
        color=colour
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    if interaction.guild and interaction.guild.icon:
        embed.set_footer(
            text=f"Gamble more in {interaction.guild.name}", icon_url=interaction.guild.icon.url
        )

    await interaction.response.send_message(embed=embed)

@app_commands.default_permissions(administrator=True)
@client.tree.command(
    name="rebuildxp",
    description="Rebuild XP from all existing messages.",
    guild=guildObj
)
async def rebuildxp(interaction: discord.Interaction):

    # Only you can use it
    if interaction.user.id not in (1223919866445172787, 1310021022208229398):
        await interaction.response.send_message(
            "No.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Rebuilding XP... This may take a while.",
        ephemeral=True
    )

    stats = {}

    for channel in interaction.guild.text_channels:

        try:
            async for message in channel.history(limit=None, oldest_first=True):

                if message.author.bot:
                    continue

                clean = "".join(c for c in message.content if c.isalnum())

                if message.author.id not in stats:
                    stats[message.author.id] = {
                        "messages": 0,
                        "characters": 0
                    }

                stats[message.author.id]["messages"] += 1
                stats[message.author.id]["characters"] += len(clean)

        except discord.Forbidden:
            continue

        except Exception as e:
            print(f"{channel.name}: {e}")

    for user_id, data in stats.items():

        messages = data["messages"]
        characters = data["characters"]

        exp = int(
            messages * 15
            + math.sqrt(characters) * 6
            + math.log2(messages + 1) * 75
        )

        level = 0.1 * math.sqrt(exp)

        cursor.execute(
            """
            UPDATE levels
            SET
                exp=?,
                level=?,
                last_lvl=?,
                messages=?,
                characters=?
            WHERE user_id=? AND guild_id=?
            """,
            (
                exp,
                level,
                int(level),
                messages,
                characters,
                user_id,
                interaction.guild.id
            )
        )

    database.commit()

    await interaction.followup.send(
        f"✅ Finished rebuilding XP for **{len(stats)} users.**"
    )

# scam kick (honeypot)

SCAM_KICK_CHANNEL_ID = int(os.getenv("SCAM_KICK_CHANNEL_ID", "0"))

cursor.execute("""
CREATE TABLE IF NOT EXISTS scamkick_stats(
    guild_id INTEGER PRIMARY KEY,
    kicks INTEGER DEFAULT 0
)
""")
database.commit()

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == SCAM_KICK_CHANNEL_ID:

        if message.author.guild_permissions.manage_messages:
            return

        cursor.execute(
            """
            INSERT INTO scamkick_stats (guild_id, kicks)
            VALUES (?, 1)
            ON CONFLICT(guild_id)
            DO UPDATE SET kicks = kicks + 1
            """,
            (message.guild.id,)
        )
        database.commit()

        cursor.execute(
            "SELECT kicks FROM scamkick_stats WHERE guild_id = ?",
            (message.guild.id,)
        )
        kick_count = cursor.fetchone()[0]

        await message.guild.ban(
            message.author,
            reason="Triggered Scam-Kick.",
            delete_message_seconds=3600
        )

        await message.guild.unban(
            message.author,
            reason="Scam-Kick temporary ban."
        )

        embed = discord.Embed(
            description=(
                "# 🛡️ Scam-Kick Triggered\n"
                f"**User:** {message.author.mention}\n"
                f"**ID:** `{message.author.id}`\n"
                f"**Channel:** {message.channel.mention}\n\n"
                "🧹 Deleted messages from the last **1 hour**.\n"
                f"📊 **Total Scammers Caught:** **{kick_count:,}**"
            ),
            color=discord.Color.red()
        )

        embed.set_thumbnail(url=message.author.display_avatar.url)

        if getattr(client, "log_channel", None):
            await client.log_channel.send(embed=embed)

        return

    await Client.on_message(client, message)


@client.tree.command(
    name="setup_scamkick",
    description="Posts the Scam-Kick warning message.",
    guild=guildObj
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_scamkick(interaction: discord.Interaction):

    cursor.execute(
        "SELECT kicks FROM scamkick_stats WHERE guild_id = ?",
        (interaction.guild.id,)
    )

    result = cursor.fetchone()
    kick_count = result[0] if result else 0

    embed = discord.Embed(
        description=(
            "# ⚠️ DO NOT SEND MESSAGES HERE\n\n"
            "This channel is used to catch *spam bots*. Any messages sent here will result in a ***softban.*** \n"
            f"## Scammers Caught: {kick_count:,}"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Micro Jam • Automatic Scam Protection")

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message(
        "✅ a cookie said that scam kicker message is created",
        ephemeral=True
    )

#joining and leaving mechanics

@client.event
async def on_member_join(member:discord.Member):
    """
        Send a welcome message in the welcome channel
        (called automatically)

        Args:
            member (discord.Member):
                The user that joined the server
    """
    print(f'Welcome {member.mention} to the server!')
    emoji = member.guild.get_emoji(1286138480585474198)
    emoji2 = member.guild.get_emoji(1392388150315450469)
    emoji3 = member.guild.get_emoji(1286139570328436866)

    rules_link = '<#1190868996074000435>'
    general_link = '<#1190868996074000438>'

    embed = discord.Embed(
        description=(
            f"# {emoji2} Welcome {member.display_name}!\n"
            f"{emoji} Hope you **enjoy** *your* stay in ***Micro Jam***!\n"
            f"*Check out* the **{rules_link} channel** to ensure you keep **the server** a *fun* and *welcoming place!*\n"
            f"Be *sure* to **talk** with *members* in the **{general_link} channel!** ***Have fun :)***"
        ),
        color=discord.Color.random()
    )

    embed.set_footer(text=f"You're the {member.guild.member_count:,}th member in the server!")
    embed.set_thumbnail(url=member.display_avatar.url)

    await client.welcome_channel.send(embed=embed)
    dmEmbed = discord.Embed(title = f"{emoji3} *Welcome* to the **Micro Jam Discord Server**, a *friendly community* that will *hopefully* **excel** *your* progress as a ***Developer*** **:D**")
    await member.send(embed=dmEmbed)

@client.event
async def on_member_remove(member:discord.Member):
    """
        Send a leave message in the leave channel
        (called automatically)

        Args:
            member (discord.Member):
                The user that left the server
    """
    print(f'{member.name} has left the server!')
    emoji = member.guild.get_emoji(1272841563952906260)

    embed = discord.Embed(title=f'{emoji} {member.name} has left the server!')

    await client.leave_channel.send(embed=embed)

if __name__ == "__main__":
    # start the bot if run directly
    client.run(token, log_handler=handler, log_level=logging.DEBUG)
