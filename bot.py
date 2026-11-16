import os
import requests
import asyncio
import replicate
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
import database as db

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db.init_db()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    credits = db.get_credits(message.from_user.id)
    if isinstance(credits, tuple):
        credits = credits[0]
    await message.answer(
        f"\nأهلاً بك في بوت عزل الموسيقى\n"
        f"قوم بفصل الصوت البشري عن الموسيقى\n"
        f"رصيدك الحالي: {credits} محاولات"
    )

@dp.message(F.audio | F.voice)
async def handle_audio(message: types.Message):
    user_id = message.from_user.id
    credits = db.get_credits(user_id)
    if isinstance(credits, tuple):
        credits = credits[0]

    if credits <= 0:
        await message.answer("عذراً، نفدت محاولاتك المجانية.")
        return

    wait_msg = await message.answer("جاري معالجة الصوت...")

    try:
        file_id = message.audio.file_id if message.audio else message.voice.file_id
        file = await bot.get_file(file_id)
        input_path = f"input_{user_id}.mp3"
        output_path = f"vocals_{user_id}.mp3"
        await bot.download_file(file.file_path, input_path)

        def run_replicate():
            with open(input_path, "rb") as audio_file:
                output = replicate.run(
                    "cjwbw/demucs:23fc375626b9ef28277259163b469bcfec109968417fb6e138a3791a8e8b6b0c",
                    input={
                        "audio": audio_file,
                        "stem": "vocals",
                        "output_format": "mp3"
                    }
                )
                return output

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_replicate)
        
        vocals_url = result.get("vocals")

        response = requests.get(vocals_url)
        with open(output_path, "wb") as f:
            f.write(response.content)

        db.use_credit(user_id)
        new_credits = db.get_credits(user_id)
        if isinstance(new_credits, tuple):
            new_credits = new_credits[0]

        await message.answer_audio(
            types.FSInputFile(output_path),
            caption=f"تم فصل الصوت بنجاح!\nرصيدك المتبقي: {new_credits}"
        )

        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

    except Exception as e:
        await message.answer(f"حدث خطأ ما: {e}")
    finally:
        await wait_msg.delete()

async def handle_ping(request):
    return web.Response(text="Bot is running")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
