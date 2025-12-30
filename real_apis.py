import requests
import logging
from itertools import combinations
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Основные букмекеры для анализа
BOOKMAKERS = {
    "bet365": "https://api.bet365.com",
    "betfair": "https://api.betfair.com",
    "pinnacle": "https://api.pinnacle.com",
    "unibet": "https://api.unibet.com",
    "william_hill": "https://api.williamhill.com",
    "bwin": "https://api.bwin.com",
    "draftkings": "https://api.draftkings.com",
    "fanduel": "https://api.fanduel.com",
    "betmgm": "https://api.betmgm.com",
    "pointsbet": "https://api.pointsbet.com",
    "caesars": "https://api.caesars.com",
    "betrivers": "https://api.betrivers.com",
    "foxbet": "https://api.foxbet.com",
    "betonline": "https://api.betonline.ag",
    "bovada": "https://api.bovada.lv",
}

LEAGUES = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Английская Премьер-лига": 39,
    "🇪🇸 Испанская Ла Лига": 140,
    "🇩🇪 Немецкая Бундеслига": 78,
    "🇮🇹 Итальянская Серия А": 135,
    "🇫🇷 Французская Лига 1": 61,
    "🇵🇹 Португальская Примейра Лига": 94,
    "🇳🇱 Голландская Эредивизи": 88,
    "🏆 Лига чемпионов": 530,
    "🇺🇸 MLS (США)": 130,
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Английская Чемпионшип": 40,
    "🇮🇹 Итальянская Серия Б": 136,
    "🇩🇪 Немецкая Бундеслига 2": 79,
}

# РАСШИРЕННЫЕ РЫНКИ
MARKET_TYPES = {
    # Основные рынки
    "H2H": "1X2 (исход матча)",
    "TOTALS": "Over/Under (голы)",
    "SPREADS": "Фора (гандикап)",
    
    # Карточки и нарушения
    "YELLOW_CARDS": "Жёлтые карточки",
    "YELLOW_CARDS_OVER_8": "Жёлтых карточек Over 8.5",
    "YELLOW_CARDS_UNDER_8": "Жёлтых карточек Under 8.5",
    
    # Форы (расширенные)
    "FORA_MINUS_0_5": "Фора -0.5 (любая победа)",
    "FORA_MINUS_1_5": "Фора -1.5 (побе да на 2+)",
    "FORA_MINUS_2_5": "Фора -2.5 (побе да на 3+)",
    
    # Двойные шансы (очень популярные)
    "DOUBLE_CHANCE_1X": "Двойной шанс 1X (дома или ничья)",
    "DOUBLE_CHANCE_12": "Двойной шанс 12 (не-ничья)",
    "DOUBLE_CHANCE_X2": "Двойной шанс X2 (ничья или гости)",
    
    # Дополнительные рынки
    "CORNERS": "Угловые",
    "FIRST_GOAL": "Первый гол - хто",
    "BOTH_TEAMS_SCORE": "Обе команды забьют",
    "CLEAN_SHEET": "Чистый лист",
}


def fetch_matches_by_league(league_id: int, league_name: str) -> list:
    """Получает матчи для конкретной лиги"""
    try:
        logger.info(f"📊 Получаю матчи для {league_name}...")
        
        # Для демонстрации - генерируем тестовые матчи
        matches = generate_test_matches(league_name, league_id)
        
        logger.info(f"✅ {league_name}: {len(matches)} матчей")
        return matches
        
    except Exception as e:
        logger.error(f"❌ {league_name}: статус {str(e)}")
        return []


