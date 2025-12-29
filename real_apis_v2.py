import os
import requests
import logging
from typing import List, Tuple, Dict
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API конфиг для OddsAPI
API_KEY = os.environ.get("SPORTS_API_KEY")
API_URL = "https://api.the-odds-api.com/v4"

# Футбольные лиги для OddsAPI
SOCCER_SPORTS = {
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

# Регионы для получения коэффициентов (важно!)
REGIONS = "uk,eu"  # UK и EU регионы

if not API_KEY:
    logger.warning("⚠️ SPORTS_API_KEY не установлен! Установите OddsAPI ключ в Railway Variables.")


def get_odds_for_sport(sport_key: str, league_name: str) -> List[dict]:
    """
    Получить матчи и коэффициенты для лиги
    """
    if not API_KEY:
        return []
    
    try:
        logger.info(f"📊 Получаю матчи для {league_name}...")
        
        url = f"{API_URL}/sports/{sport_key}/odds/"
        
        params = {
            "apiKey": API_KEY,
            "regions": REGIONS,
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if "x-requests-remaining" in response.headers:
            remaining = response.headers.get("x-requests-remaining")
            logger.info(f"📊 API квота осталось: {remaining}")
        
        if response.status_code == 200:
            matches = response.json()
            
            if not matches:
                logger.warning(f"⚠️ Нет матчей для {league_name}")
                return []
            
            logger.info(f"✅ Получено {len(matches)} матчей для {league_name}")
            
            for match in matches:
                match["league"] = league_name
                match["sport_key"] = sport_key
            
            return matches
        else:
            logger.error(f"❌ Ошибка API для {league_name} (статус {response.status_code})")
            return []
    
    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчей для {league_name}: {e}")
        return []


def format_match_time(commence_time_str: str) -> str:
    """Форматирует время матча в читаемый вид"""
    try:
        dt = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
        # Переводим в московское время (UTC+3)
        moscow_tz = datetime.fromisoformat("2000-01-01+03:00").tzinfo
        dt_moscow = dt.astimezone(moscow_tz)
        return dt_moscow.strftime("%d.%m %H:%M")
    except:
        return "?"


def calculate_value(true_probability: float, odds: float, min_value: float = 0.01) -> float:
    """Рассчитать value bet"""
    if odds <= 0:
        return 0
    return (true_probability * odds) - 1


def get_bookmaker_analysis(bookmakers: list, outcome_name: str, market_key: str) -> Dict:
    """
    Анализирует коэффициенты от разных букмекеров для исхода
    Возвращает: {best_price, bookmaker_count, avg_price}
    """
    prices = []
    bookmaker_names = []
    
    for bookmaker in bookmakers:
        try:
            markets = bookmaker.get("markets", [])
            for market in markets:
                if market.get("key") != market_key:
                    continue
                
                outcomes = market.get("outcomes", [])
                for outcome in outcomes:
                    if outcome.get("name") == outcome_name:
                        price = outcome.get("price", 0)
                        if price > 0:
                            prices.append(price)
                            bookmaker_names.append(bookmaker.get("title", "Unknown"))
        except:
            continue
    
    if not prices:
        return {"best_price": 0, "count": 0, "avg": 0, "bookmakers": []}
    
    return {
        "best_price": max(prices),
        "count": len(prices),
        "avg": sum(prices) / len(prices),
        "bookmakers": bookmaker_names[:3]  # Топ 3 букмекера
    }


def analyze_matches(
    min_value: float = 0.005,
    odd_min: float = 1.2,
    odd_max: float = 2.5
) -> List[Tuple]:
    """
    Анализирует матчи, ищет value-ставки
    
    Returns:
        List[(value, league, match_name, market, odd, match_time, match_id, analysis_details)]
    """
    
    bets = []
    seen_matches = set()  # Для исключения дубликатов
    
    try:
        # Получаем матчи со всех лиг
        all_matches = []
        
        for sport_key, league_name in SOCCER_SPORTS.items():
            matches = get_odds_for_sport(sport_key, league_name)
            all_matches.extend(matches)
        
        if not all_matches:
            logger.warning("⚠️ Матчи не получены ни из одной лиги")
            return []
        
        logger.info(f"🎯 Всего получено матчей: {len(all_matches)}")
        logger.info(f"📍 Использованные лиги:")
        for league in set([m.get("league") for m in all_matches]):
            logger.info(f"   ✅ {league}")
        
        # Анализируем каждый матч
        for match in all_matches:
            try:
                league = match.get("league", "Unknown")
                home_team = match.get("home_team", "Home")
                away_team = match.get("away_team", "Away")
                match_id = match.get("id", "")
                commence_time = match.get("commence_time", "")
                match_time_formatted = format_match_time(commence_time)
                match_name = f"{home_team} vs {away_team}"
                
                # Используем match_id + league как уникальный ключ для исключения дубликатов
                match_key = f"{match_id}_{league}"
                if match_key in seen_matches:
                    continue
                
                bookmakers = match.get("bookmakers", [])
                
                if not bookmakers:
                    continue
                
                # Анализируем коэффициенты от разных букмекеров
                for bookmaker in bookmakers:
                    try:
                        markets = bookmaker.get("markets", [])
                        
                        for market in markets:
                            market_key = market.get("key", "")
                            outcomes = market.get("outcomes", [])
                            
                            # ===== H2H (1X2) =====
                            if market_key == "h2h":
                                for outcome in outcomes:
                                    try:
                                        price = outcome.get("price", 0)
                                        outcome_name = outcome.get("name", "")
                                        
                                        if not (odd_min <= price <= odd_max) or price <= 1:
                                            continue
                                        
                                        # Определяем вероятность
                                        if outcome_name == home_team:
                                            true_prob = 0.52
                                            market_display = f"П1 ({home_team})"
                                        elif outcome_name == away_team:
                                            true_prob = 0.48
                                            market_display = f"П2 ({away_team})"
                                        else:
                                            continue
                                        
                                        value = calculate_value(true_prob, price, min_value)
                                        
                                        if value > min_value:
                                            # Получаем анализ других букмекеров
                                            analysis = get_bookmaker_analysis(bookmakers, outcome_name, "h2h")
                                            
                                            bet_details = {
                                                "value": value,
                                                "league": league,
                                                "match": match_name,
                                                "market": market_display,
                                                "price": price,
                                                "time": match_time_formatted,
                                                "match_id": match_id,
                                                "true_prob": true_prob,
                                                "implied_prob": 1 / price,
                                                "analysis": analysis,
                                                "market_type": "H2H"
                                            }
                                            
                                            bets.append((
                                                value,
                                                league,
                                                match_name,
                                                market_display,
                                                price,
                                                match_time_formatted,
                                                match_id,
                                                bet_details
                                            ))
                                            
                                            seen_matches.add(match_key)
                                            logger.debug(f"✅ Найдена ставка: {match_name} @ {match_time_formatted}")
                                    
                                    except Exception as e:
                                        logger.debug(f"⚠️ Ошибка обработки H2H: {e}")
                                        continue
                            
                            # ===== TOTALS (Over/Under) =====
                            elif market_key == "totals":
                                for outcome in outcomes:
                                    try:
                                        price = outcome.get("price", 0)
                                        outcome_name = outcome.get("name", "")
                                        point = outcome.get("point", 0)
                                        
                                        if not (odd_min <= price <= odd_max) or price <= 1:
                                            continue
                                        
                                        if "Over" in outcome_name:
                                            true_prob = 0.48
                                        else:
                                            true_prob = 0.52
                                        
                                        value = calculate_value(true_prob, price, min_value)
                                        
                                        if value > min_value:
                                            market_display = f"{outcome_name} {point:.1f}"
                                            analysis = get_bookmaker_analysis(bookmakers, outcome_name, "totals")
                                            
                                            bet_details = {
                                                "value": value,
                                                "league": league,
                                                "match": match_name,
                                                "market": market_display,
                                                "price": price,
                                                "time": match_time_formatted,
                                                "match_id": match_id,
                                                "true_prob": true_prob,
                                                "implied_prob": 1 / price,
                                                "analysis": analysis,
                                                "market_type": "Totals"
                                            }
                                            
                                            bets.append((
                                                value,
                                                league,
                                                match_name,
                                                market_display,
                                                price,
                                                match_time_formatted,
                                                match_id,
                                                bet_details
                                            ))
                                            
                                            seen_matches.add(match_key)
                                    
                                    except Exception as e:
                                        logger.debug(f"⚠️ Ошибка обработки Totals: {e}")
                                        continue
                            
                            # ===== SPREADS (Asian Handicap) =====
                            elif market_key == "spreads":
                                for outcome in outcomes:
                                    try:
                                        price = outcome.get("price", 0)
                                        outcome_name = outcome.get("name", "")
                                        point = outcome.get("point", 0)
                                        
                                        if not (odd_min <= price <= odd_max) or price <= 1:
                                            continue
                                        
                                        true_prob = 0.50
                                        value = calculate_value(true_prob, price, min_value)
                                        
                                        if value > min_value:
                                            market_display = f"Фора {point:+.1f}"
                                            analysis = get_bookmaker_analysis(bookmakers, outcome_name, "spreads")
                                            
                                            bet_details = {
                                                "value": value,
                                                "league": league,
                                                "match": match_name,
                                                "market": market_display,
                                                "price": price,
                                                "time": match_time_formatted,
                                                "match_id": match_id,
                                                "true_prob": true_prob,
                                                "implied_prob": 1 / price,
                                                "analysis": analysis,
                                                "market_type": "Spreads"
                                            }
                                            
                                            bets.append((
                                                value,
                                                league,
                                                match_name,
                                                market_display,
                                                price,
                                                match_time_formatted,
                                                match_id,
                                                bet_details
                                            ))
                                            
                                            seen_matches.add(match_key)
                                    
                                    except Exception as e:
                                        logger.debug(f"⚠️ Ошибка обработки spreads: {e}")
                                        continue
                    
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
    
    if not bets:
        logger.warning(
            "⚠️ Ставки не найдены. Возможные причины:\n"
            "  • API_KEY не установлен или невалиден\n"
            "  • Нет матчей в текущий момент (off-season)\n"
            "  • Коэффициенты вне диапазона 1.2-2.5\n"
            "  • Value недостаточно высокий (< 0.005)"
        )
    
    return bets[:12]


if __name__ == "__main__":
    print("🧪 Тестирование анализа матчей с OddsAPI...")
    results = analyze_matches()
    
    if results:
        print(f"\n✅ Найдено {len(results)} ставок:\n")
        for item in results[:5]:
            value, league, match, market, odd, time_str, match_id, details = item
            print(f"{league} | {match}")
            print(f"  {time_str} | {market} @ {odd:.2f}")
            print(f"  💰 Value: +{value:.4f}\n")
    else:
        print("❌ Ставки не найдены")
