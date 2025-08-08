

import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import math
import random
import vacefron
import sqlite3
from vacefron import Rankcard
import time

load_dotenv()
token = os.getenv('TOKEN')
guildObj = discord.Object(id=os.getenv('GUILD_ID'))

database = sqlite3.connect('database.sqlite')
cursor = database.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS levels(user_id INTEGER, guild_id INTEGER, exp INTEGER, level INTEGER, last_lvl INTEGER)""")

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.leaderboard_cache = None
        self.leaderboard_cache_time = 0

    async def on_ready(self):
        print(f"ready when you are, {self.user.name}")
        try:
            guild = discord.Object(id=os.getenv('GUILD_ID'))
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author.bot:
            return
        
        cursor.execute(
            "SELECT user_id, guild_id, exp, level, last_lvl FROM levels WHERE user_id = ? AND guild_id = ?",
            (message.author.id,message.guild.id,)
        )
        result = cursor.fetchone()
        if result is None:
            cursor.execute(
                "INSERT INTO levels(user_id, guild_id, exp, level, last_lvl) VALUES (?, ?, 0, 0, 0)",
                (message.author.id,message.guild.id,)
            )
            database.commit()
        else:
            exp = result[2]
            level = result[3]
            last_lvl = result[4]
            
            exp_gained = random.randint(1, 20)
            exp += exp_gained

            lvl = 0.1 * math.sqrt(exp)

            cursor.execute(
                "UPDATE levels SET exp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                (exp,lvl,message.author.id,message.guild.id,)
            )
            database.commit()

            if int(lvl) > last_lvl:
                levels_channel = self.get_channel(1255769461986951229)
                emoji = self.get_emoji(1380162985263366184)
                await levels_channel.send(f'{message.author.mention} has reached level {int(lvl)}! {emoji}')
                cursor.execute(
                    "UPDATE levels SET last_lvl = ? WHERE user_id = ? AND guild_id = ?",
                    (int(lvl),message.author.id,message.guild.id,)
                )
                database.commit()

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send(f'{user.name} liked the message!')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = Client(command_prefix='!', intents=intents)

@client.tree.command(name='themes', description='Suggest a theme for all following events!', guild=guildObj)
async def themes(interaction: discord.Interaction):
    await interaction.response.send_message('Suggest a theme here: https://forms.gle/HeGESheR1Pb7fPeu9')

@client.tree.command(name='prerequisites', description='Suggest a prerequisite for all following events!', guild=guildObj)
async def prerequisites(interaction: discord.Interaction):
    await interaction.response.send_message('Suggest a prerequisite here: https://forms.gle/eEyGmjeVzFXoed3c6')

@client.tree.command(name='rules', description='Read Jam rules!', guild=guildObj)
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Micro Jam Rules",
        description="Please follow these rules to ensure a fun and fair jam for everyone!",
        color=discord.Color.blue()
    )
    embed.add_field(name="1. Keep the game content clean", value="No explicit, NSFW or disturbing graphics.", inline=False)
    embed.add_field(name="2. Keep the game in English", value="The title can be in any language, but the game itself must be in English.", inline=False)
    embed.add_field(name="3. Don't start early", value="All work on your game must happen within the 48-hour jam period.", inline=False)
    embed.add_field(name="4. Don't make changes after submission", value="Do not update or change your game after the 48-hour jam period has ended.", inline=False)
    
    if interaction.guild and interaction.guild.icon:
        embed.set_footer(text=f"Rules for {interaction.guild.name}", icon_url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)


@client.tree.command(name='rank', description='Check your rank!', guild=guildObj)
async def rank(interaction: discord.Interaction):
    rank = 1
    descending = 'SELECT * FROM levels WHERE guild_id = ? ORDER BY level DESC, exp DESC'
    cursor.execute(descending, (interaction.guild.id,))
    result = cursor.fetchall()

    for i in range(len(result)):
        if result[i][0] == interaction.user.id:
            break
        else:
            rank += 1

    cursor.execute(
        "SELECT exp, level, last_lvl FROM levels WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id,interaction.guild.id,)
    )
    result = cursor.fetchone()

    level = result[1]
    exp = result[0]
    last_lvl = result[2]

    next_lvl_xp = int((int(level) + 1) / 0.1) ** 2
    next_lvl_xp = int(next_lvl_xp)

    rank_card = Rankcard(
        username = interaction.user.display_name,
        avatar_url = interaction.user.avatar.url,
        current_xp = exp,
        next_level_xp = next_lvl_xp,
        previous_level_xp = 0,
        level = int(level),
        rank = rank,
    )

    card = await vacefron.Client().rankcard(rank_card)
    await interaction.response.send_message(card.url)

@client.tree.command(name='leaderboard', description='Check the top 10 users in the server!', guild=guildObj)
async def leaderboard(interaction: discord.Interaction):
    CACHE_DURATION = 300
    current_time = time.time()

    if client.leaderboard_cache and (current_time - client.leaderboard_cache_time < CACHE_DURATION):
        print("Leaderboard: Serving from cache.")
        await interaction.response.send_message(embed=client.leaderboard_cache)
        return

    print("Leaderboard: Generating new leaderboard and caching.")
    await interaction.response.defer()
    
    
    cursor.execute('SELECT * FROM levels WHERE guild_id = ? ORDER BY level DESC, exp DESC LIMIT 10', (interaction.guild.id,))
    result = cursor.fetchall()

    if not result:
        await interaction.followup.send("There are no users on the leaderboard yet!")
        return
    
    embed = discord.Embed(title=f"🏆 Leaderboard for {interaction.guild.name}", color=discord.Color.gold())

    try:
        top_user = await client.fetch_user(result[0][0])
        embed.set_thumbnail(url=top_user.display_avatar.url)
    except discord.NotFound:
        pass

    leaderboard_string = []
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(result):
        try:
            user = await client.fetch_user(row[0])
            rank_prefix = f"{medals[i]} " if i < 3 else f"**{i+1}.** "
            leaderboard_string.append(f"{rank_prefix}{user.mention} - Level: **{int(row[3])}** (XP: {row[2]})")
        except discord.NotFound:
            leaderboard_string.append(f"**{i+1}.** Unknown User - Level: **{int(row[3])}** (XP: {row[2]})")

    embed.description = "\n".join(leaderboard_string)
    embed.set_footer(text=f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    client.leaderboard_cache = embed
    client.leaderboard_cache_time = time.time()

    await interaction.followup.send(embed=embed)

@client.event
async def on_member_join(member):
    print(f'Welcome {member.mention} to the server!')
    welcome_channel = client.get_channel(1205736676706492447)
    emoji = member.guild.get_emoji(1286138480585474198)
    emoji2 = member.guild.get_emoji(1392388150315450469)
    emoji3 = member.guild.get_emoji(1286139570328436866)

    rules_link = '<#1190868996074000435>'
    general_link = '<#1190868996074000438>'

    embed = discord.Embed(
        title=f'{emoji2} Welcome {member.display_name}!',
        description=f"{emoji} Hope you enjoy your stay in **Micro Jam**!\nCheck out the {rules_link} channel to ensure you keep the server a fun and welcoming place!\nBe sure to talk with members in the {general_link} channel! Have fun :)",
        color=discord.Color.random()
    )

    embed.set_footer(text=f"You're the {member.guild.member_count:,}th member in the server!")
    embed.set_thumbnail(url=member.display_avatar.url)

    await welcome_channel.send(embed=embed)
    dmEmbed = discord.Embed(title = f"{emoji3} Welcome to the Micro Jam Discord, a friendly community that will *hopefully* excel your progress as a Developer :D")
    await member.send(embed=dmEmbed)

@client.event
async def on_member_remove(member):
    print(f'{member.name} has left the server!')
    leave_channel = client.get_channel(1205736676706492447)
    emoji = member.guild.get_emoji(1272841563952906260)

    embed = discord.Embed(title=f'{emoji} {member.name} has left the server!')

    await leave_channel.send(embed=embed)

if __name__ == "__main__":
    client.run(token, log_handler=handler, log_level=logging.DEBUG)
