import os, json, time, requests, yt_dlp
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def create_subtitle(text, duration):
    # Style Karaoké Viral
    return TextClip(
        text.upper(), font='Arial-Bold', fontsize=70, color='yellow',
        method='caption', size=(600, None), stroke_color='black', stroke_width=2
    ).set_duration(duration).set_position(('center', 800))

def process_video(url):
    send_tg(f"🎯 Lien détecté ! Préparation de la génération (15-20 Shorts)... 🚀")
    video_path = "input.mp4"
    
    # 1. Téléchargement
    ydl_opts = {'format': 'best[height<=720]', 'outtmpl': video_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # 2. Analyse IA Gemini
    send_tg("🧠 L'IA analyse la vidéo pour trouver les moments viraux...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    video_file = genai.upload_file(video_path)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    prompt = "Trouve les 15-20 moments les plus viraux (30s chacun). Format JSON strict: [{'start': 10, 'end': 40, 'title': 'HOOK'}]"
    response = model.generate_content([prompt, video_file])
    try:
        segments = json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except:
        send_tg("❌ Erreur IA : Format JSON corrompu. Je tente de continuer..."); return

    # 3. Montage et Envoi
    send_tg(f"🎬 Montage lancé pour {len(segments)} Shorts. Arrivée imminente...")
    for i, seg in enumerate(segments):
        try:
            clip = VideoFileClip(video_path).subclip(seg['start'], seg['end'])
            # Format Vertical 9:16
            w, h = clip.size
            clip = clip.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
            
            # Karaoké + Barre
            txt = create_subtitle(seg['title'], clip.duration)
            bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(clip.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / clip.duration)), 10])
            
            final = CompositeVideoClip([clip, txt, bar])
            out = f"short_{i}.mp4"
            final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
            
            # Envoi
            with open(out, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", 
                              files={'video': f}, 
                              data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
            os.remove(out)
        except Exception as e:
            print(f"Erreur sur le segment {i}: {e}")

    os.remove(video_path)
    send_tg("✅ Terminé ! Tous les Shorts ont été envoyés.")

def run_agent():
    print("🚀 Bot Auto Shorts démarré")
    # On force la lecture des messages récents
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?limit=50"
    resp = requests.get(url).json()
    
    updates = resp.get("result", [])
    found = False
    for update in reversed(updates):
        msg = update.get("message", {}).get("text", "")
        if "youtube.com" in msg or "youtu.be" in msg:
            process_video(msg)
            found = True
            break
            
    if not found:
        print("🔍 Aucun lien trouvé.")
        send_tg("🕵️ Je ne vois aucun lien YouTube. Renvoie-le moi maintenant !")

if __name__ == "__main__":
    run_agent()
