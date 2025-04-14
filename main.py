import json
import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.ext.filters import User
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
USER_ID = 344657888
DATA_FILE = "lunch_data.json"
TIMEZONE = pytz.timezone("Asia/Nicosia")
APP_URL = "https://lunchbot-production.up.railway.app"

app = Flask(__name__)

@app.route("/")
def home():
    logging.info("📡 Пинг получен на /")
    return "LunchBot is alive", 200

def run_flask():
    logging.info("🌐 Flask сервер запускается...")
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run_flask).start()

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

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"📩 Получен ответ: {update.message.text}")
    text = update.message.text
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    data = load_data()
    data[today] = text
    save_data(data)
    await update.message.reply_text("Ответ записан. Спасибо!")

async def ask_lunch(app):
    logging.info("📤 Отправка вопроса об обеде...")
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await app.bot.send_message(chat_id=USER_ID, text="Ты пообедал сегодня?", reply_markup=keyboard)

async def send_weekly_stats(app):
    logging.info("📊 Подведение недельной статистики...")
    data = load_data()
    today = datetime.now(TIMEZONE)
    count_yes = sum(
        1 for i in range(7)
        if data.get((today - timedelta(days=i)).strftime("%Y-%m-%d")) == "Да"
    )
    messages = {
        0: "Ты не должен ощущать чувства вины (нет)",
        1: "Ну ничего, ты старался!",
        2: "Неплохо!",
        3: "Красавчик, целых три обеда на этой неделе!",
        4: "Вау! Ты супер!",
        5: "Всю рабочую неделю обедал? Невероятно!",
        6: "Ты просто лучший, почти всю неделю обедал!",
        7: "Амбиливбл! Вин стрик!"
    }
    summary = messages.get(count_yes, "Неделя прошла, но данных нет.")
    await app.bot.send_message(chat_id=USER_ID, text=f"📊 Обеденная статистика: {count_yes}/7\n{summary}")

async def ping_self():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(APP_URL)
            logging.info(f"🔄 Self-ping OK: {r.status_code}")
    except Exception as e:
        logging.warning(f"❌ Self-ping failed: {e}")

async def main():
    logging.info("🔁 Инициализация LunchBot...")
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & User(user_id=USER_ID), handle_response))

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: application.create_task(ask_lunch(application)), "cron", hour=14, minute=0)
    scheduler.add_job(lambda: application.create_task(send_weekly_stats(application)), "cron", day_of_week="sun", hour=19, minute=0)
    scheduler.add_job(lambda: application.create_task(ping_self()), "interval", minutes=4)
    scheduler.start()

    keep_alive()
    await asyncio.sleep(2)
    logging.info("✅ LunchBot готов. Старт polling...")
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
