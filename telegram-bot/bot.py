"""
РЕЙТ AI Bot - Telegram бот с ChatGPT и Gemini
Текстовый чат + генерация изображений (DALL-E 3)
Управление через inline-кнопки.

Команды:
/start - главное меню с кнопками
/img <описание> - сгенерировать изображение через DALL-E 3
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
from openai import AsyncOpenAI
import google.generativeai as genai

# ============================================================
# НАСТРОЙКИ
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "ВАШ_ТОКЕН_ОТ_BOTFATHER")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ВАШ_КЛЮЧ_OPENAI")
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "ВАШ_КЛЮЧ_GOOGLE")

# Ваш Telegram ID (только вы сможете пользоваться ботом)
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Модели
GPT_MODEL = "gpt-4o"
GEMINI_MODEL = "gemini-2.5-pro-preview-05-06"
DALLE_MODEL = "dall-e-3"

# Максимум сообщений в контексте
MAX_HISTORY = 20

# ============================================================
# Инициализация
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
genai.configure(api_key=GOOGLE_AI_API_KEY)

user_data: Dict[int, dict] = {}


def get_user_data(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {
            "model": "gpt",
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

def main_keyboard(current_model: str = "gpt") -> InlineKeyboardMarkup:
    """Главная клавиатура с кнопками управления."""
    gpt_label = "ChatGPT (GPT-4o)" if current_model != "gpt" else "✅ ChatGPT (GPT-4o)"
    gemini_label = "Gemini 2.5 Pro" if current_model != "gemini" else "✅ Gemini 2.5 Pro"

    keyboard = [
        [
            InlineKeyboardButton(gpt_label, callback_data="switch_gpt"),
            InlineKeyboardButton(gemini_label, callback_data="switch_gemini"),
        ],
        [
            InlineKeyboardButton("🖼 Сгенерировать картинку", callback_data="img_mode"),
        ],
        [
            InlineKeyboardButton("🗑 Очистить историю", callback_data="clear"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================
# Обработчики команд
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Доступ запрещён.")
        return

    data = get_user_data(update.effective_user.id)
    model_name = "ChatGPT (GPT-4o)" if data["model"] == "gpt" else "Gemini 2.5 Pro"

    await update.message.reply_text(
        f"Привет! Текущая модель: **{model_name}**\n\n"
        "Просто пишите сообщение - бот ответит.\n"
        "Для картинки: /img описание\n\n"
        "Или используйте кнопки:",
        reply_markup=main_keyboard(data["model"]),
        parse_mode="Markdown",
    )


# ============================================================
# Обработчик кнопок
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(query.from_user.id):
        return

    data = get_user_data(query.from_user.id)
    action = query.data

    if action == "switch_gpt":
        data["model"] = "gpt"
        data["history"] = []
        await query.edit_message_text(
            "Переключил на **ChatGPT (GPT-4o)**. История очищена.\n\nПишите сообщение:",
            reply_markup=main_keyboard("gpt"),
            parse_mode="Markdown",
        )

    elif action == "switch_gemini":
        data["model"] = "gemini"
        data["history"] = []
        await query.edit_message_text(
            "Переключил на **Gemini 2.5 Pro**. История очищена.\n\nПишите сообщение:",
            reply_markup=main_keyboard("gemini"),
            parse_mode="Markdown",
        )

    elif action == "clear":
        data["history"] = []
        model_name = "ChatGPT (GPT-4o)" if data["model"] == "gpt" else "Gemini 2.5 Pro"
        await query.edit_message_text(
            f"История очищена. Модель: **{model_name}**\n\nПишите сообщение:",
            reply_markup=main_keyboard(data["model"]),
            parse_mode="Markdown",
        )

    elif action == "img_mode":
        await query.edit_message_text(
            "Отправьте описание картинки командой:\n\n"
            "`/img красивый закат над морем в стиле масляной живописи`\n\n"
            "Генерация через DALL-E 3 (OpenAI).",
            parse_mode="Markdown",
        )


# ============================================================
# Генерация изображений (DALL-E 3)
# ============================================================

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text(
            "Укажите описание после команды:\n"
            "`/img красивый закат над морем`",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text("Генерирую изображение...")

    try:
        response = await openai_client.images.generate(
            model=DALLE_MODEL,
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt or ""

        caption = f"Промпт: {prompt}"
        if revised_prompt:
            caption += f"\n\nDALL-E: {revised_prompt[:300]}"

        await msg.delete()
        await update.message.reply_photo(photo=image_url, caption=caption)

    except Exception as e:
        logger.error(f"DALL-E error: {e}")
        await msg.edit_text(f"Ошибка генерации: {str(e)[:500]}")


# ============================================================
# Обработка текстовых сообщений
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    user_id = update.effective_user.id
    data = get_user_data(user_id)
    user_message = update.message.text

    # Добавляем в историю
    data["history"].append({"role": "user", "content": user_message})
    if len(data["history"]) > MAX_HISTORY:
        data["history"] = data["history"][-MAX_HISTORY:]

    # Показываем "печатает..."
    await update.message.chat.send_action("typing")

    reply = ""
    try:
        if data["model"] == "gpt":
            reply = await chat_gpt(data["history"])
        else:
            reply = await chat_gemini(data["history"])

        data["history"].append({"role": "assistant", "content": reply})

        # Пробуем с Markdown, если не получится - без
        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Ошибка: {str(e)[:500]}")


# ============================================================
# ChatGPT (OpenAI)
# ============================================================

async def chat_gpt(history: List[dict]) -> str:
    messages = [
        {
            "role": "system",
            "content": "Ты полезный ассистент. Отвечай на русском, если пользователь пишет на русском. Будь кратким и по делу.",
        }
    ] + history

    response = await openai_client.chat.completions.create(
        model=GPT_MODEL,
        messages=messages,
        max_tokens=4096,
        temperature=0.7,
    )

    return response.choices[0].message.content


# ============================================================
# Gemini (Google)
# ============================================================

async def chat_gemini(history: List[dict]) -> str:
    model = genai.GenerativeModel(GEMINI_MODEL)

    # Конвертируем формат: OpenAI -> Gemini
    gemini_history = []
    for msg in history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)
    last_message = history[-1]["content"]
    response = await chat.send_message_async(last_message)

    return response.text


# ============================================================
# Запуск
# ============================================================

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("img", generate_image))

    # Кнопки
    app.add_handler(CallbackQueryHandler(button_handler))

    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
