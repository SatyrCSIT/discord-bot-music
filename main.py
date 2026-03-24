import discord
from discord.ext import commands
import logging
import colorlog
import asyncio
from aiohttp import web
from config.settings import settings


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            fmt=(
                "%(log_color)s%(bold)s%(levelname)-8s%(reset)s "
                "│ %(cyan)s%(asctime)s%(reset)s "
                "│ %(purple)s%(name)-20s%(reset)s "
                "│ %(log_color)s%(message)s%(reset)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "white",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger("bot")

intents = discord.Intents.all()


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def setup_hook(self):
        await self.load_extension("cogs.music")
        logger.info("📦 Loaded cog: music")

    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        logger.info(f"✅ Bot is ready. Logged in as {self.user}")
        logger.info(f"🌐 Servers: {len(self.guilds)} | Users: {len(self.users)}")


async def handle_ping(request):
    return web.Response(text="Bot is alive!")


async def run_webserver():
    app = web.Application()
    app.add_routes([web.get("/", handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("🌍 Web server started on port 8080")


async def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║         🎵  DAMKOENG MUSIC BOT  🎵              ║")
    print("║            พัฒนาโดย SUPERTONG                    ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    bot = MusicBot()
    await run_webserver()
    await bot.start(settings.TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped manually")
