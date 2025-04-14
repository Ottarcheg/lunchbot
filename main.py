import asyncio
import logging
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
import nest_asyncio

nest_asyncio.apply()

BOT_TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = 344657888
DATA_FILE = "lunch_data.json"

app = Flask(__name__)
scheduler = BackgroundScheduler()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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
    logging.info("⏰ Отправка вопроса про обед...")
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await application.bot.send_message(chat_id=CHAT_ID, text="Ты пообедал сегодня?", reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_response = update.message.text.lower()
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_data()
    data[today] = 1 if user_response == "да" else 0
    save_data(data)
    logging.info(f"📥 Ответ получен: {user_response}")

async def send_weekly_summary(application: Application):
    data = load_data()
    count = sum(data.get(day, 0) for day in data)
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
    message = f"""📊 Обеденная статистика за неделю:
{messages.get(count, 'Что-то пошло не так...')}"""
    await application.bot.send_message(chat_id=CHAT_ID, text=message)
    save_data({})

@app.route("/")
def home():
    return "LunchBot работает!"

async def main():
    logging.info("🔁 Инициализация LunchBot...")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & filters.Chat(chat_id=CHAT_ID), handle_message))

    scheduler.add_job(lambda: asyncio.create_task(ask_lunch(application)), CronTrigger(hour=12, minute=20, timezone="Europe/Nicosia"))
    scheduler.add_job(lambda: asyncio.create_task(send_weekly_summary(application)), CronTrigger(day_of_week="sun", hour=19, minute=0, timezone="Europe/Nicosia"))
    scheduler.start()

    logging.info("✅ LunchBot готов. Старт polling...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
