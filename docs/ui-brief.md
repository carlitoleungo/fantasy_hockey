# UI brief — Fantasy Hockey Waiver Wire

Paste-ready description of the app for a prompt-to-UI generator (v0, Flowstep, Lovable).
Describes function and user actions per page. Written 2026-09-01 against the live routes.

---

## The app in three lines

- A fantasy hockey manager connects their Yahoo account and sees, for one league at a time, where their team is weak, who is available on the waiver wire to fix it, and whether they are on track to win this week's matchup.
- Every page is a decision aid built on dense stat tables: the manager scans, compares, and decides who to add or drop. Nothing is written back to Yahoo, this is read-only analysis.
- A demo mode shows all three tools on a frozen sample league so a visitor can evaluate the app before handing over their Yahoo account.

The audience is a fantasy hockey manager checking in a few times a week, often on a phone, often mid-week when deciding a roster move. They are comfortable with stat abbreviations (G, A, PPP, SOG, HIT, BLK, W, SV%, GAA) and want density over hand-holding.

---

## Pages

### 1. Landing (logged out)

The visitor has never signed in and needs to understand what this is and get in.

What they do:
- Read a one-line value proposition: evaluate waiver wire add/drop decisions for your Yahoo fantasy hockey leagues.
- Click "Log in with Yahoo" (primary action, redirects out to Yahoo OAuth).
- Or click "Try the demo" (secondary action) to explore the three tools on sample data without an account.

Also renders a dismissible confirmation banner after logout ("You have been logged out").

### 2. League picker (logged in, same URL)

The manager belongs to several leagues and must pick which one every other page operates on.

What they do:
- See a list of their active NHL leagues, each showing season year and league name.
- Click "Select" on one. The selected league is visually marked (highlighted row, check + "Selected" label) and persists across pages.
- Switch leagues at any time by coming back here.

Empty state: "No active NHL leagues found for your account."

### 3. Weekly Leaderboard (`/overview`)

Answers "how does my team stack up against the whole league right now?"

What they do:
- Pick a week from a dropdown. The table swaps in place, no page reload.
- Scan a grid of every team (rows) against every scoring category (columns). Each cell is colour-coded by that team's rank in that category, so weak categories read as a visual band across the row.
- Read a final "Avg Rank" column that summarises overall standing.
- Click through to the head-to-head comparison.

This is the widest table in the app. It must scroll horizontally on mobile without the page itself scrolling sideways, ideally with the team-name column pinned.

### 4. Head-to-Head (`/overview/head-to-head`)

Answers "how do I compare to one specific rival over a stretch of the season?"

What they do:
- Choose Team A and Team B from two dropdowns.
- Choose a week range with "From Week" and "To Week" dropdowns.
- The comparison table updates on every change, no submit button.
- Click back to the leaderboard.

### 5. Waiver Wire (`/waiver`) — the core page

Answers "who can I pick up to fix my weakest categories?"

What they do, in order:
1. Filter by position using a row of pill toggles: All, C, LW, RW, D, G. "All" and specific positions are mutually exclusive; multiple specific positions can be on at once.
2. Choose a ranking period with a two-option radio: "Season" or "Last 30 days". This is the streak-vs-consistency toggle and is a headline control, not a buried setting.
3. Pick one or more scoring categories from a wrapping row of pill toggles (the league's own categories, shown as abbreviations). Nothing is ranked until at least one is chosen.
4. Read the results table: available players ranked by combined performance across the chosen categories, best composite rank first.

Each result row shows:
- Player name (prominent), then a meta line: NHL team abbreviation, eligible positions, and a health badge (HEALTHY / DTD / IR / OUT, colour-coded, injury statuses visually distinct from healthy).
- When "Last 30 days" is selected only: GP (games played) and GR (games remaining this week) columns.
- One right-aligned numeric column per selected category. Missing values render as an em dash, never blank or zero.
- A footer line: total player count and which period the stats cover.

Results are paginated. The three filter groups sit above the table and the table swaps in place on every change.

Empty states: before any category is picked, "Select one or more stat categories above to rank available players." After filtering to nothing, "No players found for the selected position and categories."

### 6. Week Projection (`/projection`)

Answers "am I going to win this week, and which categories are still winnable?"

What they do:
- Pick their own team from a dropdown. Everything below reloads.
- Read three summary cards side by side: my projected category wins, categories projected to tie, opponent's projected category wins. These are the at-a-glance verdict and should be the largest numbers on the page.
- Scan a category-by-category comparison table: category name, my projected total, opponent's projected total. The winning side of each row is highlighted; the losing side is dimmed. This is where the manager finds the close categories worth a roster move.
- Scroll to two roster breakdowns, one per team, showing each rostered player with games remaining this week and their projected contribution per category.

Projections come from each player's last-30-day per-game averages multiplied by their remaining NHL games this week. A short explainer line near the top says exactly that.

Bye-week state: "{team} has no matchup this week (bye week)."

### 7. Demo mode (`/demo/overview`, `/demo/waiver`, `/demo/projection`)

Identical layouts and interactions to pages 3 to 6, running on a frozen snapshot league. The only difference is the nav, which shows the three demo links plus a persistent "Log in with Yahoo" call to action, since converting the visitor is the point of the mode.

### 8. Error page (500 / 502)

Deliberately minimal and identical for every visitor. Header shows the brand link only, no nav. Body shows a plain message and a clearly clickable "Back to home" link. The page never claims to know who the visitor is.

---

## Global shell

Persistent header on every page: brand "Fantasy Hockey" on the left, linking to `/`. Nav on the right, in one of four states:

| Visitor | Nav |
|---|---|
| Signed in | Overview, Waiver, Projection, Logout |
| Demo | Overview, Waiver, Projection, Log in with Yahoo |
| Signed out | Log in with Yahoo |
| Error page | nothing |

The selected league name is available to the header on authenticated pages and should be visible, since every number on screen is scoped to it.

---

## Design direction and constraints

- Mobile-first responsive. The manager checks this on a phone mid-week. Every wide table scrolls inside its own container; the page body never scrolls horizontally.
- Data density is a feature. Do not trade rows away for whitespace. Tables should feel closer to a stats site than a marketing page.
- Colour carries meaning: rank shading on the leaderboard, win/loss highlighting on the projection, injury badges on the waiver table. Pick a palette that keeps all three legible together and passes contrast, including for red/green colour blindness (use weight, background, and dimming as well as hue).
- Numbers are right-aligned and tabular; counting stats show as integers, rate stats (SV%, GAA) to two decimals.
- Filters update results without a submit button and without a full page reload; results regions must render correctly on their own as swapped-in fragments.
- Every table needs an explicit empty state and a loading state.
- Built with Tailwind utility classes, HTMX for partial swaps, Alpine for small client-side state. Keep markup to semantic HTML plus utility classes, no component framework.
