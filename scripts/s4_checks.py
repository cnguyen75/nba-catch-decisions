"""Stage 3b-prep step 6: value-gap openness check, old-vs-new value-gap table, power, synthetic recovery (binary model).
LeBron is computed and reported but not gated. Reads out/s4/values.csv, out/s4/cont_report.json. Writes out/s4/checks.json."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import choice as ch  # noqa: E402
from s4_data import GATED, ROOT, S4  # noqa: E402

BINS = [0, 4, 6, 8, 12, 99]
GATED_NAMES = {"Curry", "Harden"}


def gap_slope(d, nb=2000, seed=0):
    x, y = d.open_cf.to_numpy(float), (d.V_shoot - d.V_continue).to_numpy(float)
    s = np.polyfit(x, y, 1)[0]
    r = np.random.default_rng(seed)
    bs = [np.polyfit(x[i], y[i], 1)[0] for i in (r.integers(0, len(x), len(x)) for _ in range(nb))]
    lo, hi = np.quantile(bs, [.025, .975])
    return {"slope": round(float(s), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)], "n": int(len(x)), "passes": bool(lo > 0)}


def power_one(d, vcol):
    V = np.column_stack([d.V_shoot.to_numpy(float), d[vcol].to_numpy(float)])
    avail = np.ones_like(V, bool)
    y = np.where(d.action == "shoot", 0, 1)
    _, T_p, _ = ch.fit(V, avail, y, 1)  # pilot: only T is kept
    out = {"pilot_T": round(T_p, 4)}
    for cs in (-0.2, 0.0, 0.2):
        cov = np.linalg.inv(ch.fisher(V, avail, np.array([cs]), T_p))
        se = np.sqrt(np.diag(cov))
        out[f"c_shoot={cs:+.1f}"] = {"se_c": round(float(se[0]), 4), "se_T": round(float(se[1]), 4), "mde80": round(float(2.8 * se[0]), 4)}
    out["mde80_at_c0"] = out["c_shoot=+0.0"]["mde80"]
    return out, V, avail, T_p


def synth_one(d, V, avail, T_p):
    res = {}
    rng = np.random.default_rng(7)
    Vimm = V.copy(); Vimm[:, 0] = d.V_shoot_imm.to_numpy(float)
    for sname, (c0, T0) in {"S1": (np.array([-0.2]), T_p), "S2": (np.zeros(1), T_p), "S3": (np.array([0.2]), 1.5 * T_p)}.items():
        cov = np.linalg.inv(ch.fisher(V, avail, c0, T0))
        lim = 2.576 * np.sqrt(np.diag(cov))
        draws = rng.multivariate_normal(np.zeros(2), cov, 100_000)
        p_run = float(np.mean(np.all(np.abs(draws) <= lim, 1)))
        p_rule = float(sum(math.comb(20, j) * p_run ** j * (1 - p_run) ** (20 - j) for j in range(18, 21)))
        runs = []
        for seed in range(100, 120):
            g = np.random.default_rng(seed)
            P = ch.probs(V, avail, c0, T0)
            ys = (P.cumsum(1) > g.random((len(P), 1))).argmax(1)
            c_h, T_h, _ = ch.fit(V, avail, ys, 1)
            ci, _, _ = ch.fit(Vimm, avail, ys, 1)
            err = np.r_[c_h, T_h] - np.r_[c0, T0]
            runs.append({"seed": seed, "c_shoot": round(float(c_h[0]), 4), "T": round(float(T_h), 4),
                         "err": err.round(4).tolist(), "pass": bool(np.all(np.abs(err) <= lim)),
                         "c_shoot_immediate_scale": round(float(ci[0]), 4)})
        n = sum(r["pass"] for r in runs)
        ib = np.array([r["c_shoot_immediate_scale"] - c0[0] for r in runs])
        res[sname] = {"true": [float(c0[0]), round(T0, 4)], "limits": lim.round(4).tolist(), "ideal_p_rule": round(p_rule, 4),
                      "runs_passed": n, "passes": n >= 18, "immediate_scale_bias_mean_sd": [round(float(ib.mean()), 4), round(float(ib.std()), 4)],
                      "runs": runs}
    return res, all(s["passes"] for s in res.values())


def main():
    rep = {"cont_main": json.loads((S4 / "cont_report.json").read_text())["main_V_continue"]}
    main_col = "V_cont_dmf" if rep["cont_main"] == "dmf" else "V_cont_naive"
    sens_col = "V_cont_naive" if main_col == "V_cont_dmf" else "V_cont_dmf"
    v = pd.read_csv(S4 / "values.csv", dtype={"game": str})
    old = pd.read_csv(ROOT / "out/s3/values2.csv", dtype={"game": str})[["game", "pid", "start", "V_shoot", "V_continue"]]
    old = old.rename(columns={"V_shoot": "V_shoot_old", "V_continue": "V_continue_old"})
    v = v.merge(old, on=["game", "pid", "start"], how="left")
    rep["players"] = {}
    for pid, name in GATED.items():
        d = v[(v.pid == pid) & (v.split == "train") & v.action.isin(["shoot", "continue"])].copy()
        r = {"gated": name in GATED_NAMES, "n_train": int(len(d)), "n_shoot": int((d.action == "shoot").sum())}
        # value-gap table, old vs new (bins of counterfactual release openness)
        d["bin"] = pd.cut(d.open_cf, BINS, right=False)
        d["gap_new"] = d.V_shoot - d[main_col]
        d["gap_old"] = d.V_shoot_old - d.V_continue_old
        band = d[(d.d_basket >= 22) & (d.d_basket <= 30)]
        tab = band.groupby("bin", observed=True).agg(n=("gap_new", "size"), shoot_rate=("action", lambda a: (a == "shoot").mean()),
                                                     gap_new=("gap_new", "mean"), gap_old=("gap_old", "mean"))
        r["value_gap_table_22_30ft"] = {str(k): {kk: round(float(vv), 3) for kk, vv in row.items()} for k, row in tab.iterrows()}
        dd = band.assign(V_continue=band[main_col])
        r["check1_gap_slope"] = gap_slope(dd)
        r["check1_gap_slope_sensitivity_other_Vcont"] = gap_slope(band.assign(V_continue=band[sens_col]))
        if not r["check1_gap_slope"]["passes"]:
            r["decision"] = "stops at check 1 (value gap not increasing in openness)"
            rep["players"][name] = r
            continue
        d = d[d.d_basket <= 30]
        pw, V, avail, T_p = power_one(d, main_col)
        r["power_main"] = pw
        r["power_sensitivity_other_Vcont"] = power_one(d, sens_col)[0]
        if pw["mde80_at_c0"] > 0.15:
            r["decision"] = f"underpowered (MDE {pw['mde80_at_c0']}); games needed ~{math.ceil(json.loads((ROOT / 'checks/split.json').read_text())['per_player_counts'][name]['train'] * (pw['mde80_at_c0'] / 0.15) ** 2)}"
            rep["players"][name] = r
            continue
        r["synthetic"], ok = synth_one(d, V, avail, T_p)
        r["decision"] = ("passes synthetic recovery" if ok else "fails synthetic recovery") + ("" if r["gated"] else " (reported, not gated)")
        rep["players"][name] = r
    (S4 / "checks.json").write_text(json.dumps(rep, indent=1, default=str))
    for n, r in rep["players"].items():
        print(n, r["decision"])
        print("  check1", r["check1_gap_slope"], "| sens", r["check1_gap_slope_sensitivity_other_Vcont"])
        print("  table", json.dumps(r["value_gap_table_22_30ft"]))
        if "power_main" in r:
            print("  power", {k: r["power_main"][k] for k in ("pilot_T", "mde80_at_c0")}, "| sens", {k: r["power_sensitivity_other_Vcont"][k] for k in ("pilot_T", "mde80_at_c0")})
        if "synthetic" in r:
            print("  synth", {s: (x["runs_passed"], x["ideal_p_rule"], x["immediate_scale_bias_mean_sd"]) for s, x in r["synthetic"].items()})


if __name__ == "__main__":
    main()
