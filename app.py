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

st.set_page_config(
    page_title="NBA Shooting – NBA.com 2025-26",
    layout="wide"
)

# -------------------------------
# LOGO + HEADSHOT HELPERS
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
    """Color FG% cells: Red < 30, Yellow 30–40, Green > 40."""
    if pd.isna(val):
        return ""
    if val < 0.30:
        return "background-color: red"
    if val < 0.40:
        return "background-color: yellow"
    return "background-color: green"

# -------------------------------
# LOAD MAIN STATS (PER GAME)
# -------------------------------
@st.cache_data(show_spinner=True)
def load_main_stats(season: str) -> pd.DataFrame:
    stats = LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame"
    ).get_data_frames()[0]

    numeric_cols = [
        "GP", "MIN",
        "FGM", "FGA", "FG_PCT",
        "FG3M", "FG3A", "FG3_PCT",
        "FTM", "FTA", "FT_PCT",
        "PTS"
    ]
    for col in numeric_cols:
        if col in stats.columns:
            stats[col] = pd.to_numeric(stats[col], errors="coerce")

    return stats

# -------------------------------
# LOAD SHOT DATA (BY ZONE)
# -------------------------------
@st.cache_data(show_spinner=True)
def load_shot_data(season: str) -> pd.DataFrame:
    df = LeagueDashPlayerShotLocations(
        season=season,
        season_type_all_star="Regular Season",
        distance_range="By Zone",
        per_mode_detailed="PerGame"
    ).get_data_frames()[0]

    # flatten any tuple / MultiIndex columns
    flat_cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            flat_cols.append("_".join([str(x) for x in c if x]))
        else:
            flat_cols.append(str(c))
    df.columns = flat_cols

    # convert numeric FGM/FGA/FG_PCT columns
    for c in df.columns:
        if "FGM" in c or "FGA" in c or "FG_PCT" in c:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# -------------------------------
# ZONE BREAKDOWN FOR ONE PLAYER
# -------------------------------
def get_zones_for_player(player_name: str, shots_all: pd.DataFrame) -> pd.DataFrame:
    df = shots_all.copy()

    if "PLAYER_NAME" not in df.columns:
        return pd.DataFrame()

    df = df[df["PLAYER_NAME"] == player_name]
    if df.empty:
        return pd.DataFrame()

    row = df.iloc[0]

    shot_cols = [
        c for c in df.columns
        if c.endswith("_FGM") or c.endswith("_FGA") or c.endswith("_FG_PCT")
    ]

    zone_records = {}

    for col in shot_cols:
        val = row[col]

        if col.endswith("_FG_PCT"):
            zone = col.replace("_FG_PCT", "")
            metric = "FG_PCT"
        elif col.endswith("_FGM"):
            zone = col.replace("_FGM", "")
            metric = "FGM"
        else:  # _FGA
            zone = col.replace("_FGA", "")
            metric = "FGA"

        rec = zone_records.setdefault(zone, {
            "zone": zone,
            "FGM": 0.0,
            "FGA": 0.0,
            "FG_PCT": np.nan
        })

        if metric in ["FGM", "FGA"] and pd.notna(val):
            rec[metric] += float(val)
        elif metric == "FG_PCT" and pd.notna(val):
            rec["FG_PCT"] = float(val)

    zp = pd.DataFrame(zone_records.values())

    # drop Backcourt
    zp = zp[zp["zone"] != "Backcourt"].copy()

    total_fga = zp["FGA"].sum()

    zp["pts_val"] = np.where(zp["zone"].str.contains("3"), 3, 2)
    zp["PTS"] = zp["FGM"] * zp["pts_val"]
    zp["PTS_per_shot"] = np.where(zp["FGA"] > 0, zp["PTS"] / zp["FGA"], np.nan)
    zp["Shot Share"] = np.where(total_fga > 0, zp["FGA"] / total_fga, np.nan)

    return zp

# -------------------------------
# LOAD DATA
# -------------------------------
stats_all = load_main_stats(TARGET_SEASON)
shots_all = load_shot_data(TARGET_SEASON)

# -------------------------------
# SIDEBAR – TEAM & PLAYER SELECT
# -------------------------------
teams = ["All"] + sorted(stats_all["TEAM_ABBREVIATION"].unique())

with st.sidebar:
    team_sel = st.selectbox("Choose a team:", teams)

    # show team logo under the dropdown (except for All)
    if team_sel != "All":
        logo_url_sb = get_team_logo(team_sel)
        if logo_url_sb:
            st.image(logo_url_sb, width=70)

    if team_sel == "All":
        players = sorted(stats_all["PLAYER_NAME"].unique())
    else:
        players = sorted(
            stats_all[stats_all["TEAM_ABBREVIATION"] == team_sel]["PLAYER_NAME"].unique()
        )

    player_sel = st.selectbox("Choose a player:", players)

    st.markdown("---")
    st.write("Stats: NBA.com Shooting General (Per Game)")
    st.write("Zones: NBA.com Shooting Dashboard (By Zone)")
    st.write(SEASON_LABEL)

# -------------------------------
# PLAYER HEADER
# -------------------------------
if team_sel == "All":
    p_rows = stats_all[stats_all["PLAYER_NAME"] == player_sel]
else:
    p_rows = stats_all[
        (stats_all["PLAYER_NAME"] == player_sel) &
        (stats_all["TEAM_ABBREVIATION"] == team_sel)
    ]
if p_rows.empty:
    p_rows = stats_all[stats_all["PLAYER_NAME"] == player_sel]

player_row = p_rows.iloc[0]

st.title("NBA Shooting – NBA.com 2025-26")

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

        # clean zone labels
        df_zone["Zone"] = (
            df_zone["zone"]
            .str.replace("_", " ", regex=False)
            .str.replace("Non RA", "(Non-RA)", regex=False)
        )

        # base shooting columns
        df_zone = df_zone[["Zone", "FGM", "FGA", "PTS_per_shot", "FG_PCT", "PTS", "Shot Share"]].copy()
        df_zone.rename(
            columns={
                "PTS_per_shot": "PTS/shot",
                "FG_PCT": "FG%",
            },
            inplace=True
        )

        # add FT stats columns (empty for regular zones)
        df_zone["FTM"] = np.nan
        df_zone["FTA"] = np.nan
        df_zone["FT%"] = np.nan

        # add Free Throw row with real FT numbers
        ft_row = {
            "Zone": "Free Throw",
            "FGM": np.nan,
            "FGA": np.nan,
            "PTS/shot": np.nan,
            "FG%": np.nan,  # keep NaN so no color
            "PTS": np.nan,
            "Shot Share": np.nan,
            "FTM": player_row["FTM"],
            "FTA": player_row["FTA"],
            "FT%": player_row["FT_PCT"],
        }
        df_zone = pd.concat([df_zone, pd.DataFrame([ft_row])], ignore_index=True)

        # order columns nicely
        df_zone = df_zone[[
            "Zone", "FGM", "FGA", "PTS/shot", "FG%", "PTS", "Shot Share",
            "FTM", "FTA", "FT%"
        ]]

        # style + format numbers
        styled = (
            df_zone.style
            .applymap(fg_color, subset=["FG%"])  # FT row has FG% = NaN → no color
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
