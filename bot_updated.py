import os
import asyncio
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    JobQueue,
)

from real_apis import analyze_matches
from logger import log_bet

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не установлен в переменных окружения!")
if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ TELEGRAM_CHAT_ID не установлен в переменных окружения!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда"""
    keyboard = [
        [InlineKeyboardButton("🔥 Топ ставки сегодня", callback_data="top_bets")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Добро пожаловать в Football Betting Bot!\n\n"
        "Нажми кнопку для получения топ-ставок сегодня.",
        reply_markup=reply_markup
    )


async def top_bets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Топ ставки'"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text("⏳ Идёт анализ матчей, подождите...")
        
        # Запуск анализа с расширенным диапазоном коэффициентов
        loop = asyncio.get_event_loop()
        # Используем расширенные параметры: 1.2-2.5 вместо 1.3-1.9
        bets = await loop.run_in_executor(
            None, 
            analyze_matches,
            0.005,  # min_value (минимальное value)
            1.2,    # odd_min (минимальный коэффициент)
            2.5     # odd_max (максимальный коэффициент)
        )
        
        if not bets:
            await query.edit_message_text(
                "❌ Подходящих value-ставок не найдено.\n\n"
                "Возможные причины:\n"
                "• API недоступен или нет матчей\n"
                "• Off-season (сезон не начался)\n"
                "• Нет достаточного volume на рынке\n\n"
                "💡 Совет: попробуй позже, когда начнутся матчи"
            )
            logger.warning("Не найдено ставок для вывода")
            return
        
        # Форматирование результатов
        text = "🔥 *Топ ставки сегодня:*\n\n"
        
        for i, (value, league, match, market, odd) in enumerate(bets, 1):
            # Логируем каждую ставку
            log_bet(match, market, value, odd, value)
            
            text += (
                f"*{i}. {league}*\n"
                f"  🏟 {match}\n"
                f"  📊 {market}\n"
                f"  💰 Коэффициент: {odd:.2f}\n"
                f"  ✅ Value: +{value:.4f}\n\n"
            )
        
        text += (
            "_Value = (Вероятность × Коэффициент) - 1_\n"
            "_Положительное значение = математическое преимущество_\n\n"
            f"📈 Всего найдено: {len(bets)} ставок"
        )
        
        await query.edit_message_text(text, parse_mode="Markdown")
        logger.info(f"✅ Найдено {len(bets)} ставок и отправлено пользователю")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при анализе ставок: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Ошибка при анализе:\n{str(e)}\n\n"
            "Попробуйте позже."
        )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    try:
        text = "📊 *Статистика:*\n\n"
        text += "_Функция в разработке_"
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Ошибка при показе статистики: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def send_daily_bets(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет топ-ставки каждый день в 12:00 UTC"""
    try:
        loop = asyncio.get_event_loop()
        bets = await loop.run_in_executor(
            None,
            analyze_matches,
            0.005,  # min_value
            1.2,    # odd_min
            2.5     # odd_max
        )
        
        if not bets:
            logger.warning("⚠️ Нет ставок для отправки в расписании")
            return
        
        text = "🔔 *Автоматический отчёт по ставкам:*\n\n"
        
        for i, (value, league, match, market, odd) in enumerate(bets[:5], 1):
            text += (
                f"{i}. {league} | {match}\n"
                f"   {market} @ {odd:.2f} | Value: {value:.4f}\n\n"
            )
        
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown"
        )
        logger.info("✅ Отправлен ежедневный отчёт")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке ежедневного отчёта: {e}", exc_info=True)


def main():
    """Запуск бота"""
    try:
        logger.info("🚀 Запуск Football Betting Bot...")
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Обработчики команд
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(top_bets_callback, pattern="top_bets"))
        app.add_handler(CallbackQueryHandler(stats_callback, pattern="stats"))
        
        # Расписание ежедневной отправки (опционально)
        # job_queue = app.job_queue
        # job_queue.run_daily(send_daily_bets, time=datetime.time(hour=12, minute=0))
        
        logger.info("✅ Бот запущен и готов к работе")
        logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
