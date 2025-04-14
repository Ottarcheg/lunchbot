
import asyncio
import json
import logging
from datetime import datetime
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
import nest_asyncio

nest_asyncio.apply()

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = "770144130"  # Заменить на твой chat_id
DATA_FILE = "lunch_data.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
app = Flask(__name__)
scheduler = BackgroundScheduler(timezone="Europe/Nicosia")

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Файл с данными не найден, создаём новый.")
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def ask_lunch(app: Application):
    logging.info("Отправка вопроса о ланче...")
    keyboard = [[
        InlineKeyboardButton("Да", callback_data="yes"),
        InlineKeyboardButton("Нет", callback_data="no"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await app.bot.send_message(chat_id=CHAT_ID, text="Ты пообедал сегодня?", reply_markup=reply_markup)

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_response = update.callback_query.data
    user_id = str(update.callback_query.from_user.id)
    data = load_data()
    today = str(datetime.now(timezone("Europe/Nicosia")).date())
    data[today] = user_response
    save_data(data)
    await update.callback_query.answer("Ответ сохранён.")

async def send_summary(app: Application):
    logging.info("Формируем недельную статистику...")
    data = load_data()
    yes_count = list(data.values()).count("yes")
    if yes_count == 0:
        summary = "Ты не должен ощущать чувства вины (нет)"
    elif yes_count == 1:
        summary = "Ну ничего, ты старался!"
    elif yes_count == 2:
        summary = "Неплохо!"
    elif yes_count == 3:
        summary = "Красавчик, целых три обеда на этой неделе!"
    elif yes_count == 4:
        summary = "Вау! Ты супер!"
    elif yes_count == 5:
        summary = "Всю рабочую неделю обедал? Невероятно!"
    elif yes_count == 6:
        summary = "Ты просто лучший, почти всю неделю обедал!"
    else:
        summary = "Амбиливбл! Вин стрик!"
    await app.bot.send_message(
        chat_id=CHAT_ID,
        text=(
            f"📊 Обеденная статистика за неделю:
"
            f"— Да: {yes_count} раз(а)
"
            f"{summary}"
        )
    )

async def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_response))

    scheduler.add_job(lambda: asyncio.create_task(ask_lunch(application)), "cron", hour=12, minute=6)
    scheduler.add_job(lambda: asyncio.create_task(send_summary(application)), "cron", day_of_week="sun", hour=19)
    scheduler.start()

    logging.info("✅ LunchBot готов к работе.")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
