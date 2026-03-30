# Design Notes

## 1. Responsive Design / Mobile Support

**Current state:** Streamlit provides basic responsiveness for free — the sidebar collapses to a hamburger menu, `st.dataframe()` scrolls horizontally, and the content area scales to viewport width. The app is usable on mobile but not optimised for it.

**Known pain points:**
- `st.columns()` does not stack on narrow screens — it stays side-by-side and squeezes. Affected locations:
  - `pages/01_league_overview.py`: `st.columns(3)` for week/team selectors; `st.columns(3)` for win/tie/loss metrics
  - `pages/03_waiver_wire.py`: `st.columns([2, 2, 1])` for position/period/refresh controls
- The custom HTML tables rendered via `st.html()` (league overview) may have small touch targets and require horizontal scrolling on mobile.
- Content is inherently dense (stat tables) — difficult on small screens regardless of framework.

**Effort to improve:**

| Level | Work | What you get |
|---|---|---|
| None | 0 | App is passable — sidebar hamburger works, tables scroll |
| Low | < 1 day | Custom CSS via `st.markdown('<style>...</style>')` to make columns stack at narrow breakpoints (target `.stHorizontalBlock` with a media query) |
| High | 2–3 days | Redesign HTML tables as mobile-friendly cards; rethink control layout |

**Recommendation:** Don't invest in mobile-first design. The use case (weekly strategy review, dense stat tables) is inherently desktop-oriented, and the Yahoo native app already handles mobile fantasy management. Address the stacked-columns pain point with a small CSS injection if it becomes annoying, but don't treat it as a priority.

---

## 2. Architecture for Variations (Points Leagues, Other Sports)

### Background

The data and analysis layers are already well-positioned for variations:
- Stat columns in DataFrames are dynamic — derived from the API response, not hardcoded
- Analysis functions take DataFrames and work on whatever columns are present
- `scoring_type` is already fetched in `leagues.py` and stored in each league dict but is never used in business logic

The main coupling points that need attention:

| Coupling | Location | Risk |
|---|---|---|
| `LOWER_IS_BETTER` hardcoded | `analysis/team_scores.py` | Wrong for other sports (e.g. ERA in baseball) |
| `game_code == "nhl"` filter | `data/leagues.py` | Prevents other sports from appearing |
| Analysis algorithms assume H2H categories | `analysis/team_scores.py`, `matchup_sim.py`, `waiver_ranking.py` | Wrong for points leagues |

### Decisions to make before implementing variations

**A. Store `scoring_type` in session state**

It's already fetched — just not used. When the user selects a league in `app.py`, add:
```python
st.session_state["scoring_type"] = selected_league["scoring_type"]
```
Yahoo `scoring_type` values: `"head"` (H2H categories), `"headone"` (H2H points), `"rotisserie"`, `"point"`.

**B. Move `LOWER_IS_BETTER` to a per-sport config**

Extract from `analysis/team_scores.py` into a new `analysis/config.py`:
```python
LOWER_IS_BETTER_BY_SPORT: dict[str, frozenset[str]] = {
    "nhl": frozenset({"Goals Against", "Goals Against Average", "GA", "GAA"}),
    "mlb": frozenset({"ERA", "WHIP", "Earned Run Average", "Walks + Hits Per Inning Pitched"}),
    # other sports added as needed
}
```
All analysis functions that currently import `LOWER_IS_BETTER` directly would instead receive it as a parameter (they already support this via optional `lower_is_better=` args — the caller just needs to pass the right value).

**C. Introduce a `LeagueConfig` dataclass**

After league selection, build this and store it in `st.session_state["league_config"]`:
```python
@dataclass
class LeagueConfig:
    league_key: str
    scoring_type: str       # "head", "headone", "rotisserie", "point"
    sport: str              # "nhl", "nfl", "nba", "mlb"
    lower_is_better: frozenset[str]
```
This becomes the single place pages and analysis functions read sport/scoring context from, rather than spreading `scoring_type` and `sport` as separate session state keys.

**D. Page routing by scoring type**

When points-based pages are eventually built, `app.py` routes based on `league_config.scoring_type`:
```python
if st.session_state["league_config"].scoring_type in ("head",):
    pages = [categories_overview, waiver_wire]
else:
    pages = [points_overview, points_waiver_wire]
```
`st.navigation()` already supports dynamic page lists — no framework change needed.

**E. Analysis differences by scoring type**

| Feature | H2H Categories (current) | Points |
|---|---|---|
| League Overview | Rank teams by wins per category | Rank by total points |
| Matchup Sim | Win/loss per stat category | Compare total points scored |
| Waiver Wire | Rank by selected stat categories | Rank by projected point contribution |

Points-based analysis is generally simpler. These would be separate analysis functions in the same modules (e.g. `team_scores.weekly_scores_ranked` stays for categories; a new `team_scores.weekly_points_totals` for points leagues).

**F. Multi-sport: how to unlock**

`data/leagues.py` `get_user_hockey_leagues()` filters by `game_code == "nhl"`. Two options:
- **Rename + parameterise:** `get_user_leagues(sport="nhl")` — caller specifies sport. Add a sport selector before league selection.
- **Show all:** Remove the filter entirely; show all fantasy leagues the user has. Infer sport from each league's `game_code`. Simpler UX.

The all-sports approach is lower friction. The `game_code` field is already present in the API response.

### What NOT to do now

- Don't build a plugin system or abstract factory. The `LeagueConfig` dataclass + per-sport config dict is sufficient.
- Don't implement points or multi-sport logic yet — just the structural changes (A–C above) that unblock it later without a refactor.
- Don't touch analysis algorithms or create new pages until the feature is actually being built.

### Recommended sequence when ready to implement

1. **Preparatory refactor** (A–C above) — no behaviour change, ~2–3 hours
2. **Points league support** — add analysis functions + new page set + routing in `app.py`
3. **Additional sports** — add `LOWER_IS_BETTER` entries to config; update league fetch if needed
