import os
import requests
import logging
from typing import List, Tuple, Dict
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API конфиг для OddsAPI
API_KEY = os.environ.get("SPORTS_API_KEY")
API_URL = "https://api.the-odds-api.com/v4"

# Все футбольные лиги
SOCCER_SPORTS = {
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Английская Премьер-лига",
    "soccer_spain_la_liga": "🇪🇸 Испанская Ла Лига",
    "soccer_germany_bundesliga": "🇩🇪 Немецкая Бундеслига",
    "soccer_italy_serie_a": "🇮🇹 Итальянская Серия А",
    "soccer_france_ligue_one": "🇫🇷 Французская Лига 1",
    "soccer_portugal_primeira_liga": "🇵🇹 Португальская Примейра Лига",
    "soccer_netherlands_eredivisie": "🇳🇱 Голландская Эредивизи",
    "soccer_uefa_champs_league": "🏆 Лига чемпионов",
    "soccer_usa_mls": "🇺🇸 MLS (США)",
    "soccer_england_league_championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Английская Чемпионшип",
    "soccer_italy_serie_b": "🇮🇹 Итальянская Серия Б",
    "soccer_germany_2_bundesliga": "🇩🇪 Немецкая Бундеслига 2",
}

# Регионы
REGIONS = "uk,eu"

# Все рынки для анализа
ALL_MARKETS = "h2h,spreads,totals"

if not API_KEY:
    logger.warning("⚠️ SPORTS_API_KEY не установлен!")


