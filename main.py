
import asyncio
import json
import logging
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
USER_ID = 344657888
TIMEZONE = pytz.timezone("Asia/Nicosia")
DATA_FILE = "lunch_data.json"

app = Flask(__name__)
scheduler = BackgroundScheduler(timezone=TIMEZONE)

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Не удалось загрузить данные: {e}")
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def ask_lunch(context: CallbackContext):
    logging.info("⏰ Отправка напоминания пользователю...")
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], resize_keyboard=True)
    context.bot.send_message(chat_id=USER_ID, text="Ты пообедал сегодня?", reply_markup=keyboard)

async def handle_response(update: Update, context: CallbackContext):
    text = update.message.text.strip().lower()
    today = str(datetime.now(TIMEZONE).date())
    data = load_data()

    if today not in data:
        data[today] = []

    if text in ["да", "нет"]:
        data[today].append(text)
        save_data(data)
        await update.message.reply_text("Ответ записан. Спасибо!")

def run_flask():
    app.run(host="0.0.0.0", port=8080)

@app.route("/")
def index():
    return "LunchBot is alive!", 200

async def main():
    logging.info("🔁 Инициализация LunchBot...")

    app_thread = Thread(target=run_flask)
    app_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=USER_ID), handle_response))

    scheduler.add_job(lambda: application.create_task(ask_lunch(application.bot)), "cron", hour=11, minute=55)
    scheduler.start()

    logging.info("✅ LunchBot готов. Старт polling...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
