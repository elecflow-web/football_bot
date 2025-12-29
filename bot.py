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

from real_apis_pro import analyze_matches
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
    raise ValueError("❌ TELEGRAM_TOKEN не установлен!")
if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ TELEGRAM_CHAT_ID не установлен!")

# Сохраняем избранные матчи
FAVORITES = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда"""
    keyboard = [
        [InlineKeyboardButton("🔥 Топ ставки (КАЧЕСТВО)", callback_data="top_bets")],
        [InlineKeyboardButton("⭐ Мои ставки", callback_data="favorites")],
        [InlineKeyboardButton("📊 Аналитика", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *ПРОФЕССИОНАЛЬНЫЙ АНАЛИЗ СТАВОК*\n\n"
        "Мощный анализ коэффициентов как букмекер\n"
        "Только HIGH VALUE ставки (value > 0.025)\n\n"
        "Нажми кнопку для начала:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def top_bets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Топ ставки'"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text("⏳ МОЩНЫЙ АНАЛИЗ в процессе...\n(обработка 12 лиг, 150+ матчей, 3 типа рынков)")
        
        # Запуск анализа
        loop = asyncio.get_event_loop()
        bets = await loop.run_in_executor(
            None, 
            analyze_matches,
            0.025,  # min_value - ВЫСОКИЙ порог качества
            1.3,    # odd_min
            3.5     # odd_max - расширенный диапазон
        )
        
        if not bets:
            await query.edit_message_text(
                "⚠️ Нет матчей соответствующих критериям HIGH VALUE\n\n"
                "Причины:\n"
                "• Все коэффициенты переоценены букмекерами\n"
                "• Очень высокие стандарты качества (value > 0.025)\n"
                "• Сезон в процессе - матчей может быть мало\n\n"
                "Совет: попробуй позже"
            )
            logger.warning("⚠️ Нет HIGH VALUE ставок")
            return
        
        # Форматирование результатов - РАСШИРЕННЫЙ ФОРМАТ
        text = "🔥 *ТОПОВЫЕ СТАВКИ (ТОЛЬКО КАЧЕСТВО):*\n"
        text += f"_Проанализировано: 150+ матчей | Найдено: {len(bets)} VALUE бетов_\n\n"
        
        for i, bet_data in enumerate(bets[:15], 1):
            # Распаковываем данные
            value, league, match, market, odd, time_str, match_id, details = bet_data
            
            # Извлекаем детали
            true_prob = details.get("true_prob", 0)
            implied_prob = details.get("implied_prob", 0)
            stats = details.get("stats", {})
            roi = details.get("roi", 0)
            market_type = details.get("market_type", "")
            
            # Логируем ставку
            log_bet(match, market, value, odd, value)
            
            # Сохраняем для избранного
            bet_key = f"{match_id}_{market}_{odd:.2f}"
            FAVORITES[bet_key] = {
                "league": league,
                "match": match,
                "market": market,
                "odd": odd,
                "value": value,
                "time": time_str,
                "true_prob": true_prob,
                "implied_prob": implied_prob,
                "roi": roi,
                "bookmakers_count": stats.get("count", 0),
                "best_price": stats.get("best", 0)
            }
            
            # Красивый вывод
            indicator = "🟢" if value > 0.05 else "🟡"
            
            text += (
                f"{indicator} *{i}. {league}*\n"
                f"  🏟 {match}\n"
                f"  🕐 {time_str}\n"
                f"  📊 {market}\n"
                f"  💰 Коэффициент: `{odd:.2f}`\n"
                f"  ✅ *VALUE: +{value:.4f}* | ROI: {roi:.1f}%\n"
                f"  🎯 Вероятность: {true_prob*100:.1f}% | Котировка: {implied_prob*100:.1f}%\n"
                f"  🏛 Букмекеров: {stats.get('count', 0)} | Спред: {stats.get('spread', 0):.3f}\n"
                f"  💡 Лучшая цена: `{stats.get('best', 0):.2f}`\n\n"
            )
        
        text += (
            "_\n📐 *КАК ЭТО РАБОТАЕТ:*\n"
            "• Value = (Вероятность × Коэффициент) - 1\n"
            "• Value > 0.025 = КАЧЕСТВЕННАЯ ставка\n"
            "• ROI = Ожидаемая доходность в %\n"
            "• Вероятность рассчитана на основе коэффициентов букмекеров\n"
            "• Спред = разница между лучшей и худшей ценой\n\n"
            f"📈 *ИТОГО: {len(bets)} ставок прошли фильтр качества*_"
        )
        
        await query.edit_message_text(text, parse_mode="Markdown")
        logger.info(f"✅ Отправлено {len(bets)} QUALITY ставок")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при анализе: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Ошибка:\n`{str(e)}`\n\n"
            "Попробуй позже"
        )


async def favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать избранные матчи"""
    query = update.callback_query
    await query.answer()
    
    try:
        if not FAVORITES:
            await query.edit_message_text("⭐ Ты ещё не добавил ставки в избранное")
            return
        
        text = "⭐ *МОИ СТАВКИ:*\n\n"
        
        for i, (key, bet) in enumerate(list(FAVORITES.items())[:10], 1):
            text += (
                f"*{i}. {bet['league']}*\n"
                f"  {bet['match']}\n"
                f"  {bet['market']} @ {bet['odd']:.2f}\n"
                f"  💰 VALUE: +{bet['value']:.4f} | ROI: {bet['roi']:.1f}%\n"
                f"  🕐 {bet['time']}\n\n"
            )
        
        text += f"_Всего отслеживаемых: {len(FAVORITES)}_"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать аналитику"""
    query = update.callback_query
    await query.answer()
    
    try:
        text = (
            "📊 *АНАЛИТИКА И МЕТОДОЛОГИЯ:*\n\n"
            "*🏆 ЛИГИ (12):*\n"
            "  🏴󠁧󠁢󠁥󠁮󠁧󠁿 Английская Премьер-лига\n"
            "  🇪🇸 Испанская Ла Лига\n"
            "  🇩🇪 Немецкая Бундеслига\n"
            "  🇮🇹 Итальянская Серия А\n"
            "  🇫🇷 Французская Лига 1\n"
            "  🇵🇹 Португальская Примейра Лига\n"
            "  🇳🇱 Голландская Эредивизи\n"
            "  🏆 Лига чемпионов\n"
            "  🇺🇸 MLS (США)\n"
            "  🇦🇷 Чемпионшип\n"
            "  🇮🇹 Серия Б\n"
            "  🇩🇪 Бундеслига 2\n\n"
            "*💼 РЫНКИ (3+):*\n"
            "  • H2H (1X2) - Ставки на исход\n"
            "  • TOTALS - Over/Under\n"
            "  • SPREADS - Азиатский гандикап\n\n"
            "*🔬 ГЛУБИНА АНАЛИЗА:*\n"
            "  ✅ 150+ матчей в реальном времени\n"
            "  ✅ 8-15 букмекеров на каждый рынок\n"
            "  ✅ Сравнение коэффициентов между букмекерами\n"
            "  ✅ Расчёт истинной вероятности\n"
            "  ✅ Анализ спредов (разница цен)\n"
            "  ✅ ROI вычисление\n\n"
            "*⚙️ ФИЛЬТРЫ КАЧЕСТВА:*\n"
            "  • Минимум Value: *0.025* (HIGH QUALITY)\n"
            "  • Диапазон коэффициентов: 1.3 - 3.5\n"
            "  • Только уникальные ставки (БЕЗ дубликатов)\n"
            "  • Проверка по 8+ букмекерам\n\n"
            "*🎯 КАК РАБОТАЕТ:*\n"
            "1️⃣ Система как профессиональный букмекер\n"
            "2️⃣ Анализирует движение коэффициентов\n"
            "3️⃣ Ищет переоценённые исходы\n"
            "4️⃣ Предлагает только VALUE беты\n"
            "5️⃣ Гарантирует NO дубликатов"
        )
        
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


def main():
    """Запуск бота"""
    try:
        logger.info("🚀 ЗАПУСК ПРОФЕССИОНАЛЬНОГО BETTING БОТА...")
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(top_bets_callback, pattern="top_bets"))
        app.add_handler(CallbackQueryHandler(favorites_callback, pattern="favorites"))
        app.add_handler(CallbackQueryHandler(stats_callback, pattern="stats"))
        
        logger.info("✅ Бот готов!")
        logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
