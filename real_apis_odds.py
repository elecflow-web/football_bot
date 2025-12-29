import os
import requests
import logging
from typing import List, Tuple
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API конфиг для OddsAPI
API_KEY = os.environ.get("SPORTS_API_KEY")
API_URL = "https://api.the-odds-api.com/v4"

# Спортивная региона для OddsAPI
SPORTS = {
    "soccer_epl": "Английская Премьер-лига",
    "soccer_spain_la_liga": "Испанская Ла Лига",
    "soccer_germany_bundesliga": "Немецкая Бундеслига",
    "soccer_italy_serie_a": "Итальянская Серия А",
    "soccer_france_ligue_one": "Французская Лига 1",
    "soccer_portugal_primeira_liga": "Португальская Примейра Лига",
    "soccer_netherlands_eredivisie": "Голландская Эредивизи",
    "soccer_uefa_champs_league": "Лига чемпионов",
    "soccer_usa_mls": "MLS (США)",
    "soccer_england_league_championship": "Английская Чемпионшип",
    "soccer_italy_serie_b": "Итальянская Серия Б",
    "soccer_germany_2_bundesliga": "Немецкая Бундеслига 2",
}

# Букмекеры для анализа
BOOKMAKERS = [
    "bet365",
    "betfair_ex",
    "betano",
    "bwin",
    "draftkings",
    "fanduel",
    "pinnacle",
    "unibet"
]

if not API_KEY:
    logger.warning("⚠️ SPORTS_API_KEY не установлен! Установите OddsAPI ключ в Railway Variables.")


