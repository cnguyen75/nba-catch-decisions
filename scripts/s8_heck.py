"""Stage 5b (registered 40ba56a): bivariate probit with sample selection.

s8_heck.py excl            step 1: exclusion strength (and saves true params for synthetic)
s8_heck.py synth <rho>     step 2: 20 seeds at rho (0, 0.3, 0.6)
s8_heck.py real            steps 3-5 (only after steps 1-2 pass)
"""

import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import log_ndtr, ndtr


sys.path.insert(0, str(Path(__file__).parent))
from s4_data import GATED, ROOT, S4  # noqa: E402


S5 = ROOT / "out" / "s5"
GLx, GLw = np.polynomial.legendre.leggauss(20)


def build_frame(split: str) -> tuple[pd.DataFrame, int]:
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    mc = pd.concat(
        [pd.read_csv(f, dtype={"game": str}) for f in sorted(S5.glob("motion_catches_*.csv"))]
    )
    d = (
        vs[~vs.pid.isin(GATED) & (vs.split == split)]
        if split != "gated"
        else vs[vs.pid.isin(GATED)]
    )
    d = d[
        (d.d_basket >= 16)
        & (d.d_basket <= 30)
        & d.shot_clock.notna()
        & d.action.isin(["shoot", "continue"])
    ]
    d = d.merge(mc, on=["game", "pid", "start"], how="inner")
    d = d[d.closing_pre.notna() & d.closing_post.notna() & d.catcher_speed.notna()]
    d["s"] = (d.action == "shoot").astype(int)
    n_drop = int(((d.s == 1) & d.made.isna()).sum())
    d = d[~((d.s == 1) & d.made.isna())].copy()
    d["y"] = d.made.fillna(0).astype(int)
    return d.reset_index(drop=True), n_drop


def X_out(d: pd.DataFrame) -> np.ndarray:
    dd = d.d_basket.to_numpy(float) / 10
    sp = d.catcher_speed.clip(0, 25).to_numpy(float)
    return np.column_stack(
        [
            dd,
            dd**2,
            (d.zone == "above_break3").to_numpy(float),
            (d.zone == "corner3").to_numpy(float),
            d.open_catch.clip(upper=15),
            d.open_cf.clip(upper=15),
            d.shot_clock,
            d.closing_pre.clip(-15, 15),
            d.closing_post.clip(-15, 15),
            sp,
            (sp < 3).astype(float),
            d.n_def6.clip(upper=3),
            d.flight_time.clip(0, 3),
            d.flight_dist.clip(0, 60),
        ]
    ).astype(float)


def X_excl(d: pd.DataFrame) -> np.ndarray:
    src = d.source5.fillna("other")
    return np.column_stack(
        [
            d.best_tm_open.clip(upper=20),
            d.margin.clip(-20, 20),
            (src == "oreb"),
            (src == "inbound"),
            (src == "other"),
        ]
    ).astype(float)


class Std:
    def __init__(self, X: np.ndarray) -> None:
        self.m, self.s = X.mean(0), X.std(0)
        self.s[self.s == 0] = 1

    def __call__(self, X: np.ndarray) -> np.ndarray:
        return np.column_stack([np.ones(len(X)), (X - self.m) / self.s])


def probit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    def f(b: np.ndarray) -> tuple[float, np.ndarray]:
        xb = X @ b
        ll = y * log_ndtr(xb) + (1 - y) * log_ndtr(-xb)
        lam1 = np.exp(-0.5 * xb**2 - 0.5 * np.log(2 * np.pi) - log_ndtr(xb))
        lam0 = np.exp(-0.5 * xb**2 - 0.5 * np.log(2 * np.pi) - log_ndtr(-xb))
        g = X.T @ (y * lam1 - (1 - y) * lam0)
        return -ll.sum(), -g

    r = minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B")
    return r.x, -r.fun


