"""
РЕЙТ AI Bot - Telegram бот с Gemini 2.5 Flash
100% бесплатный: текстовый чат + поиск в интернете + генерация картинок

Всё через Google AI Studio (бесплатно, без карты).
"""

import os
import io
import base64
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
from google import genai
from google.genai import types

# ============================================================
# НАСТРОЙКИ
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Модели
TEXT_MODEL = "gemini-2.5-flash-preview-05-20"
IMAGE_MODEL = "gemini-2.5-flash-preview-image-generation"

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

# Google GenAI клиент
client = genai.Client(api_key=GOOGLE_AI_API_KEY)

# Хранилище
user_data: Dict[int, dict] = {}


def get_user_data(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {
            "mode": "chat",  # "chat" или "search"
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

def main_keyboard(current_mode: str = "chat") -> InlineKeyboardMarkup:
    chat_label = "✅ Чат" if current_mode == "chat" else "💬 Чат"
    search_label = "✅ Чат + Интернет" if current_mode == "search" else "🌐 Чат + Интернет"

    keyboard = [
        [
            InlineKeyboardButton(chat_label, callback_data="mode_chat"),
            InlineKeyboardButton(search_label, callback_data="mode_search"),
        ],
        [
            InlineKeyboardButton("🖼 Сгенерировать картинку", callback_data="img_help"),
        ],
        [
            InlineKeyboardButton("🗑 Очистить историю", callback_data="clear"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================
# Команды
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Доступ запрещён.")
        return

    data = get_user_data(update.effective_user.id)
    mode_name = "Чат" if data["mode"] == "chat" else "Чат + Интернет"

    await update.message.reply_text(
        f"Привет! Я бот с Gemini 2.5 (100% бесплатный).\n\n"
        f"Режим: **{mode_name}**\n\n"
        "**Что умею:**\n"
        "- Отвечать на вопросы (как ChatGPT)\n"
        "- Искать в интернете актуальную информацию\n"
        "- Генерировать картинки по описанию\n\n"
        "**Как пользоваться:**\n"
        "- Просто пишите текст - отвечу\n"
        "- /img описание - сгенерирую картинку\n"
        "- Кнопки ниже для настройки",
        reply_markup=main_keyboard(data["mode"]),
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

    if action == "mode_chat":
        data["mode"] = "chat"
        data["history"] = []
        await query.edit_message_text(
            "Режим: **Чат** (без интернета)\n\n"
            "Gemini отвечает из своих знаний. Быстрее, но без актуальной информации.\n\n"
            "Пишите сообщение:",
            reply_markup=main_keyboard("chat"),
            parse_mode="Markdown",
        )

    elif action == "mode_search":
        data["mode"] = "search"
        data["history"] = []
        await query.edit_message_text(
            "Режим: **Чат + Интернет** (Google Search)\n\n"
            "Gemini ищет актуальную информацию в Google перед ответом.\n"
            "Идеально для проверки фактов, цен, новостей.\n\n"
            "Пишите сообщение:",
            reply_markup=main_keyboard("search"),
            parse_mode="Markdown",
        )

    elif action == "clear":
        data["history"] = []
        mode_name = "Чат" if data["mode"] == "chat" else "Чат + Интернет"
        await query.edit_message_text(
            f"История очищена. Режим: **{mode_name}**\n\nПишите сообщение:",
            reply_markup=main_keyboard(data["mode"]),
            parse_mode="Markdown",
        )

    elif action == "img_help":
        await query.edit_message_text(
            "**Генерация картинок**\n\n"
            "Отправьте команду:\n"
            "`/img ваше описание`\n\n"
            "Примеры:\n"
            "- `/img обложка для статьи про стиральные машины, мужчина держит ТЭН, рядом Bosch и Candy`\n"
            "- `/img красивый закат над морем в стиле масляной живописи`\n"
            "- `/img логотип для канала про технику, минималистичный, синий`\n\n"
            "Генерация бесплатная (Gemini Flash Image).",
            parse_mode="Markdown",
        )


# ============================================================
# Генерация изображений (Gemini Flash Image - бесплатно)
# ============================================================

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text(
            "Укажите описание после команды:\n"
            "`/img обложка для статьи про стиральные машины`",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text("Генерирую изображение... (10-30 сек)")

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Ищем изображение в ответе
        image_sent = False
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                await msg.delete()
                await update.message.reply_photo(
                    photo=io.BytesIO(image_data),
                    caption=f"Промпт: {prompt[:200]}",
                )
                image_sent = True
                break

        if not image_sent:
            # Модель ответила текстом вместо картинки
            text_response = response.text if response.text else "Не удалось сгенерировать изображение. Попробуйте другое описание."
            await msg.edit_text(f"Gemini ответил текстом:\n\n{text_response[:1000]}")

    except Exception as e:
        logger.error(f"Image generation error: {e}")
        await msg.edit_text(f"Ошибка генерации: {str(e)[:500]}\n\nПопробуйте другое описание.")


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
    data["history"].append({"role": "user", "parts": [{"text": user_message}]})
    if len(data["history"]) > MAX_HISTORY:
        data["history"] = data["history"][-MAX_HISTORY:]

    await update.message.chat.send_action("typing")

    try:
        if data["mode"] == "search":
            reply = await chat_with_search(data["history"])
        else:
            reply = await chat_simple(data["history"])

        data["history"].append({"role": "model", "parts": [{"text": reply}]})

        # Пробуем Markdown, если ошибка - без него
        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Chat error: {e}")
        await update.message.reply_text(f"Ошибка: {str(e)[:500]}")


# ============================================================
# Чат без интернета
# ============================================================

async def chat_simple(history: List[dict]) -> str:
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction="Ты полезный ассистент. Отвечай на русском, если пользователь пишет на русском. Будь кратким и по делу.",
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )
    return response.text


# ============================================================
# Чат с поиском в интернете (Google Search Grounding)
# ============================================================

async def chat_with_search(history: List[dict]) -> str:
    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction="Ты полезный ассистент. Отвечай на русском. Используй Google Search для проверки актуальной информации. Будь кратким и по делу.",
            tools=[google_search_tool],
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )
    return response.text


# ============================================================
# Запуск
# ============================================================

def main():
    if not TELEGRAM_TOKEN:
        print("ОШИБКА: Не задан TELEGRAM_TOKEN!")
        print("Установите: export TELEGRAM_TOKEN='ваш_токен'")
        return

    if not GOOGLE_AI_API_KEY:
        print("ОШИБКА: Не задан GOOGLE_AI_API_KEY!")
        print("Установите: export GOOGLE_AI_API_KEY='ваш_ключ'")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("img", generate_image))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен! Ожидаю сообщения...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
