import os, json, time, requests, yt_dlp
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION (Secrets GitHub) ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)

def send_tg(text):
    """Envoie un message texte sur Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": text})

def create_subtitle(text, duration):
    """Crée le style de sous-titre Karaoké (Jaune/Noir)"""
    return TextClip(
        text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
        method='caption', size=(600, None), stroke_color='black', stroke_width=2
    ).set_duration(duration).set_position(('center', 800))

def process_video(url):
    """Télécharge, analyse et découpe la vidéo en Shorts"""
    send_tg("🚀 Lien reçu ! Tentative de téléchargement (Contournement YouTube)...")
    video_path = "input.mp4"
    
    # BLOC CORRIGÉ POUR ÉVITER L'ERREUR "SIGN IN TO CONFIRM YOU'RE NOT A BOT"
    ydl_opts = {
        'format': 'best[height<=720]',
        'outtmpl': video_path,
        'quiet': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web_embedded']
            }
        },
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        send_tg(f"❌ Erreur de téléchargement : {str(e)}")
        return

    # 1. Analyse avec Gemini
    send_tg("🧠 Analyse IA en cours pour extraire 15-20 moments viraux...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    video_file = genai.upload_file(video_path)
    
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    prompt = "Find 15 viral segments (30s each). Return ONLY a JSON list: [{'start': 10, 'end': 40, 'title': 'HOOK'}]"
    response = model.generate_content([prompt, video_file])
    
    try:
        # Nettoyage de la réponse pour extraire le JSON
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        segments = json.loads(raw_text)
    except Exception as e:
        send_tg("❌ Erreur d'analyse JSON de l'IA. Fin du processus.")
        return

    # 2. Montage des Shorts
    send_tg(f"🎬 Montage lancé : {len(segments)} vidéos en préparation...")
    full_clip = VideoFileClip(video_path)
    
    for i, seg in enumerate(segments):
        try:
            # Découpe et passage en format vertical (9:16)
            short = full_clip.subclip(seg['start'], seg['end'])
            w, h = short.size
            short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
            
            # Ajout des sous-titres et de la barre de progression
            txt = create_subtitle(seg['title'], short.duration)
            bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
            
            final = CompositeVideoClip([short, txt, bar])
            output_name = f"short_{i}.mp4"
            final.write_videofile(output_name, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast")
            
            # Envoi sur Telegram
            with open(output_name, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                              files={'video': f}, 
                              data={'chat_id': TG_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
            
            os.remove(output_name)
        except Exception as e:
            print(f"Erreur sur le segment {i}: {e}")

    # Nettoyage final
    full_clip.close()
    os.remove(video_path)
    send_tg("✅ Terminé ! Tous tes Shorts sont sur Telegram.")

def run_agent():
    """Vérifie les nouveaux messages sur Telegram"""
    print("🤖 Bot actif, vérification des messages...")
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?limit=10"
    resp = requests.get(url).json()
    
    found_link = False
    if "result" in resp:
        for update in reversed(resp["result"]):
            msg = update.get("message", {}).get("text", "")
            if "youtube.com" in msg or "youtu.be" in msg:
                process_video(msg)
                found_link = True
                break
    
    if not found_link:
        print("🔍 Aucun lien YouTube trouvé.")

if __name__ == "__main__":
    run_agent()
