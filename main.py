import os, json, requests, yt_dlp
import google.generativeai as genai

# Config
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def run_debug():
    print("🚀 Bot Auto Shorts démarré")
    
    # 1. Envoi d'un signal de vie
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  data={"chat_id": CHAT_ID, "text": "🔎 Je cherche ton lien dans la boîte aux lettres..."})

    # 2. Récupération des messages avec un "offset" pour forcer la lecture
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?limit=10&allowed_updates=['message']"
    resp = requests.get(url).json()
    
    # ON AFFICHE TOUT DANS LES LOGS GITHUB
    print(f"DEBUG - Réponse Telegram : {json.dumps(resp, indent=2)}")

    if not resp.get("result"):
        print("❌ Boîte aux lettres vide.")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": "❌ Je ne vois rien ! Renvoie-moi le lien YouTube MAINTENANT stp."})
        return

    for update in resp["result"]:
        msg = update.get("message", {}).get("text", "")
        print(f"Analyse du message : {msg}")
        if "youtube.com" in msg or "youtu.be" in msg:
            print(f"🎯 LIEN TROUVÉ : {msg}")
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": f"✅ Trouvé ! Je lance la création des 20 shorts pour : {msg}"})
            # Ici on lancerait la fonction de découpe
            return

if __name__ == "__main__":
    run_debug()
