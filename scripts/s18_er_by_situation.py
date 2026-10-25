"""Stage 12 (registered 0535882): the exchange rate by situation (5c's cuts), with Stage 8's partial pooling fitted
within each cut level. Writes out/s12/stage12.json and the figure."""

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
from s7_map import home_teams  # noqa: E402


OUT = ROOT / "out" / "s12"
NB = 1000
MINC, MINP = 150, 10
CUTS = {
    "margin": (
        lambda x: np.where(
            x.margin <= -5, "behind5+", np.where(x.margin >= 5, "ahead5+", "within5")
        ),
        ["behind5+", "within5", "ahead5+"],
    ),
    "period": (lambda x: np.where(x.quarter >= 4, "Q4+OT", "Q1-3"), ["Q1-3", "Q4+OT"]),
    "home": (lambda x: np.where(x.home, "home", "away"), ["home", "away"]),
    "source": (lambda x: x.source5.fillna("other").to_numpy(), ["pass", "other"]),
}
DIFFS = [
    ("margin", "behind5+", "ahead5+"),
    ("margin", "behind5+", "within5"),
    ("period", "Q4+OT", "Q1-3"),
    ("home", "home", "away"),
    ("source", "other", "pass"),
]


def player_fit(x):
    X, y = cov(x), (x.action == "shoot").to_numpy(float)
    keep = [0] + [j for j in range(1, X.shape[1]) if X[:, j].std() > 0]
    if 1 not in keep or 2 not in keep:
        return None
    X = X[:, keep]
    try:
        b = logit_fit(X, y)
        p = expit(X @ b)
        C = np.linalg.inv((X * (p * (1 - p))[:, None]).T @ X)
    except np.linalg.LinAlgError:  # counted as n_fit_failed
        return None
    if not (np.all(np.isfinite(b)) and np.all(np.isfinite(C))):
        return None
    return b[[1, 2]], C[np.ix_([1, 2], [1, 2])]


