import os
import asyncio
import logging
from datetime import datetime
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from deep_analysis_v2 import find_value_bets
from logger import log_bet

# Логирование
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

# Глобальные переменные
CURRENT_BETS = []


def get_main_reply_keyboard():
    """Постоянное меню в нижней части (ReplyKeyboardMarkup)"""
    keyboard = [
        [KeyboardButton("🔥 На кого ставить?"), KeyboardButton("📊 Как работает")],
        [KeyboardButton("ℹ️ Информация"), KeyboardButton("⚙️ Настройки")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_back_keyboard():
    """Кнопка "Назад в меню" для inline меню"""
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def format_bet_card(bet: dict, index: int) -> str:
    """Форматирует одну ставку с четкой командой"""
    
    match = bet['match']
    league = bet['league']
    bet_team = bet['bet_team']  # ← НА КАКУЮ КОМАНДУ СТАВИТЬ
    bet_type = bet['bet_type']
    odds = bet['odds']
    probability = bet['probability']
    edge = bet['edge']
    confidence = bet['confidence']
    
    confidence_emoji = "✅" if confidence == "HIGH" else "⚠️"
    
    text = (
        f"🟢 *{index}. {league}*\n"
        f"   {match}\n\n"
        f"   *📍 СТАВИМ НА: {bet_team}*\n"
        f"   ({bet_type})\n\n"
        f"   💰 Коэффициент: `{odds:.2f}`\n"
        f"   🎯 Вероятность: *{probability*100:.0f}%*\n"
        f"   ⚡ EDGE: *{edge*100:.1f}%*\n"
        f"   {confidence_emoji} Уверенность: *{confidence}*\n"
    )
    
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда"""
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


async def analyze_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка анализа"""
    global CURRENT_BETS
    
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "⏳ Анализирую букмекеры...\n"
            "(статистика, форма, травмы, мотивация, история встреч)"
        )
        
        # Запуск анализа
        loop = asyncio.get_event_loop()
        bets = await loop.run_in_executor(
            None,
            find_value_bets,
            1.3,   # odds_threshold_min
            1.9,   # odds_threshold_max
            0.60   # probability_threshold
        )
        
        if not bets:
            keyboard = get_back_keyboard()
            await query.edit_message_text(
                "⚠️ Нет матчей с достаточной уверенностью\n\n"
                "Сегодня не было ставок, соответствующих критериям",
                reply_markup=keyboard
            )
            return
        
        CURRENT_BETS = bets
        
        # Форматируем результаты
        text = (
            f"🔥 *НА КОГО СТАВИТЬ? ГЛУБОКИЙ АНАЛИЗ*\n\n"
            f"Найдено ставок: *{len(bets)}*\n"
            f"Вероятность: ≥60%\n"
            f"Коэффициенты: 1.3 - 1.9\n\n"
            f"{'='*50}\n\n"
        )
        
        # Добавляем все ставки
        for i, bet in enumerate(bets, 1):
            text += format_bet_card(bet, i)
            text += "\n"
            
            # Логируем ставку
            log_bet(bet['match'], bet['bet_type'], bet['edge'], bet['odds'], bet['probability'])
        
        # Методология
        text += (
            f"{'='*50}\n\n"
            f"📋 *КАК МЫ РАССЧИТАЛИ:*\n\n"
            f"• *Форма* = последние 5-10 матчей\n"
            f"• *Дома/Гости* = процент побед\n"
            f"• *Травмы* = влияние на результат\n"
            f"• *H2H* = история встреч\n"
            f"• *Мотивация* = борьба за место\n\n"
            f"*EDGE* = наше реальное преимущество\n"
            f"над букмекером"
        )
        
        keyboard = get_back_keyboard()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info(f"✅ Анализ завершён: {len(bets)} ставок")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        keyboard = get_back_keyboard()
        await query.edit_message_text(
            f"❌ Ошибка анализа",
            reply_markup=keyboard
        )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка - как работает"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "📊 *КАК ЭТО РАБОТАЕТ:*\n\n"
        "*1️⃣ СБОР КОЭФФИЦИЕНТОВ*\n"
        "Анализируем 6 букмекеров:\n"
        "bet365, betfair, pinnacle, unibet, william_hill, bwin\n"
        "Ищем события с коэффициентами 1.3 - 1.9\n\n"
        "*2️⃣ ГЛУБОКИЙ АНАЛИЗ КАЖДОГО МАТЧА*\n"
        "Анализируем каждую команду:\n\n"
        "📈 *Форма* - последние 10 матчей\n"
        "(тренд, победы, поражения)\n\n"
        "🏟️ *Статистика дома/гости*\n"
        "(% побед дома vs в гостях)\n\n"
        "🚑 *Травмы*\n"
        "(ключевые игроки, влияние на защиту)\n\n"
        "🔄 *История встреч (H2H)*\n"
        "(как часто побеждает домашняя команда)\n\n"
        "💪 *Мотивация*\n"
        "(борьба за титул, спасение, дерби)\n\n"
        "*3️⃣ РАСЧЁТ ВЕРОЯТНОСТИ*\n"
        "Базовая: 50%\n"
        "+ все корректировки = ИТОГОВАЯ\n\n"
        "*4️⃣ ОПРЕДЕЛЯЕМ НА КАКУЮ КОМАНДУ СТАВИТЬ*\n"
        "Если вероятность >60% → ставим на эту команду\n"
        "Если вероятность 50-60% → ставим на '1X' (или ничья)\n\n"
        "*5️⃣ ПОИСК EDGE*\n"
        "Ищем разницу между нашей вероятностью\n"
        "и коэффициентом букмекера\n\n"
        "*📈 РЕЗУЛЬТАТ:*\n"
        "3-5 ставок в день\n"
        "Каждая с EDGE +3-12%\n"
        "Все обоснованы статистикой"
    )
    
    keyboard = get_back_keyboard()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о системе"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "ℹ️ *ИНФОРМАЦИЯ О СИСТЕМЕ*\n\n"
        "*🎯 ПРИНЦИП РАБОТЫ:*\n"
        "Это не угадайка - это профессиональный анализ\n\n"
        "*📊 ИСТОЧНИКИ ДАННЫХ:*\n"
        "• Football-Data.org API\n"
        "• 6 крупнейших букмекеров\n"
        "• Статистика команд\n"
        "• История встреч\n\n"
        "*💼 РЕНТАБЕЛЬНОСТЬ:*\n"
        "При 5 ставках/день с EDGE +7%:\n"
        "• +350 рублей/день\n"
        "• +8,750 рублей/месяц\n"
        "• +105,000 рублей/год\n\n"
        "*✅ ПРЕИМУЩЕСТВА:*\n"
        "✓ Только 3-5 ставок в день\n"
        "✓ Вероятность >60%\n"
        "✓ EDGE +3-12% от букмекера\n"
        "✓ Коэффициенты 1.3-1.9\n"
        "✓ Четко видно на кого ставить\n\n"
        "*⚠️ ВАЖНО:*\n"
        "Ставки связаны с финансовым риском.\n"
        "Ставьте ответственно только с деньгами,\n"
        "которые можете позволить себе потерять."
    )
    
    keyboard = get_back_keyboard()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки (заглушка)"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "⚙️ *НАСТРОЙКИ*\n\n"
        "*Скоро будут доступны:*\n"
        "🔧 Выбор лиг для анализа\n"
        "🔧 Минимум вероятности\n"
        "🔧 Минимум EDGE\n"
        "🔧 Уведомления\n"
        "🔧 История ставок\n\n"
        "Обновления в скором времени!"
    )
    
    keyboard = get_back_keyboard()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка назад в меню"""
    query = update.callback_query
    await query.answer()
    
    reply_keyboard = get_main_reply_keyboard()
    
    await query.edit_message_text(
        "🤖 *ГЛАВНОЕ МЕНЮ*\n\n"
        "Выбери действие в меню снизу ⬇️",
        reply_markup=reply_keyboard,
        parse_mode="Markdown"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений из меню"""
    text = update.message.text
    reply_keyboard = get_main_reply_keyboard()
    
    if text == "🔥 На кого ставить?":
        # Выполняем анализ
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
            
            # Форматируем результаты
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
                log_bet(bet['match'], bet['bet_type'], bet['edge'], bet['odds'], bet['probability'])
            
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
            "ℹ️ *ИНФОРМАЦИЯ О СИСТЕМЕ*\n\n"
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
            "⚙️ *НАСТРОЙКИ*\n\n"
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
    """Запуск бота"""
    try:
        logger.info("🚀 ЗАПУСК BETTING БОТА...")
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Обработчики команд
        app.add_handler(CommandHandler("start", start))
        
        # Обработчики callback кнопок
        app.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
        
        # Обработчик текстовых сообщений (меню)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        logger.info("✅ Бот готов к работе!")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"❌ Ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
