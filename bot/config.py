import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
DATABASE_PATH = os.path.join(PROJECT_ROOT, os.getenv("DATABASE_PATH", "dreams.db"))
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "20"))
REMINDER_MINUTE = int(os.getenv("REMINDER_MINUTE", "0"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
