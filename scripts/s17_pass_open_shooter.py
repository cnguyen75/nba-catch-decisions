"""Stage 11 (registered 8f1379f): Stage 9 with a deliberate-choice baseline -- candidates are shooters (>= 50 jump-shot
attempts, non-test games) within 30 ft of the basket and beyond 6 ft. Writes out/s11/stage11.json and the figure."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).parent))
from s4_data import GATED, ROOT, load  # noqa: E402


S9 = ROOT / "out" / "s9"
OUT = ROOT / "out" / "s11"
NB = 1000


def shooters():
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    _, s = load()
    assert not (s.split == "test").any() and not s.game.map(split).eq("test").any(), (
        "test rows present"
    )
    js = s[s.reason.astype(str).str.startswith("ok") & s.jump.fillna(False).astype(bool)]
    n = js.groupby("shooter").size()
    return set(int(p) for p in n[n >= 50].index), int(len(n)), int((n >= 50).sum())


def build(shoot):
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    t = pd.concat([pd.read_csv(f, dtype={"game": str}) for f in sorted(S9.glob("passes_*.csv"))])
    assert not t.game.map(split).eq("test").any(), "test games present"
    key = ["game", "passer", "start"]
    n_all = t.groupby(key).ngroups
    rc = t[t.is_receiver].set_index(key)
    t["cand"] = (t.d_basket <= 30) & (t.d_basket > 6) & t.teammate.isin(shoot)
    nc = t.groupby(key).cand.sum()
    c = t[t.cand].sort_values(key + ["open"], ascending=[True, True, True, False])
    mo = c.groupby(key).head(1).set_index(key)
    d = pd.DataFrame(
        {
            "n_cand": nc,
            "recv_open": rc.open,
            "recv_dbask": rc.d_basket,
            "recv_pid": rc.teammate,
            "recv_cand": t[t.is_receiver].set_index(key).cand,
            "mo_open": mo.open,
            "mo_dbask": mo.d_basket,
            "mo_x": mo.x,
            "mo_y": mo.y,
            "bk": mo.bk,
            "mo_pid": mo.teammate,
        }
    )
    d = d[d.recv_open.notna()]
    n_excl = int((d.n_cand < 2).sum())
    d = d[d.n_cand >= 2].reset_index()
    d["is_mo"] = (d.recv_pid == d.mo_pid).astype(float)
    d["deficit"] = d.mo_open - d.recv_open
    d["gain"] = d.mo_dbask - d.recv_dbask
    d["base"] = 1.0 / d.n_cand
    base_x = np.where(d.bk == 0, 0.0, 94.0)
    d["corner"] = ((d.mo_y - 25).abs() >= 22) & ((d.mo_x - base_x).abs() <= 14)
    return d, n_all, n_excl


def summ(x):
    out = {
        "p_most_open_cand": x.is_mo.mean(),
        "baseline": x.base.mean(),
        "recv_is_cand": x.recv_cand.astype(float).mean(),
        "deficit_mean": x.deficit.mean(),
        "deficit_median": x.deficit.median(),
        "gain_mean": x.gain.mean(),
        "gain_median": x.gain.median(),
    }
    for nm, m in (("corner3", x.corner), ("elsewhere", ~x.corner)):
        y = x[m]
        out[f"{nm}_share"] = len(y) / max(len(x), 1)
        out[f"{nm}_p_most_open_cand"] = y.is_mo.mean() if len(y) else np.nan
        out[f"{nm}_deficit_mean"] = y.deficit.mean() if len(y) else np.nan
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shoot, n_shooters_any, n_shooters = shooters()
    d, n_all, n_excl = build(shoot)
    groups = {"League": ~d.passer.isin(GATED), **{n: d.passer == p for p, n in GATED.items()}}
    games = np.array(sorted(d.game.unique()))
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in games}
    rng = np.random.default_rng(0)
    point = {k: summ(d[m]) for k, m in groups.items()}
    keys = list(point["League"])
    bs = {k: [] for k in groups}
    diff = []
    for _ in range(NB):
        ix = np.concatenate([gi[g] for g in rng.choice(games, len(games))])
        db = d.iloc[ix]
        sv = {}
        for k in groups:
            s = summ(db[groups[k].to_numpy()[ix]])
            sv[k] = s
            bs[k].append([s[q] for q in keys])
        diff.append(sv["LeBron"]["p_most_open_cand"] - sv["League"]["p_most_open_cand"])
    n_lb = int(groups["LeBron"].sum())
    res = {
        "n_passes_stage9": int(n_all),
        "n_excluded_fewer_than_2_candidates": n_excl,
        "n_passes_included": int(len(d)),
        "n_shooters_ge50_jump_attempts": n_shooters,
        "n_players_with_any_jump_attempt": n_shooters_any,
        "groups": {},
    }
    for k in groups:
        arr = np.array(bs[k], float)
        res["groups"][k] = {"n": int(groups[k].sum())}
        for i, q in enumerate(keys):
            lo, hi = np.nanquantile(arr[:, i], [0.025, 0.975])
            res["groups"][k][q] = [
                round(float(point[k][q]), 4),
                [round(float(lo), 4), round(float(hi), 4)],
            ]
    lo, hi = np.quantile(diff, [0.025, 0.975])
    res["lebron_minus_league_p_most_open_cand"] = {
        "diff": round(
            float(point["LeBron"]["p_most_open_cand"] - point["League"]["p_most_open_cand"]), 4
        ),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "mde_registered_at_n639": 0.0554,
        "n_lebron_realized": n_lb,
        "mde_at_realized_n": round(2.8 * 0.5 / np.sqrt(n_lb), 4),
    }
    (OUT / "stage11.json").write_text(json.dumps(res, indent=1))
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
    ax.set_xlabel("most open candidate's space at the pass (ft)")
    ax.set_ylabel("receiver's space at the pass (ft)")
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 25)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    ax.set_title(
        "Candidates = shooters 6-30 ft from the basket; on the line: pass to the most open one",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(OUT / "stage11_pass_open_shooter.svg")
    fig.savefig(OUT / "stage11_pass_open_shooter.png", dpi=120)


if __name__ == "__main__":
    main()