def pool(B, S, rng):
    n = len(B)

    def unpack(th):
        L = np.array([[np.exp(th[2]), 0], [th[3], np.exp(th[4])]])
        return th[:2], L @ L.T

    def nll(th):
        mu, T = unpack(th)
        tot = 0.0
        for i in range(n):
            V = T + S[i]
            r = B[i] - mu
            tot += 0.5 * (np.linalg.slogdet(V)[1] + r @ np.linalg.solve(V, r))
        return tot

    sd0 = np.std(B, 0)
    r = minimize(
        nll, np.r_[np.median(B, 0), np.log(sd0[0] / 2), 0.0, np.log(sd0[1] / 2)], method="L-BFGS-B"
    )
    mu, T = unpack(r.x)
    Ti = np.linalg.inv(T)
    post = []
    for i in range(n):
        Si = np.linalg.inv(S[i])
        Sig = np.linalg.inv(Ti + Si)
        m = Sig @ (Ti @ mu + Si @ B[i])
        dr = rng.multivariate_normal(m, Sig, 2000)
        flip = float(np.mean(np.sign(dr[:, 0]) != np.sign(m[0])))
        er = -dr[:, 1] / dr[:, 0]
        post.append(
            {
                "ER": float(-m[1] / m[0]),
                "ER_ci": [float(np.quantile(er, 0.025)), float(np.quantile(er, 0.975))],
                "flip": flip,
                "indet": bool(flip > 0.05),
            }
        )
    return mu, T, bool(r.success), post


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    d = unit(vs)
    assert not d.game.map(split).eq("test").any(), "test games present"
    mc = pd.concat(
        [
            pd.read_csv(f, dtype={"game": str})
            for f in sorted((ROOT / "out/s5").glob("motion_catches_*.csv"))
        ]
    )
    d = d.merge(mc[["game", "pid", "start", "source5"]], on=["game", "pid", "start"], how="left")
    hm = home_teams()
    d["home"] = [t == hm.get(g) for g, t in zip(d.game, d.team)]
    rng = np.random.default_rng(0)
    res = {
        "n_unit_catches": int(len(d)),
        "source_dropped": {s: int((d.source5 == s).sum()) for s in ("oreb", "inbound")},
        "cuts": {},
    }
    per = {}  # (cut, level) -> DataFrame of posteriors
    for cname, (fn, levels) in CUTS.items():
        lab = fn(d)
        res["cuts"][cname] = {}
        for lv in levels:
            sub = d[lab == lv]
            cnt = sub.groupby("pid").size()
            elig = sorted(cnt[cnt >= MINC].index)
            out = {"n_catches": int(len(sub)), "n_eligible": len(elig)}
            if len(elig) < MINP:
                out["status"] = "too thin to pool"
                res["cuts"][cname][lv] = out
                continue
            B, S, ids, failed = [], [], [], 0
            for pid in elig:
                f = player_fit(sub[sub.pid == pid])
                if f is None:
                    failed += 1
                    continue
                B.append(f[0])
                S.append(f[1])
                ids.append(pid)
            mu, T, ok, post = pool(np.array(B), np.array(S), rng)
            t = pd.DataFrame(post).assign(pid=ids, n=[int(cnt[p]) for p in ids])
            per[(cname, lv)] = t
            out.update(
                {
                    "n_fit": len(ids),
                    "n_fit_failed": failed,
                    "optimizer_converged": ok,
                    "mu_ER": round(float(-mu[1] / mu[0]), 3),
                    "Tau_sd": np.sqrt(np.diag(T)).round(5).tolist(),
                    "median_ER_all": round(float(t.ER.median()), 3),
                    "median_ER_determinate": round(float(t[~t.indet].ER.median()), 3),
                    "IQR_all": np.quantile(t.ER, [0.25, 0.75]).round(3).tolist(),
                    "share_indeterminate": round(float(t.indet.mean()), 4),
                    "gated": {},
                }
            )
            for pid, nm in GATED.items():
                r_ = t[t.pid == pid]
                out["gated"][nm] = (
                    {
                        "ER": round(float(r_.ER.iloc[0]), 3),
                        "ER_ci": [round(float(v), 3) for v in r_.ER_ci.iloc[0]],
                        "flip_share": round(float(r_.flip.iloc[0]), 4),
                        "indeterminate": bool(r_.indet.iloc[0]),
                        "n": int(r_.n.iloc[0]),
                    }
                    if len(r_)
                    else {"status": "too thin", "n": int(cnt.get(pid, 0))}
                )
            res["cuts"][cname][lv] = out
    # bootstrap over players, posteriors fixed
    brng = np.random.default_rng(0)
    lvl_bs = {k: [] for k in per}
    diff_bs = {f"{c}: {a} - {b}": [] for c, a, b in DIFFS if (c, a) in per and (c, b) in per}
    allp = {
        c: sorted(set().union(*[set(per[(c, lv)].pid) for lv in CUTS[c][1] if (c, lv) in per]))
        for c in CUTS
    }
    for _ in range(NB):
        meds = {}
        for c in CUTS:
            if not allp[c]:
                continue
            pick = pd.Series(brng.choice(allp[c], len(allp[c]))).value_counts()
            for lv in CUTS[c][1]:
                if (c, lv) not in per:
                    continue
                t = per[(c, lv)]
                w = t.pid.map(pick).fillna(0).astype(int).to_numpy()
                vals = np.repeat(t.ER.to_numpy(), w)
                meds[(c, lv)] = float(np.median(vals)) if len(vals) else np.nan
                lvl_bs[(c, lv)].append(meds[(c, lv)])
        for c, a, b in DIFFS:
            k = f"{c}: {a} - {b}"
            if k in diff_bs:
                diff_bs[k].append(meds[(c, a)] - meds[(c, b)])
    q = lambda x: [round(float(v), 3) for v in np.nanquantile(x, [0.025, 0.975])]
    for (c, lv), v in lvl_bs.items():
        res["cuts"][c][lv]["median_ER_all_ci"] = q(v)
    res["differences"] = {}
    for c, a, b in DIFFS:
        k = f"{c}: {a} - {b}"
        if k in diff_bs:
            res["differences"][k] = {
                "diff": round(
                    res["cuts"][c][a]["median_ER_all"] - res["cuts"][c][b]["median_ER_all"], 3
                ),
                "ci95": q(diff_bs[k]),
            }
        else:
            res["differences"][k] = "a level too thin to pool"
    (OUT / "stage12.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 4, figsize=(11, 3.6), sharey=True)
    for ax, (c, (_, levels)) in zip(axs, CUTS.items()):
        xs, ys, lo, hi, labs = [], [], [], [], []
        for i, lv in enumerate(levels):
            o = res["cuts"][c][lv]
            labs.append(f"{lv}\n(n={o.get('n_fit', o['n_eligible'])})")
            if "median_ER_all" in o:
                xs.append(i)
                ys.append(o["median_ER_all"])
                lo.append(o["median_ER_all_ci"][0])
                hi.append(o["median_ER_all_ci"][1])
        ax.errorbar(
            xs, ys, yerr=[np.array(ys) - lo, np.array(hi) - ys], fmt="o", color="#1f6feb", capsize=4
        )
        ax.set_xticks(range(len(levels)))
        ax.set_xticklabels(labs, fontsize=8)
        ax.set_xlim(-0.5, len(levels) - 0.5)
        ax.set_title(c, fontsize=10)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("median posterior exchange rate (s of clock per ft)")
    fig.suptitle(
        "Exchange rate by situation, shrunk within each cut (players with >= 150 catches in the level)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(OUT / "stage12_er_by_situation.svg")
    fig.savefig(OUT / "stage12_er_by_situation.png", dpi=120)


if __name__ == "__main__":
    main()
