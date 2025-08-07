import discord
from discord.ext import commands
import logging
import asyncio
from aiohttp import web
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("bot")

intents = discord.Intents.all()


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def setup_hook(self):
        await self.load_extension("cogs.music")
        logger.info("Loaded cog: music")

    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        logger.info(f"Bot is ready. Logged in as {self.user}")


async def handle_ping(request):
    return web.Response(text="Bot is alive!")


async def run_webserver():
    app = web.Application()
    app.add_routes([web.get("/", handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Web server started on port 8080")


async def main():
    bot = MusicBot()
    await run_webserver()
    await bot.start(settings.TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
