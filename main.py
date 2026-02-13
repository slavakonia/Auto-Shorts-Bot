import os, json, time, requests
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_CHAT_ID, "text": text})

def create_subtitle(text, duration):
    try:
        return TextClip(
            text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
            method='caption', size=(600, None), stroke_color='black', stroke_width=2
        ).set_duration(duration).set_position(('center', 800))
    except: return None

def process_video_file(file_path):
    """La logique de découpe reste la même une fois le fichier obtenu"""
    send_tg("🧠 Analyse IA par Gemini en cours...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    video_file = genai.upload_file(file_path)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    prompt = "Trouve 10 moments viraux de 30s. Répond UNIQUEMENT avec un JSON: [{'start': 10, 'end': 40, 'title': 'TITRE'}]"
    response = model.generate_content([prompt, video_file])
    segments = json.loads(response.text.replace('```json', '').replace('```', '').strip())

    send_tg(f"🎬 Montage de {len(segments)} Shorts...")
    full_clip = VideoFileClip(file_path)
    
    for i, seg in enumerate(segments):
        short = full_clip.subclip(seg['start'], seg['end'])
        w, h = short.size
        short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
        
        txt = create_subtitle(seg['title'], short.duration)
        bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
        
        final = CompositeVideoClip([short, txt, bar]) if txt else CompositeVideoClip([short, bar])
        out = f"short_{i}.mp4"
        final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast")
        
        with open(out, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TG_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
        os.remove(out)
    
    full_clip.close()
    os.remove(file_path)
    send_tg("✅ Terminé !")

def run_agent():
    print("🤖 Bot en attente de fichier ou lien...")
    resp = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?limit=5").json()
    
    if "result" in resp:
        for update in reversed(resp["result"]):
            msg = update.get("message", {})
            
            # CAS 1 : C'est une vidéo directe
            if "video" in msg:
                send_tg("📥 Vidéo reçue en direct ! Téléchargement depuis Telegram...")
                file_id = msg["video"]["file_id"]
                file_info = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getFile?file_id={file_id}").json()
                file_path_tg = file_info["result"]["file_path"]
                
                download_url = f"https://api.telegram.org/file/bot{TG_TOKEN}/{file_path_tg}"
                r = requests.get(download_url)
                with open("input.mp4", "wb") as f:
                    f.write(r.content)
                
                process_video_file("input.mp4")
                return

            # CAS 2 : C'est un lien YouTube (On garde l'ancienne méthode au cas où)
            text = msg.get("text", "")
            if "youtube.com" in text or "youtu.be" in text:
                send_tg("🔗 Lien reçu ! (Note : Si ça échoue, envoie la vidéo directement)")
                # ... (Ici ton ancienne logique yt-dlp si tu veux la garder)
                return

if __name__ == "__main__":
    run_agent()
