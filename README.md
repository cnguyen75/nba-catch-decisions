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