def phi2(a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    """Bivariate normal CDF via Gauss-Legendre in the correlation (vectorized)."""
    base = ndtr(a) * ndtr(b)
    if abs(r) < 1e-12:
        return base
    t = (GLx + 1) * r / 2
    w = GLw * r / 2
    a_, b_ = a[:, None], b[:, None]
    dens = np.exp(-(a_**2 - 2 * a_ * b_ * t + b_**2) / (2 * (1 - t**2))) / (
        2 * np.pi * np.sqrt(1 - t**2)
    )
    return base + dens @ w


def ll_vec(
    theta: np.ndarray, Z: np.ndarray, X: np.ndarray, s: np.ndarray, y: np.ndarray
) -> np.ndarray:
    kz = Z.shape[1]
    g, b, rho = theta[:kz], theta[kz:-1], np.tanh(theta[-1])
    zg = Z @ g
    out = np.empty(len(s))
    m0 = s == 0
    out[m0] = log_ndtr(-zg[m0])
    m11 = (s == 1) & (y == 1)
    m10 = (s == 1) & (y == 0)
    xb = X @ b
    out[m11] = np.log(np.clip(phi2(zg[m11], xb[m11], rho), 1e-300, None))
    out[m10] = np.log(np.clip(phi2(zg[m10], -xb[m10], -rho), 1e-300, None))
    return out


def fit_heck(
    Z: np.ndarray, X: np.ndarray, s: np.ndarray, y: np.ndarray, g0: np.ndarray, b0: np.ndarray
) -> tuple[np.ndarray, dict[str, object], np.ndarray]:
    th0 = np.r_[g0, b0, 0.0]
    f = lambda th: -ll_vec(th, Z, X, s, y).sum()
    r = minimize(f, th0, method="L-BFGS-B", options={"maxiter": 500})
    th = r.x
    h = 1e-4
    S = np.zeros((len(s), len(th)))
    for k in range(len(th)):
        e = np.zeros(len(th))
        e[k] = h
        S[:, k] = (ll_vec(th + e, Z, X, s, y) - ll_vec(th - e, Z, X, s, y)) / (2 * h)
    cov = np.linalg.pinv(S.T @ S)
    a, se_a = th[-1], np.sqrt(cov[-1, -1])
    return (
        th,
        {
            "rho": float(np.tanh(a)),
            "rho_ci": [float(np.tanh(a - 1.96 * se_a)), float(np.tanh(a + 1.96 * se_a))],
            "se_rho_delta": float(se_a * (1 - np.tanh(a) ** 2)),
            "converged": bool(r.success),
            "nit": int(r.nit),
            "ll": float(-r.fun),
        },
        cov,
    )


def cf_rate(theta: np.ndarray, Z: np.ndarray, X: np.ndarray, s: np.ndarray) -> float:
    kz = Z.shape[1]
    g, b, rho = theta[:kz], theta[kz:-1], np.tanh(theta[-1])
    m0 = s == 0
    zg, xb = Z[m0] @ g, X[m0] @ b
    return float(np.mean(phi2(xb, -zg, -rho) / ndtr(-zg)))


def design(
    d: pd.DataFrame, sx: Std | None = None, sz: Std | None = None
) -> tuple[np.ndarray, np.ndarray, Std, Std]:
    Xo = X_out(d)
    Xz = np.column_stack([Xo, X_excl(d)])
    sx = sx or Std(Xo)
    sz = sz or Std(Xz)
    return sx(Xo), sz(Xz), sx, sz


def excl() -> None:
    d, nd = build_frame("train")
    X, Z, sx, sz = design(d)
    s, y = d.s.to_numpy(float), d.y.to_numpy(float)
    g_full, ll_full = probit(Z, s)
    g_res, ll_res = probit(X, s)
    LR = 2 * (ll_full - ll_res)
    b_naive, _ = probit(X[s == 1], y[s == 1])
    res = {
        "n": int(len(d)),
        "n_shoot": int(s.sum()),
        "made_rate_shots": round(float(y[s == 1].mean()), 4),
        "shoot_dropped_no_outcome": nd,
        "LR": round(float(LR), 2),
        "df": 5,
        "LR_per_df": round(float(LR / 5), 2),
        "partial_pseudo_R2": round(float(1 - ll_full / ll_res), 5),
        "threshold_LR_per_df": 10,
        "passes": bool(LR / 5 >= 10),
        "excluded_coefs_std": dict(
            zip(
                ["best_tm_open", "margin", "oreb", "inbound", "other"],
                g_full[-5:].round(4).tolist(),
            )
        ),
    }
    np.savez(S5 / "heck_true.npz", g=g_full, b=b_naive)
    (S5 / "s5b_excl.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def synth(rho: float) -> None:
    d, _ = build_frame("train")
    X, Z, _, _ = design(d)
    t = np.load(S5 / "heck_true.npz")
    g, b = t["g"], t["b"]
    base = {0.0: 500, 0.3: 600, 0.6: 700}[rho]
    zg, xb = Z @ g, X @ b
    runs = []
    for seed in range(base, base + 20):
        t0 = time.time()
        r = np.random.default_rng(seed)
        u = r.standard_normal(len(d))
        e = rho * u + np.sqrt(1 - rho**2) * r.standard_normal(len(d))
        s = (zg + u > 0).astype(float)
        y = (xb + e > 0).astype(float) * s
        g0, _ = probit(Z, s)
        b0, _ = probit(X[s == 1], y[s == 1])
        th, info, _ = fit_heck(Z, X, s, y, g0, b0)
        m0 = s == 0
        cf_true = float(np.mean(phi2(xb[m0], -zg[m0], -rho) / ndtr(-zg[m0])))
        cf_est = cf_rate(th, Z, X, s)
        cf_naive = float(np.mean(ndtr(X[m0] @ b0)))
        runs.append(
            {
                "seed": seed,
                **{
                    k: (round(v, 4) if isinstance(v, float) else v)
                    for k, v in info.items()
                    if k != "ll"
                },
                "rho_ci": [round(x, 4) for x in info["rho_ci"]],
                "covers": bool(info["rho_ci"][0] <= rho <= info["rho_ci"][1]),
                "cf_true": round(cf_true, 4),
                "cf_est": round(cf_est, 4),
                "cf_err": round(abs(cf_est - cf_true), 4),
                "cf_naive_err": round(abs(cf_naive - cf_true), 4),
                "shoot_rate": round(float(s.mean()), 3),
                "sec": round(time.time() - t0, 1),
            }
        )
        print(json.dumps(runs[-1]), flush=True)
    out = {
        "rho": rho,
        "covers": sum(x["covers"] for x in runs),
        "cf_within_0.03": sum(x["cf_err"] <= 0.03 for x in runs),
        "mean_se_rho": round(float(np.mean([x["se_rho_delta"] for x in runs])), 4),
        "runs": runs,
    }
    out["passes"] = bool(out["covers"] >= 18 and out["cf_within_0.03"] >= 18)
    (S5 / f"s5b_synth_{rho}.json").write_text(json.dumps(out, indent=1))
    print("SUMMARY", {k: v for k, v in out.items() if k != "runs"})


if __name__ == "__main__":
    {"excl": excl, "synth": lambda: synth(float(sys.argv[2]))}[sys.argv[1]]()
