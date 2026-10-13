"""Stage 5c (registered f391697): league exchange-rate map and within-player variation. Writes out/s5/s5c.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, ROOT, S4  # noqa: E402
from s6_clock import cov, unit  # noqa: E402

S5 = ROOT / "out" / "s5"
NB = 1000


def er_boot(d, seed):
    X, y = cov(d), (d.action == "shoot").to_numpy(float)
    b = logit_fit(X, y)
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in d.game.unique()}
    gl = list(gi)
    r = np.random.default_rng(seed)
    bs = []
    for _ in range(NB):
        ix = np.concatenate([gi[g] for g in r.choice(gl, len(gl))])
        try:
            bb = logit_fit(X[ix], y[ix])
        except np.linalg.LinAlgError:
            continue
        bs.append((bb[1], bb[2]))
    bs = np.array(bs)
    er_bs = -bs[:, 1] / bs[:, 0]
    cc = np.quantile(bs[:, 0], [.025, .975])
    return {"n": int(len(d)), "shots": int(y.sum()), "beta_clock": round(float(b[1]), 4), "beta_clock_ci": cc.round(4).tolist(),
            "beta_open": round(float(b[2]), 4), "ER": round(float(-b[2] / b[1]), 3),
            "ER_ci": np.quantile(er_bs[np.isfinite(er_bs)], [.025, .975]).round(3).tolist(),
            "resolved": bool(cc[1] < 0 or cc[0] > 0)}


def home_teams():
    p = pd.read_csv(ROOT.parent / "nba-tracking" / "pbp" / "2015-16_pbp.csv", dtype={"GAME_ID": str},
                    usecols=["GAME_ID", "HOMEDESCRIPTION", "PLAYER1_TEAM_ID"])
    h = p[p.HOMEDESCRIPTION.notna() & p.PLAYER1_TEAM_ID.notna()]
    return h.groupby("GAME_ID").PLAYER1_TEAM_ID.agg(lambda x: int(x.mode().iloc[0])).to_dict()


def main():
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    d = unit(vs)
    mc = pd.concat([pd.read_csv(f, dtype={"game": str}) for f in sorted(S5.glob("motion_catches_*.csv"))])
    d = d.merge(mc[["game", "pid", "start", "source5"]], on=["game", "pid", "start"], how="left")
    hm = home_teams()
    d["home"] = [t == hm.get(g) for g, t in zip(d.game, d.team)]
    rep = {"n_unit_catches": int(len(d))}
    # ---- league map
    counts = d.groupby("pid").size()
    elig = counts[counts >= 300].index.tolist()
    names = {}
    pb = pd.read_csv(ROOT.parent / "nba-tracking" / "pbp" / "2015-16_pbp.csv", usecols=["PLAYER1_ID", "PLAYER1_NAME"]).dropna().drop_duplicates("PLAYER1_ID")
    names = dict(zip(pb.PLAYER1_ID.astype(int), pb.PLAYER1_NAME))
    rows = []
    for k, pid in enumerate(sorted(elig)):
        r = er_boot(d[d.pid == pid], 1000 + k)
        r.update(pid=int(pid), name=names.get(int(pid), str(pid)))
        rows.append(r)
        if k % 20 == 0:
            print("map", k, len(elig), flush=True)
    mp = pd.DataFrame(rows)
    res = mp[mp.resolved].sort_values("ER")
    pct = lambda v: round(float((res.ER < v).mean() * 100), 1)
    rep["map"] = {"n_eligible": int(len(mp)), "n_resolved": int(len(res)),
                  "ER_resolved_median_iqr": np.quantile(res.ER, [.5, .25, .75]).round(3).tolist(),
                  "histogram_resolved": {str(k): int(v) for k, v in pd.cut(res.ER, [-np.inf, 0, 2, 4, 6, 8, 10, 15, np.inf]).value_counts().sort_index().items()},
                  "ten_highest": res.tail(10)[::-1][["name", "ER", "ER_ci", "n", "shots"]].to_dict("records"),
                  "ten_lowest": res.head(10)[["name", "ER", "ER_ci", "n", "shots"]].to_dict("records"),
                  "gated": {n: (lambda row: {**{kk: row[kk] for kk in ("ER", "ER_ci", "resolved", "n", "shots", "beta_clock_ci")},
                                            "percentile_among_resolved": pct(row["ER"]) if row["resolved"] else "unresolved"})(mp[mp.pid == p].iloc[0].to_dict())
                            if (mp.pid == p).any() else "not eligible" for p, n in GATED.items()},
                  "all": mp.to_dict("records")}
    print(json.dumps({k: v for k, v in rep["map"].items() if k != "all"}, indent=1, default=str))
    # ---- within-player variation
    groups = {"League": d[~d.pid.isin(GATED) & (d.split != "test")], **{n: d[d.pid == p] for p, n in GATED.items()}}
    cells = {
        "margin": lambda x: np.where(x.margin <= -5, "behind5+", np.where(x.margin >= 5, "ahead5+", "within5")),
        "period": lambda x: np.where(x.quarter >= 4, "Q4+OT", "Q1-3"),
        "home": lambda x: np.where(x.home, "home", "away"),
        "source": lambda x: x.source5.fillna("other").to_numpy(),
    }
    wv = {}
    for k, (gname, g) in enumerate(groups.items()):
        wv[gname] = {}
        for cname, fn in cells.items():
            lab = fn(g)
            wv[gname][cname] = {}
            for j, val in enumerate(sorted(set(lab))):
                sub = g[lab == val]
                if len(sub) < 30 or (sub.action == "shoot").sum() < 5:
                    wv[gname][cname][val] = {"n": int(len(sub)), "shots": int((sub.action == "shoot").sum()), "note": "too thin to fit"}
                    continue
                r = er_boot(sub, 5000 + 100 * k + 10 * list(cells).index(cname) + j)
                r["thin"] = bool(r["n"] < 150 or r["shots"] < 20 or not r["resolved"])
                wv[gname][cname][val] = r
        print(gname, json.dumps(wv[gname], default=str))
    rep["within"] = wv
    (S5 / "s5c.json").write_text(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
