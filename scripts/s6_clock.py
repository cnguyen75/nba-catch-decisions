"""Stage 4 (registered ea99d0c): openness priced in shot-clock seconds. Power first, then gradients, exchange rate,
Skinner's test. Writes out/s4/stage4.json."""

from collections.abc import Callable
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit


sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import X_full, logit_fit, ridge  # noqa: E402
from s4_data import GATED, S4  # noqa: E402


NB = 1000
BINS = [0, 4, 8, 12, 16, 20, 24.01]
NAMES = ["intercept", "shot_clock", "open", "d10", "d10sq", "ab3", "corner3", "best_tm"]


def cov(d: pd.DataFrame) -> np.ndarray:
    dd = d.d_basket.to_numpy(float) / 10
    return np.column_stack(
        [
            np.ones(len(d)),
            d.shot_clock.to_numpy(float),
            d.open_catch.clip(upper=15).to_numpy(float),
            dd,
            dd**2,
            (d.zone == "above_break3").to_numpy(float),
            (d.zone == "corner3").to_numpy(float),
            d.best_tm_open.clip(upper=20).to_numpy(float),
        ]
    )


def ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def unit(d: pd.DataFrame) -> pd.DataFrame:
    return d[
        (d.d_basket >= 16)
        & (d.d_basket <= 30)
        & d.shot_clock.notna()
        & d.action.isin(["shoot", "continue"])
    ].copy()


def boot_games(d: pd.DataFrame, fn: Callable[[pd.DataFrame], Any], seed: int) -> list[Any]:
    games = d.game.unique()
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in games}
    r = np.random.default_rng(seed)
    return [
        fn(d.iloc[np.concatenate([gi[g] for g in r.choice(games, len(games))])]) for _ in range(NB)
    ]


def ci(x: np.ndarray) -> list[float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return [round(float(v), 4) for v in np.quantile(x, [0.025, 0.975])]


def main() -> None:
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    lt_all = vs[~vs.pid.isin(GATED) & (vs.split == "train")]
    c_ = lt_all[lt_all.action == "continue"]
    b_naive = ridge(X_full(c_), c_.poss_points.to_numpy(float))
    league = unit(lt_all)
    league["V_continue"] = X_full(league) @ b_naive
    league["gap"] = league.V_shoot - league.V_continue
    league["y"] = (league.action == "shoot").astype(float)
    pv = pd.read_csv(S4 / "values.csv", dtype={"game": str})
    players = {}
    for pid, name in GATED.items():
        d = unit(pv[pv.pid == pid])
        d["gap"] = d.V_shoot - d.V_cont_naive
        d["y"] = (d.action == "shoot").astype(float)
        players[name] = d
    groups = {"League": league, **players}
    out = {"n": {k: [int(len(d)), int(d.y.sum())] for k, d in groups.items()}}

    # ---- 5. power first
    pw = {}
    for name, d in groups.items():
        X = cov(d)
        b = logit_fit(X, d.y.to_numpy())
        p = expit(X @ b)
        C = np.linalg.inv((X * (p * (1 - p))[:, None]).T @ X)
        bc, bo = b[1], b[2]
        vc, vo, cco = C[1, 1], C[2, 2], C[1, 2]
        R = bo / bc
        varR = vo / bc**2 + (bo**2 / bc**4) * vc - 2 * (bo / bc**3) * cco
        pw[name] = {
            "beta_clock": round(float(bc), 4),
            "se_beta_clock": round(float(np.sqrt(vc)), 4),
            "beta_open": round(float(bo), 4),
            "se_beta_open": round(float(np.sqrt(vo)), 4),
            "R_b": round(float(R), 3),
            "se_R_b_delta": round(float(np.sqrt(max(varR, 0))), 3),
            "smallest_detectable_R_difference_80pct": round(float(2.8 * np.sqrt(max(varR, 0))), 3),
        }
    out["power"] = pw
    print("POWER", json.dumps(pw, indent=1))

    # ---- 1-3 point estimates and bootstrap
    def meas(d: pd.DataFrame) -> tuple[float, float]:
        g = ols(cov(d), d.gap.to_numpy())
        return g[1], g[2]

    def beh(d: pd.DataFrame) -> tuple[float, float]:
        b = logit_fit(cov(d), d.y.to_numpy())
        return b[1], b[2]

    gm = meas(league)
    gm_bs = np.array(boot_games(league, meas, 0))
    out["measured_league"] = {
        "g_clock_pts_per_s": [round(float(gm[0]), 5), ci(gm_bs[:, 0])],
        "g_open_pts_per_ft": [round(float(gm[1]), 5), ci(gm_bs[:, 1])],
        "R_m_s_per_ft": [round(float(gm[1] / gm[0]), 3), ci(gm_bs[:, 1] / gm_bs[:, 0])],
    }
    out["groups"] = {}
    for k, (name, d) in enumerate(groups.items()):
        bb = beh(d)
        bs = np.array(boot_games(d, beh, 100 + k))
        Rb = bs[:, 1] / bs[:, 0]
        implied = bs[:, 1] * gm_bs[:, 0] / bs[:, 0]
        clock_ci = ci(bs[:, 0])
        r = {
            "beta_clock_logodds_per_s": [round(float(bb[0]), 4), clock_ci],
            "beta_open_logodds_per_ft": [round(float(bb[1]), 4), ci(bs[:, 1])],
            "R_b_s_per_ft": [round(float(bb[1] / bb[0]), 3), ci(Rb)],
            "R_m_s_per_ft": out["measured_league"]["R_m_s_per_ft"],
            "T_clock_points": [round(float(gm[0] / bb[0]), 4), ci(gm_bs[:, 0] / bs[:, 0])],
            "implied_value_open_pts_per_ft": [round(float(bb[1] * gm[0] / bb[0]), 4), ci(implied)],
            "measured_value_open_pts_per_ft": out["measured_league"]["g_open_pts_per_ft"],
            "implied_over_measured": [
                round(float((bb[1] * gm[0] / bb[0]) / gm[1]), 2),
                ci(implied / gm_bs[:, 1]),
            ],
            "individually_resolved": bool(
                name == "League" or not (clock_ci[0] <= 0 <= clock_ci[1])
            ),
        }

        # ---- 4. Skinner's test
        def skin(dd: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
            b = pd.cut(dd.shot_clock, BINS, right=False)
            t = dd.groupby(b, observed=False).agg(
                obs=("y", "mean"), imp=("gap", lambda x: float((x > 0).mean())), n=("y", "size")
            )
            return (t.obs - t.imp).to_numpy(), t

        diff, tab = skin(d)
        sb = np.array([skin(x)[0] for x in boot_games(d, lambda x: x, 200 + k)])
        r["skinner"] = {
            str(iv): {
                "n": int(row.n),
                "observed": round(float(row.obs), 3) if row.n else None,
                "implied_maximiser": round(float(row.imp), 3) if row.n else None,
                "obs_minus_implied": round(float(diff[j]), 3) if row.n else None,
                "ci95": ci(sb[:, j]) if row.n else None,
            }
            for j, (iv, row) in enumerate(tab.iterrows())
        }
        out["groups"][name] = r
        print(name, json.dumps({kk: vv for kk, vv in r.items() if kk != "skinner"}))
        for iv, s in r["skinner"].items():
            print("   ", iv, s)
    (S4 / "stage4.json").write_text(json.dumps(out, indent=1, default=float))
    print("MEASURED", out["measured_league"])


if __name__ == "__main__":
    main()
