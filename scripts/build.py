"""Build per-game timelines, locate shot releases, find possession spells and catches.

Implements the rules pre-registered in README.md. Writes out/shots.csv, out/catches.csv,
out/join_check.csv and out/build_meta.json. Raw data is read from ~/Documents/nba-tracking.
"""

import json
from pathlib import Path
import re

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
MIN_RUN = 5
CLEANUP = False
R3 = False
ALL_PLAYERS = False


class EmptyGame(Exception):
    pass


def load_timeline(game_id):
    path = DATA / "json" / GAMES[game_id] / f"{game_id}.json"
    if not path.exists():
        import py7zr

        with py7zr.SevenZipFile(DATA / "raw" / f"{GAMES[game_id]}.7z") as z:
            assert z.getnames() == [f"{game_id}.json"], z.getnames()
            z.extractall(path.parent)
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
    if n == 0:
        raise EmptyGame(game_id)
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
    if RULE == "d3":
        B = despike(B, prev_ok)
        tl["B"] = B
    # ball-player horizontal distances, controller
    dist = np.linalg.norm(PXY - B[:, None, :2], axis=2)
    near = dist.argmin(1)
    nd = dist[np.arange(n), near]
    ctrl = np.where((nd <= CTRL_D) & (B[:, 2] <= CTRL_Z), PID[np.arange(n), near], 0)
    tl["dist"] = dist
    if RULE == "sticky":
        ctrl = sticky_ctrl(dist, B, PID, prev_ok)
    elif RULE == "d3":
        ctrl = min_run(hyst_ctrl(dist, B, PID, prev_ok), prev_ok)
    tl["ctrl"] = ctrl
    tl["home_team"] = g["events"][0]["home"]["teamid"]
    tl["visitor_team"] = g["events"][0]["visitor"]["teamid"]
    return g, events, tl, skipped


CLOSE_RE = re.compile(r"Layup|Dunk|Tip|Hook|Putback|Finger Roll|Alley Oop")


def is_close(desc):
    m = re.search(r"(\d+)' ", desc)
    return bool(CLOSE_RE.search(desc)) or (m is not None and int(m.group(1)) <= 8)


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


def despike(B, prev_ok, win=5, tol=3.0):
    """D1: within contiguous runs, replace a ball coordinate by its centred 5-frame median where they differ
    by more than 3 ft."""
    B = B.copy()
    starts = np.r_[np.where(~prev_ok)[0], len(B)]
    h = win // 2
    for a, z in zip(starts[:-1], starts[1:]):
        seg = B[a:z]
        if len(seg) < win:
            continue
        pad = np.concatenate([np.repeat(seg[:1], h, 0), seg, np.repeat(seg[-1:], h, 0)])
        med = np.median(np.lib.stride_tricks.sliding_window_view(pad, win, axis=0), axis=-1)
        bad = np.abs(seg - med) > tol
        seg[bad] = med[bad]
    return B


def hyst_ctrl(dist, B, PID, prev_ok, keep_d=5.0, take_frames=6):
    """D2: acquire within 3 ft (nearest, z <= 8); holder keeps while within 5 ft and z <= 8; another player
    takes over after being the nearest within 3 ft for 6 consecutive frames (assigned from the first)."""
    n = len(B)
    out = np.zeros(n, dtype=PID.dtype)
    holder, sq, sl = 0, 0, 0
    low = B[:, 2] <= CTRL_Z
    for i in range(n):
        if not prev_ok[i]:
            holder, sq, sl = 0, 0, 0
        k = dist[i].argmin()
        cand = PID[i, k] if (dist[i, k] <= CTRL_D and low[i]) else 0
        if cand and cand != holder:
            sl = sl + 1 if cand == sq else 1
            sq = cand
        else:
            sq, sl = 0, 0
        hj = np.where(PID[i] == holder)[0] if holder else []
        if holder and low[i] and len(hj) and dist[i, hj[0]] <= keep_d:
            if sl >= take_frames:
                holder = sq
                out[i - take_frames + 1 : i + 1] = holder
                sq, sl = 0, 0
            else:
                out[i] = holder
        else:
            holder = cand
            out[i] = holder
            sq, sl = 0, 0
    return out


def min_run(ctrl, prev_ok, k=MIN_RUN):
    """D3: runs of the same controller shorter than 5 frames become 'no controller'."""
    out = ctrl.copy()
    n = len(ctrl)
    i = 0
    while i < n:
        j = i + 1
        while j < n and ctrl[j] == ctrl[i] and prev_ok[j]:
            j += 1
        if ctrl[i] != 0 and j - i < k:
            out[i:j] = 0
        i = j
    return out


