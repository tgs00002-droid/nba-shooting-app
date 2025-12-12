import streamlit as st
st.set_page_config(page_title="NBA Shooting – NBA.com", layout="wide")  # MUST BE FIRST st.* CALL

import pandas as pd
import numpy as np
import datetime as dt
import time
import random

from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueDashPlayerShotLocations

# -------------------------------
# NBA.com REQUEST HEADERS
# -------------------------------
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept-Language": "en-US,en;q=0.9",
}

SEASON_TYPE = "Regular Season"

def _pause():
    time.sleep(0.35 + random.random() * 0.45)

def with_retry(fn, tries=3, base_sleep=1.0):
    last_err = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            time.sleep(base_sleep * (i + 1))
    raise last_err

def season_str_from_year(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"

def candidate_seasons_latest_first(n_back: int = 8):
    today = dt.date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return [season_str_from_year(start_year - i) for i in range(n_back)]

@st.cache_data(ttl=60 * 30, show_spinner=False)  # refresh every 30 min
def detect_latest_season() -> str:
    for s in candidate_seasons_latest_first():
        try:
            _pause()
            df = LeagueDashPlayerStats(
                season=s,
                season_type_all_star=SEASON_TYPE,
                per_mode_detailed="Totals",
                headers=NBA_HEADERS,
                timeout=30,
            ).get_data_frames()[0]
            if df is not None and len(df) > 0:
                return s
        except Exception:
            continue
    return candidate_seasons_latest_first()[-1]

TARGET_SEASON = detect_latest_season()
SEASON_LABEL = f"{TARGET_SEASON} {SEASON_TYPE}"

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
    return f"https://cdn.nba.com/headshots/nba/latest/260x190/{int(player_id)}.png"

def fg_color(val):
    if pd.isna(val):
        return ""
    if val < 0.30:
        return "background-color: red"
    if val < 0.40:
        return "background-color: yellow"
    return "background-color: green"

# -------------------------------
# LOAD MAIN STATS (TOTALS -> PER GAME)
# -------------------------------
@st.cache_data(show_spinner=True, ttl=60 * 30)
def load_main_stats(season: str) -> pd.DataFrame:
    def _call():
        _pause()
        return LeagueDashPlayerStats(
            season=season,
            season_type_all_star=SEASON_TYPE,
            per_mode_detailed="Totals",
            headers=NBA_HEADERS,
            timeout=30,
        ).get_data_frames()[0]

    stats = with_retry(_call, tries=3)

    num_cols = ["GP","MIN","FGM","FGA","FG3M","FG3A","FTM","FTA","PTS"]
    for c in num_cols:
        if c in stats.columns:
            stats[c] = pd.to_numeric(stats[c], errors="coerce")

    # compute % from totals
    stats["FG_PCT"]  = np.where(stats["FGA"]  > 0, stats["FGM"]  / stats["FGA"],  np.nan)
    stats["FG3_PCT"] = np.where(stats["FG3A"] > 0, stats["FG3M"] / stats["FG3A"], np.nan)
    stats["FT_PCT"]  = np.where(stats["FTA"]  > 0, stats["FTM"]  / stats["FTA"],  np.nan)

    # convert totals -> per game (for header + team table)
    stats["PTS"] = np.where(stats["GP"] > 0, stats["PTS"] / stats["GP"], np.nan)
    stats["MIN"] = np.where(stats["GP"] > 0, stats["MIN"] / stats["GP"], np.nan)

    return stats

# -------------------------------
# LOAD SHOT DATA (BY ZONE) – LEAGUE-WIDE
# -------------------------------
@st.cache_data(show_spinner=True, ttl=60 * 30)
def load_shot_data(season: str) -> pd.DataFrame:
    def _call():
        _pause()
        return LeagueDashPlayerShotLocations(
            season=season,
            season_type_all_star=SEASON_TYPE,
            distance_range="By Zone",
            per_mode_detailed="PerGame",
            headers=NBA_HEADERS,
            timeout=30,
        ).get_data_frames()[0]

    df = with_retry(_call, tries=3)

    # flatten tuple / MultiIndex columns
    flat_cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            flat_cols.append("_".join([str(x) for x in c if x]))
        else:
            flat_cols.append(str(c))
    df.columns = flat_cols

    for c in df.columns:
        if "FGM" in c or "FGA" in c or "FG_PCT" in c:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# -------------------------------
# ZONE BREAKDOWN FOR ONE PLAYER
# -------------------------------
def get_zones_for_player(player_name: str, shots_all: pd.DataFrame) -> pd.DataFrame:
    if "PLAYER_NAME" not in shots_all.columns:
        return pd.DataFrame()

    df = shots_all[shots_all["PLAYER_NAME"] == player_name]
    if df.empty:
        return pd.DataFrame()

    row = df.iloc[0]
    shot_cols = [c for c in df.columns if c.endswith("_FGM") or c.endswith("_FGA") or c.endswith("_FG_PCT")]

    zone_records = {}
    for col in shot_cols:
        val = row[col]

        if col.endswith("_FG_PCT"):
            zone = col.replace("_FG_PCT", "")
            metric = "FG_PCT"
        elif col.endswith("_FGM"):
            zone = col.replace("_FGM", "")
            metric = "FGM"
        else:
            zone = col.replace("_FGA", "")
            metric = "FGA"

        rec = zone_records.setdefault(zone, {"zone": zone, "FGM": 0.0, "FGA": 0.0, "FG_PCT": np.nan})

        if metric in ["FGM", "FGA"] and pd.notna(val):
            rec[metric] += float(val)
        elif metric == "FG_PCT" and pd.notna(val):
            # keep it but we'll recompute FG% from FGM/FGA below to avoid 0-attempt zones showing 0%
            rec["FG_PCT"] = float(val)

    zp = pd.DataFrame(zone_records.values())
    zp = zp[zp["zone"] != "Backcourt"].copy()

    # IMPORTANT: recompute FG% so zones with FGA=0 become NA
    zp["FG_PCT"] = np.where(zp["FGA"] > 0, zp["FGM"] / zp["FGA"], np.nan)

    zp["pts_val"] = np.where(zp["zone"].str.contains("3"), 3, 2)
    zp["PTS"] = zp["FGM"] * zp["pts_val"]
    zp["PTS_per_shot"] = np.where(zp["FGA"] > 0, zp["PTS"] / zp["FGA"], np.nan)

    total_fga = zp["FGA"].sum()
    zp["Shot Share"] = np.where(total_fga > 0, zp["FGA"] / total_fga, np.nan)

    return zp

# -------------------------------
# LOAD DATA
# -------------------------------
stats_all = load_main_stats(TARGET_SEASON)
shots_all = load_shot_data(TARGET_SEASON)

# -------------------------------
# SIDEBAR
# -------------------------------
with st.sidebar:
    st.subheader("Filters")

    if st.button("Refresh now"):
        st.cache_data.clear()
        st.rerun()

    st.write(f"Season: **{TARGET_SEASON}**")

    teams = ["All"] + sorted(stats_all["TEAM_ABBREVIATION"].dropna().unique())
    team_sel = st.selectbox("Choose a team:", teams)

    if team_sel != "All":
        logo_url_sb = get_team_logo(team_sel)
        if logo_url_sb:
            st.image(logo_url_sb, width=70)

    if team_sel == "All":
        players = sorted(stats_all["PLAYER_NAME"].dropna().unique())
    else:
        players = sorted(stats_all[stats_all["TEAM_ABBREVIATION"] == team_sel]["PLAYER_NAME"].dropna().unique())

    player_sel = st.selectbox("Choose a player:", players)

    st.markdown("---")
    st.write("Stats: LeagueDashPlayerStats (Totals → Per Game)")
    st.write("Zones: LeagueDashPlayerShotLocations (By Zone)")
    st.write(SEASON_LABEL)

# -------------------------------
# PLAYER HEADER
# -------------------------------
p_rows = stats_all[stats_all["PLAYER_NAME"] == player_sel]
if not p_rows.empty:
    player_row = p_rows.iloc[0]
else:
    st.error("Player not found in stats feed.")
    st.stop()

st.title(f"NBA Shooting – NBA.com {TARGET_SEASON}")

col1, col2 = st.columns([1, 4])

with col1:
    st.image(get_headshot(player_row["PLAYER_ID"]), width=170)
    logo_url = get_team_logo(player_row["TEAM_ABBREVIATION"])
    if logo_url:
        st.image(logo_url, width=90)

with col2:
    st.subheader(f"{player_sel} ({player_row['TEAM_ABBREVIATION']}) – {SEASON_LABEL}")
    st.write(
        f"GP: **{int(player_row['GP'])}**  |  "
        f"PTS: **{player_row['PTS']:.1f}** per game  |  "
        f"FG%: **{player_row['FG_PCT']*100:.1f}%**  |  "
        f"3P%: **{player_row['FG3_PCT']*100:.1f}%**  |  "
        f"FT%: **{player_row['FT_PCT']*100:.1f}%**"
    )
    st.caption("FG% color bands: Red < 30%, Yellow 30–40%, Green > 40%")

st.markdown("---")

# -------------------------------
# TABS
# -------------------------------
tab1, tab2 = st.tabs(["Zone breakdown", "Team overview"])

# ----- TAB 1: ZONE BREAKDOWN -----
with tab1:
    zp = get_zones_for_player(player_sel, shots_all)

    if zp.empty:
        st.error("No zone data available for this player.")
    else:
        df_zone = zp.copy()
        df_zone["Zone"] = (
            df_zone["zone"]
            .str.replace("_", " ", regex=False)
            .str.replace("Non RA", "(Non-RA)", regex=False)
        )

        df_zone = df_zone[["Zone", "FGM", "FGA", "PTS_per_shot", "FG_PCT", "PTS", "Shot Share"]].copy()
        df_zone.rename(columns={"PTS_per_shot": "PTS/shot", "FG_PCT": "FG%"}, inplace=True)

        # FT columns (blank for zone rows)
        df_zone["FTM"] = np.nan
        df_zone["FTA"] = np.nan
        df_zone["FT%"] = np.nan

        # Add Free Throw row from player totals-derived % (still accurate)
        ft_row = {
            "Zone": "Free Throw",
            "FGM": np.nan,
            "FGA": np.nan,
            "PTS/shot": np.nan,
            "FG%": np.nan,
            "PTS": np.nan,
            "Shot Share": np.nan,
            "FTM": player_row["FTM"] / player_row["GP"] if player_row["GP"] > 0 else np.nan,
            "FTA": player_row["FTA"] / player_row["GP"] if player_row["GP"] > 0 else np.nan,
            "FT%": player_row["FT_PCT"],
        }
        df_zone = pd.concat([df_zone, pd.DataFrame([ft_row])], ignore_index=True)

        df_zone = df_zone.replace({None: np.nan})

        df_zone = df_zone[[
            "Zone", "FGM", "FGA", "PTS/shot", "FG%", "PTS", "Shot Share",
            "FTM", "FTA", "FT%"
        ]]

        styled = (
            df_zone.style
            .applymap(fg_color, subset=["FG%"])
            .format({
                "FGM": lambda v: "" if pd.isna(v) else f"{v:.1f}",
                "FGA": lambda v: "" if pd.isna(v) else f"{v:.1f}",
                "PTS/shot": lambda v: "" if pd.isna(v) else f"{v:.1f}",
                "PTS": lambda v: "" if pd.isna(v) else f"{v:.1f}",
                "FG%": lambda v: "" if pd.isna(v) else f"{int(round(v * 100))}%",
                "Shot Share": lambda v: "" if pd.isna(v) else f"{int(round(v * 100))}%",
                "FTM": lambda v: "" if pd.isna(v) else f"{v:.1f}",
                "FTA": lambda v: "" if pd.isna(v) else f"{v:.1f}",
                "FT%": lambda v: "" if pd.isna(v) else f"{int(round(v * 100))}%",
            })
        )

        st.dataframe(styled, use_container_width=True)

# ----- TAB 2: TEAM OVERVIEW -----
with tab2:
    if team_sel == "All":
        team_df = stats_all.copy()
    else:
        team_df = stats_all[stats_all["TEAM_ABBREVIATION"] == team_sel].copy()

    team_df = team_df.sort_values("PTS", ascending=False)

    logos = [
        f'<img src="{get_team_logo(t)}" height="28">' if get_team_logo(t) else ""
        for t in team_df["TEAM_ABBREVIATION"]
    ]

    df_out = pd.DataFrame({
        "Logo": logos,
        "Player": team_df["PLAYER_NAME"],
        "Team": team_df["TEAM_ABBREVIATION"],
        "GP": team_df["GP"].astype(int),
        "MIN": team_df["MIN"].round(1),
        "PTS": team_df["PTS"].round(1),
        "FG%": (team_df["FG_PCT"] * 100).round(1),
        "3P%": (team_df["FG3_PCT"] * 100).round(1),
        "FT%": (team_df["FT_PCT"] * 100).round(1),
    })

    st.markdown(df_out.to_html(escape=False, index=False), unsafe_allow_html=True)
