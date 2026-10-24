"""
StatsBomb Match Explorer
-------------------------
An interactive Streamlit dashboard for exploring StatsBomb open-data
matches: shot maps, xG timelines, pass maps, and defensive action heatmaps
for any competition/season/match/team combination in the open dataset.

Run with:
    streamlit run app.py
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from statsbombpy import sb
from mplsoccer import Pitch, VerticalPitch

st.set_page_config(
    page_title="StatsBomb Match Explorer | Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Look & feel design tokens
# --------------------------------------------------------------------------

ACCENT = "#22d3ee"          # cyan — primary accent
TEAM_COLORS = ["#38bdf8", "#f43f5e"]  # sky blue / vibrant rose
BG_DARK = "#0e1117"
CARD_BG = "#161b22"
PITCH_GREEN = "#0f3d24"

plt.rcParams.update({
    "figure.facecolor": BG_DARK,
    "axes.facecolor": BG_DARK,
    "savefig.facecolor": BG_DARK,
    "text.color": "#e6edf3",
    "axes.labelcolor": "#e6edf3",
    "xtick.color": "#8b949e",
    "ytick.color": "#8b949e",
    "axes.edgecolor": "#30363d",
    "grid.color": "#21262d",
    "font.family": "sans-serif",
})

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .hero {{
        background: linear-gradient(135deg, #0b1523 0%, #15293e 50%, #1a3c54 100%);
        border-radius: 18px;
        padding: 24px 30px;
        margin-bottom: 22px;
        border: 1px solid #30363d;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}
    .hero h1 {{
        margin: 0;
        font-size: 2.2rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.5px;
    }}
    .hero p {{
        margin: 8px 0 0 0;
        color: #9fb3c8;
        font-size: 0.95rem;
    }}
    .hero-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 14px;
    }}
    .meta-badge {{
        display: inline-block;
        background: rgba(34, 211, 238, 0.12);
        color: {ACCENT};
        border: 1px solid rgba(34, 211, 238, 0.35);
        border-radius: 999px;
        padding: 4px 14px;
        font-weight: 600;
        font-size: 0.88rem;
    }}
    .meta-badge-neutral {{
        display: inline-block;
        background: rgba(148, 163, 184, 0.1);
        color: #94a3b8;
        border: 1px solid #30363d;
        border-radius: 999px;
        padding: 4px 14px;
        font-weight: 500;
        font-size: 0.88rem;
    }}

    div[data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 14px 18px 8px 18px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        border-color: #565f6b;
        transform: translateY(-2px);
    }}
    div[data-testid="stMetricLabel"] {{
        color: #8b949e;
        font-weight: 500;
        font-size: 0.9rem;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {CARD_BG};
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid #30363d;
        border-bottom: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: rgba(34, 211, 238, 0.14) !important;
        border-bottom: 2px solid {ACCENT} !important;
        color: {ACCENT} !important;
    }}

    section[data-testid="stSidebar"] {{
        border-right: 1px solid #30363d;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Data loading (cached for fast rerenders)
# --------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading competitions...")
def get_competitions() -> pd.DataFrame:
    return sb.competitions()


@st.cache_data(show_spinner="Loading matches...")
def get_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    return sb.matches(competition_id=competition_id, season_id=season_id)


@st.cache_data(show_spinner="Loading match events...")
def get_events(match_id: int) -> pd.DataFrame:
    df = sb.events(match_id=match_id)
    # Expand coordinates [x, y] to explicit numeric columns
    for col in ("location", "pass_end_location", "carry_end_location", "shot_end_location"):
        if col in df.columns:
            prefix = "" if col == "location" else col.replace("location", "")
            xcol, ycol = f"{prefix}x", f"{prefix}y"
            expanded = df[col].apply(lambda v: v if isinstance(v, list) else [None, None])
            df[[xcol, ycol]] = pd.DataFrame(expanded.tolist(), index=df.index).iloc[:, :2]
    return df


def team_colors(home: str, away: str) -> dict:
    return {home: TEAM_COLORS[0], away: TEAM_COLORS[1]}


# --------------------------------------------------------------------------
# Plotting & Analysis helpers
# --------------------------------------------------------------------------

def plot_shot_map(events: pd.DataFrame, home: str, away: str, colors: dict):
    shots = events[events["type"] == "Shot"].copy()

    pitch = Pitch(pitch_type="statsbomb", pitch_color=PITCH_GREEN, line_color="#3a5a45",
                  stripe=False, linewidth=1.5)
    fig, ax = pitch.draw(figsize=(10.5, 6.8))
    fig.patch.set_facecolor(BG_DARK)

    for _, row in shots.iterrows():
        x, y = row["x"], row["y"]
        if row["team"] == home:  # home team drawn on the left, attacking left
            x, y = 120 - x, 80 - y
        is_goal = row.get("shot_outcome") == "Goal"
        pitch.scatter(
            x=x, y=y, ax=ax,
            s=550 * (row.get("shot_statsbomb_xg") or 0.02) + 40,
            ec="white" if is_goal else "#0e1117",
            lw=1.6 if is_goal else 0.8,
            c="#ffffff" if is_goal else colors[row["team"]],
            alpha=0.95 if is_goal else 0.75,
            zorder=5 if is_goal else 3,
        )

    ax.set_title(
        f"{home} (Left)  vs  {away} (Right)   ·   Bubble Size = xG   ·   White = Goal",
        color="#e6edf3", fontsize=12, fontweight="600", pad=14,
    )
    return fig


def plot_xg_timeline(events: pd.DataFrame, home: str, away: str, colors: dict):
    shots = events[events["type"] == "Shot"].copy()
    shots = shots.sort_values(["period", "minute", "second"])

    fig, ax = plt.subplots(figsize=(10.5, 4.5))
    for team in (home, away):
        team_shots = shots[shots["team"] == team]
        if not team_shots.empty:
            cum_xg = team_shots["shot_statsbomb_xg"].cumsum()
            minutes = team_shots["minute"]
            total_xg = cum_xg.iloc[-1] if len(cum_xg) > 0 else 0.0
            ax.step(minutes, cum_xg, where="post", label=f"{team} ({total_xg:.2f} xG)", color=colors[team], linewidth=2.6)
            goals = team_shots[team_shots["shot_outcome"] == "Goal"]
            if not goals.empty:
                ax.scatter(goals["minute"], cum_xg.loc[goals.index], color="#ffffff",
                            s=95, zorder=6, edgecolor=colors[team], linewidth=2.2, label=f"{team} Goal")

    ax.set_xlabel("Match Minute", fontsize=10, fontweight="600")
    ax.set_ylabel("Cumulative Expected Goals (xG)", fontsize=10, fontweight="600")
    ax.set_title("xG Race & Match Flow Timeline", fontsize=13, fontweight="700", color="#e6edf3", pad=12)
    ax.legend(frameon=True, facecolor=CARD_BG, edgecolor="#30363d", labelcolor="#e6edf3", loc="upper left")
    ax.grid(alpha=0.2, linestyle="--")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return fig


def plot_pass_map(events: pd.DataFrame, team: str, player, color: str, progressive_only: bool = False):
    passes = events[(events["type"] == "Pass") & (events["team"] == team)].copy()
    if player:
        passes = passes[passes["player"] == player]
    passes = passes.dropna(subset=["x", "y", "pass_end_x", "pass_end_y"])

    if progressive_only:
        # A pass is progressive if it moves ball at least 10m towards opponent end line (120 - end_x < 120 - start_x - 10)
        passes = passes[(passes["pass_end_x"] - passes["x"]) >= 10]

    pitch = VerticalPitch(pitch_type="statsbomb", pitch_color=PITCH_GREEN,
                           line_color="#3a5a45", half=False, linewidth=1.5)
    fig, ax = pitch.draw(figsize=(6.8, 9.8))
    fig.patch.set_facecolor(BG_DARK)

    completed = passes[passes["pass_outcome"].isna()]
    incomplete = passes[passes["pass_outcome"].notna()]

    pitch.arrows(completed["x"], completed["y"], completed["pass_end_x"], completed["pass_end_y"],
                 ax=ax, color=color, width=2.2, headwidth=5, headlength=5, alpha=0.85, label=f"Completed ({len(completed)})")
    pitch.arrows(incomplete["x"], incomplete["y"], incomplete["pass_end_x"], incomplete["pass_end_y"],
                 ax=ax, color="#6b7280", width=1.6, headwidth=4, alpha=0.5, label=f"Incomplete ({len(incomplete)})")

    ax.legend(facecolor=CARD_BG, edgecolor="#30363d", loc="lower left", labelcolor="#e6edf3")
    title = f"{team}" + (f" — {player}" if player else " — All Passes")
    if progressive_only:
        title += " (Progressive Passes Only)"
    ax.set_title(title, color="#e6edf3", fontsize=12, fontweight="600", pad=12)
    return fig


def plot_defensive_heatmap(events: pd.DataFrame, team: str, action_types: list, player: str = None):
    mask = (events["team"] == team) & (events["type"].isin(action_types))
    if player:
        mask = mask & (events["player"] == player)
    actions = events[mask].dropna(subset=["x", "y"]).copy()

    pitch = Pitch(pitch_type="statsbomb", pitch_color=PITCH_GREEN, line_color="#3a5a45", linewidth=1.5)
    fig, ax = pitch.draw(figsize=(10.5, 6.8))
    fig.patch.set_facecolor(BG_DARK)

    if len(actions) >= 5:
        pitch.kdeplot(actions["x"], actions["y"], ax=ax, cmap="inferno", fill=True, levels=50, alpha=0.55, zorder=2)

    pitch.scatter(
        actions["x"], actions["y"], ax=ax,
        color="#f59e0b", s=35, alpha=0.75, ec="#161b22", lw=0.6, zorder=3,
        label=f"Defensive Actions ({len(actions)})"
    )

    ax.legend(facecolor=CARD_BG, edgecolor="#30363d", loc="upper left", labelcolor="#e6edf3")
    title = f"{team} · Defensive Intensity & Spatial Distribution"
    if player:
        title += f" ({player})"
    ax.set_title(title, color="#e6edf3", fontsize=12, fontweight="600", pad=14)
    return fig, len(actions)


def team_shot_summary(events: pd.DataFrame) -> pd.DataFrame:
    shots = events[events["type"] == "Shot"].copy()
    if shots.empty:
        return pd.DataFrame(columns=["shots", "goals", "total_xg", "xg_per_shot"])
    summary = shots.groupby("team").agg(
        shots=("id", "count"),
        goals=("shot_outcome", lambda s: (s == "Goal").sum()),
        total_xg=("shot_statsbomb_xg", "sum"),
    ).round(2)
    summary["xg_per_shot"] = (summary["total_xg"] / summary["shots"]).round(2)
    return summary


def team_pass_summary(events: pd.DataFrame, team: str) -> dict:
    passes = events[(events["type"] == "Pass") & (events["team"] == team)].copy()
    total = len(passes)
    if total == 0:
        return {"total": 0, "completed": 0, "pct": 0.0, "progressive": 0}
    completed = len(passes[passes["pass_outcome"].isna()])
    pct = round((completed / total) * 100, 1)
    # Progressive passes
    valid = passes.dropna(subset=["x", "pass_end_x"])
    progressive = len(valid[(valid["pass_end_x"] - valid["x"]) >= 10])
    return {"total": total, "completed": completed, "pct": pct, "progressive": progressive}


# --------------------------------------------------------------------------
# Sidebar — Navigation & Match Selection
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚽ Match Explorer")
    st.caption("Open Football Analytics Intelligence")
    st.markdown("---")

    competitions = get_competitions()
    comp_labels = (competitions["competition_name"] + " — " + competitions["season_name"]).tolist()
    # Default to World Cup 2022 if available
    default_comp_idx = 0
    wc_matches = [i for i, l in enumerate(comp_labels) if "FIFA World Cup — 2022" in l]
    if wc_matches:
        default_comp_idx = wc_matches[0]

    comp_choice = st.selectbox("Competition & Season", comp_labels, index=default_comp_idx)
    comp_row = competitions.iloc[comp_labels.index(comp_choice)]

    matches = get_matches(int(comp_row["competition_id"]), int(comp_row["season_id"]))
    matches = matches.sort_values("match_date", ascending=False)
    match_labels = (
        matches["match_date"].astype(str) + "  ·  " +
        matches["home_team"] + " " + matches["home_score"].astype(str) +
        " - " + matches["away_score"].astype(str) + " " + matches["away_team"]
    ).tolist()

    # Default to Final if present
    default_match_idx = 0
    if "competition_stage" in matches.columns:
        finals = matches[matches["competition_stage"].apply(lambda s: s == "Final" or (isinstance(s, dict) and s.get("name") == "Final"))]
        if not finals.empty:
            final_id = finals.iloc[0]["match_id"]
            match_indices = [i for i, mid in enumerate(matches["match_id"]) if mid == final_id]
            if match_indices:
                default_match_idx = match_indices[0]

    match_choice = st.selectbox("Match", match_labels, index=default_match_idx)
    match_row = matches.iloc[match_labels.index(match_choice)]

home, away = match_row["home_team"], match_row["away_team"]
colors = team_colors(home, away)
events = get_events(int(match_row["match_id"]))

with st.sidebar:
    st.markdown("---")
    include_shootout = st.checkbox(
        "Include penalty shootout", value=False,
        help="Shootout kicks (period 5) are excluded by default so they don't inflate xG.",
    )
    st.caption(f"📊 **{len(events):,}** match events loaded")
    st.caption("Powered by **StatsBomb Open Data** & **mplsoccer**")
    st.markdown("---")
    st.markdown("[⭐ View on GitHub](https://github.com/YOUR-USERNAME/match-explorer)")

# --------------------------------------------------------------------------
# Hero Header
# --------------------------------------------------------------------------

stage_val = match_row.get("competition_stage")
stage_name = stage_val.get("name", "") if isinstance(stage_val, dict) else (stage_val if isinstance(stage_val, str) else "")
stadium_val = match_row.get("stadium")
stadium_name = stadium_val.get("name", "") if isinstance(stadium_val, dict) else (stadium_val if isinstance(stadium_val, str) else "")
ref_val = match_row.get("referee")
ref_name = ref_val.get("name", "") if isinstance(ref_val, dict) else (ref_val if isinstance(ref_val, str) else "")

st.markdown(
    f"""
    <div class="hero">
        <h1>{home} <span style="color:{colors[home]}">{match_row['home_score']}</span>
            &nbsp;–&nbsp;
            <span style="color:{colors[away]}">{match_row['away_score']}</span> {away}</h1>
        <p>{comp_row['competition_name']} · {comp_row['season_name']} · {match_row['match_date']}</p>
        <div class="hero-meta">
            {f'<span class="meta-badge">🏆 {stage_name}</span>' if stage_name else ''}
            {f'<span class="meta-badge-neutral">🏟️ {stadium_name}</span>' if stadium_name else ''}
            {f'<span class="meta-badge-neutral">⚖️ Ref: {ref_name}</span>' if ref_name else ''}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# KPI Row