def window(tl, q, gmax, gmin):
    return np.where((tl["Q"] == q) & (tl["GC"] <= gmax) & (tl["GC"] >= gmin))[0]


def player_xy(tl, i, pid):
    j = np.where(tl["PID"][i] == pid)[0]
    return None if len(j) == 0 else tl["PXY"][i, j[0]]


def ball_to_player(tl, i, pid):
    j = np.where(tl["PID"][i] == pid)[0]
    return np.inf if len(j) == 0 else tl["dist"][i, j[0]]


def _release_before(tl, idx, lo, a, bk, shooter, close=False):
    """Last frame in idx[lo:a] with ball within 3 ft (4 ft for close-range under R3) of shooter, plus checks."""
    d_sh = np.array([ball_to_player(tl, i, shooter) for i in idx[lo:a]])
    cand = np.where(d_sh <= (4.0 if close else 3.0))[0]
    if len(cand) == 0:
        return None, "shooter_never_near_ball"
    t_r = idx[lo + cand[-1]]
    if tl["B"][t_r, 2] < 6.0:
        return None, "z_below_6"
    if close:
        if np.linalg.norm(tl["B"][t_r, :2] - BASKETS[bk]) > 12.0:
            return None, "r3_far_from_basket"
        if tl["GC"][t_r] - tl["GC"][idx[a]] > 1.2:
            return None, "r3_arrival_late"
        return t_r, "ok"
    if t_r + 10 >= tl["n"]:
        return None, "end_of_data"
    if not ball_to_player(tl, t_r + 5, shooter) > d_sh[cand[-1]]:
        return None, "not_moving_away"
    b0 = np.linalg.norm(tl["B"][t_r, :2] - BASKETS[bk])
    b10 = np.linalg.norm(tl["B"][t_r + 10, :2] - BASKETS[bk])
    if not b10 < b0:
        return None, "not_toward_basket"
    return t_r, "ok"


def locate_release(tl, idx, shooter, target_gc, close=False):
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
        t_r, why = _release_before(tl, idx, lo, a, bk, shooter, close)
        if t_r is not None:
            found.append((abs(tl["GC"][t_r] - target_gc), t_r, idx[a], bk))
        elif reason == "no_arrival":
            reason = why
    if found:
        _, t_r, t_a, bk = min(found)
        return t_r, t_a, bk, "ok"
    a = int(B[:, 2].argmax())
    bk = int(db[a].argmin())
    t_r, reason_air = _release_before(tl, idx, 0, a, bk, shooter, close)
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
            if (
                o == co
                and Q[k] == Q[ce]
                and GC[ce] - GC[k] <= MERGE_S
                and (k - ce <= 1 or Z[ce + 1 : k].max() <= CTRL_Z)
            ):
                cur = (co, cs, k)
                continue
            out.append(cur)
        cur = (o, k, k)
    if cur is not None:
        out.append(cur)
    if RULE not in ("sticky", "d3"):
        return out
    # C1a: P, brief opponent touch (<= 12 frames), P within 1.0 s -> one possession
    res = []
    for sp in out:
        if len(res) >= 2:
            a, t = res[-2], res[-1]
            if (
                a[0] == sp[0]
                and is_brief_opp(tl, t, sp[0], sp[1])
                and Q[a[2]] == Q[sp[1]]
                and GC[a[2]] - GC[sp[1]] <= MERGE_S
            ):
                res.pop()
                res[-1] = (a[0], a[1], sp[2])
                continue
        res.append(sp)
    return res


def is_brief_opp(tl, s, pid, at):
    """Spell s is an opponent's (relative to pid at frame `at`) and lasts <= 12 frames."""
    return (
        s[2] - s[1] + 1 <= BRIEF_FRAMES
        and s[0] != pid
        and team_of(tl, s[2], s[0]) != team_of(tl, at, pid)
    )


def zone_of(pxy, bk, d_b):
    """Registered zones: rim <= 6 ft; corner three: |y-25| >= 22 and within 14 ft of baseline; three >= 23.75 ft."""
    corner = abs(pxy[1] - 25.0) >= 22.0 and abs(pxy[0] - (0.0 if bk == 0 else 94.0)) <= 14.0
    if d_b <= 6.0:
        return "rim"
    if corner:
        return "corner3"
    if d_b >= 23.75:
        return "above_break3"
    return "mid"