def get_odds_for_sport(sport_key: str, league_name: str) -> List[dict]:
    """Получить матчи и коэффициенты для лиги"""
    if not API_KEY:
        return []
    
    try:
        logger.info(f"📊 Получаю матчи для {league_name}...")
        
        url = f"{API_URL}/sports/{sport_key}/odds/"
        params = {
            "apiKey": API_KEY,
            "regions": REGIONS,
            "markets": ALL_MARKETS,
            "oddsFormat": "decimal",
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if "x-requests-remaining" in response.headers:
            remaining = response.headers.get("x-requests-remaining")
            logger.debug(f"📊 API квота: {remaining}")
        
        if response.status_code == 200:
            matches = response.json()
            
            if not matches:
                logger.warning(f"⚠️ Нет матчей для {league_name}")
                return []
            
            logger.info(f"✅ {league_name}: {len(matches)} матчей")
            
            for match in matches:
                match["league"] = league_name
                match["sport_key"] = sport_key
            
            return matches
        else:
            logger.error(f"❌ {league_name}: статус {response.status_code}")
            return []
    
    except Exception as e:
        logger.error(f"❌ Ошибка {league_name}: {e}")
        return []


def format_match_time(commence_time_str: str) -> str:
    """Форматирует время матча"""
    try:
        dt = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
        moscow_tz = datetime.fromisoformat("2000-01-01+03:00").tzinfo
        dt_moscow = dt.astimezone(moscow_tz)
        return dt_moscow.strftime("%d.%m %H:%M")
    except:
        return "?"


def estimate_true_probability(market_key: str, outcome_name: str, home_team: str, 
                              away_team: str, bookmakers_data: list) -> float:
    """
    Расчитывает истинную вероятность на основе коэффициентов букмекеров.
    Используется логика букмекера: самые низкие коэффициенты = самые вероятные исходы.
    """
    
    # Собираем все коэффициенты для этого исхода
    prices = []
    
    for bookmaker in bookmakers_data:
        try:
            for market in bookmaker.get("markets", []):
                if market.get("key") != market_key:
                    continue
                
                for outcome in market.get("outcomes", []):
                    if outcome.get("name") == outcome_name:
                        price = outcome.get("price", 0)
                        if price > 1:
                            prices.append(price)
        except:
            pass
    
    if not prices:
        return 0.5
    
    # Средний коэффициент букмекеров
    avg_price = sum(prices) / len(prices)
    
    # Вероятность = 1 / средний коэффициент
    true_prob = 1 / avg_price
    
    # Нормализуем (букмекеры закладывают маржу ~5-10%)
    true_prob = min(true_prob * 1.05, 0.99)
    
    return true_prob


def get_bookmaker_stats(bookmakers: list, outcome_name: str, market_key: str) -> Dict:
    """Анализирует коэффициенты от разных букмекеров"""
    prices = []
    bookmaker_names = []
    
    for bookmaker in bookmakers:
        try:
            for market in bookmaker.get("markets", []):
                if market.get("key") != market_key:
                    continue
                
                for outcome in market.get("outcomes", []):
                    if outcome.get("name") == outcome_name:
                        price = outcome.get("price", 0)
                        if price > 0:
                            prices.append(price)
                            bookmaker_names.append(bookmaker.get("title", "Unknown"))
        except:
            pass
    
    if not prices:
        return {"best": 0, "worst": 0, "avg": 0, "count": 0, "spread": 0}
    
    return {
        "best": max(prices),
        "worst": min(prices),
        "avg": sum(prices) / len(prices),
        "count": len(prices),
        "spread": max(prices) - min(prices),
        "top_books": bookmaker_names[:5]
    }


def calculate_value(true_prob: float, odds: float) -> float:
    """Value bet = (P × O) - 1"""
    if odds <= 1:
        return 0
    return (true_prob * odds) - 1


def analyze_matches(
    min_value: float = 0.025,  # Более высокий порог для качества
    odd_min: float = 1.3,
    odd_max: float = 3.5
) -> List[Tuple]:
    """
    Мощный анализ матчей как жадный букмекер.
    Возвращает только HIGH-VALUE ставки.
    """
    
    bets = []
    seen_bets = set()  # Исключение дубликатов
    
    try:
        # Получаем матчи со всех лиг
        all_matches = []
        leagues_used = defaultdict(int)
        
        for sport_key, league_name in SOCCER_SPORTS.items():
            matches = get_odds_for_sport(sport_key, league_name)
            all_matches.extend(matches)
            if matches:
                leagues_used[league_name] = len(matches)
        
        if not all_matches:
            logger.warning("⚠️ Матчи не получены")
            return []
        
        logger.info(f"🎯 Всего матчей: {len(all_matches)}")
        logger.info(f"📍 Использованные лиги:")
        for league, count in sorted(leagues_used.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   {league}: {count}")
        
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
                
                bookmakers = match.get("bookmakers", [])
                if not bookmakers:
                    continue
                
                # Анализируем каждый рынок
                for bookmaker in bookmakers:
                    try:
                        for market in bookmaker.get("markets", []):
                            market_key = market.get("key", "")
                            outcomes = market.get("outcomes", [])
                            
                            for outcome in outcomes:
                                try:
                                    price = outcome.get("price", 0)
                                    outcome_name = outcome.get("name", "")
                                    point = outcome.get("point", 0)
                                    
                                    # Фильтр по коэффициентам
                                    if not (odd_min <= price <= odd_max) or price <= 1:
                                        continue
                                    
                                    # Определяем вероятность на основе букмекерских данных
                                    true_prob = estimate_true_probability(
                                        market_key, outcome_name, home_team, away_team, bookmakers
                                    )
                                    
                                    if true_prob <= 0:
                                        continue
                                    
                                    # Рассчитываем value
                                    value = calculate_value(true_prob, price)
                                    
                                    # АГРЕССИВНЫЙ фильтр: только качественные ставки
                                    if value <= min_value:
                                        continue
                                    
                                    # Определяем название рынка и исход
                                    market_display = ""
                                    
                                    if market_key == "h2h":
                                        if outcome_name == home_team:
                                            market_display = f"П1 ({home_team})"
                                        elif outcome_name == away_team:
                                            market_display = f"П2 ({away_team})"
                                        elif outcome_name == "Draw":
                                            market_display = "X (Ничья)"
                                        else:
                                            continue
                                    
                                    elif market_key == "totals":
                                        market_display = f"{outcome_name}"
                                    
                                    elif market_key == "spreads":
                                        market_display = f"Фора {point:+.1f}"
                                    
                                    else:
                                        continue
                                    
                                    # Уникальный ключ: матч + рынок + точный коэффициент
                                    bet_key = f"{match_id}_{market_key}_{outcome_name}_{price:.2f}"
                                    
                                    if bet_key in seen_bets:
                                        continue
                                    
                                    seen_bets.add(bet_key)
                                    
                                    # Получаем статистику букмекеров
                                    stats = get_bookmaker_stats(bookmakers, outcome_name, market_key)
                                    
                                    bet_details = {
                                        "value": value,
                                        "league": league,
                                        "match": match_name,
                                        "market": market_display,
                                        "market_type": market_key,
                                        "price": price,
                                        "time": match_time_formatted,
                                        "match_id": match_id,
                                        "true_prob": true_prob,
                                        "implied_prob": 1 / price,
                                        "stats": stats,
                                        "outcome_name": outcome_name,
                                        "point": point,
                                        "roi": (value * 100)  # ROI в процентах
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
                                
                                except Exception as e:
                                    logger.debug(f"⚠️ Ошибка обработки исхода: {e}")
                                    continue
                    
                    except Exception as e:
                        logger.debug(f"⚠️ Ошибка обработки рынка: {e}")
                        continue
            
            except Exception as e:
                logger.debug(f"⚠️ Ошибка обработки матча: {e}")
                continue
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
    
    # Сортируем по value (убывание)
    bets.sort(reverse=True, key=lambda x: x[0])
    
    logger.info(f"🎯 Найдено качественных ставок: {len(bets)}")
    
    if not bets:
        logger.warning("⚠️ Value-ставки не найдены (порог value > 0.025)")
    
    return bets[:20]  # Топ-20 вместо топ-12


if __name__ == "__main__":
    print("🧪 Тестирование профессионального анализа...")
    results = analyze_matches()
    
    if results:
        print(f"\n✅ Найдено {len(results)} QUALITY ставок:\n")
        for item in results[:10]:
            value, league, match, market, odd, time_str, match_id, details = item
            roi = details.get("roi", 0)
            stats = details.get("stats", {})
            true_prob = details.get("true_prob", 0)
            
            print(f"{league} | {match}")
            print(f"  {time_str} | {market} @ {odd:.2f}")
            print(f"  💰 Value: +{value:.4f} (ROI: {roi:.2f}%)")
            print(f"  📊 Букмекеров: {stats.get('count', 0)} | Спред: {stats.get('spread', 0):.2f}")
            print(f"  🎯 Вероятность: {true_prob*100:.1f}% vs Котировка: {(1/odd)*100:.1f}%\n")
    else:
        print("❌ Качественные ставки не найдены")
