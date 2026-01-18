import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8596129810:AAEs_-JObRhUggkkEfWx9ltSKmcgQnSNV-Q")
# Admin IDs - Comma separated list in env
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "1118511024,8509361750,8011237487")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR.split(",") if i.strip()]

# Supabase Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://symrfxnfvmwksewpjkgc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN5bXJmeG5mdm13a3Nld3Bqa2djIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODcwOTQ0OCwiZXhwIjoyMDg0Mjg1NDQ4fQ.pOZysfpF13Ys9aGN0_WAdnhIXBHUYv13o8BqBt7xF14")
