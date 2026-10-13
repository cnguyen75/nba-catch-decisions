"""Build per-game timelines, locate shot releases, find possession spells and catches.

Implements the rules pre-registered in README.md. Writes out/shots.csv, out/catches.csv,
out/join_check.csv and out/build_meta.json. Raw data is read from ~/Documents/nba-tracking.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path.home() / "Documents" / "nba-tracking"
OUT = Path(__file__).resolve().parent.parent / "out"
GAMES = {
    "0021500003": "10.27.2015.NOP.at.GSW",
    "0021500035": "10.31.2015.GSW.at.NOP",
    "0021500002": "10.27.2015.CLE.at.CHI",
    "0021500011": "10.28.2015.CLE.at.MEM",
    "0021500010": "10.28.2015.DEN.at.HOU",
}
# second pass (registered 4a18241): 8 more GSW games
GAMES_PASS2 = {
    "0021500051": "11.02.2015.MEM.at.GSW",
    "0021500069": "11.04.2015.LAC.at.GSW",
    "0021500083": "11.06.2015.DEN.at.GSW",
    "0021500092": "11.07.2015.GSW.at.SAC",
    "0021500104": "11.09.2015.DET.at.GSW",
    "0021500120": "11.11.2015.GSW.at.MEM",
    "0021500125": "11.12.2015.GSW.at.MIN",
    "0021500144": "11.14.2015.BKN.at.GSW",
}
RULE = "nearest"  # "nearest" (first pass) or "sticky" (second pass, C1)
TARGETS = {201939: "Curry", 2544: "LeBron", 201935: "Harden"}
BASKETS = np.array([[5.25, 25.0], [88.75, 25.0]])
CONTIG = 0.06
CTRL_D, CTRL_Z = 3.0, 8.0
MERGE_S = 1.0
PRE_FRAMES = 5
SC_LAG = 12
BRIEF_FRAMES = 12


def load_timeline(game_id):
    path = DATA / "json" / GAMES[game_id] / f"{game_id}.json"
    g = json.loads(path.read_text())
    assert g["gameid"] == game_id
    seen = {}
    events = {}
    skipped = 0
    for ev in g["events"]:
        eid = int(ev["eventId"])
        ms = ev["moments"]
        if ms:
            events[eid] = (ms[0][0], max(m[2] for m in ms), min(m[2] for m in ms), ev)
        for m in ms:
            key = (m[0], m[2])
            if key in seen:
                continue
            rows = m[5]
            if len(rows) != 11 or rows[0][0] != -1:
                skipped += 1
                continue
            seen[key] = m
    keys = sorted(seen, key=lambda k: (k[0], -k[1]))
    n = len(keys)
    Q = np.array([k[0] for k in keys])
    GC = np.array([k[1] for k in keys])
    SC = np.array([np.nan if seen[k][3] is None else seen[k][3] for k in keys])
    B = np.array([seen[k][5][0][2:5] for k in keys], dtype=float)
    PID = np.array([[r[1] for r in seen[k][5][1:]] for k in keys])
    TEAM = np.array([[r[0] for r in seen[k][5][1:]] for k in keys])
    PXY = np.array([[r[2:4] for r in seen[k][5][1:]] for k in keys], dtype=float)
    tl = dict(Q=Q, GC=GC, SC=SC, B=B, PID=PID, TEAM=TEAM, PXY=PXY, n=n)
    # contiguity with previous frame
    prev_ok = np.zeros(n, bool)
    prev_ok[1:] = (Q[1:] == Q[:-1]) & ((GC[:-1] - GC[1:]) <= CONTIG)
    tl["prev_ok"] = prev_ok
    # ball-player horizontal distances, controller
    dist = np.linalg.norm(PXY - B[:, None, :2], axis=2)
    near = dist.argmin(1)
    nd = dist[np.arange(n), near]
    ctrl = np.where((nd <= CTRL_D) & (B[:, 2] <= CTRL_Z), PID[np.arange(n), near], 0)
    tl["dist"] = dist
    tl["ctrl"] = sticky_ctrl(dist, B, PID, prev_ok) if RULE == "sticky" else ctrl
    tl["home_team"] = g["events"][0]["home"]["teamid"]
    tl["visitor_team"] = g["events"][0]["visitor"]["teamid"]
    return g, events, tl, skipped


def pc_seconds(s):
    m, sec = s.split(":")
    return int(m) * 60 + int(sec)


def sticky_ctrl(dist, B, PID, prev_ok):
    """C1: the holder keeps control while the ball is within 3 ft of him and z <= 8, whoever is nearer;
    otherwise control goes to the nearest player within 3 ft (z <= 8) or to nobody. Resets at data gaps."""
    n = len(B)
    out = np.zeros(n, dtype=PID.dtype)
    holder = 0
    low = B[:, 2] <= CTRL_Z
    for i in range(n):
        if not prev_ok[i]:
            holder = 0
        if holder and low[i]:
            j = np.where(PID[i] == holder)[0]
            if len(j) and dist[i, j[0]] <= CTRL_D:
                out[i] = holder
                continue
        k = dist[i].argmin()
        holder = PID[i, k] if (dist[i, k] <= CTRL_D and low[i]) else 0
        out[i] = holder
    return out


def window(tl, q, gmax, gmin):
    return np.where((tl["Q"] == q) & (tl["GC"] <= gmax) & (tl["GC"] >= gmin))[0]


def player_xy(tl, i, pid):
    j = np.where(tl["PID"][i] == pid)[0]
    return None if len(j) == 0 else tl["PXY"][i, j[0]]


def ball_to_player(tl, i, pid):
    j = np.where(tl["PID"][i] == pid)[0]
    return np.inf if len(j) == 0 else tl["dist"][i, j[0]]


def _release_before(tl, idx, lo, a, bk, shooter):
    """Last frame in idx[lo:a] with ball within 3 ft of shooter, plus validity checks."""
    d_sh = np.array([ball_to_player(tl, i, shooter) for i in idx[lo:a]])
    cand = np.where(d_sh <= 3.0)[0]
    if len(cand) == 0:
        return None, "shooter_never_near_ball"
    t_r = idx[lo + cand[-1]]
    if tl["B"][t_r, 2] < 6.0:
        return None, "z_below_6"
    if t_r + 10 >= tl["n"]:
        return None, "end_of_data"
    if not ball_to_player(tl, t_r + 5, shooter) > d_sh[cand[-1]]:
        return None, "not_moving_away"
    b0 = np.linalg.norm(tl["B"][t_r, :2] - BASKETS[bk])
    b10 = np.linalg.norm(tl["B"][t_r + 10, :2] - BASKETS[bk])
    if not b10 < b0:
        return None, "not_toward_basket"
    return t_r, "ok"


def locate_release(tl, idx, shooter, target_gc):
    """Release rule as amended by R1 and R2. Returns (t_r, t_a, basket_index, reason)."""
    if len(idx) == 0:
        return None, None, None, "empty_window"
    B = tl["B"][idx]
    db = np.linalg.norm(B[:, None, :2] - BASKETS[None], axis=2)  # (k, 2)
    arr = np.where((db.min(1) <= 3.0) & (B[:, 2] >= 9.0))[0]
    episodes = []  # (first, last) positions in idx
    for a in arr:
        if episodes and a - episodes[-1][1] <= 6:
            episodes[-1][1] = a
        else:
            episodes.append([a, a])
    reason = "no_arrival"
    found = []
    for k in range(len(episodes) - 1, -1, -1):
        a = episodes[k][0]
        lo = episodes[k - 1][1] + 1 if k > 0 else 0
        bk = int(db[a].argmin())
        t_r, why = _release_before(tl, idx, lo, a, bk, shooter)
        if t_r is not None:
            found.append((abs(tl["GC"][t_r] - target_gc), t_r, idx[a], bk))
        elif reason == "no_arrival":
            reason = why
    if found:
        _, t_r, t_a, bk = min(found)
        return t_r, t_a, bk, "ok"
    a = int(B[:, 2].argmax())
    bk = int(db[a].argmin())
    t_r, reason_air = _release_before(tl, idx, 0, a, bk, shooter)
    if t_r is not None:
        return t_r, idx[a], bk, "ok_airball"
    return None, idx[a], bk, reason if episodes else reason_air


def spells(tl):
    """All possession spells, any player: list of (owner, start, end)."""
    ctrl, Q, GC, Z = tl["ctrl"], tl["Q"], tl["GC"], tl["B"][:, 2]
    cf = np.where(ctrl != 0)[0]
    out = []
    cur = None
    for k in cf:
        o = ctrl[k]
        if cur is not None:
            co, cs, ce = cur
            if (o == co and Q[k] == Q[ce] and GC[ce] - GC[k] <= MERGE_S
                    and (k - ce <= 1 or Z[ce + 1:k].max() <= CTRL_Z)):
                cur = (co, cs, k)
                continue
            out.append(cur)
        cur = (o, k, k)
    if cur is not None:
        out.append(cur)
    if RULE != "sticky":
        return out
    # C1a: P, brief opponent touch (<= 12 frames), P within 1.0 s -> one possession
    res = []
    for sp in out:
        if len(res) >= 2:
            a, t = res[-2], res[-1]
            if (a[0] == sp[0] and is_brief_opp(tl, t, sp[0], sp[1])
                    and Q[a[2]] == Q[sp[1]] and GC[a[2]] - GC[sp[1]] <= MERGE_S):
                res.pop()
                res[-1] = (a[0], a[1], sp[2])
                continue
        res.append(sp)
    return res


def is_brief_opp(tl, s, pid, at):
    """Spell s is an opponent's (relative to pid at frame `at`) and lasts <= 12 frames."""
    return (s[2] - s[1] + 1 <= BRIEF_FRAMES and s[0] != pid
            and team_of(tl, s[2], s[0]) != team_of(tl, at, pid))


