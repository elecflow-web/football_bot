import pandas as pd
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOG_FILE = "bets_log.csv"


def log_bet(
    match: str,
    market: str,
    prob: float,
    odds: float,
    value: float,
    stake: float = 0,
    tracked: bool = True,
    result: str = None
) -> None:
    """
    Логирует ставку в CSV файл
    
    Args:
        match: Название матча (e.g., "Manchester City vs Liverpool")
        market: Тип рынка (e.g., "П1", "Over 2.5")
        prob: Рассчитанная вероятность (0-1)
        odds: Коэффициент
        value: Value bet (ожидаемый профит)
        stake: Размер ставки (опционально)
        tracked: Отслеживать ли эту ставку
        result: Результат (W/L/V - выигрыш/проигрыш/аннулирована)
    """
    
    try:
        row = {
            "timestamp": datetime.now().isoformat(),
            "match": match,
            "market": market,
            "probability": round(prob, 4),
            "odds": round(odds, 2),
            "value": round(value, 4),
            "stake": stake,
            "tracked": tracked,
            "result": result if result else "Pending",
        }
        
        # Читаем существующие ставки или создаём новый файл
        if os.path.exists(LOG_FILE):
            df = pd.read_csv(LOG_FILE)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])
        
        # Сохраняем в CSV
        df.to_csv(LOG_FILE, index=False)
        
        logger.info(f"✅ Логирована ставка: {match} | {market} @ {odds:.2f} | Value: {value:.4f}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при логировании ставки: {e}")


def get_statistics() -> dict:
    """
    Получить статистику по всем ставкам
    
    Returns:
        dict: Словарь со статистикой
    """
    
    try:
        if not os.path.exists(LOG_FILE):
            return {
                "total_bets": 0,
                "win_rate": 0,
                "avg_value": 0,
                "profit": 0,
                "roi": 0,
            }
        
        df = pd.read_csv(LOG_FILE)
        
        # Только отслеживаемые ставки
        tracked_df = df[df["tracked"] == True]
        
        total_bets = len(tracked_df)
        
        if total_bets == 0:
            return {
                "total_bets": 0,
                "win_rate": 0,
                "avg_value": 0,
                "profit": 0,
                "roi": 0,
            }
        
        # Количество выигрышей
        wins = len(tracked_df[tracked_df["result"] == "W"])
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        
        # Средний value
        avg_value = tracked_df["value"].mean()
        
        # Прибыль (упрощённо)
        profit = 0
        for idx, row in tracked_df.iterrows():
            if row["result"] == "W":
                profit += (row["odds"] - 1) * row["stake"]
            elif row["result"] == "L":
                profit -= row["stake"]
        
        # ROI
        total_stake = tracked_df["stake"].sum()
        roi = (profit / total_stake * 100) if total_stake > 0 else 0
        
        return {
            "total_bets": total_bets,
            "win_rate": round(win_rate, 2),
            "avg_value": round(avg_value, 4),
            "profit": round(profit, 2),
            "roi": round(roi, 2),
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка при расчёте статистики: {e}")
        return {
            "total_bets": 0,
            "win_rate": 0,
            "avg_value": 0,
            "profit": 0,
            "roi": 0,
        }


def get_recent_bets(limit: int = 10) -> list:
    """
    Получить последние N ставок
    
    Args:
        limit: Количество ставок для возврата
        
    Returns:
        list: Список последних ставок
    """
    
    try:
        if not os.path.exists(LOG_FILE):
            return []
        
        df = pd.read_csv(LOG_FILE)
        return df.tail(limit).to_dict("records")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении недавних ставок: {e}")
        return []


if __name__ == "__main__":
    # Тестирование
    print("🧪 Тестирование логирования ставок...")
    
    # Логируем несколько ставок
    log_bet("Manchester City vs Liverpool", "П1", 0.65, 1.85, 0.2025, stake=100)
    log_bet("Chelsea vs Arsenal", "Over 2.5", 0.58, 1.75, 0.015, stake=50)
    log_bet("Real Madrid vs Barcelona", "BTTS", 0.72, 1.90, 0.3680, stake=200)
    
    # Показываем статистику
    stats = get_statistics()
    print("\n📊 Статистика:")
    print(f"  Всего ставок: {stats['total_bets']}")
    print(f"  Win Rate: {stats['win_rate']}%")
    print(f"  Avg Value: {stats['avg_value']}")
    print(f"  Profit: {stats['profit']}")
    print(f"  ROI: {stats['roi']}%")
