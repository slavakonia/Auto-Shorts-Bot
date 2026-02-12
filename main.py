import os
import subprocess
import uuid
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import whisper
import numpy as np

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_DIR = "work"
os.makedirs(BASE_DIR, exist_ok=True)

model = whisper.load_model("small")

# ---------------------------
# UTILITAIRES
# ---------------------------
def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

# ---------------------------
# EXTRACTION AUDIO
# ---------------------------
def extract_audio(video, audio):
    run(f"ffmpeg -y -i {video} -vn -ac 1 -ar 16000 {audio}")

# ---------------------------
# TRANSCRIPTION
# ---------------------------
def transcribe(audio):
    result = model.transcribe(audio, language="fr")
    return result["segments"]

# ---------------------------
# MEILLEURS MOMENTS
# ---------------------------
def best_segments(segments, max_clips=15):
    scored = []
    for s in segments:
        duration = s["end"] - s["start"]
        words = len(s["text"].split())
        score = words / max(duration, 1)
        if 30 <= duration <= 60:
            scored.append((score, s))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored[:max_clips]]

# ---------------------------
# SOUS-TITRES KARAOKÉ
# ---------------------------
def create_ass(segments, ass_path):
    with open(ass_path, "w") as f:
        f.write("""[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,42,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,1,0,1,2,0,2,30,30,40,1

[Events]
Format: Layer,Start,End,Style,Text
""")
        for s in segments:
            start = s["start"]
            end = s["end"]
            text = s["text"].replace("\n", " ")
            f.write(f"Dialogue: 0,{sec(start)},{sec(end)},Default,{text}\n")

def sec(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02}:{s:05.2f}"

# ---------------------------
# GÉNÉRATION SHORT
# ---------------------------
def make_short(video, seg, idx):
    out = f"{BASE_DIR}/short_{idx}.mp4"
    ass = f"{BASE_DIR}/sub_{idx}.ass"
    create_ass([seg], ass)

    run(
        f"""ffmpeg -y -i {video} -vf "subtitles={ass}" \
        -ss {seg['start']} -to {seg['end']} \
        -c:v libx264 -preset fast -crf 23 -c:a aac {out}"""
    )
    return out

# ---------------------------
# MÉTADONNÉES VIRAL
# ---------------------------
def generate_meta(text):
    title = f"Tu savais ça ? 😳 {text[:60]}"
    desc = f"{text}\n\n👇 Abonne-toi pour plus de vidéos"
    tags = "#shorts #tiktokfr #viral #motivation #france"
    return title, desc, tags

# ---------------------------
# BOT TELEGRAM
# ---------------------------
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    file = await msg.video.get_file() if msg.video else await msg.document.get_file()

    uid = str(uuid.uuid4())
    video_path = f"{BASE_DIR}/{uid}.mp4"
    audio_path = f"{BASE_DIR}/{uid}.wav"

    await file.download_to_drive(video_path)
    await msg.reply_text("📥 Vidéo reçue, traitement en cours...")

    extract_audio(video_path, audio_path)
    segments = transcribe(audio_path)
    best = best_segments(segments)

    for i, seg in enumerate(best):
        short = make_short(video_path, seg, i)
        title, desc, tags = generate_meta(seg["text"])

        await context.bot.send_video(
            chat_id=CHAT_ID,
            video=open(short, "rb"),
            caption=f"{title}\n\n{desc}\n\n{tags}"
        )

    await msg.reply_text("🎉 Shorts générés avec succès !")

# ---------------------------
# MAIN
# ---------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    print("🚀 Bot prêt")
    app.run_polling()

if __name__ == "__main__":
    main()
