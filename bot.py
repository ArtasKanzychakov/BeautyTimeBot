import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_API_KEY")

services = {
    "Оформление бровей": "30 мин",
    "Окрашивание хной": "45 мин",
    "Ламинирование": "1 час"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[service] for service in services]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Выбери процедуру:", reply_markup=reply_markup)

async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.message.text
    if service in services:
        await update.message.reply_text(f"Вы выбрали: {service}\nДлительность: {services[service]}\n\nПожалуйста, напишите удобное время записи.")
    else:
        await update.message.reply_text("Пожалуйста, выбери услугу из списка.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service))

app.run_polling()
