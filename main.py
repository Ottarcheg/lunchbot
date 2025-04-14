
import asyncio
import json
import logging
from datetime import datetime
from pytz import timezone
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import nest_asyncio
from flask import Flask
from threading import Thread

# Настройки
TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = 570026464
DATA_FILE = "lunch_data.json"
TIMEZONE = timezone("Europe/Nicosia")

# Логирование
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

# Flask сервер
app = Flask(__name__)

@app.route("/")
def home():
    return "LunchBot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Загрузка данных
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Не удалось загрузить данные: {e}")
        return {}

# Сохранение данных
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Отправка вопроса об обеде
async def ask_lunch(app: Application):
    logging.info("📨 Отправка вопроса о ланче")
    now = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    data = load_data()
    data[now] = data.get(now, {})
    markup = ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True)
    await app.bot.send_message(chat_id=CHAT_ID, text="Ты пообедал сегодня?", reply_markup=markup)
    save_data(data)

# Обработка ответа
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != CHAT_ID:
        return

    response = update.message.text.strip()
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    data = load_data()
    data[today] = {"response": response}
    save_data(data)
    await context.bot.send_message(chat_id=CHAT_ID, text="Ответ записан!")

# Подведение итогов недели
async def weekly_summary(app: Application):
    logging.info("📊 Подведение итогов недели")
    data = load_data()
    count = sum(1 for day in data.values() if day.get("response") == "Да")
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
    summary = messages.get(count, f"Ты пообедал {count} раз(а) на этой неделе.")
    await app.bot.send_message(chat_id=CHAT_ID, text=f"📊 Обеденная статистика за неделю:
{summary}")
    save_data({})  # Сброс данных

# Запуск
async def main():
    logging.info("🔁 Инициализация LunchBot...")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT, handle_response))

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: application.create_task(ask_lunch(application)), "cron", hour=12, minute=0)
    scheduler.add_job(lambda: application.create_task(weekly_summary(application)), "cron", day_of_week="sun", hour=19, minute=0)
    scheduler.start()

    Thread(target=run_flask).start()
    logging.info("✅ LunchBot готов. Старт polling...")
    await application.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