# --------------------------------------------------------------------------

# Shootout kicks live in period 5; keep them out of xG unless the user opts in
shot_events = events if include_shootout else events[events["period"] <= 4]
summary = team_shot_summary(shot_events)
pass_h = team_pass_summary(events, home)
pass_a = team_pass_summary(events, away)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric(f"{home} Shots", int(summary.loc[home, "shots"]) if home in summary.index else 0)
k2.metric(f"{home} xG", f"{summary.loc[home, 'total_xg']:.2f}" if home in summary.index else "0.00")
k3.metric(f"{home} Passes", f"{pass_h['pct']}%")
k4.metric(f"{away} Passes", f"{pass_a['pct']}%")
k5.metric(f"{away} xG", f"{summary.loc[away, 'total_xg']:.2f}" if away in summary.index else "0.00")
k6.metric(f"{away} Shots", int(summary.loc[away, "shots"]) if away in summary.index else 0)

st.write("")

# --------------------------------------------------------------------------
# Main Tabs
# --------------------------------------------------------------------------

tab_shots, tab_xg, tab_passes, tab_defensive, tab_data = st.tabs(
    ["🎯  Shot Map", "📈  xG Timeline", "🔀  Pass Map & Flow", "🔥  Defensive Heatmap", "📋  Raw Data & Export"]
)

