import os, json, time, requests, yt_dlp
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)

def send_tg(text):
    """Envoie un message de statut sur Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": text})

def create_subtitle(text, duration):
    """Crée un sous-titre style Karaoké (Jaune/Noir)"""
    try:
        return TextClip(
            text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
            method='caption', size=(600, None), stroke_color='black', stroke_width=2
        ).set_duration(duration).set_position(('center', 800))
    except Exception as e:
        print(f"Erreur ImageMagick: {e}")
        return None

def process_video(file_path):
    """Analyse avec Gemini et découpe en Shorts"""
    # 1. Vérification du fichier
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
        send_tg("❌ Erreur : Le fichier vidéo est vide ou corrompu.")
        return

    # Crucial : Laisser le temps au système de finaliser l'écriture du fichier
    time.sleep(3)

    send_tg("🧠 Analyse IA (Gemini 1.5 Flash) en cours...")
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    try:
        video_file = genai.upload_file(file_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        prompt = """Analysez cette vidéo. Trouvez 5 segments viraux de 30 secondes.
        Répondez UNIQUEMENT avec un JSON pur :
        [{"start": 10, "end": 40, "title": "HOOK"}]"""
        
        response = model.generate_content([prompt, video_file])
        res_text = response.text.strip()
        
        # Nettoyage JSON
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
            
        segments = json.loads(res_text)
    except Exception as e:
        send_tg(f"❌ Erreur IA ou JSON : {str(e)}")
        return

    send_tg(f"🎬 Montage de {len(segments)} Shorts lancé...")
    
    try:
        # Ouverture avec gestion de contexte pour libérer le fichier à la fin
        with VideoFileClip(file_path) as clip:
            for i, seg in enumerate(segments):
                try:
                    # Découpe + Format Vertical 9:16
                    short = clip.subclip(seg['start'], seg['end'])
                    w, h = short.size
                    short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
                    
                    # Sous-titres & Barre de progression
                    txt = create_subtitle(seg['title'], short.duration)
                    bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
                    
                    final = CompositeVideoClip([short, txt, bar] if txt else [short, bar])
                    
                    out_name = f"short_{i}.mp4"
                    final.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast")
                    
                    # Envoi Telegram
                    with open(out_name, 'rb') as f:
                        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                                      files={'video': f}, 
                                      data={'chat_id': TG_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
                    os.remove(out_name)
                except Exception as e:
                    print(f"Erreur segment {i}: {e}")
    except Exception as e:
        send_tg(f"❌ Erreur Montage (MoviePy) : {str(e)}")

    # Nettoyage final
    if os.path.exists(file_path):
        os.remove(file_path)
    send_tg("✅ Processus terminé !")

def run():
    print("🤖 Bot actif, vérification du dernier message...")
    # Offset -1 pour récupérer le dernier message (vidéo ou lien)
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?offset=-1"
    
    try:
        resp = requests.get(url).json()
        if "result" in resp and len(resp["result"]) > 0:
            msg = resp["result"][0].get("message", {})
            
            # CAS 1 : VIDÉO ENVOYÉE DIRECTEMENT
            if "video" in msg:
                send_tg("📥 Vidéo reçue ! Téléchargement...")
                file_id = msg["video"]["file_id"]
                file_info = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getFile?file_id={file_id}").json()
                
                if not file_info.get("ok"):
                    send_tg("❌ Erreur : Fichier trop lourd (> 20Mo).")
                    return

                dl_url = f"https://api.telegram.org/file/bot{TG_TOKEN}/{file_info['result']['file_path']}"
                r = requests.get(dl_url, stream=True)
                with open("input.mp4", "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024): # 1Mo par 1Mo
                        if chunk: f.write(chunk)
                
                process_video("input.mp4")
                
            # CAS 2 : LIEN YOUTUBE
            elif "text" in msg and ("youtube.com" in msg["text"] or "youtu.be" in msg["text"]):
                send_tg("🔗 Lien YouTube détecté ! Téléchargement...")
                ydl_opts = {
                    'format': 'best[height<=720]',
                    'outtmpl': 'input.mp4',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'quiet': True,
                    'noplaylist': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([msg["text"]])
                process_video("input.mp4")
        else:
            print("🔍 Aucun nouveau message.")
    except Exception as e:
        print(f"Erreur Run: {e}")

if __name__ == "__main__":
    run()
