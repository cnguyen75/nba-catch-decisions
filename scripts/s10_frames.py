"""Stage 6 frame features (registered 811c61b). Usage: s10_frames.py <worker> <n_workers>.
Per counted catch: minutes_so_far, def_pid_catch, rim_pid_catch. Per located shot: def_pid_rel, rim_pid_rel, shooter minutes.
Writes out/s6/frames_catches_<w>.csv, out/s6/frames_shots_<w>.csv. Test games skipped."""

import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "s6"
KEEP = set(b.GAMES.values()) | set(b.GAMES_PASS2.values())


def main(worker, nw):
    b.RULE = "d3"
    OUT.mkdir(parents=True, exist_ok=True)
    sp = json.loads((ROOT / "checks/split_all.json").read_text())
    meta = json.loads((ROOT / "out/s4/build_meta.json").read_text())["games"]
    games = sorted(g for g, v in sp["split"].items() if v != "test")[worker::nw]
    c = pd.read_csv(
        ROOT / "out/s4/catches.csv",
        dtype={"game": str},
        usecols=["game", "pid", "start", "team", "quarter"],
    )
    s = pd.read_csv(
        ROOT / "out/s4/shots.csv",
        dtype={"game": str},
        usecols=["game", "eventnum", "shooter", "team", "t_r", "basket_at_arrival"],
    )
    s = s[s.t_r.notna()]
    rc, rs = [], []
    for gi, gid in enumerate(games):
        b.GAMES[gid] = sp["files"][gid]
        _, _, tl, _ = b.load_timeline(gid)
        jdir = b.DATA / "json" / b.GAMES[gid]
        if jdir.exists() and b.GAMES[gid] not in KEEP:
            shutil.rmtree(jdir, ignore_errors=True)
        n, GC, PID, PXY, TEAM, ok = (
            tl["n"],
            tl["GC"],
            tl["PID"],
            tl["PXY"],
            tl["TEAM"],
            tl["prev_ok"],
        )
        dt = np.zeros(n)
        dt[1:] = np.where(ok[1:], GC[:-1] - GC[1:], 0.0)
        cum = {}

        def minutes(pid, i):
            if pid not in cum:
                pres = (pid == PID).any(1)
                inc = dt * pres * np.r_[False, pres[:-1]]
                cum[pid] = np.cumsum(inc)
            return float(cum[pid][i] / 60.0)

        def nearest_opp_to(i, team, point):
            m = TEAM[i] != team
            d = np.linalg.norm(PXY[i][m] - point, axis=1)
            return int(PID[i][m][d.argmin()])

        att = meta[gid]["attacking"]
        for r in c[c.game == gid].itertuples():
            st, p = int(r.start), int(r.pid)
            j = np.where(PID[st] == p)[0]
            if not len(j):
                continue
            bk = att.get(f"{int(r.team)}_{int(r.quarter)}")
            rec = {
                "game": gid,
                "pid": p,
                "start": st,
                "minutes_so_far": minutes(p, st),
                "def_pid_catch": nearest_opp_to(st, r.team, PXY[st, j[0]]),
            }
            rec["rim_pid_catch"] = (
                nearest_opp_to(st, r.team, b.BASKETS[int(bk)]) if bk is not None else np.nan
            )
            rc.append(rec)
        for r in s[s.game == gid].itertuples():
            t, sh = int(r.t_r), int(r.shooter)
            j = np.where(PID[t] == sh)[0]
            if not len(j):
                continue
            rs.append(
                {
                    "game": gid,
                    "eventnum": int(r.eventnum),
                    "def_pid_rel": nearest_opp_to(t, r.team, PXY[t, j[0]]),
                    "rim_pid_rel": nearest_opp_to(t, r.team, b.BASKETS[int(r.basket_at_arrival)])
                    if not np.isnan(r.basket_at_arrival)
                    else np.nan,
                    "shooter_minutes": minutes(sh, t),
                }
            )
        if gi % 25 == 0:
            print(worker, gi, len(games), flush=True)
    pd.DataFrame(rc).to_csv(OUT / f"frames_catches_{worker}.csv", index=False)
    pd.DataFrame(rs).to_csv(OUT / f"frames_shots_{worker}.csv", index=False)
    print("done", worker, len(rc), len(rs), flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
