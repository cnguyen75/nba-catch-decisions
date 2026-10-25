"""Stage 5b strategy 2 (registered 0dcd379): shot clock 5-24 s as exclusion.

s9_heck2.py falsify        step 1
s9_heck2.py excl           step 2
s9_heck2.py synth <rho>    step 3
"""

import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from scipy.special import expit, ndtr


sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, load  # noqa: E402
from s4_make import X2  # noqa: E402
import s8_heck as h  # noqa: E402


S5 = h.S5


def late_mid(sc: pd.Series | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sc = np.asarray(sc, float)
    return (sc <= 4).astype(float), np.clip(sc, 4, 24) - 4


def falsify() -> None:
    _, s = load()
    ms = pd.concat(
        [pd.read_csv(f, dtype={"game": str}) for f in sorted(S5.glob("motion_shots_*.csv"))]
    )
    s = s.merge(ms, on=["game", "eventnum"], how="left")
    s["cs"] = (s.catch_to_shot.notna() & (s.catch_to_shot <= 1.5)).astype(int)
    js = s[
        s.reason.astype(str).str.startswith("ok")
        & ~s.shooter.isin(GATED)
        & s.open_release_all.notna()
        & s.d_release.notna()
        & s.jump.astype(bool)
        & s.sc_release.notna()
        & s.s_closing_pre.notna()
        & s.s_speed.notna()
        & (s.split == "train")
    ].reset_index(drop=True)

    def feats(d: pd.DataFrame) -> np.ndarray:
        base = X2(d.d_release, d.zone_release, d.three, d.open_release_all, d.cs, d.sc_release)[
            :, :-2
        ]  # drop sc, sc^2
        late, mid = late_mid(d.sc_release)
        sp = d.s_speed.clip(0, 25).to_numpy(float)
        return np.column_stack(
            [
                base,
                d.s_closing_pre.clip(-15, 15),
                sp,
                (sp < 3).astype(float),
                d.s_n_def6.clip(upper=3),
                late,
                mid,
            ]
        )

    def ame(d: pd.DataFrame) -> float:
        X = feats(d)
        m, sd = X.mean(0), X.std(0)
        sd[sd == 0] = 1
        Xs = np.column_stack([np.ones(len(X)), (X - m) / sd])
        b = logit_fit(Xs, d.made.to_numpy(float))
        beta_mid = b[-1] / sd[-1]
        p = expit(Xs @ b)
        sel = d.sc_release.to_numpy(float) > 4
        return float(np.mean(p[sel] * (1 - p[sel])) * beta_mid)

    def boot(d: pd.DataFrame, seed: int) -> np.ndarray:
        gi = {g: np.where(d.game.to_numpy() == g)[0] for g in d.game.unique()}
        gl = list(gi)
        r = np.random.default_rng(seed)
        return np.array(
            [
                ame(d.iloc[np.concatenate([gi[g] for g in r.choice(gl, len(gl))])])
                for _ in range(1000)
            ]
        )

    res = {}
    for name, d, seed in (
        ("all_jump_shots", js, 0),
        (
            "release_16_30ft",
            js[(js.d_release >= 16) & (js.d_release <= 30)].reset_index(drop=True),
            1,
        ),
    ):
        a = ame(d)
        bs = boot(d, seed)
        lo, hi = np.quantile(bs, [0.025, 0.975])
        res[name] = {
            "n": int(len(d)),
            "ame_per_s": round(a, 5),
            "ci95": [round(float(lo), 5), round(float(hi), 5)],
            "covers_0": bool(lo <= 0 <= hi),
            "within_0.01": bool(lo >= -0.01 and hi <= 0.01),
        }
    res["passes"] = bool(res["all_jump_shots"]["covers_0"] and res["all_jump_shots"]["within_0.01"])
    (S5 / "s5b2_falsify.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def design2(d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    Xo = h.X_out(d)
    late, mid = late_mid(d.shot_clock)
    Xo[:, 6] = late  # shot clock column -> late indicator
    Xz = np.column_stack([Xo, mid, h.X_excl(d)])
    return h.Std(Xo)(Xo), h.Std(Xz)(Xz)


def excl() -> None:
    d, nd = h.build_frame("train")
    X, Z = design2(d)
    s, y = d.s.to_numpy(float), d.y.to_numpy(float)
    g_full, ll_full = h.probit(Z, s)
    g_res, ll_res = h.probit(X, s)
    LR = 2 * (ll_full - ll_res)
    b_naive, _ = h.probit(X[s == 1], y[s == 1])
    res = {
        "n": int(len(d)),
        "n_shoot": int(s.sum()),
        "LR": round(float(LR), 2),
        "df": 6,
        "LR_per_df": round(float(LR / 6), 2),
        "partial_pseudo_R2": round(float(1 - ll_full / ll_res), 5),
        "passes": bool(LR / 6 >= 10),
        "excluded_coefs_std": dict(
            zip(
                ["clock_mid", "best_tm_open", "margin", "oreb", "inbound", "other"],
                g_full[-6:].round(4).tolist(),
            )
        ),
    }
    np.savez(S5 / "heck2_true.npz", g=g_full, b=b_naive)
    (S5 / "s5b2_excl.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def synth(rho: float) -> None:
    d, _ = h.build_frame("train")
    X, Z = design2(d)
    t = np.load(S5 / "heck2_true.npz")
    g, b = t["g"], t["b"]
    base = {0.0: 800, 0.3: 900, 0.6: 1000}[rho]
    zg, xb = Z @ g, X @ b
    runs = []
    for seed in range(base, base + 20):
        t0 = time.time()
        r = np.random.default_rng(seed)
        u = r.standard_normal(len(d))
        e = rho * u + np.sqrt(1 - rho**2) * r.standard_normal(len(d))
        s = (zg + u > 0).astype(float)
        y = (xb + e > 0).astype(float) * s
        g0, _ = h.probit(Z, s)
        b0, _ = h.probit(X[s == 1], y[s == 1])
        th, info, _ = h.fit_heck(Z, X, s, y, g0, b0)
        m0 = s == 0
        cf_true = float(np.mean(h.phi2(xb[m0], -zg[m0], -rho) / ndtr(-zg[m0])))
        cf_est = h.cf_rate(th, Z, X, s)
        cf_naive = float(np.mean(ndtr(X[m0] @ b0)))
        runs.append(
            {
                "seed": seed,
                "rho_hat": round(info["rho"], 4),
                "rho_ci": [round(x, 4) for x in info["rho_ci"]],
                "se_rho": round(info["se_rho_delta"], 4),
                "covers": bool(info["rho_ci"][0] <= rho <= info["rho_ci"][1]),
                "converged": info["converged"],
                "cf_true": round(cf_true, 4),
                "cf_est": round(cf_est, 4),
                "cf_err": round(abs(cf_est - cf_true), 4),
                "cf_naive_err": round(abs(cf_naive - cf_true), 4),
                "sec": round(time.time() - t0, 1),
            }
        )
        print(json.dumps(runs[-1]), flush=True)
    out = {
        "rho": rho,
        "covers": sum(x["covers"] for x in runs),
        "cf_within_0.03": sum(x["cf_err"] <= 0.03 for x in runs),
        "cf_within_0.05_info": sum(x["cf_err"] <= 0.05 for x in runs),
        "mean_se_rho": round(float(np.mean([x["se_rho"] for x in runs])), 4),
        "median_cf_err": round(float(np.median([x["cf_err"] for x in runs])), 4),
        "median_naive_err": round(float(np.median([x["cf_naive_err"] for x in runs])), 4),
        "runs": runs,
    }
    out["passes"] = bool(out["covers"] >= 18 and out["cf_within_0.03"] >= 18)
    (S5 / f"s5b2_synth_{rho}.json").write_text(json.dumps(out, indent=1))
    print("SUMMARY", {k: v for k, v in out.items() if k != "runs"})


def real() -> None:
    """Step 4 (only if steps 1-3 pass): real fit on league training catches, validation once,
    reports, player check.
    """
    import json as _j

    from s4_checks import gap_slope
    from s4_cont import X_full, ridge
    from s4_data import S4

    d, _ = h.build_frame("train")
    dv, _ = h.build_frame("validation")
    dg, _ = h.build_frame("gated")

    def raw(dd: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        Xo = h.X_out(dd)
        late, mid = late_mid(dd.shot_clock)
        Xo[:, 6] = late
        return Xo, np.column_stack([Xo, mid, h.X_excl(dd)])

    Xo, Xz = raw(d)
    sx, sz = h.Std(Xo), h.Std(Xz)
    X, Z = sx(Xo), sz(Xz)
    s, y = d.s.to_numpy(float), d.y.to_numpy(float)
    g0, _ = h.probit(Z, s)
    b0, _ = h.probit(X[s == 1], y[s == 1])
    th, info, cov = h.fit_heck(Z, X, s, y, g0, b0)
    kz = Z.shape[1]
    out = {
        "n": int(len(d)),
        "fit": info,
        "resolved": bool(info["rho_ci"][0] > 0 or info["rho_ci"][1] < 0),
    }
    Xvo, Xvz = raw(dv)
    Xv, Zv = sx(Xvo), sz(Xvz)
    sv, yv = dv.s.to_numpy(float), dv.y.to_numpy(float)
    th0 = np.r_[g0, b0, 0.0]
    llh, ll0 = h.ll_vec(th, Zv, Xv, sv, yv), h.ll_vec(th0, Zv, Xv, sv, yv)
    gi = {gg: np.where(dv.game.to_numpy() == gg)[0] for gg in dv.game.unique()}
    gl = list(gi)
    r = np.random.default_rng(0)
    bs = [
        np.mean((llh - ll0)[np.concatenate([gi[x] for x in r.choice(gl, len(gl))])])
        for _ in range(1000)
    ]
    out["validation"] = {
        "n": int(len(dv)),
        "mean_ll_heck": round(float(llh.mean()), 5),
        "mean_ll_separate": round(float(ll0.mean()), 5),
        "diff": round(float((llh - ll0).mean()), 6),
        "ci95": np.quantile(bs, [0.025, 0.975]).round(6).tolist(),
    }
    # make probabilities by open_cf bin, unshot training catches
    g, b, rho = th[:kz], th[kz:-1], np.tanh(th[-1])
    zg, xb, xb0 = Z @ g, X @ b, X @ b0
    m0 = s == 0
    bins = pd.cut(d.open_cf, [0, 2, 4, 6, 8, 99], right=False)
    tab = pd.DataFrame(
        {
            "bin": bins[m0],
            "cond": h.phi2(xb[m0], -zg[m0], -rho) / ndtr(-zg[m0]),
            "marg": ndtr(xb[m0]),
            "naive": ndtr(xb0[m0]),
        }
    )
    out["unshot_make_by_open_cf"] = {
        str(k): {kk: round(float(v), 4) for kk, v in row.items()}
        for k, row in tab.groupby("bin", observed=True).mean().iterrows()
    }
    # corrected value gap by open_cf (league train catches)
    mk = _j.loads((S4 / "make_report.json").read_text())
    gz = mk["g_zone"]
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    lt = vs[~vs.pid.isin(GATED) & (vs.split == "train")]
    cc = lt[lt.action == "continue"]
    b_naive = ridge(X_full(cc), cc.poss_points.to_numpy(float))
    pts = lambda dd: 2 + dd.zone.isin(["above_break3", "corner3"]).astype(int).to_numpy()
    d["V_shoot_corr"] = ndtr(xb) * pts(d) + d.zone.map(gz).to_numpy()
    d["V_cont"] = X_full(d) @ b_naive
    d["gap_corr"] = d.V_shoot_corr - d.V_cont
    out["corrected_value_gap_by_open_cf"] = {
        str(k): round(float(v), 4)
        for k, v in d.groupby(bins, observed=True).gap_corr.mean().items()
    }
    # player check (registered check 1 on corrected values; no player offset)
    Xgo, _ = raw(dg)
    Xg = sx(Xgo)
    dg["V_shoot"] = ndtr(Xg @ b) * pts(dg) + dg.zone.map(gz).to_numpy()
    pv = pd.read_csv(S4 / "values.csv", dtype={"game": str})[
        ["game", "pid", "start", "V_cont_naive"]
    ]
    dg = dg.merge(pv, on=["game", "pid", "start"], how="left")
    out["players"] = {}
    for pid, name in GATED.items():
        band = dg[
            (dg.pid == pid) & (dg.split == "train") & (dg.d_basket >= 22) & (dg.d_basket <= 30)
        ].assign(V_continue=lambda x: x.V_cont_naive)
        chk = gap_slope(band)
        out["players"][name] = {"check1": chk, "continues": bool(out["resolved"] and chk["passes"])}
    (S5 / "s5b2_real.json").write_text(_j.dumps(out, indent=1, default=float))
    print(_j.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"falsify": falsify, "excl": excl, "synth": lambda: synth(float(sys.argv[2])), "real": real}[
        sys.argv[1]
    ]()
