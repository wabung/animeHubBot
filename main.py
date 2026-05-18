import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from services import BackendClient

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
dev_guild_id = os.getenv('DEV_GUILD_ID')

COGS = [
    'cogs.help',
    'cogs.info',
    # 'cogs.community',
    'cogs.games',
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
        self.backend = BackendClient()
        self._lang_cache: dict[int, str] = {}

    async def get_lang(self, guild_id: int) -> str:
        """Return the configured language for a guild, defaulting to 'en'."""
        if guild_id not in self._lang_cache:
            config = await self.backend.get_guild_config(guild_id)
            self._lang_cache[guild_id] = (config or {}).get("language", "en")
        return self._lang_cache[guild_id]

    def set_lang(self, guild_id: int, lang: str):
        """Update the in-memory language cache after a setlang command."""
        self._lang_cache[guild_id] = lang

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)

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

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        for guild in self.guilds:
            await self.backend.register_guild(guild.id, guild.name)
            print(f'  Registered guild: {guild.name}')

    async def on_guild_join(self, guild: discord.Guild):
        await self.backend.register_guild(guild.id, guild.name)

    async def on_member_join(self, member: discord.Member):
        await self.backend.register_user(member.id, member.name)

    async def close(self):
        await self.backend.close()
        await super().close()

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


if __name__ == '__main__':
    if not token:
        raise SystemExit("Error: DISCORD_TOKEN environment variable not set. Please set it in your .env file.")

    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    bot = Bot()
    bot.run(token, log_handler=handler, log_level=logging.DEBUG)
