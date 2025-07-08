import os
import json
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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

services = {
    "Оформление бровей": "30 мин",
    "Окрашивание хной": "45 мин",
    "Ламинирование": "1 час"
}

appointments = []
PINNED_MESSAGE_ID_FILE = "pinned_message_id.json"


def load_pinned_id():
    if os.path.exists(PINNED_MESSAGE_ID_FILE):
        with open(PINNED_MESSAGE_ID_FILE, "r") as f:
            return json.load(f).get("id")
    return None


def save_pinned_id(message_id):
    with open(PINNED_MESSAGE_ID_FILE, "w") as f:
        json.dump({"id": message_id}, f)


async def update_pinned_message(bot):
    future_appointments = [a for a in appointments if a["datetime"] > datetime.now()]
    future_appointments.sort(key=lambda x: x["datetime"])
    if not future_appointments:
        return

    text = "\u2728 <b>Ближайшие записи</b>:\n"
    for a in future_appointments:
        text += f"\n\ud83d\udd39 {a['date']} в {a['time']} — {a['service']} (@{a['user']})"

    pinned_id = load_pinned_id()
    try:
        if pinned_id:
            await bot.edit_message_text(chat_id=ADMIN_CHAT_ID, message_id=pinned_id, text=text, parse_mode="HTML")
        else:
            msg = await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode="HTML")
            await bot.pin_chat_message(chat_id=ADMIN_CHAT_ID, message_id=msg.message_id)
            save_pinned_id(msg.message_id)
    except Exception as e:
        print("Ошибка при обновлении закрепа:", e)


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

    buttons.append([InlineKeyboardButton("Назад", callback_data="back")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выберите дату:", reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("date_"):
        date_str = query.data.replace("date_", "")
        context.user_data["date"] = date_str
        await query.message.reply_text("Напишите удобное время (например: 14:30):")

    elif query.data == "back":
        await start(update, context)


async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = context.user_data.get("service")
    date = context.user_data.get("date")
    time = update.message.text

    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите время в формате ЧЧ:ММ, например 14:30.")
        return

    if service and date:
        username = update.message.from_user.username or update.message.from_user.first_name
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        appointments.append({"service": service, "date": date, "time": time, "user": username, "datetime": dt})

        message = (
            f"📋 Новая запись!\n"
            f"Услуга: {service}\n"
            f"Дата: {date}\n"
            f"Время: {time}\n"
            f"Пользователь: @{username}"
        )
        await update.message.reply_text("Спасибо! Ваша заявка отправлена.")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
        await update_pinned_message(context.bot)
        context.user_data.clear()
    else:
        await update.message.reply_text("Пожалуйста, выберите услугу сначала (/start).")


# Создание и запуск бота с вебхуком
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^\d{1,2}:\d{2}$'), handle_service))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d{1,2}:\d{2}$'), handle_time))

app.run_webhook(
    listen="0.0.0.0",
    port=5000,
    url_path=WEBHOOK_SECRET,
    webhook_url=f"https://beautytimebot-quw2.onrender.com/614200601c1fe24c024262b84559a683",
    secret_token=WEBHOOK_SECRET
) 
