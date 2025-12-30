import os
import asyncio
import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from deep_analysis_v2 import find_value_bets
from logger import log_bet

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не установлен!")
if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ TELEGRAM_CHAT_ID не установлен!")

CURRENT_BETS = []


def get_main_reply_keyboard():
    keyboard = [
        [KeyboardButton("🔥 На кого ставить?"), KeyboardButton("📊 Как работает")],
        [KeyboardButton("ℹ️ Информация"), KeyboardButton("⚙️ Настройки")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def format_bet_card(bet: dict, index: int) -> str:
    """Форматирует одну ставку с четкой командой и датой матча"""

    match = bet['match']
    league = bet['league']
    bet_team = bet['bet_team']
    bet_type = bet['bet_type']
    odds = bet['odds']
    probability = bet['probability']
    edge = bet['edge']
    confidence = bet['confidence']

    match_dt = bet.get('match_date')
    if match_dt:
        match_dt_str = match_dt.strftime("%d.%m.%Y %H:%M")
    else:
        match_dt_str = "Дата уточняется"

    confidence_emoji = "✅" if confidence == "HIGH" else "⚠️"

    text = (
        f"🟢 *{index}. {league}*\n"
        f"   {match}\n"
        f"   🕒 {match_dt_str}\n\n"
        f"   *📍 СТАВИМ НА: {bet_team}*\n"
        f"   ({bet_type})\n\n"
        f"   💰 Коэффициент: `{odds:.2f}`\n"
        f"   🎯 Вероятность: *{probability*100:.0f}%*\n"
        f"   ⚡ EDGE: *{edge*100:.1f}%*\n"
        f"   {confidence_emoji} Уверенность: *{confidence}*\n"
    )

    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = get_main_reply_keyboard()

    await update.message.reply_text(
        "🤖 *ПРОФЕССИОНАЛЬНЫЙ АНАЛИЗ СТАВОК*\n\n"
        "Глубокий анализ матчей на основе:\n"
        "✅ Статистики команд\n"
        "✅ Формы игроков\n"
        "✅ Травм и пропусков\n"
        "✅ История встреч\n"
        "✅ Мотивации\n\n"
        "Результат: 3-5 ставок с вероятностью >60%\n"
        "*И ЧЕТКО ВИДНО НА КАКУЮ КОМАНДУ СТАВИТЬ!*\n\n"
        "Выбери действие в меню снизу ⬇️",
        reply_markup=reply_keyboard,
        parse_mode="Markdown"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    reply_keyboard = get_main_reply_keyboard()

    if text == "🔥 На кого ставить?":
        try:
            await update.message.reply_text(
                "⏳ Анализирую букмекеры...\n"
                "(статистика, форма, травмы, мотивация, история встреч)"
            )

            loop = asyncio.get_event_loop()
            bets = await loop.run_in_executor(
                None,
                find_value_bets,
                1.3,
                1.9,
                0.60
            )

            if not bets:
                await update.message.reply_text(
                    "⚠️ Нет матчей с достаточной уверенностью\n\n"
                    "Сегодня не было ставок, соответствующих критериям",
                    reply_markup=reply_keyboard
                )
                return

            text_result = (
                f"🔥 *НА КОГО СТАВИТЬ? ГЛУБОКИЙ АНАЛИЗ*\n\n"
                f"Найдено ставок: *{len(bets)}*\n"
                f"Вероятность: ≥60%\n"
                f"Коэффициенты: 1.3 - 1.9\n\n"
                f"{'='*50}\n\n"
            )

            for i, bet in enumerate(bets, 1):
                text_result += format_bet_card(bet, i)
                text_result += "\n"
                log_bet(bet['match'], bet['bet_type'], bet['probability'],
                        bet['odds'], bet['edge'], 0, True, None)

            text_result += (
                f"{'='*50}\n\n"
                f"📋 *КАК МЫ РАССЧИТАЛИ:*\n"
                f"• Форма, Дома/Гости, Травмы, H2H, Мотивация\n"
                f"• EDGE = наше преимущество над букмекером"
            )

            await update.message.reply_text(
                text_result,
                parse_mode="Markdown",
                reply_markup=reply_keyboard
            )
            logger.info(f"✅ Анализ завершён: {len(bets)} ставок")

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Ошибка анализа",
                reply_markup=reply_keyboard
            )

    elif text == "📊 Как работает":
        text_help = (
            "📊 *КАК ЭТО РАБОТАЕТ:*\n\n"
            "*1️⃣ СБОР КОЭФФИЦИЕНТОВ*\n"
            "Анализируем 6 букмекеров (1.3-1.9)\n\n"
            "*2️⃣ АНАЛИЗ КОМАНД*\n"
            "📈 Форма | 🏟️ Дома/Гости | 🚑 Травмы | 🔄 H2H | 💪 Мотивация\n\n"
            "*3️⃣ РАСЧЁТ ВЕРОЯТНОСТИ*\n"
            "50% + коррекции = итоговая\n\n"
            "*4️⃣ ОПРЕДЕЛЯЕМ КОМАНДУ*\n"
            ">60% → П1 | 50-60% → 1X | <50% → П2\n\n"
            "*5️⃣ ПОИСК EDGE*\n"
            "Наша вероятность vs коэффициент\n\n"
            "✅ 3-5 ставок/день с EDGE +3-12%"
        )
        await update.message.reply_text(
            text_help,
            parse_mode="Markdown",
            reply_markup=reply_keyboard
        )

    elif text == "ℹ️ Информация":
        text_info = (
            "ℹ️ *ИНФОРМАЦИЯ О СИСТЕМЕ:*\n\n"
            "*🎯 ПРИНЦИП:*\n"
            "Профессиональный анализ, не угадайка\n\n"
            "*💼 РЕНТАБЕЛЬНОСТЬ:*\n"
            "5 ставок × +7% EDGE = +350 руб/день\n"
            "= +105,000 руб/год\n\n"
            "*✅ ПРЕИМУЩЕСТВА:*\n"
            "✓ Только 3-5 ставок\n"
            "✓ Вероятность >60%\n"
            "✓ EDGE +3-12%\n"
            "✓ Коэффициенты 1.3-1.9\n"
            "✓ Четко видно на кого ставить\n\n"
            "*⚠️ ВАЖНО:*\n"
            "Ставьте ответственно,\n"
            "только деньги которые можете потерять"
        )
        await update.message.reply_text(
            text_info,
            parse_mode="Markdown",
            reply_markup=reply_keyboard
        )

    elif text == "⚙️ Настройки":
        text_settings = (
            "⚙️ *НАСТРОЙКИ:*\n\n"
            "*Скоро будут доступны:*\n"
            "🔧 Выбор лиг\n"
            "🔧 Минимум вероятности\n"
            "🔧 Минимум EDGE\n"
            "🔧 Уведомления\n"
            "🔧 История ставок\n\n"
            "Обновления в скором времени!"
        )
        await update.message.reply_text(
            text_settings,
            parse_mode="Markdown",
            reply_markup=reply_keyboard
        )

    else:
        await update.message.reply_text(
            "👋 Используй кнопки в меню снизу ⬇️",
            reply_markup=reply_keyboard
        )


def main():
    try:
        logger.info("🚀 ЗАПУСК BETTING БОТА...")

        # Создаём custom Request с увеличенным таймаутом
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0,
        )

        # Создаём приложение с кастомным Request
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).request(request).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        logger.info("✅ Бот готов к работе!")
        logger.info("⏰ Таймауты установлены: 30 сек")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.critical(f"❌ Ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
