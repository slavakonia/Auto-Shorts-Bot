import os
import time
import json
import subprocess
import requests
import yt_dlp
import google.generativeai as genai

# =========================
# 🔐 ENV
# =========================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

genai.configure(api_key=GEMINI_API_KEY)

WORKDIR = "work"
os.makedirs(WORKDIR, exist_ok=True)

# =========================
# 📲 TELEGRAM
# =========================
def telegram_send(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text}
    )

def telegram_send_video(path, caption):
    with open(path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo",
            files={"video": f},
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        )

def wait_for_link():
    telegram_send("📥 Envoie un lien YouTube pour générer des Shorts")
    last = 0
    while True:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last+1}"
        ).json()
        for u in r.get("result", []):
            last = u["update_id"]
            txt = u.get("message", {}).get("text", "")
            if "youtu" in txt:
                return txt
        time.sleep(3)

# =========================
# ⬇️ DOWNLOAD
# =========================
def download_video(url):
    out = f"{WORKDIR}/input.mp4"
    if os.path.exists(out): os.remove(out)
    ydl_opts = {"outtmpl": out, "format": "mp4"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return out

# =========================
# 🧠 GEMINI ANALYSE
# =========================
def analyze(video):
    model = genai.GenerativeModel("gemini-2.5-flash")
    file = genai.upload_file(video)
    while file.state.name == "PROCESSING":
        time.sleep(5)
        file = genai.get_file(file.name)

    prompt = """
    Analyse cette vidéo.
    Trouve 5 segments viraux (30–60s) pour TikTok & YouTube Shorts.
    Réponds UNIQUEMENT en JSON :
    [
      {
        "start": 12,
        "end": 45,
        "title": "Titre accrocheur",
        "description": "Description courte",
        "tags": "#ia #shorts #tiktok",
        "subtitle": "Texte parlé"
      }
    ]
    """

    res = model.generate_content([prompt, file])
    txt = res.text.strip().split("```json")[-1].split("```")[0]
    return json.loads(txt)

# =========================
# 🎬 FFMPEG CUT + 9:16
# =========================
def make_short(src, seg, idx):
    out = f"{WORKDIR}/short_{idx}.mp4"

    subtitle = seg["subtitle"].replace("'", "").replace("\n", " ")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(seg["start"]),
        "-to", str(seg["end"]),
        "-i", src,
        "-vf",
        f"crop=ih*9/16:ih,scale=1080:1920,"
        f"drawtext=text='{subtitle}':"
        f"fontcolor=yellow:fontsize=48:"
        f"x=(w-text_w)/2:y=h-200:"
        f"borderw=2:bordercolor=black",
        "-c:a", "aac",
        out
    ]
    subprocess.run(cmd, check=True)
    return out

# =========================
# 🚀 MAIN
# =========================
def main():
    telegram_send("🤖 Bot prêt")
    link = wait_for_link()
    telegram_send("⬇️ Téléchargement…")
    video = download_video(link)

    telegram_send("🧠 Analyse IA…")
    segments = analyze(video)

    for i, seg in enumerate(segments):
        telegram_send(f"🎬 Short {i+1}/5")
        short = make_short(video, seg, i)

        caption = (
            f"🔥 {seg['title']}\n\n"
            f"{seg['description']}\n\n"
            f"{seg['tags']}"
        )
        telegram_send_video(short, caption)

    telegram_send("✅ Tous les shorts sont prêts")

if __name__ == "__main__":
    main()
