import os
import time
import math
import asyncio
import subprocess
import imageio_ffmpeg as ffmpeg
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import BOT_TOKEN, API_ID, API_HASH

# Initialize your Pyrogram client
app = Client(
    "stream_remover_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

PROGRESS_TEMPLATE = """
Progress: {0}%
Downloaded: {1} / {2}
Speed: {3}/s
ETA: {4}
"""

async def progress_callback(current, total, message, start_time):
    now = time.time()
    elapsed_time = now - start_time
    if elapsed_time == 0:
        elapsed_time = 1  # Avoid division by zero

    speed = current / elapsed_time
    percentage = current * 100 / total
    eta = (total - current) / speed

    progress_str = "[{0}{1}]".format(
        ''.join(["⬢" for _ in range(math.floor(percentage / 10))]),
        ''.join(["⬡" for _ in range(10 - math.floor(percentage / 10))])
    )
    tmp = progress_str + PROGRESS_TEMPLATE.format(
        round(percentage, 2),
        human_readable_size(current),
        human_readable_size(total),
        human_readable_size(speed),
        time_formatter(eta)
    )

    try:
        await message.edit(
            text=tmp,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Owner", url='https://t.me/atxbots')]]
            )
        )
    except Exception as e:
        print(f"Error updating progress: {e}")

def human_readable_size(size):
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def time_formatter(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    time_str = ((f"{days}d, " if days else "") +
                (f"{hours}h, " if hours else "") +
                (f"{minutes}m, " if minutes else "") +
                (f"{seconds}s, " if seconds else ""))
    return time_str.strip(', ')

@app.on_message(filters.command("start"))
async def start_command(bot, message: Message):
    welcome_text = (
        "Hello! I am the Stream Remover Bot.\n\n"
        "I can help you remove audio and subtitles from video files.\n\n"
        "To use me, simply forward a video to this chat, and I will process it for you.\n\n"
        "Owner: [@atxbots](https://t.me/atxbots)"
    )
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.video & filters.forwarded)
async def process_forwarded_video(bot, message: Message):
    try:
        ms = await message.reply("Processing video...")

        file_info = message.video
        file_id = file_info.file_id
        file_size = file_info.file_size
        file_path = f"downloads/{file_id}.mp4"

        if file_size > 2 * 1024 * 1024 * 1024:
            await ms.edit("Error: The video file is too large. Please send a smaller file.")
            return

        await bot.download_media(message, file_path, progress=progress_callback, progress_args=(ms, time.time()))

        start_time = time.time()
        output_filename = f"processed_{file_id}.mp4"
        ffmpeg_cmd = (
            ffmpeg.get_ffmpeg_exe(), '-i', file_path,
            '-c:v', 'copy',
            '-an', '-sn',
            output_filename
        )
        subprocess.run(ffmpeg_cmd, check=True)

        processing_time = time.time() - start_time
        processed_size = os.path.getsize(output_filename)

        await bot.send_document(
            chat_id=message.chat.id,
            document=output_filename,
            caption=f"Processed video\nSize: {human_readable_size(processed_size)}\nProcessing Time: {time_formatter(processing_time)}"
        )

        os.remove(file_path)
        os.remove(output_filename)

    except subprocess.CalledProcessError as e:
        await ms.edit(f"Error processing video: {e}")

    except Exception as e:
        await ms.edit(f"An error occurred: {e}")

if __name__ == "__main__":
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    app.run()

