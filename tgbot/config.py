import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
COOKIES_DIR = "sessions"

# Sessions papkasini avtomatik yaratish
os.makedirs(COOKIES_DIR, exist_ok=True)