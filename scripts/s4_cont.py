"""Stage 3b-prep step 5/7: V_continue (naive and Dubin-McFadden corrected), control-group selection check (7a),
DMF synthetic validation (7c). Registered ca82621 / f3a51a5. Reads out/s4/vshoot.csv. Writes out/s4/cont_report.json and
out/s4/values.csv."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).parent))
from s4_data import GATED, ZONES, S4  # noqa: E402

SHRINK_K = 50.0


def X_full(d):
    """Continuation state (registered), unstandardized; column 4 is openness at catch (capped 15)."""
    dd = d.d_basket.to_numpy(float) / 10
    z = np.stack([(d.zone == q).to_numpy() for q in ZONES[1:]], 1).astype(float)  # rim is the reference
    return np.column_stack([np.ones(len(d)), dd, dd ** 2, z, d.open_catch.clip(upper=15), d.rim_prot.clip(upper=20),
                            d.shot_clock, d.best_tm_open.clip(upper=20), d.margin.clip(-20, 20)])


OPEN_COL = 6
EXCL_COLS = [9, 10]  # best teammate openness, margin


def X_out(d):
    return np.delete(X_full(d), EXCL_COLS, axis=1)


def ridge(X, y, alpha=1.0):
    pen = alpha * np.eye(X.shape[1]); pen[0, 0] = 0
    return np.linalg.solve(X.T @ X + pen, X.T @ y)


def logit_fit(X, y, iters=50):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = expit(X @ b)
        H = (X * (p * (1 - p))[:, None]).T @ X + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def dmf_lambda(P):
    P = np.clip(P, 1e-6, 1 - 1e-6)
    return P * np.log(P) / (1 - P) + np.log(1 - P)


def dmf_fit(Xf, Xo, shoot, y):
    """First stage on all rows; second stage on continuing rows. Returns (beta_out_without_lambda, coef_lambda)."""
    g = logit_fit(Xf, shoot)
    P = expit(Xf @ g)
    cont = shoot == 0
    lam = dmf_lambda(P[cont])
    b = np.linalg.lstsq(np.column_stack([Xo[cont], lam]), y[cont], rcond=None)[0]
    return b[:-1], b[-1]


def cluster_boot(df, fn, nb, seed):
    games = df.game.unique()
    idx = {g: np.where(df.game.to_numpy() == g)[0] for g in games}
    r = np.random.default_rng(seed)
    out = []
    for _ in range(nb):
        pick = r.choice(games, len(games))
        out.append(fn(df.iloc[np.concatenate([idx[g] for g in pick])]))
    return np.array(out)


def control_group(lt):
    band = lt[(lt.d_basket >= 22) & (lt.d_basket <= 30)]
    per = band.groupby("pid").agg(n=("action", "size"), rate=("action", lambda a: (a == "shoot").mean()))
    per = per[per.n >= 40]
    ctrl_ids, shoot_ids = per[per.rate < 0.02].index, per[per.rate >= 0.02].index
    res = {"n_players_control": int(len(ctrl_ids)), "n_players_shooters": int(len(shoot_ids))}
    def slope(d):
        return ridge(X_full(d), d.poss_points.to_numpy(float))[OPEN_COL]
    for name, ids in (("control", ctrl_ids), ("shooters", shoot_ids)):
        d = band[band.pid.isin(ids) & (band.action == "continue")]
        bs = cluster_boot(d, slope, 2000, 0)
        res[name] = {"n_catches": int(len(d)), "slope_pts_per_ft": round(float(slope(d)), 4),
                     "ci95": [round(float(x), 4) for x in np.quantile(bs, [.025, .975])]}
    res["selection_present"] = bool(res["shooters"]["slope_pts_per_ft"] > res["control"]["ci95"][1])
    return res


def synth_validation(lt, n_seeds=20, nb=200, rho=0.3):
    """Known continuation values; correlated choice/outcome errors; same sample size as the real league train set."""
    Xf, Xo = X_full(lt), X_out(lt)
    cont = (lt.action == "continue").to_numpy()
    beta_true = np.linalg.lstsq(Xo[cont], lt.poss_points.to_numpy(float)[cont], rcond=None)[0]
    sigma = float(np.std(lt.poss_points.to_numpy(float)[cont] - Xo[cont] @ beta_true))
    true_slope = beta_true[OPEN_COL]
    mean_c = Xo @ beta_true
    gap = lt.V_shoot.to_numpy(float) - mean_c
    Z = np.column_stack([np.ones(len(lt)), gap, lt.best_tm_open.clip(upper=20), lt.margin.clip(-20, 20)])
    gam = logit_fit(Z, (lt.action == "shoot").to_numpy(float))
    rows = []
    for seed in range(300, 300 + n_seeds):
        r = np.random.default_rng(seed)
        z1 = r.standard_normal(len(lt)); z2 = rho * z1 + np.sqrt(1 - rho ** 2) * r.standard_normal(len(lt))
        u = norm.cdf(z2)
        nu = np.log(u / (1 - u))  # logistic marginal
        shoot = ((Z @ gam + nu) > 0).astype(float)
        y = mean_c + sigma * z1
        c_ = shoot == 0
        def naive(ix):
            return np.linalg.lstsq(Xo[ix][c_[ix]], y[ix][c_[ix]], rcond=None)[0][OPEN_COL]
        def corr(ix):
            return dmf_fit(Xf[ix], Xo[ix], shoot[ix], y[ix])[0][OPEN_COL]
        allix = np.arange(len(lt))
        en, ec = naive(allix), corr(allix)
        bn, bc = [], []
        for _ in range(nb):
            ix = r.integers(0, len(lt), len(lt))
            bn.append(naive(ix)); bc.append(corr(ix))
        cin, cic = np.quantile(bn, [.025, .975]), np.quantile(bc, [.025, .975])
        rows.append({"seed": seed, "true": round(true_slope, 4), "naive": round(float(en), 4), "naive_ci": cin.round(4).tolist(),
                     "naive_covers": bool(cin[0] <= true_slope <= cin[1]), "corrected": round(float(ec), 4),
                     "corrected_ci": cic.round(4).tolist(), "corrected_covers": bool(cic[0] <= true_slope <= cic[1]),
                     "shoot_rate": round(float(shoot.mean()), 3)})
    cov_c = sum(x["corrected_covers"] for x in rows)
    miss_n = sum(not x["naive_covers"] for x in rows)
    return {"rho": rho, "sigma": round(sigma, 3), "true_open_slope": round(float(true_slope), 4), "n": int(len(lt)),
            "corrected_covers": cov_c, "naive_misses": miss_n, "passes": bool(cov_c >= 18 and miss_n >= 10),
            "mean_naive_bias": round(float(np.mean([x["naive"] - x["true"] for x in rows])), 4),
            "mean_corrected_bias": round(float(np.mean([x["corrected"] - x["true"] for x in rows])), 4), "runs": rows}


def main():
    v = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    lt = v[~v.pid.isin(GATED) & (v.split == "train")].reset_index(drop=True)
    rep = {"control_group": control_group(lt)}
    print(json.dumps(rep["control_group"], indent=1))
    rep["dmf_synthetic"] = synth_validation(lt)
    print(json.dumps({k: x for k, x in rep["dmf_synthetic"].items() if k != "runs"}, indent=1))
    # naive and corrected V_continue on real data
    cont = (lt.action == "continue").to_numpy()
    y = lt.poss_points.to_numpy(float)
    b_naive = ridge(X_full(lt)[cont], y[cont])
    b_dmf, lam_coef = dmf_fit(X_full(lt), X_out(lt), (lt.action == "shoot").to_numpy(float), y)
    rep["real"] = {"naive_open_slope": round(float(b_naive[OPEN_COL]), 4), "dmf_open_slope": round(float(b_dmf[OPEN_COL]), 4),
                   "dmf_lambda_coef": round(float(lam_coef), 4)}
    use_dmf = rep["control_group"]["selection_present"] and rep["dmf_synthetic"]["passes"]
    rep["main_V_continue"] = "dmf" if use_dmf else "naive"
    g = v[v.pid.isin(GATED)].copy()
    g["V_cont_naive"] = X_full(g) @ b_naive
    g["V_cont_dmf"] = X_out(g) @ b_dmf
    offs = {}
    for pid, name in GATED.items():
        mine = g[(g.pid == pid) & (g.split == "train") & (g.action == "continue")]
        offs[name] = {k: float((mine.poss_points - mine[k]).sum() / (len(mine) + SHRINK_K)) for k in ("V_cont_naive", "V_cont_dmf")}
        for k in ("V_cont_naive", "V_cont_dmf"):
            g.loc[g.pid == pid, k] += offs[name][k]
    rep["player_offsets_cont"] = offs
    g["V_continue"] = g["V_cont_dmf"] if use_dmf else g["V_cont_naive"]
    g.to_csv(S4 / "values.csv", index=False)
    (S4 / "cont_report.json").write_text(json.dumps(rep, indent=1, default=float))
    print(json.dumps({k: rep[k] for k in ("real", "main_V_continue", "player_offsets_cont")}, indent=1))


if __name__ == "__main__":
    main()
