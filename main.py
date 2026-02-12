import os
import asyncio
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import random

# ----------------------
# CONFIGURATION
# ----------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SHORTS_COUNT = 10
SHORT_DURATION = (30, 60)  # secondes
SUBTITLE_COLOR_1 = "white"
SUBTITLE_COLOR_2 = "yellow"
SUBTITLE_FONT_SIZE = 40
OUTPUT_DIR = "shorts_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------
# UTILITAIRES
# ----------------------
def generate_title_description_hashtags():
    """Retourne un tuple (title, description, hashtags) optimisés"""
    titles = [
        "Incroyable moment à voir !",
        "Vous ne croirez pas ça !",
        "Top moment de la vidéo 🔥",
        "À ne pas manquer !",
        "Moment hilarant / choquant !"
    ]
    hashtags = ["#Shorts", "#Viral", "#TikTok", "#YTShorts", "#Fun", "#FYP"]
    description = "Découvrez ce moment incroyable de la vidéo !"
    title = random.choice(titles)
    random.shuffle(hashtags)
    return title, description, " ".join(hashtags[:5])

def add_karaoke_subtitles(clip, texts):
    """Ajoute des sous-titres karaoké (2 lignes max)"""
    subtitle_clips = []
    for text, start, end in texts:
        txt_clip1 = TextClip(text, fontsize=SUBTITLE_FONT_SIZE, color=SUBTITLE_COLOR_1, font="Arial", method='caption', size=(clip.w, None))
        txt_clip1 = txt_clip1.set_position(("center","bottom")).set_start(start).set_end(end)
        txt_clip2 = TextClip(text, fontsize=SUBTITLE_FONT_SIZE, color=SUBTITLE_COLOR_2, font="Arial", method='caption', size=(clip.w, None))
        txt_clip2 = txt_clip2.set_position(("center","bottom")).set_start(start+0.1).set_end(end)
        subtitle_clips.extend([txt_clip1, txt_clip2])
    return CompositeVideoClip([clip, *subtitle_clips])

def split_video_into_shorts(video_path):
    """Découpe la vidéo en shorts"""
    clip = VideoFileClip(video_path)
    shorts = []
    duration = clip.duration
    for i in range(SHORTS_COUNT):
        start = random.uniform(0, max(0, duration - SHORT_DURATION[1]))
        end = min(duration, start + random.uniform(*SHORT_DURATION))
        short_clip = clip.subclip(start, end)
        # Exemple simple de sous-titres karaoké
        texts = [("Moment clé !", 0, short_clip.duration)]
        short_clip = add_karaoke_subtitles(short_clip, texts)
        filename = os.path.join(OUTPUT_DIR, f"short_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.mp4")
        short_clip.write_videofile(filename, codec="libx264", audio_codec="aac")
        title, desc, tags = generate_title_description_hashtags()
        shorts.append({"file": filename, "title": title, "description": desc, "hashtags": tags})
    return shorts

# ----------------------
# TELEGRAM HANDLER
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🚀 Bot démarré. Envoyez une vidéo pour créer les shorts.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Aucune vidéo détectée !")
        return

    file = await context.bot.get_file(video.file_id)
    local_path = os.path.join("downloads", f"{video.file_id}.mp4")
    os.makedirs("downloads", exist_ok=True)
    await file.download_to_drive(local_path)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Vidéo téléchargée ! Traitement en cours...")

    # Découpage en shorts
    loop = asyncio.get_event_loop()
    shorts = await loop.run_in_executor(None, split_video_into_shorts, local_path)

    # Envoi des shorts
    for s in shorts:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"🎬 {s['title']}\n{s['description']}\n{s['hashtags']}")
        await context.bot.send_video(chat_id=update.effective_chat.id, video=open(s["file"], "rb"))

# ----------------------
# MAIN
# ----------------------
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
