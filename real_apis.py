import os
import requests
from typing import List, Tuple

LEAGUES = {
    "EPL": ("Англия", 39),
    "LaLiga": ("Испания", 140),
    "Bundesliga": ("Германия", 78),
    "SerieA": ("Италия", 135),
    "Ligue1": ("Франция", 61),
    "UEFA": ("Лига чемпионов", 2),
    "Eredivisie": ("Нидерланды", 88),
    "Primeira": ("Португалия", 94),
    "MLS": ("США", 253),
    "Championship": ("Англия 2", 40),
    "SerieB": ("Италия 2", 136),
    "Bundesliga2": ("Германия 2", 79)
}

API_KEY = os.environ.get("SPORTS_API_KEY")
API_URL = "https://api.sportsdata.io/v4/soccer/odds/json"

def get_fixtures(league_id: int):
    r = requests.get(f"{API_URL}/FixturesByLeague/{league_id}", headers={"Ocp-Apim-Subscription-Key": API_KEY})
    return r.json() if r.status_code == 200 else []

def get_odds(league_id: int):
    r = requests.get(f"{API_URL}/OddsByLeague/{league_id}", headers={"Ocp-Apim-Subscription-Key": API_KEY})
    return r.json() if r.status_code == 200 else []

def get_xg(team_id: int, league_id: int) -> float:
    return 1.2  # упрощённый пример

def elo_prob(home: int, away: int) -> float:
    return 0.55  # упрощённый пример

def analyze_matches(min_value=0.01, odd_min=1.4, odd_max=1.9) -> List[Tuple[float, str, str, str, float]]:
    bets = []

    for lname, league_id in LEAGUES.values():
        fixtures = get_fixtures(league_id)
        odds_data = get_odds(league_id)

        for f in fixtures:
            home = f["HomeTeam"]
            away = f["AwayTeam"]

            hxg = get_xg(home["TeamId"], league_id)
            axg = get_xg(away["TeamId"], league_id)
            total_goals = hxg + axg
            xg_home = hxg / (hxg + axg)
            elo_home = elo_prob(1550, 1500)
            model_home = 0.45 * xg_home + 0.35 * elo_home + 0.2 * 0.55

            prob_over25 = min(total_goals / 3.1, 0.78)
            prob_under25 = 1 - prob_over25
            prob_btts = min((hxg * axg) / 2.2, 0.75)

            for g in odds_data:
                if g["HomeTeam"] != home:
                    continue
                for bm in g.get("Bookmakers", []):
                    for m in bm.get("Markets", []):
                        for o in m.get("Outcomes", []):
                            implied = 1 / o["Price"]
                            name = o["Name"]

                            if odd_min <= o["Price"] <= odd_max:
                                # 1X2
                                if m["Key"] == "h2h":
                                    if name == home:
                                        value = model_home - implied
                                        if value > min_value:
                                            bets.append((value, lname, f"{home} vs {away}", "П1", o["Price"]))
                                    elif name == away:
                                        value = (1 - model_home) - implied
                                        if value > min_value:
                                            bets.append((value, lname, f"{home} vs {away}", "П2", o["Price"]))
                                # Double chance
                                if m["Key"] == "double_chance":
                                    value = model_home + 0.25 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Over/Under
                                if m["Key"] == "totals":
                                    if "Over" in name:
                                        value = prob_over25 - implied
                                        if value > min_value:
                                            bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                    elif "Under" in name:
                                        value = prob_under25 - implied
                                        if value > min_value:
                                            bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # BTTS
                                if m["Key"] == "btts" and name == "Yes":
                                    value = prob_btts - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", "BTTS YES", o["Price"]))
                                # Handicap (Фора)
                                if m["Key"] == "spreads":
                                    value = model_home + 0.1 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", f"Фора {o['Point']}", o["Price"]))
                                # Total Goals Range
                                if m["Key"] == "total_goals_range":
                                    value = prob_over25 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Half Time / Full Time
                                if m["Key"] == "ht_ft":
                                    value = model_home - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Corners Over/Under
                                if m["Key"] == "corners_totals":
                                    value = prob_over25 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Cards Over/Under
                                if m["Key"] == "cards_totals":
                                    value = prob_over25 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Asian Handicap
                                if m["Key"] == "asian_handicap":
                                    value = model_home + 0.15 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Odd/Even Goals
                                if m["Key"] == "odd_even":
                                    value = 0.5 - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))
                                # Winning Margin
                                if m["Key"] == "winning_margin":
                                    value = model_home - implied
                                    if value > min_value:
                                        bets.append((value, lname, f"{home} vs {away}", name, o["Price"]))

    bets.sort(reverse=True, key=lambda x: x[0])
    return bets[:12]
