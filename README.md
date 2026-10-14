# Do great shooters shoot when the points say to?

A pre-registered study of catch-and-shoot decisions in the NBA's public
2015-16 player-tracking data.

**The question.** When Stephen Curry, LeBron James and James Harden (and the
league) catch the ball 16-30 ft from the basket, do they shoot when the
expected points say they should?

**The rules.**

- Every test and threshold was committed to this repository before the code
  that used it ran ([REGISTRATIONS.md](REGISTRATIONS.md), in commit order).
- The held-out test games were never read.
- Every failed gate stays failed.
- The full record, mistakes included, is in [record/](record/).

## The story in one paragraph

Inverse optimization rests on one idea. If a choice solves a problem, its
first-order condition reveals the cost you can't see.

- **The earlier attempt.** On 2014-15 shot logs, I tried to recover players'
  costs from defender distance at the shot, and it failed. That distance is
  an outcome of shooting: in this tracking data, defenders close about 4 ft
  between catch and release.
- **This repository's approach.** It measures space at the catch, before the
  decision. That delivers the one thing a first-order condition can: a
  marginal rate of substitution, the exchange rate between a foot of space
  and seconds of shot clock.
- **Release timing** is where a timing condition can be tested directly. The
  answer is a corner, not a trade-off: shooters release at a mechanical floor.
- **What neither design can deliver** is the value of the shot not taken. Three
  instrument sets were too weak for a selection model to recover it. The
  record shows the precision any instrument would need (SE on ρ of about 0.02)
  against what the three sets achieved (0.06-0.16).

See [record/thread.md](record/thread.md) for the longer version.

## Headline results

Intervals are 95%, from a game bootstrap unless stated otherwise. Catches
are at 16-30 ft, in non-test games.

**What a foot of space is worth**

| Result | Value |
|---|---|
| A foot of space at the catch, in shot-clock seconds, league (pooled) | **7.1 s/ft** [6.5, 7.8] |
| The same, median player, partial pooling (219 players) | **7.8 s/ft**, IQR 6.1-11.8 (6.9 without the 28% whose clock response is indeterminate) |
| Curry; LeBron; Harden (shrunk) | 5.1 [3.2, 13.3] (11th percentile); 6.1 [3.5, 17.0]; clock-indeterminate |
| Trailing by 5+ minus leading by 5+ | **+2.1 s/ft** [+1.2, +3.1] (8.8 vs 6.6; bootstrap over players) |
| Threes vs mid-range (point estimates) | 8.8 vs 5.3 s/ft |
| Measured value of a foot of space at the catch | −0.003 points [−0.0033, −0.0029] |

**Clock-added shots and release timing**

| Result | Value |
|---|---|
| Quality of the shots the clock adds (4-8 s vs 12-20 s) | −1.4 points [−6.0, +3.4]: unresolved |
| Rushed shots, last 4 s | −6.0 points [−8.7, −3.1] |
| Release brought forward at a fast closeout | 0.13 s [0.12, 0.14], about 1.5 ft of space kept |
| Gain − loss from waiting 0.1 s more at a fast closeout | −1.4 points [−2.2, −0.7]: the floor is mechanics |

**Passes and streaks**

| Result | Value |
|---|---|
| Pass to a shooter reaches the most open one (league) | **34.8%** [34.4, 35.2] vs 31.1% by chance (post hoc) |
| The same for LeBron; Harden | 50.5% [45.9, 54.8]; 53.9% [49.0, 59.1] |
| After a make, the next shot | −1.9 points [−3.2, −0.7]: no positive hot hand |

**The selection model.** It recovered passed-up shot quality within 0.03
in only 6, 1 and 8 of 20 synthetic runs, so it was closed without a real
fit.

**Gate errors.** Five gates were set below their own noise floor. Each was
caught and is numbered in the record.

## Stages

The full chronological table, with every number, is at the top of
[record/feasibility.md](record/feasibility.md). In short:

| Stage | Question | Outcome |
|---|---|---|
| Feasibility, second pass | Is there pre-decision variation at the catch? | Yes, after fixing the catch rule. Curry shoots 3% to 44% from tight to open. |
| Stage 2 | A trusted catch detector | Held-out eye check 57/60, PASS. |
| Stage 3a / 3b-prep / calibration 2 | Values and a make model | Two calibration gates failed (gate errors one and two). Attempt 2 passed on 60 fresh games. |
| Sequence, final round | Per-player choice models | No gated player proceeds. |
| Stage 4, 5a, 5c | Openness priced in clock seconds | About 7 s/ft for the league. The league under-shoots a points-maximiser at every clock state. |
| Stage 5b, strategy 2, Stage 6 | Hidden shot quality via selection | Three instrument sets too weak. Closed. |
| Review | Independent audit | Gate errors three to five recorded. Pooled league 7 s/ft. |
| Stages 7-12 | Clock-added shots, pooled map, passes, release timing, situation | As in the headline results above. |

## Data and provenance

**Data:** the 2015-16 SportVU feed (27 October 2015 to 23 January 2016; 621
usable games), archived publicly. The licence is not stated, and raw data is
not redistributed: this repository carries code, registrations and aggregate
results only.

