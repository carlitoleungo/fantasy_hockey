# Design system

The visual direction for the UI redesign. `docs/ui-brief.md` says **what** each page does; this file
says **how it looks**. Settled with the owner on 2026-11-05 after three rounds of moodboards.

Mockups (private claude.ai artifacts, owner access):
- Waiver Wire, desktop and phone: https://claude.ai/artifact/13huj8FN8Cw4CM9Ay2CJqX
- Landing, league picker, Leaderboard, Head-to-Head, Projection: https://claude.ai/artifact/2rf4w5gNqwrjSCx3MjuMZN

## Direction in one line

A **modern pro terminal** (think a stock screener, not a sports app): navy panels, sans for names,
mono for every number, one blue accent. Two borrowed details give it a hockey/sport feel without
jerseys or flames: **F1-timing position blocks** and **condensed caps labels**. Rank is shown by
**shading the cell**, never by colouring the number.

## Principles

1. **The table is the product.** Every page is a dense table; nothing trades rows for whitespace.
2. **Shade, don't paint.** "Better in this column" = a darker cell of one hue (four steps), plus
   bold on the best. Win/loss reuses the same shade for the winner and dims the loser.
3. **Nothing relies on red vs green.** Direction uses arrows (▲ ▼) as well as colour; injuries use
   a filled tag for IR/OUT and an outlined one for DTD.