with tab_shots:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.pyplot(plot_shot_map(shot_events, home, away, colors))
    with col2:
        st.markdown("##### 📊 Shot & xG Summary")
        st.dataframe(summary, width="stretch")
        csv_shots = summary.to_csv().encode('utf-8')
        st.download_button(
            label="📥 Download Summary (CSV)",
            data=csv_shots,
            file_name=f"{home}_vs_{away}_shot_summary.csv",
            mime="text/csv",
        )
        st.caption("xG calculated via StatsBomb proprietary statistical expected goals model.")

with tab_xg:
    st.pyplot(plot_xg_timeline(shot_events, home, away, colors))
    st.caption("Cumulative Expected Goals (xG) trajectory showing momentum shifts and scoring chances throughout match duration.")

with tab_passes:
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        team_p = st.selectbox("Select Team", [home, away], key="pass_team")
    players = ["All players"] + sorted(
        events[(events["team"] == team_p) & (events["type"] == "Pass")]["player"].dropna().unique().tolist()
    )
    with col_b:
        player_p = st.selectbox("Select Player", players, key="pass_player")
    with col_c:
        prog_only = st.checkbox("Progressive Passes Only (≥10m gain)", value=False)

    filter_player = None if player_p == "All players" else player_p
    st.pyplot(plot_pass_map(events, team_p, filter_player, colors[team_p], progressive_only=prog_only))

