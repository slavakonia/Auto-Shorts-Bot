import os, json, time, requests, yt_dlp, feedparser
import google.generativeai as genai
import numpy as np
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHANNELS = ["UCv6UXP-H47-Vb-Txs-W9pzA", "UCjEdsqg2p3J_O0K7yQy4tHg"] # Ajoute tes IDs ici

genai.configure(api_key=GEMINI_API_KEY)

def log(msg): print(f"🤖 {msg}")

# --- MOTEUR DE SOUS-TITRES KARAOKÉ ---
def create_subtitle(text, duration, size):
    # Crée un texte stylisé avec contour
    return TextClip(
        text.upper(),
        fontsize=70,
        color='yellow',
        font='Arial-Bold',
        stroke_color='black',
        stroke_width=2,
        method='caption',
        size=(size[0]*0.8, None)
    ).set_duration(duration).set_position(('center', 500))

# --- TRAITEMENT COMPLET ---
def process_video(url, title):
    log(f"🚀 Traitement lancé pour : {title}")
    video_path = "input.mp4"
    
    # 1. Téléchargement haute qualité
    ydl_opts = {'format': 'bestvideo[height<=720]+bestaudio/best', 'outtmpl': video_path, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])

    # 2. Analyse Gemini pour 10-20 segments
    model = genai.GenerativeModel('gemini-1.5-flash')
    video_file = genai.upload_file(video_path)
    while video_file.state.name == "PROCESSING": time.sleep(2); video_file = genai.get_file(video_file.name)
    
    prompt = "Trouve les 15 moments les plus viraux (30s chacun). Pour chaque segment, donne un titre accrocheur. Format JSON: [{'start': 10, 'end': 40, 'title': 'HOOK'}]"
    response = model.generate_content([prompt, video_file])
    segments = json.loads(response.text.replace('```json', '').replace('```', '').strip())

    # 3. Découpe et Montage FFMPEG via MoviePy
    for i, seg in enumerate(segments):
        log(f"🎬 Création du Short {i+1}/{len(segments)}")
        clip = VideoFileClip(video_path).subclip(seg['start'], seg['end'])
        
        # Format Vertical 9:16
        w, h = clip.size
        target_w = h * 9 / 16
        clip = clip.crop(x_center=w/2, width=target_w, height=h).resize(height=1280)
        
        # Ajout du titre Karaoké (simplifié pour la vitesse)
        txt = create_subtitle(seg['title'], clip.duration, (720, 1280))
        
        # Barre de progression
        progress = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(clip.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / clip.duration)), 10])
        
        final = CompositeVideoClip([clip, txt, progress])
        short_name = f"short_{i}.mp4"
        final.write_videofile(short_name, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
        
        # 4. Envoi Telegram
        with open(short_name, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': f"✅ Short {i+1}: {seg['title']}"})
        
        os.remove(short_name) # Nettoyage immédiat pour la place disque
    
    os.remove(video_path)

# --- ÉCOUTEUR TELEGRAM & YOUTUBE ---
def run_agent():
    # 1. Vérifier nouveaux liens sur Telegram
    log("📩 Vérification des messages Telegram...")
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    updates = requests.get(tg_url).json()
    if updates["result"]:
        for update in updates["result"]:
            msg = update.get("message", {}).get("text", "")
            if "youtube.com" in msg or "youtu.be" in msg:
                process_video(msg, "Lien Manuel Telegram")
                # Optionnel : Marquer comme lu (nécessite offset)

    # 2. Vérifier YouTube RSS
    log("📺 Vérification YouTube...")
    for c_id in CHANNELS:
        feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={c_id}")
        if feed.entries:
            latest = feed.entries[0]
            # Ici tu peux ajouter une logique de temps pour éviter les doublons
            process_video(latest.link, latest.title)

if __name__ == "__main__":
    run_agent()
