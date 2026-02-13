import os, json, time, requests
import google.generativeai as genai # On garde celui-ci pour l'instant car google.genai est la toute nouvelle version 2026
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
        # Style Karaoké Premium
        return TextClip(
            text.upper(), font='Arial-Bold', fontsize=65, color='yellow',
            method='caption', size=(620, None), stroke_color='black', stroke_width=2
        ).set_duration(duration).set_position(('center', 850))
    except: return None

def process_video_file(file_path):
    send_tg("🧠 Analyse du contenu par l'IA...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Upload vers Gemini pour analyse
    video_file = genai.upload_file(file_path)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    # Prompt optimisé pour 2026
    prompt = "Find 10 viral segments (30s each). Return ONLY JSON: [{'start': 10, 'end': 40, 'title': 'HOOK'}]"
    response = model.generate_content([prompt, video_file])
    
    try:
        raw_json = response.text.replace('```json', '').replace('```', '').strip()
        segments = json.loads(raw_json)
    except:
        send_tg("❌ L'IA a renvoyé un format invalide. Réessaie.")
        return

    send_tg(f"🎬 Création de {len(segments)} Shorts en cours...")
    clip = VideoFileClip(file_path)
    
    for i, seg in enumerate(segments):
        # Format 9:16 Vertical
        short = clip.subclip(seg['start'], seg['end'])
        w, h = short.size
        short = short.crop(x_center=w/2, width=h*9/16, height=h).resize(height=1280)
        
        # Sous-titres + Progress Bar
        txt = create_subtitle(seg['title'], short.duration)
        bar = ColorClip(size=(720, 10), color=(255, 255, 0)).set_duration(short.duration).set_position(("left", "bottom")).resize(lambda t: [max(1, int(720 * t / short.duration)), 10])
        
        final = CompositeVideoClip([short, txt, bar]) if txt else CompositeVideoClip([short, bar])
        out = f"short_{i}.mp4"
        final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast")
        
        with open(out, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TG_CHAT_ID, 'caption': f"🔥 Short {i+1}: {seg['title']}"})
        os.remove(out)
    
    clip.close()
    os.remove(file_path)
    send_tg("✅ Tous les Shorts sont prêts !")

def run_agent():
    print("🤖 Bot en attente de fichier ou lien...")
    # On force la lecture en ignorant l'historique lu
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?offset=-1" 
    resp = requests.get(url).json()
    
    if "result" in resp and len(resp["result"]) > 0:
        msg = resp["result"][0].get("message", {})
        
        # PRIORITÉ : Vidéo Directe
        if "video" in msg:
            send_tg("📥 Vidéo reçue ! Préparation du montage...")
            file_id = msg["video"]["file_id"]
            file_info = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getFile?file_id={file_id}").json()
            
            if not file_info.get("ok"):
                send_tg("❌ Fichier trop lourd (limite 20Mo). Compresse-le ou envoie un lien.")
                return

            download_url = f"https://api.telegram.org/file/bot{TG_TOKEN}/{file_info['result']['file_path']}"
            r = requests.get(download_url)
            with open("input.mp4", "wb") as f:
                f.write(r.content)
            
            process_video_file("input.mp4")
        else:
            print("🔍 Aucun nouveau message vidéo trouvé.")

if __name__ == "__main__":
    run_agent()