**Tracking:**
[`linouk23/NBA-Player-Movements`](https://github.com/linouk23/NBA-Player-Movements),
folder `data/2016.NBA.Raw.SportVU.Game.Logs/` (upstream commit `f7d4cf2`).

**Play-by-play:**
[`sumitrodatta/nba-alt-awards`](https://github.com/sumitrodatta/nba-alt-awards),
`Historical/PBP Data/2015-16_pbp.csv`.

- It is joined on `GAME_ID == gameid` and `EVENTNUM == eventId`.
- The join follows the Hugging Face loader
  `dcayton/nba_tracking_data_15_16`.

## Reproduce

The scripts expect the data at `~/Documents/nba-tracking/` (`DATA` in
`scripts/build.py`). Edit that line to use another location. Python 3.12
with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

**1. Download** the 626 archives (about 3.5 GB) and the play-by-play (90 MB):

```bash
mkdir -p ~/Documents/nba-tracking/{raw,json,pbp}
cd ~/Documents/nba-tracking/raw
for s in $(cat ~/path/to/nba-catch-decisions/checks/all_stems.txt); do
  curl -sfL -o "$s.7z" "https://raw.githubusercontent.com/linouk23/NBA-Player-Movements/master/data/2016.NBA.Raw.SportVU.Game.Logs/$s.7z" || echo "FAIL $s"
done
curl -sfL -o ../pbp/2015-16_pbp.csv "https://raw.githubusercontent.com/sumitrodatta/nba-alt-awards/main/Historical/PBP%20Data/2015-16_pbp.csv"
```

**2. Parse.** Builds the timelines, shot releases, possession spells and
catches. It runs in three parts, in parallel, then merges them and extends
the game split:

```bash
for i in 1 2 3; do
  uv run python -I scripts/build.py --rule d3 --stems out/s4/stems$i.txt --all-players --cleanup --out out/s4/part$i &
done; wait
uv run python -I scripts/s4_data.py                  # merge parts, checks/split_all.json
uv run python -I scripts/poss.py build out/s4        # possession points and margin
```

**3. Each stage, in order.** Each script names its registration commit in
its docstring.

```bash
# Stage 3b-prep and calibration attempt 2: make model and values
uv run python -I scripts/s4_make.py
uv run python -I scripts/s4_make.py --score-only
uv run python -I scripts/s4_cont.py
uv run python -I scripts/s4_checks.py

# Final round
uv run python -I scripts/s5_final.py

# Stage 4
uv run python -I scripts/s6_clock.py

# Stage 5a: motion features, then analysis
for w in 0 1 2 3; do uv run python -I scripts/s7_motion.py $w 4 & done; wait
uv run python -I scripts/s7_make.py

# Stage 5c
uv run python -I scripts/s7_map.py

# Stage 5b
uv run python -I scripts/s8_heck.py excl
for r in 0.0 0.3 0.6; do uv run python -I scripts/s8_heck.py synth $r; done

# Stage 5b, strategy 2
uv run python -I scripts/s9_heck2.py falsify
uv run python -I scripts/s9_heck2.py excl
for r in 0.0 0.3 0.6; do uv run python -I scripts/s9_heck2.py synth $r; done

# Stage 6
for w in 0 1 2 3; do uv run python -I scripts/s10_frames.py $w 4 & done; wait
uv run python -I scripts/s10_state.py
uv run python -I scripts/s11_b.py
uv run python -I scripts/s11_c.py excl
for r in 0.0 0.3 0.6; do uv run python -I scripts/s11_c.py synth $r; done

# Stage 7
uv run python -I scripts/s12_clock_added.py power
uv run python -I scripts/s12_clock_added.py confirm

# Stage 8
uv run python -I scripts/s13_pooled_er.py

# Stage 9
for w in 0 1 2 3; do uv run python -I scripts/s14_pass_frames.py $w 4 & done; wait
uv run python -I scripts/s15_pass_open.py

# Stage 10
uv run python -I scripts/s16_release_timing.py

# Stage 11, plus the post-hoc like-for-like addendum
uv run python -I scripts/s17_pass_open_shooter.py
uv run python -I scripts/s17b_conditional.py

# Stage 12
uv run python -I scripts/s18_er_by_situation.py
```

**Earlier passes, and the work before the 621-game set,** used:

- `build.py --games pass1|pass2`, `gate.py` and `gate2.py`;
- `heldout.py`, `shot_eye.py`, `dp_eye.py` and `dp2.py`;
- `split.py`, `values.py`, `vshoot2.py`, `values2.py` and `choice.py`.

**What carries over from the original run:**

- The game split, the calibration games and the stem lists ship in `checks/`
  and `out/s4/stems*.txt`, so a re-run uses the same games.
- Seeds are fixed in the scripts.
- The small result JSONs from the original run are in `checks/` and
  `out/s*/`.

**Caveat:** this section was reconstructed from the scripts and the session
logs. It has not been re-executed from a clean checkout.

## References

Methods draw on:

- **Skinner (2011):** the clock-threshold form.
- **Cervone, D'Amour, Bornn and Goldsberry (2014):** valuing possessions
  from tracking.
- **Sandholtz, Mortensen and Bornn (2019):** zone-level allocation.
- **Bocskocsky, Ezekowitz and Stein (2014):** rhythm and shot difficulty.
- **Chang and colleagues (2014):** defender height.
- **Goldman and Rao (2012):** pressure.

## Credits

Built in 2026 with an AI coding agent under pre-registered rules. Every test
and threshold was committed before it ran, and every stage is in the record.
The gates were audited by a second, independent agent.

## Licence

Code: [MIT](LICENSE). The tracking and play-by-play data belong to their
sources and are not included.
