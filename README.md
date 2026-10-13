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
