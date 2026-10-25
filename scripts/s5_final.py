"""Final round (registered e0ab785): gated checks on the 16-30 ft unit, and the descriptive
revealed-vs-measured value of openness. Writes out/s4/final.json.
"""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression


sys.path.insert(0, str(Path(__file__).parent))
from s4_checks import gap_slope, power_one  # noqa: E402
from s4_cont import OPEN_COL, X_full, ridge  # noqa: E402
from s4_data import GATED, S4, ZONES  # noqa: E402
from s4_make import X2  # noqa: E402


GATED_NAMES = {"Curry", "Harden"}


def main() -> None:
    m = np.load(S4 / "make_model.npz")
    mk = json.loads((S4 / "make_report.json").read_text())
    g_zone, offs, kf = mk["g_zone"], mk["player_offsets"], int(m["kf"])

    def v_shoot(d: pd.DataFrame, op: pd.Series | np.ndarray, name: str) -> np.ndarray:
        Xr = X2(
            d.d_basket,
            d.zone,
            d.points3 if "points3" in d else d.zone.isin(["above_break3", "corner3"]).astype(int),
            op,
            np.ones(len(d)),
            (d.shot_clock - kf / 25).clip(lower=0),
        )
        lg = float(m["A"]) * (
            ((Xr - m["mean"]) / m["scale"]) @ m["coef"].ravel() + m["intercept"][0]
        ) + float(m["B"])
        lg = lg + d.zone.map({z: offs[name][z]["offset_logit"] for z in ZONES}).to_numpy()
        pts = 2 + d.zone.isin(["above_break3", "corner3"]).astype(int).to_numpy()
        return expit(lg) * pts + d.zone.map(g_zone).to_numpy()

    # naive V_continue openness coefficient (refit exactly as s4_cont did)
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    lt = vs[~vs.pid.isin(GATED) & (vs.split == "train")]
    cont = lt[lt.action == "continue"]
    b_open = float(ridge(X_full(cont), cont.poss_points.to_numpy(float))[OPEN_COL])

    v = pd.read_csv(S4 / "values.csv", dtype={"game": str})
    v = v[(v.d_basket >= 16) & (v.d_basket <= 30) & v.action.isin(["shoot", "continue"])].copy()
    out = {"unit": "16-30 ft", "b_open_continue_pts_per_ft": round(b_open, 5), "players": {}}
    rng_seed = 0
    for pid, name in GATED.items():
        d = v[v.pid == pid].copy()
        chk = np.abs(v_shoot(d, d.open_cf, name) - d.V_shoot.to_numpy()).max()
        r = {"gated": name in GATED_NAMES, "v_shoot_reproduction_max_abs_diff": float(chk)}
        tr = d[d.split == "train"]
        r["n_train"] = int(len(tr))
        r["n_train_shoot"] = int((tr.action == "shoot").sum())
        # ---- gated checks
        band = tr[tr.d_basket >= 22].assign(V_continue=lambda x: x.V_cont_naive)
        r["check1_gap_slope_22_30"] = gap_slope(band)
        if r["check1_gap_slope_22_30"]["passes"]:
            pw = power_one(tr, "V_cont_naive")[0]
            r["power"] = pw
            r["power_passes"] = bool(pw["mde80_at_c0"] <= 0.15)
        else:
            r["power_passes"] = False
        r["proceeds"] = bool(r["check1_gap_slope_22_30"]["passes"] and r["power_passes"])
        # ---- descriptive: revealed vs measured value of openness (train + validation, 16-30 ft)
        ref_cf, ref_c = float(d.open_cf.median()), float(d.open_catch.median())
        vs_ref = v_shoot(d, np.full(len(d), ref_cf), name)
        vc_ref = d.V_cont_naive.to_numpy() - b_open * (
            d.open_catch.clip(upper=15).to_numpy() - min(ref_c, 15)
        )
        d["gap"] = d.V_shoot - d.V_cont_naive
        d["gap_dz"] = vs_ref - vc_ref
        d["gap_open"] = d.gap - d.gap_dz
        y = (d.action == "shoot").astype(int).to_numpy()
        Xo, gdz, gop = (
            d.open_cf.to_numpy(float),
            d.gap_dz.to_numpy(float),
            d.gap_open.to_numpy(float),
        )

        def est(ix: np.ndarray) -> tuple[float, float, float, float]:
            a = np.polyfit(Xo[ix], gop[ix], 1)[0]
            lr = LogisticRegression(C=1e6, max_iter=1000).fit(
                np.column_stack([Xo[ix], gdz[ix]]), y[ix]
            )
            b, c = lr.coef_[0]
            return a, b, c, b / c

        pt = est(np.arange(len(d)))
        rr = np.random.default_rng(rng_seed)
        bs = np.array([est(rr.integers(0, len(d), len(d))) for _ in range(2000)])
        ci = lambda j: [round(float(x), 4) for x in np.quantile(bs[:, j], [0.025, 0.975])]
        desc = {
            "n": int(len(d)),
            "n_shoot": int(y.sum()),
            "ref_open_cf": round(ref_cf, 2),
            "sd_gap_dz": round(float(gdz.std()), 4),
            "sd_open_cf": round(float(Xo.std()), 3),
            "a_measured_pts_per_ft": [round(float(pt[0]), 4), ci(0)],
            "b_logodds_per_ft": [round(float(pt[1]), 4), ci(1)],
            "c_logodds_per_point_gap_dz": [round(float(pt[2]), 4), ci(2)],
            "d_revealed_pts_per_ft": [round(float(pt[3]), 4), ci(3)],
            "c_ci_includes_0": bool(ci(2)[0] <= 0 <= ci(2)[1]),
        }
        r["descriptive"] = desc
        out["players"][name] = r
    (S4 / "final.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
