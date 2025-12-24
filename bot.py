from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, JobQueue
)
import os
import asyncio

# ---------------------- Настройки ----------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ---------------------- Лиги ----------------------
LEAGUES = {
    "soccer": [
        ("Premier League", 39),
        ("La Liga", 140),
        ("Serie A", 135),
        ("Bundesliga", 78),
        ("Ligue 1", 61),
        ("Eredivisie", 88),
        ("Primeira Liga", 94),
        ("Russian Premier League", 293),
        ("Super Lig", 307),
        ("Ukrainian Premier League", 262),
        ("MLS", 253),
        ("Championship", 40)
    ]
}

# ---------------------- Команды ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Анализ ставок", callback_data="analyze")],
        [InlineKeyboardButton("Топ-матчи", callback_data="top_matches")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Бот запущен и готов к работе.", reply_markup=reply_markup
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "analyze":
        await query.edit_message_text("Идёт анализ матчей, подождите...")
        bets = await analyze_matches()
        text = format_bets(bets)
        await query.edit_message_text(text)
    elif query.data == "top_matches":
        await query.edit_message_text("Функция топ-матчей пока в разработке.")

# ---------------------- Анализ матчей ----------------------
async def analyze_matches():
    bets = []

    # Проходим по всем лигам
    for sport, leagues in LEAGUES.items():
        for lname, league_id in leagues:
            fixtures = get_fixtures(league_id)  # Реальный API
            odds_data = get_odds(sport)        # Реальный API

            for f in fixtures:
                home = f["teams"]["home"]
                away = f["teams"]["away"]

                hxg = get_xg(home["id"], league_id)
                axg = get_xg(away["id"], league_id)
                total_goals = hxg + axg

                xg_home = hxg / (hxg + axg) if (hxg+axg) > 0 else 0.5
                elo_home = elo_prob(home["elo"], away["elo"])
                model_home = 0.45 * xg_home + 0.35 * elo_home + 0.2 * 0.5

                prob_over25 = min(total_goals / 3.1, 0.78)
                prob_under25 = 1 - prob_over25
                prob_btts = min((hxg * axg) / 2.2, 0.75)

                # Проходим по рынкам
                for g in odds_data:
                    if home["name"] not in g["home_team"]:
                        continue
                    for bm in g["bookmakers"]:
                        for m in bm["markets"]:
                            for o in m["outcomes"]:
                                implied = 1 / o["price"]
                                name = o["name"]

                                # 1X2
                                if m["key"] == "h2h" and name == home["name"]:
                                    value = model_home - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "П1", o["price"]))

                                # Totals
                                if m["key"] == "totals":
                                    if "Over" in name:
                                        value = prob_over25 - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", name, o["price"]))
                                    if "Under" in name:
                                        value = prob_under25 - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", name, o["price"]))

                                # BTTS
                                if m["key"] == "btts" and name == "Yes":
                                    value = prob_btts - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "BTTS YES", o["price"]))

                                # Handicap
                                if m["key"] == "spreads" and name == home["name"]:
                                    prob = model_home + 0.1
                                    value = prob - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", f"Фора {o['point']}", o["price"]))

                                if m["key"] == "spreads" and name == away["name"] and o["point"] == 1:
                                    prob = 1 - model_home + 0.15
                                    value = prob - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "Фора +1 (гости)", o["price"]))

                                # Double Chance 1X
                                if m["key"] == "h2h" and name == home["name"]:
                                    prob = model_home + 0.25
                                    value = prob - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", "1X", o["price"]))

    bets.sort(reverse=True, key=lambda x: x[0])
    return bets[:12]

def format_bets(bets):
    text = "🔥 Рекомендованные ставки:\n\n"
    for value, league, match, market, odd in bets:
        text += f"{league}: {match}\n{market} — {odd:.2f} (Value: {value:.2f})\n\n"
    return text

# ---------------------- JobQueue ----------------------
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    if TELEGRAM_CHAT_ID:
        bets = await analyze_matches()
        text = format_bets(bets)
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

# ---------------------- Main ----------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))

    # JobQueue каждые 10 минут
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(notify_top_bets, interval=600, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
