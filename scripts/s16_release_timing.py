"""Stage 10 (registered e507fa2): release timing against the closeout. Descriptive. Writes
out/s10/stage10.json and the figure. Test rows are dropped at load and asserted absent.
"""

import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, ROOT, load  # noqa: E402
from s4_make import OPEN_KNOTS, X2, shots_X  # noqa: E402
from vshoot2 import ns_basis  # noqa: E402


OUT = ROOT / "out" / "s10"
NB = 1000
NAMED = {201939: "Curry", 2544: "LeBron", 201935: "Harden", 202691: "Thompson", 200755: "Redick"}
RBINS = [(0.3, 0.7), (0.7, 0.9), (0.9, 1.1), (1.1, 1.5)]
RLAB = ["0.3-0.7", "0.7-0.9", "0.9-1.1", "1.1-1.5"]
REF = "0.9-1.1"


def frames() -> tuple[pd.DataFrame, pd.DataFrame, int]:
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    _, s = load()
    ms = pd.concat(
        [
            pd.read_csv(f, dtype={"game": str})
            for f in sorted((ROOT / "out/s5").glob("motion_shots_*.csv"))
        ]
    )
    s = s.merge(ms, on=["game", "eventnum"], how="left")
    assert not (s.split == "test").any() and not s.game.map(split).eq("test").any(), (
        "test rows present"
    )
    s["cs"] = (s.catch_to_shot.notna() & (s.catch_to_shot <= 1.5)).astype(int)
    base = s[
        s.reason.astype(str).str.startswith("ok")
        & s.jump.astype(bool)
        & (s.cs == 1)
        & (s.d_release >= 16)
        & (s.d_release <= 30)
        & s.sc_release.notna()
        & s.open_release_all.notna()
    ].copy()
    n0 = len(base)
    d = base[base.s_closing_pre.notna() & base.s_speed.notna() & base.s_n_def6.notna()].copy()
    d["rt"] = d.catch_to_shot.astype(float)
    d["v"] = d.s_closing_pre.clip(-15, 15)
    d["rbin"] = pd.cut(d.rt, [0.3, 0.7, 0.9, 1.1, 1.5], labels=RLAB, right=False)
    d.loc[d.rt == 1.5, "rbin"] = "1.1-1.5"  # right-closed at 1.5
    return s, d, n0 - len(d)


def ctrl(x: pd.DataFrame) -> np.ndarray:
    z = np.stack([(x.zone_release == q).to_numpy() for q in ("above_break3", "corner3")], 1).astype(
        float
    )
    return np.column_stack([ns_basis(x.d_release.to_numpy(float)), z])


def ols_slope(x: pd.DataFrame) -> float:
    X = np.column_stack([np.ones(len(x)), x.v.to_numpy(float), ctrl(x)])
    b = np.linalg.lstsq(X, x.rt.to_numpy(float), rcond=None)[0]
    return float(b[1])


def quart(x: pd.DataFrame, cuts: np.ndarray) -> dict[str, dict[str, float]]:
    q = np.digitize(x.v.to_numpy(float), cuts)  # 0..3, slowest closeout first
    out = {}
    for k in range(4):
        y = x[q == k]
        out[f"Q{k + 1}"] = {
            "n": len(y),
            "rt": y.rt.median() if len(y) else np.nan,
            "open": y.open_release_all.median() if len(y) else np.nan,
            "v": y.v.median() if len(y) else np.nan,
            "make": y.made.mean() if len(y) else np.nan,
        }
    return out


def rush(x: pd.DataFrame) -> dict[str, float]:
    y = x[x.rbin.notna()]
    op = y.open_release_all.clip(upper=30).to_numpy(float)
    Xn = np.column_stack(
        [
            ns_basis(op, OPEN_KNOTS),
            ns_basis(y.d_release.to_numpy(float)),
            np.stack(
                [(y.zone_release == q).to_numpy() for q in ("above_break3", "corner3")], 1
            ).astype(float),
            y.three.astype(float),
            y.v,
            y.s_speed.clip(0, 25),
            y.s_n_def6.clip(upper=3),
        ]
    )
    mu, sd = Xn.mean(0), Xn.std(0)
    sd[sd == 0] = 1
    Xn = (Xn - mu) / sd
    others = [b for b in RLAB if b != REF]
    D = np.stack([(y.rbin.astype(str) == b).to_numpy() for b in others], 1).astype(float)
    b = logit_fit(np.column_stack([np.ones(len(y)), Xn, D]), y.made.to_numpy(float))
    lin = b[0] + Xn @ b[1 : 1 + Xn.shape[1]]
    coef = dict(zip(others, b[1 + Xn.shape[1] :]))
    p_ref = expit(lin).mean()
    return {lab: float(expit(lin + coef.get(lab, 0.0)).mean() - p_ref) for lab in RLAB}


