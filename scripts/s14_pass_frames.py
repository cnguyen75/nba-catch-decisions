"""Stage 9 extraction (registered 4d5a2f8). Usage: s14_pass_frames.py <worker> <n_workers>. For each
pass (counted catch ending in a teammate's catch within 1.5 s), at the pass frame (passer's spell
end): each teammate's openness, distance to the attacking basket, distance from the passer,
position, and whether he is the receiver (owner of the next D3 spell). Long format, one row per
(pass, teammate). Writes out/s9/passes_<w>.csv.
"""

import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "s9"
KEEP = set(b.GAMES.values()) | set(b.GAMES_PASS2.values())


def main(worker: int, nw: int) -> None:
    b.RULE = "d3"
    OUT.mkdir(parents=True, exist_ok=True)
    sp = json.loads((ROOT / "checks/split_all.json").read_text())
    meta = json.loads((ROOT / "out/s4/build_meta.json").read_text())["games"]
    games = sorted(g for g, v in sp["split"].items() if v != "test")[worker::nw]
    assert all(sp["split"][g] != "test" for g in games), "test game in stem list"
    c = pd.read_csv(
        ROOT / "out/s4/catches.csv",
        dtype={"game": str},
        usecols=["game", "pid", "start", "end", "team", "quarter", "next_rel", "next_gap"],
    )
    c = c[(c.next_rel == "teammate") & (c.next_gap <= 1.5) & c.game.isin(games)]
    rows, n_drop = [], 0
    for gi, gid in enumerate(games):
        b.GAMES[gid] = sp["files"][gid]
        _, _, tl, _ = b.load_timeline(gid)
        jdir = b.DATA / "json" / b.GAMES[gid]
        if jdir.exists() and b.GAMES[gid] not in KEEP:
            shutil.rmtree(jdir, ignore_errors=True)
        spells = b.spells(tl)
        k_of = {x[1]: k for k, x in enumerate(spells)}
        att = meta[gid]["attacking"]
        for r in c[c.game == gid].itertuples():
            st, en, p, team = int(r.start), int(r.end), int(r.pid), int(r.team)
            k = k_of.get(st)
            bk = att.get(f"{team}_{int(r.quarter)}")
            if k is None or k + 1 >= len(spells) or bk is None:
                n_drop += 1
                continue
            recv = int(spells[k + 1][0])
            ppos = b.player_xy(tl, en, p)
            tm = [j for j in range(10) if tl["TEAM"][en, j] == team and tl["PID"][en, j] != p]
            if ppos is None or recv not in [int(tl["PID"][en, j]) for j in tm]:
                n_drop += 1
                continue
            for j in tm:
                pos = tl["PXY"][en, j]
                rows.append(
                    {
                        "game": gid,
                        "passer": p,
                        "start": st,
                        "end": en,
                        "quarter": int(r.quarter),
                        "teammate": int(tl["PID"][en, j]),
                        "open": b.nearest_opp(tl, en, team, pos),
                        "d_basket": float(np.linalg.norm(pos - b.BASKETS[int(bk)])),
                        "d_passer": float(np.linalg.norm(pos - ppos)),
                        "x": float(pos[0]),
                        "y": float(pos[1]),
                        "bk": int(bk),
                        "is_receiver": int(tl["PID"][en, j]) == recv,
                    }
                )
        if gi % 25 == 0:
            print(worker, gi, len(games), flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"passes_{worker}.csv", index=False)
    (OUT / f"drop_{worker}.json").write_text(json.dumps({"dropped": n_drop}))
    print("done", worker, len(rows), "dropped", n_drop, flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
