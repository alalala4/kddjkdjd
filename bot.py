"""
РЕЙТ AI Bot - Telegram бот с OpenAI (GPT-4o + Web Search + DALL-E 3)
Текстовый чат С ПОИСКОМ В ИНТЕРНЕТЕ + генерация изображений.
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

# ============================================================
# НАСТРОЙКИ
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Модели
CHAT_MODEL = "gpt-4o-mini"
IMAGE_MODEL = "dall-e-3"

MAX_HISTORY = 10

# ============================================================
# Инициализация
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

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
        [InlineKeyboardButton("🖼 Сгенерировать картинку", callback_data="img_help")],
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
        "Привет! Я бот с GPT-4o + поиск в интернете + DALL-E 3.\n\n"
        "Что умею:\n"
        "- Отвечать на вопросы с актуальной инфой из интернета (2026!)\n"
        "- Генерировать картинки по описанию\n\n"
        "Как пользоваться:\n"
        "- Просто пишите текст - отвечу (с поиском в сети)\n"
        "- /img описание - сгенерирую картинку\n\n"
        "Кнопки ниже:",
        reply_markup=main_keyboard(),
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
        )

    elif action == "img_help":
        await query.edit_message_text(
            "Генерация картинок (DALL-E 3)\n\n"
            "Отправьте команду:\n"
            "/img ваше описание\n\n"
            "Примеры:\n"
            "- /img обложка для статьи про стиральные машины, мужчина держит ТЭН, рядом Bosch и Candy\n"
            "- /img YouTube превью, шокированный мужчина, рядом два холодильника с ценниками",
            reply_markup=main_keyboard(),
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
            "/img обложка для статьи про стиральные машины"
        )
        return

    msg = await update.message.reply_text("Генерирую изображение... (15-30 сек)")

    try:
        response = await openai_client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size="1792x1024",
            quality="hd",
            n=1,
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt or ""

        caption = f"Промпт: {prompt[:200]}"
        if revised_prompt:
            caption += f"\n\nDALL-E: {revised_prompt[:300]}"

        await msg.delete()
        await update.message.reply_photo(photo=image_url, caption=caption[:1024])

    except Exception as e:
        logger.error(f"DALL-E error: {e}")
        await msg.edit_text(f"Ошибка генерации: {str(e)[:500]}")


# ============================================================
# Обработка текстовых сообщений (с поиском в интернете!)
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
        # Используем responses API с web_search tool для актуальной информации
        response = await openai_client.responses.create(
            model=CHAT_MODEL,
            instructions="Ты полезный ассистент. Отвечай на русском, если пользователь пишет на русском. Будь кратким и по делу. ВСЕГДА ищи в интернете актуальную информацию перед ответом.",
            input=user_message,
            tools=[{"type": "web_search_preview"}],
        )

        reply = response.output_text
        data["history"].append({"role": "assistant", "content": reply[:2000]})

        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        # Если web_search не поддерживается - откатимся на обычный chat
        try:
            messages = [
                {"role": "system", "content": "Ты полезный ассистент. Отвечай на русском. Будь кратким."}
            ] + data["history"]

            response = await openai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
            )

            reply = response.choices[0].message.content
            data["history"].append({"role": "assistant", "content": reply[:2000]})

            try:
                await update.message.reply_text(reply, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(reply)

        except Exception as e2:
            await update.message.reply_text(f"Ошибка: {str(e2)[:500]}")


# ============================================================
# Запуск
# ============================================================

def main():
    if not TELEGRAM_TOKEN:
        print("ОШИБКА: Не задан TELEGRAM_TOKEN!")
        return

    if not OPENAI_API_KEY:
        print("ОШИБКА: Не задан OPENAI_API_KEY!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("img", generate_image))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен! GPT-4o + Web Search + DALL-E 3")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