4. **One accent.** Blue marks selection, the top pick, and "you". Everything else is neutral,
   except position chips, which have their own five colours (owner's call, 2026-11-08).
5. **No decoration without a job.** Row colour stripes were tried and dropped until there's a
   distinct use case for them.
6. **Light and dark are both first-class.** Dark is the reference; light mirrors it.

## Tokens

Defined once as CSS custom properties; Tailwind classes reference them (see "Wiring" below).

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#070b12` | `#e9edf2` | Page behind the app |
| `--app` | `#0b111b` | `#f4f6f9` | App body |
| `--panel` | `#0f1724` | `#ffffff` | Tables, cards, header |
| `--panel-2` | `#131d2d` | `#f3f5f8` | Row hover, table status bar |
| `--line` | `#1f2b3e` | `#dce2ea` | Borders, header rules |
| `--line-2` | `#162133` | `#edf0f4` | Row dividers |
| `--fg` | `#dfe6f0` | `#1a2230` | Body text, numbers |
| `--strong` | `#ffffff` | `#0b111b` | Names, headings, best cell |
| `--muted` | `#8190a6` | `#5d6a7c` | Labels, meta |
| `--dim` | `#56647a` | `#97a2b1` | Em dashes, losing values |
| `--accent` | `#3d8bff` | `#1f5fbf` | Selection, top pick, "you" |
| `--accent-soft` | `#132745` | `#e3ecfa` | Selected row / chip fill |
| `--pos-bg` / `--pos-fg` | `#fff` / `#070b12` | `#0b111b` / `#fff` | Position blocks |
| `--h4` … `--h1` | accent at 55 / 32 / 16 / 6 % | accent at 42 / 24 / 12 / 5 % | Rank shading, best → worst |
| `--up` | `#4cc3ff` | `#0b6fb0` | ▲ rank change, HOT tag |
| `--down` | `#ffa04d` | `#b85600` | ▼ rank change, COLD tag |
| `--dtd` | `#ffb547` | `#a86200` | DTD tag (outline) |
| `--inj` | `#ff6b6b` | `#c62828` | IR / OUT tag (filled) |
| `--pc-c` `--pc-lw` `--pc-rw` `--pc-d` `--pc-g` | `#5cc0f2` `#4fd39b` `#b99bff` `#e9c74f` `#ff86bd` | `#13729f` `#16784e` `#6b47c4` `#8a6a00` `#b23772` | Position chips C / LW / RW / D / G |

```css
:root {                         /* dark is the default */
  color-scheme: dark;
  --bg:#070b12; --app:#0b111b; --panel:#0f1724; --panel-2:#131d2d;
  --line:#1f2b3e; --line-2:#162133;
  --fg:#dfe6f0; --strong:#fff; --muted:#8190a6; --dim:#56647a;
  --accent:#3d8bff; --accent-soft:#132745;
  --pos-bg:#fff; --pos-fg:#070b12;
  --h4:rgb(61 139 255/.55); --h3:rgb(61 139 255/.32); --h2:rgb(61 139 255/.16); --h1:rgb(61 139 255/.06);
  --up:#4cc3ff; --down:#ffa04d; --dtd:#ffb547; --inj:#ff6b6b;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    color-scheme: light;
    --bg:#e9edf2; --app:#f4f6f9; --panel:#fff; --panel-2:#f3f5f8;
    --line:#dce2ea; --line-2:#edf0f4;
    --fg:#1a2230; --strong:#0b111b; --muted:#5d6a7c; --dim:#97a2b1;
    --accent:#1f5fbf; --accent-soft:#e3ecfa;
    --pos-bg:#0b111b; --pos-fg:#fff;
    --h4:rgb(31 95 191/.42); --h3:rgb(31 95 191/.24); --h2:rgb(31 95 191/.12); --h1:rgb(31 95 191/.05);
    --up:#0b6fb0; --down:#b85600; --dtd:#a86200; --inj:#c62828;
  }
}
/* repeat the light block under :root[data-theme="light"] if a manual toggle is added */
```

### Type

| Role | Face | Where |
|---|---|---|
| Sans | IBM Plex Sans 400/500/600/700 | Names, headings, sentences |
| Mono | IBM Plex Mono 400/500/600 | Every number, meta lines, status bars |
| Condensed | Barlow Condensed 500/600/700, caps, `letter-spacing: .1em` | Nav, column headers, filter labels, tags, position blocks |

Scale: 12 (meta) · 13 (table numbers) · 14 (names, body) · 22 (page title) · 34 (landing headline only).
Numbers are right-aligned with `font-variant-numeric: tabular-nums`; counting stats are integers,
rate stats (SV%, GAA) two or three decimals, missing values an em dash in `--dim`.

All three are self-hosted (`web/static/fonts/`, latin + latin-ext, SIL OFL licences alongside),
copied from `@fontsource` by `web/styles/copy-fonts.mjs`.

### Spacing and shape

- 4 px base. Table rows 36 px tall (32 on the Leaderboard), cell padding 0 × 10 px.
- Radius: 2–3 px on blocks and tags, 4 px on chips and buttons, 6–8 px on panels. No pills except
  small status pills.
- Borders 1 px `--line`. No shadows.

## Components

| Component | Spec |
|---|---|
| **App bar** | 52 px, `--panel`, bottom `--line`. Brand = "FH" position block + "Fantasy Hockey". League name in a mono outlined chip. Nav in condensed caps; active item has a 2 px `--accent` underline. |
| **Position block** | 26 × 22 px, condensed 700 15 px, `--pos-bg`/`--pos-fg`. Blue (`--accent`) for the top pick or your own team. Leads every ranked list. |
| **Filter chip** | Mono 12.5 px, 1 px border, 4 px radius. Selected: `--accent-soft` fill + `--accent` border. |
| **Segmented toggle** | Season / Last 30 days / Rest of week, week ‹ › picker. Selected segment filled `--accent`, white text. |
| **Tabs** | Condensed caps with a mono count (`SCREEN 248`). Active = `--strong` + accent underline. |
| **Data grid** | Panel with a mono status bar on top (count, filters, period, legend) and a footer (pagination, notes). First column sticky. Ranked-on columns get an accent underline in the header. |
| **Phone grid** (below `md`) | **No sideways scrolling: the stats are the point of the screen.** Each player is two lines: position block, name, team, position chips and status on top; every ranked stat on one shaded line underneath, lined up under a single header (`--n` columns). At 9+ stats the numbers drop to 11 px. The name line ends with `14 GP · 3 left` (games played last 30, games left this week). Rest of week values show one decimal. Classes `.pg-head`, `.pg-row`, `.pg-cells`. Chosen over a squeezed one-line table and a heat strip (mockups: https://claude.ai/artifact/HKCmHiRGreZQNkx6r8f6BN, option B2). |
| **Position chip** | One chip per eligible position (`C,LW` → two chips), condensed 700 11 px, position colour on a 16 % tint of itself. The label is always shown, so colour is a second cue. Macro `pos_chips()` in `web/templates/_components.html`. |
| **Rank shading** | Classes `s4`…`s1` on cells, computed per column; `s4` also bold `--strong`. Lower-is-better stats (GAA) flip the order. Always show the legend (worse ▢▢▢▢ better). |
| **Status tag** | Condensed 700 11 px. DTD = `--dtd` outline; IR / OUT = `--inj` fill; healthy = em dash. |
| **Form tag** | HOT = `--up` fill; COLD = `--down` outline. Last-30 pace vs season pace, ±15 % (threshold to tune). |
| **Week strip** | 7 boxes (M–S), 12 × 14 px. Grey = game, accent = off-night game, past days 30 % opacity, `out` text when injured. Header letters mark today (underline) and off-nights (accent). Needs specs 047–049. |
| **Verdict blocks** (Projection) | Three panels with 58 px condensed numbers: my wins (accent block), ties (outlined), their wins (position-block colours). Largest numbers in the app. |
| **Win / lose cells** (H2H, Projection) | Winner `s3` + bold; loser `--dim`. H2H adds ◀ ▶ pointing at the winner; Projection adds a centred "who leads" bar and a `CLOSE` tag for margins under 10 %. |
| **Buttons** | Primary = accent fill; secondary = panel + border. 4 px radius, sans 600 14 px. |
| **Empty / loading** | Plain sentence in `--muted` inside the grid panel; loading uses the same panel with a mono "Loading…" status bar. |

## Wiring

Decided with the owner on 2026-11-05: built Tailwind, self-hosted fonts, follow the system theme.

- **Sources:** `web/styles/` holds `app.css` (tokens + component classes such as `.pos`, `.chip`,
  `.seg`, `.dt`, `.s1`–`.s4`, `.tag`), `tailwind.config.js` (colours and font families point at
  the tokens, e.g. `bg-panel`, `text-muted`, `font-cond`) and `package.json`.
- **Output:** `npm run build` writes `web/static/app.css`, which is committed. `base.html` links
  it with a content-hash `?v=` so browsers pick up changes. See `RUNNING.md`.
- **Theme:** dark by default, light under `prefers-color-scheme: light`. A page opts in to that by
  overriding `{% block theme_attr %}{% endblock %}`; pages not yet redesigned keep the default
  `data-theme="light"`.
- **Shading:** `analysis.waiver_ranking.shade_levels` returns a 0–4 level per cell, computed across
  the whole ranked pool (not the page) so shades don't shift when paging; templates add `s{level}`.
- **Order:** redesign page by page, Waiver Wire first (done); check live and `/demo/*` for each.
  Shared pieces are Jinja macros in `web/templates/_components.html` (`pos_chips` so far).
- **Dynamic class names** (`pchip-{{ pos }}`, `s{{ level }}`) must be in the `safelist` in
  `tailwind.config.js`, or the build drops them.

## Open questions

- Watchlist tab and the 7-day rank change column appear in mockups but need new data; treat as
  future work, not part of the redesign.
- HOT / COLD form tag and the week strip are specified but not built yet (week strip needs specs
  047–049).
