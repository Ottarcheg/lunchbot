import asyncio
import json
import logging
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters, ContextTypes
)

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = 344657888
DATA_FILE = "lunch_data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__)
scheduler = BackgroundScheduler()

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Файл данных не найден, создаю новый.")
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def ask_lunch(application):
    now = datetime.now().strftime('%H:%M:%S')
    logging.info(f"⏰ Время задать вопрос. Сейчас {now}")
    await application.bot.send_message(
        chat_id=CHAT_ID,
        text="Ты пообедал сегодня?",
        reply_markup={
            "keyboard": [["Да"], ["Нет"]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }
    )

async def handle_response(update, context: ContextTypes.DEFAULT_TYPE):
    user_response = update.message.text.lower()
    data = load_data()
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in data:
        data[today] = []
    if user_response in ["да", "нет"]:
        data[today].append(user_response)
        save_data(data)
        await update.message.reply_text("Ответ сохранён ✅")
    else:
        await update.message.reply_text("Пожалуйста, ответь 'Да' или 'Нет'.")

async def send_weekly_summary(application):
    data = load_data()
    count = sum(day.count("да") for day in data.values())
    messages = {
        0: "На этой неделе ты совсем забывал обедать. Надо это исправить! 🍽️",
        1: "Ты пообедал всего один раз за неделю. Так нельзя! 😥",
        2: "Два обеда — это уже что-то, но всё ещё мало. 🥄",
        3: "Серединка на половинку. Надо лучше! 🍴",
        4: "Четыре раза — почти отлично! Ещё немного! 🍛",
        5: "Отличный результат! Почти каждый день с обедом! 👏",
        6: "Ты был на высоте! Шесть обедов из семи! 🔥",
        7: "Идеально! Все семь обедов на месте! 🏆",
    }
    message = (
        "📊 Обеденная статистика за неделю:\n" +
        messages.get(count, "Что-то пошло не так...")
    )
    await application.bot.send_message(chat_id=CHAT_ID, text=message)

@app.route("/")
def home():
    return "LunchBot is running"

async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_response))

    scheduler.add_job(lambda: asyncio.create_task(ask_lunch(application)), "cron", hour=13, minute=30)
    scheduler.add_job(lambda: asyncio.create_task(send_weekly_summary(application)), "cron", day_of_week="sun", hour=19, minute=0)
    scheduler.start()

    logging.info("✅ LunchBot готов. Старт polling...")
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
