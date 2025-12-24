def analyze():
    bets = []

    for sport, (lname, league_id) in LEAGUES.items():
        fixtures = get_fixtures(league_id)
        odds = get_odds(sport)

        for f in fixtures:
            home = f["teams"]["home"]
            away = f["teams"]["away"]

            hxg = get_xg(home["id"], league_id)
            axg = get_xg(away["id"], league_id)

            total_goals = hxg + axg

            xg_home = hxg / (hxg + axg)
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
                            if m["key"] == "h2h" and name == home["name"]:
                                value = model_home - implied
                                if value > 0.08:
                                    bets.append((value, lname, f"{home['name']} vs {away['name']}", "П1", o["price"]))

                            # Over / Under
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

                            # Handicap Home
                            if m["key"] == "spreads" and name == home["name"]:
                                prob = model_home + 0.1
                                value = prob - implied
                                if value > 0.08:
                                    bets.append((value, lname, f"{home['name']} vs {away['name']}", f"Фора {o['point']}", o["price"]))

                            # Handicap Away +1
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
