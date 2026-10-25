"""Stage 3a choice model: pilot T, Fisher power, ideal-estimator power of the synthetic rule, synthetic recovery.
Registered 4a3a3d3. Real-data use is limited to the pilot T on train games; pilot c estimates are discarded.

  choice.py power    -> out/s3/power.json
  choice.py synth    -> out/s3/synth.json   (only players that proceed)
"""

import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parent.parent
S3 = ROOT / "out" / "s3"
PLAYERS = {"Curry": 201939, "LeBron": 2544, "Harden": 201935}
ZONES = ["rim", "mid", "above_break3", "corner3"]


def primary_model():
    dp = json.loads((ROOT / "checks/dp2_score.json").read_text())  # the registered retest decides
    return "fourway" if dp["passes"] else "binary"


D_MAX = 30.0  # scope rule: support of the shot model


def load_values():
    v = pd.read_csv(S3 / "values2.csv", dtype={"game": str})
    return v[v.d_basket <= D_MAX]


def design(df, model):
    """Return V (n x A), avail mask (n x A), observed action index y, action names. Last action is the reference."""
    if model == "fourway":
        acts = ["shoot", "drive", "pass", "hold"]
        V = df[["V_shoot", "V_drive", "V_pass", "V_hold"]].to_numpy(float)
        avail = np.ones_like(V, bool)
        avail[:, 1] = df.d_basket.to_numpy() >= 20
        y = df.action.map({a: i for i, a in enumerate(acts)}).to_numpy()
    else:
        acts = ["shoot", "continue"]
        V = df[["V_shoot", "V_continue"]].to_numpy(float)
        avail = np.ones_like(V, bool)
        y = np.where(df.action == "shoot", 0, 1)
    return V, avail, y, acts


def probs(V, avail, c, T):
    cc = np.r_[c, 0.0]
    u = (V - cc) / T
    u = np.where(avail, u, -np.inf)
    u -= u.max(1, keepdims=True)
    e = np.exp(u)
    return e / e.sum(1, keepdims=True)


def nll(theta, V, avail, y):
    c, T = theta[:-1], math.exp(theta[-1])
    p = probs(V, avail, c, T)
    return -np.sum(np.log(p[np.arange(len(y)), y] + 1e-300))


def fit(V, avail, y, k):
    x0 = np.r_[np.zeros(k), 0.0]
    r = minimize(nll, x0, args=(V, avail, y), method="BFGS")
    return r.x[:-1], math.exp(r.x[-1]), r


def fisher(V, avail, c, T, zone_idx=None, nz=0):
    """Fisher information in (c..., T). If zone_idx given, c_shoot is split by zone (secondary)."""
    n, A = V.shape
    k = A - 1
    P = (nz + k - 1 + 1) if zone_idx is not None else k + 1
    p = probs(V, avail, c, T) if zone_idx is None else None
    I = np.zeros((P, P))
    for i in range(n):
        if zone_idx is None:
            cc = np.r_[c, 0.0]
            pi = p[i]
            J = np.zeros((A, P))
            for a in range(k):
                J[a, a] = -1.0 / T
            J[:, -1] = -(V[i] - cc) / T**2
        else:
            cz = c[:nz]
            rest = c[nz:]
            cs = np.r_[cz[zone_idx[i]], rest, 0.0]
            u = np.where(avail[i], (V[i] - cs) / T, -np.inf)
            u -= u.max()
            pi = np.exp(u) / np.exp(u).sum()
            J = np.zeros((A, P))
            J[0, zone_idx[i]] = -1.0 / T
            for a in range(1, k):
                J[a, nz + a - 1] = -1.0 / T
            J[:, -1] = -(V[i] - cs) / T**2
        pi = np.where(avail[i], pi, 0.0)
        W = np.diag(pi) - np.outer(pi, pi)
        I += J.T @ W @ J
    return I


