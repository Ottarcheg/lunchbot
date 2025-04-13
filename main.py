import json
import os
import asyncio
import nest_asyncio
from datetime import datetime
from flask import Flask
from threading import Thread
from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackContext, MessageHandler, filters

# Настройки
DATA_FILE = "lunch_data.json"
TIMEZONE = timezone("Asia/Nicosia")
USER_ID = 344657888  # Замени на свой Telegram ID
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask для UptimeRobot
app = Flask("")

@app.route("/")
def home():
    return "LunchBot is alive!", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run_flask).start()

# Хранилище данных
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Обработка ответов
async def handle_response(update: Update, context: CallbackContext):
    user_response = update.message.text
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    data = load_data()
    data[today] = user_response
    save_data(data)
    await update.message.reply_text("Ответ записан. Спасибо!")

# Вопрос об обеде
async def ask_lunch(app):
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await app.bot.send_message(chat_id=USER_ID, text="Ты пообедал сегодня?", reply_markup=keyboard)

# Еженедельная статистика
async def send_weekly_stats(app):
    data = load_data()
    today = datetime.now(TIMEZONE)
    count_yes = 0

    for i in range(7):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if data.get(day) == "Да":
            count_yes += 1

    if count_yes == 0:
        text = "Ты не должен ощущать чувства вины (нет)"
    elif count_yes == 1:
        text = "Ну ничего, ты старался!"
    elif count_yes == 2:
        text = "Неплохо!"
    elif count_yes == 3:
        text = "Красавчик, целых три обеда на этой неделе!"
    elif count_yes == 4:
        text = "Вау! Ты супер!"
    elif count_yes == 5:
        text = "Всю рабочую неделю обедал? Невероятно!"
    elif count_yes == 6:
        text = "Ты просто лучший, почти всю неделю обедал!"
    else:
        text = "Амбиливбл! Вин стрик!"

    await app.bot.send_message(chat_id=USER_ID, text=f"📊 Обеденная статистика: {count_yes}/7\n{text}")

# Основной запуск
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & filters.USER(user_id=USER_ID), handle_response))

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: application.create_task(ask_lunch(application)), "cron", hour=14, minute=0)
    scheduler.add_job(lambda: application.create_task(send_weekly_stats(application)), "cron", day_of_week="sun", hour=19, minute=0)
    scheduler.start()

    keep_alive()
    await application.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
