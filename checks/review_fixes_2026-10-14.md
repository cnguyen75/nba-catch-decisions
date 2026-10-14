# Review fixes applied to feasibility.md (2026-10-14)

The record file is outside this repo, at
`~/Personal/site-handoff/tracks/nba-catch-decisions/feasibility.md`. This note
records what was changed and the checks behind it. Nothing was added to
results.json.

**The review itself was not available.** The file
`review-2026-10-13.md` did not exist at the stated path. The fixes follow
the brief's statement of the review's findings, and each number was
re-computed here where the stored data allowed.

| # | Fix | My check |
|---|---|---|
| 1 | Attempt-2 level and gradient limits underpowered (gate errors 3, 4) | Level SE 0.00648 at n = 5,546, so the limit is 1.54 SE. Gradient SE 0.0243 (n = 2,651 vs 474), so the limit is 1.23 SE. P(a perfect model fails ≥ 1) = 0.31. |
| 2 | 5b 0.03 recovery limit unreachable (gate error five) | Re-computed from `checks/*synth*.json`, nine settings: slope −0.71 to −1.02, correlation −0.986 to −0.997, residual SD 0.0065–0.0106. SE(ρ) achieved 0.06–0.16. |
| 3 | 5c median filtered against pooled | Pooled league: Stage 4 R_b −7.12 (so 7.1 s/ft); 5a motion 7.0. |
| 4 | Stage 6 hot-hand reading withdrawn; Curry first-shot result is 1 of 12 contrasts | Controls confirmed in `scripts/s11_b.py` `mfeats()`. 12 = 3 players × 2 contrasts × 2 outcomes (D10). |
| 5 | Site paragraph corrected | The old paragraph is kept, marked superseded. |
| 6 | Review row added to the chronological table | |