def stats(d: pd.DataFrame, cuts: np.ndarray) -> dict[str, Any]:
    lg = d[~d.shooter.isin(GATED)]
    out = {"lg_q": quart(lg, cuts), "lg_slope": ols_slope(lg)}
    vtop = lg[lg.v >= cuts[2]].v.median()
    out["vtop"] = float(vtop)
    out["space_preserved"] = -out["lg_slope"] * vtop
    out["ame"] = rush(lg)
    out["gain_07_11"] = (out["ame"]["0.9-1.1"] - out["ame"]["0.7-0.9"]) / 2
    out["gain_10_13"] = -out["ame"]["1.1-1.5"] / 3
    dec = np.quantile(lg.v, np.linspace(0, 1, 11)[1:-1])
    qd = np.digitize(lg.v.to_numpy(float), dec)
    out["deciles"] = [
        (float(lg.v[qd == k].median()), float(lg.rt[qd == k].median())) for k in range(10)
    ]
    for pid, nm in NAMED.items():
        x = d[d.shooter == pid]
        out[nm] = {
            "q": quart(x, cuts),
            "slope": ols_slope(x) if len(x) >= 100 else np.nan,
            "n": len(x),
            "v_med": float(x.v.median()) if len(x) else np.nan,
            "rt_med": float(x.rt.median()) if len(x) else np.nan,
        }
    return out


def open_slope(s: pd.DataFrame, d: pd.DataFrame) -> tuple[float, int, int]:
    """Attempt-2 make model refitted identically on league training jump shots; dP/dopen at release
    openness 4-6 ft.
    """
    lg = s[
        s.reason.astype(str).str.startswith("ok")
        & ~s.shooter.isin(GATED)
        & s.open_release_all.notna()
        & s.d_release.notna()
    ]
    tr = lg[lg.jump.astype(bool) & lg.sc_release.notna() & (lg.split == "train")]

    def fit_base(x: pd.DataFrame) -> tuple[StandardScaler, LogisticRegression]:
        sc_ = StandardScaler().fit(shots_X(x))
        return sc_, LogisticRegression(C=1.0, max_iter=5000).fit(
            sc_.transform(shots_X(x)), x.made.astype(int)
        )

    games = np.array(sorted(tr.game.unique()))
    perm = np.random.default_rng(5).permutation(len(games))
    fold = {g: i % 5 for i, g in zip(range(len(games)), games[perm])}
    f = tr.game.map(fold).to_numpy()
    oof = np.zeros(len(tr))
    for k in range(5):
        a_, m_ = fit_base(tr[f != k])
        oof[f == k] = m_.decision_function(a_.transform(shots_X(tr[f == k])))
    pl = LogisticRegression(C=1e6).fit(oof.reshape(-1, 1), tr.made.astype(int))
    A, B = float(pl.coef_[0, 0]), float(pl.intercept_[0])
    scl, mdl = fit_base(tr)
    pm = lambda Xr: expit(A * mdl.decision_function(scl.transform(Xr)) + B)
    w = d[~d.shooter.isin(GATED) & (d.open_release_all >= 4) & (d.open_release_all < 6)]
    up = pm(X2(w.d_release, w.zone_release, w.three, w.open_release_all + 0.5, w.cs, w.sc_release))
    dn = pm(X2(w.d_release, w.zone_release, w.three, w.open_release_all - 0.5, w.cs, w.sc_release))
    return float(np.mean(up - dn)), int(len(w)), int(len(tr))


def r4(v: float | None) -> float | None:
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 4)


