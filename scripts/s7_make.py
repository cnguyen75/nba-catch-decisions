"""Stage 5a analysis (registered 0437efd): make-model comparison (current vs motion) on the fresh calibration games,
and the Stage 4 behavioural logistic refit with motion features. Writes out/s5/s5a.json."""

from collections.abc import Callable
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, S4, load  # noqa: E402
from s4_make import BINS, X2  # noqa: E402
from s6_clock import cov, unit  # noqa: E402
from vshoot2 import ece  # noqa: E402


S5 = Path(__file__).resolve().parent.parent / "out" / "s5"
NB = 1000


def motion_X(d: pd.DataFrame) -> np.ndarray:
    sp = d.s_speed.clip(0, 25).to_numpy(float)
    return np.column_stack(
        [
            d.s_closing_pre.clip(-15, 15).to_numpy(float),
            sp,
            (sp < 3).astype(float),
            d.s_n_def6.clip(upper=3).to_numpy(float),
        ]
    )


def fit_platt(
    tr: pd.DataFrame, Xf: Callable[[pd.DataFrame], np.ndarray]
) -> Callable[[pd.DataFrame], np.ndarray]:
    games = np.array(sorted(tr.game.unique()))
    perm = np.random.default_rng(5).permutation(len(games))
    fold = {g: i % 5 for i, g in zip(range(len(games)), games[perm])}
    f = tr.game.map(fold).to_numpy()
    X = Xf(tr)
    y = tr.made.astype(int).to_numpy()
    oof = np.zeros(len(tr))
    for k in range(5):
        sc = StandardScaler().fit(X[f != k])
        m = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(X[f != k]), y[f != k])
        oof[f == k] = m.decision_function(sc.transform(X[f == k]))
    pl = LogisticRegression(C=1e6).fit(oof.reshape(-1, 1), y)
    A, B = float(pl.coef_[0, 0]), float(pl.intercept_[0])
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(X), y)
    return lambda d: expit(A * m.decision_function(sc.transform(Xf(d))) + B)


def criteria(ev: pd.DataFrame, p: np.ndarray) -> dict[str, float | bool]:
    out = ev.assign(pred=p)
    lvl = abs(out.pred.mean() - out.made.mean())
    t = out.groupby(pd.cut(out.open_release_all, BINS, right=False), observed=True).agg(
        n=("made", "size"), pred=("pred", "mean"), obs=("made", "mean")
    )
    t["limit"] = np.maximum(0.04, 2 * np.sqrt(t.obs * (1 - t.obs) / t.n))
    t["err"] = t.pred - t.obs
    lo, hi = out[out.open_release_all < 4], out[out.open_release_all >= 8]
    dg = abs((hi.pred.mean() - lo.pred.mean()) - (hi.made.mean() - lo.made.mean()))
    return {
        "level": round(float(lvl), 4),
        "level_pass": bool(lvl <= 0.01),
        "gradient": round(float(dg), 4),
        "gradient_pass": bool(dg <= 0.03),
        "bins_pass": bool((t.err.abs() <= t.limit).all()),
        "worst_bin_err": round(float(t.err.abs().max()), 4),
        "ece": round(ece(out.pred.to_numpy(), out.made.to_numpy(float))[0], 4),
    }


