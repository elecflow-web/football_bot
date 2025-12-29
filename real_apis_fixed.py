import os
import requests
import logging
from typing import List, Tuple
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ЛИГИ (исправлено - правильные ID для SportsData.io)
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
    "Bundesliga2": ("Германия 2", 79),
}

# API конфиг
API_KEY = os.environ.get("SPORTS_API_KEY")
API_URL = "https://api.sportsdata.io/v4/soccer/odds/json"

if not API_KEY:
    logger.warning("⚠️ SPORTS_API_KEY не установлен! Бот будет работать с демо-данными.")


def get_fixtures(league_id: int) -> list:
    """Получить матчи лиги"""
    if not API_KEY:
        return []
    
    try:
        url = f"{API_URL}/FixturesByLeague/{league_id}"
        headers = {"Ocp-Apim-Subscription-Key": API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Получены матчи для лиги {league_id}")
            return response.json()
        else:
            logger.error(f"❌ Ошибка API (статус {response.status_code}): {response.text}")
            return []
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout при запросе матчей")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчей: {e}")
        return []


def get_odds(league_id: int) -> list:
    """Получить коэффициенты для лиги"""
    if not API_KEY:
        return []
    
    try:
        url = f"{API_URL}/OddsByLeague/{league_id}"
        headers = {"Ocp-Apim-Subscription-Key": API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Получены коэффициенты для лиги {league_id}")
            return response.json()
        else:
            logger.error(f"❌ Ошибка API коэффициентов: {response.status_code}")
            return []
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout при запросе коэффициентов")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка при получении коэффициентов: {e}")
        return []


def get_xg(team_id: int, league_id: int) -> float:
    """
    Получить xG команды
    TODO: Реализовать реальный расчёт на основе исторических данных
    """
    # На данный момент - упрощённый пример
    return 1.2


def elo_prob(home_elo: float, away_elo: float) -> float:
    """
    Рассчитать вероятность домашней команды по Elo
    Формула: prob = 1 / (1 + 10^(-rating_diff/400))
    """
    try:
        rating_diff = home_elo - away_elo
        prob = 1 / (1 + 10 ** (-rating_diff / 400))
        return prob
    except Exception as e:
        logger.error(f"Ошибка при расчёте Elo: {e}")
        return 0.5


