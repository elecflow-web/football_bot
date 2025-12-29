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
    
    По документации OddsAPI:
    GET /v4/sports/{sport}/odds/?apiKey={apiKey}®ions={regions}&markets={markets}
    """
    if not API_KEY:
        return []
    
    try:
        logger.info(f"📊 Получаю матчи и коэффициенты для {league_name}...")
        
        url = f"{API_URL}/sports/{sport_key}/odds/"
        
        # Параметры согласно документации
        params = {
            "apiKey": API_KEY,
            "regions": REGIONS,
            "markets": "h2h,spreads,totals",  # Три основных рынка
            "oddsFormat": "decimal",  # Десятичные коэффициенты
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        # Логируем использование квоты
        if "x-requests-remaining" in response.headers:
            remaining = response.headers.get("x-requests-remaining")
            used = response.headers.get("x-requests-used")
            cost = response.headers.get("x-requests-last")
            logger.info(
                f"📊 API квота - Осталось: {remaining}, "
                f"Использовано: {used}, Стоимость запроса: {cost}"
            )
        
        if response.status_code == 200:
            matches = response.json()
            
            if not matches:
                logger.warning(f"⚠️ Нет матчей для {league_name}")
                return []
            
            logger.info(f"✅ Получено {len(matches)} матчей для {league_name}")
            
            # Добавляем название лиги в каждый матч
            for match in matches:
                match["league"] = league_name
            
            return matches
        else:
            logger.error(
                f"❌ Ошибка API для {league_name} "
                f"(статус {response.status_code}): {response.text}"
            )
            return []
    
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout при получении матчей для {league_name}")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчей для {league_name}: {e}")
        return []


def calculate_value(true_probability: float, odds: float, min_value: float = 0.01) -> float:
    """
    Рассчитать value bet
    Value = (Вероятность × Коэффициент) - 1
    
    Положительное значение = математическое преимущество
    """
    if odds <= 0:
        return 0
    
    return (true_probability * odds) - 1


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
        # Получаем матчи со всех лиг
        all_matches = []
        
        for sport_key, league_name in SOCCER_SPORTS.items():
            matches = get_odds_for_sport(sport_key, league_name)
            all_matches.extend(matches)
        
        if not all_matches:
            logger.warning("⚠️ Матчи не получены ни из одной лиги")
            return []
        
        logger.info(f"🎯 Всего получено матчей: {len(all_matches)}")
        
        # Анализируем каждый матч
        for match in all_matches:
            try:
                league = match.get("league", "Unknown")
                home_team = match.get("home_team", "Home")
                away_team = match.get("away_team", "Away")
                match_name = f"{home_team} vs {away_team}"
                
                bookmakers = match.get("bookmakers", [])
                
                if not bookmakers:
                    continue
                
                # Анализируем коэффициенты от разных букмекеров
                for bookmaker in bookmakers:
                    try:
                        bookmaker_name = bookmaker.get("title", "Unknown")
                        markets = bookmaker.get("markets", [])
                        
                        for market in markets:
                            market_key = market.get("key", "")
                            outcomes = market.get("outcomes", [])
                            
                            # ===== H2H (1X2 / Moneyline) =====
                            if market_key == "h2h":
                                for outcome in outcomes:
                                    try:
                                        price = outcome.get("price", 0)
                                        outcome_name = outcome.get("name", "")
                                        
                                        # Фильтр по диапазону коэффициентов
                                        if not (odd_min <= price <= odd_max) or price <= 1:
                                            continue
                                        
                                        # Вероятность на основе коэффициента букмекера
                                        bookmaker_prob = 1 / price
                                        
                                        # Упрощённая модель: предполагаем 52% для домашних, 48% для гостей
                                        if outcome_name == home_team:
                                            true_prob = 0.52
                                            market_display = f"П1 ({home_team})"
                                        elif outcome_name == away_team:
                                            true_prob = 0.48
                                            market_display = f"П2 ({away_team})"
                                        else:
                                            continue
                                        
                                        # Рассчитываем value
                                        value = calculate_value(true_prob, price, min_value)
                                        
                                        if value > min_value:
                                            bets.append((
                                                value,
                                                league,
                                                match_name,
                                                market_display,
                                                price
                                            ))
                                            logger.debug(
                                                f"✅ Найдена ставка: {match_name} | "
                                                f"{market_display} @ {price:.2f} | "
                                                f"Value: {value:.4f} ({bookmaker_name})"
                                            )
                                    
                                    except Exception as e:
                                        logger.debug(f"⚠️ Ошибка обработки исхода H2H: {e}")
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
                                        
                                        # Упрощённо: Over = 48%, Under = 52%
                                        if "Over" in outcome_name:
                                            true_prob = 0.48
                                        else:
                                            true_prob = 0.52
                                        
                                        value = calculate_value(true_prob, price, min_value)
                                        
                                        if value > min_value:
                                            market_display = f"{outcome_name} {point:.1f}"
                                            
                                            bets.append((
                                                value,
                                                league,
                                                match_name,
                                                market_display,
                                                price
                                            ))
                                            logger.debug(
                                                f"✅ Найдена ставка: {match_name} | "
                                                f"{market_display} @ {price:.2f} | "
                                                f"Value: {value:.4f}"
                                            )
                                    
                                    except Exception as e:
                                        logger.debug(f"⚠️ Ошибка обработки исхода Totals: {e}")
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
                                        
                                        true_prob = 0.50  # Консервативно
                                        value = calculate_value(true_prob, price, min_value)
                                        
                                        if value > min_value:
                                            market_display = f"Фора {point:+.1f}"
                                            
                                            bets.append((
                                                value,
                                                league,
                                                match_name,
                                                market_display,
                                                price
                                            ))
                                    
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
            "  • Коэффициенты вне диапазона 1.3-1.9\n"
            "  • Value недостаточно высокий (< 0.01)"
        )
    
    # Возвращаем топ-12 ставок
    return bets[:12]


if __name__ == "__main__":
    # Тестирование
    print("🧪 Тестирование анализа матчей с OddsAPI...")
    results = analyze_matches()
    
    if results:
        print(f"\n✅ Найдено {len(results)} ставок:\n")
        for value, league, match, market, odd in results[:10]:
            print(f"{league}")
            print(f"  {match}")
            print(f"  {market} @ {odd:.2f}")
            print(f"  💰 Value: {value:.4f}\n")
    else:
        print("❌ Ставки не найдены")
        print("Проверьте:")
        print("  1. SPORTS_API_KEY установлен в переменных окружения")
        print("  2. Доступ в интернет")
        print("  3. OddsAPI квота не исчерпана")
