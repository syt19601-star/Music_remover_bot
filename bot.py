import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import LabeledPrice, PreCheckoutQuery, FSInputFile
from gradio_client import Client, handle_file
import database as db

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db.init_db()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    credits = db.get_credits(message.from_user.id)
    await message.answer(
        f"أهلاً بك في بوت عزل الموسيقى!\n"
        f"أرسل لي أي مقطع صوتي أو أغنية وسأقوم بفصل الصوت البشري عن الموسيقى.\n\n"
        f"رصيدك الحالي: {credits} محاولات."
    )

@dp.message(F.audio | F.voice)
async def handle_audio(message: types.Message):
    user_id = message.from_user.id
    credits = db.get_credits(user_id)

    if credits <= 0:
        await send_stars_invoice(message)
        return

    wait_msg = await message.answer("جاري تحميل المقطع وعزل الموسيقى، قد يستغرق هذا دقيقة...")

    try:
        file_id = message.audio.file_id if message.audio else message.voice.file_id
        file = await bot.get_file(file_id)
        input_path = f"input_{user_id}.mp3"
        await bot.download_file(file.file_path, input_path)

        client = Client("abidlabs/music-separation", hf_token=HF_TOKEN)
        result = client.predict(
            handle_file(input_path),
            api_name="/predict"
        )

        vocals_path = result[0] if isinstance(result, (list, tuple)) else result

        db.use_credit(user_id)
        new_credits = db.get_credits(user_id)

        await message.answer_audio(
            FSInputFile(vocals_path),
            caption=f"تم عزل الصوت بنجاح!\nرصيدك المتبقي: {new_credits} محاولات."
        )

        if os.path.exists(input_path):
            os.remove(input_path)

    except Exception as e:
        await message.answer("حدث خطأ أثناء المعالجة، لم يتم خصم أي محاولة. حاول مرة أخرى لاحقاً.")
        print(f"Error: {e}")
    finally:
        await wait_msg.delete()

async def send_stars_invoice(message: types.Message):
    prices = [LabeledPrice(label="5 محاولات إضافية", amount=10)]
    await message.answer_invoice(
        title="شحن رصيد عزل الموسيقى",
        description="لقد استنفدت محاولاتك المجانية. اشترِ 5 محاولات إضافية باستخدام نجوم تلغرام.",
        payload="buy_5_credits",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    if message.successful_payment.invoice_payload == "buy_5_credits":
        db.add_credits(message.from_user.id, 5)
        new_credits = db.get_credits(message.from_user.id)
        await message.answer(f"شكراً لك! تم شحن 5 محاولات بنجاح. رصيدك الحالي: {new_credits}.")

async def handle_ping(request):
    return web.Response(text="Bot is running!")

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
