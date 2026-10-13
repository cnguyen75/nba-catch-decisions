"""Compute the pre-registered gate from out/catches.csv and out/shots.csv. Writes out/results.json."""
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "out"
BANDS = [("0-10", 0, 10), ("10-22", 10, 22), ("22+", 22, 47.0001)]
TARGET_IDS = {"Curry": 201939, "LeBron": 2544, "Harden": 201935}
MIN_CATCHES = 60
N_BOOT = 10_000


def iqr(x):
    q1, q3 = np.quantile(x, [0.25, 0.75])
    return float(q3 - q1), float(q1), float(q3)


def tercile_gap(openness, cs):
    lo, hi = np.quantile(openness, [1 / 3, 2 / 3])
    bot, top = cs[openness <= lo], cs[openness > hi]
    if len(bot) == 0 or len(top) == 0:
        return np.nan, len(bot), len(top)
    return float(top.mean() - bot.mean()), len(bot), len(top)


def main():
    c = pd.read_csv(OUT / "catches.csv", dtype={"game": str})
    s = pd.read_csv(OUT / "shots.csv", dtype={"game": str})
    rng = np.random.default_rng(0)
    res = {"git_commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                                        text=True, cwd=OUT.parent).stdout.strip(), "players": {}}
    s["located"] = s.reason.str.startswith("ok")
    res["join"] = {"fga_pbp": int(len(s)), "fga_joined": int(s.joined.sum())}
    res["release"] = {"located": int(s.located.sum()), "of_joined": int(s.joined.sum()),
                      "reasons": s.reason.value_counts().to_dict()}
    for name, pid in TARGET_IDS.items():
        pc = c[c.pid == pid].copy()
        games = sorted(pc.game.unique())
        n_games = len(games)
        cnt = pc[pc.valid_catch & pc.frontcourt & pc.sc_running].copy()
        cnt["cs"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 1.5)).astype(int)
        cnt["shot4"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 4.0)).astype(int)
        n = len(cnt)
        r = {"games": games, "spells_all": int(len(pc)), "valid_catches": int(pc.valid_catch.sum()),
             "counted_catches": n, "catches_per_game": n / n_games if n_games else None,
             "excluded": {"no_valid_pre_window": int((~pc.valid_catch).sum()),
                          "backcourt": int((pc.valid_catch & ~pc.frontcourt).sum()),
                          "shot_clock_not_running": int((pc.valid_catch & pc.frontcourt & ~pc.sc_running).sum())},
             "source": cnt.source.value_counts().to_dict()}
        # bands
        bands = {}
        crit1_ok = True
        for lab, lo, hi in BANDS:
            x = cnt[(cnt.d_basket >= lo) & (cnt.d_basket < hi)]
            b = {"n": int(len(x))}
            if len(x) >= 1:
                q, q1, q3 = iqr(x.open_catch.values)
                b.update(iqr=q, q1=q1, median=float(x.open_catch.median()), q3=q3,
                         p_cs=float(x.cs.mean()), p_shot4=float(x.shot4.mean()))
            if len(x) >= 10 and b["iqr"] < 3.0:
                crit1_ok = False
            if lab == "22+" and len(x) < 10:
                crit1_ok = False
            bands[lab] = b
        r["bands"] = bands
        # criterion 2
        far = cnt[cnt.d_basket >= 22]
        c2 = {"n": int(len(far))}
        if len(far) >= 6:
            o, y = far.open_catch.values, far.cs.values
            gap, nb, nt = tercile_gap(o, y)
            boots = []
            for _ in range(N_BOOT):
                i = rng.integers(0, len(o), len(o))
                boots.append(tercile_gap(o[i], y[i])[0])
            boots = np.array(boots)
            boots = boots[~np.isnan(boots)]
            lo95, hi95 = np.quantile(boots, [0.025, 0.975])
            c2.update(gap_top_minus_bottom=gap, n_bottom=nb, n_top=nt, ci95=[float(lo95), float(hi95)],
                      p_cs_bottom=float(y[o <= np.quantile(o, 1 / 3)].mean()),
                      p_cs_top=float(y[o > np.quantile(o, 2 / 3)].mean()),
                      cut_ft=[float(np.quantile(o, 1 / 3)), float(np.quantile(o, 2 / 3))])
            crit2_ok = abs(gap) >= 0.10 and (lo95 > 0 or hi95 < 0)
        else:
            crit2_ok = False
        r["crit2"] = c2
        share4 = float(cnt.shot4.mean()) if n else None
        crit3_ok = share4 is not None and 0.20 <= share4 <= 0.80
        r["crit3"] = {"share_shot4": share4, "share_cs": float(cnt.cs.mean()) if n else None}
        r["criteria"] = {"1_variation": crit1_ok, "2_prediction": crit2_ok, "3_choice": crit3_ok}
        r["enough_catches"] = n >= MIN_CATCHES
        r["passes"] = bool(crit1_ok and crit2_ok and crit3_ok and n >= MIN_CATCHES)
        r["games_needed_for_60"] = math.ceil(MIN_CATCHES / r["catches_per_game"]) if n else None
        # descriptives
        r["descriptive"] = {
            "open_catch_all": dict(zip(["q1", "median", "q3"], np.quantile(cnt.open_catch, [.25, .5, .75]).round(2).tolist())) if n else None,
            "rim_prot_median": float(cnt.rim_prot.median()) if n else None,
            "t_next_median": float(cnt.t_next.median()) if n else None,
            "shot_clock_median": float(cnt.shot_clock.median()) if n else None,
        }
        ps = s[s.shooter == pid]
        linked = ps.get("linked", pd.Series(dtype=object)).astype("boolean").fillna(False).astype(bool)
        linked_counted = cnt.catch_to_shot.notna().sum()
        sh = cnt[cnt.catch_to_shot.notna()]
        r["shots"] = {"pbp_fga": int(len(ps)), "located": int(ps.located.sum()),
                      "linked_to_any_spell": int(linked.sum()),
                      "linked_to_counted_catch": int(linked_counted),
                      "unlinked_or_unlocated": int(len(ps) - linked.sum()),
                      "open_catch_median_on_shots": float(sh.open_catch.median()) if len(sh) else None,
                      "open_release_median": float(sh.open_release.median()) if len(sh) else None,
                      "corr_open_catch_release": float(np.corrcoef(sh.open_catch, sh.open_release)[0, 1]) if len(sh) > 2 else None,
                      "catch_to_shot_median": float(sh.catch_to_shot.median()) if len(sh) else None}
        res["players"][name] = r
    passing = [k for k, v in res["players"].items() if v["passes"]]
    enough = [k for k, v in res["players"].items() if v["enough_catches"]]
    if passing:
        verdict = "pass"
    elif not enough:
        verdict = "sample too small"
    else:
        verdict = "fail"
    res["verdict"] = verdict
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
