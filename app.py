import time
import streamlit as st
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import (
    LeagueDashPlayerStats,
    LeagueDashPlayerShotLocations
)

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
    """Color FG% cells."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    v = float(val)
    if v < 0.30:
        return "background-color: #ff4d4d"
    if v < 0.40:
        return "background-color: #ffe066"
    return "background-color: #69db7c"

# -------------------------------
# NBA API RELIABILITY
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
# LOAD MAIN STATS
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
    for c in numeric_cols:
        if c in stats.columns:
            stats[c] = pd.to_numeric(stats[c], errors="coerce")

    return stats

# -------------------------------
# LOAD SHOT DATA
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
        "_".join(c) if isinstance(c, tuple) else c
        for c in df.columns
    ]

    for c in df.columns:
        if "FG" in c:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# -------------------------------
# PLAYER ZONE BREAKDOWN
# -------------------------------
def get_zones_for_player(player_name: str, shots_all: pd.DataFrame) -> pd.DataFrame:
    df = shots_all[shots_all["PLAYER_NAME"] == player_name]
    if df.empty:
        return pd.DataFrame()

    row = df.iloc[0]
    zones = {}

    for col, val in row.items():
        if not col.endswith(("FGM", "FGA", "FG_PCT")):
            continue

        zone = col.replace("_FGM", "").replace("_FGA", "").replace("_FG_PCT", "")
        rec = zones.setdefault(zone, {"zone": zone, "FGM":0,"FGA":0,"FG_PCT":np.nan})

        if col.endswith("FGM") and pd.notna(val):
            rec["FGM"] += val
        elif col.endswith("FGA") and pd.notna(val):
            rec["FGA"] += val
        elif col.endswith("FG_PCT"):
            rec["FG_PCT"] = val

    zp = pd.DataFrame(zones.values())
    zp = zp[zp["zone"] != "Backcourt"]

    zp["PTS"] = zp["FGM"] * np.where(zp["zone"].str.contains("3"),3,2)
    zp["PTS/shot"] = zp["PTS"] / zp["FGA"]
    zp["Shot Share"] = zp["FGA"] / zp["FGA"].sum()

    return zp

# -------------------------------
# LOAD DATA
# -------------------------------
stats_all = load_main_stats(TARGET_SEASON)
shots_all = load_shot_data(TARGET_SEASON)

# -------------------------------
# SIDEBAR FILTERS
# -------------------------------
teams = ["All"] + sorted(stats_all["TEAM_ABBREVIATION"].dropna().unique())
team_sel = st.sidebar.selectbox("Team", teams)

players = stats_all[
    stats_all["TEAM_ABBREVIATION"].eq(team_sel) | (team_sel == "All")
]["PLAYER_NAME"].unique()

player_sel = st.sidebar.selectbox("Player", sorted(players))

player_row = stats_all[stats_all["PLAYER_NAME"]==player_sel].iloc[0]

# -------------------------------
# MAIN VIEW
# -------------------------------
st.title("NBA Shooting – 2025‑26")

zones = get_zones_for_player(player_sel, shots_all)

styled = (
    zones.style
    .map(fg_color, subset=["FG_PCT"])
    .format({
        "FG_PCT": lambda v: f"{v*100:.0f}%",
        "Shot Share": lambda v: f"{v*100:.0f}%",
        "PTS": "{:.1f}",
        "PTS/shot": "{:.2f}"
    })
)

st.dataframe(styled, use_container_width=True)
``
