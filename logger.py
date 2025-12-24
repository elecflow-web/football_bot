import pandas as pd
import os
from datetime import datetime

LOG_FILE = "bets_log.csv"

def log_bet(match, market, prob, odds, value, stake=0, tracked=True, result=None):
    row = {
        "timestamp": datetime.now(),
        "match": match,
        "market": market,
        "probability": round(prob,4),
        "odds": odds,
        "value": round(value,4),
        "stake": stake,
        "tracked": tracked,
        "result": result
    }

    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(LOG_FILE, index=False)