def stage3_features(tl, sp, k, p, team, bk, pxy, unloc):
    """Stage 3a features for a counted catch: zone, best teammate openness, drive/pass flags (registered rules),
    next-owner relation, F1 unknown flag."""
    o, st, en = sp[k]
    GC, Q = tl["GC"], tl["Q"]
    d_b = float(np.linalg.norm(pxy - BASKETS[bk]))
    out = {"zone": zone_of(pxy, bk, d_b)}
    tm = [j for j in range(10) if tl["TEAM"][st, j] == team and tl["PID"][st, j] != p]
    out["best_tm_open"] = (
        max(nearest_opp(tl, st, team, tl["PXY"][st, j]) for j in tm) if tm else np.nan
    )
    seg = np.arange(st, en + 1)
    j_p = [np.where(tl["PID"][i] == p)[0] for i in seg]
    dP = np.array(
        [
            np.linalg.norm(tl["PXY"][i, jj[0]] - BASKETS[bk]) if len(jj) else np.nan
            for i, jj in zip(seg, j_p)
        ]
    )
    bP = np.array([tl["dist"][i, jj[0]] if len(jj) else np.inf for i, jj in zip(seg, j_p)])
    drib = (tl["B"][seg, 2] <= 1.5) & (bP <= 5.0)
    cs = np.r_[0, np.cumsum(drib)]
    drive = False
    four = GC[st] - 4.0
    for jj in np.where(dP <= 10.0)[0]:
        ii = np.where((dP[:jj] >= 20.0) & (GC[seg[:jj]] >= four))[0]
        if len(ii) and cs[jj + 1] - cs[ii[-1]] > 0:
            drive = True
            break
    out["drive"] = drive
    out["min_dbasket"] = float(np.nanmin(dP))
    out["max_dbasket"] = float(np.nanmax(dP))
    out["n_dribbles"] = int(np.sum(drib[1:] & ~drib[:-1]))
    for kf in range(5, 45, 5):
        i = st + kf
        pk = player_xy(tl, i, p) if i < tl["n"] and Q[i] == Q[st] else None
        out[f"open_k{kf}"] = nearest_opp(tl, i, team, pk) if pk is not None else np.nan
    nxt = sp[k + 1] if k + 1 < len(sp) else None
    if nxt is None or Q[nxt[1]] != Q[st]:
        rel, gap = "none", np.nan
    else:
        gap = float(GC[en] - GC[nxt[1]])
        rel = (
            "self"
            if nxt[0] == p
            else ("teammate" if team_of(tl, nxt[1], nxt[0]) == team else "opponent")
        )
    out["next_rel"], out["next_gap"] = rel, gap
    out["pass"] = (not drive) and rel == "teammate" and gap <= 1.5 and (GC[st] - GC[en]) <= 4.0
    lo, hi = GC[en] - 0.5, GC[st]
    out["f1_unknown"] = any(q == Q[st] and lo <= pg + 5.0 and pg + 0.5 <= hi for q, pg in unloc)
    return out


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
        try:
            g, events, tl, skipped = load_timeline(gid)
        except EmptyGame:
            print("SKIP no tracking frames", gid, GAMES[gid], flush=True)
            meta.setdefault("skipped_games", []).append(GAMES[gid])
            continue
        if CLEANUP and GAMES[gid] not in KEEP_STEMS:
            path = DATA / "json" / GAMES[gid] / f"{gid}.json"
            path.unlink()
            path.parent.rmdir()
        gp = pbp[gid == pbp.GAME_ID]
        # --- join: every PBP row
        for _, row in gp.iterrows():
            e = events.get(int(row.EVENTNUM))
            join_rows.append(
                dict(
                    game=gid,
                    eventnum=int(row.EVENTNUM),
                    msgtype=int(row.EVENTMSGTYPE),
                    period=int(row.PERIOD),
                    pctime=row.PCTIMESTRING,
                    joined=e is not None,
                    ev_q=None if e is None else e[0],
                    ev_gmax=None if e is None else e[1],
                    ev_gmin=None if e is None else e[2],
                    desc=" | ".join(
                        str(x)
                        for x in (
                            row.HOMEDESCRIPTION,
                            row.NEUTRALDESCRIPTION,
                            row.VISITORDESCRIPTION,
                        )
                        if isinstance(x, str)
                    ),
                    p1=int(row.PLAYER1_ID),
                )
            )
        # --- releases for every FGA
        fga = gp[gp.EVENTMSGTYPE.isin([1, 2])]
        votes = {}
        for _, row in fga.iterrows():
            e = events.get(int(row.EVENTNUM))
            rec = dict(
                game=gid,
                eventnum=int(row.EVENTNUM),
                shooter=int(row.PLAYER1_ID),
                team=int(row.PLAYER1_TEAM_ID),
                period=int(row.PERIOD),
                pctime=row.PCTIMESTRING,
                made=int(row.EVENTMSGTYPE == 1),
                joined=e is not None,
                pbp_gc=pc_seconds(row.PCTIMESTRING),
            )
            if e is None:
                rec["reason"] = "not_joined"
                shots_rows.append(rec)
                continue
            pbp_gc = pc_seconds(row.PCTIMESTRING)
            rec["pbp_gc"] = pbp_gc
            idx = window(tl, int(row.PERIOD), pbp_gc + 10.0, pbp_gc - 0.5)
            desc = " ".join(
                str(x) for x in (row.HOMEDESCRIPTION, row.VISITORDESCRIPTION) if isinstance(x, str)
            )
            rec["close"] = is_close(desc)
            rec["three"] = "3PT" in desc
            t_r, t_a, bk, reason = locate_release(
                tl, idx, rec["shooter"], pbp_gc + 2.5, R3 and rec["close"]
            )
            rec.update(reason=reason, t_r=t_r, t_a=t_a, basket_at_arrival=bk)
            if t_r is not None:
                rec["gc_release"] = float(tl["GC"][t_r])
                rec["q_release"] = int(tl["Q"][t_r])
                rec["ball_z_release"] = float(tl["B"][t_r, 2])
                # nearest player to ball at release
                rec["nearest_at_release"] = int(tl["PID"][t_r, tl["dist"][t_r].argmin()])
                sxy = player_xy(tl, t_r, rec["shooter"])
                rec["jump"] = "Jump" in desc
                rec["sc_release"] = None if np.isnan(tl["SC"][t_r]) else float(tl["SC"][t_r])
                if sxy is not None:
                    d_rel = float(np.linalg.norm(sxy - BASKETS[bk]))
                    rec["d_release"] = d_rel
                    rec["zone_release"] = zone_of(sxy, bk, d_rel)
                    rec["open_release_all"] = nearest_opp(tl, t_r, rec["team"], sxy)
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
        vote_purity = {
            f"{t}_{q}": (float(np.mean(np.array(v) == att[(t, q)])), len(v))
            for (t, q), v in votes.items()
        }
        # --- spells and catches for target players present in this game
        sp = spells(tl)
        present = [p for p in TARGETS if (tl["PID"] == p).any()]
        GC, Q, SC = tl["GC"], tl["Q"], tl["SC"]
        catchers = sorted({x[0] for x in sp}) if ALL_PLAYERS else present
        unloc = {}
        for x in shots_rows:
            if x["game"] == gid and x.get("t_r") is None:
                unloc.setdefault(x["shooter"], []).append((x["period"], x["pbp_gc"]))
        my_shots = [s for s in shots_rows if s["game"] == gid and s.get("t_r") is not None]
        for p in catchers:
            psp = [(k, s) for k, s in enumerate(sp) if s[0] == p]
            for k, (o, st, en) in psp:
                ok_pre = (
                    st >= PRE_FRAMES
                    and all(tl["prev_ok"][st - j] for j in range(PRE_FRAMES))
                    and all(tl["ctrl"][st - j] != p for j in range(1, PRE_FRAMES + 1))
                )
                team = team_of(tl, st, p)
                q = int(Q[st])
                bk = att.get((team, q))
                pxy = player_xy(tl, st, p)
                d_b = None if bk is None else float(np.linalg.norm(pxy - BASKETS[bk]))
                sc_run = (
                    st + SC_LAG < tl["n"]
                    and not np.isnan(SC[st])
                    and all(tl["prev_ok"][st + j] for j in range(1, SC_LAG + 1))
                    and SC[st + SC_LAG] < SC[st]
                )
                frontcourt = d_b is not None and d_b <= 47.0
                kk = k - 1
                brief = False
                while (
                    RULE in ("sticky", "d3")
                    and kk >= 0
                    and Q[sp[kk][1]] == q
                    and is_brief_opp(tl, sp[kk], p, st)
                ):
                    kk -= 1
                    brief = True
                prev = sp[kk] if kk >= 0 else None
                if prev is None or Q[prev[1]] != q:
                    src = "none"
                elif prev[0] == p:
                    src = "self"
                else:
                    src = "teammate" if team_of(tl, prev[2], prev[0]) == team else "opponent"
                row = dict(
                    game=gid,
                    player=TARGETS.get(p, "other"),
                    pid=p,
                    start=st,
                    end=en,
                    quarter=q,
                    gc=float(GC[st]),
                    valid_catch=bool(ok_pre),
                    frontcourt=bool(frontcourt),
                    sc_running=bool(sc_run),
                    shot_clock=None if np.isnan(SC[st]) else float(SC[st]),
                    d_basket=d_b,
                    source=src,
                    brief_opp_touch=brief,
                    t_next=float(GC[st] - GC[en]),
                )
                if bk is not None:
                    row["open_catch"] = nearest_opp(tl, st, team, pxy)
                    row["rim_prot"] = nearest_opp(tl, st, team, BASKETS[bk])
                if ALL_PLAYERS:
                    if not (ok_pre and frontcourt and sc_run):
                        continue
                    row["team"] = int(team)
                    row.update(stage3_features(tl, sp, k, p, team, bk, pxy, unloc.get(p, [])))
                catch_rows.append(row)
        meta["games"][gid] = dict(
            file=GAMES[gid],
            frames=tl["n"],
            skipped_moments=skipped,
            events=len(g["events"]),
            events_with_moments=len(events),
            attacking={f"{t}_{q}": b for (t, q), b in att.items()},
            vote_purity=vote_purity,
            present_targets=[TARGETS[p] for p in present],
            n_spells=len(sp),
        )
        # link located target shots to latest spell of shooter at/before t_r with no other spell in between
        for s in my_shots:
            if s["shooter"] not in TARGETS and not ALL_PLAYERS:
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
        print(
            gid,
            GAMES[gid],
            "frames",
            tl["n"],
            "skipped",
            skipped,
            "spells",
            len(sp),
            "targets",
            present,
        )
    shots = pd.DataFrame(shots_rows)
    catches = pd.DataFrame(catch_rows)
    # attach shot outcome to catches
    link = shots[shots["linked"].astype("boolean").fillna(False).astype(bool)]
    key = {
        (r.game, int(r.link_start)): (r.catch_to_shot, r.open_release, r.eventnum)
        for r in link.itertuples()
    }
    catches["catch_to_shot"] = [
        key.get((r.game, r.start), (None,))[0] for r in catches.itertuples()
    ]
    catches["open_release"] = [
        key.get((r.game, r.start), (None, None))[1] for r in catches.itertuples()
    ]
    catches["shot_event"] = [
        key.get((r.game, r.start), (None, None, None))[2] for r in catches.itertuples()
    ]
    shots.to_csv(OUT / "shots.csv", index=False)
    catches.to_csv(OUT / "catches.csv", index=False)
    pd.DataFrame(join_rows).to_csv(OUT / "join_check.csv", index=False)
    (OUT / "build_meta.json").write_text(json.dumps(meta, indent=1, default=str))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", choices=["nearest", "sticky", "d3"], default="nearest")
    ap.add_argument("--games", choices=["pass1", "pass2"], default="pass1")
    ap.add_argument(
        "--stems", default=None, help="file with one archive stem per line; replaces --games"
    )
    ap.add_argument(
        "--cleanup", action="store_true", help="delete each extracted JSON after loading it"
    )
    ap.add_argument("--out", default=None)
    ap.add_argument("--r3", action="store_true", help="close-range release rule R3")
    ap.add_argument(
        "--all-players", action="store_true", help="Stage 3a: counted catches for every player"
    )
    a = ap.parse_args()
    ALL_PLAYERS = a.all_players
    RULE = a.rule
    R3 = a.r3
    CLEANUP = a.cleanup
    KEEP_STEMS = set(GAMES.values()) | set(GAMES_PASS2.values())
    if a.games == "pass2":
        GAMES.update(GAMES_PASS2)
    if a.stems:
        import py7zr

        GAMES.clear()
        for stem in Path(a.stems).read_text().split():
            with py7zr.SevenZipFile(DATA / "raw" / f"{stem}.7z") as z:
                names = z.getnames()
            if not names:
                print("SKIP empty archive", stem)
                continue
            assert len(names) == 1 and names[0].endswith(".json") and "/" not in names[0], names
            GAMES[names[0][:-5]] = stem
    if a.out:
        OUT = Path(a.out).resolve()
    main()
