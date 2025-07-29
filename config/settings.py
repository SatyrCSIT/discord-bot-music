import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    TOKEN = os.getenv("DISCORD_TOKEN")
    MUSIC_ROOM_PREFIX = "🎵"


settings = Settings()
