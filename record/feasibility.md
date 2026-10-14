# NBA catch decisions: the complete record (2026-10-13)

**Question.** When Stephen Curry, LeBron James and James Harden catch the ball
at 16–30 ft, do they shoot when the points say to?

**Answer.** It could not be answered with a choice model, and the record
below shows why at every step.

**What was established.**

- The decision to shoot tracks openness strongly: a clear, positive effect
  for all three players.
- It does not track the rest of the measured value of shooting (distance,
  zone, clock) detectably.
- So the exchange rate between openness and points cannot be pinned down.
- **Stage 4** priced openness in shot-clock seconds instead. By the points, a
  foot of space at the catch is worth about −0.003. Players act as if it were
  worth about +0.01 toward shooting (league 0.014, Curry 0.008, LeBron 0.009;
  Harden not resolved). And they shoot far less than a points-maximiser would,
  at every stage of the clock.

*results.json key for the project status: `project_status`.*

**Repo:** `~/Documents/nba-catch-decisions`, local only. Every
rule was registered before it ran. The test games were never used.

## The sequence (chronological; every section is kept in full below: the Final round and Stages 4–12 oldest first, then the site paragraphs, then Stage 3b-prep back to the first pass newest first)

| Stage | What was asked | Outcome |
|---|---|---|
| **Feasibility pass** (5 games) | Is there pre-decision variation at the catch? | Gate FAIL on criterion 2 (inconclusive: Curry +9.7 pp, CI −9 to +29). Join 97.7%; shots located 86%. |
| **Second pass** (10 Curry games, fixed catch rule) | Same gate, 22–30 ft | Label "no variation" (rim band, n = 14). Criterion 2 passed strongly: 3% to 44% shoot-now from tight to open. |
| **Decision** | Proceed? | Proceed, post hoc. Criterion 1 judged mis-specified for the rim. |
| **Stage 2** (detector D1–D3, 116 games) | Can catches be detected reliably? | Held-out eye check **57/60, PASS.** Full set built. |
| **Stage 3a** | Detectors, values, power | R3 close-range fix rejected (18/30). Drive/pass 53/60 FAIL, so binary. ECE 0.03 limit shown to be below the noise floor (gate error one). **STOPPED: V_shoot ECE 0.0545 FAIL; power and synthetic not run.** |
| **Stage 3a, decisions** | V_shoot fix, one scale, drive/pass retest | V_shoot fix PASS (powered rule). Drive/pass retest 51/60 FAIL. Scope rule ≤ 30 ft. **No player proceeded:** openness looked flat. |
| **Correction (Colin)** | Was "openness is flat" real? | **No, an artefact.** Openness at catch on taken shots. By release openness, threes go 29% to 43% (Colin's table; all league threes 28% to 41% in the 3b-prep reproduction). |
| **Stage 3b-prep** (621 games) | Make model on release openness | Powered ECE **FAIL** (0.0163 vs 0.0159). Replacement criteria (post hoc): bins **FAIL by 0.00002**. That bins limit (about 1.3 SE) repeated the old project's v3b error (gate error two). |
| **Calibration attempt 2** (60 fresh games, openness spline) | Fit for purpose? | **PASS** (level 0.0095, gradient 0.007, all bins). |
| **Sequence on ≤ 30 ft** | Selection, value gap, power | No selection detected (7a). Dubin–McFadden not shown to work (7c). Curry fails the value-gap check. Harden's pilot T diverges: **rim catches had been valued with a jump-shot model.** |
| **Final round** (16–30 ft) | Same checks, plus the descriptive result | **No gated player proceeds** (Curry check 1; Harden pilot T diverges). Descriptive result below. |
| **Stage 4** (openness priced in clock seconds; new question) | Do players trade openness against shot clock the way the points do? | **No, the signs are opposite.** Measured: a foot of openness at the catch is worth −0.003 pts and a second of clock −0.002 pts toward shooting (+1.6 s per ft). Behaviour: −7.1 s per ft (league). Implied openness value 0.014 pts/ft (league), Curry 0.008, LeBron 0.009; Harden not individually resolved. Skinner: under-shooting at every clock state. |
| **Stage 5a** (motion features) | Do closing speed and set/moving improve the make model? Do they change the behavioural slopes? | Make model: **no improvement** (log loss −0.00014 [−0.0009, +0.0006]). League exchange rate stable at ~7 s/ft. Curry's openness slope falls 0.34 → 0.25 (part of 'openness' was motion). |
| **Stage 5c** (exchange-rate map) | How do players price a foot of space in shot-clock seconds? | 98 of 219 players resolved. Median 5.1 s/ft (IQR 4.0–6.1). Curry 3.9 (24th percentile), LeBron 4.6 (42nd), Harden unresolved. League: trailing by 5+ gives 8.1 vs 6.7 within 5; loose-ball and steal catches 2.7 vs passes 7.8. |
| **Stage 5b** (latent shot quality: bivariate probit with selection) | Can unobserved shot quality be separated from the choice? | Exclusions pass the threshold (LR 130, 26/df) but are practically weak (partial pseudo-R² 0.002). Synthetic at real strength: ρ covered 20/19/20, but the passed-up make rate is recovered within 0.03 in only **10, 4, 7 of 20**. **FAIL; stopped, no real fit.** |
| **Stage 5b, strategy 2** (shot clock 5–24 s as the exclusion) | Does the strongest lever identify hidden shot quality? | Falsification **passes** (clock effect on makes +0.001/s [−0.0001, +0.002]). Exclusion strength 4.6× higher (partial pseudo-R² 0.0091 vs 0.0020). Synthetic: ρ covered 18–20/20, but the passed-up make rate within 0.03 in only **2, 10, 8 of 20**. **FAIL; 5b closed, no real fit.** |
| **Stage 6** (clock + rhythm; richer state) | Third and last instrument set; what moves the decision and the make? | Falsification valid for clock (+0.001/s), recent makes (−0.005/make) and the first-shot flag (−0.003). **Hot hand negative:** −1.9 points after a make. Absolute openness beats relative on held-out games. Joint strength did not rise (pseudo-R² 0.0088). Synthetic: within 0.03 in **6, 1, 8 of 20**. **5b closed for good.** Threes 8.8 s/ft vs mid-range 5.3. |
| **Review** (2026-10-13) | Independent audit of code, gates, identification | Code supports the numbers (the review's own finding). Gate errors 3–5 found (attempt-2 level and gradient at 1.2–1.5 SE; 5b 0.03 limit unreachable). 5c median biased low by the resolved filter; pooled league 7 s/ft. Site paragraph corrected (three sentences, plus "players" → "league players"). **Gate errors in all: five** (one: 3a ECE limit; two: 3b-prep bins limit; three and four: attempt-2 level and gradient; five: 5b recovery). |
| **Stage 7** (clock-added shots; new question) | Are the shots the clock makes players take any worse? | Shoot rate 13% → 25% from 12–20 s to 4–8 s (marginal share 0.50). Added shots' quality gap Δ = **−1.4 points** [−6.0, +3.4]: **unresolved at this sample size** (registered bound −5; the power check predicted it). Rushed shots under 4 s: −6.0 points [−8.7, −3.1]. |
| **Stage 8** (exchange-rate map, partial pooling) | What is the league exchange rate when every player gets an estimate? | All 219 eligible players shrunk toward the league. **Median 7.8 s/ft** (6.9 without the 61 clock-indeterminate players, 28%); league μ 8.1; IQR 6.1–11.8. Curry 5.1 [3.2, 13.3], 11th percentile; LeBron 6.1 [3.5, 17.0], 26th; Harden indeterminate. 5c's filtered 5.1 reproduced (5.08). Site sentence unchanged (within 1 s/ft of 7). |
| **Stage 9** (does the pass find the most open teammate?) | Where does the ball go when a player passes? | Over 133,882 passes, the receiver is the most open of the four teammates **31%** of the time (25% would be random); the ball gives up 4.2 ft of space on average for 3.4 ft of basket proximity. The open corner man is found only 15%. **LeBron 37% (+6.2 [+1.9, +10.4] vs league, above the registered MDE 5.5)**, Harden 42%, Curry 24%. |
| **Stage 10** (release timing against the closeout; descriptive) | Do shooters trade set-up time against the closing defender? | Median catch-to-release falls from 1.08 s to a **0.92 s floor** as closing speed rises (slope −0.011 s per ft/s [−0.011, −0.010]); release brought forward **0.13 s** [0.12, 0.14] at a top-quartile closeout, preserving about **1.5 ft** of space (units corrected; see the Stage 10 section). Rush penalty flat above 0.7 s (0.7–0.9 s vs 0.9–1.1 s: −1.1 points [−2.6, +0.5]). Waiting 0.1 s at a fast closeout loses 2.0 points vs gains 0.5 [−0.2, +1.3]: **gain − loss −1.4 [−2.2, −0.7]; the floor is mechanics, not a trade-off.** Curry and Thompson release at 0.80 s; LeBron and Harden too thin. |
| **Stage 11** (Stage 9 with shooters-only candidates; descriptive) | Does the pass find the most open *shooter* within 30 ft? | 6,720 passes excluded (< 2 candidates); 127,162 left. League **28.0%** [27.6, 28.3] against a 33.0% chance baseline; gives up 3.2 ft of space for 1.6 ft of proximity. Open corner shooter found **14%**. **LeBron 37.5% (+9.6 [+5.7, +13.3] vs league, above the MDE 5.8)**, Harden 41.2%, Curry 25.2%. These numbers replace Stage 9's for the page. **Like-for-like (post hoc, after correction):** when the receiver is a candidate, the league finds the most open one 34.8% [34.4, 35.2] against 31.1% chance; LeBron 50.5%, Harden 53.9%, Curry 35.0%. |
| **Stage 12** (exchange rate by situation, partial pooling; descriptive) | Does the situation move the exchange rate once every player is shrunk within the cut? | Behind by 5+ **8.8** s/ft, within 5 7.8, ahead by 5+ **6.6**: behind − ahead **+2.1 [+1.2, +3.1]**. Q4 vs Q1–3 +0.1 [−1.2, +0.6] and home vs away +0.2 [−0.4, +0.7]: no difference. Loose-ball/steal catches too thin to pool (no player has 150). Curry's low rate is from away games (3.8) and leading (3.9). |

## Final round

*results.json key: `final_round`*

**Scope fix, recorded.** Rim catches had been valued with a make model
trained on jump shots. A rim catch usually ends in a layup or dunk, which
goes in far more often. So V_shoot at the rim was understated, the value gap
there was negative while players shot 18–33% of those catches, and the
choice-model slope was pulled negative. The unit is now 16–30 ft, the
jump-shot model's valid range.

**Gated checks:**

| | Curry | Harden | LeBron (reported, not gated) |
|---|---|---|---|
| Train catches, 16–30 ft (shoot now) | 432 (103) | 450 (59) | 429 (24) |
| Value-gap slope, 22–30 ft (pts/ft) | 0.0050 [−0.0059, 0.0183] **fail** | 0.0187 [0.0097, 0.0293] pass | 0.0162 [0.0109, 0.0216] pass |
| Pilot T | — | **510, diverged** | 0.73 |
| MDE at c = 0 (bar 0.15) | — | 163, **underpowered** | 0.246 (would be underpowered) |
| Outcome | stops | stops | — |

**No gated player proceeds.** There was no synthetic recovery, no real fit
of c, and the test games were never touched. The registered gradient-scale
and Dubin–McFadden sensitivities therefore have nothing to apply to.

**Descriptive: revealed against measured value of openness.** Non-test
catches at 16–30 ft; bootstrap 95% intervals.

| | Curry | Harden | LeBron |
|---|---|---|---|
| Catches (shoot now) | 585 (134) | 596 (72) | 610 (38) |
| (a) **measured:** change in value gap per ft of openness (pts) | **0.019** [0.015, 0.024] | **0.029** [0.024, 0.034] | **0.021** [0.017, 0.024] |
| (b) change in log-odds of shooting per ft of openness | **0.18** [0.10, 0.29] | **0.14** [0.03, 0.26] | **0.27** [0.19, 0.38] |
| (c) change in log-odds per point of value gap from everything except openness | −0.02 [−0.81, 0.85] | 0.90 [−1.27, 2.97] | −0.46 [−3.24, 2.23] |
| (d) = (b)/(c): **revealed** pts per ft | unstable | 0.15 [−1.24, 1.30] | unstable |

**Plain-language reading.**

- **All three shoot markedly more when they're more open.** Each extra foot
  raises the odds of an immediate shot by about 15–30%.
- **The measured value of that foot is small:** about 0.02–0.03 points of
  value gap.
- **Their choices don't move detectably with the other parts of the value
  gap** (distance, zone, clock), so the exchange rate between openness and
  points is not identified:
  - **Harden:** he behaves as if an extra foot of openness were worth about
    0.15 points, against a measured 0.03. That is five times as much, but
    the interval (−1.2 to 1.3) includes both the measured value and zero.
  - **Curry and LeBron:** no stable "as if" figure exists. The denominator is
    indistinguishable from zero.

## Stage 4: openness priced in shot-clock seconds (registered `ea99d0c`; no earlier gate reopened)

*results.json key: `stage4_openness_in_clock_seconds`*

**Setup.**

- **Unit:** catches at 16–30 ft with the shot clock recorded.
- **Covariates, the same in every model:** shot clock, openness at catch,
  distance, zone, best teammate openness.
- **Measured gradients:** OLS of the value gap (V_shoot − V_continue,
  possession scale) on league train catches.
- **Behavioural gradients:** a logistic model of shoot-now.
- **Intervals:** bootstrap over games.

**Power first:**

| | SE of clock slope (log-odds/s) | Smallest detectable difference in the openness/clock trade (s/ft) |
|---|---|---|
| League | 0.002 | 0.8 |
| Curry | 0.029 | 3.5 |
| LeBron | 0.040 | 5.2 |
| Harden | 0.030 | very large; his clock slope is about 0 |

**Results:**

| | League | Curry | LeBron | Harden |
|---|---|---|---|---|
| Clock slope (log-odds per s) | −0.055 [−0.061, −0.050] | −0.088 [−0.151, −0.035] | −0.100 [−0.191, −0.046] | −0.004 [−0.059, 0.062], **not individually resolved** |
| Openness slope (log-odds per ft) | 0.39 | 0.35 | 0.46 | 0.46 |
| Behavioural trade (s of clock per ft) | −7.1 [−7.8, −6.5] | −3.9 [−10.1, −2.3] | −4.6 [−10.0, −2.5] | (use league) |
| **Implied value of a foot of openness** (pts) | **0.014** [0.013, 0.016] | **0.008** [0.005, 0.020] | **0.009** [0.005, 0.020] | (use league: 0.014) |
| **Measured value** of a foot of openness at the catch (pts) | **−0.003** [−0.0033, −0.0029] | same (league) | same | same |

The measured value of a second of clock is −0.002 pts (toward shooting as it
runs down). The measured trade is +1.6 s per ft.

**Plain reading.**

- **By the points, a foot of space at the catch is worth almost nothing.** It
  even tilts slightly toward continuing, because an open catch also makes
  passing and driving better.
- **Players behave the other way.** Priced through how strongly they react to
  the shot clock, they act as if an open foot were worth about **0.01 points
  toward shooting**: 0.014 for the league, 0.008 for Curry, 0.009 for LeBron.
- **Harden's own clock response is too flat** to price anything, so the
  league figure stands in for him.

**Skinner's test.** A value-maximiser using the measured values would shoot
42–84% of these catches at every clock state. Players shoot 2–40%, and every
interval excludes "no difference".

| Shot clock | League observed | League maximiser |
|---|---|---|
| 0–4 s | 40% | 61% |
| 4–8 s | 25% | 70% |
| 8–12 s | 18% | 72% |
| 12–16 s | 13% | 69% |
| 16–20 s | 12% | 64% |
| 20–24 s | 19% | 42% |

- The shortfall is **largest mid-clock and smallest at both ends.** That is
  under-shooting everywhere, not a specific "waits too long" pattern.
- Curry with under 4 s left (5 of 6 shot) is the one bin above the
  maximiser, but n = 6.
- **Caveat:** V_continue is what actually followed continuing, not optimal
  play. And V_shoot for passed-up catches rests on the counterfactual
  release openness.

## Stage 5a: motion features (registered `0437efd`)

*results.json key: `stage5a_motion`*

**Coverage:** motion features for 239,824 catches and 80,220 shots
(non-test games).

- **Closing speed:** the nearest defender's velocity toward the catcher,
  0.5 s before and after the catch.
- **Catcher speed** and set (< 3 ft/s).
- **Defenders within 6 ft.**
- **Pass flight** time and distance.
- **Catch source** (at 16–30 ft: pass 96%, other 3%, offensive rebound 1%, inbound 0.2%).

**Make model** (414 training games; scored on the 60 fresh calibration games,
5,512 jump shots):

| | Current | With motion |
|---|---|---|
| Level / gradient / worst bin | 0.0094 / 0.0072 / 0.026, all pass | 0.0097 / 0.0062 / 0.026, all pass |
| ECE | 0.013 | 0.015 |
| Log loss | 0.65394 | 0.65380 |
| Change (motion − current) [95% CI] | | −0.00014 [−0.00092, +0.00061]: **no improvement** |

Once release openness is in the model, how fast the defender closed and
whether the shooter was set add nothing measurable to make probability.

**Behavioural slopes (16–30 ft, shot clock recorded):**

| | Openness slope, Stage 4 → with motion | Clock slope | Exchange rate (s/ft) |
|---|---|---|---|
| League | 0.396 → 0.421 | −0.055 → −0.060 | 7.18 → 7.00 [6.44, 7.63] |
| Curry | 0.344 → **0.247** | −0.089 → −0.097 | 3.86 → 2.54 [1.29, 5.78] |
| LeBron | 0.465 → 0.393 | −0.100 → −0.130 | 4.63 → 3.02 [1.17, 6.45] |
| Harden | 0.465 → 0.494 | ≈ 0, unresolved | unresolved |

Dropping the post-catch window barely changes anything. **For Curry and
LeBron, part of what looked like "openness" was motion**, such as being set
or catching on the move. For the league the exchange rate is stable at about
7 s/ft.

## Stage 5c: the exchange-rate map (registered `f391697`; descriptive)

*results.json key: `stage5c_map`*

**Exchange rate** = how many seconds of shot clock one foot of space at the
catch is "worth" in players' shooting decisions. It is the ratio of the
openness and clock slopes. Catches at 16–30 ft, non-test games; intervals by
bootstrap over games.

**The league:**

- **219 players** have ≥ 300 catches. **98 are resolved**, meaning their
  clock response is distinguishable from zero.
- Among resolved players: **median 5.1 s/ft, IQR 4.0–6.1.** The counts are
  1 below 0, 3 at 0–2, 21 at 2–4, 46 at 4–6, 19 at 6–8, 7 at 8–10, and 1 at
  10–15 s/ft.
- **Highest:** Luol Deng 10.1, Klay Thompson 9.3, Avery Bradley 9.1, Omri
  Casspi 8.7, Eric Gordon 8.3, José Calderón 8.3, Evan Fournier 8.3,
  Carmelo Anthony 8.2, Anthony Tolliver 7.8, Paul Millsap 7.6. Their upper
  intervals are very wide (20–70), so they are not individually precise.
- **Lowest:** Serge Ibaka −8.5 (he shoots more when *more* clock remains),
  Trevor Booker 1.8, Jarrett Jack 2.0, Dwyane Wade 2.0, Monta Ellis 2.1,
  Draymond Green 2.4, DeMar DeRozan 2.8, Blake Griffin 2.9, Maurice Harkless
  3.0, Evan Turner 3.0.
- **The three:**
  - **Curry 3.9** [2.3, 10.1], 24th percentile among resolved players: space
    matters less to him, relative to the clock, than to most players.
  - **LeBron 4.6** [2.6, 10.1], 42nd percentile.
  - **Harden unresolved.** His shooting doesn't respond to the clock.

**Within-player variation, league:**

| Cut | Exchange rate [95% CI] |
|---|---|
| Behind by 5+ | **8.1** [7.1, 9.5] |
| Within 5 | 6.7 [6.1, 7.4] |
| Ahead by 5+ | 7.0 [6.3, 7.9] |
| Quarters 1–3 | 7.4 [6.9, 8.1] |
| 4th quarter + OT | 6.6 [5.9, 7.6] |
| Home | 7.2 [6.6, 8.0] |
| Away | 7.2 [6.6, 7.9] |
| Pass | 7.8 [7.2, 8.4] |
| **Loose ball / steal** | **2.7** [2.1, 3.5] |
| Offensive rebound, inbound | thin (wide intervals) |

**For the three players,** most cells are too thin (flagged). The resolved
ones:

- **Curry:** ahead by 5+ 3.1 [1.6, 9.3]; quarters 1–3 5.3 [2.8, 17.4]; away
  2.1 [1.2, 5.5]; pass 3.9 [2.3, 11.4].
- **LeBron:** quarters 1–3 4.2 [1.8, 11.0]; away 4.8 [2.2, 12.0]; pass 4.8
  [2.4, 11.1].
- **Harden:** no resolved cell.

**Plain reading.**

- **The typical player treats a foot of space like about five seconds of
  shot clock.** A wide-open catch is a strong reason to shoot now, about as
  strong as the clock running down by several seconds.
- **Teams that are behind weight space a little more.**
- **Scrambly catches** (loose balls, steals) weight it far less.
- **Curry weights space less than most:** he'll shoot with less of it.

**Recorded after review: pooled against filtered exchange rate.**

- **The "median 5.1 s/ft" is filtered.** It is the median over the 98
  players whose clock slope is significantly non-zero. Requiring a
  large-enough denominator biases the ratio low.
- **The pooled league estimate is 7.1 s/ft** (Stage 4) and **7.0** (5a).
- Both stay reported. **The pooled figure is the one for the league
  sentence.**

## Stage 5b: latent shot quality (registered `40ba56a`): stopped at synthetic validation

*results.json key: `stage5b`*

**Model.** A bivariate probit with sample selection.

- **Selection:** shoot-now on the full catch state, including the 5a motion
  features.
- **Outcome:** made, on the same state minus the excluded variables.
- **Excluded variables:** best teammate openness, score margin, catch
  source.
- **ρ:** the correlation of the two errors. It measures unobserved shot
  quality, meaning whether players shoot more often when their shot is
  better in ways the tracking can't see.

**Step 1, exclusion strength** (threshold set before measuring: LR per df
≥ 10). League training catches: 101,532, with 16,018 shots.

- **LR = 130 on 5 df (26 per df): passes.**
- **Partial pseudo-R² = 0.002:** the excluded variables explain almost none
  of the decision.

**Step 2, synthetic validation, built at exactly that real strength:**

| True ρ | 95% interval covers ρ (need ≥ 18/20) | Passed-up make rate within 0.03 (need ≥ 18/20) | Median error, corrected / naive |
|---|---|---|---|
| 0 | 20 | **10** | 0.034 / 0.005 |
| 0.3 | 19 | **4** | 0.088 / 0.243 |
| 0.6 | 20 | **7** | 0.056 / 0.491 |

**FAIL; stopped as registered.** There was no real fit, no power step and no
player sequence.

**In plain terms.**

- **The estimator is honest but imprecise at this strength.** Its intervals
  for ρ cover the truth, but they are wide: about ±0.3 at ρ = 0, so the
  smallest detectable ρ is about 0.45.
- **So it can't pin the make rate of the shots players passed up** to within
  3 points.
- **The stakes are large if selection exists.** At ρ = 0.3, the naive model
  overstates the make rate of passed-up shots by 24 points on average. The
  correction cuts that to about 9, but not to 3.
- **So the data can't tell us whether passed-up shots were worse than they
  look.** If they were, the "players under-shoot" finding from Stage 4 would
  shrink. If not, it stands.

**What the result depends on** (for the page).

> The attempt to measure hidden shot quality rests on two assumptions. The
> first is that the unobserved parts of "do I shoot?" and "will it go in?"
> follow a joint normal distribution. The second is that a few things affect
> whether a player shoots but not whether the shot goes in: how open his best
> teammate is, the score margin, and how he got the ball. With 100,000 catches
> those variables are detectably related to shooting, but they explain only
> 0.2% of it. Simulations built at that real strength showed the method can't
> recover how good the passed-up shots were to within 3 percentage points. So
> I didn't run it on the real data, and the question of whether players pass
> up shots because they can see something the tracking can't stays open.


### Strategy 2 (registered `0dcd379`): the shot clock as the exclusion. 5b closed.

**The idea.** Between 5 and 24 seconds left, the shot clock changes *whether*
a player shoots but should not change *whether a given shot goes in*. A
late-clock indicator (≤ 4 s) stays in both equations, because rushed shots
are worse.

**Falsification test: PASS.** On 37,122 taken league jump shots, with release
openness, distance, zone, shot type, motion and the late-clock flag
controlled, each extra second of clock moves make probability by **+0.001**
[−0.0001, +0.002]. That is indistinguishable from zero and far inside the
±0.01 bound. The 16–30 ft subset agrees.

**Exclusion strength: much stronger.** LR = 603 on 6 df (101 per df).
Partial pseudo-R² = **0.009**, against 0.002 before. The clock is by far the
strongest excluded variable.

**Synthetic recovery at that strength: FAIL.**

| True ρ | ρ covered (need ≥ 18/20) | Passed-up make rate within 0.03 (need ≥ 18/20) | Within 0.05 (information) | Median error, corrected / naive |
|---|---|---|---|---|
| 0 | 18 | **2** | 8 | 0.064 / 0.003 |
| 0.3 | 20 | **10** | 15 | 0.031 / 0.243 |
| 0.6 | 20 | **8** | 12 | 0.035 / 0.488 |

**Plain reading.**

- **The clock made the estimate sharper.** SE(ρ) fell from 0.16 to 0.10,
  and where selection exists the error on passed-up shots was halved.
- **It still can't pin their make rate to within 3 points.**
- **Where there is no selection, the correction does worse than the naive
  model** (6 points off, against 0.3).

**As registered, this closes 5b.** The strongest available lever could not
resolve the selection, so there was no real fit.

**What the result depends on** (updated paragraph for the page).

> To ask whether players pass up shots because they see something the
> tracking can't, I fitted a selection model on simulated data built to match
> the real thing. It assumes the hidden parts of "do I shoot?" and "will it go
> in?" are jointly normal. It also needs something that changes whether a
> player shoots but not whether the shot goes in. The best candidate was the
> shot clock between 5 and 24 seconds left. I checked that it doesn't predict
> makes once openness and the rest are accounted for (+0.1 percentage points
> per second, indistinguishable from zero). Even with it, the method couldn't
> recover how good the passed-up shots were to within 3 percentage points in
> simulations built at the real data's strength. So I didn't apply it to the
> real data. Whether the "players under-shoot" finding partly reflects shots
> they could tell were bad stays open.

### Recorded after review: the 5b recovery gate could not be passed (gate error five)

**The criterion was unreachable by construction:** "passed-up make rate
within 0.03 in ≥ 18 of 20".

- **The counterfactual error just tracks the ρ̂ error.** Across all nine
  synthetic settings (three strategies × three values of ρ), the
  counterfactual make-rate error is a near-deterministic function of the
  error in ρ̂:
  - slope −0.71 to −1.02 per unit of ρ;
  - correlation −0.986 to −0.997;
  - residual SD 0.007–0.011.
  - (The review quoted −0.75 to −1.0, −0.99 and 0.007; these are my
    re-computed figures from the stored runs.)
- **So the gate needed SE(ρ) of about 0.02.** Meeting 0.03 in 90% of seeds
  requires 1.645 × 0.8 × SE(ρ) ≤ 0.03.
- **Achieved SE(ρ):** 0.06–0.10 with the clock instruments, and 0.09–0.16
  with the first set.
- **The conclusion stands.** The selection could not be resolved at the
  data's strength. But **the gate was not a test of the method**: no
  estimator with that SE(ρ) could pass it.

## Stage 6: the last identification attempt (registered `811c61b`)

*results.json key: `stage6`*

**Three instrument sets were tried in order, each chosen before its run:**

1. **Exclusions** (best teammate openness, score margin, catch source):
   plausible decision shifters. Too weak.
2. **Plus the shot clock over 5–24 s.** Stage 4 showed the clock drives the
   decision. It passed falsification, but synthetic recovery failed.
3. **Plus rhythm (recent makes) and the first-shot flag.**
   - Players who have hit recent shots take harder ones (Bocskocsky,
     Ezekowitz & Stein, Sloan 2014), so rhythm should move the decision.
   - Defender height follows Chang et al. (Sloan 2014), and the clutch flag
     follows Goldman & Rao (Sloan 2012).
   - The 2015 course project used a running in-game field-goal percentage
     for the same reason. The 2026 audit found it was computed across games.

**What moves the decision** (league; 16–30 ft catches; held-out = validation
games):

- **Absolute openness predicts better than relative** (held-out log loss
  0.3294 against 0.3326). Adding relative on top barely helps.
- **Last attempt made:** +0.14 log-odds of shooting now [0.09, 0.20].
  Recent-make counts add nothing beyond it.
- **Taller nearest defender:** −0.13 per 10 cm. **Defender closing fast:**
  −0.05 per ft/s.
- **No effect:** back-to-back games, clutch time.
- **Defender and rim-protector identity:** no held-out gain (+0.00001).

**What moves the make,** among taken league jump shots, with openness,
distance and motion controlled:

| | Effect on make probability [95% CI] | As an instrument |
|---|---|---|
| Shot clock, 5–24 s (per second) | +0.001 [−0.0001, +0.002] | valid |
| Makes in last 5 (per make) | −0.005 [−0.011, +0.002] | valid |
| First shot of the game made | −0.003 [−0.015, +0.007] | valid |
| **Last attempt made** | **−0.019** [−0.032, −0.007] | (hot-hand size) |

**There is no positive hot hand.** After a make, the next shot is about 2
points less likely to go in. That fits players taking harder shots when they
feel hot.

**Selection model, strategy 3: FAIL; 5b closed for good.**

- With the richer state in both equations, the joint strength of all valid
  instruments did not rise: partial pseudo-R² 0.0088, against 0.0091 for the
  clock alone. Rhythm and the first shot barely move the decision once the
  last-shot result is in the state.
- **Synthetic:** the passed-up make rate is recovered within 0.03 in only
  **6, 1 and 8 of 20** seeds (within 0.05: 8, 8, 11), with ρ covered 18–20
  of 20.
- **As registered, 5b is closed for good.** With the strongest levers the
  data offers, the selection on unobserved shot quality cannot be resolved.

**Descriptive:**

- **Exchange rate by zone (league):** a foot of space is worth **8.8 s of
  shot clock on threes**, against **5.3 s from mid-range**.
- **Curry:** mid-range 3.1 s/ft. His threes, and Harden in both zones, are
  unresolved.
- **Rhythm response:**
  - Curry shoots slightly more off the catch after 2–3 recent makes (+5
    points, interval includes 0).
  - **In games where Curry's first shot went in, he shoots off the catch 9
    points less often** (17.6% against 26.7%; [−15, −3]).
  - LeBron and Harden show no clear response.
- **Best jump-shot contesters** (≥ 100 contests): Anthony Davis,
  LaMarcus Aldridge, Dwight Howard, Marco Belinelli, Stephen Curry, Andre
  Roberson, Emmanuel Mudiay, JJ Redick, Enes Kanter, Goran Dragić.
- **Best rim protectors** (≥ 50): Rudy Gobert, DeAndre Jordan, Robin Lopez,
  Kristaps Porziņģis, Spencer Hawes, Andrew Bogut, Serge Ibaka, Marcin
  Gortat, Paul Millsap, Jeff Withey.
- **Caveat:** shots over the best defenders are the ones players chose to
  take, so these rankings carry selection.

**Corrected after review.**

- **The hot-hand reading above is withdrawn.** The −1.9-point effect of a
  made last attempt is estimated with all of these controlled:
  - release openness, distance and zone;
  - shot type and shot clock (late flag and 5–24 s);
  - closing speed and the other motion features;
  - defender height and defender identity.

  So "players take harder shots when they feel hot" cannot explain it, at
  least not through anything measured. **The mechanism is an open
  question.**
- **The Curry first-shot result** (shoot-now rate 9 points lower in games
  where his first shot went in) is **1 of 12 descriptive contrasts**
  (3 players × 2 contrasts × 2 outcomes), with **no multiplicity control**.
  It should not be read as a finding on its own.

## Stage 7: clock-added shots (registered `e5933e9`; power `0dcd95f`; result `6aa2859`)

*results.json key: `stage7_clock_added_shots`*

**Question.** As the shot clock runs from 24 down to 5 seconds, players
shoot off the catch about twice as often. Are the shots the clock adds any
worse than the ones taken with more time, at equal openness, distance,
type and motion?

**Why this sidesteps 5b.** If players shoot whenever hidden shot quality
clears a threshold that falls as the clock runs down, the catches added late
are the marginal ones. Comparing taken shots with taken shots then measures
how good those marginal passed-up shots are. It never has to separate ρ
from the make model.

**Design** (league jump shots and catches, 16–30 ft, shot clock recorded):

- **Confirmatory sample:** the 183 validation and calibration games, scored
  once.
- **Training games:** spent by the review's pilot, so they were used only
  for the make model's nuisance terms and for power.

**Power, recorded before the run.**

- Expected SE(Δ) ≈ 0.027; smallest detectable Δ at 80% power ≈ **0.076**.
- That is larger than the registered reading bound of 0.05, so
  "unresolved" was the likely outcome, and the record says so in advance.

**Raw table** (confirmatory games):

| Shot clock | Catches | Shoot-now rate | Jump shots | Raw make % | Adjusted make % [95% CI] |
|---|---|---|---|---|---|
| [0,4) rushed | 956 | 40.2% | 1,152 | 30.2 | 32.0 [29.5, 34.6] |
| [4,8) | 4,160 | **25.4%** | 2,077 | 37.2 | 37.4 [35.2, 39.6] |
| [8,12) | 9,928 | 17.9% | 3,040 | 38.0 | 37.6 [35.7, 39.4] |
| [12,16) | 16,028 | 13.0% | 3,141 | 37.9 | 37.5 [36.1, 39.2] |
| [16,20) | 12,166 | 12.1% | 2,076 | 38.3 | 39.1 [37.0, 41.2] |
| [20,24) | 3,059 | 18.7% | 503 | 41.4 | 41.8 [37.5, 45.8] |

"Adjusted" means every shot is set to that bin, with openness, distance,
zone, type and motion held as observed.

**The registered statistics:**

| | Estimate [95% CI] |
|---|---|
| Marginal share m (half of the late shots are "added") | 0.503 [0.468, 0.536] |
| AME, [4,8) against [12,20), make probability | −0.007 [−0.030, +0.017] |
| **Δ, the added shots' quality gap** | **−0.014 [−0.060, +0.034]** |
| Information: [0,4) against [12,20) | −0.060 [−0.087, −0.031] |
| Information: catch-and-shoot only, [4,8) against [12,20) | −0.015 [−0.047, +0.014] |

**Registered reading: "unresolved at this sample size".** The interval's
lower bound (−0.060) is below −0.05, and its upper bound is above it.

**Plain reading.**

- **The added shots go in about as often as the earlier ones,** about 1.4
  points less at equal observables. But the interval runs from 6 points
  worse to 3 points better.
- **So the data can't rule out a 5-point drop.** This is the size that would
  explain away the first tranche of the Stage 4 under-shooting.
- **The data can't confirm one either.** The point estimate is small.
- **Only the rushed last four seconds are clearly worse** (6 points), which
  is why that bin was set aside.

**Caveats.**

1. **The exclusion assumption:** hidden shot quality is independent of the
   shot clock, given the observables. That is the strategy-2 assumption,
   whose falsification test passed. It cannot be tested directly.
2. **Marginal, not inframarginal:** this bounds the catches added as the
   clock runs down, not the catches players pass up even late.
3. **The training pilot was spent** (the review ran it before this
   registration). The point estimate on training (Δ −0.016) agrees with the
   confirmatory one.
4. **214 shots** across all non-test splits lack motion features and are
   dropped. The script's JSON key labelled this "confirmatory"; it is
   corrected in results.json.

**Figure:** `figures/stage7/stage7_clock_added.svg` (and .png). Shot clock on
the x-axis; shoot-now rate and adjusted make rate with intervals; the [0,4)
bin is lighter and labelled "rushed".

## Stage 8: the exchange-rate map with partial pooling (registered `9cca730`; result `94f4d2d`; descriptive)

*results.json key: `stage8_exchange_rate_pooled`*

**Why.** Stage 5c's "median 5.1 s/ft" covered only the 98 players whose clock
slope was individually significant, which biases the ratio low. Here every
player with ≥ 300 catches at 16–30 ft (219 players, including the three) gets
an estimate.

**Method.**

- Each player's Stage 4 slopes (β_clock, β_open) are shrunk toward the
  league by empirical Bayes: a bivariate normal prior, fitted by maximum
  marginal likelihood, treating each player's Fisher covariance as known.
- **Exchange rate (ER)** = −β_open / β_clock, in seconds of shot clock per
  foot of space, from the posterior means. Intervals come from 2,000
  posterior draws.
- A player is **clock-indeterminate** when more than 5% of his draws flip
  the sign of β_clock. He keeps an ER, flagged unresolved.

**The fitted prior:**

- **League mean μ:** β_clock = −0.0559, β_open = 0.453. That gives an ER of
  **8.1 s/ft.**
- **Spread between players (Τ):** SD 0.036 in β_clock and 0.084 in β_open,
  correlation −0.35.

**Results:**

| | Value |
|---|---|
| Eligible players | 219 |
| Clock-indeterminate | **61 (28%)**, above the registered 10%, so the median is reported both ways |
| **Median ER, all players (the league number)** | **7.8 s/ft** |
| Median ER, without the indeterminate | 6.9 s/ft |
| IQR, all players | 6.1–11.8 |
| Histogram (≤ 0 / 0–2 / 2–4 / 4–6 / 6–8 / 8–10 / 10–15 / > 15) | 4 / 0 / 3 / 45 / 66 / 26 / 39 / 36 |
| Sanity check: raw median over 5c's 98 resolved | **5.08** (5c: 5.08), reproduced |

**The three:**

| Player | ER [95%] | Percentile among all 219 | Raw (unshrunk) |
|---|---|---|---|
| Curry | **5.1** [3.2, 13.3] | 11th | 3.9 |
| LeBron | **6.1** [3.5, 17.0] | 26th | 4.6 |
| Harden | indeterminate (12% of draws flip the clock sign) | — | — |

**Information only:**

- **Lowest resolved:** Monta Ellis 3.3, Draymond Green 3.7, Blake Griffin
  3.9, Dwyane Wade 4.1, DeMar DeRozan 4.2, Jarrett Jack 4.3.
- **The extremes on both ends** (Crawford, Crabbe, Collison at the top;
  Ariza, Lowry, Ibaka, Korver at the bottom) are all clock-indeterminate.
  Their ratios are not meaningful.

**Plain reading.**

- **Once every player counts, the typical player treats a foot of space at
  the catch like about eight seconds of shot clock** (seven without the
  players whose clock response can't be pinned down). That is close to the
  pooled league 7. The old 5.1 was the filter talking.
- **Curry and LeBron still sit in the lower part of the distribution.**
  Space matters less to them, relative to the clock, than to most players.
- **Site sentence:** the registered rule changes it only if the median
  differs from 7 by more than 1 s/ft. Neither 7.8 nor 6.9 does, so the
  paragraph is unchanged.

**Implementation notes.**

- 11 players had a constant covariate column (for example, no corner
  catches), which made their Fisher matrix singular. Those columns were
  dropped per player before any result (`s13_pooled_er`, a separate
  commit). β_clock and β_open are unaffected.
- The run printed the spurious macOS NumPy matmul warnings. All outputs were
  checked finite.

**Figure:** `figures/stage8/stage8_er_map.svg` (and .png).

## Stage 9: does the pass find the most open teammate? (registered `4d5a2f8`; result `1334986`; descriptive)

*results.json key: `stage9_pass_to_open_man`*

**What was measured.** Every pass in the non-test games that a teammate
caught within 1.5 s: 133,882 passes, with 177 dropped (receiver not
matched). At the pass frame, I took each of the passer's four teammates'
space (nearest-defender distance), distance to the basket, and position.

**Results** (game-bootstrap 95% intervals):

| Passer | Passes | To the most open teammate | Within 1 ft of the most open | Space given up, mean (median), ft | Receiver closer to the basket by, mean, ft |
|---|---|---|---|---|---|
| League (non-gated) | 132,315 | **31.2% [30.8, 31.6]** | 37.3% [36.9, 37.7] | 4.2 (2.9) | 3.4 |
| Curry | 419 | 24.3% [21.2, 27.6] | 31.0% [28.2, 34.2] | 5.2 (4.4) | 6.1 |
| LeBron | 639 | **37.4% [33.2, 41.6]** | 44.6% [40.0, 49.4] | 4.2 (2.0) | 4.6 |
| Harden | 509 | **42.4% [37.5, 47.2]** | 49.5% [44.3, 54.4] | 3.4 (1.1) | 3.6 |

If passes went to a random one of the four teammates, the rate would be 25%.

**Registered comparison.** LeBron against the league on P(most open):
**+6.2 points [+1.9, +10.4]**. The MDE written down before the run was 5.5
points. The interval excludes zero and the point estimate exceeds the MDE.

**By where the most open man stands (league):**

| Most open man's spot | Share of passes | Pass reaches him | Mean space given up (ft) |
|---|---|---|---|
| Corner three | 26% | **14.6% [14.1, 15.0]** | 5.1 |
| 30+ ft | 15% | 41.3% [40.5, 42.2] | 5.3 |
| Elsewhere | 59% | 36.0% [35.6, 36.5] | 3.5 |
| Rim (≤ 6 ft) | 0.3% | 18.2% [14.3, 22.4] | 2.1 |

- LeBron finds the open corner man **30.3% [25.0, 36.2]** of the time and Harden
  **34.3% [26.7, 41.6]**, against the league's 14.6%. Curry: 15.8% [8.8, 23.3].
- The three players' rim cells rest on 1–3 passes each, so they are too thin
  to read. (Curry's "100%" is one pass.)

**Plain reading.**

- **When a player passes, the ball goes to the most open teammate about a
  third of the time,** only a little better than chance.
- **The typical pass gives up about 4 ft of space,** and buys about 3 ft of
  proximity to the basket in return.
- **The most open man is most often missed when he is in the corner.** He is
  found only 15% of the time there. That's the longest, most defended pass
  lane, and corner shooters are often "open" only because their defender is
  helping inside.
- **LeBron and Harden find the open man clearly more often than the league**
  (37% and 42%). For LeBron that difference passes the registered test.
- **Curry finds him less often** (24%). His passes trade space for proximity
  to the basket (6 ft closer on average), consistent with him passing inside
  rather than kicking out.

**Caveats.**

- **"Most open" is a snapshot at the pass frame,** not at the ball's
  arrival. Defenders move while the ball is in the air.
- **Corner and rim catches are open for different reasons:** help defence
  versus position.
- **Openness is not value.** The most open man may be a poor shooter, or
  too far away. This measures the choice of receiver, not whether it was
  right.

**Figure:** `figures/stage9/stage9_pass_open.svg` (and .png). Dots on the
45° line are passes to the most open man; LeBron is in colour.

## Stage 10: release timing against the closeout (registered `e507fa2`; result `11f8a5e`; descriptive)

*results.json key: `stage10_release_timing`*

**What was measured.** The sample is 24,324 catch-and-shoot jump shots
(catch to release ≤ 1.5 s, 16-30 ft) in the non-test games: 24,059 league,
the rest the gated three. 102 shots were dropped for missing motion
features.

- **Release time** = catch to release.
- **Closing speed** = how fast the nearest defender at release was
  approaching over the last 0.5 s (ft/s).
- **Quartile cuts:** 5.2, 8.0 and 10.5 ft/s, from the league.

The training-game pilot was disclosed before the run, and those games are
in the sample. Nothing here is confirmatory.

**Results (league; game-bootstrap 95% intervals).**

| Closing-speed quartile | Median closing speed (ft/s) | Median release time (s) | Median release openness (ft) | Make rate |
|---|---|---|---|---|
| Q1 (slowest) | 3.2 | 1.04 | 5.34 [5.24, 5.43] | 38.4% [37.2, 39.6] |
| Q2 | 6.7 | 0.96 | 4.65 [4.59, 4.69] | 37.2% [36.0, 38.5] |
| Q3 | 9.2 | 0.92 | 4.93 [4.86, 4.98] | 38.8% [37.5, 40.0] |
| Q4 (fastest) | 12.1 | 0.92 | 5.24 [5.18, 5.32] | 39.5% [38.3, 40.8] |

The median release times have degenerate intervals (e.g. 1.04 [1.04,
1.04]), because tracking runs at 25 frames a second: release times come in
0.04 s steps, and the median sits on one step.

- **By decile,** the median falls from 1.08 s (closing at 1.2 ft/s) to
  0.92 s at about 8.4 ft/s. It stays at 0.92 s through the fastest decile
  (13.5 ft/s): **a floor.**
- **Slope of release time on closing speed** (OLS, distance and zone
  controlled): **−0.0106 s per ft/s [−0.0113, −0.0099]**.
- **Space preserved** at the top-quartile closing speed (12.1 ft/s):
  **0.13 ft [0.12, 0.14]**.

**Rush-penalty curve** (make-probability AMEs against the 0.9-1.1 s bin;
24,020 shots; 39 under 0.3 s excluded):

| Release time | Shots | AME vs 0.9-1.1 s |
|---|---|---|
| 0.3-0.7 s | 1,104 | −2.5 points [−5.5, +0.6] |
| 0.7-0.9 s | 7,968 | −1.1 points [−2.6, +0.5] |
| 0.9-1.1 s | 9,535 | (reference) |
| 1.1-1.5 s | 5,413 | −0.4 points [−2.1, +1.3] |

**Registered reading** (the stationarity condition of the timing problem):

- **The openness slope:** the attempt-2 make model, refitted identically,
  gives dP/d(openness) = **0.0164 per ft** at release openness 4-6 ft. The
  brief's guide was about 0.02.
- **Loss** from waiting 0.1 s while a top-quartile defender closes at 12.1
  ft/s: **2.0 points [1.97, 1.99]** (the slope is held fixed).
- **Gain** in make probability per 0.1 s over 0.7-1.1 s, from the rush
  curve: **0.5 points [−0.2, +1.3]**. Over 1.0-1.3 s: 0.1 [−0.4, +0.7].
- **Gain − loss** over 0.7-1.1 s: **−1.4 points [−2.2, −0.7]**. The loss is
  larger, and the interval excludes zero.
- **What it says:** the rush penalty is flat above about 0.7 s (the gain
  interval includes zero), and waiting another 0.1 s costs more than it
  buys. By the registered reading, waiting at a fast closeout is pure loss.
  The ~0.9 s floor is mechanics (how fast a jump shot can be gathered and
  released), not a trade-off that players are solving at the margin.
- **Consistent with that:** shooters do release sooner when the closeout is
  fast, but only by 0.16 s from the slowest to the fastest decile, and only
  until they hit the floor. That saves about 0.13 ft of space, a rounding
  error on the 4 ft that defenders close between catch and release.

**The named players** (league cuts; median release time; slope in s per
ft/s):

| Player | Shots | Median closing speed | Median release time | Slope |
|---|---|---|---|---|
| Curry | 146 | 9.3 | **0.80 [0.76, 0.85]** | −0.015 [−0.027, +0.001] |
| Klay Thompson | 246 | 7.7 | **0.80 [0.76, 0.82]** | −0.004 [−0.010, +0.005] |
| JJ Redick | 204 | 7.6 | 0.96 [0.95, 1.00] | −0.011 [−0.019, −0.004] |
| LeBron | 37 | — | too thin (< 100) | — |
| Harden | 82 | — | too thin (< 100) | — |

- **Curry and Thompson release about 0.12 s faster than the league's
  floor,** whatever the closeout. Their quartile medians run 0.75-0.96 s
  (Curry) and 0.76-0.84 s (Thompson). Neither slope is distinguishable from
  zero.
- **Redick sits at the league's pace and does speed up** against faster
  closeouts (1.03 s → 0.92 s from Q1 to Q4).
- **The floor is a property of the shooter's mechanics:** the two fastest
  shooters in the league have a lower one.

**Caveats.**

- **The release marker is about 0.1 s late** (up to 0.5 s at close range).
  At 16-30 ft, differences across bins are comparable; levels are not.
- **Closing speed is measured over the 0.5 s before release,** so it partly
  reflects the timing it is set against. The slope is descriptive.
- **The loss calculation assumes the defender keeps closing at full speed**
  for the extra 0.1 s, and uses the make model's openness slope at 4-6 ft.
  Both make the loss an upper-end figure. On the point estimates, the two
  would balance only if the loss were about 4× smaller. At the gain's upper
  bound (1.3 points), it would need to be about 1.5× smaller.
- **The figure shows three of the five named players;** LeBron and Harden
  are too thin.

**Figure:** `figures/stage10/stage10_release_timing.svg` (and .png).

- **The figure's annotation is wrong on units.** It reads "space preserved
  at top-quartile closing speed: 0.13 ft [0.12, 0.14]".
- **It should read:** "release brought forward 0.13 s [0.12, 0.14] at a
  top-quartile closeout; space preserved ≈ 1.5 ft".
- **The figure was not redrawn.**

**Recorded after correction (2026-10-14): a registration error in the units
of (iii).**

- **The error.** The registered formula "space preserved = −slope × median
  top-quartile closing speed, in ft" yields **seconds**, not feet. The slope
  is in s per ft/s, and multiplying by ft/s leaves s.
  - The error came from the brief and was registered as written.
  - This is a registration error, not a code error: the script computed
    exactly the registered formula.
  - The 0.13 reported as "ft" above is a time.
- **Corrected quantities.** Both come from `checks/s10_stage10.json`; nothing
  was rerun.
  - **Release brought forward** at a top-quartile closeout: −slope × 12.08
    ft/s = **0.128 s [0.119, 0.137]**.
  - **Space preserved** = that time × the top-quartile median closing speed
    = 0.128 s × 12.08 ft/s = **1.55 ft**.
  - Its approximate interval is **[1.43, 1.66]**: the products of the
    corresponding interval ends. The bootstrap draws of the product were
    not stored.
- **What changes in the reading.** Releasing early against a fast closeout
  keeps about 1.5 ft of space, not 0.13 ft. That is a real share of the
  roughly 4 ft defenders close between catch and release, and the sentence
  above calling it "a rounding error" is withdrawn.
- **What doesn't change.** The registered timing reading (gain − loss −1.4
  points [−2.2, −0.7]) is computed separately and stands: shooters hurry
  against a fast closeout, and that hurry is worth about 1.5 ft. But at the
  margin, a further 0.1 s of waiting still costs more than it buys, down to
  the mechanical floor.

## Stage 11: Stage 9 with a deliberate-choice baseline (registered `8f1379f`; result `6257eba`; descriptive)

*results.json key: `stage11_pass_to_open_shooter`*

**What changed from Stage 9.** The pass table is the same. "Most open" is
now taken only over **candidates**: teammates 6-30 ft from the attacking
basket who are shooters, meaning at least 50 jump-shot attempts in non-test
games (289 of the 440 players with any).

- Passes with fewer than two candidates are excluded: **6,720**, leaving
  127,162.
- The receiver need not be a candidate. If he is not, the pass counts as
  missing the most open candidate. Receivers are candidates on 80% of
  league passes.

**The Stage 9 numbers stay in the record; these are the ones for the page.**

**Results** (game-bootstrap 95% intervals):

| Passer | Passes | To the most open candidate | Chance among candidates (1/n) | Receiver is a candidate | Space given up, mean (median), ft | Receiver closer to the basket by, mean, ft |
|---|---|---|---|---|---|---|
| League (non-gated) | 125,690 | **28.0% [27.6, 28.3]** | 33.0% | 80% | 3.2 (2.2) | 1.6 |
| Curry | 401 | 25.2% [21.6, 29.1] | 35.7% | 72% | 4.0 (3.5) | 3.9 |
| LeBron | 586 | **37.5% [33.6, 41.1]** | 38.4% | 74% | 3.1 (0.9) | 2.8 |
| Harden | 485 | **41.2% [36.7, 45.3]** | 38.8% | 76% | 2.9 (0.7) | 2.5 |

**Registered comparison.** LeBron against the league:
**+9.6 points [+5.7, +13.3]**.

- **MDE:** 0.055, written down at Stage 9's n = 639. At the realized n = 586,
  the same formula gives 0.058.
- **Result:** the interval excludes zero, and the point estimate exceeds
  the MDE.

**By where the most open candidate stands:**

| Passer | Most open candidate in the corner: share | Reached | Elsewhere: reached |
|---|---|---|---|
| League | 29% | **14.1% [13.6, 14.5]** | 33.5% [33.2, 33.9] |
| Curry | 22% | 15.7% [8.9, 23.1] | 27.9% [24.3, 31.7] |
| LeBron | 35% | **29.1% [24.8, 34.0]** | 42.1% [36.7, 47.2] |
| Harden | 39% | **32.8% [25.8, 40.1]** | 46.6% [41.3, 51.7] |

**Plain reading.**

- **Ruling out men open only because the defence ignores them** (30+ ft
  out, at the rim, non-shooters) does not make passers look more
  deliberate. It makes the league look less so.
  - The ball reaches the most open shooter **28%** of the time, below the 33%
    a random choice among shooters would give.
  - One in five league passes goes to a non-shooter or to a man outside the
    6-30 ft band (e.g. a big rolling to the rim). Those passes count as
    misses here.
  - Among passes that go to a candidate at all, the rate is roughly 0.28 /
    0.80 ≈ 35%, about chance. This is arithmetic on two registered numbers,
    not a registered quantity.
- **The trade is smaller than Stage 9 suggested:** about **3 ft of space**
  given up for about **1.6 ft of proximity** to the basket.
- **The corner is still where the open man goes unfound:** **one pass in
  seven** reaches the most open shooter when he is in the corner.
- **LeBron and Harden are the exceptions:**
  - they hit the most open shooter at or above chance (37.5% and 41.2%,
    against baselines of 38-39%);
  - they find the open corner shooter about twice as often as the league
    (29% and 33%);
  - **LeBron is +9.6 points above the league,** beyond the registered MDE.
- **Curry,** passing from the most crowded spot on the floor, finds the
  most open shooter 25% of the time, 10 points under his chance baseline. His
  passes buy 3.9 ft of proximity.

**Caveats** (as Stage 9):

- **The snapshot is at the pass frame,** not at the ball's arrival.
- **"Shooter" is a volume threshold** (50 jump attempts in half a season),
  not a measure of skill.
- **The 1/n baseline treats every candidate as equally reachable.** Passing
  lanes are not.

**Recorded after correction (2026-10-14): the like-for-like comparison.**
This was added on request after the run. It is post hoc and not registered.

- **Why it is needed.** The headline P(most open candidate) counts passes
  to non-candidates (20% of league passes) as misses. So it cannot be read
  against the 1/n baseline.
- **The like-for-like number.** P(receiver is the most open candidate |
  receiver is a candidate), against the mean of 1/n over the same passes.
- **How it was computed.** The per-pass table was rebuilt with Stage 11's
  own `build()` (`scripts/s17b_conditional.py`; no model is fitted).
  Intervals are a game bootstrap, 1,000 resamples, seed 0, as in Stage 11.
  Output: `checks/s11_conditional.json`.

| Passer | Passes to a candidate | Reaches the most open candidate | Chance (1/n, same passes) | Difference |
|---|---|---|---|---|
| League | 101,009 | **34.8% [34.4, 35.2]** | 31.1% | +3.7 [+3.3, +4.1] |
| Curry | 289 | 35.0% [30.3, 40.3] | 33.9% | +1.1 [−3.5, +6.2] |
| LeBron | 436 | **50.5% [45.9, 54.8]** | 37.2% | **+13.2 [+8.4, +17.4]** |
| Harden | 371 | **53.9% [49.0, 59.1]** | 37.2% | **+16.7 [+11.6, +21.8]** |

- LeBron − league on this measure: **+15.7 [+11.0, +20.1]**.

**Reading.**

- **Among shooters, the ball reaches the most open one only a little more
  often than chance** for the league (35% against 31%). Curry is at chance.
- **LeBron and Harden are the exceptions:** they find the most open shooter
  about half the time, 13-17 points above chance.
- The plain reading above ("below the 33% a random choice among shooters
  would give") compared numbers that are not like-for-like. This table
  replaces it for the page.

**Figure:** `figures/stage11/stage11_pass_open_shooter.svg` (and .png).
Dots on the 45° line are passes to the most open candidate. Dots above it
are passes to a receiver who was not a candidate and was more open than
every candidate.

## Stage 12: the exchange rate by situation, with partial pooling (registered `0535882`; result `40258aa`; descriptive)

*results.json key: `stage12_exchange_rate_by_situation`*

**What changed from 5c.** The cuts are the same, but each cut level now
gets Stage 8's treatment:

- every player with ≥ 150 catches in the level gets his own fit;
- the fits are shrunk toward a prior fitted within that level;
- the headline is the median over **all** of them, determinate or not.

Intervals are a bootstrap over players (1,000, seed 0), with posteriors held
fixed.

**Results** (median posterior exchange rate, seconds of clock per foot of
space):

| Cut | Level | Players | Median, all [95% CI] | Median, determinate only | IQR | Indeterminate | Prior μ |
|---|---|---|---|---|---|---|---|
| Margin | Behind by 5+ | 135 | **8.8** [8.5, 9.2] | 8.5 | 7.8–10.5 | 19% | 9.0 |
| | Within 5 | 179 | 7.8 [7.4, 8.3] | 7.2 | 6.4–9.5 | 20% | 7.6 |
| | Ahead by 5+ | 100 | **6.6** [5.7, 7.4] | 5.1 | 4.5–11.0 | 47% | 7.1 |
| Period | Q1–3 | 267 | 8.2 [7.8, 8.7] | 7.2 | 6.6–10.6 | 29% | 8.3 |
| | Q4 + OT | 54 | 8.3 [7.1, 8.6] | 6.8 | 6.5–10.4 | 33% | 8.1 |
| Home/away | Home | 215 | 7.8 [7.3, 8.1] | 6.9 | 6.1–11.1 | 35% | 8.1 |
| | Away | 213 | 7.6 [7.3, 7.9] | 6.9 | 6.2–10.1 | 31% | 7.7 |
| Catch source | Pass | 302 | 8.2 [7.8, 8.6] | 7.3 | 6.8–11.7 | 30% | 8.6 |
| | Loose ball / steal | 0 | **too thin to pool** (4,319 catches; no player has 150) | | | | |

- Offensive-rebound (1,276) and inbound (264) catches were dropped as thin.
- One player's fit failed in each of "ahead by 5+" and "pass", and was
  excluded.

**Differences between levels** (bootstrap over players):

| Comparison | Difference (s/ft) [95% CI] |
|---|---|
| Behind 5+ − ahead 5+ | **+2.1 [+1.2, +3.1]** |
| Behind 5+ − within 5 | **+0.9 [+0.5, +1.5]** |
| Q4+OT − Q1–3 | +0.1 [−1.2, +0.6] |
| Home − away | +0.2 [−0.4, +0.7] |
| Loose ball/steal − pass | not estimable (level too thin) |

**The three players** (posterior ER [95% interval]; "too thin" means fewer
than 150 catches in the level; "indet." means the clock sign flips in more
than 5% of posterior draws):

| Level | Curry | LeBron | Harden |
|---|---|---|---|
| Behind 5+ | too thin (49) | too thin (131) | 8.1 [4.0, 32.6] |
| Within 5 | 6.4 [3.0, 33.3] | 6.5 [3.3, 23.0] | indet. |
| Ahead 5+ | **3.9 [2.3, 9.9]** | 6.0 [−26, 49] | too thin (132) |
| Q1–3 | 6.4 [3.5, 22.2] | 6.1 [3.5, 19.0] | indet. |
| Q4+OT | too thin (70) | too thin (144) | too thin (121) |
| Home | 8.9 [−37, 71] | 7.1 [−22, 50] | indet. |
| Away | **3.8 [2.4, 8.7]** | 6.2 [3.5, 21.5] | 10.6 [−46, 78] |
| Pass | 5.4 [3.3, 14.2] | 6.6 [3.8, 21.8] | indet. |

**Plain reading.**

- **Situation matters through the score, not the quarter or the venue.**
  With every player counted and shrunk, a team behind by 5+ treats a foot of
  space as worth about 9 seconds of clock. A team ahead by 5+ treats it as
  worth about 6.6.
  - Trailing teams demand more space before they shoot early; leading
    teams take what they get.
  - The difference (+2.1 s/ft) excludes zero.
  - It confirms the direction of 5c's behind-vs-within gap (8.1 vs 6.7,
    pooled). It also separates behind from ahead, whose intervals overlapped
    in 5c (8.1 [7.1, 9.5] vs 7.0 [6.3, 7.9]).
- **Fourth quarter vs the first three, and home vs away: no difference.**
- **5c's loose-ball/steal finding cannot be checked this way:** no player
  has 150 such catches. 5c's pooled 2.7 s/ft stays as the only estimate. It
  is a league-pooled number, not a per-player one.
- **Curry's low rate comes from away games and from leading** (3.8 and 3.9
  s/ft, the only individually precise cells). At home, his rate is
  indistinguishable from the league's, with a very wide interval.
- **Harden is clock-indeterminate in most cells,** as in Stage 8.

**Caveats.**

- **The interval holds each player's posterior fixed.** It reflects which
  players are in the level, not the noise in each estimate, so it is
  narrower than a full bootstrap would be.
- **"Ahead by 5+" has 47% indeterminate players.** Its all-player median
  leans on noisy rates. The determinate-only medians (8.5, 7.2, 5.1) show
  the same ordering.

**Figure:** `figures/stage12/stage12_er_by_situation.svg` (and .png).

## Suggested site paragraph (current; updated after the record corrections, 2026-10-14)

> **Do great shooters shoot when the points say to?** Using player tracking
> from the first half of 2015-16, I parsed 621 games, valued every catch
> with a shot model calibrated on fresh games, and pre-registered every
> test.
>
> Space drives the decision. Priced in shot-clock seconds, a foot of space
> at the catch is worth about seven seconds to the league, nearly nine on
> threes and five from mid-range, and Curry weights it less than nine players
> in ten. Teams trailing by five or more ask for more: a foot is worth about
> nine seconds to them, against under seven for teams leading by five. For a
> quarter of the league, Harden among them, the clock doesn't measurably move
> the decision at all. Yet by the points, that space barely changes whether
> shooting beats passing or driving, partly because defenders take most of
> it back before the release. Shooters do hurry against a fast closeout, but
> only down to a fixed floor; another tenth of a second of set-up would buy
> less than the defender takes back, so the floor is mechanics, not a choice.
> Against the measured values, the league shoots far less than a
> points-maximiser would at every stage of the clock, and the shots the clock
> forces go in about as often as the rest (1.4 points lower, interval −6 to
> +3); only the last four seconds are clearly rushed.
>
> Whether players pass up shots because they see something the tracking
> can't, I couldn't settle: three instrument sets were too weak for a
> selection model to recover passed-up shot quality to within three points,
> and the record shows the precision any instrument would need (SE on rho
> of about 0.02) against what the three sets achieved (0.06-0.16). Passers
> trade space the same way, giving up about three feet of it for under two
> feet of proximity to the basket: when the ball goes to a shooter within 30
> feet, it reaches the most open one 35% of the time, little more than the
> 31% a random pick among them would. LeBron and Harden find him about half
> the time; when the most open shooter is in the corner, he gets the ball
> one time in seven.
>
> The record also shows my own mistakes, each caught by a check, five of
> them gates set below their own noise floor.

**What changed from the version after Stages 10–12:**

- **The passing sentence** now uses the like-for-like Stage 11 number: 35%
  against 31% chance, with LeBron and Harden about half the time.
  - The old "28%" counted passes to non-shooters as misses.
  - The old "LeBron ten points more" is replaced by the conditional
    comparison, where LeBron is +15.7 over the league.
- **The instrument clause** now states the precision needed against the
  precision achieved, instead of "why no instrument in this data could".
- **Stage 10's sentence is unchanged.** It makes no claim in feet.

## Suggested site paragraph (after Stages 10–12; superseded after the record corrections, kept for the record)

> **Do great shooters shoot when the points say to?** Using player tracking
> from the first half of 2015-16, I parsed 621 games, valued every catch
> with a shot model calibrated on fresh games, and pre-registered every
> test.
>
> Space drives the decision. Priced in shot-clock seconds, a foot of space
> at the catch is worth about seven seconds to the league, nearly nine on
> threes and five from mid-range, and Curry weights it less than nine players
> in ten. Teams trailing by five or more ask for more: a foot is worth about
> nine seconds to them, against under seven for teams leading by five. For a
> quarter of the league, Harden among them, the clock doesn't measurably move
> the decision at all. Yet by the points, that space barely changes whether
> shooting beats passing or driving, partly because defenders take most of
> it back before the release. Shooters do hurry against a fast closeout, but
> only down to a fixed floor; another tenth of a second of set-up would buy
> less than the defender takes back, so the floor is mechanics, not a choice.
> Against the measured values, the league shoots far less than a
> points-maximiser would at every stage of the clock, and the shots the clock
> forces go in about as often as the rest (1.4 points lower, interval −6 to
> +3); only the last four seconds are clearly rushed.
>
> Whether players pass up shots because they see something the tracking
> can't, I couldn't settle: three instrument sets were too weak for a
> selection model to recover passed-up shot quality to within three points,
> and the record shows why no instrument in this data could. Passers trade
> space the same way: the ball reaches the most open shooter within 30 feet
> only 28% of the time, giving up three feet of space for under two feet of
> proximity to the basket. LeBron finds him ten points more often than the
> league; when the most open shooter is in the corner, he gets the ball one
> time in seven.
>
> The record also shows my own mistakes, each caught by a check, five of
> them gates set below their own noise floor.

**What changed from the brief's draft, and why:**

- **Stage 12 adds one sentence** (trailing vs leading). Behind 5+ minus
  ahead 5+ is +2.1 s/ft [+1.2, +3.1]; the interval excludes zero.
- **Stage 10 adds one sentence** (the release floor). Gain − loss is −1.4
  points [−2.2, −0.7]; the interval excludes zero.
  - The floor's level (~0.9 s) is left out on purpose, because the release
    marker is about 0.1 s late.
- **Stage 11 replaces the draft's Stage 9 passing numbers,** as registered.
  - "A third of the time" becomes 28%.
  - "Four feet of space for three feet of proximity" becomes three feet for
    under two (3.2 and 1.6 ft).
  - LeBron's margin goes from six points to ten (+9.6 [+5.7, +13.3]).
  - The corner stays one in seven (14.1%).
- **Left out:** the comparison with a random pick among shooters (33%).
  One receiver in five is not a candidate, so 28% vs 33% is not
  like-for-like; it stays in the Stage 11 section.
- **Unchanged:**
  - "about seven seconds": Stage 8's 7.8 / 6.9 are within 1 s/ft of 7;
  - "less than nine players in ten": Curry is at the 11th percentile;
  - "a quarter of the league": 28% are indeterminate;
  - "four seconds", "−6 to +3": Stage 7;
  - "five" gate errors: see the gate-error count in the chronological
    table.
- **Period, home/away and the loose-ball check (Stage 12) add nothing.**
  Their intervals include zero, or the level is too thin.

## Suggested site paragraph (after Stage 7; superseded after Stages 10–12, kept for the record)

> **Do great shooters shoot when the points say to?** Using player tracking
> from the first half of 2015-16, I parsed 621 games and valued every catch
> with a shot model calibrated on fresh games, pre-registering every test.
>
> Space is the big driver of the decision. Priced in shot-clock seconds, the
> typical player treats a foot of space at the catch like about seven seconds
> for the league (five for the median player whose clock response is
> measurable): nearly nine on threes, five from mid-range. Yet by the points,
> that space barely changes whether shooting beats passing or driving. And
> against the measured values, league players shoot far less often than a
> points-maximiser would, at every stage of the clock.
>
> The extra shots players take as the clock runs down go in about as often
> as the earlier ones: 1.4 points less at equal openness, distance and type,
> but anywhere from 6 points worse to 3 better. That is too wide to say
> whether they are passing up shots the tracking can't see are bad. Only the
> rushed last four seconds are clearly worse. I tried three sets of
> "instruments", meaning things that shift the decision but not the make:
> teammate openness and score, then the shot clock, then the player's rhythm.
> The clock and rhythm passed falsification tests; the first set passed only
> a strength test. None was strong enough for the selection model to recover
> passed-up shot quality in simulations built to match the data.
>
> One by-product: no positive hot hand. The record also shows my own
> mistakes, each caught by a check.

## Suggested site paragraph (corrected after review; superseded after Stage 7, kept for the record)

> **Do great shooters shoot when the points say to?** Using player tracking
> from the first half of 2015-16, I parsed 621 games and valued every catch
> with a shot model calibrated on fresh games, pre-registering every test.
>
> Space is the big driver of the decision. Priced in shot-clock seconds, the
> typical player treats a foot of space at the catch like about seven seconds
> for the league (five for the median player whose clock response is
> measurable): nearly nine on threes, five from mid-range. Yet by the points,
> that space barely changes whether shooting beats passing or driving. And
> against the measured values, league players shoot far less often than a
> points-maximiser would, at every stage of the clock.
>
> Whether they pass up shots because they can see something the tracking
> can't, I couldn't settle. I tried three sets of "instruments", meaning
> things that shift the decision but not the make: teammate openness and
> score, then the shot clock, then the player's rhythm. The clock and rhythm
> passed falsification tests; the first set passed only a strength test.
> None was strong enough for the selection model to recover passed-up shot
> quality in simulations built to match the data.
>
> One by-product: no positive hot hand. The record also shows my own
> mistakes, each caught by a check.

## Suggested site paragraph (after Stage 6; superseded after review, kept for the record)

> **Do great shooters shoot when the points say to?** Using player tracking
> from the first half of 2015-16, I parsed 621 games and valued every catch
> with a shot model calibrated on fresh games, pre-registering every test.
>
> Space is the big driver of the decision. Priced in shot-clock seconds, the
> typical player treats a foot of space at the catch like about five seconds:
> nearly nine on threes, five from mid-range. Yet by the points, that space
> barely changes whether shooting beats passing or driving. And against the
> measured values, players shoot far less often than a points-maximiser
> would, at every stage of the clock.
>
> Whether they pass up shots because they can see something the tracking
> can't, I couldn't settle. I tried three sets of "instruments", meaning
> things that shift the decision but not the make: teammate openness and
> score, then the shot clock, then the player's rhythm. Each passed its
> falsification test, but none was strong enough for the selection model to
> recover passed-up shot quality in simulations built to match the data.
>
> Two by-products: no positive hot hand (after a make, the next shot goes in
> slightly *less* often, consistent with players taking harder shots when
> they feel hot), and Curry shoots off the catch less in games where his
> first shot went in. The record also shows my own mistakes, each caught by a
> check.

## Suggested site paragraph (after Stage 4; superseded, kept for the record)

> **Do great shooters shoot when the points say to?** A follow-up to my
> shot-selection project, using player tracking from the first half of the
> 2015-16 season, where defenders are visible *before* the shot. I built a
> catch detector, checked by eye on held-out plays, and parsed 621 games. I
> valued every catch with a shot model calibrated on fresh games, and
> pre-registered every test.
>
> The clearest finding is about *space*. By the points, being open when you
> catch the ball barely changes whether a shot beats passing or driving: a
> foot of space is worth about zero, slightly favouring continuing. Yet
> players react to it strongly. Priced through how they respond to the shot
> clock, the league acts as if an open foot were worth about 0.014 points
> toward shooting (Curry 0.008, LeBron 0.009; Harden's clock response is too
> flat to price). And against the measured values, everyone shoots far less
> often than a points-maximiser would, at every stage of the clock.
>
> Two caveats travel with that. The value of "not shooting" is what teams
> actually did next, not the best they could have done. And the
> pre-registered choice model never passed its power checks. Two of my own
> mistakes, both caught by the checks, are in the record: a calibration rule
> set below its own noise floor, and rim catches valued with a jump-shot
> model.

## Site paragraph (superseded; kept for the record)

> **Do great shooters shoot when the points say to?** A follow-up to my
> shot-selection project, this time using player-tracking data from the first
> half of the 2015-16 season, where defenders are visible *before* the shot.
> I built a catch detector (checked by eye on held-out plays), parsed 621
> games, and valued every catch with a shot model calibrated on fresh games,
> pre-registering every test.
>
> The data say something clear and something unanswerable. Clear: Curry,
> Harden and LeBron all shoot far more often when they catch the ball open.
> Each extra foot of space raises the odds of an immediate shot by 15–30%,
> though a foot of space is worth only about 0.02–0.03 points by the
> make-probability numbers. Unanswerable: their choices don't respond
> detectably to the *other* parts of a shot's value, such as distance or the
> shot clock. So there is no stable exchange rate to say whether they over-
> or under-value an open look, and the pre-registered choice model never
> passed its power checks.
>
> Along the way the record shows two of my own mistakes, both caught by the
> checks: a calibration rule set below its own noise floor, and rim catches
> valued with a jump-shot model.

---

# Stage 3b-prep, calibration attempt 2 and the registered sequence (2026-10-13): no gated player proceeds

**Recorded first.** The replacement bins criterion had been set at about 1.3
SE of its noisiest bin, which is the same error as the old project's v3b
gate: a perfect model fails it often.

Attempt 2 was registered before running (`0812282`):

- 60 fresh calibration games (seed 2028) removed from league training;
- an openness spline replaces log(1 + openness) in the main effect;
- bins limit max(0.04, 2 SE).

## Make model (attempt 2): PASS, scored once on the fresh games

The fresh set has 5,546 jump shots; 58 of the 60 games contain any.

| Criterion | Result | Limit |
|---|---|---|
| Level | 0.0095 (pred .378 vs obs .368) | ≤ 0.01 |
| Gradient (0–4 ft → 8+ ft) | 0.057 predicted vs 0.050 observed: **0.0068** | ≤ 0.03 |
| Bins, error / limit | 0–2: .006/.040 · 2–4: .012/.040 · 4–6: .005/.040 · 6–8: .011/.040 · 8–12: .013/.053 · 12+: .029/.083 | all pass |

- ECE (information) 0.0153.
- The observed-over-predicted gradient ratio is **0.88**. It feeds the
  registered gradient-scale sensitivity for the main fit.
- The level passes, but only just (0.0095 against 0.01).

**Recorded after review.** Two of the three criteria were not properly
powered. Only the bins rule was. These are **gate errors three and four**.

- **Level limit:** 0.01 at n = 5,546, where the standard error of the
  overall make rate is 0.0065. The limit is 1.5 SE.
- **Gradient limit:** 0.03, comparing n = 2,651 shots at 0–4 ft with 474 at
  8+ ft, where the standard error of the difference is 0.024. The limit is
  1.2 SE.
- **So a perfectly calibrated model fails at least one of the two about 30%
  of the time** (my check: 31%).
- Both passed here.

## Values

**V_shoot** uses the counterfactual release openness: openness at catch +
1.0 s (delta 0.96 s).

- **Shot-side adjustment applied** (above 1 ft): rim 1.33 ft, above-break
  three 1.01 ft. Mid-range (0.54) and corner (0.53) are unchanged.
- **g(zone):** rim 0.107, mid 0.135, above-break 0.162, corner 0.168.

**Selection in V_continue, measured (7a):**

| Group (league, 22–30 ft, ≥ 40 catches) | Players | Continuing catches | Openness slope (pts/ft) [95% CI] |
|---|---|---|---|
| Control (shoot-now rate < 2%) | 28 | 2,260 | 0.0010 [−0.0143, 0.0158] |
| Shooters | 310 | 58,743 | 0.0086 [0.0054, 0.0119] |

- **No selection detected:** 0.0086 is inside the control interval.
- **The test is weak,** because the control group is small (interval width
  0.03 pts/ft).

**Dubin–McFadden (7c), synthetic validation with known values (ρ = 0.3,
n = 129,131):**

- the corrected interval covers the true slope in **20 of 20** seeds;
- the naive one misses in only **3 of 20** (mean bias −0.0009 pts/ft).
- So the naive estimate does **not** visibly fail, and the correction is
  **not shown to work** under the rule. At this sample size and error
  correlation, the selection bias it targets is negligible.
- **Naive V_continue is primary.** The Dubin–McFadden version (real-data
  openness slope 0.0052 against 0.0100 naive) is kept as a sensitivity.
- **Bias direction (stated):** if selection exists, V_continue(open) is
  overstated, and c_shoot is biased toward a shooter's premium.

## Value gap, old (Stage 3a) and new, by counterfactual release openness (22–30 ft, train)

| Player | Bin (ft) | n | Shoot-now rate | Gap new | Gap old |
|---|---|---|---|---|---|
| **Curry** | 0–4 | 239 | 20% | 0.196 | 0.293 |
| | 4–6 | 55 | 26% | 0.268 | 0.304 |
| | 6–8 | 14 | 71% | 0.318 | 0.251 |
| | 8–12 | 7 | 43% | 0.171 | 0.079 |
| | 12+ | 8 | 38% | 0.223 | 0.168 |
| **Harden** | 0–4 | 185 | 15% | 0.081 | 0.199 |
| | 4–6 | 92 | 14% | 0.166 | 0.207 |
| | 6–8 | 22 | 23% | 0.213 | 0.170 |
| | 8–12 | 10 | 30% | 0.180 | 0.175 |
| | 12+ | 2 | 0% | 0.038 | 0.091 |
| **LeBron** (not gated) | 0–4 | 115 | 1% | 0.074 | 0.276 |
| | 4–6 | 94 | 11% | 0.151 | 0.267 |
| | 6–8 | 57 | 11% | 0.183 | 0.259 |
| | 8–12 | 33 | 12% | 0.151 | 0.239 |
| | 12+ | 5 | 20% | 0.236 | 0.280 |

The new values do increase with openness for every player, which the old
values did not. But the increase is small, about 0.1 points across the
range. And the counterfactual openness is concentrated under 4 ft, because
defenders close.

## Checks and decisions

| | Curry | Harden | LeBron (reported, not gated) |
|---|---|---|---|
| 1. Value-gap slope, 22–30 ft (pts/ft) [95% CI] | 0.0050 [−0.0059, 0.0183] **FAIL** | 0.0187 [0.0097, 0.0293] pass | 0.0162 [0.0109, 0.0216] pass |
| 2. Pilot T | (not reached) | **496, diverged** | **720, diverged** |
| MDE at c = 0 (bar 0.15) | | 142, **underpowered** | 186 |
| Sensitivity, Dubin–McFadden V_continue: pilot T and MDE | | 91 and 27 | 588 and 153 |
| 3. Synthetic recovery | not run | not run | not run |

**Decision:** **no gated player proceeds.** Curry stops at check 1, and
Harden is underpowered because the pilot T diverged. The games-needed numbers
at a diverged T are meaningless and not quoted. There was no real fit of c.

## Why the pilot diverges (slopes only; no c looked at)

| Slope of P(shoot) on the value gap | Curry | LeBron | Harden |
|---|---|---|---|
| All catches ≤ 30 ft | −0.27 | −2.57 | −1.05 |
| 22–30 ft only | +0.05 | +0.16 | −1.82 |

1. **The rim zone pulls the slope negative.** The value gap there is −0.16 to
   −0.22, yet players shoot 18–33% of rim catches. **The make model is jump
   shots only** (as registered), but it values rim catches, whose shots are
   mostly layups and dunks. So it understates V_shoot at the rim. This is a
   scope mismatch I should have flagged when registering.
2. **Within the three-point band the gap barely moves the choice.** Openness
   moves the value of shooting by about 0.1 points across its whole range,
   while shoot rates move a lot (Harden 15% → 30%). Harden's slope is even
   negative. A model where the choice depends only on the value gap cannot
   fit that with a sensible T.

## Options for Colin (none taken)

- (a) Value rim and close catches with a make model trained on their own
  shot types (layups, dunks, floaters), or restrict the unit to jump-shot
  range (for example 16–30 ft). This is a scope decision, registered before
  running.
- (b) Accept that the value gap from release openness is too flat to carry
  the choice. The decision depends on openness far more than the points do,
  which is itself the descriptive result.
- (c) Stop.

---

# Stage 3b-prep, re-score (2026-10-13): STOPPED; the bins criterion fails by 0.00002

**On the record:**

- **The registered powered-ECE rule failed and stays failed.** It tested
  *perfect* calibration, which at 11,550 shots detects errors too small to
  matter.
- **Colin's replacement criteria were chosen after seeing that result.**
  They target what passes into c_shoot: the level, the openness gradient,
  and local error by openness.
- **The same model was scored once** on the same shots. It was rebuilt by the
  identical deterministic code path; the Platt map matches to every digit and
  the ECE is 0.016258.

| Criterion | Result | Limit | Outcome |
|---|---|---|---|
| Level, \|mean pred − mean obs\| | 0.3766 vs 0.3760, **0.0006** | ≤ 0.01 | pass |
| Gradient, change from 0–4 ft to 8+ ft (pred vs obs) | 0.067 vs 0.091, **0.024** | ≤ 0.03 | pass |
| Bins, worst \|error\| | **0.040019** (12+ ft bin) | ≤ 0.04 | **FAIL** |

| Release openness (ft) | 0–2 | 2–4 | 4–6 | 6–8 | 8–12 | 12+ |
|---|---|---|---|---|---|---|
| n | 1,101 | 4,250 | 3,933 | 1,328 | 679 | 259 |
| Predicted | .329 | .366 | .382 | .399 | .422 | .435 |
| Observed | .312 | .367 | .373 | .418 | .436 | .475 |
| Error | +.016 | −.001 | +.010 | −.019 | −.014 | **−.040** |

**How small the miss is.**

- The 12+ bin misses by 0.00002, less than one shot: 123 makes in 259, and
  one fewer make would pass.
- In that bin the observed rate's binomial SE is 0.031, so a 0.04 limit is
  about 1.3 SE there.
- The model's error is real but small, and it has a pattern: it slightly
  **understates** the gain from being very open (8+ ft, by 1.4–4 points).
  This is also visible in the gradient (0.067 predicted vs 0.091 observed).

**Stopped per the rule.** There is no fix on the spent validation games.
V_shoot, V_continue, 7a–7c, the checks, power and synthetic were not run.
The code for all of them is written.

**Decision for Colin.** Each of these is a new post-hoc choice, so I haven't
made any:

1. accept the near-miss, with the record showing it failed;
2. score a registered fix on a fresh calibration set. None remains in this
   archive unless train games are re-split and the model refit, which is
   itself a registered change;
3. stop the project at this point.

---

# Stage 3b-prep results (2026-10-13): STOPPED at the make-model calibration rule (narrow fail)

*results.json key: `stage3b_prep`*

**Commits:** registration `ca82621` and `f3a51a5`; the scored result at the
latest commit. There is no real fit of c, and power and synthetic recovery
were not run.

## Parse

- **621 of 626 archives parsed.** Four are empty upstream (01.14 DET@MEM,
  CLE@SAS, CHI@PHI; 01.23 UTA@WAS), and one has no tracking frames (01.23
  CHI@CLE).
- **Totals:** 247,358 counted catches and 104,568 FG attempts.
- **Split:** 474 train, 126 validation, 21 test (unchanged and untouched).
  The 505 new games went 80/20.

## All league threes by defender distance at release (completes Colin's table)

| Release openness (ft) | 0–2 | 2–4 | 4–6 | 6–8 | 8–12 | 12+ |
|---|---|---|---|---|---|---|
| All league threes, make % (n) | 28.1 (919) | 31.4 (6,509) | 35.6 (9,763) | 38.1 (4,049) | 40.8 (2,255) | 40.8 (1,201) |
| Catch-and-shoot threes, make % (n) | 30.6 (588) | 33.4 (4,474) | 36.3 (7,449) | 39.0 (3,339) | 41.6 (1,901) | 40.6 (1,071) |

This matches Colin's 29% to 43% for all threes; mine are 28% to 41% over
24,696 shots.

## Step 2, make model on release openness: FAILS the powered rule (narrowly)

**Model:** league jump shots, 42,919 train and 11,550 validation (half
catch-and-shoot). Validation **ECE 0.0163**, against a perfect-model median
of 0.0112 and **95th percentile of 0.0159**.

| Decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Predicted | .286 | .329 | .347 | .360 | .372 | .383 | .395 | .409 | .427 | .458 |
| Observed | .292 | .312 | .330 | .389 | .391 | .389 | .365 | .398 | .446 | .450 |

- **The errors are small and not systematic.** The largest miss is about 3
  points (deciles 4 and 7, in opposite directions), and the overall level
  matches (mean predicted ≈ mean observed ≈ 0.38).
- **The rule bites because the sample is large.** With 11,550 shots, the
  perfect-model noise floor is about 1.1 points, so 1.6 points of average
  miscalibration is detectable.
- **What it means for V_shoot.** A 1.6-point error in P(make) is about 0.05
  points of V_shoot on a three. That is a third of the 0.15 effect the power
  rule targets, so it is not negligible.
- **Per the registration** ("If it fails: stop and report"), V_shoot was
  **not built.** The control-group test (7a), the Dubin–McFadden validation
  (7c), the value-gap check, power and synthetic were **not run**.

**The openness effect the model learned** (catch-and-shoot, shot clock 12):

| Release openness (ft) | 1 | 2 | 4 | 6 | 8 | 12 |
|---|---|---|---|---|---|---|
| Three, 25 ft | .307 | .327 | .355 | .373 | .388 | .409 |
| Mid-range, 16 ft | .400 | .425 | .457 | .479 | .495 | .518 |

**Late-clock cross-check** (logit slope on log(1 + release openness)):

- all train jump shots: **0.344** [0.296, 0.394];
- shot clock ≤ 4 s: **0.479** [0.327, 0.671] (n = 4,273).

The openness effect is at least as strong when the clock forces the shot, so
it is not an artefact of shot selection.

## Steps that don't depend on the make model (computed)

**Step 3.** delta = **0.96 s**, the median catch-to-release time of league
catch-and-shoots, used as 25 frames (1.0 s).

**Counterfactual release openness against openness at catch,** league train
catches within 30 ft:

| Zone | n | Median change (cf − catch) | Correlation | Share where defender closer |
|---|---|---|---|---|
| Rim | 8,229 | +0.23 ft | 0.14 | 45% |
| Mid | 66,538 | −1.52 ft | 0.39 | 71% |
| Above-break three | 63,113 | −3.28 ft | 0.31 | 86% |
| Corner three | 9,751 | −6.49 ft | 0.43 | 96% |

Defenders close hard on catches beyond the arc. Openness at catch explains
only 10–18% of the variance in openness 1 s later.

**Step 7b, the shot-side check.** At equal catch openness, catches that did
**not** become shots had a counterfactual openness larger than the shots
had by:

| Zone | Non-shot − shot | Rule outcome |
|---|---|---|
| Rim | **1.33 ft** | > 1 ft: subtracted for non-shooters |
| Above-break three | **1.02 ft** | > 1 ft: subtracted for non-shooters |
| Mid | 0.55 ft | below 1 ft: no change |
| Corner three | 0.58 ft | below 1 ft: no change |

**Recomputed g(zone)** on the larger set: rim 0.098, mid 0.134, above-break
0.160, corner 0.165.

## Decision for Colin

The make model misses a perfect-calibration standard by a hair at a sample
size where 1.6 points is detectable. Options:

1. **Accept the near-miss as fit for purpose,** with a stated error bound
   (for example, judge calibration by the maximum decile error against a
   tolerance like 0.03, with the bound registered).
2. **Register a fix and score once on a fresh calibration set.** The 126
   validation games are now used. One fresh set is the four held-out games
   from Stage 2, or a split of the validation games registered before
   looking.
3. **Keep the rule and stop here.**

Everything downstream (7a, 7c, the checks, power, synthetic) is written and
ready to run in about 15 minutes once you decide.

---

# Stage 3b-prep: finding recorded first (2026-10-13)

**Correction to Stage 3a.** "Openness does not move the value of shooting"
was an **artefact**. It came from measuring openness at the *catch* on
*taken* shots. Taken catch-and-shoot threes almost never have a defender
close at the catch; the defender closes during the shot.

**Colin's tables:**

- Of 2,607 league catch-and-shoot threes, 74 had the defender within 6 ft at
  the catch.
- By defender distance at **release**, the same shots run **34% (0–2 ft) to
  47% (8–12 ft)**.
- All league threes run **29% to 43%**.

**My reproduction,** 2,713 non-test league catch-and-shoot threes, 62 with
the defender within 6 ft at the catch:

| Defender distance (ft) | 0–2 | 2–4 | 4–6 | 6–8 | 8–12 | 12+ |
|---|---|---|---|---|---|---|
| At release: make % (n) | 30.8 (78) | 33.6 (703) | 38.1 (1,028) | 42.5 (463) | 46.2 (264) | 46.3 (177) |
| At catch: make % (n) | 0 (2) | 28.6 (14) | 28.3 (46) | 34.9 (195) | 38.3 (872) | 40.0 (1,584) |

---

# Stage 3a, continued (2026-10-13): no player proceeds; the value model does not see what drives the choice

All part 3 changes were registered before running (`4a1b93d`, amendments
`1dcdbba` and `705a334`, scope rule `8aeac43`). There is **no real-player
fit**. The pilot T was the only real-data choice fit, and its c was never
printed.

## Decisions carried out

| Item | Result | Bar | Outcome |
|---|---|---|---|
| Powered calibration rule | Replaces the fixed 0.03 (a perfect model passed it 29% of the time) | | Recorded |
| **V_shoot fix** (spline, shot clock, openness × distance, zone; Platt map from cross-validated training predictions), scored once | **ECE 0.0385** | perfect-model 95th percentile, 0.0492 | **PASS** (p = 0.31) |
| **g(zone)**, points after a catch-and-shoot beyond the shot itself | rim 0.143, mid 0.216, above-break 0.130, corner 0.143 | | V_shoot is now on the possession scale |
| **Drive/pass retest** (fresh 60, labels first) | **51 / 60** (strata 16 / 16 / 19) | 54, none below 16 | **FAIL.** Binary is primary; four-way is a registered extension; not retried |
| Design notes and the 2.0 s sensitivity | Added to the README | | |

**V_shoot decile table.** The validation make rate is 48.5%; the lowest deciles
are still about 6 points under-predicted.

| Predicted | .32 | .35 | .38 | .39 | .41 | .44 | .47 | .55 | .64 | .74 |
|---|---|---|---|---|---|---|---|---|---|---|
| Observed | .38 | .46 | .41 | .41 | .44 | .46 | .47 | .50 | .63 | .69 |

**Drive/pass findings.**

- **The tuning-set review found my own label errors.** At least 4 of the
  first check's 7 "errors" were mine. Two "lob passes" were the catcher's
  own shots, one label misread the drive-start rule, and one misread the
  catch distance. The first FAIL stands as committed.
- **Retest errors** were mostly transition drives that start 38+ ft out and
  that D-v2 missed (3), plus 4 passes it called holds.

## Two problems found after the V_shoot fix passed

**1. V_shoot extrapolates beyond its data.**

- Mean make probability is 0.57 at 35–47 ft, up to 0.97 for a 45 ft catch,
  against 0.41 at 26–30 ft.
- 98% of league training catch-and-shoots are within 30 ft.
- Validation calibration cannot see this, because validation shots come from
  the same range.
- **I did not modify V_shoot.** I registered a **scope rule**: the choice
  unit is catches within 30 ft. This removes 22% (Curry), 28% (LeBron) and
  36% (Harden) of training catches. **This needs your sign-off**, since it
  narrows the unit you defined.

**2. Openness at the catch barely moves the value of shooting, so the
identification route in the design notes does not hold.**

| Openness at catch (ft) | 1 | 3 | 5 | 8 | 12 |
|---|---|---|---|---|---|
| League model P(make), 25 ft above-break three | .348 | .356 | .361 | .366 | .370 |
| League model P(make), 16 ft mid-range | .476 | .513 | .534 | .556 | .575 |

- **The raw data agree.** League catch-and-shoot threes from 22–30 ft go in
  at **39%, 36% and 39%** across the openness thirds of the shots taken.
- **Players shoot far more when open** (Stage 2: 5% to 46% for Curry), but
  the shots taken go in at about the same rate whatever the openness. That
  is consistent with selection: contested catch-and-shoots are rare and taken
  by those who can make them.
- **So V_shoot − V_continue varies mostly with distance and zone, not
  openness.** For two of the three players it moves the *opposite* way from
  their shooting.

Diagnostic slopes from the training catches (slopes only; no intercepts or c
were looked at):

| Slope of P(shoot now) on | Curry | LeBron | Harden |
|---|---|---|---|
| V_shoot − V_continue (= 1/T) | **−1.06** | +1.73 | **−3.69** |
| the same, within zone (zone-c model) | **−1.63** | +1.50 | **−5.25** |
| log(1 + openness at catch) | +1.80 | +0.91 | +2.77 |

## Power (binary model, catches within 30 ft, training games), and decisions

| | Curry | LeBron | Harden |
|---|---|---|---|
| Training catches (shoot now) | 493 (122) | 535 (44) | 500 (64) |
| Pilot T | **1,091 (diverged)** | 0.58 | **532 (diverged)** |
| SE(c_shoot) at c = 0 | undefined | 0.121 | undefined |
| Minimum detectable \|c_shoot\| (80%) | undefined | **0.34** | undefined |
| **Decision** (rule: proceed if ≤ 0.15) | **Underpowered:** model degenerate | **Underpowered:** about 113 training games needed (has 22) | **Underpowered:** model degenerate |

**What "diverged" means.** The pilot T for Curry and Harden runs off to the
T → ∞ boundary, because the likelihood is best when the value difference is
ignored. The registered rule still gives "underpowered", but the cause is
model failure, not sample size: more games would not fix a negative slope.

**Synthetic recovery was not run.** The registration runs it only for
players who proceed, and none did. The code, including the immediate-scale
bias sensitivity, is ready.

## My read

The data contain a strong, clean pre-decision signal: openness at the catch
predicts shooting. But a league value model built from catch-and-shoot
outcomes does not register openness as value, because the shots that get
taken are already selected. A model of the form "shoot when the points say
so" therefore attributes almost all of the openness effect to the choice
rule, and none to value.

Getting further needs a way to value **the shots not taken**. A model of
P(make) for tightly guarded shots cannot be estimated from catch-and-shoots,
because almost none are taken tightly guarded. Two options:

- (a) borrow the defender effect from all jump shots, including off the
  dribble, where contested attempts are common (as in Cervone et al.); or
- (b) accept that this design cannot separate value from preference here.

Either is your decision. I have stopped.

---

# Stage 3a: detectors, values, power, synthetic (2026-10-13). STOPPED at the V_shoot calibration limit

*results.json key: `stage3a`*

There is **no real-player fit.** Power and synthetic recovery were **not
run**: the registration says V_shoot is not used for them until a
registered fix, and V_shoot failed its calibration limit.

**Where the rules are.**

- Registration part 1 (`d3460a7`): design, the four citations, the split,
  F1, R3 and its gate, the drive/pass detector and its gate, and possession
  points.
- Registration part 2 (`4a3a3d3`): the value models, choice model, pilot T,
  power rule and synthetic rule.
- Split: `b7b6dcb`.
- Test games were never read.

## Gates and checks

| Item | Result | Bar | Outcome |
|---|---|---|---|
| R3, close-range release (30 shots, labels first, `79679cf`) | **18 / 30** | 27 | **FAIL.** R3 rejected; R1 + R2 kept |
| Drive/pass detector (60 validation catches, labels first) | **53 / 60** (strata 18 / 16 / 19) | 54, none below 16 | **FAIL by one.** Primary model becomes **binary** (shoot now against continue) |
| Possession points (20 possessions vs PBP) | 19 / 20, then 20 / 20 after a code fix | check only | Fixed a missed-and-one case to match the registered rule |
| V_shoot calibration (1,231 validation league shots) | **ECE 0.0545** | 0.03 | **FAIL.** Power and synthetic not run |

**R3.**

- The 9 "not visible" shots were all correctly left unlocated.
- Most errors are timing offsets of 6–14 frames. The 4 ft radius made four
  previously located shots *later*.
- The existing R1 + R2 rule is also weak at close range: only 5 of the 10
  located close shots fell within 0.2 s, typically 0.3–0.56 s late.
- **Artefact:** some close-range "shoot now" catches may be timed as holds.

**Drive/pass errors.** Seven:

- two drives that reached almost exactly 10 ft;
- two lob passes the detector called holds;
- one drive to 7 ft it missed;
- one uncertain play;
- one (D32) where my label was wrong against the rule as registered. The
  registered drive rule lets the start be *any* frame 20+ ft out within
  4 s, and I labelled by the drive's actual start.

Labels were committed first, so the 53 stands. **Disclosure:** the drive and
pass flags were computed in the same batch build as the sampling proxies.
They were not read for these 60 until the labels were committed.

## V_shoot calibration

The model is logistic in distance, zone and openness. It was trained on
3,455 league train-game shoot-now attempts, and the validation make rate is
48.5%.

| Decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Predicted | .34 | .37 | .38 | .39 | .40 | .43 | .49 | .55 | .63 | .73 |
| Observed | .40 | .46 | .41 | .44 | .37 | .53 | .41 | .58 | .61 | .66 |

- **The registered limit cannot be reached at this sample size.** By
  simulation, a perfectly calibrated model with these predictions has a
  median ECE of 0.034 and passes the 0.03 limit only **29%** of the time.
  This is the same flaw the old project's v3b gate had.
- **The miscalibration is still real.** 0.0545 is beyond the perfect model's
  95th percentile of 0.049 (p = 0.013). The predictions are too compressed:
  low deciles are under-predicted and the top is over-predicted.

## Other value-model findings

1. **Continuation values barely move with the state.** On validation,
   V_continue has RMSE 1.1595 against 1.1607 for an intercept-only model, and
   the drive, pass and hold models are similar. The predicted range is only
   0.88–1.17 points.
   - In this data, the state at the catch says almost nothing about what the
     possession then scores.
   - So c_shoot would be identified almost entirely from variation in
     V_shoot.
2. **V_shoot is on a different scale from the continuation values.** League
   possession points after a shoot-now average **1.309**, while V_shoot
   averages **1.141**. The **0.168-point** gap is offensive rebounds and free
   throws, which V_shoot leaves out by design.
   - That is larger than the 0.15-point effect the power rule targets.
   - Left as is, it would push c_shoot toward a "shooter's premium" by about
     0.17 for everyone.
3. **The gated players' shoot-now samples are small** (train catches, of
   which shoot-now):
   - Curry: 629, of which 128;
   - LeBron: 740, of which 45;
   - Harden: 775, of which 71.
   - LeBron catches and shoots at once only 6% of the time, which will limit
     his power.
4. **Shrunk player offsets** are in `results.json`. Curry's above-break-three
   make-probability offset is +0.46 on the logit scale (53 attempts). Every
   other offset is small.
5. **Unknown actions (F1) excluded,** non-test catches:
   - Curry 3.8%, LeBron 5.3%, Harden 5.6%, league 4.6%;
   - plus drives that start inside 20 ft (choice-set rule): Curry 3,
     LeBron 11, Harden 6.

## What is ready, and what is blocked

**Ready:**

- detectors (with the stated weaknesses);
- the split;
- possession points;
- league-trained values and the shrunk offsets;
- the choice-model, Fisher and synthetic code. On made-up data, the Fisher
  standard errors match the spread of the maximum-likelihood estimates. One
  fit in 60 drifted toward the "constant action shares" limit (T → ∞), a
  weak-identification risk worth knowing about.

**Blocked:** power and synthetic. Both wait on your decisions below.

## Decisions for Colin

1. **The ECE limit.** Keep 0.03 and add validation shots (it needs roughly
   2.7× as many for a perfect model to pass 0.03 95% of the time), or replace
   it with a powered rule
   (for example, ECE no worse than a perfect model's 95th percentile).
2. **The V_shoot fix,** registered before it runs. For example, a richer
   distance and shot-clock form, plus recalibration fitted on cross-validated
   train predictions and scored once on validation.
3. **The 0.168-point scale mismatch.** Either value shooting by expected
   possession points (adding the rebound and free-throw continuation), or
   keep the immediate shot value and accept the offset.
4. **The binary primary model** stands unless you'd rather re-gate drive/pass
   with a fixed lob/handoff rule and a fresh held-out set.

---

# Decision after the second pass (recorded 2026-10-13, before any further work)

- **The registered label fell as "no variation".** That came from the
  0–10 ft band only: 14 catches, IQR of openness at catch 1.9 ft, against a
  3 ft bar.
- **Colin decided to proceed and build the dataset.** The decision was made
  after seeing the numbers, so it is a **post-hoc judgement about the test,
  not a reinterpretation of the result**.
  - The judgement is that criterion 1 was mis-specified for the rim band,
    where geometry bounds openness.
  - Criteria 2 and 3 passed: at 22–30 ft the gap was +41 pp, 95% CI
    [+26, +53], and 30% of catches ended in his shot within 4 s.
  - The result stays "no variation" as registered.
- **The registered label scheme is accepted,** including the residual
  "unlabelled (reason)" label.

---

# Stage 2: trusted catch detector and the full set (2026-10-13)

**Result: the detector passed its held-out gate, and the full set is built.**
Everything below is descriptive. There is no model, and nothing here is a
claim about what any player prefers.

**Commits.**

- Detector rules D1–D3 and the eye-check protocol, registered before
  anything ran: `25c4336`.
- Held-out labels, written by eye before D1–D3 had run on those games:
  `ba682ab`.
- Gate result: `b8d7e19`.
- Descriptive numbers: `3257818`, under `stage2_full_set` in `results.json`.

## Detector rules (D1–D3, on top of C1 + C1a)

- **D1, despike:** any ball coordinate more than 3 ft from its centred
  5-frame median is replaced by that median.
- **D2, hysteresis:**
  - **Acquire:** the ball within 3 ft of a player.
  - **Keep:** while the ball stays within 5 ft of the holder.
  - **Takeover:** another player takes the ball only after being the nearest,
    within 3 ft, for 6 consecutive frames.
- **D3, minimum duration:** a possession must last at least 5 frames
  (0.2 s).

## Held-out eye check: PASSED, 57/60

**Sample.** 60 candidate catches drawn from four GSW games not used before
(seed 4):

- 11.22 at DEN
- 11.30 at UTA
- 12.06 at BKN
- 01.08 at POR

**Candidate pool.** The 150 counted Curry catches from either earlier detector
(126 from C1 + C1a, 24 from the nearest-player rule only). From these, 20
were drawn per openness third (seed 5).

**How labelling worked.**

- The sheets were shuffled, and they showed no openness value and no D-detector
  output.
- Result: 46 real catches and 14 not-catches. The not-catches were:
  - 9 mid-dribble or holding-offset restarts;
  - 3 ball-position glitches;
  - 1 loose-ball scramble;
  - 1 screen tangle.

| | Correct | Bar |
|---|---|---|
| All | **57 / 60 (95%)** | ≥ 54 |
| Tight third | 17 / 20 | ≥ 16 |
| Middle third | 20 / 20 | ≥ 16 |
| Open third | 20 / 20 | ≥ 16 |

- **All 46 real catches were found.** This is recall relative to the pool
  only. Catches that both earlier detectors missed were never candidates.
- **The 3 errors are all false catches, all in the tight third:** a screen or
  handoff tangle, a dribble excursion to 4.5 ft, and a holding offset of
  3–7 ft.
- **What that means.** A small residue of false "catches" remains, and it
  sits where defenders are close. That pushes the tight third's shoot rates
  slightly down, because non-catches rarely end in a shot. On the held-out
  rate (3 in 20), roughly 15% of tight-third catches may not be real catches.
- **Error types seen and fixed** (glitches and dribble restarts are now
  rejected):
  - Interleaved and one-frame "teleport" ball positions appeared in 3 of 60
    candidates.

## Full set

**Games.** All archive games for GSW, CLE and HOU: 118 archives, 116 built.

- 01.14.2016.CLE.at.SAS: the upstream archive is empty (32 bytes).
- 01.23.2016.CHI.at.CLE: 466 play-by-play events but no tracking frames.

| | Curry | LeBron* | Harden* |
|---|---|---|---|
| Games with the player | 39 of 41 built (absent 12.30 at DAL, 12.31 at HOU) | 37 of 37 built (39 archives, 2 unusable) | 42 of 42 |
| Counted frontcourt catches | **1,119** | 1,327 | 1,378 |
| Catches per game: mean (sd), min–median–max | 28.7 (9.5), 0–29–54 | 35.9 (11.8), 0–36–53 | 32.8 (7.2), 16–33.5–50 |
| Source: teammate / self / opponent | 1,023 / 30 / 66 | 1,243 / 47 / 36 | 1,259 / 37 / 82 |
| Share with his shot within 1.5 s / within 4 s | 17.8% / 28.3% | 6.3% / 13.6% | 7.8% / 15.0% |
| FG attempts located / in play-by-play | 650 / 754 (86%) | 501 / 698 (72%) | 616 / 815 (76%) |
| Shots following a counted catch | 357 | 311 | 326 |

\* Reported, not gated.

**Openness at catch by distance band** (nearest opponent, ft; median
[IQR], n):

| Band | Curry | LeBron | Harden |
|---|---|---|---|
| 0–10 ft | 2.7 [1.9–4.4], 75 | 2.8 [2.0–4.4], 125 | 2.4 [1.8–4.4], 46 |
| 10–22 ft | 4.7 [3.1–7.5], 251 | 3.9 [2.6–6.2], 338 | 3.5 [2.3–5.3], 293 |
| 22–30 ft | 6.4 [4.6–8.6], 561 | 8.6 [6.2–11.0], 504 | 6.9 [4.9–9.3], 549 |
| 30–47 ft | 7.3 [5.9–10.3], 232 | 10.3 [8.6–12.5], 360 | 9.8 [7.6–12.2], 490 |

**22–30 ft: shot rates by openness third at the catch** (bootstrap 95%
intervals, seed 0):

| | Tight third | Middle third | Open third | Open − tight |
|---|---|---|---|---|
| **Curry** (n = 561; cuts 5.2 / 7.7 ft) | | | | |
| Shot within 1.5 s | 5.3% [2.1, 8.6] | 12.8% [8.6, 17.6] | **45.5%** [38.5, 52.4] | +40 pp [+32, +48] |
| Shot within 4 s | 14.4% [9.6, 19.8] | 24.1% [18.2, 30.5] | 57.8% [50.8, 64.7] | +43 pp [+35, +53] |
| **LeBron*** (n = 504; cuts 7.0 / 9.9 ft) | | | | |
| Shot within 1.5 s | 1.8% [0, 4.2] | 4.2% [1.2, 7.1] | 14.3% [9.5, 19.6] | +13 pp [+7, +19] |
| Shot within 4 s | 12.5% | 12.5% | 22.0% | +10 pp [+2, +19] |
| **Harden*** (n = 549; cuts 5.7 / 8.6 ft) | | | | |
| Shot within 1.5 s | 4.4% [1.6, 7.7] | 3.8% [1.1, 6.6] | 32.2% [25.7, 39.3] | +28 pp [+20, +36] |
| Shot within 4 s | 14.8% | 9.3% | 40.4% | +26 pp [+16, +35] |

The bootstrap intervals for the open − tight gaps resample catches with the
tercile cuts recomputed. The per-third intervals use fixed cuts.

**Time from catch to shot,** for shots following a counted catch:

| | Median [IQR] | Within 1.5 s |
|---|---|---|
| Curry | 1.24 s [0.80–2.68] | 56% |
| LeBron | 3.06 s [1.42–6.29] | 27% |
| Harden | 2.63 s [1.16–5.16] | 33% |

Curry's distribution peaks sharply in the 0.5–1.0 s bin (141 of 357 shots,
the catch-and-shoot). LeBron's and Harden's have long tails out to 6–8 s,
which are drives after a catch.

**Openness at catch against openness at release** (same shots):

| | At catch (median) | At release (median) | Correlation | Release tighter than catch |
|---|---|---|---|---|
| Curry | 7.7 ft | 4.0 ft | 0.49 | 86% |
| LeBron | 7.3 ft | 3.6 ft | 0.45 | 84% |
| Harden | 8.1 ft | 3.4 ft | 0.27 | 86% |

At 22–30 ft, Curry's figures are 8.3 ft at the catch and 4.1 ft at the
release. Defenders close by about 4 ft between catch and shot. So the old
data's at-release distance is a different, later quantity, only moderately
related to openness at the catch.

## Things that look like detector or data artefacts

1. **The shot clock is null for whole games.** This happens in
   01.22.2016.IND.at.GSW, 11.02.2015.CLE.at.PHI and 01.08.2016.CLE.at.MIN,
   and for 29% of catches in 11.11.2015.GSW.at.MEM.
   - The registered "shot clock running" rule excludes those catches, which
     is why Curry and LeBron each have a 0-catch game.
   - I did not change the rule after seeing this. About 1 Curry game and 2
     LeBron games are effectively lost.
2. **Residual false catches cluster in the tight third** (3 of 20 held out,
   none elsewhere). Tight-third rates are therefore probably slightly
   understated, and the open − tight gaps slightly overstated. The size of
   this bias is not measured beyond the held-out rate.
3. **Shot location is weaker for drivers.** 72% of LeBron's FG attempts are
   located, against 86% for Curry, because close-range releases are the
   rule's known weak spot. LeBron's and Harden's shoot rates are therefore
   understated, most likely their slower drives.
4. **Curry's catches by quarter** (per game, Q1–Q4) run 9.4 / 5.4 / 10.2 /
   3.4. That fits his usual rest pattern (2015-16 fourth-quarter blowouts),
   not a detector fault, but it is uneven. LeBron and Harden are flatter.
5. **Coverage:**
   - frames per game range from 50.7k to 86.6k (median 69.6k), and the low
     ones are partial games, e.g. 01.18.2016.GSW.at.CLE at 50.7k;
   - dropped malformed moments range from 75 to 1,796 per game.
6. **No sign of other artefacts:**
   - no catch-to-shot times under 0.3 s for Curry (1 each for LeBron and
     Harden);
   - 2–3% of catches end within 0.3 s;
   - under 1.2% of catches sit at 45–47 ft (the frontcourt edge);
   - 1–3% of catches have the nearest defender within 1 ft.

## Data scope note

"LeBron's and Harden's games run the same way" was read as all CLE and HOU
games in the archive. The four games shared between these teams and GSW
were built once.

Curry's 39 games include all the games used earlier: the 10 from pass 2 and
the 4 held-out games. So the held-out games appear in the full set as well;
they were not used for tuning.

## Time

Stage 2 ran from 12:35 to about 13:15, well inside the 3-hour box.

- The full build takes about 4 minutes on one core. Each extracted JSON is
  deleted after loading.
- The archives (665 MB) stay in `~/Documents/nba-tracking/raw`.

---

# Second pass: 10 Curry games (2026-10-13)

**Question.** The 2015-16 SportVU logs record where the defenders are *at the
catch*, before the player decides whether to shoot. Do they hold enough of that
pre-decision variation to justify a real project?

This is a feasibility check only. There is no cost model and no fitting, and it
makes no claim about any player.

**Registered label: "no variation".**

- Under the decision rule, criterion 1 is checked first, and it fails in the
  0–10 ft band.
- The other two criteria pass, and criterion 2 passes by a wide margin.
- So the label is correct by the rule, but it does not describe what the data
  shows. Details are below; the decision is yours. I have stopped as asked.

**Commits.**

- Registration `4a18241`, written before the 8 new games were downloaded.
- C1a `aefe72f`: a refinement, recorded before any new game was scored. See
  "Catch rule" below.
- Eye-check verdicts and gate code `e74a8b3`/`288db65`.
- The gate ran once, at `288db65`.
- `results.json` holds `pass2_10_curry_games` (this pass) and
  `pass1_5_games` (the first pass, unchanged).

## Gate (Curry, 10 earliest GSW games in the archive, 330 counted catches)

| Criterion | Result | Bar | Holds? |
|---|---|---|---|
| **1. Variation:** IQR of openness at catch, by band (n) | 0–10 ft: **1.9 ft** (14) · 10–22: 4.8 ft (72) · 22+: 4.7 ft (244) | ≥ 3 ft in every band with ≥ 10 catches | **no**, 0–10 band only |
| **2. Prediction,** 22–30 ft (n = 182): P(shot within 1.5 s), bottom → top tercile | **3.3% → 44.3%** (61 catches each; cuts 5.3 / 8.1 ft) | gap ≥ 10 pp, 95% CI excludes 0 | **yes:** +41 pp, CI [+26, +53] |
| **3. A choice to model:** share with his shot within 4 s | 30.0% | 20–80% | **yes** |
| Catches | 330 (33 per game) | ≥ 60 | yes |

**Reading it.**

- **The one failing band is the rim.** Within 10 ft, someone is almost always
  within 2–4 ft (median 2.6 ft), so openness there barely varies. With only 14
  catches it is also the smallest band.
- **The bands where a shoot-or-not choice happens vary,** with an IQR of
  4.7–4.8 ft.
- **Openness at the catch strongly predicts an immediate shot.** In the
  22–30 ft band, Curry shot within 1.5 s on 44% of his most open catches and
  on 3% of his most tightly guarded.
- **Catch and release are different measures.** On the 110 shots that
  followed a counted catch, the median defender distance was 8.6 ft at the
  catch and 4.4 ft at the release, with a correlation of 0.40.
- **Treat the size of the gap with caution.** The eye check found 3 of 10
  catches wrong, and I have not checked whether those errors fall unevenly
  across the openness terciles. This is a description, not a model and not a
  claim about Curry's preferences.
- **Why the registered order produced this label.** Criterion 1, as
  registered in the first pass, required every band with ≥ 10 catches to have
  an IQR of at least 3 ft. The rim band reached 10 catches only with the
  larger sample. Under the decision rule, "no variation" is checked before
  "pass", so the label follows from the rule as written. I have not
  relabelled it.

**Shot location (Curry, 10 games).** 193 of 221 FG attempts were located
(87%).

## Catch rule: before and after, and the eye check

**C1 as registered.** Under "sticky" control, the holder keeps the ball while
it is within 3 ft of him, whoever is nearer.

On Curry's two first-pass games, this cut opponent-sourced catches only from
22 to 18. Tracing the remaining 18 showed two groups:

- **About 11 were real passes,** where the ball skimmed within 3 ft of a
  defender in flight. The catch is real; only the source label was wrong.
- **About 5 were still your dribble case.** The ball strayed 4–7 ft from Curry
  on a dribble, and a defender got 1–13 frames of "control".

**C1a, added before any new game was scored.** A brief opponent touch
(12 frames, 0.48 s, or less) between two of P's spells less than 1 s apart
merges them into one possession. When a catch's source is computed, brief
touches are skipped.

**Accepted cost.** A real deflection off P that comes back to him within 1 s
no longer creates a catch.

**Before and after, Curry, the two first-pass games** (report only):

| | Spells | Valid catches | Counted | Source | Shots linked |
|---|---|---|---|---|---|
| Before (nearest player) | 347 | 237 | 83 | teammate 56, opponent 22, self 5 | 25 |
| After (C1 + C1a) | 261 | 205 | 76 | teammate 69, opponent 1, self 6 | 25 |

Across all 10 games, 37 catches were relabelled from "opponent" to
"teammate" because the pass had skimmed a defender. Nine opponent-sourced
catches remain.

**Eye check of the fixed rule: 7 of 10 correct** (10 new-game catches, seed 3,
in `figures/eye_check_c1/`). The registered stop line was below 7, so the gate
ran. The three misses are new error types, not the dribble flicker:

1. **Holding offset.** Curry had held the ball for more than 2 s, but the
   ball was tracked 3–5 ft from his centre. The "catch" is the ball crossing
   the 3 ft line mid-possession.
2. **Tracking glitch.** In a one-frame glitch, the ball's height jumped
   15 → 3.4 → 15 ft.
3. **Teammate's rebound.** A rebound coming down passed within 2.2 ft of
   Curry at 8 ft, and Ezeli took it.

A next step, if you want one, would be to require a catch to hold for a few
frames and to ignore single-frame height jumps. Both are new rules and would
need registering. I have not made them.

## LeBron and Harden (reported, not gated; first-pass games with the fixed rule)

| | LeBron (2 games) | Harden (1 game) |
|---|---|---|
| Counted catches | 66 | 36 |
| IQR of openness, ft: 0–10 / 10–22 / 22+ (n) | 2.5 (9) / 5.7 (17) / 3.6 (40) | 0 (1) / 1.8 (6) / 5.4 (29) |
| 22–30 ft: P(cs), bottom → top tercile | 0% → 20% (n = 30), gap +20 pp, CI [0, +50] | 0% → 50% (n = 13), CI [0, +100] |
| Share with his shot within 4 s | 21.2% | 16.7% |

Both point the same way as Curry's result, but they are far too small to say
more.

## Second-pass data quirks

- **The Warriors' 30 Oct 2015 game at HOU is missing from the archive.**
  "10 earliest in the archive" therefore skips it.
- **The BKN game went to overtime,** giving 79k frames. Frames dropped as
  malformed ranged from 389 to 1,202 per game.
- **The three catch-error types above:** holding offset, single-frame ball
  height glitches, and balls passing a player on the way to a teammate's
  rebound.

## Time

The second pass ran from 12:25 to about 12:35, well inside the 2-hour box.
The build over 13 games took 38 s and the gate about 1 s. Nothing heavier was
run.

---

# First pass: 5 games (kept as written)

**Question.** The 2015-16 SportVU logs record where the defenders are *at the
catch*, before the player decides whether to shoot. Do they hold enough of that
pre-decision variation to justify a real project?

This is a feasibility check only. There is no cost model and no fitting, and it
makes no claim about any player.

- **Repo:** `~/Documents/nba-catch-decisions` (local only, no remote).
- **Pre-registration:** `a191b73`.
- **Rule changes:** R1 `b198761` and R2 `ea26df7`, both made before any gate
  number existed.
- **Gate code:** `f773249`; post-hoc additions at `c8161d5`.

## Verdict (first pass)

**FAIL by the pre-registered rule, but the failure is inconclusive. My
recommendation is "need more games": about 10 Curry games in total (8 more),
after one definition fix.** Not "go", and not "not worth it".

- **Curry** (83 frontcourt catches in 2 games) passes criteria 1 (variation)
  and 3 (a choice to model). He fails criterion 2 (does openness predict the
  shot?).
  - Catch-and-shoot rate is 4.5% in the tightest-guarded third of his 22+ ft
    catches and 14.3% in the most open third.
  - That is a gap of +9.7 pp, just under the 10 pp bar. The 95% interval runs
    from −9 to +29 pp.
  - The test could not tell "no effect" from a large effect.
- **The variation the old project lacked is there.**
  - On the shots that followed a counted catch, the nearest defender was a
    median 7.6 ft away at the catch and 3.9 ft at the release (Curry).
  - The correlation between the two is 0.53. Defender distance at the catch
    is a different, earlier quantity from distance at the shot.
- **Why criterion 2 failed:**
  - Curry catch-and-shoots on only 8% of his 22+ ft catches, so each tercile
    holds about 21 catches and 1–3 shots.
  - A post-hoc simulation, not part of the gate: if the true gap were 15 pp,
    criterion 2 would pass 80% of the time with about 240 catches at 22+ ft.
    That is about 8 Curry games, or 4 games if the true gap were 20 pp.
  - 41 GSW games are in the public release, so the data exists.
- **Under my pre-registered labels** this counts as "no variation", because
  criterion 2 failed with at least 60 catches. That label overstates it.
  - The variation exists (criterion 1).
  - What's missing is evidence that it predicts the action, and two games
    can't supply that evidence either way.

## Does the join work? Yes

- **Join rate:** 2,372 of 2,427 PBP rows (97.7%) in the five games match an
  event with tracking frames, as do 868 of 876 FG attempts.
- **20 random events (seed 0):**
  - The period matches in 20/20.
  - The PBP clock falls inside the event's tracking window (±2 s) in 20/20.
  - By eye (`figures/join20_sheet.png`), 13 stills match their description.
    3 have nothing to check (substitutions, a timeout). 4 are ambiguous because
    the ball has already moved on by the PBP clock (rebounds, a turnover).
  - None contradicts its description.

## Does shot location work? Yes, with a known lag and a close-range weakness

| | Located | Rate |
|---|---|---|
| All FG attempts (joined) | 744 / 868 | 86% |
| Curry | 48 / 53 | 91% |
| LeBron | 31 / 35 | 89% |
| Harden | 20 / 21 | 95% |

- **Two rule changes were needed** before any gate number was computed. Both
  are recorded in the README.
  - **R1.** An event's frames start about 20 s before its PBP row, so "the
    first time the ball reaches a rim" usually found the *previous* shot.
  - **R2.** Event windows are not reliably bounded: some contain the next shot,
    and some end before their own. The search is now anchored on the PBP clock.
    The PBP clock trails the release by a median of 2.7 s (IQR 2.2–3.3 s).
- **Eye check, 10 target shots (seed 1), `figures/eye_check/`: 8 of 10
  correct within 0.2 s.**
  - On jump shots the marked frame sits about 0.1 s after the ball leaves the
    hands, because it is the last frame with the ball within 3 ft.
  - Both misses are close range: a 4 ft floater and a running layup. The
    shooter moves with the ball there, and top-down data can't pin the release
    (probably 0.2–0.4 s off).
- **The pre-registered check "shooter is the nearest player at release" was
  ill-posed.** It held for 53% of located shots and 3/6 in the 20-event
  sample.
  - At the marked frame the ball is already about 2.6 ft out, and a
    contesting defender is often nearer.
  - 0.2 s earlier, the shooter is nearest in 94% of cases.

## Gate numbers

Counted catches are frontcourt catches with the shot clock running. Openness at
the catch is the nearest opponent's distance to the catcher.

| | Curry | LeBron | Harden |
|---|---|---|---|
| Games | 2 | 2 | 1 |
| Counted catches (per game) | **83** (41.5) | **70** (35) | 40 (40) |
| **1. IQR of openness, ft:** 0–10 / 10–22 / 22+ (n) | 4.4 (5)† / 3.2 (14) / 5.0 (64) | **2.6 (11)** / 7.3 (19) / 3.6 (40) | 1.2 (2)† / 3.5 (8)† / 6.2 (30) |
| Criterion 1 | pass | **fail** (0–10 band) | pass |
| **2. P(catch-and-shoot), 22+:** bottom → top tercile | 4.5% → 14.3% | 0% → 7.7% | 10% → 40% |
| Gap [95% CI] | +9.7 pp [−9, +29] | +7.7 pp [0, +27] | +30 pp [−9, +67] |
| Criterion 2 | **fail** | **fail** | **fail** |
| **3. Share with his shot within 4 s** | 20.5% | 18.6% | 15.0% |
| Criterion 3 | pass (barely) | **fail** | **fail** |
| At least 60 catches | yes | yes | no (1 game) |

† Fewer than 10 catches, so not scored, as pre-registered.

- **Other numbers at the catch (Curry):**
  - median openness 6.5 ft (IQR 3.5–8.4);
  - nearest opponent to the rim 7.3 ft;
  - shot clock 15.9 s;
  - 1.3 s from the catch to his next action.
- **Shots not counted as "shot after a catch":**
  - FG attempts with no located release, or not linked to a spell: Curry
    6/53, LeBron 8/35, Harden 3/21.
  - Only about half of each player's shots follow a *counted* catch: Curry
    25, LeBron 18, Harden 9. The rest come after backcourt or transition
    possessions, or after catches excluded by the pre-window rule.

## Example plays (catch and release marked)

These are in `figures/examples/`. Each has a GIF drawn with the upstream
`Event` animation class and a sheet: zoomed frames around the catch and the
release, plus a trace of ball height and ball-to-player distance.

| Play | Catch | Openness at catch → release | Catch to shot | Check |
|---|---|---|---|---|
| LeBron, CLE@MEM #93 | 25.5 ft, from a pass | 8.7 → 3.1 ft | 2.1 s | catch ✓ release ✓ |
| LeBron, CLE@CHI #299 | 29.7 ft, from a pass | 13.3 → 6.0 ft | 1.9 s | ✓ ✓ |
| Harden, DEN@HOU #251 | 27.6 ft, from a pass | 11.9 → 3.1 ft | 1.1 s | ✓ ✓ |
| Curry, NOP@GSW #14 | 1.7 ft, pass at the rim | 6.7 → 3.3 ft | 0.6 s | ✓, layup release ±0.2 s |
| Curry, GSW@NOP #208 | 32 ft, source "opponent" | 0.1 → 3.9 ft | 2.1 s | **✗ spurious catch:** he had been dribbling for over 1 s; a defender was briefly nearer the ball |

## Data quirks found

1. **The spurious "opponent" catches are the main fix needed before
   scaling.**
   - The control rule ("nearest player within 3 ft") flips to a defender for
     a few frames during tight on-ball defence. Ending such a flip restarts
     the possession as a new "catch".
   - 39 of 193 counted catches (20%) are "from an opponent", with a median
     opponent "possession" of 0.16 s. Most of these are not real.
   - Post-hoc sensitivity, keeping only catches from a teammate's pass:
     - share with a shot within 4 s rises to 27% (Curry), 22% (LeBron) and
       19% (Harden);
     - criterion 2 is still inconclusive (Curry +6 pp [−19, +38]).
2. **The 22+ band mixes shot chances with catches that start the offence.** A
   third of its catches are beyond 30 ft.
   - Post-hoc, restricting criterion 2 to 22–30 ft gives Curry +20 pp
     [−3, +43] and LeBron +20 pp [0, +50].
   - Both have larger point estimates, and both are still inconclusive.
3. **Event frame windows overlap and are not tied to their event** (see R1 and
   R2). Frames have to be deduplicated across events. After that, coverage is
   about 69–71k frames per game, against 72k for 48 minutes.
4. **Malformed frames:** 177–1,548 moments per game have fewer or more than 10
   players, or no ball row. They are dropped; the HOU game loses the most,
   about 2%.
5. **Ball height sometimes flatlines**, apparently interpolated. In game 003
   event 339, z sits at 10.0 ft for 0.45 s mid-shot.
6. **Deduplicating on (quarter, game clock) collapses stopped-clock periods**
   to one frame, which makes free throws invisible. That is harmless here,
   because only live-ball catches count.
7. **The PBP has no shot coordinates**, and shooting fouls with no FG attempt
   don't appear as shots. Such catches count as "no shot".
8. **Upstream animation script:** it crashes on current matplotlib
   (`table.properties()['child_artists']`). It is shimmed in `render.py`, and
   upstream is untouched.
9. **Listing:** 636 entries are 626 games plus 10 duplicates with malformed
   names, all on 12.05.2015.

## Recommendation

**Need more games: about 10 Curry games (8 more), as a second pre-registered
feasibility pass, not a modelling project yet.**

- **Before it, fix and pre-register the catch rule.** Either require the
  previous possession to be a teammate's (a pass), or require any change of
  control to last at least about 0.5 s. Also consider a 22–30 ft band for
  criterion 2.
- **These were chosen after seeing the numbers, so they belong in a new
  pre-registration.** They should not be re-scored on these five games.
- **Cost:** about 6 MB per game to download, and the pipeline runs in about
  15 s per 5 games.
- **If ~10 Curry games still give an interval spanning zero,** that is a real
  "no usable signal" and the project should stop.
- **LeBron and Harden fail criterion 3 here.** Fewer than 20% of their counted
  catches end in their own shot within 4 s, so shooting right after the catch
  is the rarer branch for them. That is worth knowing before choosing them as
  subjects.

## Time and box

- **Wall clock:** 11:59 to 12:25, about 26 minutes, well inside the
  3 h box.
- **Compute:**
  - building catches for all five games: 15 s;
  - the gate with its bootstrap: under 1 min;
  - the post-hoc power simulation: about 1.5 min, single core.
- **Not run:** anything heavier.

## Reproduce

```bash
cd ~/Documents/nba-catch-decisions && uv sync
uv run python -I scripts/extract.py ~/Documents/nba-tracking/raw ~/Documents/nba-tracking/json
uv run python -I scripts/build.py && uv run python -I scripts/join_check.py && uv run python -I scripts/gate.py
```

Raw data stays in `~/Documents/nba-tracking/` and is never committed. Its
SHA-256s are listed in the repo README, and the source is a public scrape with
no licence.
