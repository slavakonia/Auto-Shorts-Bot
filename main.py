import os
import requests

print("🚀 Bot Auto Shorts démarré")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not GEMINI_API_KEY:
    raise Exception("❌ GEMINI_API_KEY manquante")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("❌ Telegram non configuré")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    requests.post(url, json=payload)

send_telegram("✅ GitHub Actions fonctionne ! Bot lancé avec succès.")
print("✅ Message Telegram envoyé")
