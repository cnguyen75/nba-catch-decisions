# NBA catch decisions: feasibility pass

Does the public 2015-16 SportVU tracking contain enough **pre-decision**
variation (defender positions at the catch, before the shoot/don't-shoot
choice) to support a choice model? This repo answers that question only. There
is no cost model and no fitting, and it makes no claim about any player.

It follows a negative result in `~/Documents/NBA-Inverse-Shot-Optimization`
(branch `redesign`). There, defender distance was measured at the shot, so it was
a consequence of the choice rather than a cause.

## Data and provenance

- **Tracking:** `linouk23/NBA-Player-Movements`, `data/2016.NBA.Raw.SportVU.Game.Logs/`
  (upstream commit `f7d4cf2`). The NBA's public SportVU feed was scraped before
  it ended on 23 Jan 2016, and there is **no licence**.
- **Play-by-play:** `sumitrodatta/nba-alt-awards`, `Historical/PBP Data/2015-16_pbp.csv`.
  It is joined to the tracking on `GAME_ID == gameid` and `EVENTNUM == eventId`,
  following the Hugging Face loader `dcayton/nba_tracking_data_15_16`.
- **Raw data is never committed.** It lives in `~/Documents/nba-tracking/`,
  outside the repo. Only aggregates are published.

Games, chosen by rule (the earliest two with GSW, the earliest two with CLE,
the earliest with HOU):

| file | game id |
|---|---|
| 10.27.2015.NOP.at.GSW | 0021500003 |
| 10.31.2015.GSW.at.NOP | 0021500035 |
| 10.27.2015.CLE.at.CHI | 0021500002 |
| 10.28.2015.CLE.at.MEM | 0021500011 |
| 10.28.2015.DEN.at.HOU | 0021500010 |

## Running

```bash
uv sync
uv run python -I scripts/extract.py ~/Documents/nba-tracking/raw ~/Documents/nba-tracking/json
uv run python -I scripts/build.py      # timeline, releases, catches -> out/
uv run python -I scripts/gate.py       # gate numbers -> out/results.json
```

## Pre-registration (committed before any number was computed)

### Conventions

- **Coordinates:** court x is 0–94 ft and y is 0–50 ft. The baskets are at
  (5.25, 25) and (88.75, 25). All distances are horizontal (x, y) unless a
  height (z) is named.
- **Timeline:** the moments of all events in a game are concatenated and
  deduplicated on (quarter, game_clock), keeping the first occurrence. They are
  then sorted by quarter and by game clock, descending. Consecutive timeline
  frames are **contiguous** if their game clocks differ by at most 0.06 s.
- **Target players:** Stephen Curry (201939, GSW), LeBron James (2544, CLE),
  James Harden (201935, HOU).

### Join

- Each PBP row is joined to the tracking event with the same game id and
  `EVENTNUM == eventId`. Hit rate = joined FG attempts / PBP FG attempts
  (`EVENTMSGTYPE` 1 or 2) in the five games.
- **Check on 20 random joined events** (seed 0, all event types). For each:
  - the PBP period equals the event's quarter;
  - the PBP clock (`PCTIMESTRING`) lies within the event's game-clock range,
    with 2 s of slack;
  - **for FG attempts,** the PBP shooter is the player nearest the ball at the
    detected release;
  - plus a still of the event's last frame and its PBP description, looked at by eye.

### Shot release

For each PBP FG attempt by **any** player (so the attacking-basket rule has
votes), the search runs over the timeline frames in the event's game-clock range.

1. **Arrival** `t_a`: the first frame where the ball is within 3 ft of either
   basket and z ≥ 9 ft. If there is none (an air ball), `t_a` is the frame of
   the ball's maximum z in the window.
2. **Release** `t_r`: the last frame before `t_a` where the ball is within 3 ft
   of the shooter (any z).
3. **Valid only if** all of these hold:
   - z at `t_r` is at least 6 ft (hand height or above);
   - the ball-to-shooter distance increases from `t_r` to `t_r + 5` frames;
   - the ball-to-basket distance (nearest basket at `t_a`) decreases from `t_r`
     to `t_r + 10` frames.

   Otherwise the release counts as "not located".
4. **Shot-location hit rate** = located releases / joined FG attempts. It is
   reported overall and for the target players.
5. **Eye check:** for 10 target-player shots (seed 1), a GIF is rendered with
   the upstream `Event` animation class, with the release frame marked. Each is
   scored by eye as correct if the marked frame is within about 0.2 s of the
   visible release.

### Attacking basket

For each (team, period), the attacking basket is the majority vote, over that
team's located releases, of the basket nearest the ball at `t_a`. A (team,
period) pair with no located release takes the opposite of the other team's
basket in that period.

### Catch

- **Control:** P controls the ball in a frame if the ball is within 3 ft of P,
  z ≤ 8 ft, and P is the nearest player to the ball.
- **Possession spell:** a maximal run of P's control frames, merged across gaps
  that last at most 1.0 s, in which no other player controls the ball and the
  ball stays at z ≤ 8 ft. This keeps dribbles and fumbles inside one possession.
  A shot (z > 8) or another player's control ends the spell.
- **Catch** = the first frame of a spell. It requires the 5 preceding frames to
  be contiguous and not P's control, so a catch is never inferred at a data gap.
- **Counted catches** are those that meet both conditions:
  - **Frontcourt:** P is in the attacking half at the catch frame, within 47 ft
    of the attacking basket.
  - **Shot clock running:** the shot clock is not null at the catch frame and
    has decreased 12 frames (0.48 s) later. Catches at those frames must also be
    contiguous.
- **Recorded at the catch:**
  - `d_basket`: P's distance from the attacking basket.
  - `open_catch`: the nearest opponent's distance to P.
  - `rim_prot`: the nearest opponent's distance to the attacking basket.
  - `shot_clock`.
  - `t_next`: seconds from the catch to the end of the spell, i.e. P's next
    action (shot release, pass or loss), in game-clock seconds.
- **Source** of the catch (descriptive only): the last player to control the
  ball before the catch. It is "teammate" (a pass), "opponent", or "none" (a
  rebound, loose ball, or start of data).

### Action after the catch

- A located release of a PBP FG attempt by P is **linked** to the latest
  counted-or-uncounted catch by P at or before `t_r`, provided no other player
  controls the ball between them. Catch-to-shot time = game clock at catch −
  game clock at `t_r`.
- **Categories:**
  - `cs`: shot within 1.5 s.
  - `shot4`: shot within 4 s (includes `cs`).
  - `noshot4`: no linked shot within 4 s.
- **Known limit, accepted:** shooting fouls with no FG attempt in the PBP, and
  shots whose release is not located, count as "no shot". The report gives the
  number of P's PBP FG attempts left unlinked.

### Openness at release

The nearest opponent's distance to P at `t_r`, for P's located shots. It is
reported next to openness at catch for the same shots, as the bridge to the old
`CLOSE_DEF_DIST`.

### The gate (per player; Curry primary, then LeBron and Harden)

Bands of `d_basket` at the catch: [0, 10), [10, 22), [22, 47] ft.

1. **Variation:** in every band with at least 10 counted catches, the IQR of
   `open_catch` is at least 3 ft. The 22+ band must itself have at least 10
   catches.
