import asyncio
import json
import logging
from datetime import datetime
from pytz import timezone
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = 344657888  # твой Telegram ID
DATA_FILE = "lunch_data.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)
scheduler = BackgroundScheduler(timezone="Europe/Nicosia")
keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Файл данных не найден, создаём новый.")
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def ask_lunch(application: Application):
    today = datetime.now(timezone("Europe/Nicosia")).strftime("%Y-%m-%d")
    data = load_data()
    if today not in data:
        data[today] = None
        save_data(data)
        await application.bot.send_message(chat_id=CHAT_ID, text="Ты пообедал сегодня?", reply_markup=keyboard)
        logging.info("Отправлен запрос обеда.")
    else:
        logging.info("Сегодня уже спрашивали.")

async def send_summary(application: Application):
    data = load_data()
    week = [d for d in data.items() if d[1] == "Да"]
    count = len(week)
    messages = {
        0: "Ты не должен ощущать чувства вины (нет)",
        1: "Ну ничего, ты старался!",
        2: "Неплохо!",
        3: "Красавчик, целых три обеда на этой неделе!",
        4: "Вау! Ты супер!",
        5: "Всю рабочую неделю обедал? Невероятно!",
        6: "Ты просто лучший, почти всю неделю обедал!",
        7: "Амбиливбл! Вин стрик!",
    }
    summary_text = messages.get(count, f"Ответов 'Да': {count}")
    await application.bot.send_message(
        chat_id=CHAT_ID,
        text=f"""📊 Обеденная статистика за неделю:

{summary_text}"""
    )
    logging.info("Отправлена статистика за неделю.")

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(timezone("Europe/Nicosia")).strftime("%Y-%m-%d")
    data = load_data()
    if today in data and data[today] is None:
        data[today] = update.message.text
        save_data(data)
        await update.message.reply_text("Ответ записан.")
        logging.info(f"Ответ на {today}: {update.message.text}")

@app.route("/")
def home():
    return "LunchBot работает!"

async def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & filters.USER(chat_id=CHAT_ID), handle_response))

    scheduler.add_job(lambda: asyncio.create_task(ask_lunch(application)), "cron", hour=12, minute=10)
    scheduler.add_job(lambda: asyncio.create_task(send_summary(application)), "cron", day_of_week="sun", hour=19, minute=0)
    scheduler.start()

    logging.info("✅ LunchBot готов. Запуск polling...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