with tab_defensive:
    col_d1, col_d2 = st.columns([1, 1])
    with col_d1:
        team_d = st.selectbox("Select Team", [home, away], key="def_team")
    with col_d2:
        def_action_labels = {
            "Pressures (High Press & Pressing Zones)": ["Pressure"],
            "Tackles, Recoveries & Interceptions": ["Ball Recovery", "Interception", "Duel", "Block"],
            "All Defensive Actions": ["Pressure", "Ball Recovery", "Interception", "Duel", "Block", "Clearance"]
        }
        action_choice = st.selectbox("Defensive Action Category", list(def_action_labels.keys()))

    fig_def, act_count = plot_defensive_heatmap(events, team_d, def_action_labels[action_choice])
    st.pyplot(fig_def)
    st.caption(f"Showing {act_count} recorded events. Kernel Density Estimation (KDE) reveals spatial intensity centers.")

with tab_data:
    st.markdown("##### 🔍 Match Event Explorer")
    event_types = sorted(events["type"].dropna().unique().tolist())
    selected_types = st.multiselect("Filter by Event Type", event_types, default=["Shot", "Pass"])
    filtered_df = events[events["type"].isin(selected_types)] if selected_types else events
    st.dataframe(filtered_df, width="stretch")

    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Events (CSV)",
        data=csv_data,
        file_name=f"{home}_vs_{away}_events.csv",
        mime="text/csv",
    )
