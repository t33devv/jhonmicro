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

# loads the bot token from .env (create your own bot if you want to help with development)
load_dotenv()
token = os.getenv('TOKEN')

# loads the guild token from .env (create your own guild if you want to help with development)
guildObj = discord.Object(id=os.getenv('GUILD_ID'))

# connect to "database.sqlite"
database = sqlite3.connect('database.sqlite')
cursor = database.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS levels(user_id INTEGER, guild_id INTEGER, exp INTEGER, level INTEGER, last_lvl INTEGER)""")

class Client(commands.Bot):
    async def on_ready(self):
        print(f"ready when you are, {self.user.name}")

        # sync the slash commands
        try:
            guild = discord.Object(id=os.getenv('GUILD_ID'))
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    # ranking system
    async def on_message(self, message):
        levels_channel = self.get_channel(1255769461986951229)
        emoji = self.get_emoji(1380162985263366184)

        if message.author.bot:
            return
        
        cursor.execute(f"SELECT user_id, guild_id, exp, level, last_lvl FROM levels WHERE user_id = {message.author.id} AND guild_id = {message.guild.id}")
        result = cursor.fetchone()
        if result is None:
            cursor.execute(f"INSERT INTO levels(user_id, guild_id, exp, level, last_lvl) VALUES ({message.author.id}, {message.guild.id}, 0, 0, 0)")
        else:
            exp = result[2]
            level = result[3]
            last_lvl = result[4]
            
            exp_gained = random.randint(1, 20)
            exp += exp_gained

            lvl = 0.1 * math.sqrt(exp)

            cursor.execute(f"UPDATE levels SET exp = {exp}, level = {lvl}, last_lvl = {last_lvl} WHERE user_id = {message.author.id} AND guild_id = {message.guild.id}")
            database.commit()

            if int(lvl) > last_lvl:
                await levels_channel.send(f'{message.author.mention} has reached level {int(lvl)}! {emoji}')
                cursor.execute(f"UPDATE levels SET last_lvl = {int(lvl)} WHERE user_id = {message.author.id} AND guild_id = {message.guild.id}")
                database.commit()

    # some stupid testing stuff
    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send(f'{user.name} liked the message!')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = Client(command_prefix='!', intents=intents)

# below is all the slash commands

@client.tree.command(name='themes', description='Suggest a theme for all following events!', guild=guildObj)
async def themes(interaction: discord.Interaction):
    await interaction.response.send_message('Suggest a theme here: https://forms.gle/HeGESheR1Pb7fPeu9')

@client.tree.command(name='prerequisites', description='Suggest a theme for all following events!', guild=guildObj)
async def prerequisites(interaction: discord.Interaction):
    await interaction.response.send_message('Suggest a prerequisite here: https://forms.gle/eEyGmjeVzFXoed3c6')

@client.tree.command(name='rank', description='Check your rank!', guild=guildObj)
async def rank(interaction: discord.Interaction):
    rank = 1
    descending = 'SELECT * FROM levels WHERE guild_id = ? ORDER BY exp DESC'
    cursor.execute(descending, (interaction.guild.id,))
    result = cursor.fetchall()

    for i in range(len(result)):
        if result[i][0] == interaction.user.id:
            break
        else:
            rank += 1

    cursor.execute(f"SELECT exp, level, last_lvl FROM levels WHERE user_id = {interaction.user.id} AND guild_id = {interaction.guild.id}")
    result = cursor.fetchone()

    level = result[1]
    exp = result[0]
    last_lvl = result[2]

    next_lvl_xp = int((int(level) + 1) / 0.1) ** 2
    next_lvl_xp = int(next_lvl_xp)

    # use vacefron's RankCard to easily create the ranking graphic
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

# joining and leaving mechanics

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

# start the bot
    
client.run(token, log_handler=handler, log_level=logging.DEBUG)
