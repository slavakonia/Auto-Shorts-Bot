import os
import subprocess
import whisper
import random
import math
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import openai

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MAX_SHORTS = 10
MIN_DURATION = 30
MAX_DURATION = 60

WORKDIR = "temp"
SHORTS_DIR = f"{WORKDIR}/shorts"

os.makedirs(SHORTS_DIR, exist_ok=True)

openai.api_key = OPENAI_API_KEY
model = whisper.load_model("base")

# ================== UTILS ==================

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

def extract_audio(video):
    run(f"ffmpeg -y -i {video} -ac 1 -ar 16000 {WORKDIR}/audio.wav")

def transcribe():
    return model.transcribe(f"{WORKDIR}/audio.wav", language="fr")

def generate_segments(duration):
    segments = []
    t = 0
    while t + MIN_DURATION < duration and len(segments) < MAX_SHORTS:
        length = random.randint(MIN_DURATION, MAX_DURATION)
        segments.append((t, min(t + length, duration)))
        t += length
    return segments

def generate_ass(segments):
    ass = """[Script Info]
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Style: Default,Arial,48,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,2,2,20,20,40,1

[Events]
"""
    for s in segments:
        start = s["start"]
        end = s["end"]
        text = s["text"].replace("\n", " ")
        ass += f"Dialogue: 0,{sec(start)},{sec(end)},Default,,0,0,0,,{text}\n"

    with open(f"{WORKDIR}/subs.ass", "w", encoding="utf-8") as f:
        f.write(ass)

def sec(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    s = s % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def make_short(i, start, end):
    out = f"{SHORTS_DIR}/short_{i}.mp4"
    run(
        f"""ffmpeg -y -i {WORKDIR}/input.mp4 \
        -vf "crop=ih*9/16:ih,ass={WORKDIR}/subs.ass" \
        -ss {start} -to {end} -c:a copy {out}"""
    )
    return out

def generate_meta(text):
    prompt = f"""
Génère un titre, une description courte et 8 hashtags
optimisés pour TikTok et YouTube Shorts en français.

Contenu:
{text}
"""
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content

# ================== TELEGRAM ==================

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = await update.message.video.get_file()
    await video.download_to_drive(f"{WORKDIR}/input.mp4")

    await update.message.reply_text("🎬 Vidéo reçue, traitement en cours...")

    extract_audio(f"{WORKDIR}/input.mp4")
    result = transcribe()

    generate_ass(result["segments"])

    duration = math.floor(result["segments"][-1]["end"])
    segments = generate_segments(duration)

    for i, (start, end) in enumerate(segments):
        short = make_short(i, start, end)
        meta = generate_meta(result["text"][:500])

        await update.message.reply_video(
            video=open(short, "rb"),
            caption=meta
        )

    await update.message.reply_text("✅ Shorts générés avec succès !")

# ================== MAIN ==================

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.VIDEO, handle_video))

print("🤖 Bot Telegram lancé")
app.run_polling()
