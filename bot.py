import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from real_apis import (
    get_fixtures,
    get_odds,
    get_xg,
    elo_prob,
    LEAGUES,
)

TOKEN = os.getenv("TELEGRAM_TOKEN")

VALUE_EDGE = 0.01  # ОСЛАБЛЕННЫЙ VALUE (как ты просил)
TOP_LIMIT = 5


# ===================== CORE ANALYTICS =====================

def analyze_all_matches():
    results = []

    for league in LEAGUES:
        fixtures = get_fixtures(league)

        for match in fixtures:
            odds = get_odds(match["id"])
            if not odds:
                continue

            xg_home, xg_away = get_xg(match["home"], match["away"])
            prob_home = elo_prob(match["home"], match["away"])

            for market in odds:
                bookmaker_prob = 1 / market["odd"]
                model_prob = prob_home if market["side"] == "home" else (1 - prob_home)

                edge = model_prob - bookmaker_prob

                results.append({
                    "league": league,
                    "match": f'{match["home"]} vs {match["away"]}',
                    "market": market["name"],
                    "odd": market["odd"],
                    "prob": model_prob,
                    "edge": edge,
                })

    return results


def select_bets():
    all_bets = analyze_all_matches()

    # 1️⃣ VALUE (ослабленный)
    value_bets = [
        b for b in all_bets
        if b["edge"] >= VALUE_EDGE and b["odd"] >= 1.6
    ]

    value_bets.sort(key=lambda x: x["edge"], reverse=True)

    if value_bets:
        return value_bets[:TOP_LIMIT], "value"

    # 2️⃣ FALLBACK — лучшие из доступных
    fallback = sorted(
        all_bets,
        key=lambda x: (x["edge"], x["odd"]),
        reverse=True
    )

    return fallback[:TOP_LIMIT], "fallback"


# ===================== TELEGRAM =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔥 Топ ставки сегодня", callback_data="top")]
    ]
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def top_bets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("📊 Анализирую матчи, подождите...")

    bets, mode = select_bets()

    if not bets:
        await query.edit_message_text("❌ Сегодня рынок пуст.")
        return

    text = "🔥 **ТОП СТАВКИ СЕГОДНЯ**\n\n"
    if mode == "fallback":
        text += "_Value не найден — показаны лучшие доступные_\n\n"

    for b in bets:
        text += (
            f"🏟 {b['match']}\n"
            f"📌 {b['market']}\n"
            f"🎯 Кэф: {b['odd']}\n"
            f"📈 Edge: {b['edge']:.3f}\n\n"
        )

    await query.edit_message_text(text, parse_mode="Markdown")


# ===================== BOOT =====================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(top_bets, pattern="top"))

    app.run_polling()


if __name__ == "__main__":
    main()
