"""Stage 9 analysis (registered 4d5a2f8): does the pass find the most open teammate? Writes out/s9/stage9.json and
the figure."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).parent))
from s4_data import GATED, ROOT  # noqa: E402


S9 = ROOT / "out" / "s9"
NB = 1000


def build():
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    t = pd.concat([pd.read_csv(f, dtype={"game": str}) for f in sorted(S9.glob("passes_*.csv"))])
    assert not t.game.map(split).eq("test").any(), "test games present"
    key = ["game", "passer", "start"]
    t = t.sort_values(key + ["open"], ascending=[True, True, True, False])
    mo = t.groupby(key).head(1).set_index(key)
    rc = t[t.is_receiver].set_index(key)
    d = (
        pd.DataFrame(
            {
                "recv_open": rc.open,
                "recv_dbask": rc.d_basket,
                "recv_pid": rc.teammate,
                "mo_open": mo.open,
                "mo_dbask": mo.d_basket,
                "mo_x": mo.x,
                "mo_y": mo.y,
                "bk": mo.bk,
                "mo_pid": mo.teammate,
            }
        )
        .dropna()
        .reset_index()
    )
    d["is_most_open"] = (d.recv_pid == d.mo_pid).astype(float)
    d["within1"] = ((d.mo_open - d.recv_open) <= 1.0).astype(float)
    d["deficit"] = d.mo_open - d.recv_open
    d["adv"] = d.mo_dbask - d.recv_dbask
    base_x = np.where(d.bk == 0, 0.0, 94.0)
    corner = ((d.mo_y - 25).abs() >= 22) & ((d.mo_x - base_x).abs() <= 14) & (d.mo_dbask > 6)
    d["mo_loc"] = np.where(
        d.mo_dbask <= 6,
        "rim",
        np.where(corner, "corner3", np.where(d.mo_dbask >= 30, "30+ft", "elsewhere")),
    )
    return d


def summ(x):
    out = {
        "n": len(x),
        "p_most_open": x.is_most_open.mean(),
        "p_within1": x.within1.mean(),
        "deficit_mean": x.deficit.mean(),
        "deficit_median": x.deficit.median(),
        "adv_mean": x.adv.mean(),
        "adv_median": x.adv.median(),
    }
    for loc in ("rim", "corner3", "30+ft", "elsewhere"):
        y = x[x.mo_loc == loc]
        out[f"{loc}_share"] = len(y) / max(len(x), 1)
        out[f"{loc}_p_most_open"] = y.is_most_open.mean() if len(y) else np.nan
        out[f"{loc}_deficit_mean"] = y.deficit.mean() if len(y) else np.nan
    return out


def main():
    d = build()
    drops = sum(json.loads(f.read_text())["dropped"] for f in S9.glob("drop_*.json"))
    groups = {"League": ~d.passer.isin(GATED), **{n: d.passer == p for p, n in GATED.items()}}
    games = np.array(sorted(d.game.unique()))
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in games}
    rng = np.random.default_rng(0)
    point = {k: summ(d[m]) for k, m in groups.items()}
    keys = [k for k in point["League"] if k != "n"]
    bs = {k: [] for k in groups}
    diff = []
    for _ in range(NB):
        ix = np.concatenate([gi[g] for g in rng.choice(games, len(games))])
        db = d.iloc[ix]
        sv = {}
        for k in groups:
            m = groups[k].to_numpy()[ix]
            s = summ(db[m])
            sv[k] = s
            bs[k].append([s[q] for q in keys])
        diff.append(sv["LeBron"]["p_most_open"] - sv["League"]["p_most_open"])
    res = {
        "n_passes_total": int(len(d)),
        "dropped_receiver_not_matched_or_no_basket": int(drops),
        "groups": {},
    }
    for k in groups:
        arr = np.array(bs[k], float)
        res["groups"][k] = {"n": int(point[k]["n"])}
        for i, q in enumerate(keys):
            v = point[k][q]
            lo, hi = np.nanquantile(arr[:, i], [0.025, 0.975])
            res["groups"][k][q] = [round(float(v), 4), [round(float(lo), 4), round(float(hi), 4)]]
    lo, hi = np.quantile(diff, [0.025, 0.975])
    res["lebron_minus_league_p_most_open"] = {
        "diff": round(float(point["LeBron"]["p_most_open"] - point["League"]["p_most_open"]), 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "registered_mde": 0.0554,
    }
    (S9 / "stage9.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lg = d[groups["League"]].sample(3000, random_state=0)
    lb = d[groups["LeBron"]]
    fig, ax = plt.subplots(figsize=(6.2, 6))
    ax.scatter(
        lg.mo_open.clip(upper=25),
        lg.recv_open.clip(upper=25),
        s=5,
        color="#8c959f",
        alpha=0.35,
        label="league (random 3,000 passes)",
    )
    ax.scatter(
        lb.mo_open.clip(upper=25),
        lb.recv_open.clip(upper=25),
        s=10,
        color="#8250df",
        alpha=0.8,
        label=f"LeBron ({len(lb)} passes)",
    )
    ax.plot([0, 25], [0, 25], color="black", lw=1)
    ax.set_xlabel("most open teammate's space at the pass (ft)")
    ax.set_ylabel("receiver's space at the pass (ft)")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 25)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    ax.set_title(
        "Dots on the line: the pass went to the most open man (snapshot at the pass)", fontsize=9
    )
    fig.tight_layout()
    fig.savefig(S9 / "stage9_pass_open.svg")
    fig.savefig(S9 / "stage9_pass_open.png", dpi=120)


if __name__ == "__main__":
    main()