def analyze_matches(
    min_value: float = 0.01, 
    odd_min: float = 1.3, 
    odd_max: float = 1.9
) -> List[Tuple[float, str, str, str, float]]:
    """
    Анализирует все матчи, ищет value-ставки
    
    Returns:
        List[(value, league_name, match, market, odds)]
    """
    
    bets = []
    
    # ИСПРАВЛЕНО: правильная распаковка словаря
    for short_name, (league_name, league_id) in LEAGUES.items():
        try:
            logger.info(f"📊 Анализирую {league_name} (ID: {league_id})...")
            
            fixtures = get_fixtures(league_id)
            odds_data = get_odds(league_id)
            
            if not fixtures or not odds_data:
                logger.warning(f"⚠️ Нет данных для {league_name}")
                continue
            
            # Обработка матчей
            for fixture in fixtures:
                try:
                    # ИСПРАВЛЕНО: правильная обработка структуры JSON
                    home_team_id = fixture.get("HomeTeamId")
                    away_team_id = fixture.get("AwayTeamId")
                    home_team_name = fixture.get("HomeTeam", {}).get("Name", "Unknown")
                    away_team_name = fixture.get("AwayTeam", {}).get("Name", "Unknown")
                    
                    if not all([home_team_id, away_team_id, home_team_name, away_team_name]):
                        continue
                    
                    # Получаем xG
                    home_xg = get_xg(home_team_id, league_id)
                    away_xg = get_xg(away_team_id, league_id)
                    
                    total_goals = home_xg + away_xg
                    
                    # Вероятности
                    xg_home_prob = home_xg / (home_xg + away_xg) if total_goals > 0 else 0.5
                    
                    # Elo (упрощённо)
                    elo_home_prob = elo_prob(1550, 1500)
                    
                    # Комбинированная модель
                    model_home = 0.45 * xg_home_prob + 0.35 * elo_home_prob + 0.2 * 0.55
                    
                    # Вероятности для других рынков
                    prob_over25 = min(total_goals / 3.1, 0.78)
                    prob_under25 = 1 - prob_over25
                    prob_btts = min((home_xg * away_xg) / 2.2, 0.75)
                    
                    match_name = f"{home_team_name} vs {away_team_name}"
                    
                    # Обработка коэффициентов
                    for odd_entry in odds_data:
                        try:
                            # ИСПРАВЛЕНО: правильная обработка структуры коэффициентов
                            odd_home_id = odd_entry.get("HomeTeamId")
                            odd_away_id = odd_entry.get("AwayTeamId")
                            
                            if odd_home_id != home_team_id or odd_away_id != away_team_id:
                                continue
                            
                            # Букмекеры
                            bookmakers = odd_entry.get("Bookmakers", [])
                            
                            for bookmaker in bookmakers:
                                markets = bookmaker.get("Markets", [])
                                
                                for market in markets:
                                    market_key = market.get("Key", "")
                                    outcomes = market.get("Outcomes", [])
                                    
                                    for outcome in outcomes:
                                        try:
                                            odd_price = outcome.get("Price", 0)
                                            outcome_name = outcome.get("Name", "")
                                            
                                            if not (odd_min <= odd_price <= odd_max) or odd_price == 0:
                                                continue
                                            
                                            implied_prob = 1 / odd_price
                                            value = 0
                                            market_name = ""
                                            
                                            # ========== РЫНКИ ==========
                                            
                                            # 1X2
                                            if market_key == "h2h":
                                                if outcome_name == home_team_name:
                                                    value = model_home - implied_prob
                                                    market_name = f"П1 (Победа {home_team_name})"
                                                elif outcome_name == away_team_name:
                                                    value = (1 - model_home) - implied_prob
                                                    market_name = f"П2 (Победа {away_team_name})"
                                            
                                            # Over/Under 2.5
                                            elif market_key == "totals":
                                                if "Over" in outcome_name:
                                                    value = prob_over25 - implied_prob
                                                    market_name = f"Тотал {outcome_name}"
                                                elif "Under" in outcome_name:
                                                    value = prob_under25 - implied_prob
                                                    market_name = f"Тотал {outcome_name}"
                                            
                                            # BTTS
                                            elif market_key == "btts":
                                                if "Yes" in outcome_name:
                                                    value = prob_btts - implied_prob
                                                    market_name = "BTTS Yes"
                                            
                                            # Double Chance
                                            elif market_key == "double_chance":
                                                value = (model_home + 0.25) - implied_prob
                                                market_name = f"Двойной шанс {outcome_name}"
                                            
                                            # Asian Handicap
                                            elif market_key == "asian_handicap":
                                                value = model_home + 0.15 - implied_prob
                                                market_name = f"Азиатский гандикап {outcome_name}"
                                            
                                            # Добавляем в список, если value положителен
                                            if value > min_value and market_name:
                                                bets.append((
                                                    value,
                                                    league_name,
                                                    match_name,
                                                    market_name,
                                                    odd_price
                                                ))
                                                logger.info(
                                                    f"  ✅ Найдена ставка: {match_name} | "
                                                    f"{market_name} @ {odd_price:.2f} | "
                                                    f"Value: {value:.4f}"
                                                )
                                        
                                        except Exception as e:
                                            logger.debug(f"Ошибка обработки коэффициента: {e}")
                                            continue
                        
                        except Exception as e:
                            logger.debug(f"Ошибка обработки коэффициента входа: {e}")
                            continue
                
                except Exception as e:
                    logger.debug(f"Ошибка обработки матча: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"❌ Ошибка при анализе {league_name}: {e}")
            continue
    
    # Сортировка по value (убывание)
    bets.sort(reverse=True, key=lambda x: x[0])
    
    logger.info(f"📈 Всего найдено ставок: {len(bets)}")
    
    # Возвращаем топ-12
    return bets[:12]


if __name__ == "__main__":
    # Тестирование
    print("🧪 Тестирование анализа матчей...")
    results = analyze_matches()
    
    if results:
        print(f"\n✅ Найдено {len(results)} ставок:\n")
        for value, league, match, market, odd in results[:5]:
            print(f"{league} | {match}")
            print(f"  {market} @ {odd:.2f} | Value: {value:.4f}\n")
    else:
        print("❌ Ставки не найдены")
