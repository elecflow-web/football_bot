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
    MessageHandler,
    filters,
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
    raise ValueError("❌ TELEGRAM_TOKEN не установлен!")
if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ TELEGRAM_CHAT_ID не установлен!")

# Сохраняем избранные матчи
FAVORITES = {}


def get_main_keyboard():
    """Возвращает главную клавиатуру"""
    keyboard = [
        [InlineKeyboardButton("🔥 Топ ставки (КАЧЕСТВО)", callback_data="top_bets")],
        [InlineKeyboardButton("⭐ Мои ставки", callback_data="favorites")],
        [InlineKeyboardButton("📊 Аналитика", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


def extract_total_value(market: str) -> str:
    """Извлекает значение тотала из строки"""
    import re
    match = re.search(r'(Over|Under)\s*(\d+\.?\d*)', market, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return market


def format_market_with_team(match_str: str, market: str) -> str:
    """Форматирует рынок с указанием команды для фор"""
    import re
    
    # Извлекаем домашнюю команду
    home_team = match_str.split(" vs ")[0].strip() if " vs " in match_str else "?"
    
    # Обработка фор
    if "Фора" in market:
        fora_match = re.search(r'Фора\s*([-+]?\d+\.?\d*)', market)
        if fora_match:
            fora_value = float(fora_match.group(1))
            if fora_value < 0:
                return f"📊 {home_team} {market}"
            else:
                away_team = match_str.split(" vs ")[1].strip() if " vs " in match_str else "?"
                return f"📊 {away_team} {market}"
    
    # Over/Under
    if "Over" in market or "Under" in market:
        total_value = extract_total_value(market)
        return f"📊 {total_value}"
    
    return f"📊 {market}"


def format_bet_description(match_str: str, market: str) -> str:
    """Создаёт полное описание ставки для выбора"""
    import re
    
    home_team = match_str.split(" vs ")[0].strip() if " vs " in match_str else "?"
    away_team = match_str.split(" vs ")[1].strip() if " vs " in match_str else "?"
    
    # Обработка фор
    if "Фора" in market:
        fora_match = re.search(r'Фора\s*([-+]?\d+\.?\d*)', market)
        if fora_match:
            fora_value = float(fora_match.group(1))
            if fora_value < 0:
                return f"**СТАВКА:** {home_team} {market}\n   (Домашняя команда должна выиграть с перевесом)"
            else:
                return f"**СТАВКА:** {away_team} {market}\n   (Гостевая команда с форой)"
    
    # Двойные шансы
    if "1X" in market and "12" not in market:
        return f"**СТАВКА:** {home_team} или Ничья\n   ({market})"
    elif "12" in market and "1X" not in market:
        return f"**СТАВКА:** {home_team} или {away_team} (НЕ-ничья)\n   ({market})"
    elif "X2" in market:
        return f"**СТАВКА:** Ничья или {away_team}\n   ({market})"
    
    # Over/Under
    if "Over" in market:
        total = extract_total_value(market)
        return f"**СТАВКА:** В матче будет 3+ голов\n   ({total})"
    elif "Under" in market:
        total = extract_total_value(market)
        return f"**СТАВКА:** В матче будет 0-2 гола\n   ({total})"
    
    # Обе забьют
    if "Обе" in market or "Both" in market.lower():
        return f"**СТАВКА:** {home_team} И {away_team} обе забьют\n   (Обе команды в сетке)"
    
    # Дополнительные
    if "Чистый лист" in market:
        return f"**СТАВКА:** {home_team} сыграет без пропущенных голов"
    elif "Углы" in market or "Corner" in market.lower():
        return f"**СТАВКА:** На количество угловых\n   (по всему матчу)"
    
    return f"**СТАВКА:** {market}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда - главное меню"""
    keyboard = get_main_keyboard()
    
    await update.message.reply_text(
        "🤖 *ПРОФЕССИОНАЛЬНЫЙ АНАЛИЗ СТАВОК*\n\n"
        "Мощный анализ коэффициентов как букмекер\n"
        "Только HIGH VALUE ставки (вероятность ≥ 60%)\n\n"
        "Выбери действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def top_bets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Топ ставки'"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text("⏳ МОЩНЫЙ АНАЛИЗ в процессе...\n(обработка 12 лиг, 150+ матчей, 13 рынков)")
        
        # Запуск анализа
        loop = asyncio.get_event_loop()
        bets = await loop.run_in_executor(
            None, 
            analyze_matches,
            0.025,  # min_value
            1.3,    # odd_min
            3.5     # odd_max
        )
        
        if not bets:
            keyboard = get_main_keyboard()
            await query.edit_message_text(
                "⚠️ Нет матчей соответствующих критериям HIGH VALUE\n\n"
                "Причины:\n"
                "• Все коэффициенты переоценены букмекерами\n"
                "• Очень высокие стандарты качества (value > 0.025)\n"
                "• Вероятность должна быть ≥ 60%\n\n"
                "Совет: попробуй позже",
                reply_markup=keyboard
            )
            logger.warning("⚠️ Нет HIGH VALUE ставок")
            return
        
        # Форматирование результатов
        text = "🔥 *ТОПОВЫЕ СТАВКИ (ТОЛЬКО КАЧЕСТВО):*\n"
        text += f"_Проанализировано: 150+ матчей | Найдено: {len(bets)} VALUE бетов | Вероятность ≥ 60%_\n\n"
        
        for i, bet_data in enumerate(bets[:12], 1):
            value, league, match, market, odd, time_str, match_id, details = bet_data
            
            true_prob = details.get("true_prob", 0)
            implied_prob = details.get("implied_prob", 0)
            stats = details.get("stats", {})
            roi = details.get("roi", 0)
            
            log_bet(match, market, value, odd, value)
            
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
            
            indicator = "🟢" if value > 0.05 else "🟡"
            market_display = format_market_with_team(match, market)
            bet_description = format_bet_description(match, market)
            
            text += (
                f"{indicator} *{i}. {league}*\n"
                f"  🏟 {match}\n"
                f"  🕐 {time_str}\n"
                f"{bet_description}\n"
                f"  💰 Коэффициент: `{odd:.2f}`\n"
                f"  ✅ *VALUE: +{value:.4f}* | ROI: {roi:.1f}%\n"
                f"  🎯 Вероятность: {true_prob*100:.1f}% | Котировка: {implied_prob*100:.1f}%\n"
                f"  🏛 Букмекеров: {stats.get('count', 0)} | Спред: {stats.get('spread', 0):.3f}\n"
                f"  💡 Лучшая цена: `{stats.get('best', 0):.2f}`\n\n"
            )
        
        text += (
            "_\n📚 *ВИДЫ СТАВОК:*\n"
            "🟢 *Over/Under* - на общее количество голов\n"
            "   • Over 2.5 = будет 3+ голов в матче ⚽⚽⚽\n"
            "   • Under 2.5 = будет 0, 1 или 2 гола ⚽⚽\n\n"
            "🟢 *Фора (Гандикап)* - команда играет с минусом\n"
            "   • Фора -1.5 = команда должна выиграть на 2+ гола\n"
            "   • Фора +1.5 = команде даётся виртуальное преимущество\n\n"
            "🟢 *Двойные шансы* - комбинированные исходы\n"
            "   • 1X = дома или ничья\n"
            "   • 12 = не-ничья (дома или гости)\n"
            "   • X2 = ничья или гости\n\n"
            "🟢 *П1/П2/X* - исход матча\n"
            "   • П1 = победа домашней команды\n"
            "   • П2 = победа гостевой команды\n"
            "   • X = ничья\n\n"
            "📐 *ФОРМУЛА VALUE:*\n"
            "• Value = (Вероятность × Коэффициент) - 1\n"
            "• Value > 0.025 = ВЫГОДНАЯ ставка\n"
            "• ROI = ожидаемая доходность в %\n"
            "• Вероятность ≥ 60% = ВЫСОКАЯ УВЕРЕННОСТЬ\n\n"
            f"📈 *ИТОГО: {len(bets)} ставок прошли фильтр качества*_"
        )
        
        keyboard = get_main_keyboard()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info(f"✅ Отправлено {len(bets)} QUALITY ставок")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при анализе: {e}", exc_info=True)
        keyboard = get_main_keyboard()
        await query.edit_message_text(
            f"❌ Ошибка:\n`{str(e)}`\n\n"
            "Попробуй позже",
            reply_markup=keyboard
        )


async def favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать избранные матчи"""
    query = update.callback_query
    await query.answer()
    
    try:
        if not FAVORITES:
            keyboard = get_main_keyboard()
            await query.edit_message_text(
                "⭐ Ты ещё не добавил ставки в избранное",
                reply_markup=keyboard
            )
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
        
        keyboard = get_main_keyboard()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        keyboard = get_main_keyboard()
        await query.edit_message_text(f"❌ Ошибка: {str(e)}", reply_markup=keyboard)


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
            "  🏴󠁧󠁢󠁥󠁮󠁧󠁿 Чемпионшип\n"
            "  🇮🇹 Серия Б\n"
            "  🇩🇪 Бундеслига 2\n\n"
            "*💼 РЫНКИ (13):*\n"
            "  • H2H (1X2) - исход матча\n"
            "  • TOTALS - Over/Under голов\n"
            "  • SPREADS - Азиатский гандикап (Фора)\n"
            "  • DOUBLE_CHANCE - двойные шансы\n"
            "  • YELLOW_CARDS - жёлтые карточки\n"
            "  • BOTH_SCORE - обе забьют\n"
            "  • CORNERS - угловые\n"
            "  • CLEAN_SHEET - чистый лист\n"
            "  + ещё 5 рынков\n\n"
            "*🔬 ГЛУБИНА АНАЛИЗА:*\n"
            "  ✅ 150+ матчей в реальном времени\n"
            "  ✅ 15 букмекеров на каждый рынок\n"
            "  ✅ Сравнение коэффициентов между букмекерами\n"
            "  ✅ Расчёт истинной вероятности\n"
            "  ✅ Анализ спредов (разница цен)\n"
            "  ✅ ROI вычисление\n\n"
            "*⚙️ ФИЛЬТРЫ КАЧЕСТВА:*\n"
            "  • Минимум Value: *0.025*\n"
            "  • Диапазон коэффициентов: 1.3 - 3.5\n"
            "  • Только уникальные ставки (БЕЗ дубликатов)\n"
            "  • Вероятность ≥ *60%* (высокая уверенность)\n"
            "  • Проверка по 15 букмекерам\n\n"
            "*🎯 КАК РАБОТАЕТ:*\n"
            "1️⃣ Система как профессиональный букмекер\n"
            "2️⃣ Анализирует движение коэффициентов\n"
            "3️⃣ Ищет переоценённые исходы\n"
            "4️⃣ Предлагает только VALUE беты\n"
            "5️⃣ Гарантирует NO дубликатов"
        )
        
        keyboard = get_main_keyboard()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        keyboard = get_main_keyboard()
        await query.edit_message_text(f"❌ Ошибка: {str(e)}", reply_markup=keyboard)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений - возврат в меню"""
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        "👋 Привет! Используй кнопки ниже для навигации:",
        reply_markup=keyboard
    )


def main():
    """Запуск бота"""
    try:
        logger.info("🚀 ЗАПУСК ПРОФЕССИОНАЛЬНОГО BETTING БОТА...")
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Обработчики команд
        app.add_handler(CommandHandler("start", start))
        
        # Обработчики кнопок
        app.add_handler(CallbackQueryHandler(top_bets_callback, pattern="top_bets"))
        app.add_handler(CallbackQueryHandler(favorites_callback, pattern="favorites"))
        app.add_handler(CallbackQueryHandler(stats_callback, pattern="stats"))
        
        # Обработчик текстовых сообщений (для возврата в меню)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        logger.info("✅ Бот готов!")
        logger.info(f"Chat ID: {TELEGRAM_CHAT_ID}")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
