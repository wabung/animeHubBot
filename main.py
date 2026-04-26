import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
dev_guild_id = os.getenv('DEV_GUILD_ID')

COGS = [
    'cogs.help',
    'cogs.info',
    # 'cogs.community',
    # 'cogs.games',
    'cogs.admin',
]

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        activity = discord.Game(name="/help")
        super().__init__(command_prefix='!', intents=intents, activity=activity)
        self.remove_command('help')

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)
        
        # Sync prefix/slash commands
        try:
            if dev_guild_id:
                guild = discord.Object(id=int(dev_guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"Synced {len(synced)} command(s) to DEV_GUILD.")
            else:
                synced = await self.tree.sync()
                print(f"Synced {len(synced)} global command(s).")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_command_error(self, ctx, error):
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

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')

    async def on_member_join(self, member):
        print(f'Welcome {member} to the server!')

if __name__ == '__main__':
    if not token:
        raise SystemExit("Error: DISCORD_TOKEN environment variable not set. Please set it in your .env file.")
    
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    bot = Bot()

    bot.run(token, log_handler=handler, log_level=logging.DEBUG)


