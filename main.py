import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackContext, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import os
import nest_asyncio

nest_asyncio.apply()

DATA_FILE = "lunch_data.json"
USER_ID = 344657888
TIMEZONE = pytz.timezone("Asia/Nicosia")

app_flask = Flask('')
application = None
loop = None

@app_flask.route('/')
def home():
    return "LunchBot is alive!", 200

def run_flask():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def ask_lunch(app):
    keyboard = [["Да", "Нет"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await app.bot.send_message(chat_id=USER_ID, text="Ты пообедал сегодня?", reply_markup=markup)

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != USER_ID:
        return

    user_text = update.message.text
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    data = load_data()

    if str(user_id) not in data:
        data[str(user_id)] = {}

    if user_text in ["Да", "Нет"]:
        data[str(user_id)][today] = user_text
        save_data(data)
        await update.message.reply_text(f"Ответ записан: {user_text}")
    else:
        await update.message.reply_text("Пожалуйста, выбери 'Да' или 'Нет' с кнопки.")

async def weekly_summary(app):
    data = load_data()
    user_data = data.get(str(USER_ID), {})
    now = datetime.now(TIMEZONE)
    last_7_days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    count_yes = sum(1 for day in last_7_days if user_data.get(day) == "Да")

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

    final_msg = messages.get(count_yes, "Неделя прошла, но данных нет.")
    await app.bot.send_message(chat_id=USER_ID, text=final_msg)

async def main():
    global application, loop
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    loop = asyncio.get_event_loop()

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(ask_lunch(application), loop),
                      "cron", hour=14, minute=0)
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(weekly_summary(application), loop),
                      "cron", day_of_week='sun', hour=19, minute=0)
    scheduler.start()

    keep_alive()
    await application.run_polling()

asyncio.run(main())