def generate_test_matches(league_name: str, league_id: int) -> list:
    """Генерирует тестовые матчи с реалистичными коэффициентами"""
    import random
    from datetime import datetime, timedelta
    
    teams = {
        39: ["Manchester City", "Liverpool", "Arsenal", "Chelsea", "Manchester United", "Tottenham", "Newcastle"],
        140: ["Barcelona", "Real Madrid", "Atletico Madrid", "Sevilla", "Valencia", "Real Sociedad"],
        78: ["Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen", "Eintracht Frankfurt"],
        135: ["Juventus", "AS Roma", "AC Milan", "Napoli", "Inter Milan", "Lazio"],
        61: ["Paris Saint Germain", "Marseille", "AS Monaco", "Lyon", "Lens", "Nice"],
        94: ["Benfica", "Porto", "Sporting", "Braga", "Guimaraes"],
        88: ["Ajax", "PSV", "Feyenoord", "AZ Alkmaar", "FC Twente"],
        530: ["Real Madrid", "Manchester City", "Bayern Munich", "Liverpool", "PSG"],
        130: ["Inter Miami", "LA Galaxy", "Seattle Sounders", "LAFC", "New York City FC"],
        40: ["Leeds United", "Southampton", "Leicester City", "Coventry City"],
        136: ["Parma", "Como", "Pisa", "Brescia", "Cremonese"],
        79: ["Cologne", "Hamburger SV", "Schalke 04", "Dynamo Dresden"],
    }
    
    team_list = teams.get(league_id, ["Team A", "Team B", "Team C", "Team D"])
    matches = []
    
    for _ in range(min(20, len(team_list) * 2)):
        home = random.choice(team_list)
        away = random.choice([t for t in team_list if t != home])
        
        # Генерируем коэффициенты для всех рынков
        odds_h2h = [
            random.uniform(1.5, 3.0),  # П1
            random.uniform(2.5, 4.5),  # X
            random.uniform(1.5, 3.0),  # П2
        ]
        
        odds_over = random.uniform(1.8, 2.2)
        odds_under = random.uniform(1.8, 2.2)
        odds_fora_minus_1_5 = random.uniform(1.8, 2.5)
        odds_fora_minus_0_5 = random.uniform(1.4, 1.8)
        odds_fora_minus_2_5 = random.uniform(2.5, 3.5)
        
        # Двойные шансы
        odds_double_1x = random.uniform(1.3, 1.8)
        odds_double_12 = random.uniform(1.3, 1.8)
        odds_double_x2 = random.uniform(1.3, 1.8)
        
        # Жёлтые карточки
        odds_yellow_over = random.uniform(1.8, 2.2)
        odds_yellow_under = random.uniform(1.8, 2.2)
        
        # Дополнительные рынки
        odds_corners = random.uniform(1.8, 2.2)
        odds_both_score = random.uniform(1.6, 2.0)
        odds_clean_sheet = random.uniform(1.5, 2.5)
        
        match_time = datetime.now() + timedelta(days=random.randint(1, 30))
        
        matches.append({
            "home": home,
            "away": away,
            "time": match_time,
            "odds": {
                # Основные рынки
                "h2h": odds_h2h,
                "over_2_5": odds_over,
                "under_2_5": odds_under,
                
                # Форы
                "fora_minus_0_5": odds_fora_minus_0_5,
                "fora_minus_1_5": odds_fora_minus_1_5,
                "fora_minus_2_5": odds_fora_minus_2_5,
                
                # Двойные шансы
                "double_1x": odds_double_1x,
                "double_12": odds_double_12,
                "double_x2": odds_double_x2,
                
                # Жёлтые карточки
                "yellow_over_8": odds_yellow_over,
                "yellow_under_8": odds_yellow_under,
                
                # Дополнительные
                "corners": odds_corners,
                "both_score": odds_both_score,
                "clean_sheet": odds_clean_sheet,
            },
            "bookmakers": {
                bm: {
                    # Основные рынки
                    "h2h": [o + random.uniform(-0.1, 0.1) for o in odds_h2h],
                    "over_2_5": odds_over + random.uniform(-0.15, 0.15),
                    "under_2_5": odds_under + random.uniform(-0.15, 0.15),
                    
                    # Форы
                    "fora_minus_0_5": odds_fora_minus_0_5 + random.uniform(-0.1, 0.1),
                    "fora_minus_1_5": odds_fora_minus_1_5 + random.uniform(-0.2, 0.2),
                    "fora_minus_2_5": odds_fora_minus_2_5 + random.uniform(-0.3, 0.3),
                    
                    # Двойные шансы
                    "double_1x": odds_double_1x + random.uniform(-0.1, 0.1),
                    "double_12": odds_double_12 + random.uniform(-0.1, 0.1),
                    "double_x2": odds_double_x2 + random.uniform(-0.1, 0.1),
                    
                    # Жёлтые карточки
                    "yellow_over_8": odds_yellow_over + random.uniform(-0.15, 0.15),
                    "yellow_under_8": odds_yellow_under + random.uniform(-0.15, 0.15),
                    
                    # Дополнительные
                    "corners": odds_corners + random.uniform(-0.15, 0.15),
                    "both_score": odds_both_score + random.uniform(-0.1, 0.1),
                    "clean_sheet": odds_clean_sheet + random.uniform(-0.2, 0.2),
                }
                for bm in list(BOOKMAKERS.keys())[:10]  # 10 букмекеров
            }
        })
    
    return matches


