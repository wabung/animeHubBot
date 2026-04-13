import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

COGS = [
    'cogs.help',
    'cogs.info',
    'cogs.community',
    'cogs.games',
    'cogs.admin',
]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.event
async def on_member_join(member):
    print(f'Welcome {member} to the server!')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(
            description=f"Command not found. Use `!help` to see available commands.",
            color=discord.Color.red()
        ))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing required arguments. Use `!help {ctx.command}` for more info.",
            color=discord.Color.orange()
        ))
    else:
        print(f'Error in command {ctx.command}: {error}')



bot.run(token, log_handler=handler, log_level=logging.DEBUG)