# Improvements Backlog

Tracks pending and completed small fixes and improvements to the app.

---

## Completed

- **Exclude incomplete current week from season average ranks** — `avg_ranks()` now accepts an `exclude_weeks` parameter. The current in-progress week (from Yahoo's `current_week` setting) is excluded so partial data doesn't skew season rankings. The week selector also labels the current week "(in progress)".

- **Color-code weekly scores table** — Each stat column in the Weekly Scores table is now color-coded: green = strong performance, red = weak. For stats where lower is better (Goals Against, GAA), the gradient is reversed.

- **Per-week ranking and avg_rank column in Weekly Scores** — The Weekly Scores table now includes an `avg_rank` column showing each team's average rank across all stat categories for that week. The table defaults to sorting by `avg_rank` ascending (best team at top).

---

## Pending

<!-- Add future improvements here -->
