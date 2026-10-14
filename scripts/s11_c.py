"""Stage 6 C (registered 811c61b): selection model strategy 3 with all valid instruments.

  s11_c.py excl            exclusion strength (instruments from out/s6/b.json)
  s11_c.py synth <rho>     synthetic gate
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

sys.path.insert(0, str(Path(__file__).parent))
import s8_heck as h  # noqa: E402
from s4_data import GATED, ROOT, S4  # noqa: E402

S6 = ROOT / "out" / "s6"


def frame(split):
    c = pd.read_csv(S6 / "catch_state.csv", dtype={"game": str}, low_memory=False)
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str}, usecols=["game", "pid", "start", "open_cf"])
    c = c.merge(vs, on=["game", "pid", "start"], how="inner")
    d = c[~c.pid.isin(GATED) & (c.split == split)]
    d = d[(d.d_basket >= 16) & (d.d_basket <= 30) & d.shot_clock.notna() & d.action.isin(["shoot", "continue"])
          & d.closing_pre.notna() & d.closing_post.notna() & d.catcher_speed.notna() & d.minutes_so_far.notna() & d.rel_open.notna()]
    d = d[~((d.action == "shoot") & d.made.isna())].copy()
    d["s"] = (d.action == "shoot").astype(int); d["y"] = d.made.fillna(0).astype(int)
    return d.reset_index(drop=True)


def design(d, instruments, window):
    Xo = h.X_out(d)
    sc = d.shot_clock.to_numpy(float)
    Xo[:, 6] = (sc <= 4)
    A = np.column_stack([d.last_made.fillna(0), d.none_yet, d.t_since_make, d.rel_open, d.def_h / 10, d.def_h_missing, d.minutes_so_far / 10,
                         d.b2b.fillna(0), d.clutch, d.def_eff, d.rim_eff, d.drive_eff]).astype(float)
    X = np.column_stack([Xo, A])
    inst = []
    if "clock_mid" in instruments:
        inst.append(np.clip(sc, 4, 24) - 4)
    if "window" in instruments:
        inst.append(d[window].to_numpy(float))
    if "first_made" in instruments:
        inst.append(d.first_made.fillna(0).to_numpy(float))
    Z = np.column_stack([X] + inst + [h.X_excl(d)])
    return h.Std(X)(X), h.Std(Z)(Z), len(inst) + 5


def load_b():
    b = json.loads((S6 / "b.json").read_text())
    return b["make_falsification"]["valid_instruments"], b["make_falsification"]["window_used"]


def excl():
    inst, w = load_b()
    d = frame("train")
    X, Z, k = design(d, inst, w)
    s, y = d.s.to_numpy(float), d.y.to_numpy(float)
    g_full, ll_full = h.probit(Z, s); _, ll_res = h.probit(X, s)
    b_naive, _ = h.probit(X[s == 1], y[s == 1])
    LR = 2 * (ll_full - ll_res)
    res = {"instruments": inst + ["best_tm_open", "margin", "source(3)"], "window": w, "n": int(len(d)), "n_shoot": int(s.sum()),
           "LR": round(float(LR), 2), "df": k, "LR_per_df": round(float(LR / k), 2), "partial_pseudo_R2": round(float(1 - ll_full / ll_res), 5),
           "passes": bool(LR / k >= 10), "instrument_coefs_std": g_full[-k:].round(4).tolist()}
    np.savez(S6 / "heck3_true.npz", g=g_full, b=b_naive)
    (S6 / "c_excl.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def synth(rho):
    inst, w = load_b()
    d = frame("train")
    X, Z, _ = design(d, inst, w)
    t = np.load(S6 / "heck3_true.npz"); g, b = t["g"], t["b"]
    base = {0.0: 1100, 0.3: 1200, 0.6: 1300}[rho]
    zg, xb = Z @ g, X @ b
    runs = []
    for seed in range(base, base + 20):
        t0 = time.time(); r = np.random.default_rng(seed)
        u = r.standard_normal(len(d)); e = rho * u + np.sqrt(1 - rho ** 2) * r.standard_normal(len(d))
        s = (zg + u > 0).astype(float); y = (xb + e > 0).astype(float) * s
        g0, _ = h.probit(Z, s); b0, _ = h.probit(X[s == 1], y[s == 1])
        th, info, _ = h.fit_heck(Z, X, s, y, g0, b0)
        m0 = s == 0
        cf_true = float(np.mean(h.phi2(xb[m0], -zg[m0], -rho) / ndtr(-zg[m0])))
        cf_est = h.cf_rate(th, Z, X, s); cf_naive = float(np.mean(ndtr(X[m0] @ b0)))
        runs.append({"seed": seed, "rho_hat": round(info["rho"], 4), "rho_ci": [round(x, 4) for x in info["rho_ci"]], "se_rho": round(info["se_rho_delta"], 4),
                     "covers": bool(info["rho_ci"][0] <= rho <= info["rho_ci"][1]), "converged": info["converged"], "cf_true": round(cf_true, 4),
                     "cf_est": round(cf_est, 4), "cf_err": round(abs(cf_est - cf_true), 4), "cf_naive_err": round(abs(cf_naive - cf_true), 4),
                     "sec": round(time.time() - t0, 1)})
        print(json.dumps(runs[-1]), flush=True)
    out = {"rho": rho, "covers": sum(x["covers"] for x in runs), "cf_within_0.03": sum(x["cf_err"] <= 0.03 for x in runs),
           "cf_within_0.05_info": sum(x["cf_err"] <= 0.05 for x in runs), "mean_se_rho": round(float(np.mean([x["se_rho"] for x in runs])), 4),
           "median_cf_err": round(float(np.median([x["cf_err"] for x in runs])), 4), "median_naive_err": round(float(np.median([x["cf_naive_err"] for x in runs])), 4),
           "runs": runs}
    out["passes"] = bool(out["covers"] >= 18 and out["cf_within_0.03"] >= 18)
    (S6 / f"c_synth_{rho}.json").write_text(json.dumps(out, indent=1))
    print("SUMMARY", {k: v for k, v in out.items() if k != "runs"})


if __name__ == "__main__":
    {"excl": excl, "synth": lambda: synth(float(sys.argv[2]))}[sys.argv[1]]()