2. **Prediction:** in the 22+ band, split catches into terciles of
   `open_catch` (by the band's 1/3 and 2/3 quantiles). Then:
   - |P(cs | top tercile) − P(cs | bottom tercile)| ≥ 0.10;
   - its bootstrap 95% interval excludes zero. The bootstrap uses 10,000
     resamples of the band's catches with replacement, recomputes the terciles
     each time, seed 0, and takes the percentile interval.
3. **A choice to model:** 0.20 ≤ share of counted catches in `shot4` ≤ 0.80.

**Pass** if all three hold for at least one player with at least 60 counted
frontcourt catches.

If no player reaches 60 catches, the verdict is **"sample too small"**. In that
case, games needed = ceil(60 / that player's counted catches per game),
reported per player. That verdict is distinct from **"no variation"**, which
means criterion 1 or 2 fails with at least 60 catches.

### Stop rule

If the join or the shot location cannot be made to work within the session box
(3 h), stop and report that.

**Rule changes after this commit** are recorded below with the reason, before
re-running.

## Changes to the pre-registration

### R1: release arrival, the last episode rather than the first (before the gate was computed)

**What was seen.** Under the original rule, only 62% of FG attempts were
located. Among those, the shooter was nearest the ball at release in only 51%.
Tracing plays showed the cause:

- An event's moments start about 20 s before the PBP event and end at the PBP
  clock.
- So the window often contains the *previous* shot, frequently the opponent's,
  and "the first arrival in the window" picks that shot.
- Example: game 0021500003, event 14, Curry layup at 9:34. The window opens on
  an opponent shot at 593 s, while Curry's release is at about 578.8 s.

Only the join check and the release table had been looked at. No catch or gate
quantity had been computed.

**New rule.** Arrival frames, as before (ball within 3 ft of a basket, z ≥ 9),
are grouped into **episodes**: runs merged across gaps of 5 frames or fewer.

1. Scan the episodes from last to first.
2. For each, search for the release over the frames after the previous episode
   (or from the window start) up to the episode's first frame. The release is
   the last frame there with the ball within 3 ft of the shooter.
3. Apply the same three validity checks as before. The latest episode that
   yields a valid release is used.
4. If no episode does, fall back to the air-ball rule (the maximum-z frame of
   the window) and its checks.

Everything else is unchanged.

### R2: release search anchored on the PBP clock (before the gate was computed)

**What was seen.** After R1, 78% of FG attempts were located, but 18 releases
were shared by two different PBP events. The cause:

- Event moment windows are not reliably bounded. Some run on past their own
  PBP event and contain the next shot.
- Example: game 0021500003, event 82, Curry at 3:06. Its window contains
  Curry's next shot, event 88 at 2:45.
- Other windows end before their shot (113 cases where the shooter was "never
  near the ball").

Among located shots, the release preceded the PBP clock by 1.9–3.2 s in the
interquartile range (median 2.55 s). The PBP clock is reliable and the event
window is not.

**New rule.**

- The release search window is the deduplicated timeline frames in the PBP
  period with game clock in [pbp − 0.5 s, pbp + 10 s], where pbp is
  `PCTIMESTRING` in seconds. It no longer uses the event's moments.
- The R1 arrival episodes and validity checks apply within that window.
- Among all episodes yielding a valid release, use the one whose release clock
  is closest to pbp + 2.5 s. The air-ball fallback is unchanged.

The join (event number → PBP row) is unchanged and still supplies shooter,
period, clock and description. Still no catch or gate quantity had been
computed.

## Raw file checksums (SHA-256)

```
33c1eed43de032dc42b47f130c03a87ad2e70ee9287017d95819661ca7782747  10.27.2015.CLE.at.CHI.7z
1734f248b324b52eff271e606af300ae89d50059a38f46b7112761c94c4ff4a1  10.27.2015.NOP.at.GSW.7z
815cacfd9a583df862c2a38b9464f70b3db452f7ccd1986dd2e68d20f3c3388d  10.28.2015.CLE.at.MEM.7z
1a8c71f74cfdc29e809bda203755b4de6fe5de2ad997ecf1ad921284ac99eef2  10.28.2015.DEN.at.HOU.7z
17b4225ae1a9c1ac8d617238f29e0e067181c81d392ca4be122fd504efced603  10.31.2015.GSW.at.NOP.7z
b10a0e3ff6870d9a7559281e910ebaed12fd244938049b7384480be64dd0d21f  2015-16_pbp.csv
```

## Results

Gate numbers and the report are in
`~/Personal/site-handoff/tracks/nba-catch-decisions/` (`feasibility.md`,
`results.json`). The pre-registered verdict is **fail**: criterion 2 fails for
all three players.

These were added to `gate.py` **after** the gate numbers were seen. They are
reported separately and do not change the verdict:
`post_hoc_sensitivity` (teammate-pass catches only; criterion 2 at 22–30 ft)
and `power_crit2` (simulated power of criterion 2).

---

# Second pass: 10 Curry games (registered 2026-10-13, before any new data was scored)

This section was written and committed before any of the 8 new games was
downloaded. It governs the second pass. Where it is silent, the first-pass
rules above (with R1 and R2) apply unchanged.

### Sample

- **Gated:** Curry (201939) in the 10 earliest-dated GSW games in the archive.
  - The two already used: 10.27.2015.NOP.at.GSW and 10.31.2015.GSW.at.NOP.
  - Plus 8 more: 11.02.2015.MEM.at.GSW, 11.04.2015.LAC.at.GSW,
    11.06.2015.DEN.at.GSW, 11.07.2015.GSW.at.SAC, 11.09.2015.DET.at.GSW,
    11.11.2015.GSW.at.MEM, 11.12.2015.GSW.at.MIN, 11.14.2015.BKN.at.GSW.
- **Reported but not gated:** LeBron and Harden, on their first-pass games,
  with the fixed catch rule. They get numbers but no label.

### C1: fixed catch rule ("sticky" control)

**Why.** Under the old rule, the nearest player within 3 ft controlled the
ball. A defender briefly nearer the ball during the holder's own dribble
therefore ended his possession, and when it ended a new "catch" started.

**New control rule,** applied frame by frame:

- **Holder keeps the ball.** If the current holder H has the ball within
  3 ft and z ≤ 8 ft, H keeps control, whoever else is nearer.
- **Otherwise it passes to the nearest player.** Control goes to the nearest
  player with the ball within 3 ft and z ≤ 8 ft, or to nobody.
- **Resets.** The holder resets to nobody at a frame that is not contiguous
  with the previous one, or at a change of quarter.

**Unchanged:** possession spells (merging across gaps of 1.0 s or less, with no
other controller and z ≤ 8), the 5-frame clean pre-window, frontcourt, shot
clock running, the measures at the catch, the outcome linkage, and the
release rule.

**What counts as a catch.** A catch is the first frame of P's spell under
sticky control. Its source is recorded for reporting:

| Source | Meaning |
|---|---|
| teammate | a pass or handoff, including an inbound |
| opponent | a steal or deflection that ended in P's hands |
| none / self | a rebound, loose ball, or his own miss |

Under sticky control the ball must actually leave P's 3 ft (or go above 8 ft)
before anyone else can take control. So an opponent source now means the ball
really left him.

**Report only, not a gate:** before and after catch counts, by source, on the
two first-pass Curry games.

### Eye check of C1, before the gate runs

- **Sample:** 10 counted Curry catches drawn from the 8 new games (seed 3).
  Each is rendered with the catch frame marked, showing frames, ball height,
  and ball-to-player distance. The openness value is not displayed.
- **A hit** means the marked frame is within 0.2 s of a real start of
  possession: the ball arrives from elsewhere and was not already in his
  dribble.
- **The hit rate is reported.**
- **It is not a gate,** but if it is below 7/10, I stop and report before
  running the gate.

### C2: criterion 2 restricted to 22–30 ft

Criterion 2 now uses only catches with `d_basket` in [22, 30) ft. Its
thresholds are unchanged:

- |P(cs | top tercile) − P(cs | bottom tercile)| ≥ 0.10;
- a bootstrap 95% interval that excludes 0, using 10,000 resamples, seed 0,
  with the terciles recomputed each time.

Criteria 1 (bands 0–10, 10–22, 22+) and 3, and the 60-catch minimum, are
unchanged.

### C3: outcome labels (Curry only), with a decision rule

`gap` is the top-minus-bottom tercile difference in P(cs). Its CI is the
bootstrap interval above. Exactly one label applies, taken from the first
rule that matches:

1. **sample too small:** fewer than 60 counted catches.
2. **no variation:** criterion 1 fails.
3. **pass:** criteria 1, 2 and 3 all hold.
4. **no prediction:** the CI lies entirely below +0.10 (upper bound < 0.10).
5. **underpowered:** the CI includes both 0 and +0.10.
6. **unlabelled (named reason):** any case the four labels above don't cover.
   - Example: criteria 1 and 2 hold but criterion 3 fails.
   - Example: the CI excludes 0 and includes +0.10, but the point gap is below
     0.10.

   This is reported as such, and not forced into another label.

The labels are directional (positive means more open → more catch-and-shoot).
Criterion 2 itself still uses |gap|, as registered. A strongly negative gap
(CI below 0) would fall under rule 4.

**The gate runs once.** Its numbers are reported whichever way they go, and
then the work stops.

### C1a: brief opponent touches (recorded before any new game was scored or eye-checked)

**What was seen.** On the two first-pass Curry games, C1 cut counted catches
only from 83 to 80, and opponent-sourced catches from 22 to 18. Tracing the
remaining 18:

- **About 11 are real passes.** A teammate's pass passes within 3 ft of a
  defender for 1–4 frames in flight. The catch is real; only its source label
  is wrong.
- **About 5 are still the dribble flicker.** In each, Curry's previous spell
  ended 1–25 frames earlier and the ball strayed 4–7 ft on a dribble. A
  defender within 3 ft of the ball then held "control" for 1–13 frames.
- C1's "the holder keeps the ball within 3 ft" therefore does not cover your
  stated intent: a defender briefly nearest the ball during the shooter's own
  dribble does not end or start a possession.

**Rule added on top of C1.** A **brief opponent touch** is an opponent spell of
12 frames (0.48 s) or less.

1. **Merge.** If P's spell, then a brief opponent touch, then P's spell again,
   with the gap from the end of P's first spell to the start of his second
   at most 1.0 s, the two P spells merge into one possession. No catch is
   created.
2. **Source.** When a catch's source is computed, brief opponent touches are
   skipped and the spell before them is used. A pass that skims a defender is
   therefore labelled "teammate". Every catch carries a `brief_opp_touch` flag.

**Accepted cost.** A real steal or deflection off P that comes back to P within
1 s no longer creates a catch. Under the first-pass definitions this is rare.

Everything else in C1, C2 and C3 is unchanged.

## Second-pass results

The gate ran once, at `288db65`; see `out/v2/results.json`, copied to the
track folder. The C1 eye check scored 7/10, in `checks/eye_c1.json`.

**Curry's registered label is "no variation".**

- **Criterion 1 fails** in the 0–10 ft band only: IQR 1.9 ft with n = 14. The
  10–22 and 22+ bands are 4.8 and 4.7 ft.
- **Criterion 2 passes:** 22–30 ft, +41 pp, 95% CI [+26, +53].
- **Criterion 3 passes:** 30%.

Stopped here, as instructed.

---

# Decision after the second pass (Colin, 2026-10-13)

- **Proceed to building the dataset.** The registered label "no variation"
  stands; it came from the 0–10 ft band only (14 catches, IQR 1.9 ft).
- **The decision was made after seeing the numbers.** It is a post-hoc
  judgement that criterion 1 was mis-specified for the rim band, where
  geometry bounds openness. It is not a reinterpretation of the result.
- **Criteria 2 and 3 passed.**
- **The registered label scheme, with its residual label, is accepted.**

# Stage 2: trusted catch detector, then the full set (registered before running)

## Detector rules D1–D3

These are added on top of C1 + C1a. Everything else is unchanged: the 1.0 s
gap merge, the 5-frame clean pre-window, frontcourt, shot clock running, the
measures at the catch, release rules R1 and R2, and the outcome linkage.

- **D1, despike the ball track.** This happens first, and the cleaned track
  then feeds everything else, including the release rule.
  - Within each run of contiguous frames, and for each ball coordinate (x, y
    and z) separately, compute the centred 5-frame median.
  - Wherever the value differs from that median by more than 3 ft, replace it
    with the median.
  - A ball in smooth flight sits on its median, so only isolated jumps
    change. This targets the one-frame height jump seen in the eye check
    (15 → 3.4 → 15 ft).
- **D2, hysteresis on possession distance.** This handles the holding offset.
  - **Acquire:** the nearest player with the ball within 3 ft and z ≤ 8 ft.
  - **Keep:** the holder H keeps control while the ball is within **5 ft** of
    H and z ≤ 8 ft.
  - **Takeover:** another player Q takes control from H if Q is the nearest
    player to the ball, with the ball within 3 ft and z ≤ 8, for **6
    consecutive frames** (0.24 s). Control is then assigned to Q from the
    first of those frames.
  - **Reset:** control resets to nobody at a non-contiguous frame or a change
    of quarter.
- **D3, minimum duration.** After D2, any run of consecutive frames with the
  same controller that is shorter than **5 frames** (0.2 s) is set to "no
  controller". Spells, the gap merge, C1a and catches are then built as
  before. A catch therefore holds for at least 5 frames.

## Held-out eye check (gate)

**Held-out games.** Four GSW games drawn at random (seed 4) from the 31 GSW
games not used so far:

- 11.22.2015.GSW.at.DEN
- 11.30.2015.GSW.at.UTA
- 12.06.2015.GSW.at.BKN
- 01.08.2016.GSW.at.POR

The full list is in `checks/manifest.json`.

**Candidate pool.** The union, for Curry, of the counted catches from both
earlier detectors run on these games:

- the nearest-player rule (pass 1);
- C1 + C1a (pass 2).

Candidates within 5 frames of each other are merged, keeping the C1 + C1a
frame.

**Sampling.** Openness thirds are the tercile cuts of openness at the
candidate frame within the pool. Draw 20 candidates per third (seed 5), 60 in
all.

**Labelling, by eye, before D1–D3 is run on these games.** The sheet shows
the frames from −2 s to +1 s, the raw ball height, and the ball-to-Curry
distance. It does not show openness or any D-detector output. Each candidate
gets one label:

- `real`: a real start of possession by Curry, with the ball arriving from
  elsewhere (a pass, rebound, loose ball or steal). It is recorded with t*,
  the first frame the ball is in his hands, read from the trace to about
  ±2 frames.
- `not_catch`: anything else, recorded with its error type.

The labels are committed in `checks/heldout_labels.json` before D1–D3 is run
on these games.

**Scoring.**

- A `real` candidate is correct if D1–D3 reports a counted Curry catch within
  5 frames of t*.
- A `not_catch` candidate is correct if D1–D3 reports no counted Curry catch
  within 5 frames of the candidate frame.

**Gate.** At least 54 of 60 correct, and no openness third below 16 of 20.

**If it fails:** report the error types and stop. No tuning on the held-out
set.

**Known limitation.** The pool contains only catches that an earlier detector
found. So the check measures D1–D3's precision, and its recall relative to
that pool. It does not measure recall on catches that both earlier detectors
missed.

## If the gate passes: the full set (descriptive only)

**Games.**

- Curry: all 41 GSW games in the archive.
- LeBron: all 39 CLE games, reported but not gated.
- Harden: all 42 HOU games, reported but not gated.
- A game shared between these teams is built once.

Each game is extracted, processed, and its extracted JSON deleted. The .7z
archives stay in `~/Documents/nba-tracking/raw`.

**Reported numbers.** No model.

- catches per game;
- openness at catch by distance band;
- at 22–30 ft, the rate of shooting within 1.5 s and within 4 s by openness
  third, with bootstrap 95% CIs;
- time from catch to shot;
- openness at catch against openness at release;
- detector-artefact checks:
  - the per-game spread of catches per game, and any outliers;
  - catches by quarter;
  - catch frames bunched at the edge of the window;
  - spikes in catch-to-shot times.

## Stage 2 results

**Held-out eye check passed: 57/60 correct**, with 20/20/17 across the
openness thirds. All three errors are false catches in the tight third. The
files are `checks/heldout_score.json` and `checks/heldout_labels.json`.

**Full set:** 116 games built.

- Curry: 39 games and 1,119 counted catches.
- LeBron: 37 games and 1,327 catches.
- Harden: 42 games and 1,378 catches.

**Descriptive numbers only** are in `out/full/describe.json`, copied into the
track folder's `results.json`.

- At 22–30 ft, Curry's rate of shooting within 1.5 s rises from 5.3% in the
  tight third to 45.5% in the open third.
- **Data artefacts:**
  - The shot clock is null for whole games in three games, so the "shot
    clock running" rule excludes their catches.
  - One archive is empty.
  - One game has no tracking frames.
- Stopped here, as instructed.

---

# Stage 3a: detectors, values, power, synthetic recovery (registration part 1)

Registered 2026-10-13, before anything below was run. There is **no fit to a
real player in 3a**. The one exception is the crude pilot for T in the power
step: it is specified there, and its c estimates are neither saved nor
printed.

## Design (Colin, final)

**Question.** "When Stephen Curry, LeBron James and James Harden catch the
ball, do they shoot when the points say to?"

- **Players:** all three are gated under the same rules. Gates and decisions
  apply per player.
- **Unit:** a frontcourt catch with the shot clock running. The catch is
  defined by D1–D3 + C1 + C1a, and the missing-shot-clock exclusion stays as
  it is.
- **Actions:**
  - **shoot now:** his shot within 1.5 s;
  - **drive:** NBA definition, starting 20+ ft out and dribbled to within
    10 ft;
  - **pass:** the ball goes to a teammate without a drive;
  - **hold:** anything else (dribbling without driving, a shot after 1.5 s,
    a turnover).
  - If the drive/pass detector fails its gate, the primary model becomes
    binary (shoot now against continue), and the four-way model is a
    registered extension.
- **Choice model:** P(a | x) ∝ exp((V_a(x) − c_a) / T), with c_hold = 0 as
  the reference and one temperature T per player.
- **Headline parameter: c_shoot.**
  - 0 means he shoots exactly when the points say to.
  - Negative means a shooter's premium.
  - Positive means he passes up shots the points would take.
- **Secondary:** c_shoot by zone (rim, mid-range, above-break three, corner
  three). Corner threes may be too rare for some players.

## Citations for design choices

- **Skinner, B. (2011).** "The problem of shot selection in basketball."
  arXiv:1107.5793. Source of the threshold form of the shoot/continue
  decision, and of its prediction that players "wait too long".
- **Cervone, D., D'Amour, A., Bornn, L., Goldsberry, K. (2014).** "A
  multiresolution stochastic process model for predicting basketball
  possession outcomes." arXiv:1408.0777. Region and defender openness belong
  in the value model, and player skill enters through shrinkage.
- **Sandholtz, N., Mortensen, J., Bornn, L. (2019).** "Measuring spatial
  allocative efficiency in basketball." arXiv:1912.05129. Over- and
  under-shooting is measured at zone level.
- **"Leveraging expected action value",** Journal of Sports Analytics (2025).
  Each immediate action at a decision point is valued.

## Split (committed before any value model is fitted)

- **Game set:** the 116 built games, all GSW, CLE and HOU games in the
  archive.
- **Assignment:** games are permuted with seed 2026. In that order, each game
  goes to the split (train/validation/test) with the largest deficit against
  60/20/20 targets, summed over the gated players who appear in it. Ties go
  train, then validation, then test.
- **Shared games** (between two of these teams) get one label.
- **Test games are never touched in 3a.** They appear in no value model,
  pilot, synthetic run or eye check.
- **League data:** the value models train on catches by every player other
  than the three gated ones, in train-split games only. Validation-split
  games are used for calibration.
- **Stored in** `checks/split.json`.

## Data fix F1: unlocated shots make the action unknown

- **Rule.** The possession is P's spell from the catch to its end. The game
  clock interval [gc_end − 0.5 s, gc_catch] is compared with the plausible
  release interval of each PBP FG attempt by P whose release was not
  located: [pbp_gc + 0.5 s, pbp_gc + 5.0 s]. If they overlap, the catch's
  action is **unknown** and it is excluded from every model.
- **5.0 s** is the 95th percentile of the PBP lag seen in pass 1.
- **Precedence.** A located shot-now link takes precedence over F1.
- **Reporting.** The exclusion rate is reported per player.

## Data fix R3: close-range release

**Scope.** R3 applies to FG attempts whose PBP description contains
"Layup", "Dunk", "Tip", "Hook", "Putback", "Finger Roll" or "Alley Oop", or
states a distance of 8 ft or less. All other shots keep R1 + R2 unchanged.

**Within the R2 window and R1 arrival episodes:**

- **Release:** the last frame before the episode's arrival where the ball is
  within **4 ft** of the shooter (3 ft for other shots).
- **Validity:**
  - z at release ≥ 6 ft;
  - the ball within **12 ft** of the arrival basket at release;
  - arrival no more than **1.2 s** after release.
- **Dropped for close shots:** the "moving away over 5 frames" and "toward
  the basket over 10 frames" checks. The shooter moves with the ball there.
- **Choice of episode:** the one closest to pbp + 2.5 s, as in R2.
- **Air-ball fallback:** the maximum-z frame, with the same close-range
  validity checks.

**Eye check, gate 27/30.**

- **Sample:** 30 close-range FG attempts from train or validation games other
  than the pass-1 tuning games (seed 31). 20 are drawn from attempts
  currently unlocated and 10 from attempts currently located.
- **Labelling, by eye, committed before R3 runs:**
  - Each sheet shows ball height, ball-to-shooter distance and
    ball-to-basket distance over [pbp − 0.5 s, pbp + 6 s], with players drawn
    around the shooter. No detector output is shown.
  - Each attempt gets the release frame, or "not visible" if the data has no
    release.
- **Scoring:** R3 is correct if its release falls within 5 frames of the
  label, or if both say "not visible".

## Drive/pass detector (rules)

**Inside P's possession,** the spell from catch frame s to end frame e:

- **dribble:** a frame with ball z ≤ 1.5 ft and the ball within 5 ft of P.
- **drive:** frames i < j in [s, e] where:
  - P is ≥ 20 ft from the attacking basket at i;
  - P is ≤ 10 ft from it at j;
  - at least one dribble falls in [i, j];
  - i is at most 4.0 s after s.
- **pass:** no drive, and:
  - the next spell after e belongs to a teammate;
  - it starts within 1.5 s of e;
  - e is at most 4.0 s after s.
- **Precedence:** shoot now > unknown (F1) > drive > pass > hold.

**Held-out check, gate 54/60 with no class below 16/20.**

- **Sample:** 60 catches from **validation** games. These are not tuning
  games; tuning is limited to the pass-1 games.
- **Strata, by a cruder proxy, 20 each:**
  - "drive-like": P's minimum distance to the basket during the spell is
    ≤ 10 ft and he was ≥ 20 ft out at some point;
  - "pass-like": the next spell's owner is a teammate;
  - "other".
  - Shoot-now catches are excluded from the draw.
- **Labelling, committed before the detector runs on them:** each catch is
  labelled drive, pass or hold from a sheet showing:
  - P's track and the ball's track;
  - distance to the basket and ball height;
  - the next owner;
  - no detector output and no stratum.
- **Classes** for the per-class bar are the strata. The confusion matrix by
  eye label is also reported.

## Possession points (rule and check)

- **Offence:** P's team.
- **Events after the catch:** PBP rows in the catch's period with
  PCTIMESTRING-seconds < gc_catch, in EVENTNUM order. PBP lags real time, so
  an event logged at a smaller clock value than the catch happened after it.
- **The possession ends at the first of:**
  - a made FG by the offence (an "and-one" free throw at the same clock
    stays in the possession);
  - the offence's last free throw made, or missed and then rebounded by the
    defence;
  - a defensive rebound (rebounder's team, or team rebound, not the
    offence);
  - an offence turnover;
  - the end of the period.
- **Points:** the offence's made FGs (3 if "3PT" is in the description,
  otherwise 2) and made FTs (description not starting with "MISS"), from
  the catch to the end.
- **Score margin at the catch:** offence minus defence, from the last SCORE
  before the first post-catch row.
- **Eye check:** 20 random league catches from train/validation games (seed
  20). The PBP rows around each are printed, and each computed end and point
  total is judged against them. Reported as a hit count; it is a check, not
  a gate.

## State features at the catch

- distance to the attacking basket;
- zone:
  - rim: ≤ 6 ft;
  - three: ≥ 23.75 ft, or a corner;
  - corner three: |y − 25| ≥ 22 ft and within 14 ft of the baseline;
  - above-break three: the other threes;
  - mid-range: the rest;
- openness at catch;
- rim protection;
- shot clock;
- best teammate's openness (the maximum over teammates of each one's
  nearest-opponent distance);
- score margin.

# Stage 3a registration, part 2: values, choice model, power, synthetic

Registered before any value model is fitted or any choice model is run.

## Data for the value models

**League catches:** counted catches by every player except the three gated
ones, in **train-split** games. Validation-split league catches are used
only for calibration reports.

**Excluded:**

- catches with action unknown (F1);
- drives from catches inside 20 ft (see "Choice set");
- catches missing any state feature.

## V_shoot

**Data:** league shoot-now attempts, i.e. located shots within 1.5 s of the
catch. The outcome is make/miss from the PBP.

**Model:** logistic regression (scikit-learn 1.5.2, L2 with C = 1.0, lbfgs)
on:

- d and d² (distance at the catch, ft);
- zone one-hot (rim, mid, above-break three, corner three);
- log(1 + openness at catch), and that term × the three indicator.

**Value:** V_shoot = P(make) × points, with points = 3 for corner and
above-break zones and 2 otherwise. This is the immediate value of the shot
only (see the note below).

**Calibration, on validation-game league shoot-now attempts:**

- ECE over 10 equal-count bins of predicted P;
- a decile table;
- **limit: ECE ≤ 0.03.**
- If it fails, it is reported and V_shoot is not used for synthetic or
  power until a registered fix.

**Player skill:** a per-zone logit offset δ_z for each gated player.

- Fitted on his train-game shoot-now attempts only, by maximum a posteriori
  with prior N(0, 0.3²). This is shrinkage toward zero, as in Cervone et al.
- A zone with no attempts gets δ = 0.

## V_drive, V_pass, V_hold (and V_continue)

**Outcome:** possession points after the catch (rule in part 1).

**Model:** for each action a, ridge regression (alpha = 1.0) on league train
catches whose observed action is a. Features, standardized:

- d and d²;
- zone one-hot;
- openness (capped at 15);
- rim protection (capped at 20);
- shot clock;
- best teammate's openness (capped at 20);
- score margin (clipped to ±20).

**V_continue,** for the binary model, uses the same regression on all
league catches that are not shoot-now.

**Player offsets:** δ_a = Σ residuals / (n_a + 50) over his own train
catches with action a. The 50 is the shrinkage pseudo-count.

**Reported on validation league catches:**

- RMSE against an intercept-only model;
- a decile table of predicted against observed.

**Assumption, selection on observables.** Each continuation value is the
mean outcome of catches where that action was chosen in that state. Using it
as the value of that action had it been chosen assumes nothing unobserved
drives both the choice and the outcome. This is an assumption, not
something tested.

**Known mismatch (flagged, not fixed, per the design).** V_shoot counts only
the shot's own points. The continuation values are whole-possession points,
which include offensive rebounds and free throws. To size the gap, the mean
possession points after league shoot-now catches minus mean V_shoot is
reported.

## Choice model

P(a | x) ∝ exp((V_a(x) − c_a) / T), with c_hold = 0.

- **Four-way:** actions {shoot, drive, pass, hold}; parameters (c_shoot,
  c_drive, c_pass, T).
- **Binary:** {shoot, continue}; parameters (c_shoot, T).

**Primary model:** four-way if the drive/pass detector passes its gate,
binary otherwise.

**Choice set:** drive is available only if d_basket ≥ 20 ft at the catch.
Catches with an observed drive and d_basket < 20 are excluded and counted.

**Fitting:** maximum likelihood (scipy 1.14.1, BFGS on c's and log T),
used for synthetic recovery only in 3a.

**Secondary:** c_shoot by zone, with zone-specific c_shoot and the other
parameters shared. Only its expected standard errors are reported in 3a.

## Pilot T (the only real-data choice fit in 3a)

The primary model is fitted by maximum likelihood on each gated player's
train-game catches. **Only T is written out.** The pilot's c estimates are
discarded in code and never printed.

## Power (Fisher information)

**Setup:**

- each player's real train-game catch states;
- his fitted V's, including his offsets;
- T = his pilot T.

**Parameter settings:** c_shoot ∈ {−0.2, 0, +0.2}, with c_drive = c_pass = 0.

**Fisher information:** for each catch, J_iᵀ (diag p − p pᵀ) J_i, summed over
catches. J_i is the Jacobian of the utilities with respect to the
parameters.

**Reported:** standard errors of c_shoot and T, and the minimum detectable
|c_shoot| at 80% power (two-sided α = 0.05): MDE = 2.80 × SE(c_shoot).

**Decision, per player:** evaluated at c_shoot = 0.

- **Proceed** if MDE ≤ 0.15 points.
- **Otherwise underpowered,** with games needed = ceil(train games ×
  (MDE / 0.15)²).

## Synthetic recovery

**Setup:** for each player that proceeds, a made-up player built on his real
train catch states and fitted V's.

**Settings** (as (c_shoot, c_drive, c_pass, T)):

- S1: (−0.2, +0.1, −0.1, T_p);
- S2: (0, 0, 0, T_p);
- S3: (+0.2, −0.1, +0.1, 1.5 T_p).

For the binary model, only c_shoot and T apply. **20 seeds per setting**
(seeds 100–119).

**Limits:** for each parameter, 2.576 × SE from the Fisher information at
the true setting, which is the ideal estimator's 99th percentile of |error|.

**Pass rule:**

- a run passes if every parameter is within its limit;
- a player passes if at least 18 of 20 runs pass in every setting.

**Ideal-estimator power of this rule:** the probability that it passes when
the errors are exactly N(0, I⁻¹), computed by simulation (100,000 draws,
seed 7) and reported before synthetic runs.

**Every run is reported.** Players who don't proceed get no synthetic runs.

## Stage 3a results: stopped at the V_shoot calibration limit

| Item | Result | Bar | Outcome |
|---|---|---|---|
| R3 close-range release | 18/30 | 27 | **Rejected** |
| Drive/pass detector | 53/60 | 54 | **Fails;** the primary model is binary |
| Possession points | 20/20 | check only | After a code fix to the registered rule |
| V_shoot ECE | 0.0545 | 0.03 | **Fails** |

- **The 0.03 limit is underpowered.** A perfectly calibrated model passes it
  only 29% of the time at n = 1,231.
- **The miscalibration is still real** (p = 0.013).
- **Not run,** per the registration: power and synthetic.
- **The report** is at `~/Personal/site-handoff/tracks/nba-catch-decisions/feasibility.md`.

# Stage 3a registration, part 3: decisions after the stop (Colin, 2026-10-13)

Registered before any of it runs.

## Notes required by the design

- **Continuation values depend only weakly on the state.** On validation,
  V_continue's RMSE is 1.1595 against 1.1607 for an intercept-only model, and
  its predicted range is 0.88–1.17. So c_shoot is identified mainly through
  openness (and distance) moving the value of shooting, not through the
  alternatives.
- **The close-range release detector runs 0.3–0.5 s late.** In the R3 eye
  check, R1 + R2 placed only 5 of 10 located close shots within 0.2 s, mostly
  7–14 frames late. A **registered sensitivity** will therefore rerun the
  main fit with a **2.0 s** "shoot now" window instead of 1.5 s.

## C-rule: powered calibration rule (replaces the fixed ECE ≤ 0.03)

- **Why it changed.** At the validation sample size (1,231 shots), a
  perfectly calibrated model with the observed predictions has a median ECE
  of 0.034, and passes 0.03 only 29% of the time. The fixed limit was below
  the noise floor.
- **New rule.** V_shoot passes if its validation ECE (10 equal-count bins)
  is at or below the 95th percentile of the ECE that a perfectly calibrated
  model would show with **the same predicted probabilities**. That reference
  is found by simulating y ~ Bernoulli(p̂) from the model's own validation
  predictions: 5,000 draws, seed 0, the same binning.
- **Reporting.** The decile table is reported either way.

## V_shoot fix (scored once on validation)

**Base model:** logistic regression (L2, C = 1.0) on league train
shoot-now attempts, with features:

- natural cubic spline in distance (knots at 4, 10, 18, 23.75 and 28 ft;
  boundary knots at 0 and 47);
- zone one-hot;
- log(1 + openness), and that term × distance/10 (openness-by-distance);
- that term × the three indicator;
- shot clock at the catch, and its square/100.

**Recalibration:**

- 5-fold cross-validated out-of-fold predictions on the train attempts
  (folds by game, seed 5).
- A Platt map (a logistic fit of y on the out-of-fold logit) is fitted to
  them.
- The final model is the base model refit on all train attempts, with the
  Platt map applied.

**Scoring:** once on validation under the C-rule. **If it fails:** stop and
report, with no further tuning.

## One scale: possession points

- **V_shoot = P(make | x) × points + g(zone).**
- **g(zone)** is the mean over league train shoot-now catches in that zone
  of (possession points − actual shot points, i.e. made × 2 or 3). It is the
  value of offensive rebounds and free throws after the shot, and is
  reported by zone.
- Player make-probability offsets are unchanged (MAP, prior N(0, 0.3²)).
- **Sensitivity, immediate-shot scale (V_shoot without g):**
  - **In 3a, synthetic only.** For each synthetic run, the data is generated
    with possession-scale V_shoot and also fitted with immediate-scale
    V_shoot. The mean c_shoot bias that causes is reported.
  - **In the real fit, later:** registered as a sensitivity.

## Drive/pass retest (once)

**Fixed detector, D-v2.** Same as before except for the pass rule.

- **Touch:** the ball is within 3 ft of a player, at **any height**, for at
  least 2 consecutive frames.
- **pass:** no drive; P's possession ends within 4.0 s of the catch; and the
  first player other than P to touch the ball within 2.0 s after the end is
  a teammate. This covers lobs and alley-oops caught above 8 ft, and
  handoffs.
- **drive:** unchanged. There is a frame i in [s, min(e, s + 4.0 s)] where P
  is ≥ 20 ft from the attacking basket, a later frame j ≤ e where P is
  ≤ 10 ft from it, and at least one dribble (ball z ≤ 1.5 ft, within 5 ft of
  P) in [i, j]. **The drive's start is any such frame i**, not its actual
  start.
- **hold:** everything else.
- **Precedence:** shoot now > unknown > drive > pass > hold.

**Labelling rule (identical wording, used by eye):**

- **drive** if at any moment in the first 4 s of the possession he is 20+ ft
  from the basket, and later in the same possession he has dribbled to
  within 10 ft;
- **else pass** if the possession ends within 4 s of the catch and the next
  player to touch the ball (any height, within 2 s) is a teammate;
- **else hold.**

**Fresh held-out set.**

- 60 catches from **validation** games, excluding the 60 catches of the
  first check.
- Tuning used the pass-1 games and the first check's 60.
- Proxy strata as before, 20 each, seed 43. Shoot-now and unknown catches
  are excluded.
- Sheets show the possession and the following 2 s: tracks, ball height,
  and teammate and opponent positions **at the next touch**. No detector
  output.
- **The D-v2 detector is a separate script** (`scripts/dp2.py`). It is run
  only after the labels are committed.

**Gate:** 54/60, no stratum below 16.

- **Pass:** the four-way model is primary.
- **Fail:** binary is primary, four-way is a registered extension, and
  nothing is retried.

## Then

Power, then synthetic recovery, as registered in part 2, using:

- the possession-scale V_shoot;
- the primary model this retest decides;
- V_drive, V_pass and V_hold refit with the D-v2 action labels.

**Stop before any real-player fit.** The pilot T is the only exception,
with c discarded as before.

### Amendment to the retest, before the D-v2 detector or the fresh sample ran

**Problem.** "Touch at any height" would credit a lob that passes 1–2 ft
horizontally over a defender's head (ball at 13–14 ft) to the defender.
Tuning-set plays D24 and D53 show exactly this.

**New rule.** A touch is the ball within 3 ft horizontally **and at most
12 ft high** (within reach), for at least 2 consecutive frames. The labelling
rule reads the same: "the next player to touch the ball (within reach)".

**Tuning-set re-read of D55.** It was my eye error, not a detector miss: the
catch was at 18.1 ft, and he passed 20 ft only after reaching 7 ft. No
change.

### Amendment 2 to the retest, before the fresh sample was drawn or D-v2 ran on it

**Problem.** On the tuning set, the "touch" rule (within 3 ft, z ≤ 12, 2
frames) credits passes to defenders the ball flies past just after release.
It scored 51/60 against 53 for the old rule.

**Replacement pass rule.** **pass** if there is no drive, P's possession ends
within 4.0 s of the catch, and either:

- the next D3 possession spell starts within **2.0 s** of the end and
  belongs to a teammate; or
- before any other spell starts, a **located FG release by a teammate**
  falls within 2.0 s after the end (a lob or alley-oop caught above 8 ft and
  finished at once).

The labelling rule reads the same: "the next player to take possession of
the ball, or to shoot it on the catch, within 2 s".

**Tuning-set finding.** First-check plays D24 and D53, which I labelled
"lob pass", were in fact **the catcher's own shots**. Each was a located FG
attempt by P, released just after 1.5 s (so "hold") and rebounded by the
defence.

Together with D32 (rule semantics) and D55 (catch at 18.1 ft), at least 4 of
the first check's 7 "errors" were my labels. The first gate's FAIL stands as
committed.

**Sheet change for the fresh set.** A ball-to-basket trace is added, so
shots are visible on the sheet. No detector output is shown.

### Results so far, and a scope rule (registered before power or synthetic ran)

**Results so far.**

- **V_shoot fix: PASSES the powered rule.** ECE 0.0385 against a null 95th
  percentile of 0.0492. g(zone): rim 0.143, mid 0.216, above-break 0.130,
  corner 0.143.
- **Drive/pass retest: FAILS, 51/60** (strata 16/16/19). **Binary is
  primary**, four-way is a registered extension, and nothing is retried.

**Support problem found after the fix passed.** The fixed V_shoot
extrapolates beyond its data. Mean predicted make probability is 0.57 at
35–47 ft, and up to 0.97 for a 45 ft catch, against 0.41 at 26–30 ft. 98.0%
of league train catch-and-shoot attempts are within 30 ft (only 70 beyond).
The gated players' shoot-now attempts beyond 30 ft number 1, 7 and 6.
Validation calibration cannot see this, because validation shots come from
the same range.

**Scope rule (for Colin's sign-off).** The choice-model unit is restricted to
catches with **d_basket ≤ 30 ft**, the support of the shot model. V_shoot is
not modified. This removes 21.6% (Curry), 27.7% (LeBron) and 35.5% (Harden)
of train catches. Power and synthetic run on the restricted set.

**Synthetic, immediate-scale bias (detail of the part 3 sensitivity).** Each
synthetic data set, generated with possession-scale V_shoot, is also fitted
with V_shoot_imm. The per-run difference (c_shoot fitted on the immediate
scale minus the truth) is reported, as its mean and SD per setting.

## Stage 3a results (part 3): stopped, no player proceeds

| Item | Result |
|---|---|
| V_shoot fix | **PASSES** (ECE 0.0385 ≤ 0.0492) |
| Drive/pass retest | **FAILS** 51/60; binary is primary |
| Scope rule | d ≤ 30 ft (shot-model support) |
| Power: Curry, Harden | Pilot T diverges, so underpowered (model degenerate) |
| Power: LeBron | MDE 0.34 > 0.15, so underpowered (~113 train games needed) |
| Synthetic | **Not run** (no player proceeds) |

**Diagnostic.** League P(make) on catch-and-shoot threes is flat in openness
at the catch (39/36/39% by tercile), so V_shoot does not move with openness.
For Curry and Harden, shooting falls as V_shoot − V_continue rises (slopes
−1.06 and −3.69).

The report is in the track folder's `feasibility.md`.

---

# Stage 3b-prep (registered 2026-10-13, before anything below ran)

The scope rule (catches within 30 ft) is **approved**. LeBron is
**reported, not gated**: his numbers are computed, but no decision rests on
them.

## Finding recorded first (Colin's review)

**"Openness does not move the value of shooting" (Stage 3a) was an
artefact.** It came from measuring openness at the *catch* on *taken* shots.
Taken catch-and-shoot threes almost never have a defender close at the catch;
the defender closes during the shot.

**Colin's tables:**

- Of 2,607 league catch-and-shoot threes, 74 had the defender within 6 ft at
  the catch.
- By defender distance at **release**, the same shots run **34% (0–2 ft) to
  47% (8–12 ft)**.
- All league threes run **29% to 43%**.

**My reproduction,** non-test league catch-and-shoot threes (linked and
located, three by "3PT" in the PBP): 2,713 shots, 62 with the defender
within 6 ft at the catch.

| Defender distance (ft) | 0–2 | 2–4 | 4–6 | 6–8 | 8–12 | 12+ |
|---|---|---|---|---|---|---|
| **At release:** make % (n) | 30.8 (78) | 33.6 (703) | 38.1 (1,028) | 42.5 (463) | 46.2 (264) | 46.3 (177) |
| **At catch:** make % (n) | 0 (2) | 28.6 (14) | 28.3 (46) | 34.9 (195) | 38.3 (872) | 40.0 (1,584) |

The "all league threes" table is reproduced after the full parse (step 1),
which is when release openness exists for every shot.

## 1. Parse every usable game in the archive

- **Scope:** all 626 correctly named archives, built with the D1–D3 + C1a
  rules, R1 + R2 releases (no R3), and the all-player catch features.
- **Skipped:** empty archives and games with no tracking frames, with a log.
- **Load:** 3 build processes in parallel, each deleting extracted JSON after
  loading.
- **Split:**
  - The 116 already-split games keep their labels (test stays test).
  - **New games** (no gated player appears in them) are assigned 80% train
    and 20% validation at game level (seed 2027). None are test.
  - League value models train on train games and calibrate on validation
    games, excluding the gated players' catches and shots, as before.

**New per-shot fields** (located FG attempts):

- defender distance at release (nearest opponent to the shooter at t_r);
- shooter's distance to the arrival basket at release;
- zone at release (same zone rule);
- shot clock at release;
- **jump shot:** PBP description contains "Jump";
- **shot type:** catch-and-shoot if linked to the shooter's catch with
  catch-to-release ≤ 1.5 s, otherwise off-the-dribble or other.

**New per-catch fields:** P's nearest-opponent distance at the catch frame +
k frames, for k = 5, 10, …, 40.

## 2. Make model on release openness

**Data:** all league **jump shots** (located; train games). Three is taken
from "3PT" in the PBP.

**Model:** logistic regression (L2, C = 1.0) on:

- a natural cubic spline in release distance (knots as before);
- zone one-hot (at release);
- log(1 + release openness), and × distance/10, and × three;
- catch-and-shoot indicator, and C&S × log(1 + release openness);
- shot clock at release, and its square/100.

**Calibration:** a Platt map from 5-fold game-grouped out-of-fold predictions
(seed 5).

**Scored once** on validation league jump shots under the powered rule (ECE
≤ the perfect-model 95th percentile, simulated from the model's own
validation predictions, 5,000 draws, seed 0). Decile table reported.

- **If it fails:** stop and report.
- **Cross-check, reported only:** a logistic of make on log(1 + release
  openness) + the distance spline + three, fitted separately on all train
  jump shots and on the **late-clock subset (shot clock at release ≤ 4 s)**.
  The two openness slopes are compared.

## 3. Counterfactual release openness, for every catch

- **delta** = the median catch-to-release delay (s) of league train
  catch-and-shoots (reported), rounded to the nearest 5 frames.
- **open_cf** = P's nearest-opponent distance at frame catch + delta. This is
  observed for every catch, whether or not he shoots.
- **Reported by zone:** median open_cf − open_catch, the correlation, and the
  share with open_cf < open_catch.

## 4. V_shoot (one scale)

**V_shoot = P(make | open_cf, distance at catch, zone at catch, C&S = 1,
shot clock at catch − delta) × points + g(zone).**

- g(zone) is as registered in part 3, recomputed on the new training set.
- **Player skill:** a per-zone logit offset, MAP with prior N(0, 0.3²),
  fitted on the player's train catch-and-shoot attempts, evaluated at their
  *actual* release openness and distance.
- Within the 30 ft scope.

## 5. V_continue and the selection-bias statement

**V_continue** is as before (ridge on the registered state), refit on the
larger league train set, plus the shrunk player offset.

**Selection-bias direction (assumption made explicit).** Among open catches,
the players who continued instead of shooting were selected: they continued
when continuing looked better than average. So **V_continue(open) is
overstated**, the value gap V_shoot − V_continue is understated for open
catches, and **c_shoot is biased toward a shooter's premium** (negative).

**Registered sensitivity: Dubin–McFadden correction.**

- **Reduced-form choice:** a logit of shoot-now on the full state, on league
  train catches. It includes best teammate openness and score margin.
- **Correction term:** for continuing catches, with P = P(shoot):
  λ = P·ln P / (1 − P) + ln(1 − P).
- **Corrected regression:** possession points on the state **excluding best
  teammate openness and margin** (the exclusion restrictions), plus λ. The
  corrected V_continue is the prediction with the λ term removed.
- **Flag:** the exclusion is strong. Best teammate openness plausibly affects
  continuation points directly, and Colin's instruction names the shot
  outcome as the excluded equation. Applied to the continuation equation as
  the only place a correction can use it, it is an assumption, not a
  finding.
- **Validated first on synthetic data with known values:**
  - league train states;
  - a known continuation function (the uncorrected regression's fitted
    values minus the exclusion variables' terms);
  - a shoot choice driven by a known gap plus the exclusion variables;
  - an unobservable correlated with continuation points (correlation 0.3).
- **Pass:** the corrected regression recovers the true continuation function
  to within 0.02 points (mean absolute error) where the naive one misses by
  more. Otherwise the correction is not used, and that is reported.

## 6. Checks, in order (each player; LeBron reported, not gated)

1. **Value gap is positive in openness.** Within 22–30 ft train catches, the
   OLS slope of (V_shoot − V_continue) on open_cf must be **> 0**, with a
   bootstrap 95% CI excluding 0 (2,000 resamples, seed 0). Otherwise the
   player stops here.
2. **Power rule** (part 2): pilot T, Fisher information, proceed if
   MDE ≤ 0.15.
3. **Synthetic recovery** (part 2 limits and pass rule; S1–S3; 20 seeds),
   with the immediate-scale bias also reported.

**Reported in all cases:** the value-gap table by openness bin (0–4, 4–6,
6–8, 8–12, 12+ ft, by open_cf), old values (Stage 3a) and new side by side,
per player.

**Stop before any real fit of c.**

## 7. Measure the selection in V_continue (Colin; amendment registered before anything ran)

This **replaces step 5's assumed bias direction and validation rule** where
they differ.

### (a) Control group, continuation side

- **Groups,** league non-gated players with **at least 40** train catches at
  22–30 ft:
  - **control:** shoot-now rate there under 2%;
  - **shooters:** the rest.
- **Fit, for each group:** the V_continue regression (same features, ridge
  α = 1, *unstandardized* openness so the slope is in points per ft) on that
  group's **continuing** catches at 22–30 ft, train games.
- **Reported:** the openness-at-catch coefficient with a **game-clustered
  bootstrap 95% interval** (2,000 resamples, seed 0).
- **Decision:** if the shooters' slope is **above the upper end of the
  control group's 95% interval,** selection is present and (c) becomes the
  main path. Otherwise the naive V_continue stands and (c) is a
  sensitivity.

### (b) The same check on the shot side

- **Comparison:** within 1-ft bins of openness at catch, the mean
  counterfactual release openness (catch + delta) of catches that became
  shoot-now, against those that did not. League train catches at ≤ 30 ft.
- **Difference = non-shot − shot,** averaged over bins weighted by non-shot
  counts, by zone.
- **Rule:** if it exceeds 1 ft in a zone, it is **subtracted** from the
  counterfactual for non-shooting catches in that zone, and this is reported.

### (c) Dubin–McFadden correction

- **Choice:** the reduced-form shoot/continue logit on the full state.
  **Exclusion restrictions:** best teammate openness and score margin enter
  the choice and are left out of the corrected continuation equation.
- **Term and corrected value:** λ = P·ln P/(1 − P) + ln(1 − P). The
  corrected V_continue is the prediction without λ.
- **Synthetic validation before any real use:**
  - league train catch states and the same sample sizes;
  - known true continuation values, with a known openness slope;
  - choice and outcome errors with correlation 0.3 (normal errors; the
    choice is a threshold on a latent index with logistic marginal);
  - 20 seeds (300–319);
  - 95% intervals by bootstrap that re-estimates the first stage (200
    resamples).
- **Pass:** the corrected estimate's interval contains the true openness
  slope in **≥ 18 of 20** seeds, **and** the naive estimate visibly fails:
  its interval excludes the truth in **≥ 10 of 20** seeds.
- **If not:** the correction is not shown to work. The naive values stand,
  with the bias direction stated.

### Reporting

c_shoot's power and synthetic recovery are reported under **whichever
V_continue the rule selects**. The other is a sensitivity.

## Stage 3b-prep results: stopped at the make-model calibration rule

- **Make model** (all league jump shots on release openness): validation ECE
  0.0163, against a perfect-model 95th percentile of 0.0159 (n = 11,550).
  **Fails narrowly.**
- **Not run:** V_shoot, 7a, 7c, the checks, power and synthetic.
- **Computed:**
  - all league threes by release openness: 28.1% → 40.8%;
  - late-clock openness slope 0.479 [0.327, 0.671], against 0.344 overall;
  - delta 0.96 s (25 frames);
  - shot-side check: rim 1.33 ft and above-break 1.02 ft adjusted; mid and
    corner not adjusted;
  - g(zone) recomputed.
- **Report:** the track folder's `feasibility.md`.

### Calibration decision (Colin), registered before re-scoring

**What happened.** The registered powered-ECE rule **failed, and stays
recorded as failed** (0.0163 against 0.0159). That rule tests *perfect*
calibration. At 11,550 validation shots, it detects errors too small to
matter for this model.

**The replacement was chosen after seeing the result.** The reason: the
quantities that pass into c_shoot are

- the overall level, since a constant error passes one-for-one into c_shoot;
- the openness gradient, which is the slope that identifies c;
- no large local error at any openness;

not a perfect-calibration test.

**Replacement criteria.** The **same model** (no refit, no tuning) is scored
**once** on the **same validation shots:**

1. **Level:** |mean predicted − mean observed| ≤ 0.01.
2. **Gradient:** |(pred rate in 8+ ft − pred rate in 0–4 ft) − (obs rate in
   8+ ft − obs rate in 0–4 ft)| ≤ 0.03, by release-openness bins.
3. **Bins:** for each release-openness bin (0–2, 2–4, 4–6, 6–8, 8–12,
   12+ ft), |mean predicted − observed| ≤ 0.04.

ECE and the decile table are reported as information.

**If all three hold,** the make model is fit for purpose, and the registered
sequence continues:

- V_shoot with the counterfactual release openness;
- V_continue;
- 7a–7c;
- the value-gap check;
- power;
- synthetic recovery.

It stops before any real fit of c.

**If any fails:** stop and report. No fix on the spent validation games.

**"No refit" in practice.** The model was not saved, so it is reconstructed
by the identical deterministic code path (same data, same seeds, lbfgs). It
must reproduce the scored ECE (0.0163) and Platt map exactly. Otherwise it
is not the same model, and I stop.

### Re-score result: FAILS (bins), stop

The same model (Platt map reproduced to every digit, ECE 0.016258) was scored
once on the same validation shots.

| Criterion | Result | Limit | Outcome |
|---|---|---|---|
| Level | 0.3766 predicted vs 0.3760 observed, \|diff\| 0.0006 | ≤ 0.01 | pass |
| Gradient | predicted change 0.0672 vs observed 0.0909 (0–4 ft vs 8+ ft), \|diff\| 0.0236 | ≤ 0.03 | pass |
| Bins | 0–2: +0.016; 2–4: −0.001; 4–6: +0.010; 6–8: −0.019; 8–12: −0.014; **12+: −0.040019** | ≤ 0.04 | **FAIL** |

**The 12+ bin misses by 0.00002.** It has n = 259 and 123 makes, an
observed rate of 0.4749 against 0.4349 predicted. One fewer make would put
the error at about −0.036. The binomial SE of the observed rate is 0.031, so
the 0.04 bin limit is about 1.3 SE in that bin.

**Per the rule:** stop and report. There is no fix on the spent validation
games, and V_shoot, V_continue, 7a–7c, the checks, power and synthetic were
not run.

---

# Stage 3b-prep, calibration attempt 2 (Colin: option 2; registered before running)

## Recorded first

The replacement **bins criterion** (|error| ≤ 0.04 in every
release-openness bin) was set at about **1.3 standard errors of its noisiest
bin** (12+ ft: n = 259, SE 0.031). It was therefore **the same error as the
old project's v3b gate:** a perfect model fails it often. The re-score
failure, by 0.00002, stays on the record.

## 1. Fresh calibration set

- **60 games** drawn at random (**seed 2028**) from the 474 training games,
  stored in `checks/calib_games.json`.
- **Removed from training for every league model:** the make model, g(zone),
  V_continue, the control-group fits and the Dubin–McFadden first stage.
- **The gated players' own catches are unaffected.** They are never used in
  league models, and their train/validation/test labels stay as in
  `checks/split.json`, so their offsets, power and synthetic use the same
  games as before.
- **League models train on the remaining 414** training games.
- **Validation games are spent** and not scored again. Test games stay
  untouched.

## 2. Registered model change (the only change)

- **Release openness main effect:** a **natural cubic spline** with knots at
  **2, 4, 6, 8 and 12 ft** (boundary knots 2 and 12, linear beyond; openness
  capped at 30), **instead of log(1 + openness)**.
- **Unchanged:** the openness interactions, which still use log(1 +
  openness) (× distance/10, × three, × C&S), plus the distance spline, zone,
  shot type and shot clock.
- **Platt recalibration:** from 5-fold game-grouped out-of-fold training
  predictions (seed 5), as before.

## 3. Criteria, scored once on the 60 fresh games (league jump shots)

1. **Level:** |mean predicted − mean observed| ≤ 0.01.
2. **Gradient:** |(predicted 8+ ft rate − predicted 0–4 ft rate) − (observed
   8+ ft rate − observed 0–4 ft rate)| ≤ 0.03.
3. **Bins:** for each release-openness bin (0–2, 2–4, 4–6, 6–8, 8–12,
   12+), |predicted − observed| ≤ max(0.04, 2 × SE), with SE =
   sqrt(obs × (1 − obs) / n).

ECE and the decile table are reported as information.

## 4. Outcome

**Pass:** continue the registered sequence:

- V_shoot with the counterfactual release openness (using this model);
- V_continue;
- 7a–7c;
- the value-gap check;
- power;
- synthetic recovery.

It stops before any real fit of c.

**Registered sensitivity for the main fit (later).** Rerun the main fit with
V_shoot's openness gradient scaled by r = (observed 8+ minus 0–4 change) /
(predicted 8+ minus 0–4 change) from this scoring, and report how much
c_shoot moves. The rescaling holds each catch's P(make) at its 0–4 ft level
and multiplies the openness-driven difference above that level by r.

**Fail:** stop and report. No further calibration attempts.

## Calibration attempt 2 and the registered sequence: results (stopped, no gated player proceeds)

**Make model (attempt 2), scored once on 58 fresh games with jump shots
(5,546 shots): PASS.**

| Criterion | Result | Limit |
|---|---|---|
| Level | 0.0095 | 0.01 |
| Gradient | 0.0068 (observed-over-predicted ratio 0.881) | 0.03 |
| Bins | all within max(0.04, 2 SE); worst 12+ ft, 0.029 vs 0.083 | |
| ECE (information) | 0.0153 | |

**V_shoot,** with the counterfactual release openness:

- delta 0.96 s (25 frames);
- shot-side adjustment: rim 1.33 ft and above-break 1.01 ft subtracted for
  non-shooters;
- g(zone): rim 0.107, mid 0.135, above-break 0.162, corner 0.168.

**7a, control group:**

- control (28 players, 2,260 catches): slope 0.0010 [−0.0143, 0.0158];
- shooters (310 players, 58,743 catches): 0.0086 [0.0054, 0.0119];
- **no selection detected.** The control interval is wide.

**7c, Dubin–McFadden synthetic validation:** corrected covers 20/20 seeds;
naive misses only 3/20 (bias −0.0009 at ρ = 0.3). **Not shown to work** under
the rule. **Naive V_continue is primary**, and the Dubin–McFadden version
(real openness slope 0.0052 against 0.0100 naive) is a sensitivity.

**Check 1, value-gap slope in counterfactual openness at 22–30 ft:**

| Player | Slope [95% CI] | Outcome |
|---|---|---|
| Curry | 0.0050 [−0.0059, 0.0183] | **FAILS:** stops here |
| Harden | 0.0187 [0.0097, 0.0293] | passes |
| LeBron (not gated) | 0.0162 [0.0109, 0.0216] | passes |

**Power:** the pilot T diverges for Harden (496) and LeBron (720). MDE is
142 and 186, so **underpowered**; the games-needed numbers are meaningless
at a diverged T.

**Synthetic:** not run, because no gated player proceeds.

**Diagnostic** (slopes of P(shoot) on the value gap only; no c):

- **all ≤ 30 ft:** Curry −0.27, LeBron −2.57, Harden −1.05;
- **22–30 ft:** +0.05, +0.16, −1.82.

The rim zone's gap is negative (−0.16 to −0.22) while players shoot 18–33%
of rim catches. **The make model is jump shots only, and it is applied to rim
catches whose shots are mostly layups and dunks, so it understates V_shoot at
the rim.**

---

# Final round (Colin; registered 2026-10-13 before running)

## Recorded first: the scope mismatch

**What went wrong.** The make model is trained on **jump shots only**, but
the choice unit included catches from 0–16 ft, including rim catches.

- A catch at the rim is usually finished with a layup or dunk, which goes in
  far more often than a jump shot from the same spot.
- Valuing it with the jump-shot model understated V_shoot there, giving a
  value gap of −0.16 to −0.22 while players shot 18–33% of rim catches.
- That pulled the choice-model slope negative.
- The mismatch should have been caught when the scope was registered.

**Fix: the choice unit is catches 16–30 ft from the basket.** That is the
jump-shot model's valid range, and catch-and-shoot is the decision being
studied.

## 1. Gated sequence on the 16–30 ft unit (Curry, Harden; LeBron reported, not gated)

**Rerun, as registered:**

- **Check 1:** the value-gap slope on counterfactual release openness, 22–30 ft
  train catches. OLS, bootstrap 95% CI (2,000 resamples, seed 0), must
  exclude 0 on the positive side.
- **Power:** pilot T on 16–30 ft train catches (c discarded), Fisher
  information; proceed if MDE ≤ 0.15 at c = 0.

**If a player passes both, then in order:**

1. **Synthetic recovery** (S1–S3 × 20 seeds, part 2 limits and pass rule).
2. **The real fit, scored once on test games:**
   - c_shoot and T are fitted by maximum likelihood on the player's train +
     validation catches (16–30 ft);
   - c_shoot is reported with a Fisher 95% interval;
   - **once** on his test-game catches: per-catch log-likelihood of the
     fitted model, against (i) his train + validation shoot rate as a
     constant, and (ii) the model with c = 0 and T refit;
   - test-game values use the same league models and his train-game
     offsets.
3. **Sensitivities:** the gradient-scale rerun (openness-driven part of
   P(make) above the 0–4 ft level × 0.881), and Dubin–McFadden V_continue.

**If no player passes, the gated sequence stops there.**

## 2. Descriptive result (no gate): revealed against measured value of openness

**Data:** each player's non-test catches (train + validation games) at
16–30 ft, shoot-now against continue.

**Definitions:**

- **Openness** = counterfactual release openness, open_cf (catch + 1.0 s,
  with the shot-side adjustment).
- **Reference openness** = the player's median open_cf, and his median
  openness at catch (V_continue's openness input).
- **gap** = V_shoot − V_continue (naive V_continue).
- **gap_dz** = the gap recomputed with both openness inputs at the reference
  values. It varies with distance, zone, shot clock, rim protection,
  teammates and margin; everything except openness. The stated wording "from
  distance and zone" covers all non-openness state.
- **gap_open** = gap − gap_dz.

**The four results:**

- **(a) Measured value of openness:** the OLS slope of gap_open on open_cf,
  in points per ft.
- **(b) and (c):** a logistic model, logit P(shoot now) = α + b·open_cf +
  c·gap_dz.
  - **(b)** = b, the change in log-odds of shooting per ft of openness;
  - **(c)** = c, per point of non-openness value gap.
- **(d)** = b / c, in points per ft: **the openness value players behave as
  if they see**, set against (a).

**Intervals:** bootstrap 95% (2,000 resamples of catches, seed 0). The
ratio's interval is percentile-based and reported as unstable if c's
interval includes 0.

**Plain-language reading per player:** "he behaves as if an extra foot of
openness were worth d points, against a measured a points."

## 3. Record

`feasibility.md` gets the full sequence (feasibility, Stage 2, 3a, 3b-prep,
the calibration rounds, this round), with nothing removed, plus a suggested
site paragraph for the outcome that occurs. **Then stop: the project's
record is complete.**

## Final round: results (the project record is complete)

**Gated, 16–30 ft unit:**

- Curry: check 1 FAIL (0.0050 [−0.0059, 0.0183]).
- Harden: check 1 pass (0.0187 [0.0097, 0.0293]); pilot T diverges (510),
  MDE 163, so **underpowered.**
- **No gated player proceeds.** The gated sequence stops: no synthetic, no
  real fit of c, test games never touched.
- LeBron (not gated): pilot T 0.73, MDE 0.246, which would be underpowered.

**Descriptive** (16–30 ft, non-test catches; bootstrap 95% intervals):

| | (a) measured pts/ft | (b) log-odds/ft | (c) log-odds per point of gap_dz | (d) = b/c pts/ft |
|---|---|---|---|---|
| Curry (n = 585, 134 shots) | 0.019 [0.015, 0.024] | 0.18 [0.10, 0.29] | −0.02 [−0.81, 0.85] | unstable (−9.2; [−7.6, 6.0]) |
| Harden (n = 596, 72) | 0.029 [0.024, 0.034] | 0.14 [0.03, 0.26] | 0.90 [−1.27, 2.97] | 0.15 [−1.24, 1.30] |
| LeBron (n = 610, 38) | 0.021 [0.017, 0.024] | 0.27 [0.19, 0.38] | −0.46 [−3.24, 2.23] | unstable (−0.59; [−3.09, 3.10]) |

**Reading.** The interval for (c) includes 0 for every player, so (d) is
reported as unstable, as registered.

---

# Stage 4: openness priced in shot-clock seconds (registered 2026-10-13, before running)

This is a new question with its own registration. **No earlier gate is
reopened.** It covers all three players, plus the league as the reference.

## Data and unit

- **Unit:** counted catches at 16–30 ft with the shot clock recorded,
  shoot-now against continue. Unknown actions are excluded.
- **League:** non-gated catches in **train** games, the 414 after the 60
  calibration games were removed.
- **Players:** each player's non-test catches (train + validation).
- **Values** are as built (possession scale):
  - V_shoot from the attempt-2 make model, with counterfactual release
    openness and its shot clock (catch clock − 1.0 s), so late shots are
    rushed;
  - **naive V_continue** (league ridge; plus the player offset for player
    catches).
- **Openness** = nearest-opponent distance **at the catch**, capped at 15 ft,
  in every regression.
- **Covariates (identical in steps 1 and 2):** shot clock (s), openness at
  catch, distance/10 and its square, zone dummies (mid as reference; above
  the break, corner), and best teammate openness (capped at 20).
- **Intervals:** bootstrap over **games** (1,000 resamples, seed 0). The
  player and league bootstraps are independent and paired by replicate
  index, for any quantity that combines them.

## 1. Measured value gradients (league)

OLS of gap = V_shoot − V_continue on the covariates.

- **g_clock** = the coefficient on shot clock (points per second).
- **g_open** = the coefficient on openness (points per ft).

## 2. Behavioural gradients (each player, and the league)

Logistic regression of shoot-now on the same covariates (unpenalized).

- **β_clock:** log-odds per second.
- **β_open:** log-odds per ft.

## 3. Exchange rate

- **Behavioural ratio** R_b = β_open / β_clock, against **measured ratio**
  R_m = g_open / g_clock, in seconds of clock per ft of openness. Under a
  single temperature they are equal.
- **Implied temperature** from the clock: T_clock = g_clock / β_clock.
- **Implied value of a foot of openness** = β_open × T_clock (points per
  ft), against the measured g_open.
- Reported per player (behavioural, from his catches; measured, from the
  league) and for the league.

## 4. Skinner's test

- **Value-maximiser:** shoots if and only if gap > 0, with his own values
  for players and league values for the league.
- **Implied shoot-now rate** in each shot-clock bin (0–4, 4–8, 8–12, 12–16,
  16–20, 20–24 s) = the share of catches with gap > 0.
- **Reported:** observed rate, implied rate, and the difference with an
  interval.
- **Reading:**
  - shooting **later** than the maximiser = observed below implied early in
    the clock and above it late (Skinner's "waits too long");
  - **earlier** = the reverse.
- **Caveat (stated):** V_continue is the average of what actually followed
  continuing, not of optimal continuation.

## 5. Power first (computed and reported before steps 3–4 are read)

- From the Fisher information of the step 2 logit at its fitted parameters,
  on each player's real catches: SE(β_clock), SE(β_open), and their
  covariance.
- **Smallest detectable difference** between R_b and R_m at 80% power:
  2.8 × SE(R_b), by the delta method.
- **Rule:** each player's exchange rate is reported with its interval
  regardless. A player is marked **"not individually resolved"** if his
  β_clock bootstrap interval includes 0, and the league estimate is the one
  to lean on for him.

## 6. Reporting

Everything, with the plain reading. `feasibility.md` gets its chronological
table and site paragraph updated.

## Stage 4 results

**Repo note.** A commit titled "Stage 4 script" (`50c2605`) holds the
registered script with identical content. Its message differs from the one
intended. The results below come from that committed script, and the working
tree was clean.

**Power** (Fisher information of the step 2 logit):

| Group | SE(β_clock) | Smallest detectable R_b − R_m (s/ft, 80%) |
|---|---|---|
| League | 0.0021 | 0.78 |
| Curry | 0.029 | 3.5 |
| LeBron | 0.040 | 5.2 |
| Harden | 0.030 | 2,568 (β_clock ≈ 0) |

**Measured (league train, 16–30 ft):**

- g_clock = −0.00196 pts/s [−0.0021, −0.0018];
- g_open (openness at catch) = **−0.00308 pts/ft** [−0.0033, −0.0029];
- R_m = +1.57 s/ft [1.42, 1.74].

**Behavioural:**

| Group | β_clock | β_open | R_b (s/ft) | Implied value pts/ft | Implied ÷ measured |
|---|---|---|---|---|---|
| League | −0.055 [−0.061, −0.050] | 0.394 [0.386, 0.403] | −7.1 [−7.8, −6.5] | **0.014 [0.013, 0.016]** | −4.6 |
| Curry | −0.088 [−0.151, −0.035] | 0.35 | −3.9 [−10.1, −2.3] | **0.008 [0.005, 0.020]** | −2.5 |
| LeBron | −0.100 [−0.191, −0.046] | 0.46 | −4.6 [−10.0, −2.5] | **0.009 [0.005, 0.020]** | −3.0 |
| Harden | −0.004 [−0.059, 0.062] | 0.46 | — | 0.23 [−0.50, 0.55] | **not individually resolved** (lean on league) |

**Skinner's test.** At every clock state the observed shoot-now rate is far
**below** the value-maximiser's.

| Clock bin | League observed | League maximiser |
|---|---|---|
| 0–4 s | 0.40 | 0.61 |
| 4–8 s | 0.25 | 0.70 |
| 8–12 s | 0.18 | 0.72 |
| 12–16 s | 0.13 | 0.69 |
| 16–20 s | 0.12 | 0.64 |
| 20–24 s | 0.19 | 0.42 |

Every interval excludes 0. The players show the same pattern. The shortfall
is largest mid-clock and smallest at both ends, so the result is
**under-shooting at every clock state**, not a specific "waits too long"
timing pattern.

---

# Stage 5a: motion features (registered 2026-10-13, before running)

**Scope.** Earlier gates stand. Test games are skipped entirely, as always.
This part adds features and compares models; **V_shoot is not rebuilt here**
(that waits for 5b).

## Features, from the frames (D1–D3 timeline, 25 Hz)

**Velocity rule.** A player's velocity at frame i is (position(i+1) −
position(i−1)) / (game-clock difference), computed only where the frames are
contiguous.

**Per counted catch (catch frame s, catcher C, team T):**

- **closing_pre:** take D, the nearest opponent to C at frame s. Average,
  over frames s−12 … s−1 (0.5 s), D's velocity projected onto the unit vector
  from D toward C, in ft/s (positive means approaching).
- **closing_post:** the same, over frames s … s+12.
- **catcher_speed:** |position(s+2) − position(s−2)| / 0.16 s.
- **set:** catcher_speed < 3 ft/s.
- **n_def6:** the number of opponents within 6 ft of C at frame s.
- **Catch source,** from the previous possession spell (same rule as the
  build: brief opponent touches skipped), with precedence inbound > offensive
  rebound > pass > other:
  - **inbound:** the previous owner is a teammate whose position at his last
    control frame is outside the court (x < 0 or > 94, y < 0 or > 50);
  - **offensive rebound:** a located FG release by team T falls between the
    previous spell's start and frame s, in the same quarter;
  - **pass:** the previous owner is a teammate (otherwise);
  - **other:** a loose ball, steal, own spell, or no previous owner.
- **Pass flight,** for passes only: time = clock at the passer's last control
  frame − clock at s; distance = |passer position there − C at s|. Set to 0
  with a flag for other sources.

**Per located shot (release frame t_r, shooter S):**

- closing_pre over t_r−12 … t_r−1, toward S;
- shooter_speed (±2 frames) and set (< 3 ft/s);
- n_def6 at t_r.

## Make-model comparison (league jump shots)

- **Train** = the 414 league training games; **evaluate** = the 60 fresh
  calibration games.
- **Current model:** the attempt-2 specification, refit identically.
- **Motion model:** the current model plus closing_pre (clipped ±15),
  shooter_speed (clipped at 25), set, and n_def6 (capped at 3). Same Platt
  procedure.
- **Reported:**
  - the registered criteria (level, gradient, bins with max(0.04, 2 SE)) for
    the motion model;
  - ECE for both;
  - **mean log loss** for both, and the difference (motion − current) with a
    bootstrap 95% interval over calibration games (1,000 resamples, seed 0).

"Improves" means the log-loss difference interval lies entirely below 0. Its
calibration is judged by the same criteria.

## Behavioural model with motion (the Stage 4 step-2 logistic)

- **Main:** the Stage 4 covariates plus closing_pre, closing_post,
  catcher_speed (clipped at 25), set, n_def6, pass flight time and distance
  (0 when not a pass), and catch-source dummies (pass as the reference).
- **Sensitivity:** the same, **without closing_post.** The window after the
  catch overlaps the decision itself, so the defender may be reacting to it.
- **Reported:** the openness and clock slopes, with and without motion, for
  the league and each player, with intervals (bootstrap over games, 1,000
  resamples). Same unit as Stage 4 (16–30 ft, shot clock recorded).

# Stage 5c: descriptive exchange-rate map (registered 2026-10-13, before running; no gates)

## Exchange rate (ER)

- **Definition:** ER = −β_open / β_clock, in **seconds of shot clock per
  foot of space**. It comes from the Stage 4 step-2 logistic (Stage 4
  covariates, no motion features) on the group's catches. It is positive when
  more space and less clock both raise shooting.
- **Data:** non-test catches (train, validation and calibration games) at
  16–30 ft, shot clock recorded, shoot-now against continue.
- **Intervals:** bootstrap over games, 1,000 resamples (seed 0; per-player
  seeds offset by rank).
- **"Resolved":** the β_clock 95% interval excludes 0. Unresolved players
  are listed but not ranked.

## League-wide map

- **Eligibility:** every player with **≥ 300** such catches.
- **Reported:**
  - the distribution of ER among resolved players (median, IQR, histogram
    counts);
  - the **ten highest and ten lowest** resolved;
  - Curry, LeBron and Harden's values and their percentile among the
    resolved (or "unresolved").

## Within-player variation (Curry, LeBron, Harden, and the league = all non-gated players)

**Cells:**

- score margin (offence's view): behind by 5+, within 5, ahead by 5+;
- period: 1–3 against 4th and overtime;
- home against away (home team from the PBP);
- catch source (5a): pass, offensive rebound, inbound, other.

**Each cell:** ER and its 95% interval, n, and shots.

**Thin cells:** fewer than 150 catches, fewer than 20 shots, or a β_clock
interval that includes 0. Their numbers are still reported, flagged.

## Stage 5a and 5c results (5b not started: it waits for review with Colin)

### 5a

**Motion features:** computed for 239,824 catches and 80,220 shots in
non-test games.

**Make model, 60 fresh calibration games, 5,512 shots:**

- Motion **does not improve** it. Log loss changes by −0.00014 [−0.00092,
  +0.00061].
- Both models pass all registered criteria:

| Model | Level | Gradient | Worst bin | ECE |
|---|---|---|---|---|
| Current | 0.0094 | 0.0072 | 0.026 | 0.013 |
| Motion | 0.0097 | 0.0062 | 0.026 | 0.015 |

- Standardized motion coefficients are small: shooter speed −0.09, closing
  +0.06, set −0.02, defenders within 6 ft +0.02.

**Behavioural slopes, Stage 4 against with motion:**

| Group | Openness slope | Clock slope | ER (s/ft) |
|---|---|---|---|
| League | 0.396 → 0.421 | −0.055 → −0.060 | 7.18 → 7.00 |
| Curry | 0.344 → **0.247** | | 3.86 → 2.54 [1.29, 5.78] |
| LeBron | | | 4.63 → 3.02 [1.17, 6.45] |
| Harden | | | unresolved (clock slope interval includes 0) |

Dropping the post-catch closing window changes nothing material.

### 5c (ER = seconds of shot clock per foot of space)

**League map:**

- 219 players with ≥ 300 catches; **98 resolved**.
- Median **5.08** s/ft, IQR 3.99–6.13.
- Highest: Deng 10.1, Thompson 9.3, Bradley 9.1, Casspi 8.7, Gordon 8.3.
  Upper intervals are wide.
- Lowest: Ibaka −8.5 (shoots more with more clock), Booker 1.8, Jack 2.0,
  Wade 2.0, Ellis 2.1.
- **Curry 3.93 [2.27, 10.07], 24th percentile; LeBron 4.63 [2.59, 10.08],
  42nd; Harden unresolved.**

**Within-player (league):**

| Cut | ER [95% CI] |
|---|---|
| Behind by 5+ | 8.12 [7.08, 9.48] |
| Within 5 | 6.70 [6.09, 7.42] |
| Ahead by 5+ | 6.97 [6.26, 7.90] |
| Q1–3 | 7.44 [6.86, 8.07] |
| Q4 + OT | 6.64 [5.89, 7.64] |
| Home | 7.25 |
| Away | 7.17 |
| Pass | 7.79 [7.24, 8.42] |
| **Other (loose ball, steal)** | **2.68 [2.13, 3.53]** |
| Offensive rebound, inbound | thin |

**Within-player (the three):** most cells are thin. Resolved: Curry
ahead-by-5+ 3.13, Q1–3 5.32, away 2.10, pass 3.88; LeBron Q1–3 4.23, away
4.77, pass 4.81. Harden has no resolved cell.

---

# Stage 5b: latent shot quality, bivariate probit with sample selection (registered 2026-10-13, before any measurement)

**Earlier gates stand.** Test games are untouched until a player passes
everything below.

## Data

**League training catches:** the 414 training games, 16–30 ft, shot clock
recorded, motion features present, action shoot-now or continue.

- Selection s = shoot-now.
- Outcome y = made, observed only for shoot-now catches with a located,
  linked make/miss. Shoot-now catches without that are dropped and counted.

## Model

| | Equation | Covariates |
|---|---|---|
| **Selection** | s* = Zγ + u | Z = X + **excluded variables:** best teammate openness (capped at 20), score margin (clipped ±20), catch-source dummies (offensive rebound, inbound, other; pass is the reference) |
| **Outcome** | y* = Xβ + e | X = 1, distance/10 and its square, zone dummies (above the break, corner), openness at catch (capped 15), counterfactual release openness open_cf (capped 15), shot clock, **motion state:** closing_pre and closing_post (clipped ±15), catcher speed (clipped at 25), set, defenders within 6 ft (capped at 3), pass flight time (clipped at 3) and distance (clipped at 60) |

- Errors (u, e) are standard bivariate normal with correlation **ρ**,
  parameterized as ρ = tanh(α).
- **Note:** flight time and distance are 0 for catches that aren't passes,
  so they carry a little of the catch-source information into the outcome
  equation. Stated, not changed.

**Log-likelihood:**

- s = 0: ln Φ(−Zγ)
- s = 1, y = 1: ln Φ₂(Zγ, Xβ; ρ)
- s = 1, y = 0: ln Φ₂(Zγ, −Xβ; −ρ)

Φ₂ is computed by 20-node Gauss–Legendre integration of the bivariate
density in ρ. Covariates are standardized (the intercept is not).

**Fitting:** L-BFGS-B, starting from the two separate probits and ρ = 0.

**Uncertainty:** BHHH (outer product of per-observation scores, by central
differences). The 95% interval for ρ is Wald on α, transformed back.

## Quantities

- **Counterfactual make rate for unshot catches** = the mean over s = 0
  catches of P(y = 1 | x, s = 0) = Φ₂(Xβ, −Zγ; −ρ) / Φ(−Zγ).
- **Naive counterpart** = the mean of Φ(Xβ_naive) over the same catches,
  with β_naive from a probit on the shoot-now catches alone.

## Step 1: exclusion strength (threshold set here, before measuring)

- **Measurement:** on league training catches, a probit of s on Z (full)
  against s on X (restricted).
  - **Statistic:** LR = 2(ℓ_full − ℓ_restricted), with df = 5.
  - **Partial pseudo-R²** = 1 − ℓ_full / ℓ_restricted.
- **Threshold:** **LR / df ≥ 10**, the likelihood-ratio analogue of the
  first-stage F ≥ 10 rule. Partial pseudo-R² is reported alongside.
- **Below the threshold:** stop and report.
- With about 100,000 catches, LR will easily clear this. The **practical**
  test of whether ρ is identified is step 2, run at the real strength.

## Step 2: synthetic validation, at the real exclusion strength

- **Covariates:** the real league training catches (all rows, same size).
- **True γ:** the real selection probit coefficients (from step 1), so the
  excluded variables carry **exactly the real strength**.
- **True β:** the real naive outcome probit coefficients.
- **Data:** (u, e) bivariate normal with ρ ∈ {0, 0.3, 0.6}. Then s =
  1[Zγ + u > 0], and y = 1[Xβ + e > 0], observed only if s = 1.
- **Seeds:** 20 per setting (500–519, 600–619, 700–719).
- **Each run, reported:**
  - ρ̂ with its 95% interval, and whether it covers the truth;
  - the estimated and the true counterfactual make rate for unshot catches,
    and the absolute error;
  - the naive estimate's error.
- **Pass, in every setting:** the interval covers the true ρ in **≥ 18 of
  20** seeds, **and** the counterfactual error is ≤ 0.03 in **≥ 18 of 20**.
- **Fail:** stop.

## Step 3: power on ρ

- **Expected SE of ρ** at the real size = the mean BHHH SE across the
  ρ = 0 synthetic runs. The minimum detectable |ρ| is 2.8 × SE.
- **Registered:** the correction is used only if the **real ρ's 95%
  interval excludes 0**. Otherwise the naive make model stands, and 5b ends
  with that finding.

## Step 4: real fit and validation (once)

- **Fit** on league training catches. If one fit takes more than 30 minutes,
  a 50% subsample at seed 4242 is used instead, and stated.
- **Validation once,** on league **validation-game** catches (same unit):
  mean per-catch log-likelihood of the bivariate probit against the two
  separate probits (ρ = 0), with the difference and a game-bootstrap 95%
  interval (1,000 resamples, seed 0).
- **Reported:**
  - ρ̂ [95% CI];
  - by open_cf bin (0–2, 2–4, 4–6, 6–8, 8+ ft), for unshot catches, the
    corrected conditional make probability, the corrected marginal Φ(Xβ),
    and the naive Φ(Xβ_naive);
  - the **corrected value gap** by open_cf bin: corrected V_shoot
    (marginal make probability × points + g(zone)) minus naive V_continue.

## Step 5: the player sequence

A player continues only if **both** hold:

- ρ is resolved;
- his corrected value gap passes the old **check 1** (22–30 ft OLS slope on
  open_cf > 0, bootstrap 95% CI excluding 0). For the check, V_shoot is the
  league-corrected marginal value with no player offset (zone constants
  don't change a within-band openness slope).

**If so, the registered sequence:**

1. power (pilot T, MDE ≤ 0.15);
2. synthetic recovery;
3. the real fit of c, scored once on test games;
4. the sensitivities.

**Otherwise stop there.**

## Reporting

- **One interim message** with the exclusion strength and the synthetic
  results, before the real fit. Then continue.
- **Final:** everything in plain terms, including **one paragraph on what
  the result depends on** (the normality of the errors, and the exclusion
  restrictions).
