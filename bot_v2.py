import os
import asyncio
import logging
from datetime import datetime
import json

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

# Сохраняем избранные матчи
FAVORITES = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда"""
    keyboard = [
        [InlineKeyboardButton("🔥 Топ ставки сегодня", callback_data="top_bets")],
        [InlineKeyboardButton("⭐ Избранные матчи", callback_data="favorites")],
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
        bets = await loop.run_in_executor(
            None, 
            analyze_matches,
            0.005,
            1.2,
            2.5
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
        
        for i, bet_data in enumerate(bets[:10], 1):
            # Распаковываем данные
            value, league, match, market, odd, time_str, match_id, details = bet_data
            
            # Анализ для отображения
            true_prob = details.get("true_prob", 0)
            implied_prob = details.get("implied_prob", 0)
            analysis = details.get("analysis", {})
            market_type = details.get("market_type", "")
            
            # Логируем ставку
            log_bet(match, market, value, odd, value)
            
            # Сохраняем для избранного
            bet_key = f"{match_id}_{market}"
            FAVORITES[bet_key] = {
                "league": league,
                "match": match,
                "market": market,
                "odd": odd,
                "value": value,
                "time": time_str,
                "true_prob": true_prob,
                "implied_prob": implied_prob,
                "bookmakers_count": analysis.get("count", 0)
            }
            
            text += (
                f"*{i}. {league}*\n"
                f"  🏟 {match}\n"
                f"  🕐 {time_str}\n"
                f"  📊 {market}\n"
                f"  💰 Коэффициент: {odd:.2f}\n"
                f"  📈 Value: +{value:.4f}\n"
                f"  🎯 Букмекеров в сравнении: {analysis.get('count', 0)}\n\n"
            )
        
        text += (
            "_📐 Анализ:_\n"
            "_Value = (Вероятность × Коэффициент) - 1_\n"
            "_Положительное значение = математическое преимущество_\n\n"
            f"📈 Всего найдено: {len(bets)} ставок\n"
            f"🔍 Проанализировано: 12 лиг"
        )
        
        await query.edit_message_text(text, parse_mode="Markdown")
        logger.info(f"✅ Найдено {len(bets)} ставок и отправлено пользователю")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при анализе ставок: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Ошибка при анализе:\n{str(e)}\n\n"
            "Попробуйте позже."
        )


async def favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать избранные матчи"""
    query = update.callback_query
    await query.answer()
    
    try:
        if not FAVORITES:
            await query.edit_message_text("⭐ У вас пока нет избранных матчей")
            return
        
        text = "⭐ *Избранные матчи:*\n\n"
        
        for i, (key, bet) in enumerate(list(FAVORITES.items())[:5], 1):
            text += (
                f"*{i}. {bet['league']}*\n"
                f"  {bet['match']}\n"
                f"  {bet['market']} @ {bet['odd']:.2f}\n"
                f"  Value: +{bet['value']:.4f}\n\n"
            )
        
        text += (
            f"_Всего отслеживаемых матчей: {len(FAVORITES)}_"
        )
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Ошибка при показе избранного: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    try:
        text = (
            "📊 *Статистика анализа:*\n\n"
            "📍 *Лиги в анализе:*\n"
            "  ✅ Английская Премьер-лига\n"
            "  ✅ Испанская Ла Лига\n"
            "  ✅ Немецкая Бундеслига\n"
            "  ✅ Итальянская Серия А\n"
            "  ✅ Французская Лига 1\n"
            "  ✅ Португальская Примейра Лига\n"
            "  ✅ Голландская Эредивизи\n"
            "  ✅ Лига чемпионов\n"
            "  ✅ MLS (США)\n"
            "  ✅ Английская Чемпионшип\n"
            "  ✅ Итальянская Серия Б\n"
            "  ✅ Немецкая Бундеслига 2\n\n"
            "📊 *Рынки анализа:*\n"
            "  • H2H (Ставки на победу 1X2)\n"
            "  • Totals (Over/Under)\n"
            "  • Spreads (Азиатский гандикап)\n\n"
            "📈 *Глубина анализа:*\n"
            "  • 8+ букмекеров на каждый матч\n"
            "  • 3 типа рынков\n"
            "  • Сравнение коэффициентов\n"
            "  • Расчёт математического преимущества (value)\n\n"
            "⚙️ *Параметры поиска:*\n"
            "  • Диапазон коэффициентов: 1.2 - 2.5\n"
            "  • Минимальное value: 0.005\n"
            "  • Обновление: каждый запрос"
        )
        
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
            0.005,
            1.2,
            2.5
        )
        
        if not bets:
            logger.warning("⚠️ Нет ставок для отправки в расписании")
            return
        
        text = "🔔 *Автоматический отчёт по ставкам:*\n\n"
        
        for i, bet_data in enumerate(bets[:5], 1):
            value, league, match, market, odd, time_str, match_id, details = bet_data
            text += (
                f"{i}. {league} | {match}\n"
                f"   {time_str} | {market} @ {odd:.2f}\n"
                f"   Value: +{value:.4f}\n\n"
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
        logger.info("🚀 Запуск Football Betting Bot v2...")
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Обработчики команд
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(top_bets_callback, pattern="top_bets"))
        app.add_handler(CallbackQueryHandler(favorites_callback, pattern="favorites"))
        app.add_handler(CallbackQueryHandler(stats_callback, pattern="stats"))
        
        logger.info("✅ Бот запущен и готов к работе")
        logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
