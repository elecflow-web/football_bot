from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, JobQueue
import os
import asyncio

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Список 12 лиг
LEAGUES = {
    "EPL": ("English Premier League", 39),
    "LaLiga": ("La Liga", 140),
    "Bundesliga": ("Bundesliga", 78),
    "SerieA": ("Serie A", 135),
    "Ligue1": ("Ligue 1", 61),
    "Champions": ("Champions League", 2),
    "Europa": ("Europa League", 3),
    "MLS": ("MLS", 253),
    "Brasileirao": ("Brasileirao", 7),
    "Primeira": ("Primeira Liga", 94),
    "Eredivisie": ("Eredivisie", 88),
    "SuperLig": ("Turkish Super Lig", 81)
}

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставки", callback_data="topbets")],
        [InlineKeyboardButton("Обновить данные", callback_data="refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Бот запущен и готов к работе.\nВыберите действие:", reply_markup=reply_markup
    )

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "topbets":
        await query.edit_message_text("Идёт анализ матчей, подождите...")
        bets = await analyze_matches()
        if not bets:
            await query.message.reply_text("На данный момент потенциально проходящих ставок нет.")
            return
        text = "💰 Рекомендации по ставкам:\n\n"
        for b in bets[:15]:  # максимум 15 рекомендаций
            value, league, match, market, price = b
            text += f"{league} | {match} | {market} | Коэф: {price:.2f} | Value: {value:.2f}\n"
        await query.message.reply_text(text)
    elif query.data == "refresh":
        await query.edit_message_text("Данные обновлены!")

# Асинхронная функция анализа матчей
async def analyze_matches():
    bets = []
    for sport, (lname, league_id) in LEAGUES.items():
        fixtures = get_fixtures(league_id)  # реальные API
        odds_list = get_odds(sport)         # реальные API

        for f in fixtures:
            home = f["teams"]["home"]
            away = f["teams"]["away"]
            
            hxg = get_xg(home["id"], league_id)
            axg = get_xg(away["id"], league_id)
            total_goals = hxg + axg
            xg_home = hxg / (hxg + axg) if hxg + axg > 0 else 0.5
            elo_home = elo_prob(home.get("elo", 1500), away.get("elo", 1500))
            model_home = 0.45 * xg_home + 0.35 * elo_home + 0.20 * 0.5

            prob_over25 = min(total_goals / 3.1, 0.78)
            prob_under25 = 1 - prob_over25
            prob_btts = min((hxg * axg) / 2.2, 0.75)

            for g in odds_list:
                if home["name"] not in g["home_team"]:
                    continue
                for bm in g["bookmakers"]:
                    for m in bm["markets"]:
                        for o in m["outcomes"]:
                            implied = 1 / o["price"]
                            name = o["name"]

                            # 1X2
                            if m["key"] == "h2h":
                                if name == home["name"]:
                                    value = model_home - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "П1", o["price"]))
                                elif name == away["name"]:
                                    value = (1 - model_home) - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "П2", o["price"]))

                            # Over/Under
                            if m["key"] == "totals":
                                if "Over" in name:
                                    value = prob_over25 - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", name, o["price"]))
                                elif "Under" in name:
                                    value = prob_under25 - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", name, o["price"]))

                            # BTTS
                            if m["key"] == "btts" and name == "Yes":
                                value = prob_btts - implied
                                if value > 0.08:
                                    bets.append((value, lname, f"{home['name']} vs {away['name']}", "BTTS YES", o["price"]))

                            # Handicap
                            if m["key"] == "spreads":
                                if name == home["name"]:
                                    prob = model_home + 0.1
                                    value = prob - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", f"Фора {o['point']}", o["price"]))
                                elif name == away["name"] and o["point"] == 1:
                                    prob = 1 - model_home + 0.15
                                    value = prob - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "Фора +1 (гости)", o["price"]))

                            # Double Chance
                            if m["key"] == "h2h" and name == home["name"]:
                                prob = model_home + 0.25
                                value = prob - implied
                                if value > 0.08:
                                    bets.append((value, lname, f"{home['name']} vs {away['name']}", "1X", o["price"]))
    bets.sort(reverse=True, key=lambda x: x[0])
    return bets

# JobQueue для автоматического обновления
async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    bets = await analyze_matches()
    if TELEGRAM_CHAT_ID and bets:
        text = "💰 Автоматическое обновление топ ставок:\n\n"
        for b in bets[:10]:
            value, league, match, market, price = b
            text += f"{league} | {match} | {market} | Коэф: {price:.2f} | Value: {value:.2f}\n"
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # JobQueue
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(scheduled_job, interval=600, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
