"""Stage 3b-prep steps 0, 2, 3, 7b, 4 (registered ca82621 / f3a51a5). Writes
out/s4/make_report.json, out/s4/vshoot.csv.
"""

import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
from numpy.typing import ArrayLike
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


sys.path.insert(0, str(Path(__file__).parent))
from s4_data import GATED, S4, ZONES, load  # noqa: E402
from s4_data import ROOT as ROOT_DIR
from values import map_offset  # noqa: E402
from vshoot2 import ece, ns_basis  # noqa: E402


BINS = [0, 2, 4, 6, 8, 12, 99]
SCORE_ONLY = "--score-only" in sys.argv
OPEN_KNOTS = np.array([2.0, 4.0, 6.0, 8.0, 12.0])


def X2(
    d: ArrayLike, zone: ArrayLike, three: ArrayLike, op: ArrayLike, cs: ArrayLike, sc: ArrayLike
) -> np.ndarray:
    d = np.asarray(d, float)
    z = np.stack([(np.asarray(zone) == q) for q in ZONES], 1).astype(float)
    lo = np.log1p(np.clip(np.asarray(op, float), 0, 30))
    three = np.asarray(three, float)
    cs = np.asarray(cs, float)
    sc = np.asarray(sc, float)
    op_c = np.clip(np.asarray(op, float), 0, 30)
    return np.column_stack(
        [
            ns_basis(d),
            z,
            ns_basis(op_c, OPEN_KNOTS),
            lo * d / 10,
            lo * three,
            cs,
            cs * lo,
            sc,
            sc**2 / 100,
        ]
    )


def shots_X(df: pd.DataFrame) -> np.ndarray:
    return X2(df.d_release, df.zone_release, df.three, df.open_release_all, df.cs, df.sc_release)


