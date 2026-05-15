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

# Модель
MODEL_ID = "compound-beta"
MODEL_NAME = "Compound (с интернетом)"

MAX_HISTORY = 20  # Храним 20 сообщений, но обрезаем если слишком длинные

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

def main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🗑 Очистить историю", callback_data="clear")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================
# Команды
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Доступ запрещён.")
        return

    await update.message.reply_text(
        "Привет! Я бот с ИИ + поиском в интернете.\n\n"
        "Просто пишите сообщение - отвечу с учётом актуальной информации из сети.\n\n"
        "Кнопка ниже для сброса диалога:",
        reply_markup=main_keyboard(),
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

    if action == "clear":
        data["history"] = []
        await query.edit_message_text(
            "История очищена. Пишите сообщение:",
            reply_markup=main_keyboard(),
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
        messages = [
            {
                "role": "system",
                "content": "Ты полезный ассистент. Отвечай на русском, если пользователь пишет на русском. Будь кратким и по делу.",
            }
        ] + data["history"]

        response = groq_client.chat.completions.create(
            model=MODEL_ID,
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
        # Если ошибка 413 (слишком длинный запрос) - обрезаем историю и пробуем снова
        if "413" in str(e) or "too_large" in str(e) or "Request Entity Too Large" in str(e):
            data["history"] = data["history"][-4:]  # Оставляем только 4 последних
            await update.message.reply_text("История была слишком длинной - обрезал. Попробуйте ещё раз.")
        else:
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
