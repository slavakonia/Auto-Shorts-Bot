import os, json, time, requests, yt_dlp, feedparser
import google.generativeai as genai
# Note : Si MoviePy te pose problème sur GitHub, on peut utiliser FFmpeg direct, 
# mais restons sur MoviePy pour le moment.

# --- CONFIGURATION (Assure-toi que ces noms correspondent à tes Secrets GitHub) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def run_agent():
    print("🚀 Bot Auto Shorts démarré")
    send_tg("🤖 Bot en ligne. Analyse de ton lien en cours...")
    
    # On demande TOUS les messages non traités
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(tg_url).json()
    
    # --- LOG DE DEBUG DANS GITHUB ---
    print(f"DEBUG JSON REÇU : {json.dumps(response, indent=2)}")
    
    updates = response.get("result", [])
    if not updates:
        print("❌ Aucun message trouvé dans la file d'attente Telegram.")
        send_tg("⚠️ Je ne vois aucun nouveau lien. Renvoie-le moi sur Telegram !")
        return

    found_link = False
    # On parcourt les messages du plus récent au plus ancien
    for update in reversed(updates):
        msg = update.get("message", {}).get("text", "")
        print(f"Analyse du message : {msg}")
        
        if "youtube.com" in msg or "youtu.be" in msg:
            print(f"🎯 LIEN DÉTECTÉ : {msg}")
            send_tg(f"✅ Lien reçu : {msg}\nLancement de la découpe (10-20 Shorts)...")
            
            # Ici on appelle ta fonction de découpe (process_video)
            # Pour le test, on va juste simuler :
            print("Début du téléchargement et de l'analyse...")
            found_link = True
            break # On traite le lien le plus récent et on s'arrête
            
    if not found_link:
        print("🔍 Aucun lien YouTube dans les messages récents.")    prompt = "Analyse cette vidéo. Trouve les 15 segments les plus captivants (30-40s). Retourne UNIQUEMENT un JSON: [{'start': 10, 'end': 40, 'title': 'TITRE'}]"
    res = model.generate_content([prompt, vf])
    try:
        segments = json.loads(res.text.replace('```json', '').replace('```', '').strip())
    except:
        send_tg("❌ Erreur de lecture AI. Je réessaie avec 5 segments."); return

    # 3. Montage & Envoi
    for i, seg in enumerate(segments):
        try:
            clip = VideoFileClip(video_path).subclip(seg['start'], seg['end'])
            # Format Vertical
            w, h = clip.size
            clip = clip.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
            
            # Sous-titres + Progress Bar
            txt = create_subtitle(seg['title'], clip.duration)
            bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(clip.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / clip.duration)), 10])
            
            final = CompositeVideoClip([clip, txt, bar])
            out = f"short_{i}.mp4"
            final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
            
            with open(out, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"🔥 Short {i+1}/20\n{seg['title']}"})
            os.remove(out)
        except Exception as e: print(f"Erreur segment {i}: {e}")

    os.remove(video_path)
    send_tg("✅ Batch terminé ! 20 Shorts générés.")

def run_agent():
    print("🚀 Bot Auto Shorts démarré")
    
    # On demande les 50 derniers messages pour être sûr
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?limit=50"
    response = requests.get(tg_url).json()
    
    print(f"DEBUG: Nombre de messages trouvés : {len(response.get('result', []))}")
    
    found_link = False
    if "result" in response:
        # On parcourt du plus récent au plus ancien
        for update in reversed(response["result"]):
            msg = update.get("message", {}).get("text", "")
            print(f"DEBUG: Message analysé : {msg}") # Pour voir ce que le bot lit
            
            if "youtube.com" in msg or "youtu.be" in msg:
                print(f"🎯 LIEN TROUVÉ : {msg}")
                process_video(msg)
                found_link = True
                break 
    
    if not found_link:
        print("🔍 Aucun lien YouTube détecté dans les derniers messages.")

if __name__ == "__main__":
    run_agent()
