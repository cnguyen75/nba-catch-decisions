"""Stage 6 PBP-derived state (registered 811c61b): rhythm (m3, m5, none_yet, last_made,
t_since_make), first_made, relative openness, heights table (by PBP id via names), back-to-back.
Writes out/s6/state_catches.csv, out/s6/state_shots.csv, out/s6/heights.csv,
out/s6/state_report.json.
"""

import json
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
EXT = Path.home() / "Documents" / "nba-tracking" / "ext"
OUT = ROOT / "out" / "s6"


def elapsed(period: pd.Series | np.ndarray, t: pd.Series | np.ndarray) -> np.ndarray:
    period = np.asarray(period, float)
    t = np.asarray(t, float)
    return np.where(
        period <= 4, (period - 1) * 720 + (720 - t), 2880 + (period - 5) * 300 + (300 - t)
    )


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", s)
    return re.sub(r"[^a-z]", "", s)


def rhythm_for(
    att_el: np.ndarray, att_made: np.ndarray, query_el: np.ndarray, strict_before: bool = True
) -> dict[str, np.ndarray]:
    """For each query time, features from attempts with elapsed < query time (sorted attempts)."""
    k = np.searchsorted(att_el, query_el, side="left")  # number of prior attempts
    cm = np.r_[0, np.cumsum(att_made)]
    m3 = cm[k] - cm[np.maximum(k - 3, 0)]
    m5 = cm[k] - cm[np.maximum(k - 5, 0)]
    if len(att_made) == 0:
        nan = np.full(len(query_el), np.nan)
        return dict(
            n_prior=k,
            m3=m3,
            m5=m5,
            none_yet=np.ones(len(query_el), int),
            last_made=nan,
            t_since_make=np.full(len(query_el), 24.0),
            first_made=nan,
        )
    last_made = np.where(k > 0, att_made[np.maximum(k - 1, 0)], np.nan)
    first_made = np.where(k > 0, att_made[0], np.nan)
    make_el = att_el[att_made == 1]
    j = np.searchsorted(make_el, query_el, side="left")
    tsm = (
        np.where(j > 0, (query_el - make_el[np.maximum(j - 1, 0)]) / 60.0, 24.0)
        if len(make_el)
        else np.full(len(query_el), 24.0)
    )
    return dict(
        n_prior=k,
        m3=m3,
        m5=m5,
        none_yet=(k == 0).astype(int),
        last_made=last_made,
        t_since_make=np.minimum(tsm, 24.0),
        first_made=first_made,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sp = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    s = pd.read_csv(ROOT / "out/s4/shots.csv", dtype={"game": str})
    s = s[s.game.map(sp) != "test"].copy()
    loc = s.gc_release.notna()
    # attempt time: release clock if located, else PBP clock + 2.5 s (PBP lags the release)
    s["att_el"] = np.where(
        loc, elapsed(s.q_release.fillna(s.period), s.gc_release), elapsed(s.period, s.pbp_gc + 2.5)
    )
    c = pd.read_csv(
        ROOT / "out/s4/catches.csv",
        dtype={"game": str},
        usecols=["game", "pid", "start", "team", "quarter", "gc", "open_catch"],
    )
    c = c[c.game.map(sp) != "test"].copy()
    c["el"] = elapsed(c.quarter, c.gc)
    rows_c, rows_s = [], []
    for (g, p), att in s.sort_values("att_el").groupby(["game", "shooter"]):
        ael, am = att.att_el.to_numpy(float), att.made.to_numpy(int)
        f = rhythm_for(ael, am, ael - 1e-6)  # for shots: attempts strictly before
        rows_s.append(pd.DataFrame({"game": g, "eventnum": att.eventnum.to_numpy(), **f}))
    st = pd.concat(rows_s)
    att_by = {
        k: (v.att_el.to_numpy(float), v.made.to_numpy(int))
        for k, v in s.sort_values("att_el").groupby(["game", "shooter"])
    }
    out = []
    for (g, p), cc in c.groupby(["game", "pid"]):
        ael, am = att_by.get((g, p), (np.array([]), np.array([], int)))
        f = rhythm_for(ael, am, cc.el.to_numpy(float) - 0.04)
        out.append(pd.DataFrame({"game": g, "pid": p, "start": cc.start.to_numpy(), **f}))
    sc = pd.concat(out)
    # relative openness: team running mean of capped openness over earlier counted catches this game
    c = c.sort_values(["game", "team", "el"])
    oc = c.open_catch.clip(upper=15)
    grp = oc.groupby([c.game, c.team])
    prior_sum = grp.cumsum() - oc
    prior_n = grp.cumcount()
    league_mean = float(oc.mean())
    c["team_mean_open"] = np.where(prior_n > 0, prior_sum / prior_n.replace(0, 1), league_mean)
    c["first_team_catch"] = (prior_n == 0).astype(int)
    c["rel_open"] = oc - c.team_mean_open
    sc = sc.merge(
        c[["game", "pid", "start", "team_mean_open", "rel_open", "first_team_catch"]],
        on=["game", "pid", "start"],
        how="left",
    )
    gm = pd.read_csv(EXT / "games" / "games.csv")
    gm = gm[(gm.SEASON == 2015) & (gm.GAME_ID.astype(str).str.startswith("215"))]
    gm["date"] = pd.to_datetime(gm.GAME_DATE_EST)
    tg = pd.concat(
        [
            gm[["GAME_ID", "date", "HOME_TEAM_ID"]].rename(columns={"HOME_TEAM_ID": "team"}),
            gm[["GAME_ID", "date", "VISITOR_TEAM_ID"]].rename(columns={"VISITOR_TEAM_ID": "team"}),
        ]
    ).sort_values(["team", "date"])
    tg["b2b"] = (tg.groupby("team").date.diff().dt.days == 1).astype(int)
    tg["game"] = "00" + tg.GAME_ID.astype(str)
    b2b = tg.set_index(["game", "team"]).b2b.to_dict()
    cteam = c.set_index(["game", "pid", "start"]).team
    sc["b2b"] = [
        b2b.get((g, int(cteam[(g, p, s_)])), np.nan) for g, p, s_ in zip(sc.game, sc.pid, sc.start)
    ]
    st = st.merge(s[["game", "eventnum", "team"]], on=["game", "eventnum"], how="left")
    st["b2b"] = [b2b.get((g, int(t)), np.nan) for g, t in zip(st.game, st.team)]
    # heights: PBP id -> name -> height (2015-16)
    pbp = pd.read_csv(
        Path.home() / "Documents/nba-tracking/pbp/2015-16_pbp.csv",
        usecols=[
            "PLAYER1_ID",
            "PLAYER1_NAME",
            "PLAYER2_ID",
            "PLAYER2_NAME",
            "PLAYER3_ID",
            "PLAYER3_NAME",
        ],
    )
    ids = pd.concat(
        [
            pbp[[f"PLAYER{k}_ID", f"PLAYER{k}_NAME"]].set_axis(["pid", "name"], axis=1)
            for k in (1, 2, 3)
        ]
    ).dropna()
    ids = ids[(ids.pid > 0) & (ids.pid < 1610612737)].drop_duplicates("pid")
    ht = pd.read_csv(EXT / "heights" / "all_seasons.csv")
    ht = (
        ht[ht.season == "2015-16"]
        .assign(key=lambda x: x.player_name.map(norm))
        .drop_duplicates("key")
    )
    hmap = dict(zip(ht.key, ht.player_height))
    ids["height_cm"] = ids.name.map(lambda n: hmap.get(norm(n), np.nan))
    ids[["pid", "name", "height_cm"]].to_csv(OUT / "heights.csv", index=False)
    rep = {
        "pbp_players": int(len(ids)),
        "height_coverage_players": round(float(ids.height_cm.notna().mean()), 4),
        "league_mean_open_capped": round(league_mean, 3),
        "b2b_share_catches": round(float(np.nanmean(sc.b2b)), 4),
        "b2b_missing_catches": int(np.isnan(sc.b2b.astype(float)).sum()),
    }
    sc.to_csv(OUT / "state_catches.csv", index=False)
    st.to_csv(OUT / "state_shots.csv", index=False)
    (OUT / "state_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1), len(sc), len(st))


if __name__ == "__main__":
    main()