def ci(a: list[float] | np.ndarray) -> list[float | None]:
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    return [r4(np.quantile(a, 0.025)), r4(np.quantile(a, 0.975))] if len(a) else [None, None]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s, d, dropped = frames()
    lg = d[~d.shooter.isin(GATED)]
    cuts = np.quantile(lg.v, [0.25, 0.5, 0.75])
    pt = stats(d, cuts)
    dpdo, n_w, n_tr = open_slope(s, d)
    games = np.array(sorted(d.game.unique()))
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in games}
    rng = np.random.default_rng(0)
    bs = []
    for _ in range(NB):
        ix = np.concatenate([gi[g] for g in rng.choice(games, len(games))])
        bs.append(stats(d.iloc[ix], cuts))
    get = lambda f: [f(b) for b in bs]
    loss = lambda st: dpdo * st["vtop"] * 0.1
    res = {
        "n_shots": int(len(d)),
        "n_league": int(len(lg)),
        "dropped_missing_motion": int(dropped),
        "n_rush_sample_league": int(lg.rbin.notna().sum()),
        "n_excluded_under_0p3s_league": int((lg.rt < 0.3).sum()),
        "closing_speed_quartile_cuts": [round(float(c), 3) for c in cuts],
        "league": {},
    }
    L = res["league"]
    L["by_quartile"] = {
        q: {
            "n": int(pt["lg_q"][q]["n"]),
            "median_closing_speed": r4(pt["lg_q"][q]["v"]),
            "median_release_time": [r4(pt["lg_q"][q]["rt"]), ci(get(lambda b: b["lg_q"][q]["rt"]))],
            "median_release_openness": [
                r4(pt["lg_q"][q]["open"]),
                ci(get(lambda b: b["lg_q"][q]["open"])),
            ],
            "make_rate": [r4(pt["lg_q"][q]["make"]), ci(get(lambda b: b["lg_q"][q]["make"]))],
        }
        for q in pt["lg_q"]
    }
    L["slope_s_per_ftps"] = [r4(pt["lg_slope"]), ci(get(lambda b: b["lg_slope"]))]
    L["top_quartile_median_closing_speed"] = [r4(pt["vtop"]), ci(get(lambda b: b["vtop"]))]
    L["space_preserved_ft"] = [r4(pt["space_preserved"]), ci(get(lambda b: b["space_preserved"]))]
    L["rush_ame_vs_0.9-1.1"] = {
        lab: [r4(pt["ame"][lab]), ci(get(lambda b, lab=lab: b["ame"][lab]))] for lab in RLAB
    }
    L["rush_bin_counts"] = {lab: int((lg.rbin.astype(str) == lab).sum()) for lab in RLAB}
    res["registered_reading"] = {
        "dP_dopen_attempt2_at_4to6ft": round(dpdo, 5),
        "n_shots_4to6ft": n_w,
        "attempt2_refit_train_shots": n_tr,
        "loss_per_0.1s": [r4(loss(pt)), ci(get(loss))],
        "gain_per_0.1s_0.7to1.1": [r4(pt["gain_07_11"]), ci(get(lambda b: b["gain_07_11"]))],
        "gain_minus_loss_0.7to1.1": [
            r4(pt["gain_07_11"] - loss(pt)),
            ci(get(lambda b: b["gain_07_11"] - loss(b))),
        ],
        "info_gain_per_0.1s_1.0to1.3": [r4(pt["gain_10_13"]), ci(get(lambda b: b["gain_10_13"]))],
    }
    res["players"] = {}
    for nm in NAMED.values():
        p = pt[nm]
        if p["n"] < 100:
            res["players"][nm] = {"n": p["n"], "status": "too thin"}
            continue
        res["players"][nm] = {
            "n": p["n"],
            "median_closing_speed": r4(p["v_med"]),
            "median_release_time": [r4(p["rt_med"]), ci(get(lambda b, nm=nm: b[nm]["rt_med"]))],
            "slope_s_per_ftps": [r4(p["slope"]), ci(get(lambda b, nm=nm: b[nm]["slope"]))],
            "by_quartile": {
                q: {
                    "n": int(p["q"][q]["n"]),
                    "median_release_time": [
                        r4(p["q"][q]["rt"]),
                        ci(get(lambda b, q=q, nm=nm: b[nm]["q"][q]["rt"])),
                    ],
                    "median_release_openness": [
                        r4(p["q"][q]["open"]),
                        ci(get(lambda b, q=q, nm=nm: b[nm]["q"][q]["open"])),
                    ],
                }
                for q in p["q"]
            },
        }
    dec_pt = pt["deciles"]
    res["league"]["deciles"] = [
        {
            "median_closing_speed": r4(v),
            "median_release_time": [r4(t), ci(get(lambda b, k=k: b["deciles"][k][1]))],
        }
        for k, (v, t) in enumerate(dec_pt)
    ]
    (OUT / "stage10.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.6))
    xs = [x["median_closing_speed"] for x in res["league"]["deciles"]]
    ys = [x["median_release_time"][0] for x in res["league"]["deciles"]]
    lo = [x["median_release_time"][1][0] for x in res["league"]["deciles"]]
    hi = [x["median_release_time"][1][1] for x in res["league"]["deciles"]]
    ax.errorbar(
        xs,
        ys,
        yerr=[np.array(ys) - lo, np.array(hi) - ys],
        fmt="o-",
        color="#57606a",
        capsize=3,
        label="league median by closing-speed decile",
    )
    cols = {
        "Curry": "#1f6feb",
        "LeBron": "#8250df",
        "Harden": "#d1242f",
        "Thompson": "#bf8700",
        "Redick": "#1a7f37",
    }
    for nm, p in res["players"].items():
        if "median_release_time" in p:
            ax.scatter(
                [p["median_closing_speed"]],
                [p["median_release_time"][0]],
                s=60,
                color=cols[nm],
                zorder=3,
            )
            ax.annotate(
                nm,
                (p["median_closing_speed"], p["median_release_time"][0]),
                xytext=(5, 4),
                textcoords="offset points",
                color=cols[nm],
                fontsize=9,
            )
    sp = res["league"]["space_preserved_ft"]
    ax.text(
        0.02,
        0.04,
        f"faster closeouts, quicker releases: slope {pt['lg_slope']:.3f} s per ft/s\n"
        f"space preserved at top-quartile closing speed: {sp[0]:.2f} ft "
        f"[{sp[1][0]:.2f}, {sp[1][1]:.2f}]",
        transform=ax.transAxes,
        fontsize=8,
        color="#24292f",
    )
    ax.set_xlabel("closing speed of the nearest defender, 0.5 s before release (ft/s)")
    ax.set_ylabel("catch to release (s)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.3)
    ax.set_title(
        "Catch-and-shoot jump shots, 16-30 ft, non-test games "
        "(release marker ~0.1 s late: compare, don't read levels)",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(OUT / "stage10_release_timing.svg")
    fig.savefig(OUT / "stage10_release_timing.png", dpi=120)


if __name__ == "__main__":
    main()