def power():
    model = primary_model()
    v = load_values()
    split = json.loads((ROOT / "checks/split.json").read_text())
    out = {"primary_model": model, "players": {}}
    for name, pid in PLAYERS.items():
        d = v[(v.pid == pid) & (v.split == "train")].copy()
        if model == "fourway":
            d = d[d.action.isin(["shoot", "drive", "pass", "hold"])]
        V, avail, y, acts = design(d, model)
        k = len(acts) - 1
        _, T_p, r = fit(V, avail, y, k)  # pilot: only T is kept; c estimates are discarded here
        del r
        n_games = split["per_player_counts"][name]["train"]
        rows = {}
        for cs in (-0.2, 0.0, 0.2):
            c = np.r_[cs, np.zeros(k - 1)]
            cov = np.linalg.inv(fisher(V, avail, c, T_p))
            se = np.sqrt(np.diag(cov))
            rows[f"c_shoot={cs:+.1f}"] = {
                "se_c": dict(zip([f"c_{a}" for a in acts[:-1]], se[:-1].round(4).tolist())),
                "se_T": round(float(se[-1]), 4),
                "mde80_c_shoot": round(float(2.80 * se[0]), 4),
            }
        mde = rows["c_shoot=+0.0"]["mde80_c_shoot"]
        proceed = mde <= 0.15
        zi = d.zone.map({z: i for i, z in enumerate(ZONES)}).to_numpy()
        try:
            Iz = fisher(V, avail, np.r_[np.zeros(4), np.zeros(k - 1)], T_p, zone_idx=zi, nz=4)
            sez = np.sqrt(np.diag(np.linalg.pinv(Iz)))[:4]
            zone_se = {z: round(float(s), 4) for z, s in zip(ZONES, sez)}
        except np.linalg.LinAlgError:
            zone_se = None
        out["players"][name] = {
            "n_train_catches": int(len(d)),
            "n_train_games": n_games,
            "actions": d.action.value_counts().to_dict(),
            "pilot_T": round(T_p, 4),
            "fisher": rows,
            "mde80_at_c0": mde,
            "proceed": bool(proceed),
            "games_needed_if_underpowered": None
            if proceed
            else int(math.ceil(n_games * (mde / 0.15) ** 2)),
            "secondary_se_c_shoot_by_zone": zone_se,
            "zone_counts_train": d.zone.value_counts().to_dict(),
        }
    (S3 / "power.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def settings(model, T_p):
    if model == "fourway":
        return {
            "S1": (np.array([-0.2, 0.1, -0.1]), T_p),
            "S2": (np.zeros(3), T_p),
            "S3": (np.array([0.2, -0.1, 0.1]), 1.5 * T_p),
        }
    return {
        "S1": (np.array([-0.2]), T_p),
        "S2": (np.zeros(1), T_p),
        "S3": (np.array([0.2]), 1.5 * T_p),
    }


def synth():
    pw = json.loads((S3 / "power.json").read_text())
    model = pw["primary_model"]
    v = load_values()
    out = {"primary_model": model, "players": {}}
    for name, pid in PLAYERS.items():
        info = pw["players"][name]
        if not info["proceed"]:
            out["players"][name] = {"skipped": "underpowered"}
            continue
        d = v[(v.pid == pid) & (v.split == "train")]
        if model == "fourway":
            d = d[d.action.isin(["shoot", "drive", "pass", "hold"])]
        V, avail, _, acts = design(d, model)
        k = len(acts) - 1
        names = [f"c_{a}" for a in acts[:-1]] + ["T"]
        res = {"settings": {}}
        # ideal-estimator power of the pass rule, per setting
        rng = np.random.default_rng(7)
        for sname, (c0, T0) in settings(model, info["pilot_T"]).items():
            cov = np.linalg.inv(fisher(V, avail, c0, T0))
            lim = 2.576 * np.sqrt(np.diag(cov))
            draws = rng.multivariate_normal(np.zeros(len(lim)), cov, 100_000)
            p_run = float(np.mean(np.all(np.abs(draws) <= lim, 1)))
            p_rule = float(
                sum(math.comb(20, j) * p_run**j * (1 - p_run) ** (20 - j) for j in range(18, 21))
            )
            runs = []
            for seed in range(100, 120):
                g = np.random.default_rng(seed)
                P = probs(V, avail, c0, T0)
                ysim = (P.cumsum(1) > g.random((len(P), 1))).argmax(1)
                ch, Th, _ = fit(V, avail, ysim, k)
                est = np.r_[ch, Th]
                err = est - np.r_[c0, T0]
                Vimm = V.copy()
                Vimm[:, 0] = d.V_shoot_imm.to_numpy(float)
                ci, Ti, _ = fit(Vimm, avail, ysim, k)
                runs.append(
                    {
                        "seed": seed,
                        "c_shoot_immediate_scale_fit": round(float(ci[0]), 4),
                        "immediate_scale_bias": round(float(ci[0] - c0[0]), 4),
                        "estimate": dict(zip(names, est.round(4).tolist())),
                        "error": dict(zip(names, err.round(4).tolist())),
                        "within": dict(zip(names, (np.abs(err) <= lim).tolist())),
                        "pass": bool(np.all(np.abs(err) <= lim)),
                    }
                )
            npass = sum(r["pass"] for r in runs)
            ib = np.array([r["immediate_scale_bias"] for r in runs])
            res["settings"][sname] = {
                "true": dict(zip(names, np.r_[c0, T0].round(4).tolist())),
                "limits": dict(zip(names, lim.round(4).tolist())),
                "ideal_p_run_pass": round(p_run, 4),
                "ideal_p_rule_pass": round(p_rule, 4),
                "runs_passed": npass,
                "setting_passes": npass >= 18,
                "immediate_scale_bias_mean_sd": [
                    round(float(ib.mean()), 4),
                    round(float(ib.std()), 4),
                ],
                "runs": runs,
            }
        res["passes"] = all(s["setting_passes"] for s in res["settings"].values())
        out["players"][name] = res
    (S3 / "synth.json").write_text(json.dumps(out, indent=1))
    for n, r in out["players"].items():
        if "settings" in r:
            print(
                n,
                {
                    s: (x["runs_passed"], x["ideal_p_rule_pass"], x["limits"])
                    for s, x in r["settings"].items()
                },
                "PASS" if r["passes"] else "FAIL",
            )
        else:
            print(n, r)


if __name__ == "__main__":
    {"power": power, "synth": synth}[sys.argv[1]]()
