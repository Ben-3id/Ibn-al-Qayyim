import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8596129810:AAEs_-JObRhUggkkEfWx9ltSKmcgQnSNV-Q")
# Admin IDs - Comma separated list in env
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "8011237487,1118511024")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR.split(",") if i.strip()]
