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

# Салоны сети "Фортуна"
salons = {
    "Фортуна - Центральный": "ул. Ленина, д.10",
    "Фортуна - Восточный": "ул. Советская, д.25",
    "Фортуна - Западный": "пр. Мира, д.5"
}

# Процедуры с мастерами и рейтингом
services = {
    "Оформление бровей": [
        {"name": "Мария", "rating": 4.5},
        {"name": "Александра", "rating": 4.8},
        {"name": "Елена", "rating": 4.3}
    ],
    "Окрашивание хной": [
        {"name": "Ольга", "rating": 4.6},
        {"name": "Татьяна", "rating": 4.2}
    ],
    "Ламинирование": [
        {"name": "Ирина", "rating": 4.7},
        {"name": "Наталья", "rating": 4.4}
    ]
}

appointments = {}  # {user_id: appointment_dict}

PINNED_ADMIN_MESSAGE_FILE = "pinned_admin_message.json"
PINNED_USER_MESSAGES_FILE = "pinned_user_messages.json"


def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

# Админский закреп
def load_admin_pinned_id():
    data = load_json(PINNED_ADMIN_MESSAGE_FILE)
    return data.get("id")

def save_admin_pinned_id(message_id):
    save_json(PINNED_ADMIN_MESSAGE_FILE, {"id": message_id})

# Пользовательские закрепы
def load_user_pinned_ids():
    return load_json(PINNED_USER_MESSAGES_FILE)

def save_user_pinned_ids(data):
    save_json(PINNED_USER_MESSAGES_FILE, data)


async def update_admin_pinned_message(bot):
    future_apps = [a for a in appointments.values() if a["datetime"] > datetime.now()]
    future_apps.sort(key=lambda x: x["datetime"])

    if not future_apps:
        text = "Нет предстоящих записей."
    else:
        text = "\u2728 <b>Ближайшие записи всех клиентов:</b>\n"
        for a in future_apps:
            text += f"\n\ud83d\udd39 {a['date']} {a['time']} — {a['service']} у мастера {a['master']} в {a['salon']} (@{a['username']})"

    pinned_id = load_admin_pinned_id()
    try:
        if pinned_id:
            await bot.edit_message_text(chat_id=ADMIN_CHAT_ID, message_id=pinned_id, text=text, parse_mode="HTML")
        else:
            msg = await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode="HTML")
            await bot.pin_chat_message(chat_id=ADMIN_CHAT_ID, message_id=msg.message_id)
            save_admin_pinned_id(msg.message_id)
    except Exception as e:
        print("Ошибка при обновлении закрепа админа:", e)


async def update_user_pinned_message(bot, user_id):
    user_apps = appointments.get(user_id)
    pinned_ids = load_user_pinned_ids()

    if not user_apps or user_apps["datetime"] < datetime.now():
        # Если записи нет или она прошла — удаляем закреп (если был)
        if str(user_id) in pinned_ids:
            try:
                await bot.unpin_chat_message(chat_id=user_id, message_id=pinned_ids[str(user_id)])
            except:
                pass
            pinned_ids.pop(str(user_id))
            save_user_pinned_ids(pinned_ids)
        return

    text = (
        f"\u2728 <b>Ваша запись:</b>\n\n"
        f"Салон: {user_apps['salon']}\n"
        f"Процедура: {user_apps['service']}\n"
        f"Мастер: {user_apps['master']} (рейтинг {user_apps['master_rating']})\n"
        f"Дата: {user_apps['date']}\n"
        f"Время: {user_apps['time']}\n"
        f"\nЕсли хотите отменить запись, нажмите кнопку ниже."
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Отменить запись", callback_data="cancel_appointment")]]
    )

    try:
        if str(user_id) in pinned_ids:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=pinned_ids[str(user_id)],
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            msg = await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            await bot.pin_chat_message(chat_id=user_id, message_id=msg.message_id)
            pinned_ids[str(user_id)] = msg.message_id
            save_user_pinned_ids(pinned_ids)
    except Exception as e:
        print("Ошибка при обновлении закрепа пользователя:", e)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Если у пользователя уже есть запись — показываем её
    if user_id in appointments:
        await update_user_pinned_message(context.bot, user_id)
        await update.message.reply_text("Добро пожаловать! У вас уже есть запись. Можете отменить её или сделать новую через /start.")
        return

    # Выбор салона
    keyboard = [[salon] for salon in salons]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите салон:", reply_markup=reply_markup)


