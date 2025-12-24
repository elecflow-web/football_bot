import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Токен ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- Лиги ---
LEAGUES = {
    "soccer": [
        ("Premier League", 39),
        ("La Liga", 140),
        ("Serie A", 135),
        ("Bundesliga", 78),
        ("Ligue 1", 61),
        ("Eredivisie", 88),
        ("Primeira Liga", 94),
        ("Championship", 40),
        ("Liga MX", 262),
        ("MLS", 253),
        ("Brasileirão", 235),
        ("Russian Premier League", 2)
    ]
}

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔥 Топ ставок", callback_data='top_bets')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите опцию:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'top_bets':
        await query.edit_message_text(text="Идёт анализ матчей, подождите...")
        bets = await analyze_top_bets()
        msg = "\n".join([f"{b[2]} | {b[3]} | Коэфф: {b[4]}" for b in bets])
        await query.edit_message_text(text=f"💰 Топ ставки:\n{msg}")
    elif query.data == 'help':
        await query.edit_message_text(text="Помощь: используйте кнопки для навигации.")
    elif query.data == 'stats':
        await query.edit_message_text(text="Статистика по матчам появится здесь.")

# --- Анализ матчей ---
async def analyze_top_bets():
    bets = []

    for sport, leagues in LEAGUES.items():
        for lname, league_id in leagues:
            fixtures = get_fixtures(league_id)  # API-функция
            odds = get_odds(sport)  # API-функция

            for f in fixtures:
                home = f["teams"]["home"]
                away = f["teams"]["away"]

                hxg = get_xg(home["id"], league_id)
                axg = get_xg(away["id"], league_id)
                total_goals = hxg + axg

                xg_home = hxg / (hxg + axg) if (hxg + axg) > 0 else 0.5
                elo_home = elo_prob(1550, 1500)
                model_home = 0.45 * xg_home + 0.35 * elo_home + 0.20 * 0.55

                prob_over25 = min(total_goals / 3.1, 0.78)
                prob_under25 = 1 - prob_over25
                prob_btts = min((hxg * axg) / 2.2, 0.75)

                for g in odds:
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
                                        value = (1-model_home) - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", "П2", o["price"]))

                                # Double Chance
                                if m["key"] == "h2h":
                                    if name == home["name"]:
                                        prob = model_home + 0.25
                                        value = prob - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", "1X", o["price"]))
                                    if name == away["name"]:
                                        prob = 1-model_home + 0.25
                                        value = prob - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", "X2", o["price"]))

                                # Totals Over/Under
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

                                # Handicap / Spread
                                if m["key"] == "spreads":
                                    if name == home["name"]:
                                        prob = model_home + 0.1
                                        value = prob - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", f"Фора {o['point']}", o["price"]))
                                    if name == away["name"]:
                                        prob = 1-model_home + 0.1
                                        value = prob - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['name']} vs {away['name']}", f"Фора {o['point']} (гости)", o["price"]))

                                # Точный счёт (пример)
                                if m["key"] == "score":
                                    value = 0.2  # минимальная модель
                                    if value - implied > 0.08:
                                        bets.append((value, lname, f"{home['name']} vs {away['name']}", name, o["price"]))

    bets.sort(reverse=True, key=lambda x: x[0])
    return bets[:12]

# --- Основная функция ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
