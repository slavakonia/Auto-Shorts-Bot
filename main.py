import os, json, time, requests, yt_dlp
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_CHAT_ID, "text": text})

def create_sub(text, duration):
    return TextClip(text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
                    method='caption', size=(600, None), stroke_color='black', stroke_width=2).set_duration(duration).set_position(('center', 800))

def process_video(url):
    send_tg(f"🎯 Lien YouTube détecté ! Préparation de la génération (10-20 Shorts)... 🚀")
    video_path = "input.mp4"
    
    # 1. Téléchargement
    with yt_dlp.YoutubeDL({'format': 'best[height<=720]', 'outtmpl': video_path}) as ydl:
        ydl.download([url])

    # 2. IA Gemini
    send_tg("🧠 L'IA analyse la vidéo pour trouver les moments viraux...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    vf = genai.upload_file(video_path)
    while vf.state.name == "PROCESSING": time.sleep(2); vf = genai.get_file(vf.name)
    
    prompt = "Trouve les 15 moments les plus viraux (30s chacun). Format JSON: [{'start': 10, 'end': 40, 'title': 'HOOK'}]"
    res = model.generate_content([prompt, vf])
    segments = json.loads(res.text.replace('```json', '').replace('```', '').strip())

    # 3. Montage Karaoké
    send_tg(f"🎬 Début du montage de {len(segments)} shorts...")
    full_clip = VideoFileClip(video_path)
    
    for i, seg in enumerate(segments):
        short = full_clip.subclip(seg['start'], seg['end'])
        # Vertical 9:16
        w, h = short.size
        short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
        
        # Subs + Progress Bar
        txt = create_sub(seg['title'], short.duration)
        bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
        
        final = CompositeVideoClip([short, txt, bar])
        out = f"short_{i}.mp4"
        final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None)
        
        with open(out, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TG_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
        os.remove(out)

    os.remove(video_path)
    send_tg("✅ Terminé ! Tes shorts sont arrivés.")

def run_agent():
    print("🚀 Bot Démarré")
    # On force la lecture des messages
    updates = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?limit=50").json()
    
    found = False
    for u in reversed(updates.get("result", [])):
        msg = u.get("message", {}).get("text", "")
        if "youtube.com" in msg or "youtu.be" in msg:
            process_video(msg)
            found = True
            break
            
    if not found:
        send_tg("🕵️ Je suis allumé, mais je ne vois AUCUN lien YouTube dans notre discussion. Renvoie-le moi maintenant !")

if __name__ == "__main__":
    run_agent()