def main() -> None:
    c, s = load()
    rep = {}
    s["located"] = s.reason.astype(str).str.startswith("ok")
    s["cs"] = (s.catch_to_shot.notna() & (s.catch_to_shot <= 1.5)).astype(int)
    lg = s[s.located & ~s.shooter.isin(GATED) & s.open_release_all.notna() & s.d_release.notna()]
    # ---- step 0: all league threes by release openness (non-test)
    th = lg[lg.three.astype(bool)]

    def tab(d: pd.DataFrame) -> dict[str, dict[str, float]]:
        return {
            str(k): {"make": round(float(v["mean"]), 3), "n": int(v["size"])}
            for k, v in d.groupby(pd.cut(d.open_release_all, BINS, right=False), observed=True)
            .made.agg(["mean", "size"])
            .iterrows()
        }

    rep["threes_by_release_openness"] = {
        "all_league_threes": tab(th),
        "catch_and_shoot_threes": tab(th[th.cs == 1]),
        "n_all": int(len(th)),
        "n_cs": int((th.cs == 1).sum()),
    }
    # ---- step 2: make model on all league jump shots
    js = lg[lg.jump.astype(bool) & lg.sc_release.notna()]
    tr, va = (
        js[js.split == "train"],
        js[js.split == "calib"],
    )  # attempt 2: score on the fresh calibration games

    def fit_base(d: pd.DataFrame) -> tuple[StandardScaler, LogisticRegression]:
        sc_ = StandardScaler().fit(shots_X(d))
        return sc_, LogisticRegression(C=1.0, max_iter=5000).fit(
            sc_.transform(shots_X(d)), d.made.astype(int)
        )

    games = np.array(sorted(tr.game.unique()))
    perm = np.random.default_rng(5).permutation(len(games))
    fold = {g: i % 5 for i, g in zip(range(len(games)), games[perm], strict=False)}
    f = tr.game.map(fold).to_numpy()
    oof = np.zeros(len(tr))
    for k in range(5):
        a_, m_ = fit_base(tr[f != k])
        oof[f == k] = m_.decision_function(a_.transform(shots_X(tr[f == k])))
    pl = LogisticRegression(C=1e6).fit(oof.reshape(-1, 1), tr.made.astype(int))
    A, B = float(pl.coef_[0, 0]), float(pl.intercept_[0])
    scl, mdl = fit_base(tr)

    def p_make(Xraw: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-(A * mdl.decision_function(scl.transform(Xraw)) + B)))

    pv = p_make(shots_X(va))
    yv = va.made.to_numpy(float)
    e, dec = ece(pv, yv)
    rng = np.random.default_rng(0)
    null = np.array(
        [
            ece(pv, (rng.random(len(pv)) < pv).astype(float))[0]
            for _ in range(5000 if SCORE_ONLY else 1)
        ]
    )
    if SCORE_ONLY:
        out = va.assign(pred=pv)
        out[["game", "made", "pred", "open_release_all", "three", "cs"]].to_csv(
            S4 / "make_calib_preds.csv", index=False
        )
        lvl = abs(out.pred.mean() - out.made.mean())
        bb = pd.cut(out.open_release_all, BINS, right=False)
        t = out.groupby(bb, observed=True).agg(
            n=("made", "size"), pred=("pred", "mean"), obs=("made", "mean")
        )
        t["se"] = np.sqrt(t.obs * (1 - t.obs) / t.n)
        t["limit"] = np.maximum(0.04, 2 * t.se)
        t["err"] = t.pred - t.obs
        t["ok"] = t.err.abs() <= t.limit
        lo4, hi8 = out[out.open_release_all < 4], out[out.open_release_all >= 8]
        dp, do = hi8.pred.mean() - lo4.pred.mean(), hi8.made.mean() - lo4.made.mean()
        res = {
            "n_train_shots": int(len(tr)),
            "n_calib_shots": int(len(out)),
            "n_calib_games": int(out.game.nunique()),
            "platt": [A, B],
            "level": {
                "mean_pred": round(out.pred.mean(), 4),
                "mean_obs": round(out.made.mean(), 4),
                "abs_diff": round(lvl, 4),
                "passes": bool(lvl <= 0.01),
            },
            "gradient": {
                "pred_change": round(dp, 4),
                "obs_change": round(do, 4),
                "abs_diff": round(abs(dp - do), 4),
                "passes": bool(abs(dp - do) <= 0.03),
                "ratio_obs_over_pred": round(do / dp, 4),
            },
            "bins": {
                str(k): {kk: (round(float(x), 4) if kk != "ok" else bool(x)) for kk, x in r.items()}
                for k, r in t.iterrows()
            },
            "bins_pass": bool(t.ok.all()),
            "ece_info": round(e, 4),
            "decile_table_info": dec,
        }
        res["all_pass"] = res["level"]["passes"] and res["gradient"]["passes"] and res["bins_pass"]
        (ROOT_DIR / "checks/s4_calib2_score.json").write_text(
            json.dumps(res, indent=1, default=str)
        )
        print(
            json.dumps(
                {k: v for k, v in res.items() if k != "decile_table_info"}, indent=1, default=str
            )
        )
        return
    rep["make_model"] = {
        "n_train": int(len(tr)),
        "n_val": int(len(va)),
        "platt": [A, B],
        "ece_val": round(e, 4),
        "null_p95": round(float(np.quantile(null, 0.95)), 4),
        "null_median": round(float(np.median(null)), 4),
        "passes": bool(e <= np.quantile(null, 0.95)),
        "decile_table_val": dec,
        "share_cs_train": round(float(tr.cs.mean()), 3),
    }
    # openness response of the fitted model (C&S three at 25 ft, sc 12)
    grid = [1, 2, 4, 6, 8, 12]
    rep["make_model"]["p_make_cs_three_25ft"] = {
        o: round(float(p_make(X2([25], ["above_break3"], [1], [o], [1], [12]))[0]), 3) for o in grid
    }
    rep["make_model"]["p_make_cs_mid_16ft"] = {
        o: round(float(p_make(X2([16], ["mid"], [0], [o], [1], [12]))[0]), 3) for o in grid
    }

    # late-clock cross-check
    def slope(d: pd.DataFrame, seed: int = 0, nb: int = 200) -> dict[str, Any]:
        Xs = np.column_stack(
            [
                np.log1p(d.open_release_all.clip(upper=30)),
                ns_basis(d.d_release.to_numpy(float)),
                d.three.astype(float),
            ]
        )
        coef = LogisticRegression(C=1e6, max_iter=5000).fit(Xs, d.made.astype(int)).coef_[0, 0]
        r = np.random.default_rng(seed)
        bs = []
        for _ in range(nb):
            i = r.integers(0, len(d), len(d))
            bs.append(
                LogisticRegression(C=1e6, max_iter=5000)
                .fit(Xs[i], d.made.astype(int).to_numpy()[i])
                .coef_[0, 0]
            )
        return {
            "slope_log1p_open": round(float(coef), 3),
            "ci95": [round(float(x), 3) for x in np.quantile(bs, [0.025, 0.975])],
            "n": int(len(d)),
        }

    rep["late_clock_check"] = {
        "all_train_jump_shots": slope(tr),
        "shot_clock_le_4": slope(tr[tr.sc_release <= 4]),
    }
    # ---- step 3: delta and counterfactual openness
    delta = float(lg[(lg.split == "train") & (lg.cs == 1)].catch_to_shot.median())
    kf = int(min(40, max(5, 5 * round(delta * 25 / 5))))
    rep["delta"] = {
        "median_catch_to_release_s": round(delta, 3),
        "frames_used": kf,
        "seconds_used": kf / 25,
    }
    c = c[c.ok & (c.d_basket <= 30)].copy()
    c["open_cf_raw"] = c[f"open_k{kf}"]
    c = c[c.open_cf_raw.notna()]
    lt = c[~c.pid.isin(GATED) & (c.split == "train")]
    rep["cf_vs_catch_by_zone"] = {
        z: {
            "n": int(len(x)),
            "median_cf_minus_catch": round(float((x.open_cf_raw - x.open_catch).median()), 2),
            "corr": round(float(np.corrcoef(x.open_cf_raw, x.open_catch)[0, 1]), 3),
            "share_cf_lt_catch": round(float((x.open_cf_raw < x.open_catch).mean()), 3),
        }
        for z, x in lt.groupby("zone")
    }
    # ---- step 7b: shot-side selection check
    adj = {}
    for z, x in lt.groupby("zone"):
        x = x.assign(b=np.floor(x.open_catch.clip(upper=29.9)))
        g = x.groupby(["b", x.action == "shoot"]).open_cf_raw.mean().unstack()
        n_ns = x[x.action != "shoot"].groupby("b").size()
        g = g.dropna()
        if len(g) == 0 or True not in g.columns:
            adj[z] = {"diff_nonshot_minus_shot": None, "adjust": 0.0}
            continue
        w = n_ns.reindex(g.index).fillna(0)
        diff = float(np.average(g[False] - g[True], weights=w)) if w.sum() > 0 else np.nan
        adj[z] = {
            "diff_nonshot_minus_shot": round(diff, 3),
            "bins": int(len(g)),
            "adjust": round(diff, 3) if diff > 1.0 else 0.0,
        }
    rep["shot_side_check"] = adj
    c["open_cf"] = c.open_cf_raw - np.where(
        c.action != "shoot", c.zone.map({z: adj[z]["adjust"] for z in adj}).fillna(0), 0.0
    )
    # ---- step 4: g(zone) and V_shoot
    sh = lt[(lt.action == "shoot") & lt.made.notna()]
    sh_pts = sh.made * np.where(sh.three_pbp.astype(bool), 3, 2)
    gz = (sh.poss_points - sh_pts).groupby(sh.zone).mean()
    rep["g_zone"] = {z: round(float(gz.get(z, 0.0)), 4) for z in ZONES}
    sc_cf = (c.shot_clock - kf / 25).clip(lower=0)
    c["p_make_league"] = p_make(
        X2(c.d_basket, c.zone, c.points3, c.open_cf, np.ones(len(c)), sc_cf)
    )
    c["logit_league"] = np.log(c.p_make_league / (1 - c.p_make_league))
    offs = {}
    for pid, name in GATED.items():
        mine = c[
            (c.pid == pid)
            & (c.split == "train")
            & (c.action == "shoot")
            & c.made.notna()
            & c.open_release_all.notna()
            & c.d_release.notna()
            & c.sc_release.notna()
        ]
        lg_act = (
            np.log(
                1
                / p_make(
                    X2(
                        mine.d_release,
                        mine.zone_release,
                        mine.three_pbp.astype(float),
                        mine.open_release_all,
                        np.ones(len(mine)),
                        mine.sc_release,
                    )
                )
                - 1
            )
            * -1
        )
        offs[name] = {
            z: {
                "n": int((mine.zone == z).sum()),
                "offset_logit": round(
                    map_offset(
                        lg_act[(mine.zone == z).to_numpy()], mine[mine.zone == z].made.to_numpy()
                    ),
                    4,
                )
                if (mine.zone == z).any()
                else 0.0,
            }
            for z in ZONES
        }
        sel = c.pid == pid
        o = c.loc[sel, "zone"].map({z: offs[name][z]["offset_logit"] for z in ZONES})
        c.loc[sel, "logit_league"] = c.loc[sel, "logit_league"] + o
    rep["player_offsets"] = offs
    p = 1 / (1 + np.exp(-c.logit_league))
    c["V_shoot_imm"] = p * (2 + c.points3)
    c["V_shoot"] = c.V_shoot_imm + c.zone.map(rep["g_zone"])
    keep = [
        "game",
        "split",
        "pid",
        "start",
        "team",
        "quarter",
        "d_basket",
        "zone",
        "open_catch",
        "open_cf_raw",
        "open_cf",
        "rim_prot",
        "shot_clock",
        "best_tm_open",
        "margin",
        "poss_points",
        "action",
        "made",
        "V_shoot",
        "V_shoot_imm",
    ]
    c[keep].to_csv(S4 / "vshoot.csv", index=False)
    np.savez(
        S4 / "make_model.npz",
        mean=scl.mean_,
        scale=scl.scale_,
        coef=mdl.coef_,
        intercept=mdl.intercept_,
        A=A,
        B=B,
        kf=kf,
    )
    (S4 / "make_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(
        json.dumps(
            {k: v for k, v in rep.items() if k not in ("make_model",)}, indent=1, default=str
        )
    )
    print(
        json.dumps(
            {k: v for k, v in rep["make_model"].items() if k != "decile_table_val"}, indent=1
        )
    )
    print(pd.DataFrame(rep["make_model"]["decile_table_val"]).to_string())


if __name__ == "__main__":
    main()
