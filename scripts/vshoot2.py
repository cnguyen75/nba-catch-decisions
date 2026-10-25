"""V_shoot fix (registered 4a1b93d): spline/shot-clock/interaction logistic + Platt map from 5-fold
game-grouped out-of-fold predictions; scored ONCE on validation under the powered calibration
rule. Also g(zone). Writes out/s3/vshoot2.json and out/s3/vshoot2_model.npz.
"""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


sys.path.insert(0, str(Path(__file__).parent))
from values import GATED, ZONES, load  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
S3 = ROOT / "out" / "s3"
KNOTS = np.array([0.0, 4.0, 10.0, 18.0, 23.75, 28.0, 47.0])


def ns_basis(x: np.ndarray, k: np.ndarray = KNOTS) -> np.ndarray:
    """Natural cubic spline basis (ESL 5.4): N1 = x, N_{j+2} = d_j - d_{K-1}, j = 1..K-2."""
    K = len(k)

    def d(j: int) -> np.ndarray:
        return (np.clip(x - k[j], 0, None) ** 3 - np.clip(x - k[K - 1], 0, None) ** 3) / (
            k[K - 1] - k[j]
        )

    cols = [x] + [d(j) - d(K - 2) for j in range(K - 2)]
    return np.column_stack(cols)


def X(df: pd.DataFrame) -> np.ndarray:
    dist = df.d_basket.to_numpy(float)
    z = np.stack([(df.zone == q).to_numpy() for q in ZONES], 1).astype(float)
    lo = np.log1p(df.open_catch.clip(upper=30).to_numpy(float))
    three = df.points3.to_numpy(float)
    sc = df.shot_clock.to_numpy(float)
    return np.column_stack([ns_basis(dist), z, lo, lo * dist / 10.0, lo * three, sc, sc**2 / 100.0])


def fit_base(df: pd.DataFrame) -> tuple[StandardScaler, LogisticRegression]:
    sc = StandardScaler().fit(X(df))
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=5000).fit(
        sc.transform(X(df)), df.made.astype(int)
    )
    return sc, lr


def logit_of(sc: StandardScaler, lr: LogisticRegression, df: pd.DataFrame) -> np.ndarray:
    return lr.decision_function(sc.transform(X(df)))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> tuple[float, list[dict[str, float]]]:
    q = pd.qcut(p + np.arange(len(p)) * 1e-12, bins, labels=False)
    t = (
        pd.DataFrame({"p": p, "y": y, "b": q})
        .groupby("b")
        .agg(n=("y", "size"), pred=("p", "mean"), obs=("y", "mean"))
    )
    return float((t.n / t.n.sum() * (t.pred - t.obs).abs()).sum()), t.round(
        4
    ).reset_index().to_dict("records")


def main() -> None:
    c = load()
    use = c[(c.excluded == "") & (c.action == "shoot") & c.made.notna() & c.shot_clock.notna()]
    league = use[~use.pid.isin(GATED)]
    tr, va = league[league.split == "train"], league[league.split == "validation"]
    # 5-fold game-grouped OOF predictions (seed 5)
    games = np.array(sorted(tr.game.unique()))
    perm = np.random.default_rng(5).permutation(len(games))
    fold_of = {g: i % 5 for i, g in zip(range(len(games)), games[perm], strict=False)}
    f = tr.game.map(fold_of).to_numpy()
    oof = np.zeros(len(tr))
    for k in range(5):
        sc, lr = fit_base(tr[f != k])
        oof[f == k] = logit_of(sc, lr, tr[f == k])
    platt = LogisticRegression(C=1e6, solver="lbfgs").fit(oof.reshape(-1, 1), tr.made.astype(int))
    a, b = float(platt.coef_[0, 0]), float(platt.intercept_[0])
    sc, lr = fit_base(tr)

    def predict(df: pd.DataFrame) -> np.ndarray:
        return 1 / (1 + np.exp(-(a * logit_of(sc, lr, df) + b)))

    pv = predict(va)
    yv = va.made.to_numpy(float)
    e, tab = ece(pv, yv)
    rng = np.random.default_rng(0)
    null = np.array([ece(pv, (rng.random(len(pv)) < pv).astype(float))[0] for _ in range(5000)])
    p95 = float(np.quantile(null, 0.95))
    res = {
        "n_train": int(len(tr)),
        "n_val": int(len(va)),
        "platt": {"a": a, "b": b},
        "ece_val": round(e, 4),
        "null_median": round(float(np.median(null)), 4),
        "null_p95": round(p95, 4),
        "passes": bool(e <= p95),
        "p_null_ge_obs": round(float(np.mean(null >= e)), 4),
        "decile_table_val": tab,
        "brier_val": round(float(np.mean((pv - yv) ** 2)), 4),
        "val_base_rate": round(float(yv.mean()), 4),
    }
    # ---- g(zone) from league train shoot-now catches
    trs = tr.copy()
    trs["shot_pts"] = trs.made * (2 + trs.points3)
    g = (trs.poss_points - trs.shot_pts).groupby(trs.zone).agg(["mean", "size", "sem"])
    res["g_zone"] = {
        z: {
            "g": round(float(g.loc[z, "mean"]), 4),
            "n": int(g.loc[z, "size"]),
            "se": round(float(g.loc[z, "sem"]), 4),
        }
        for z in ZONES
        if z in g.index
    }
    np.savez(
        S3 / "vshoot2_model.npz",
        mean=sc.mean_,
        scale=sc.scale_,
        coef=lr.coef_,
        intercept=lr.intercept_,
        a=a,
        b=b,
    )
    (S3 / "vshoot2.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "decile_table_val"}, indent=1))
    print(pd.DataFrame(tab).to_string())


if __name__ == "__main__":
    main()
