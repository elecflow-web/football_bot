import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Файл для хранения логов
BETS_LOG_FILE = "bets.log"


def log_bet(match: str, market: str, value: float, odd: float, confidence: float):
    """
    Логирует ставку в файл и консоль
    
    Args:
        match: Название матча (например, "Manchester City vs Chelsea")
        market: Тип рынка (например, "П1" или "Over 2.5")
        value: Value bet (преимущество)
        odd: Коэффициент
        confidence: Уверенность в ставке (0-1)
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"[{timestamp}] {match} | {market} @ {odd:.2f} | Value: {value:.4f} | Confidence: {confidence:.2f}\n"
        
        # Логируем в файл
        with open(BETS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Логируем в консоль
        logger.info(f"✅ Логирована ставка: {match} | {market} @ {odd:.2f} | Value: {value:.4f}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка логирования ставки: {e}")


def get_logged_bets(limit: int = 10) -> list:
    """Получает последние логированные ставки"""
    try:
        if not os.path.exists(BETS_LOG_FILE):
            return []
        
        with open(BETS_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        return lines[-limit:]
    except Exception as e:
        logger.error(f"❌ Ошибка чтения логов: {e}")
        return []


def clear_logs():
    """Очищает файл логов"""
    try:
        if os.path.exists(BETS_LOG_FILE):
            os.remove(BETS_LOG_FILE)
            logger.info("✅ Логи очищены")
    except Exception as e:
        logger.error(f"❌ Ошибка очистки логов: {e}")
