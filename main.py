import json
import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackContext, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import os

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
USER_ID = 344657888
DATA_FILE = "lunch_data.json"
TIMEZONE = pytz.timezone("Asia/Nicosia")

app = Flask(__name__)

@app.route("/")
def home():
    return "LunchBot is alive!", 200

def run_flask():
    logging.info("🌐 Flask сервер запускается...")
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        logging.info("✅ Данные загружены")
        return data
    except Exception as e:
        logging.warning(f"Не удалось загрузить данные: {e}")
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
        logging.info("✅ Данные сохранены")
    except Exception as e:
        logging.error(f"Ошибка при сохранении данных: {e}")

def get_today_key():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

async def handle_response(update: Update, context: CallbackContext):
    logging.info(f"📩 Получен ответ от пользователя: {update.message.text}")
    data = load_data()
    today = get_today_key()
    if today not in data:
        data[today] = []
    if update.message.text == "Да":
        if USER_ID not in data[today]:
            data[today].append(USER_ID)
    elif update.message.text == "Нет":
        if USER_ID in data[today]:
            data[today].remove(USER_ID)
    save_data(data)
    await update.message.reply_text("Ответ сохранён.")

async def send_lunch_reminder(application):
    logging.info("⏰ Отправка напоминания о ланче...")
    kb = [["Да", "Нет"]]
    await application.bot.send_message(chat_id=USER_ID, text="Ты пообедал сегодня?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    logging.info("✅ Напоминание отправлено")

async def run_ping(application):
    logging.info("📡 Пинг от Railway")
    await application.bot.send_message(chat_id=USER_ID, text="📡 Пинг от Railway")

async def main():
    logging.info("🔁 Инициализация LunchBot...")
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & filters.User(USER_ID), handle_response))

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: application.create_task(send_lunch_reminder(application)), "cron", hour=11, minute=50)
    scheduler.add_job(lambda: application.create_task(run_ping(application)), "interval", minutes=4)
    scheduler.start()
    logging.info("✅ LunchBot готов. Старт polling...")
    keep_alive()
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
