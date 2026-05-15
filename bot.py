"""
РЕЙТ AI Bot - Telegram бот с Groq (Llama 4)
100% бесплатный, работает из России, без карты.

Groq - сверхбыстрый ИИ (500+ токенов/сек), модели уровня GPT-4o.
Регистрация: https://console.groq.com (email или Google, без карты).
"""

import os
import logging
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from groq import Groq

# ============================================================
# НАСТРОЙКИ
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Модели Groq (все бесплатные)
MODELS = {
    "llama4": {
        "id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "name": "Llama 4 Scout",
        "description": "Новейшая модель Meta, уровень GPT-4o",
    },
    "llama3": {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B",
        "description": "Мощная, отлично пишет на русском",
    },
    "gemma": {
        "id": "gemma2-9b-it",
        "name": "Gemma 2 9B",
        "description": "Быстрая модель от Google, хороша для коротких задач",
    },
}

MAX_HISTORY = 20

# ============================================================
# Инициализация
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

user_data: Dict[int, dict] = {}


def get_user_data(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {
            "model": "llama4",
            "history": [],
        }
    return user_data[user_id]


def is_allowed(user_id: int) -> bool:
    if ALLOWED_USER_ID == 0:
        return True
    return user_id == ALLOWED_USER_ID


# ============================================================
# Клавиатуры
# ============================================================

def main_keyboard(current_model: str = "llama4") -> InlineKeyboardMarkup:
    keyboard = []
    for key, model_info in MODELS.items():
        label = f"✅ {model_info['name']}" if key == current_model else model_info['name']
        keyboard.append([InlineKeyboardButton(label, callback_data=f"model_{key}")])
    keyboard.append([InlineKeyboardButton("🗑 Очистить историю", callback_data="clear")])
    return InlineKeyboardMarkup(keyboard)


# ============================================================
# Команды
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Доступ запрещён.")
        return

    data = get_user_data(update.effective_user.id)
    model_name = MODELS[data["model"]]["name"]

    await update.message.reply_text(
        f"Привет! Я бот с ИИ (100% бесплатный).\n\n"
        f"Текущая модель: *{model_name}*\n\n"
        "Просто пишите сообщение - отвечу.\n"
        "Кнопки ниже для переключения модели:",
        reply_markup=main_keyboard(data["model"]),
        parse_mode="Markdown",
    )


# ============================================================
# Кнопки
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(query.from_user.id):
        return

    data = get_user_data(query.from_user.id)
    action = query.data

    if action.startswith("model_"):
        model_key = action.replace("model_", "")
        if model_key in MODELS:
            data["model"] = model_key
            data["history"] = []
            model_info = MODELS[model_key]
            await query.edit_message_text(
                f"Переключил на *{model_info['name']}*\n"
                f"_{model_info['description']}_\n\n"
                "История очищена. Пишите сообщение:",
                reply_markup=main_keyboard(model_key),
                parse_mode="Markdown",
            )

    elif action == "clear":
        data["history"] = []
        model_name = MODELS[data["model"]]["name"]
        await query.edit_message_text(
            f"История очищена. Модель: *{model_name}*\n\nПишите сообщение:",
            reply_markup=main_keyboard(data["model"]),
            parse_mode="Markdown",
        )


# ============================================================
# Обработка сообщений
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    user_id = update.effective_user.id
    data = get_user_data(user_id)
    user_message = update.message.text

    data["history"].append({"role": "user", "content": user_message})
    if len(data["history"]) > MAX_HISTORY:
        data["history"] = data["history"][-MAX_HISTORY:]

    await update.message.chat.send_action("typing")

    try:
        model_id = MODELS[data["model"]]["id"]

        messages = [
            {
                "role": "system",
                "content": "Ты полезный ассистент. Отвечай на русском, если пользователь пишет на русском. Будь кратким и по делу.",
            }
        ] + data["history"]

        response = groq_client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        data["history"].append({"role": "assistant", "content": reply})

        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Groq error: {e}")
        await update.message.reply_text(f"Ошибка: {str(e)[:500]}")


# ============================================================
# Запуск
# ============================================================

def main():
    if not TELEGRAM_TOKEN:
        print("ОШИБКА: Не задан TELEGRAM_TOKEN!")
        return

    if not GROQ_API_KEY:
        print("ОШИБКА: Не задан GROQ_API_KEY!")
        print("Получите бесплатно: https://console.groq.com")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен! Ожидаю сообщения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
