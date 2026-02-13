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
    try:
        return TextClip(
            text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
            method='caption', size=(600, None), stroke_color='black', stroke_width=2
        ).set_duration(duration).set_position(('center', 800))
    except Exception as e:
        print(f"Erreur TextClip (ImageMagick?) : {e}")
        return None

def process_video(url):
    """Télécharge, analyse et découpe la vidéo en Shorts"""
    send_tg("🚀 Lien reçu ! Connexion sécurisée à YouTube via Cookies...")
    video_path = "input.mp4"
    
    # OPTIONS DE TÉLÉCHARGEMENT AVEC COOKIES ET AGENT UTILISATEUR
    ydl_opts = {
        'format': 'best[height<=720]',
        'outtmpl': video_path,
        'quiet': True,
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt',  # <--- UTILISE LE FICHIER CRÉÉ PAR GITHUB ACTIONS
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web_embedded']
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        send_tg(f"❌ Erreur de téléchargement (même avec cookies) : {str(e)}")
        return

    # 1. Analyse avec Gemini 1.5 Flash
    send_tg("🧠 Analyse IA par Gemini en cours (recherche de moments viraux)...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    try:
        video_file = genai.upload_file(video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        prompt = "Trouve 10 moments viraux de 30 secondes. Répond UNIQUEMENT avec un JSON: [{'start': 10, 'end': 40, 'title': 'TITRE'}]"
        response = model.generate_content([prompt, video_file])
        
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        segments = json.loads(raw_text)
    except Exception as e:
        send_tg(f"❌ Erreur Gemini : {str(e)}")
        return

    # 2. Montage des Shorts
    send_tg(f"🎬 Montage de {len(segments)} Shorts en format vertical...")
    
    try:
        full_clip = VideoFileClip(video_path)
        
        for i, seg in enumerate(segments):
            try:
                # Découpe + Format Vertical 9:16
                short = full_clip.subclip(seg['start'], seg['end'])
                w, h = short.size
                short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
                
                # Sous-titres Karaoké
                txt = create_subtitle(seg['title'], short.duration)
                
                # Barre de progression jaune en bas
                bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
                
                if txt:
                    final = CompositeVideoClip([short, txt, bar])
                else:
                    final = CompositeVideoClip([short, bar])
                
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
        
        full_clip.close()
    except Exception as e:
        send_tg(f"❌ Erreur Montage : {str(e)}")

    # Nettoyage
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists('cookies.txt'):
        os.remove('cookies.txt')
        
    send_tg("✅ Terminé ! Tous les Shorts ont été envoyés.")

def run_agent():
    """Vérifie les nouveaux liens sur Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?limit=5"
    try:
        resp = requests.get(url).json()
        if "result" in resp:
            for update in reversed(resp["result"]):
                msg = update.get("message", {}).get("text", "")
                if "youtube.com" in msg or "youtu.be" in msg:
                    process_video(msg)
                    return
    except Exception as e:
        print(f"Erreur bot : {e}")

if __name__ == "__main__":
    run_agent()
