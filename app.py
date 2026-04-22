import time
import streamlit as st
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueDashPlayerShotLocations

# -------------------------------
# SETTINGS
# -------------------------------
TARGET_SEASON = "2025-26"
SEASON_LABEL = "2025-26 Regular Season"

CACHE_TTL_SECONDS = 300

st.set_page_config(
    page_title="NBA Shooting – NBA.com 2025-26",
    layout="wide"
)

# -------------------------------
# SIDEBAR: FORCE REFRESH BUTTON
# -------------------------------
with st.sidebar:
    if st.button(" Refresh data now (pull latest)"):
        st.cache_data.clear()
        st.rerun()

# -------------------------------
# TEAM LOGOS + HEADSHOTS
# -------------------------------
TEAM_LOGOS = {
    "ATL": "https://cdn.nba.com/logos/nba/1610612737/primary/L/logo.svg",
    "BOS": "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg",
    "BKN": "https://cdn.nba.com/logos/nba/1610612751/primary/L/logo.svg",
    "CHA": "https://cdn.nba.com/logos/nba/1610612766/primary/L/logo.svg",
    "CHI": "https://cdn.nba.com/logos/nba/1610612741/primary/L/logo.svg",
    "CLE": "https://cdn.nba.com/logos/nba/1610612739/primary/L/logo.svg",
    "DAL": "https://cdn.nba.com/logos/nba/1610612742/primary/L/logo.svg",
    "DEN": "https://cdn.nba.com/logos/nba/1610612743/primary/L/logo.svg",
    "DET": "https://cdn.nba.com/logos/nba/1610612765/primary/L/logo.svg",
    "GSW": "https://cdn.nba.com/logos/nba/1610612744/primary/L/logo.svg",
    "HOU": "https://cdn.nba.com/logos/nba/1610612745/primary/L/logo.svg",
    "IND": "https://cdn.nba.com/logos/nba/1610612754/primary/L/logo.svg",
    "LAC": "https://cdn.nba.com/logos/nba/1610612746/primary/L/logo.svg",
    "LAL": "https://cdn.nba.com/logos/nba/1610612747/primary/L/logo.svg",
    "MEM": "https://cdn.nba.com/logos/nba/1610612763/primary/L/logo.svg",
    "MIA": "https://cdn.nba.com/logos/nba/1610612748/primary/L/logo.svg",
    "MIL": "https://cdn.nba.com/logos/nba/1610612749/primary/L/logo.svg",
    "MIN": "https://cdn.nba.com/logos/nba/1610612750/primary/L/logo.svg",
    "NOP": "https://cdn.nba.com/logos/nba/1610612740/primary/L/logo.svg",
    "NYK": "https://cdn.nba.com/logos/nba/1610612752/primary/L/logo.svg",
    "OKC": "https://cdn.nba.com/logos/nba/1610612760/primary/L/logo.svg",
    "ORL": "https://cdn.nba.com/logos/nba/1610612753/primary/L/logo.svg",
    "PHI": "https://cdn.nba.com/logos/nba/1610612755/primary/L/logo.svg",
    "PHX": "https://cdn.nba.com/logos/nba/1610612756/primary/L/logo.svg",
    "POR": "https://cdn.nba.com/logos/nba/1610612757/primary/L/logo.svg",
    "SAC": "https://cdn.nba.com/logos/nba/1610612758/primary/L/logo.svg",
    "SAS": "https://cdn.nba.com/logos/nba/1610612759/primary/L/logo.svg",
    "TOR": "https://cdn.nba.com/logos/nba/1610612761/primary/L/logo.svg",
    "UTA": "https://cdn.nba.com/logos/nba/1610612762/primary/L/logo.svg",
    "WAS": "https://cdn.nba.com/logos/nba/1610612764/primary/L/logo.svg",
}

def get_team_logo(team):
    return TEAM_LOGOS.get(team, "")

def get_headshot(player_id: int):
    return f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png"

def fg_color(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    v = float(val)
    if v < 0.30:
        return "background-color: #ff4d4d"
    if v < 0.40:
        return "background-color: #ffe066"
    return "background-color: #69db7c"

# -------------------------------
# NBA API RELIABILITY (RETRIES)
# -------------------------------
def nba_call_with_retries(fn, tries=3, base_sleep=1.5):
    last_err = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            time.sleep(base_sleep * (i + 1))
    raise last_err

# -------------------------------
# LOAD MAIN STATS (PER GAME)
# -------------------------------
@st.cache_data(show_spinner=True, ttl=CACHE_TTL_SECONDS)
def load_main_stats(season: str) -> pd.DataFrame:
    def _call():
        return LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame"
        ).get_data_frames()[0]

    stats = nba_call_with_retries(_call)

    numeric_cols = [
        "GP","MIN","FGM","FGA","FG_PCT",
        "FG3M","FG3A","FG3_PCT",
        "FTM","FTA","FT_PCT","PTS"
    ]
    for col in numeric_cols:
        if col in stats.columns:
            stats[col] = pd.to_numeric(stats[col], errors="coerce")

    return stats

# -------------------------------
# LOAD SHOT DATA (BY ZONE)
# -------------------------------
@st.cache_data(show_spinner=True, ttl=CACHE_TTL_SECONDS)
def load_shot_data(season: str) -> pd.DataFrame:
    def _call():
        return LeagueDashPlayerShotLocations(
            season=season,
            season_type_all_star="Regular Season",
            distance_range="By Zone",
            per_mode_detailed="PerGame"
        ).get_data_frames()[0]

    df = nba_call_with_retries(_call)

    df.columns = [
        "_".join([str(x) for x in c if x]) if isinstance(c, tuple) else str(c)
        for c in df.columns
    ]

    for c in df.columns:
        if "FG" in c:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# -------------------------------
# ZONE BREAKDOWN TAB
# -------------------------------
styled = (
    df_zone.style
    .map(fg_color, subset=["FG%"])   # ✅ FIXED LINE
    .format({
        "FGM": lambda v: "" if pd.isna(v) else f"{v:.1f}",
        "FGA": lambda v: "" if pd.isna(v) else f"{v:.1f}",
        "PTS/shot": lambda v: "" if pd.isna(v) else f"{v:.2f}",
        "PTS": lambda v: "" if pd.isna(v) else f"{v:.1f}",
        "FG%": lambda v: "" if pd.isna(v) else f"{int(round(v * 100))}%",
        "Shot Share": lambda v: "" if pd.isna(v) else f"{int(round(v * 100))}%",
        "FTM": lambda v: "" if pd.isna(v) else f"{v:.1f}",
        "FTA": lambda v: "" if pd.isna(v) else f"{v:.1f}",
        "FT%": lambda v: "" if pd.isna(v) else f"{int(round(v * 100))}%",
    })
)

st.dataframe(styled, use_container_width=True)

st.dataframe(styled, use_container_width=True)
``
