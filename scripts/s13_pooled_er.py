"""Stage 8 (registered 9cca730): exchange-rate map with partial pooling (empirical Bayes). Writes out/s8/stage8.json and
figures to out/s8/."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit


sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, ROOT, S4  # noqa: E402
from s6_clock import cov, unit  # noqa: E402


OUT = ROOT / "out" / "s8"
HBINS = [-np.inf, 0, 2, 4, 6, 8, 10, 15, np.inf]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    d = unit(vs)
    assert not d.game.map(split).eq("test").any(), "test games present"
    counts = d.groupby("pid").size()
    elig = sorted(counts[counts >= 300].index)
    est, S, ids, dropped_cols = [], [], [], []
    for pid in elig:
        x = d[d.pid == pid]
        X, y = cov(x), (x.action == "shoot").to_numpy(float)
        keep = [0] + [
            j for j in range(1, X.shape[1]) if X[:, j].std() > 0
        ]  # drop all-constant columns (e.g. no corner catches)
        assert 1 in keep and 2 in keep
        X = X[:, keep]
        b = logit_fit(X, y)
        p = expit(X @ b)
        C = np.linalg.inv((X * (p * (1 - p))[:, None]).T @ X)
        est.append(b[[1, 2]])
        S.append(C[np.ix_([1, 2], [1, 2])])
        ids.append(pid)
        dropped_cols.append(X.shape[1] < 8)
    B, S = np.array(est), np.array(S)
    n = len(B)

    def unpack(th: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mu = th[:2]
        L = np.array([[np.exp(th[2]), 0], [th[3], np.exp(th[4])]])
        return mu, L @ L.T

    def nll(th: np.ndarray) -> float:
        mu, T = unpack(th)
        tot = 0.0
        for i in range(n):
            V = T + S[i]
            r = B[i] - mu
            sign, ld = np.linalg.slogdet(V)
            tot += 0.5 * (ld + r @ np.linalg.solve(V, r))
        return tot

    mu0 = np.median(B, 0)
    sd0 = np.std(B, 0)
    r = minimize(nll, np.r_[mu0, np.log(sd0[0] / 2), 0.0, np.log(sd0[1] / 2)], method="L-BFGS-B")
    mu, T = unpack(r.x)
    Ti = np.linalg.inv(T)
    rng = np.random.default_rng(0)
    rows = []
    names = pd.read_csv(ROOT / "out/s6/heights.csv").set_index("pid").name
    for i, pid in enumerate(ids):
        Si = np.linalg.inv(S[i])
        Sig = np.linalg.inv(Ti + Si)
        m = Sig @ (Ti @ mu + Si @ B[i])
        dr = rng.multivariate_normal(m, Sig, 2000)
        flip = float(np.mean(np.sign(dr[:, 0]) != np.sign(m[0])))
        er_d = -dr[:, 1] / dr[:, 0]
        rows.append(
            {
                "pid": int(pid),
                "name": names.get(int(pid), str(pid)),
                "n": int(counts[pid]),
                "shots": int((d[d.pid == pid].action == "shoot").sum()),
                "raw_beta_clock": float(B[i, 0]),
                "raw_beta_open": float(B[i, 1]),
                "raw_ER": float(-B[i, 1] / B[i, 0]),
                "post_beta_clock": float(m[0]),
                "post_beta_open": float(m[1]),
                "ER": float(-m[1] / m[0]),
                "ER_ci": [float(np.quantile(er_d, 0.025)), float(np.quantile(er_d, 0.975))],
                "clock_sign_flip_share": flip,
                "unresolved": bool(flip > 0.05),
            }
        )
    t = pd.DataFrame(rows)
    unres = t.unresolved.mean()
    res = {
        "n_eligible": n,
        "mu_beta_clock_open": mu.round(5).tolist(),
        "Tau": T.round(6).tolist(),
        "Tau_sd": np.sqrt(np.diag(T)).round(5).tolist(),
        "Tau_corr": round(float(T[0, 1] / np.sqrt(T[0, 0] * T[1, 1])), 3),
        "mu_ER": round(float(-mu[1] / mu[0]), 3),
        "optimizer_converged": bool(r.success),
        "n_players_with_constant_columns_dropped": int(sum(dropped_cols)),
        "n_unresolved": int(t.unresolved.sum()),
        "share_unresolved": round(float(unres), 4),
    }
    res["median_ER_all"] = round(float(t.ER.median()), 3)
    res["median_ER_resolved_only"] = round(float(t[~t.unresolved].ER.median()), 3)
    res["league_number_for_page"] = (
        res["median_ER_resolved_only"]
        if unres < 0.10
        else {
            "with_unresolved": res["median_ER_all"],
            "without_unresolved": res["median_ER_resolved_only"],
        }
    )
    res["IQR_all"] = np.quantile(t.ER, [0.25, 0.75]).round(3).tolist()
    res["histogram_all"] = {
        str(k): int(v) for k, v in pd.cut(t.ER, HBINS).value_counts().sort_index().items()
    }
    t["pct"] = t.ER.rank(pct=True) * 100
    res["gated"] = {
        name: {
            k: (round(v, 3) if isinstance(v, float) else v)
            for k, v in t[t.pid == pid]
            .iloc[0][
                [
                    "ER",
                    "ER_ci",
                    "unresolved",
                    "clock_sign_flip_share",
                    "pct",
                    "n",
                    "shots",
                    "raw_ER",
                ]
            ]
            .to_dict()
            .items()
        }
        for pid, name in GATED.items()
        if (t.pid == pid).any()
    }
    # sanity: raw median over 5c's resolved players
    c5 = json.loads((ROOT / "checks/s5c.json").read_text())["map"]["all"]
    res5 = [x["pid"] for x in c5 if x["resolved"]]
    res["sanity_raw_median_5c_resolved"] = {
        "n": len(res5),
        "median_raw_ER": round(float(t[t.pid.isin(res5)].raw_ER.median()), 3),
        "5c_reported": 5.082,
    }
    srt = t.sort_values("ER")
    fmt = lambda x: [
        {
            "name": r_.name,
            "ER": round(r_.ER, 2),
            "ER_ci": [round(r_.ER_ci[0], 2), round(r_.ER_ci[1], 2)],
            "unresolved": r_.unresolved,
            "n": r_.n,
        }
        for r_ in x.itertuples()
    ]
    res["ten_highest"], res["ten_lowest"] = fmt(srt.tail(10)[::-1]), fmt(srt.head(10))
    res["all"] = t.drop(columns=["pct"]).to_dict("records")
    (OUT / "stage8.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: v for k, v in res.items() if k != "all"}, indent=1, default=float))
    # figure
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 6))
    ok = ~t.unresolved
    ax.scatter(
        t.post_beta_open[ok],
        -t.post_beta_clock[ok],
        s=14,
        color="#57606a",
        alpha=0.7,
        label="players (resolved)",
    )
    ax.scatter(
        t.post_beta_open[~ok],
        -t.post_beta_clock[~ok],
        s=14,
        facecolors="none",
        edgecolors="#57606a",
        alpha=0.7,
        label="clock-indeterminate",
    )
    xmax = max(t.post_beta_open.max(), 0.6) * 1.05
    xs = np.linspace(0, xmax, 50)
    for er in (2, 5, 7, 10):
        ax.plot(xs, xs / er, ls=":", lw=1, color="#8c959f")
        ax.text(xs[-1], xs[-1] / er, f"{er} s/ft", fontsize=8, color="#57606a", va="center")
    for pid, name, col in (
        (201939, "Curry", "#1f6feb"),
        (2544, "LeBron", "#8250df"),
        (201935, "Harden", "#d1242f"),
    ):
        rr = t[t.pid == pid]
        if len(rr):
            ax.scatter(rr.post_beta_open, -rr.post_beta_clock, s=60, color=col, zorder=3)
            ax.annotate(
                name,
                (rr.post_beta_open.iloc[0], -rr.post_beta_clock.iloc[0]),
                xytext=(5, 5),
                textcoords="offset points",
                color=col,
            )
    ax.scatter([mu[1]], [-mu[0]], marker="*", s=180, color="black", zorder=4, label="league μ")
    ax.set_xlabel("posterior β_open (log-odds per ft of space)")
    ax.set_ylabel("−posterior β_clock (log-odds per second run off)")
    ax.set_xlim(0, xmax)
    ax.set_ylim(bottom=min(0, (-t.post_beta_clock).min() * 1.1))
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    ax.set_title("Shrunk shooting slopes, every player with ≥ 300 catches at 16-30 ft", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "stage8_er_map.svg")
    fig.savefig(OUT / "stage8_er_map.png", dpi=120)


if __name__ == "__main__":
    main()
