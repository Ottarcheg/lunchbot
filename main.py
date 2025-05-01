import asyncio
import json
import logging
from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters, ContextTypes
)
from pytz import timezone

# === НАСТРОЙКИ ===
TOKEN = "7701441306:AAF5Dd4VcXSilKIw9mAfPMmWQrzvAiWB69I"
CHAT_ID = 344657888
DATA_FILE = "lunch_data.json"
CYPRUS_TZ = timezone("Europe/Nicosia")

# === ЛОГИ ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# === ИНИЦИАЛИЗАЦИЯ ===
app = Flask(__name__)
scheduler = BackgroundScheduler(timezone=CYPRUS_TZ)

def load_data():
    try:
        logging.info("📂 Загружаю данные из файла...")
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("⚠️ Файл данных не найден, создаю новый.")
        return {}

def save_data(data):
    logging.info("💾 Сохраняю данные в файл...")
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def ask_lunch(application):
    now = datetime.now(CYPRUS_TZ).strftime('%H:%M:%S')
    logging.info(f"⏰ Время задать вопрос. Сейчас {now}")
    try:
        await application.bot.send_message(
            chat_id=CHAT_ID,
            text="Ты пообедал сегодня?",
            reply_markup={
                "keyboard": [["Да"], ["Нет"]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        )
        logging.info("📨 Вопрос отправлен успешно.")
    except Exception as e:
        logging.exception(f"Ошибка при отправке вопроса: {e}")

async def handle_response(update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("📩 Получен ответ от пользователя.")
    user_response = update.message.text.strip()
    data = load_data()
    today = datetime.now(CYPRUS_TZ).strftime('%Y-%m-%d')

    if today not in data:
        data[today] = {
            "Ответы": [],
            "Группировка": {
                "Злаки": 0,
                "Белок": 0,
                "Овощи": 0,
                "Фрукты": 0,
                "Жиры": 0,
                "Молоко": 0
            }
        }

    if user_response.lower() in ["да", "нет"]:
        data[today]["Ответы"].append(user_response.lower())
        save_data(data)
        await update.message.reply_text("Ответ сохранён ✅")
        logging.info(f"✅ Ответ '{user_response}' сохранён.")
        return

    if " - " in user_response:
        try:
            category, value = map(str.strip, user_response.split(" - "))
            value = float(value)
            if category in data[today]["Группировка"]:
                data[today]["Группировка"][category] += value
                save_data(data)
                await update.message.reply_text(f"{category} обновлено на +{value} ✅")
                logging.info(f"📊 {category} увеличено на {value}.")
                return
        except Exception as e:
            logging.exception("Ошибка при обработке категории")

    await update.message.reply_text("Пожалуйста, отправь 'Да', 'Нет' или 'Категория - X'.")
    logging.info("⚠️ Неверный формат сообщения.")

async def send_weekly_summary(application):
    logging.info("📊 Генерация еженедельной статистики...")
    data = load_data()
    count = sum(day.count("да") for day in data.values())
    messages = {
        0: "0/7. На этой неделе ты совсем забывал обедать. Надо это исправить! 🍽️",
        1: "1/7. Ты пообедал всего один раз за неделю. Так нельзя! 😥",
        2: "2/7. Два обеда — это уже что-то, но всё ещё мало. 🥄",
        3: "3/7. Серединка на половинку. Надо лучше! 🍴",
        4: "4/7. Четыре раза — почти отлично! Ещё немного! 🍛",
        5: "5/7. Отличный результат! Почти каждый день с обедом! 👏",
        6: "6/7. Ты был на высоте! Шесть обедов из семи! 🔥",
        7: "7/7! Идеально! Все семь обедов на месте! 🏆",
    }
    message = (
        "📊 Обеденная статистика за неделю:\n" +
        messages.get(count, "Что-то пошло не так...")
    )
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
        logging.info("📤 Статистика отправлена.")
    except Exception as e:
        logging.exception(f"Ошибка при отправке статистики: {e}")

@app.route("/")
def home():
    logging.info("🌍 Получен HTTP GET запрос на /")
    return "LunchBot is running"

from telegram import Update
from telegram.ext import ContextTypes
from datetime import timedelta

async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("📥 Обнаружено сообщение в группе или канале.")
    if update.message and "завтрак" in update.message.text.lower():
        logging.info("🍳 Обнаружено сообщение с 'завтрак'.")

        async def remind(delay_minutes, note):
            await asyncio.sleep(delay_minutes * 60)
            try:
                await context.bot.send_message(chat_id=CHAT_ID, text=f"⏰ Прошло уже {note} после завтрака. Скоро обед!")
                logging.info(f"🔔 Напоминание '{note}' отправлено.")
            except Exception as e:
                logging.exception(f"Ошибка при отправке напоминания '{note}': {e}")

        asyncio.create_task(remind(270, "4ч30м"))  # 4 ч 30 мин
        asyncio.create_task(remind(290, "4ч50м"))  # 4 ч 50 мин
        asyncio.create_task(remind(300, "5ч"))     # 5 ч

async def main():
    logging.info("🚀 Инициализация Telegram Application...")
    logging.info(f"🕒 Время сервера (UTC): {datetime.now(timezone('UTC'))}")
    logging.info(f"🕒 Время Кипра: {datetime.now(CYPRUS_TZ)}")

    application = ApplicationBuilder().token(TOKEN).build()
    await application.bot.delete_webhook(drop_pending_updates=True)
    from telegram.ext import filters

    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_response))

    # === Хендлер для канала ===
    application.add_handler(
        MessageHandler(filters.TEXT & (filters.ChatType.CHANNEL | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP), handle_channel_message)
    )

    # Получаем текущий event loop
    loop = asyncio.get_running_loop()

    # Планирование задач
    logging.info("📅 Планирую задачи...")
    scheduler.add_job(lambda: loop.create_task(ask_lunch(application)), "cron", hour=19, minute=0)
    scheduler.add_job(lambda: loop.create_task(send_weekly_summary(application)), "cron", day_of_week="sun", hour=22, minute=0)
    scheduler.add_job(lambda: loop.create_task(send_daily_table(application)), "cron", hour=16, minute=50)
    scheduler.add_job(lambda: loop.create_task(send_nutrition_summary(application)), "cron", hour=0, minute=0)
    scheduler.start()
    logging.info("✅ Планировщик запущен")
    
    logging.info("📡 LunchBot готов. Старт polling...")
    await application.run_polling()
    
async def send_daily_table(application):
    logging.info("📋 Отправка таблицы питания в группу...")
    table = (
        "| Категория | План | Факт |\n"
        "|-----------|------|------|\n"
        "| Злаки     | 7    |      |\n"
        "| Белок     | 6    |      |\n"
        "| Овощи     | 3    |      |\n"
        "| Фрукты    | 4    |      |\n"
        "| Жиры      | 4    |      |\n"
        "| Молоко    | 1    |      |"
    )
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=f"🍽 План питания на сегодня:\n\n{table}")
        logging.info("📤 Таблица отправлена.")
    except Exception as e:
        logging.exception("Ошибка при отправке таблицы.")
        
async def send_nutrition_summary(application):
    logging.info("📊 Генерация дневной статистики питания...")
    data = load_data()
    today = datetime.now(CYPRUS_TZ).strftime('%Y-%m-%d')
    norms = {
        "Злаки": 7, "Белок": 6, "Овощи": 3, "Фрукты": 4, "Жиры": 4, "Молоко": 1
    }

    if today not in data or "Группировка" not in data[today]:
        logging.warning("⚠️ Нет данных для сравнения.")
        return

    actuals = data[today]["Группировка"]
    summary_lines = ["📊 Сравнение рациона за день:"]
    for cat, plan in norms.items():
        fact = actuals.get(cat, 0)
        diff = round(fact - plan, 1)
        status = "✅" if diff == 0 else ("⬆️" if diff > 0 else "⬇️")
        summary_lines.append(f"{cat}: план {plan}, факт {fact} ({status} {diff})")

    message = "\n".join(summary_lines)
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
        logging.info("📤 Дневная статистика отправлена.")
    except Exception as e:
        logging.exception("Ошибка при отправке дневной статистики.")

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    logging.info("🔁 Запуск LunchBot через asyncio.run...")
    asyncio.run(main())