def main() -> None:
    c, s = load()
    ms = pd.concat(
        [pd.read_csv(f, dtype={"game": str}) for f in sorted(S5.glob("motion_shots_*.csv"))]
    )
    mc = pd.concat(
        [pd.read_csv(f, dtype={"game": str}) for f in sorted(S5.glob("motion_catches_*.csv"))]
    )
    rep = {"n_motion_catches": int(len(mc)), "n_motion_shots": int(len(ms))}
    # ---------- make-model comparison
    s = s.merge(ms, on=["game", "eventnum"], how="left")
    s["located"] = s.reason.astype(str).str.startswith("ok")
    s["cs"] = (s.catch_to_shot.notna() & (s.catch_to_shot <= 1.5)).astype(int)
    js = s[
        s.located
        & ~s.shooter.isin(GATED)
        & s.open_release_all.notna()
        & s.d_release.notna()
        & s.jump.astype(bool)
        & s.sc_release.notna()
    ]
    n_all = len(js)
    js = js[js.s_closing_pre.notna() & js.s_speed.notna()]
    rep["make_rows_dropped_missing_motion"] = int(n_all - len(js))
    tr, ev = js[js.split == "train"], js[js.split == "calib"]
    Xc = lambda d: X2(d.d_release, d.zone_release, d.three, d.open_release_all, d.cs, d.sc_release)
    Xm = lambda d: np.column_stack([Xc(d), motion_X(d)])
    pc, pm = fit_platt(tr, Xc)(ev), fit_platt(tr, Xm)(ev)
    y = ev.made.to_numpy(float)
    ll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    llc, llm = ll(pc), ll(pm)
    gidx = {g: np.where(ev.game.to_numpy() == g)[0] for g in ev.game.unique()}
    r = np.random.default_rng(0)
    gs = list(gidx)
    dl = []
    for _ in range(NB):
        ix = np.concatenate([gidx[g] for g in r.choice(gs, len(gs))])
        dl.append(llm[ix].mean() - llc[ix].mean())
    rep["make_comparison"] = {
        "n_train": int(len(tr)),
        "n_eval": int(len(ev)),
        "current": criteria(ev, pc),
        "motion": criteria(ev, pm),
        "logloss_current": round(float(llc.mean()), 5),
        "logloss_motion": round(float(llm.mean()), 5),
        "delta_logloss_motion_minus_current": [
            round(float(llm.mean() - llc.mean()), 5),
            [round(float(x), 5) for x in np.quantile(dl, [0.025, 0.975])],
        ],
    }
    rep["make_comparison"]["motion_improves_logloss"] = bool(np.quantile(dl, 0.975) < 0)
    # motion coefficients (standardized logit, for direction only)
    Xt = Xm(tr)
    sc = StandardScaler().fit(Xt)
    m = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(Xt), tr.made.astype(int))
    rep["motion_coefs_standardized"] = dict(
        zip(["closing_pre", "shooter_speed", "set", "n_def6"], m.coef_[0, -4:].round(4).tolist())
    )
    print(json.dumps(rep, indent=1))
    # ---------- behavioural refit
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    lg = unit(vs[~vs.pid.isin(GATED) & (vs.split == "train")])
    pv = pd.read_csv(S4 / "values.csv", dtype={"game": str})
    groups = {"League": lg, **{n: unit(pv[pv.pid == p]) for p, n in GATED.items()}}

    def motion_cov(d: pd.DataFrame, post: bool = True) -> np.ndarray:
        src = d.source5.fillna("other")
        cols = [
            d.closing_pre.clip(-15, 15),
            d.catcher_speed.clip(0, 25),
            (d.catcher_speed < 3).astype(float),
            d.n_def6.clip(upper=3),
            d.flight_time.clip(0, 3),
            d.flight_dist.clip(0, 60),
            (src == "oreb").astype(float),
            (src == "inbound").astype(float),
            (src == "other").astype(float),
        ]
        if post:
            cols.insert(1, d.closing_post.clip(-15, 15))
        return np.column_stack([cov(d)] + [np.asarray(x, float) for x in cols])

    beh = {}
    for k, (name, d) in enumerate(groups.items()):
        d = d.merge(mc, on=["game", "pid", "start"], how="left")
        d = d[d.closing_pre.notna() & d.closing_post.notna() & d.catcher_speed.notna()]
        d = d.assign(y=(d.action == "shoot").astype(float))
        gi = {g: np.where(d.game.to_numpy() == g)[0] for g in d.game.unique()}
        gl = list(gi)
        res = {"n": int(len(d)), "shots": int(d.y.sum())}
        for label, fx in (
            ("stage4", cov),
            ("motion", motion_cov),
            ("motion_no_post", lambda x: motion_cov(x, False)),
        ):
            X = fx(d)
            yy = d.y.to_numpy()
            b = logit_fit(X, yy)
            rr = np.random.default_rng(300 + k)
            bs = []
            for _ in range(NB):
                ix = np.concatenate([gi[g] for g in rr.choice(gl, len(gl))])
                bb = logit_fit(X[ix], yy[ix])
                bs.append((bb[1], bb[2]))
            bs = np.array(bs)
            res[label] = {
                "beta_clock": [
                    round(float(b[1]), 4),
                    np.quantile(bs[:, 0], [0.025, 0.975]).round(4).tolist(),
                ],
                "beta_open": [
                    round(float(b[2]), 4),
                    np.quantile(bs[:, 1], [0.025, 0.975]).round(4).tolist(),
                ],
                "ER_s_per_ft": [
                    round(float(-b[2] / b[1]), 3),
                    np.quantile(-bs[:, 1] / bs[:, 0], [0.025, 0.975]).round(3).tolist(),
                ],
            }
        beh[name] = res
        print(name, json.dumps(res))
    rep["behavioural"] = beh
    (S5 / "s5a.json").write_text(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
