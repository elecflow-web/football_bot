import pandas as pd
import numpy as np

# ===== xG с учётом последних матчей =====
def weighted_xg(df, team, date):
    team_matches = df[(df['home_team']==team) | (df['away_team']==team)]
    team_matches = team_matches.sort_values("date", ascending=False).head(10)
    hxg = team_matches['home_xg'].mean() if not team_matches.empty else 1.2
    axg = team_matches['away_xg'].mean() if not team_matches.empty else 1.0
    return hxg, axg

# ===== усталость команды =====
def fatigue(xg, rest_factor):
    return xg * 0.95 if rest_factor < 3 else xg

# ===== вероятность через Poisson (приблизительно) =====
def probabilities(home_xg, away_xg):
    return 0.5  # Заглушка, можно заменить более точной моделью

# ===== Elo рейтинг =====
def calculate_elo(df):
    teams = pd.concat([df['home_team'], df['away_team']]).unique()
    elo = {team:1500 for team in teams}
    return elo
