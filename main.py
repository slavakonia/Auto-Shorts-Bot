import os
import json
import subprocess
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

from google import genai

# ==============================
# CONFIG
# ==============================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

SHORTS_COUNT = 10
SHORT_MIN = 30
SHORT_MAX = 60

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ==============================
# GEMINI INIT
# ==============================
client = genai.Client(api_key=GEMINI_API_KEY)

# ==============================
# GEMINI HELPERS
# ==============================
def gemini_best_moments(transcript: str):
    """
    Retourne 10 segments forts (start, end, hook)
    """
    prompt = f"""
Tu es un expert TikTok & YouTube Shorts.
À partir de la transcription suivante, détecte EXACTEMENT 10 meilleurs moments.

Contraintes :
- Durée entre 30 et 60 secondes
- Moments très engageants
- Langue FR
- Format JSON STRICT

Format attendu :
[
  {{
    "start": 12,
    "end": 52,
    "hook": "phrase accrocheuse"
  }}
]

TRANSCRIPTION :
{transcript}
"""

    res = client.models.generate_content(
        model="gemini-1.5-pro",
        contents=prompt
    )

    return json.loads(res.text)


def gemini_titles_descriptions(hook: str):
    prompt = f"""
Génère pour ce short :
- 1 titre viral TikTok
- 1 titre YouTube Shorts
- 1 description optimisée
- 10 hashtags FR max

Sujet :
{hook}

Réponds en JSON strict :
{{
 "tiktok_title": "",
 "yt_title": "",
 "description": "",
 "hashtags": []
}}
"""
    res = client.models.generate_content(
        model="gemini-1.5-pro",
        contents=prompt
    )

    return json.loads(res.text)

# ==============================
# FFMPEG HELPERS
# ==============================
def run(cmd):
    subprocess.run(cmd, check=True)


def extract_audio(video, audio):
    run([
        "ffmpeg", "-y",
        "-i", video,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        audio
    ])


def transcribe(audio):
    """
    Simple transcription via Whisper local ou API externe.
    Pour l’instant placeholder neutre.
    """
    return "TRANSCRIPTION FR SIMPLIFIÉE POUR DÉMO"


def make_short(video, start, end, out):
    run([
        "ffmpeg", "-y",
        "-i", video,
        "-ss", str(start),
        "-to", str(end),
        "-vf", "scale=1080:1920",
        "-c:a", "copy",
        out
    ])


def karaoke_subs(text, srt_path):
    """
    Sous-titres karaoké FR
    Blanc → Jaune
    Bas de l’écran, 2 lignes max
    """
    lines = text.split(".")
    with open(srt_path, "w") as f:
        t = 0
        idx = 1
        for line in lines:
            if not line.strip():
                continue
            f.write(f"{idx}\n")
            f.write(f"00:00:{t:02d},000 --> 00:00:{t+3:02d},000\n")
            f.write(f"{line.strip()}\n\n")
            t += 3
            idx += 1


def burn_subs(video, srt, out):
    run([
        "ffmpeg", "-y",
        "-i", video,
        "-vf",
        "subtitles={}:force_style='FontSize=36,PrimaryColour=&HFFFFFF&,SecondaryColour=&H00FFFF&,Alignment=2'".format(srt),
        out
    ])

# ==============================
# TELEGRAM HANDLER
# ==============================
def handle_video(update, context):
    chat_id = update.message.chat_id  # AUTO
    context.bot.send_message(
        chat_id=chat_id,
        text="🚀 Vidéo reçue, génération des shorts…"def handle_video(update, context):
    video = update.message.video or update.message.document
    file = context.bot.get_file(video.file_id)  # PLUS d'await
    file.download(f"{video.file_id}.mp4")
    context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Vidéo téléchargée !")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        video_path = tmp / "input.mp4"
        audio_path = tmp / "audio.wav"

        file = await context.bot.get_file(video.file_id)
        await file.download_to_drive(video_path)

        extract_audio(str(video_path), str(audio_path))
        transcript = transcribe(str(audio_path))

        moments = gemini_best_moments(transcript)

        for i, m in enumerate(moments[:SHORTS_COUNT]):
            short_raw = tmp / f"short_{i}.mp4"
            short_sub = tmp / f"short_{i}_sub.mp4"
            srt = tmp / f"sub_{i}.srt"

            make_short(video_path, m["start"], m["end"], short_raw)
            karaoke_subs(m["hook"], srt)
            burn_subs(short_raw, srt, short_sub)

            meta = gemini_titles_descriptions(m["hook"])

            final_out = OUTPUT_DIR / f"short_{i+1}.mp4"
            short_sub.rename(final_out)

            with open(OUTPUT_DIR / f"short_{i+1}.txt", "w") as f:
                f.write(f"TIKTOK TITLE:\n{meta['tiktok_title']}\n\n")
                f.write(f"YT SHORTS TITLE:\n{meta['yt_title']}\n\n")
                f.write(f"DESCRIPTION:\n{meta['description']}\n\n")
                f.write("HASHTAGS:\n" + " ".join(meta["hashtags"]))

        await update.message.reply_text("✅ 10 shorts générés avec succès")

# ==============================
# MAIN
# ==============================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    print("🚀 Bot Telegram prêt")
    app.run_polling()

if __name__ == "__main__":
    main()