async def handle_salon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text not in salons:
        await update.message.reply_text("Пожалуйста, выберите салон из списка.")
        return

    context.user_data["salon"] = text

    # Выбор процедуры
    keyboard = [[service] for service in services]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите процедуру:", reply_markup=reply_markup)


async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text not in services:
        await update.message.reply_text("Пожалуйста, выберите процедуру из списка.")
        return

    context.user_data["service"] = text

    # Выбор мастера
    masters = services[text]
    keyboard = [
        [f"{m['name']} (рейтинг: {m['rating']})"] for m in masters
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выберите мастера:", reply_markup=reply_markup)


async def handle_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    service = context.user_data.get("service")
    if not service:
        await update.message.reply_text("Сначала выберите процедуру.")
        return

    masters = services[service]
    master_names = [f"{m['name']} (рейтинг: {m['rating']})" for m in masters]

    if text not in master_names:
        await update.message.reply_text("Пожалуйста, выберите мастера из списка.")
        return

    # Сохраняем имя мастера и рейтинг
    selected_master_name = text.split(" (рейтинг:")[0]
    selected_master_rating = next(m["rating"] for m in masters if m["name"] == selected_master_name)

    context.user_data["master"] = selected_master_name
    context.user_data["master_rating"] = selected_master_rating

    # Показ календаря для выбора даты
    await show_calendar(update, context)


async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.today()
    buttons = []

    for i in range(5):
        day = today + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(day.strftime("%d.%m.%Y (%a)"), callback_data=f"date_{day.strftime('%Y-%m-%d')}")
        ])

    buttons.append([InlineKeyboardButton("Назад", callback_data="back_to_master")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выберите дату:", reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data.startswith("date_"):
        selected_date = data[5:]
        context.user_data["date"] = selected_date
        # Предлагаем время
        await show_times(query, context)
    elif data.startswith("time_"):
        selected_time = data[5:]
        context.user_data["time"] = selected_time

        # Сохраняем запись
        dt_str = f"{context.user_data['date']} {context.user_data['time']}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

        appointments[user_id] = {
            "salon": context.user_data["salon"],
            "service": context.user_data["service"],
            "master": context.user_data["master"],
            "master_rating": context.user_data["master_rating"],
            "date": context.user_data["date"],
            "time": context.user_data["time"],
            "datetime": dt,
            "username": query.from_user.username or query.from_user.full_name
        }

        await query.message.edit_text("Запись успешно создана!")

        # Обновляем закрепы у пользователя и админа
        await update_user_pinned_message(context.bot, user_id)
        await update_admin_pinned_message(context.bot)

    elif data == "cancel_appointment":
        if user_id in appointments:
            appointments.pop(user_id)
            await query.message.edit_text("Ваша запись отменена.")
            # Обновляем закрепы
            await update_user_pinned_message(context.bot, user_id)
            await update_admin_pinned_message(context.bot)
        else:
            await query.message.edit_text("У вас нет активной записи.")

    elif data == "back_to_master":
        # Показать выбор мастера заново
        service = context.user_data.get("service")
        if not service:
            await query.message.edit_text("Произошла ошибка, попробуйте заново /start")
            return
        masters = services[service]
        keyboard = [
            [f"{m['name']} (рейтинг: {m['rating']})"] for m in masters
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await query.message.edit_text("Выберите мастера:", reply_markup=reply_markup)

async def show_times(query, context):
    # Предлагаем 5 слотов с шагом 1 час с 10:00 до 15:00
    buttons = []
    base_time = datetime.strptime("10:00", "%H:%M")
    for i in range(5):
        t = (base_time + timedelta(hours=i)).strftime("%H:%M")
        buttons.append([InlineKeyboardButton(t, callback_data=f"time_{t}")])
    buttons.append([InlineKeyboardButton("Назад", callback_data="back_to_master")])
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.message.edit_text("Выберите время:", reply_markup=reply_markup)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_salon), group=0)  # сначала салон
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service), group=1)  # потом процедура
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_master), group=2)  # потом мастер

    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        url_path=WEBHOOK_SECRET,
        webhook_url=f"https://beautytimebot-quw2.onrender.com/614200601c1fe24c024262b84559a683"
    )


if __name__ == '__main__':
    main()