def get_best_odds(bookmakers_odds: dict, market: str) -> tuple:
    """Получает лучший коэффициент и информацию о спреде"""
    odds_list = []
    
    for bm, odds in bookmakers_odds.items():
        if market in odds:
            odd_val = odds[market]
            if isinstance(odd_val, list):
                odds_list.extend(odd_val)
            else:
                odds_list.append(odd_val)
    
    if not odds_list:
        return 0, 0, len(odds_list)
    
    best = max(odds_list)
    worst = min(odds_list)
    spread = abs(best - worst)
    
    return best, spread, len(odds_list)


def calculate_value(probability: float, odds: float) -> float:
    """Рассчитывает VALUE ставки"""
    if odds <= 0:
        return 0
    return (probability * odds) - 1


def calculate_roi(value: float, odds: float) -> float:
    """Рассчитывает ROI (Return on Investment)"""
    if odds <= 1:
        return 0
    return (value / (odds - 1)) * 100 if odds > 1 else 0


def get_implied_probability(odds: float) -> float:
    """Рассчитывает подразумеваемую вероятность из коэффициента"""
    if odds <= 0:
        return 0
    return 1 / odds


def analyze_matches(min_value: float = 0.025, odd_min: float = 1.3, odd_max: float = 3.5) -> list:
    """Анализирует матчи и находит VALUE ставки по ВСЕМ рынкам"""
    all_bets = []
    
    logger.info(f"🎯 Начинаю анализ...")
    logger.info(f"   Фильтры: Value > {min_value}, Коэффициенты {odd_min}-{odd_max}")
    logger.info(f"   Рынков для анализа: {len(MARKET_TYPES)}")
    
    for league_name, league_id in LEAGUES.items():
        matches = fetch_matches_by_league(league_id, league_name)
        
        for match in matches:
            home = match["home"]
            away = match["away"]
            match_str = f"{home} vs {away}"
            time_str = match["time"].strftime("%d.%m %H:%M")
            bookmakers_odds = match["bookmakers"]
            
            # ОСНОВНЫЕ РЫНКИ
            # Over/Under
            for market_name, market_key in [("Over", "over_2_5"), ("Under", "under_2_5")]:
                best_odd, spread, count = get_best_odds(bookmakers_odds, market_key)
                if best_odd > 0 and count >= 5 and odd_min <= best_odd <= odd_max:
                    true_prob = 0.52 if market_name == "Over" else 0.48
                    value = calculate_value(true_prob, best_odd)
                    if value >= min_value:
                        roi = calculate_roi(value, best_odd)
                        all_bets.append((
                            value, league_name, match_str, f"{market_name} 2.5", best_odd, time_str,
                            hash(match_str), {
                                "true_prob": true_prob, "implied_prob": get_implied_probability(best_odd),
                                "stats": {"count": count, "spread": spread, "best": best_odd},
                                "roi": roi, "market_type": "TOTALS"
                            }
                        ))
            
            # ФОРЫ
            for market_name, market_key, prob in [
                ("Фора -0.5", "fora_minus_0_5", 0.48),
                ("Фора -1.5", "fora_minus_1_5", 0.45),
                ("Фора -2.5", "fora_minus_2_5", 0.40),
            ]:
                best_odd, spread, count = get_best_odds(bookmakers_odds, market_key)
                if best_odd > 0 and count >= 5 and odd_min <= best_odd <= odd_max:
                    value = calculate_value(prob, best_odd)
                    if value >= min_value:
                        roi = calculate_roi(value, best_odd)
                        all_bets.append((
                            value, league_name, match_str, market_name, best_odd, time_str,
                            hash(match_str), {
                                "true_prob": prob, "implied_prob": get_implied_probability(best_odd),
                                "stats": {"count": count, "spread": spread, "best": best_odd},
                                "roi": roi, "market_type": "SPREADS"
                            }
                        ))
            
            # ДВОЙНЫЕ ШАНСЫ (высокая вероятность = низкий коэффициент)
            for market_name, market_key, prob in [
                ("1X (дома или ничья)", "double_1x", 0.68),
                ("12 (не-ничья)", "double_12", 0.65),
                ("X2 (ничья или гости)", "double_x2", 0.68),
            ]:
                best_odd, spread, count = get_best_odds(bookmakers_odds, market_key)
                if best_odd > 0 and count >= 5 and 1.1 <= best_odd <= 2.0:  # Другой диапазон для двойных
                    value = calculate_value(prob, best_odd)
                    if value >= min_value:
                        roi = calculate_roi(value, best_odd)
                        all_bets.append((
                            value, league_name, match_str, f"Двойной шанс {market_name}", best_odd, time_str,
                            hash(match_str), {
                                "true_prob": prob, "implied_prob": get_implied_probability(best_odd),
                                "stats": {"count": count, "spread": spread, "best": best_odd},
                                "roi": roi, "market_type": "DOUBLE_CHANCE"
                            }
                        ))
            
            # ЖЁЛТЫЕ КАРТОЧКИ
            for market_name, market_key, prob in [
                ("Жёлтых Over 8.5", "yellow_over_8", 0.50),
                ("Жёлтых Under 8.5", "yellow_under_8", 0.50),
            ]:
                best_odd, spread, count = get_best_odds(bookmakers_odds, market_key)
                if best_odd > 0 and count >= 5 and odd_min <= best_odd <= odd_max:
                    value = calculate_value(prob, best_odd)
                    if value >= min_value:
                        roi = calculate_roi(value, best_odd)
                        all_bets.append((
                            value, league_name, match_str, market_name, best_odd, time_str,
                            hash(match_str), {
                                "true_prob": prob, "implied_prob": get_implied_probability(best_odd),
                                "stats": {"count": count, "spread": spread, "best": best_odd},
                                "roi": roi, "market_type": "YELLOW_CARDS"
                            }
                        ))
            
            # ДОПОЛНИТЕЛЬНЫЕ РЫНКИ (Углы, обе забьют и т.д.)
            for market_name, market_key, prob in [
                ("Обе команды забьют", "both_score", 0.52),
                ("Углы", "corners", 0.50),
                ("Чистый лист", "clean_sheet", 0.35),
            ]:
                best_odd, spread, count = get_best_odds(bookmakers_odds, market_key)
                if best_odd > 0 and count >= 5 and odd_min <= best_odd <= odd_max:
                    value = calculate_value(prob, best_odd)
                    if value >= min_value:
                        roi = calculate_roi(value, best_odd)
                        all_bets.append((
                            value, league_name, match_str, market_name, best_odd, time_str,
                            hash(match_str), {
                                "true_prob": prob, "implied_prob": get_implied_probability(best_odd),
                                "stats": {"count": count, "spread": spread, "best": best_odd},
                                "roi": roi, "market_type": "ADDITIONAL"
                            }
                        ))
    
    # Сортируем по VALUE (лучшие сверху)
    all_bets.sort(key=lambda x: x[0], reverse=True)
    
    logger.info(f"🎯 Всего матчей: {sum(len(fetch_matches_by_league(lid, ln)) for ln, lid in LEAGUES.items())}")
    logger.info("📍 Использованные лиги:")
    for league_name, league_id in LEAGUES.items():
        count = len(fetch_matches_by_league(league_id, league_name))
        if count > 0:
            logger.info(f"   {league_name}: {count}")
    logger.info(f"📈 Рынков проанализировано: {len(MARKET_TYPES)}")
    logger.info(f"🎯 Найдено качественных ставок: {len(all_bets)}")
    
    return all_bets


if __name__ == "__main__":
    bets = analyze_matches()
    for bet in bets[:10]:
        print(bet)
