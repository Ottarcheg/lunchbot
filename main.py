import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json
import pytz
import os

TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = None  # Будет задан при первом взаимодействии

DATA_FILE = "lunch_data.json"
TIMEZONE = pytz.timezone("Europe/Nicosia")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

def load_data():
    if not os.path.exists(DATA_FILE):
        logging.warning("Файл с данными не найден, создаём новый.")
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def ask_lunch(application: Application):
    global CHAT_ID
    if not CHAT_ID:
        logging.info("CHAT_ID ещё не установлен, пропускаем отправку.")
        return

    now = datetime.now(TIMEZONE)
    date_str = now.strftime("%Y-%m-%d")

    data = load_data()
    if date_str not in data:
        data[date_str] = None
        save_data(data)

    reply_markup = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await application.bot.send_message(chat_id=CHAT_ID, text="Ты пообедал сегодня?", reply_markup=reply_markup)
    logging.info("Отправлен запрос на обед.")

async def send_summary(application: Application):
    global CHAT_ID
    if not CHAT_ID:
        logging.info("CHAT_ID ещё не установлен, пропускаем отправку отчёта.")
        return

    data = load_data()
    count = sum(1 for v in data.values() if v == "Да")

    if count == 0:
        message = "Ты не должен ощущать чувства вины (нет)"
    elif count == 1:
        message = "Ну ничего, ты старался!"
    elif count == 2:
        message = "Неплохо!"
    elif count == 3:
        message = "Красавчик, целых три обеда на этой неделе!"
    elif count == 4:
        message = "Вау! Ты супер!"
    elif count == 5:
        message = "Всю рабочую неделю обедал? Невероятно!"
    elif count == 6:
        message = "Ты просто лучший, почти всю неделю обедал!"
    else:
        message = "Амбиливбл! Вин стрик!"

    await application.bot.send_message(chat_id=CHAT_ID, text=f"📊 Обеденная статистика за неделю:

{message}")
    logging.info("Отправлен отчёт за неделю.")
    save_data({})

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    text = update.message.text
    now = datetime.now(TIMEZONE)
    date_str = now.strftime("%Y-%m-%d")

    data = load_data()
    data[date_str] = text
    save_data(data)

    await context.bot.send_message(chat_id=CHAT_ID, text="Ответ сохранён.")
    logging.info(f"Сохранён ответ: {date_str} -> {text}")

async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_response))

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: asyncio.create_task(ask_lunch(application)), "cron", hour=11, minute=55)
    scheduler.add_job(lambda: asyncio.create_task(send_summary(application)), "cron", day_of_week="sun", hour=19, minute=0)
    scheduler.start()

    logging.info("🔁 Инициализация LunchBot...")
    await application.initialize()
    logging.info("✅ LunchBot готов. Старт polling...")
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
