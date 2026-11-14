#!/usr/bin/env python3
"""
Add edge cases to the demo snapshot so the UI can be checked against them without
a Yahoo key.

Run from the project root after scripts/generate_demo_data.py (which overwrites
these files):

    .venv/bin/python scripts/add_demo_edge_cases.py

Safe to run more than once: every change sets a value rather than adding to it.

What it adds:
- Last-30-day rows for defencemen and goalies. The snapshot only had the top 25
  forwards, so the Last 30 / Rest of week views had no D or G rows at all. Values are
  derived from each player's season line (about 35 %, with a little seeded noise),
  not real last-30 stats.
- Every injury/availability status Yahoo uses for NHL players, on players who show
  up in the Last 30 views too.
- Games-remaining values of 0 and 4, filling the six teams the snapshot was missing.
- An accented, 24-character name (Charles-Édouard D'Astous, his real spelling;
  Yahoo returned it as "Charle-Edouard D'Astous").
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "demo" / "data"

SKATER_STATS = [
    "Goals", "Assists", "Points", "Plus/Minus", "Penalty Minutes",
    "Powerplay Points", "Shots on Goal", "Faceoffs Won", "Hits", "Blocks",
]
GOALIE_COUNT_STATS = ["Wins", "Shutouts"]
GAA = "Goals Against Average"

# player_name -> Yahoo status code. Together with the snapshot's own O / DTD / IR / NA
# this covers every code the template has to style.
STATUSES = {
    "Collin Graf": "IR-LT",
    "Justin Brazeau": "IR-NR",
    "Joel Farabee": "SUSP",
    "Cody Glass": "GTD",
    "Bobby Brink": "NA",
    "Matthew Wood": "IR",
    "Tristan Jarry": "IR",
}

# Teams missing from games_remaining.json; 0 and 4 are the cases the snapshot lacked.
GAMES_REMAINING = {"NSH": 4, "NYR": 4, "VAN": 4, "PHI": 0, "NYI": 0, "WPG": 2}

RENAMES = {"Charle-Edouard D'Astous": "Charles-Édouard D'Astous"}

N_DEFENCE = 10
N_GOALIES = 7


def main() -> None:
    season = pd.read_parquet(DATA_DIR / "players_season.parquet")
    lastmonth = pd.read_parquet(DATA_DIR / "players_lastmonth.parquet")

    season["player_name"] = season["player_name"].replace(RENAMES)
    for name, status in STATUSES.items():
        assert (season["player_name"] == name).any(), name
        season.loc[season["player_name"] == name, "status"] = status

    rng = np.random.default_rng(14)
    defence = season[season["display_position"] == "D"].head(N_DEFENCE)
    dastous = season[season["player_name"] == RENAMES["Charle-Edouard D'Astous"]]
    defence = pd.concat([defence, dastous]).drop_duplicates("player_key")
    goalies = season[season["display_position"] == "G"].head(N_GOALIES)

    new_rows = []
    for _, p in defence.iterrows():
        row = {"player_key": p["player_key"], "games_played": int(rng.integers(12, 16))}
        for stat in SKATER_STATS:
            value = p[stat] * 0.35 * rng.uniform(0.7, 1.3)
            row[stat] = float(round(value)) if pd.notna(value) else np.nan
        row["Points"] = row["Goals"] + row["Assists"]
        new_rows.append(row)

    for i, (_, p) in enumerate(goalies.iterrows()):
        # The last goalie gets a single start: the small-sample case.
        gp = 1 if i == len(goalies) - 1 else int(rng.integers(4, 11))
        share = gp / 40
        row = {"player_key": p["player_key"], "games_played": gp}
        for stat in GOALIE_COUNT_STATS:
            row[stat] = float(min(round(p[stat] * share * rng.uniform(0.7, 1.3)), gp))
        row["Saves"] = float(round(p["Saves"] * share * rng.uniform(0.8, 1.2)))
        row[GAA] = round(float(p[GAA]) * rng.uniform(0.8, 1.25), 2)
        new_rows.append(row)

    new = pd.DataFrame(new_rows)
    lastmonth = lastmonth[~lastmonth["player_key"].isin(new["player_key"])]
    lastmonth = pd.concat([lastmonth, new], ignore_index=True)
    for col in SKATER_STATS + GOALIE_COUNT_STATS + ["Saves", GAA]:
        lastmonth[col] = lastmonth[col].astype("float64")
    lastmonth["games_played"] = lastmonth["games_played"].astype("int64")

    season.to_parquet(DATA_DIR / "players_season.parquet", index=False)
    lastmonth.to_parquet(DATA_DIR / "players_lastmonth.parquet", index=False)

    games_path = DATA_DIR / "games_remaining.json"
    games = json.loads(games_path.read_text())
    games.update(GAMES_REMAINING)
    games_path.write_text(json.dumps(dict(sorted(games.items())), indent=2) + "\n")

    print(f"lastmonth rows: {len(lastmonth)}; teams with games remaining: {len(games)}")


if __name__ == "__main__":
    main()
