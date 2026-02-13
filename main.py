import os, json, time, requests, yt_dlp
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)

def send_tg_msg(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": text})

def create_karaoke_sub(text, duration):
    # Style Karaoké : Jaune, Gras, Contour noir
    return TextClip(
        text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
        method='caption', size=(600, None), stroke_color='black', stroke_width=2
    ).set_duration(duration).set_position(('center', 800))

def process_video(url):
    send_tg_msg("🚀 Lien reçu ! Téléchargement et analyse en cours...")
    video_path = "input.mp4"
    
    # 1. Download
    with yt_dlp.YoutubeDL({'format': 'best[height<=720]', 'outtmpl': video_path, 'quiet': True}) as ydl:
        ydl.download([url])

    # 2. IA Gemini pour segments
    model = genai.GenerativeModel('gemini-1.5-flash')
    video_file = genai.upload_file(video_path)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    prompt = "Trouve les 15 moments les plus viraux (30s chacun). Format JSON strict: [{'start': 10, 'end': 40, 'title': 'HOOK'}]"
    response = model.generate_content([prompt, video_file])
    segments = json.loads(response.text.replace('```json', '').replace('```', '').strip())

    # 3. Montage
    send_tg_msg(f"🎬 Génération de {len(segments)} Shorts avec sous-titres...")
    clip = VideoFileClip(video_path)
    
    for i, seg in enumerate(segments):
        # Découpe + Format Vertical
        short = clip.subclip(seg['start'], seg['end'])
        w, h = short.size
        short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
        
        # Subs + Progress Bar
        txt = create_karaoke_sub(seg['title'], short.duration)
        bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
        
        final = CompositeVideoClip([short, txt, bar])
        out_name = f"short_{i}.mp4"
        final.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", logger=None)
        
        # Envoi Telegram
        with open(out_name, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                          files={'video': f}, data={'chat_id': TG_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
        os.remove(out_name)

    os.remove(video_path)
    send_tg_msg("✅ Tous les shorts sont prêts !")

def run():
    print("🤖 Bot en cours de vérification...")
    # On regarde les 20 derniers messages sur Telegram
    updates = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?limit=20").json()
    for u in reversed(updates.get("result", [])):
        msg = u.get("message", {}).get("text", "")
        if "youtube.com" in msg or "youtu.be" in msg:
            process_video(msg)
            return # On traite un lien à la fois

if __name__ == "__main__":
    run()
