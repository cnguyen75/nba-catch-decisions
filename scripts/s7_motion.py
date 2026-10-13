"""Stage 5a motion features (registered 0437efd). Usage: s7_motion.py <worker> <n_workers>.
Writes out/s5/motion_catches_<w>.csv and out/s5/motion_shots_<w>.csv. Test games are skipped."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "s5"
W = 12  # 0.5 s


def main(worker, nw):
    b.RULE = "d3"
    OUT.mkdir(parents=True, exist_ok=True)
    sp = json.loads((ROOT / "checks/split_all.json").read_text())
    games = sorted(g for g, v in sp["split"].items() if v != "test")[worker::nw]
    c = pd.read_csv(ROOT / "out/s4/catches.csv", dtype={"game": str})
    s = pd.read_csv(ROOT / "out/s4/shots.csv", dtype={"game": str})
    s = s[s.t_r.notna()]
    rows_c, rows_s = [], []
    for gi, gid in enumerate(games):
        b.GAMES[gid] = sp["files"][gid]
        _, _, tl, _ = b.load_timeline(gid)
        jdir = b.DATA / "json" / b.GAMES[gid]
        if jdir.exists() and b.GAMES[gid] not in set(b.GAMES_PASS2.values()) | {"10.27.2015.NOP.at.GSW", "10.31.2015.GSW.at.NOP", "10.27.2015.CLE.at.CHI", "10.28.2015.CLE.at.MEM", "10.28.2015.DEN.at.HOU"}:
            shutil.rmtree(jdir, ignore_errors=True)
        n, GC, Q, PID, PXY, TEAM, ok = tl["n"], tl["GC"], tl["Q"], tl["PID"], tl["PXY"], tl["TEAM"], tl["prev_ok"]

        def pos(i, pid):
            if i < 0 or i >= n:
                return None
            j = np.where(PID[i] == pid)[0]
            return PXY[i, j[0]] if len(j) else None

        def contig(a, z):
            return a >= 1 and z + 1 < n and all(ok[k] for k in range(a, z + 2))

        def vel(i, pid):
            p0, p1 = pos(i - 1, pid), pos(i + 1, pid)
            if p0 is None or p1 is None or not (ok[i] and ok[i + 1]):
                return None
            dt = GC[i - 1] - GC[i + 1]
            return (p1 - p0) / dt if dt > 0 else None

        def closing(a, z, dpid, cpid):
            vals = []
            for i in range(a, z + 1):
                v, pd_, pc = vel(i, dpid), pos(i, dpid), pos(i, cpid)
                if v is None or pd_ is None or pc is None:
                    continue
                u = pc - pd_
                nu = np.linalg.norm(u)
                if nu > 0:
                    vals.append(float(v @ (u / nu)))
            return float(np.mean(vals)) if len(vals) >= 6 else np.nan

        def speed(i, pid):
            p0, p1 = pos(i - 2, pid), pos(i + 2, pid)
            if p0 is None or p1 is None or not contig(i - 1, i + 1):
                return np.nan
            dt = GC[i - 2] - GC[i + 2]
            return float(np.linalg.norm(p1 - p0) / dt) if dt > 0 else np.nan

        def nearest_opp_pid(i, pid, team):
            pc = pos(i, pid)
            m = TEAM[i] != team
            d = np.linalg.norm(PXY[i][m] - pc, axis=1)
            return int(PID[i][m][d.argmin()]), int((d <= 6.0).sum())

        spells = b.spells(tl)
        start_idx = {x[1]: k for k, x in enumerate(spells)}
        gs = s[s.game == gid]
        rel = [(int(r.t_r), int(r.team)) for r in gs.itertuples()]
        for r in c[c.game == gid].itertuples():
            st, p = int(r.start), int(r.pid)
            team = b.team_of(tl, st, p)
            if team is None or pos(st, p) is None:
                continue
            dpid, n6 = nearest_opp_pid(st, p, team)
            rec = {"game": gid, "pid": p, "start": st, "n_def6": n6,
                   "closing_pre": closing(st - W, st - 1, dpid, p), "closing_post": closing(st, st + W, dpid, p),
                   "catcher_speed": speed(st, p)}
            k = start_idx.get(st)
            src, ft, fd = "other", 0.0, 0.0
            if k is not None:
                kk = k - 1
                while kk >= 0 and Q[spells[kk][1]] == Q[st] and b.is_brief_opp(tl, spells[kk], p, st):
                    kk -= 1
                prev = spells[kk] if kk >= 0 and Q[spells[kk][1]] == Q[st] else None
                if prev is not None and prev[0] != p and b.team_of(tl, prev[2], prev[0]) == team:
                    pp = pos(prev[2], prev[0])
                    if pp is not None and (pp[0] < 0 or pp[0] > 94 or pp[1] < 0 or pp[1] > 50):
                        src = "inbound"
                    elif any(tm == team and prev[1] <= t <= st and Q[t] == Q[st] for t, tm in rel):
                        src = "oreb"
                    else:
                        src = "pass"
                        ft = float(GC[prev[2]] - GC[st])
                        fd = float(np.linalg.norm(pp - pos(st, p))) if pp is not None else np.nan
                elif prev is not None and any(tm == team and prev[1] <= t <= st and Q[t] == Q[st] for t, tm in rel):
                    src = "oreb"
            rec.update(source5=src, flight_time=ft, flight_dist=fd)
            rows_c.append(rec)
        for r in gs.itertuples():
            t, sh = int(r.t_r), int(r.shooter)
            team = b.team_of(tl, t, sh)
            if team is None or pos(t, sh) is None:
                continue
            dpid, n6 = nearest_opp_pid(t, sh, team)
            rows_s.append({"game": gid, "eventnum": int(r.eventnum), "s_closing_pre": closing(t - W, t - 1, dpid, sh),
                           "s_speed": speed(t, sh), "s_n_def6": n6})
        if gi % 20 == 0:
            print(worker, gi, len(games), gid, flush=True)
    pd.DataFrame(rows_c).to_csv(OUT / f"motion_catches_{worker}.csv", index=False)
    pd.DataFrame(rows_s).to_csv(OUT / f"motion_shots_{worker}.csv", index=False)
    print("done", worker, len(rows_c), len(rows_s), flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
