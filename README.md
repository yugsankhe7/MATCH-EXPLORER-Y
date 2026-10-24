# StatsBomb Match Explorer

![Match Explorer showcase](assets/showcase_banner.png)

A Streamlit dashboard for digging into any match in [StatsBomb's free open data](https://github.com/statsbomb/open-data). Pick a competition and a match, then look at the game through shots, xG, passing and defensive pressure.

I started this as a single shot-map notebook for the 2022 World Cup final (it's still in `notebooks/`) and kept adding views until it turned into an app. The final is the default match because 3–3 plus a shootout gives the charts plenty to show.

## What it does

- **Shot map:** every shot on one pitch, sized by xG, goals in white.
- **xG timeline:** cumulative xG per team over the match, with goals marked.
- **Pass map:** pass arrows for a team or a single player, completed vs. incomplete, with a progressive-pass filter (10+ yards towards goal).
- **Defensive heatmap:** pressures, recoveries, interceptions and blocks, drawn as a density map over the raw events.
- **Raw data:** filter events by type and download them as CSV.

## What the final looks like

Over 120 minutes Argentina had 20 shots worth **2.76 xG**; France had 10 shots worth **2.27 xG**. Both scored three. France created almost nothing until the 79th minute and then scored twice within two minutes, which is the sharp step in the xG chart.

| Shot map | xG timeline |
|---|---|
| ![Shot map](assets/shot_map.png) | ![xG timeline](assets/xg_timeline.png) |

| Messi's passes (49 of 60 completed) | Argentina's pressure |
|---|---|
| ![Pass map](assets/pass_map.png) | ![Pressure heatmap](assets/pressure_heatmap.png) |

## Run it

```bash
git clone https://github.com/YOUR-USERNAME/match-explorer.git
cd match-explorer
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501. No API key is needed; it only uses the open data.

## Things I ran into

- **Shootout kicks inflate xG.** StatsBomb stores penalty-shootout shots as `period 5`. My first version counted them, which made the final look like 5.89 vs 5.41 xG. They're now excluded by default, with a sidebar checkbox to bring them back.
- **Pitch direction.** StatsBomb coordinates always point to the right-hand goal, so one team's shots have to be mirrored (`120 - x`, `80 - y`) to share a pitch.
- **Caching.** `@st.cache_data` on the competition, match and event calls keeps switching tabs and filters instant.

## Project layout

```
match-explorer/
├── app.py                    # the Streamlit app
├── requirements.txt
├── .streamlit/config.toml    # dark theme
├── notebooks/
│   └── shot_map_prototype.ipynb
└── assets/                   # images used in this README
```

## Ideas for next

- Individual player stat pages
- Pass networks
- Progressive carries

## Credits

Event data from [StatsBomb Open Data](https://github.com/statsbomb/open-data). If you publish anything using it, credit StatsBomb. Built with Streamlit, mplsoccer, statsbombpy, pandas and matplotlib.

MIT licensed, see [LICENSE](LICENSE).
