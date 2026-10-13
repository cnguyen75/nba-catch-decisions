"""Possession points and score margin for each counted catch (rule registered d3460a7).

  poss.py build    writes out/s3/poss.csv (game, pid, start, poss_points, end_type, end_eventnum, margin)
  poss.py check    prints 20 random train/validation league catches with their PBP rows (seed 20)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = Path.home() / "Documents" / "nba-tracking"
TARGET_IDS = {201939, 2544, 201935}


def secs(s):
    m, x = s.split(":")
    return int(m) * 60 + int(x)


def load_pbp(games):
    p = pd.read_csv(DATA / "pbp" / "2015-16_pbp.csv", dtype={"GAME_ID": str})
    p = p[p.GAME_ID.isin(games)].copy()
    p["gc"] = p.PCTIMESTRING.map(secs)
    p["desc"] = p.HOMEDESCRIPTION.fillna("") + " | " + p.VISITORDESCRIPTION.fillna("")
    team = p.PLAYER1_TEAM_ID.copy()
    is_team = p.PLAYER1_ID >= 1610612737
    team[team.isna() & is_team] = p.PLAYER1_ID[team.isna() & is_team]
    p["team"] = team
    return {g: d.sort_values("EVENTNUM").reset_index(drop=True) for g, d in p.groupby("GAME_ID")}


def possession(rows, period, gc_catch, off, home):
    """Return (points, end_type, end_eventnum, margin_offence)."""
    per = rows[rows.PERIOD == period]
    after = per[per.gc < gc_catch]
    before = rows[(rows.PERIOD < period) | ((rows.PERIOD == period) & (rows.gc >= gc_catch))]
    sc = before.SCORE.dropna()
    if len(sc):
        v, h = (int(x) for x in sc.iloc[-1].split(" - "))
    else:
        v, h = 0, 0
    margin = (h - v) if off == home else (v - h)
    pts = 0
    pending_fg_clock = None
    for r in after.itertuples():
        t = r.EVENTMSGTYPE
        mine = r.team == off
        if pending_fg_clock is not None and not (t == 3 and mine and r.PCTIMESTRING == pending_fg_clock) and t not in (6, 8, 9, 18):
            return pts, "made_fg", prev_ev, margin
        if t == 1 and mine:
            pts += 3 if "3PT" in r.desc else 2
            pending_fg_clock, prev_ev = r.PCTIMESTRING, r.EVENTNUM
            continue
        if t == 3 and mine:
            made = not any(part.strip().startswith("MISS") for part in r.desc.split("|") if "Free Throw" in part)
            pts += int(made)
            if pending_fg_clock is not None:
                prev_ev = r.EVENTNUM
                continue
            last = any(k in r.desc for k in ("1 of 1", "2 of 2", "3 of 3")) and "Technical" not in r.desc
            if last and made:
                return pts, "last_ft_made", r.EVENTNUM, margin
            continue
        if t == 4 and r.team != off and not np.isnan(r.team):
            return pts, "def_rebound", r.EVENTNUM, margin
        if t == 5 and mine:
            return pts, "turnover", r.EVENTNUM, margin
        if t == 13:
            return pts, "period_end", r.EVENTNUM, margin
    if pending_fg_clock is not None:
        return pts, "made_fg", prev_ev, margin
    return pts, "no_end_found", None, margin


def build():
    c = pd.read_csv(ROOT / "out/s3/catches.csv", dtype={"game": str})
    meta = json.loads((ROOT / "out/s3/build_meta.json").read_text())["games"]
    pbp = load_pbp(set(c.game))
    homes = {}
    for g in set(c.game):
        r = pbp[g]
        hd = r[r.HOMEDESCRIPTION.notna() & r.PLAYER1_TEAM_ID.notna()]
        homes[g] = int(hd.PLAYER1_TEAM_ID.mode().iloc[0])
    out = []
    for r in c.itertuples():
        pts, et, ev, mg = possession(pbp[r.game], r.quarter, r.gc, r.team, homes[r.game])
        out.append((r.game, r.pid, r.start, pts, et, ev, mg))
    df = pd.DataFrame(out, columns=["game", "pid", "start", "poss_points", "end_type", "end_eventnum", "margin"])
    df.to_csv(ROOT / "out/s3/poss.csv", index=False)
    print(df.end_type.value_counts(normalize=True).round(3).to_dict(), df.poss_points.mean().round(3))


def check():
    split = json.loads((ROOT / "checks/split.json").read_text())["split"]
    c = pd.read_csv(ROOT / "out/s3/catches.csv", dtype={"game": str})
    ps = pd.read_csv(ROOT / "out/s3/poss.csv", dtype={"game": str})
    c = c.merge(ps, on=["game", "pid", "start"])
    c = c[~c.pid.isin(TARGET_IDS) & c.game.map(lambda g: split[g] in ("train", "validation"))]
    pick = c.sample(20, random_state=20)
    pbp = load_pbp(set(pick.game))
    for i, r in enumerate(pick.itertuples()):
        rows = pbp[r.game]
        per = rows[rows.PERIOD == r.quarter]
        near = per[(per.gc <= r.gc + 8) & (per.gc >= r.gc - 30)]
        print(f"\n=== P{i:02d} game {r.game} Q{r.quarter} catch gc={r.gc:.1f} ({int(r.gc)//60}:{int(r.gc)%60:02d}) offence team {r.team} "
              f"-> points {r.poss_points}, end {r.end_type} at event {r.end_eventnum}, margin {r.margin}")
        for x in near.itertuples():
            mark = "<-- END" if x.EVENTNUM == r.end_eventnum else ""
            print(f"   ev{x.EVENTNUM:4d} {x.PCTIMESTRING:>5} t{x.EVENTMSGTYPE:2d} team {int(x.team) if not np.isnan(x.team) else '-'} "
                  f"score {x.SCORE if isinstance(x.SCORE, str) else '':7} {x.desc[:90]} {mark}")


if __name__ == "__main__":
    {"build": build, "check": check}[sys.argv[1]]()
