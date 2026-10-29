# UVIT: Source Smasher

A 60-second tap-to-smash arcade game inspired by AstroSat's Ultra Violet Imaging Telescope (UVIT).
Smash stars, noise and rare sources (AGNs, RR Lyrae stars, galaxies). Avoid meteors and space rocks.

## Files

| File | What it is |
|---|---|
| `index.html` | The complete game: HTML, CSS and JavaScript in one file. No build step, no server, no audio files. |
| `tests/test_game.py` | Automated mechanics test (Playwright + Chromium), desktop and touch-phone viewports. |

## Run it

1. Double-click `index.html`. It opens in any modern browser (Chrome, Edge, Firefox, Safari).
2. Optional local server (handy for testing on a phone on the same Wi-Fi):
   ```
   cd uvit-source-smasher
   python3 -m http.server 8000
   ```
   Then open `http://localhost:8000` (or `http://<your-computer-ip>:8000` on the phone).

Fonts load from Google Fonts. Offline, the game still works and falls back to system fonts.
Best score and the mute setting are saved in the browser's local storage.

Controls: tap or click sources. `Esc` or `P` pauses. The game auto-pauses when the tab is hidden.

## Tuning the game

Everything tunable lives in the `CONFIG` object near the top of the `<script>` in `index.html`.

**Point values** — `CONFIG.types.<type>.points`
```js
star:    { points: 10, ... }
noise:   { points: 15, ... }
rrlyrae: { points: 40, ... }
agn:     { points: 50, ... }
galaxy:  { points: 60, ... }
```

**How often each object appears** — `weight: [start, end]`. These are relative chances, blended
from the start of the round to the end. Meteors start at `0` and ramp to `11`, so they appear more late in the round.
`hazardFreeSeconds` keeps the first few seconds hazard-free.

**Difficulty curve** — `CONFIG.spawn`
- `intervalStart` / `intervalEnd`: seconds between spawns (0.95 s → 0.36 s)
- `maxStart` / `maxEnd`: max objects on screen (5 → 13)
- `speedStart` / `speedEnd`: speed multiplier (1.0× → 1.6×)
- Per-type `life` (seconds on screen), `speed` (px/s) and `r` (size in px)

**Other knobs**
- `roundSeconds` (60), `lives` (3), `comboWindow` (2.4 s before a combo expires)
- `multipliers`: `[{at:10,x:2},{at:5,x:1.5},{at:3,x:1.2}]`
- `filterFlip`: first event at 12 s, every 15 s, lasts 7 s, +20 bonus, brightness `threshold` 0.6
- `minTapRadius`: minimum touch radius in px (26)
- `discoveryChance`: chance of an info card after the first discovery of each rare type

**FUV/NUV brightness per source** is set in `makeObj()` and `STAR_CLASS`. Hot stars, spiral galaxies and AGNs
are FUV-bright; warm stars, RR Lyrae and AGNs are NUV-bright; elliptical galaxies, cool stars and noise never light up.

## Scoring rules

- Points earned = `round(base × multiplier)` + filter bonus (if the source glows in the active filter).
- The floating label shows the points actually earned, with the `base × multiplier` breakdown underneath.
- Meteors and rocks cost one life and reset the combo. They never remove points.
- Missing a target or tapping empty space costs nothing.
- When tapping where a target and a hazard overlap, the target wins.

## Test checklist

Run with `python3 tests/test_game.py` (needs `pip install playwright` and `playwright install chromium`).
The script edits `URL` at the top to point at the file you want to test.

All checks below passed on desktop (1280×800, mouse) and phone (390×780, touch):

- [x] Play starts the 3-2-1-GO countdown, then the round
- [x] Star +10, Noise +15, RR Lyrae +40, AGN +50, Galaxy +60
- [x] Tapping the same object twice scores once
- [x] Combo multipliers: hits 1–10 earn 10, 10, 12, 12, 15, 15, 15, 15, 15, 20
- [x] Combo expires after 2.4 s idle
- [x] Filter Flip highlights the right sources and pays +20
- [x] Rock and meteor each cost a life, reset combo, keep score
- [x] Tapping empty space is harmless
- [x] Pause freezes timer and object movement; Resume continues
- [x] Late round reaches level 5 with the final-10-seconds state
- [x] Objects stay inside the play area, below the HUD
- [x] Results screen appears when the timer hits zero, with all stats
- [x] Zero lives ends the round early
- [x] Best score persists after a browser refresh
- [x] Play Again, Restart and Quit to Menu reset all state
- [x] Sound toggle works and persists
- [x] No horizontal overflow at phone width
