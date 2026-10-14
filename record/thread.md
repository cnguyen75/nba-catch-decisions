# How the two NBA pages tell one story (for the site build)

## The thread

Inverse optimization rests on one idea. If a choice solves a problem, its
first-order condition reveals the cost you can't see. Both NBA pages apply
that idea to shot selection; together they show what the condition can and
can't deliver.

**The 2014-15 page: nothing for the condition to bite on.** The shot logs
give the closest defender's distance at the shot. The page treats it as
context the shooter takes as given, but it is an outcome of shooting. In the
2015-16 tracking, defenders close about 4 ft between catch and release on
the three players' shots. A condition taken with respect to a variable the
choice itself moves has nothing fixed to bite on. So the recovered costs got
defender distance backwards, and the page ends negative.

**The 2015-16 page: the one thing the condition can deliver.** Tracking
measures space at the catch, before the decision. The shoot-now choice then
yields a marginal rate of substitution, the exchange rate: a foot of space
is worth about seven seconds of shot clock to the league. It is about nine
when trailing by five or more. A ratio of
marginal effects is what a first-order condition gives, and all it gives:
the level of the hidden cost cancels out of the ratio.

**Release timing (Stage 10): where the condition can be tested directly.**
An additive hidden shot quality drops out of the derivative, so a timing
condition is estimable from taken shots.

- **The answer is a corner, not a trade-off.** At a fast closeout, another
  tenth of a second costs about two points of make probability and buys
  about half a point (interval −0.2 to +1.3).
- **Shooters release at a mechanical floor** (lower for Curry and Klay
  Thompson), so there is no hidden timing cost to reveal.

**What neither page can deliver: the value of the shot not taken.** Both
pages see only the shots that were taken. Whether players pass up shots
because they see something the tracking can't is a counterfactual question.
It needs a selection model and a strong instrument, not a first-order
condition. Three instrument sets were too weak: the record shows the precision any
instrument would need (SE on rho of about 0.02) against what the three sets
achieved (0.06-0.16).

## Cross-links (two sentences each)

**On the 2014-15 page:**

> A follow-up uses 2015-16 player tracking to measure a shooter's space at
> the catch, before the decision, rather than at the shot. That turns the
> question into one a first-order condition can answer: what a foot of
> space is worth in shot-clock seconds.

**On the 2015-16 page:**

> An earlier attempt, on 2014-15 shot logs, tried to recover players' costs
> from defender distance at the shot and failed, because that distance is
> partly an outcome of the shot itself. This page measures space at the
> catch instead, which is why its exchange rate can be estimated where the
> earlier cost could not.

## Sources

- **2014-15:** `../nba-shot-decisions/dossier.md` (v2, v3c).
- **2015-16:** `feasibility.md`:
  - the 4 ft closing: "Full set", openness at catch against release;
  - the exchange rate: Stages 4, 5a, 8 and 12;
  - release timing: Stage 10;
  - instruments: 5b, 5b strategy 2 and Stage 6.