def team_of(tl, i, pid):
    j = np.where(tl["PID"][i] == pid)[0]
    return None if len(j) == 0 else tl["TEAM"][i, j[0]]


def nearest_opp(tl, i, team, point):
    m = tl["TEAM"][i] != team
    return float(np.linalg.norm(tl["PXY"][i][m] - point, axis=1).min())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pbp = pd.read_csv(DATA / "pbp" / "2015-16_pbp.csv", dtype={"GAME_ID": str})
    pbp = pbp[pbp.GAME_ID.isin(GAMES)].copy()
    shots_rows, catch_rows, join_rows = [], [], []
    meta = {"games": {}}
    for gid in GAMES:
        g, events, tl, skipped = load_timeline(gid)
        gp = pbp[pbp.GAME_ID == gid]
        # --- join: every PBP row
        for _, row in gp.iterrows():
            e = events.get(int(row.EVENTNUM))
            join_rows.append(dict(game=gid, eventnum=int(row.EVENTNUM), msgtype=int(row.EVENTMSGTYPE),
                                  period=int(row.PERIOD), pctime=row.PCTIMESTRING,
                                  joined=e is not None,
                                  ev_q=None if e is None else e[0],
                                  ev_gmax=None if e is None else e[1],
                                  ev_gmin=None if e is None else e[2],
                                  desc=" | ".join(str(x) for x in (row.HOMEDESCRIPTION, row.NEUTRALDESCRIPTION,
                                                                    row.VISITORDESCRIPTION) if isinstance(x, str)),
                                  p1=int(row.PLAYER1_ID)))
        # --- releases for every FGA
        fga = gp[gp.EVENTMSGTYPE.isin([1, 2])]
        votes = {}
        for _, row in fga.iterrows():
            e = events.get(int(row.EVENTNUM))
            rec = dict(game=gid, eventnum=int(row.EVENTNUM), shooter=int(row.PLAYER1_ID),
                       team=int(row.PLAYER1_TEAM_ID), period=int(row.PERIOD), pctime=row.PCTIMESTRING,
                       made=int(row.EVENTMSGTYPE == 1), joined=e is not None)
            if e is None:
                rec["reason"] = "not_joined"
                shots_rows.append(rec)
                continue
            pbp_gc = pc_seconds(row.PCTIMESTRING)
            idx = window(tl, int(row.PERIOD), pbp_gc + 10.0, pbp_gc - 0.5)
            t_r, t_a, bk, reason = locate_release(tl, idx, rec["shooter"], pbp_gc + 2.5)
            rec.update(reason=reason, t_r=t_r, t_a=t_a, basket_at_arrival=bk)
            if t_r is not None:
                rec["gc_release"] = float(tl["GC"][t_r])
                rec["q_release"] = int(tl["Q"][t_r])
                rec["ball_z_release"] = float(tl["B"][t_r, 2])
                # nearest player to ball at release
                rec["nearest_at_release"] = int(tl["PID"][t_r, tl["dist"][t_r].argmin()])
                votes.setdefault((rec["team"], rec["period"]), []).append(bk)
            shots_rows.append(rec)
        # --- attacking basket per (team, period)
        att = {}
        periods = sorted(set(tl["Q"].tolist()))
        teams = [tl["home_team"], tl["visitor_team"]]
        for q in periods:
            for t in teams:
                v = votes.get((t, q), [])
                if v:
                    att[(t, q)] = int(np.bincount(v, minlength=2).argmax())
            for t, o in (teams, teams[::-1]):
                if (t, q) not in att and (o, q) in att:
                    att[(t, q)] = 1 - att[(o, q)]
        vote_purity = {f"{t}_{q}": (float(np.mean(np.array(v) == att[(t, q)])), len(v))
                       for (t, q), v in votes.items()}
        # --- spells and catches for target players present in this game
        sp = spells(tl)
        present = [p for p in TARGETS if (tl["PID"] == p).any()]
        GC, Q, SC = tl["GC"], tl["Q"], tl["SC"]
        my_shots = [s for s in shots_rows if s["game"] == gid and s.get("t_r") is not None]
        for p in present:
            psp = [(k, s) for k, s in enumerate(sp) if s[0] == p]
            for k, (o, st, en) in psp:
                ok_pre = st >= PRE_FRAMES and all(tl["prev_ok"][st - j] for j in range(PRE_FRAMES)) \
                    and all(tl["ctrl"][st - j] != p for j in range(1, PRE_FRAMES + 1))
                team = team_of(tl, st, p)
                q = int(Q[st])
                bk = att.get((team, q))
                pxy = player_xy(tl, st, p)
                d_b = None if bk is None else float(np.linalg.norm(pxy - BASKETS[bk]))
                sc_run = (st + SC_LAG < tl["n"] and not np.isnan(SC[st])
                          and all(tl["prev_ok"][st + j] for j in range(1, SC_LAG + 1))
                          and SC[st + SC_LAG] < SC[st])
                frontcourt = d_b is not None and d_b <= 47.0
                kk = k - 1
                brief = False
                while RULE == "sticky" and kk >= 0 and Q[sp[kk][1]] == q and is_brief_opp(tl, sp[kk], p, st):
                    kk -= 1
                    brief = True
                prev = sp[kk] if kk >= 0 else None
                if prev is None or Q[prev[1]] != q:
                    src = "none"
                elif prev[0] == p:
                    src = "self"
                else:
                    src = "teammate" if team_of(tl, prev[2], prev[0]) == team else "opponent"
                row = dict(game=gid, player=TARGETS[p], pid=p, start=st, end=en, quarter=q,
                           gc=float(GC[st]), valid_catch=bool(ok_pre), frontcourt=bool(frontcourt),
                           sc_running=bool(sc_run), shot_clock=None if np.isnan(SC[st]) else float(SC[st]),
                           d_basket=d_b, source=src, brief_opp_touch=brief, t_next=float(GC[st] - GC[en]))
                if bk is not None:
                    row["open_catch"] = nearest_opp(tl, st, team, pxy)
                    row["rim_prot"] = nearest_opp(tl, st, team, BASKETS[bk])
                catch_rows.append(row)
        meta["games"][gid] = dict(file=GAMES[gid], frames=tl["n"], skipped_moments=skipped,
                                  events=len(g["events"]), events_with_moments=len(events),
                                  attacking={f"{t}_{q}": b for (t, q), b in att.items()},
                                  vote_purity=vote_purity, present_targets=[TARGETS[p] for p in present],
                                  n_spells=len(sp))
        # link located target shots to latest spell of shooter at/before t_r with no other spell in between
        for s in my_shots:
            if s["shooter"] not in TARGETS:
                continue
            t_r = s["t_r"]
            before = [x for x in sp if x[1] <= t_r]
            if not before:
                continue
            last = before[-1]
            s["linked"] = last[0] == s["shooter"]
            if s["linked"]:
                s["link_start"] = last[1]
                s["catch_to_shot"] = float(GC[last[1]] - GC[t_r]) if Q[last[1]] == Q[t_r] else None
                team = s["team"]
                s["open_release"] = nearest_opp(tl, t_r, team, player_xy(tl, t_r, s["shooter"]))
        print(gid, GAMES[gid], "frames", tl["n"], "skipped", skipped, "spells", len(sp), "targets", present)
    shots = pd.DataFrame(shots_rows)
    catches = pd.DataFrame(catch_rows)
    # attach shot outcome to catches
    link = shots[shots["linked"].astype("boolean").fillna(False).astype(bool)]
    key = {(r.game, int(r.link_start)): (r.catch_to_shot, r.open_release, r.eventnum) for r in link.itertuples()}
    catches["catch_to_shot"] = [key.get((r.game, r.start), (None,))[0] for r in catches.itertuples()]
    catches["open_release"] = [key.get((r.game, r.start), (None, None))[1] for r in catches.itertuples()]
    catches["shot_event"] = [key.get((r.game, r.start), (None, None, None))[2] for r in catches.itertuples()]
    shots.to_csv(OUT / "shots.csv", index=False)
    catches.to_csv(OUT / "catches.csv", index=False)
    pd.DataFrame(join_rows).to_csv(OUT / "join_check.csv", index=False)
    (OUT / "build_meta.json").write_text(json.dumps(meta, indent=1, default=str))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", choices=["nearest", "sticky"], default="nearest")
    ap.add_argument("--games", choices=["pass1", "pass2"], default="pass1")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    RULE = a.rule
    if a.games == "pass2":
        GAMES.update(GAMES_PASS2)
    if a.out:
        OUT = Path(a.out).resolve()
    main()
