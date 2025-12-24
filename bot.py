# bot.py
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)
import httpx

# ---------------- CONFIG ----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
XG_API_KEY = os.environ.get("XG_API_KEY")

# ---------------- LEAGUES ----------------
# Пример 12 лиг, можно расширить
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
        ("Belgian Pro League", 95),
        ("Swiss Super League", 203),
        ("MLS", 253),
    ]
}

# ---------------- REAL DATA FUNCTIONS ----------------
async def get_fixtures(league_id):
    url = f"https://api.sportsdata.io/v4/soccer/scores/json/FixturesByLeague/{league_id}"
    headers = {"Ocp-Apim-Subscription-Key": ODDS_API_KEY}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

async def get_odds(sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "h2h,spreads,totals,btts,team_totals,double_chance,draw_no_bet,half_time_full_time,ou_1.5,ou_3.5"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

async def get_xg(team_id, league_id):
    url = f"https://your-xg-api.com/team/{team_id}/xg?league={league_id}"
    headers = {"Authorization": f"Bearer {XG_API_KEY}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()["xG"]

def elo_prob(home_elo, away_elo):
    diff = home_elo - away_elo
    return 1 / (1 + 10 ** (-diff / 400))

# ---------------- ANALYSIS ----------------
async def analyze_top_bets():
    bets = []

    for sport, leagues in LEAGUES.items():
        for lname, league_id in leagues:
            fixtures = await get_fixtures(league_id)
            odds_list = await get_odds(sport)

            for f in fixtures:
                home = f["HomeTeam"]
                away = f["AwayTeam"]

                hxg = await get_xg(home["TeamId"], league_id)
                axg = await get_xg(away["TeamId"], league_id)
                elo_home = elo_prob(home["Elo"], away["Elo"])

                total_goals = hxg + axg
                xg_home = hxg / (hxg + axg) if (hxg + axg) > 0 else 0.5
                model_home = 0.45 * xg_home + 0.35 * elo_home + 0.20 * 0.55

                prob_over25 = min(total_goals / 3.1, 0.78)
                prob_under25 = 1 - prob_over25
                prob_btts = min((hxg * axg) / 2.2, 0.75)

                # Проходим по реальным рынкам
                for market in odds_list:
                    for bm in market["bookmakers"]:
                        for m in bm["markets"]:
                            for o in m["outcomes"]:
                                implied = 1 / o["price"]
                                name = o["name"]

                                # 1X2
                                if m["key"] == "h2h" and name == home["Name"]:
                                    value = model_home - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['Name']} vs {away['Name']}", "П1", o["price"]))

                                # Over / Under
                                if m["key"] == "totals":
                                    if "Over" in name:
                                        value = prob_over25 - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['Name']} vs {away['Name']}", name, o["price"]))
                                    if "Under" in name:
                                        value = prob_under25 - implied
                                        if value > 0.08:
                                            bets.append((value, lname, f"{home['Name']} vs {away['Name']}", name, o["price"]))

                                # BTTS
                                if m["key"] == "btts" and name == "Yes":
                                    value = prob_btts - implied
                                    if value > 0.08:
                                        bets.append((value, lname, f"{home['Name']} vs {away['Name']}", "BTTS YES", o["price"]))

    bets.sort(reverse=True, key=lambda x: x[0])
    return bets[:12]

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставки", callback_data="top_bets")],
        [InlineKeyboardButton("Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Бот запущен и готов к работе.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "top_bets":
        await query.edit_message_text(text="Идёт анализ матчей, подождите...")
        bets = await analyze_top_bets()
        text = "🔥 Топ ставки:\n\n" + "\n".join([f"{l}: {m} — {mk} ({o})" for _, l, m, mk, o in bets])
        await query.edit_message_text(text=text)
    elif query.data == "help":
        await query.edit_message_text(text="Используйте кнопку 'Топ ставки' для получения рекомендаций.")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # JobQueue — каждые 10 минут обновление
    job_queue = app.job_queue
    job_queue.run_repeating(lambda ctx: asyncio.create_task(analyze_top_bets()), interval=600, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
