import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8596129810:AAEs_-JObRhUggkkEfWx9ltSKmcgQnSNV-Q")
# Admin ID - Convert to int safely
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8011237487"))
