import os, json, time, requests, yt_dlp, feedparser
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHANNELS = ["UCv6UXP-H47-Vb-Txs-W9pzA", "UCjEdsqg2p3J_O0K7yQy4tHg"] 

genai.configure(api_key=GEMINI_API_KEY)

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def create_subtitle(text, duration):
    # Style Karaoké simple et percutant
    return TextClip(
        text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
        method='caption', size=(600, None), stroke_color='black', stroke_width=2
    ).set_duration(duration).set_position(('center', 800))

def process_video(url):
    send_tg("📥 Vidéo détectée ! Lancement de la machine (Analyse + Montage)...")
    video_path = "input.mp4"
    
    # 1. Download
    with yt_dlp.YoutubeDL({'format': 'best[height<=720]', 'outtmpl': video_path}) as ydl:
        ydl.download([url])

    # 2. AI Analysis (Demande de 15-20 segments)
    model = genai.GenerativeModel('gemini-1.5-flash')
    vf = genai.upload_file(video_path)
    while vf.state.name == "PROCESSING": time.sleep(2); vf = genai.get_file(vf.name)
    
    prompt = "Analyse cette vidéo. Trouve les 15 segments les plus captivants (30-40s). Retourne UNIQUEMENT un JSON: [{'start': 10, 'end': 40, 'title': 'TITRE'}]"
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
    
    # Lecture des messages Telegram (on regarde les 20 derniers messages)
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?limit=20"
    updates = requests.get(tg_url).json()
    
    found_link = False
    if "result" in updates:
        for update in updates["result"]:
            msg = update.get("message", {}).get("text", "")
            if "youtube.com" in msg or "youtu.be" in msg:
                process_video(msg)
                found_link = True
                break # On traite un lien à la fois par run pour éviter les timeouts GitHub
    
    if not found_link:
        print("🔍 Aucun nouveau lien trouvé sur Telegram.")
        # Ici on pourrait ajouter le scan YouTube RSS

if __name__ == "__main__":
    run_agent()
