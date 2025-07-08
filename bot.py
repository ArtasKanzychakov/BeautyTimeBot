import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_API_KEY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://beautytimebot-quw2.onrender.com
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # 5000

services = {
    "Оформление бровей": "30 мин",
    "Окрашивание хной": "45 мин",
    "Ламинирование": "1 час"
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[service] for service in services]
    keyboard.append(["Показать все услуги"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Выбери процедуру:", reply_markup=reply_markup)


async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Показать все услуги":
        msg = "\n".join([f"• {k} — {v}" for k, v in services.items()])
        await update.message.reply_text(f"Доступные услуги:\n\n{msg}")
        return

    if text in services:
        context.user_data["service"] = text
        await show_calendar(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выбери услугу из списка.")


async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.today()
    buttons = []

    for i in range(5):
        day = today + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(day.strftime("%d.%m.%Y (%a)"), callback_data=f"date_{day.strftime('%Y-%m-%d')}")
        ])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выберите дату:", reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("date_"):
        date_str = query.data.replace("date_", "")
        context.user_data["date"] = date_str
        await query.message.reply_text("Напишите удобное время (например: 14:30):")


async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = context.user_data.get("service")
    date = context.user_data.get("date")
    time = update.message.text

    if service and date:
        message = (
            f"📋 Новая запись!\n"
            f"Услуга: {service}\n"
            f"Дата: {date}\n"
            f"Время: {time}\n"
            f"Пользователь: @{update.message.from_user.username or update.message.from_user.first_name}"
        )
        await update.message.reply_text("Спасибо! Ваша заявка отправлена.")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
        context.user_data.clear()
    else:
        await update.message.reply_text("Пожалуйста, выберите услугу сначала (/start).")


# Создание и запуск бота с вебхуком
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^\d{1,2}:\d{2}$'), handle_service))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d{1,2}:\d{2}$'), handle_time))

# Запуск вебхука
app.run_webhook(
    listen="0.0.0.0",
    port=5000,
    webhook_url=f"{WEBHOOK_URL}/5000",  # <-- ВАЖНО!
    secret_token="5000"
)
