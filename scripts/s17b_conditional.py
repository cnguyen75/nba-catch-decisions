"""Stage 11 addendum (post hoc, requested 2026-10-14; not registered): P(receiver is the most open candidate | receiver is
a candidate), with the like-for-like baseline mean(1/n_candidates) over the same passes. Rebuilds Stage 11's per-pass table
with its own build() (no model is fitted) and bootstraps games exactly as Stage 11 did (1,000, seed 0).
Writes out/s11/stage11_conditional.json."""

import json
from pathlib import Path
import sys

import numpy as np


sys.path.insert(0, str(Path(__file__).parent))
from s4_data import GATED  # noqa: E402
from s17_pass_open_shooter import NB, OUT, build, shooters  # noqa: E402


def summ(x):
    c = x[x.recv_cand.astype(bool)]
    return {
        "p_most_open_given_cand": c.is_mo.mean(),
        "baseline_given_cand": c.base.mean(),
        "n_recv_cand": len(c),
    }


def main():
    shoot, _, _ = shooters()
    d, _, _ = build(shoot)
    groups = {"League": ~d.passer.isin(GATED), **{n: d.passer == p for p, n in GATED.items()}}
    games = np.array(sorted(d.game.unique()))
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in games}
    rng = np.random.default_rng(0)
    point = {k: summ(d[m]) for k, m in groups.items()}
    bs = {k: [] for k in groups}
    diff = []
    for _ in range(NB):
        ix = np.concatenate([gi[g] for g in rng.choice(games, len(games))])
        db = d.iloc[ix]
        sv = {k: summ(db[groups[k].to_numpy()[ix]]) for k in groups}
        for k in groups:
            bs[k].append(
                [
                    sv[k]["p_most_open_given_cand"],
                    sv[k]["baseline_given_cand"],
                    sv[k]["p_most_open_given_cand"] - sv[k]["baseline_given_cand"],
                ]
            )
        diff.append(sv["LeBron"]["p_most_open_given_cand"] - sv["League"]["p_most_open_given_cand"])
    ci = lambda a: [round(float(v), 4) for v in np.nanquantile(a, [0.025, 0.975])]
    res = {"post_hoc": True, "n_passes_included": int(len(d)), "groups": {}}
    for k in groups:
        a = np.array(bs[k])
        p = point[k]
        res["groups"][k] = {
            "n_recv_cand": int(p["n_recv_cand"]),
            "p_most_open_given_cand": [round(p["p_most_open_given_cand"], 4), ci(a[:, 0])],
            "baseline_given_cand": [round(p["baseline_given_cand"], 4), ci(a[:, 1])],
            "minus_baseline": [
                round(p["p_most_open_given_cand"] - p["baseline_given_cand"], 4),
                ci(a[:, 2]),
            ],
        }
    res["lebron_minus_league_given_cand"] = [
        round(
            point["LeBron"]["p_most_open_given_cand"] - point["League"]["p_most_open_given_cand"], 4
        ),
        ci(diff),
    ]
    (OUT / "stage11_conditional.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
