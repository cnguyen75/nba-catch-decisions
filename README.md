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