def get_matches() -> List[dict]:
    """Получить все текущие матчи со всех лиг"""
    if not API_KEY:
        return []
    
    all_matches = []
    
    for sport_key, sport_name in SPORTS.items():
        try:
            logger.info(f"📊 Получаю матчи для {sport_name}...")
            
            url = f"{API_URL}/sports/{sport_key}/events"
            params = {
                "apiKey": API_KEY,
                "limit": 50,
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                matches = response.json()
                logger.info(f"✅ Получено {len(matches)} матчей для {sport_name}")
                
                for match in matches:
                    match["league"] = sport_name
                    all_matches.append(match)
            else:
                logger.error(f"❌ Ошибка API для {sport_name} (статус {response.status_code})")
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout при получении матчей для {sport_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении матчей для {sport_name}: {e}")
    
    logger.info(f"📈 Всего получено матчей: {len(all_matches)}")
    return all_matches


def get_odds_for_match(sport_key: str, event_id: str) -> List[dict]:
    """Получить коэффициенты для конкретного матча"""
    if not API_KEY:
        return []
    
    try:
        url = f"{API_URL}/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": API_KEY,
            "bookmakers": ",".join(BOOKMAKERS),
            "markets": "h2h,spreads,totals",
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("bookmakers", [])
        else:
            logger.debug(f"⚠️ Ошибка получения коэффициентов для события {event_id}")
            return []
            
    except Exception as e:
        logger.debug(f"⚠️ Ошибка при получении коэффициентов: {e}")
        return []


def calculate_probability(outcomes: List[dict]) -> dict:
    """Рассчитать вероятность на основе коэффициентов"""
    try:
        probs = {}
        total_implied = 0
        
        for outcome in outcomes:
            price = outcome.get("price", 0)
            if price > 0:
                implied = 1 / price
                total_implied += implied
                probs[outcome.get("name")] = implied
        
        # Нормализуем до 100%
        if total_implied > 0:
            probs = {k: v / total_implied for k, v in probs.items()}
        
        return probs
    except Exception as e:
        logger.debug(f"⚠️ Ошибка расчёта вероятности: {e}")
        return {}


def analyze_matches(
    min_value: float = 0.01,
    odd_min: float = 1.3,
    odd_max: float = 1.9
) -> List[Tuple[float, str, str, str, float]]:
    """
    Анализирует матчи, ищет value-ставки
    
    Returns:
        List[(value, league_name, match, market, odds)]
    """
    
    bets = []
    
    try:
        # Получаем все матчи
        matches = get_matches()
        
        if not matches:
            logger.warning("⚠️ Матчи не получены")
            return []
        
        # Анализируем каждый матч
        for match in matches:
            try:
                league = match.get("league", "Unknown")
                sport_key = next(
                    (k for k, v in SPORTS.items() if v == league),
                    None
                )
                
                if not sport_key:
                    continue
                
                event_id = match.get("id")
                home_team = match.get("home_team", "Home")
                away_team = match.get("away_team", "Away")
                match_name = f"{home_team} vs {away_team}"
                
                # Получаем коэффициенты
                bookmakers_data = get_odds_for_match(sport_key, event_id)
                
                if not bookmakers_data:
                    continue
                
                # Анализируем коэффициенты
                for bookmaker in bookmakers_data:
                    try:
                        bookmaker_name = bookmaker.get("title", "Unknown")
                        markets = bookmaker.get("markets", [])
                        
                        for market in markets:
                            market_key = market.get("key", "")
                            outcomes = market.get("outcomes", [])
                            
                            # H2H (1X2)
                            if market_key == "h2h":
                                for outcome in outcomes:
                                    price = outcome.get("price", 0)
                                    
                                    if not (odd_min <= price <= odd_max):
                                        continue
                                    
                                    outcome_name = outcome.get("name", "")
                                    implied_prob = 1 / price if price > 0 else 0
                                    
                                    # Упрощённый расчёт вероятности (50/50 для демо)
                                    if outcome_name == "Home":
                                        true_prob = 0.52
                                        market_name = f"П1 ({home_team})"
                                    elif outcome_name == "Away":
                                        true_prob = 0.48
                                        market_name = f"П2 ({away_team})"
                                    else:
                                        true_prob = 0.50
                                        market_name = outcome_name
                                    
                                    value = true_prob - implied_prob
                                    
                                    if value > min_value:
                                        bets.append((
                                            value,
                                            league,
                                            match_name,
                                            market_name,
                                            price
                                        ))
                                        logger.info(
                                            f"✅ Найдена ставка: {match_name} | "
                                            f"{market_name} @ {price:.2f} | Value: {value:.4f}"
                                        )
                            
                            # Over/Under
                            elif market_key == "totals":
                                for outcome in outcomes:
                                    price = outcome.get("price", 0)
                                    
                                    if not (odd_min <= price <= odd_max):
                                        continue
                                    
                                    outcome_name = outcome.get("name", "")
                                    implied_prob = 1 / price if price > 0 else 0
                                    
                                    if "Over" in outcome_name:
                                        true_prob = 0.48
                                    else:
                                        true_prob = 0.52
                                    
                                    value = true_prob - implied_prob
                                    
                                    if value > min_value:
                                        bets.append((
                                            value,
                                            league,
                                            match_name,
                                            outcome_name,
                                            price
                                        ))
                                        logger.info(
                                            f"✅ Найдена ставка: {match_name} | "
                                            f"{outcome_name} @ {price:.2f} | Value: {value:.4f}"
                                        )
                            
                            # Spreads (Asian Handicap)
                            elif market_key == "spreads":
                                for outcome in outcomes:
                                    price = outcome.get("price", 0)
                                    
                                    if not (odd_min <= price <= odd_max):
                                        continue
                                    
                                    outcome_name = outcome.get("name", "")
                                    implied_prob = 1 / price if price > 0 else 0
                                    true_prob = 0.50
                                    value = true_prob - implied_prob
                                    
                                    if value > min_value:
                                        point = outcome.get("point", 0)
                                        market_name = f"Фора {point}"
                                        
                                        bets.append((
                                            value,
                                            league,
                                            match_name,
                                            market_name,
                                            price
                                        ))
                    
                    except Exception as e:
                        logger.debug(f"⚠️ Ошибка обработки букмекера: {e}")
                        continue
            
            except Exception as e:
                logger.debug(f"⚠️ Ошибка обработки матча: {e}")
                continue
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка анализа: {e}", exc_info=True)
    
    # Сортируем по value (убывание)
    bets.sort(reverse=True, key=lambda x: x[0])
    
    logger.info(f"📈 Всего найдено ставок: {len(bets)}")
    
    # Возвращаем топ-12
    return bets[:12]


if __name__ == "__main__":
    # Тестирование
    print("🧪 Тестирование анализа матчей с OddsAPI...")
    results = analyze_matches()
    
    if results:
        print(f"\n✅ Найдено {len(results)} ставок:\n")
        for value, league, match, market, odd in results[:5]:
            print(f"{league} | {match}")
            print(f"  {market} @ {odd:.2f} | Value: {value:.4f}\n")
    else:
        print("❌ Ставки не найдены (проверьте API_KEY)")
