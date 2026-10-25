"""Stage 2 descriptive numbers on the full D1-D3 set (out/full). No model. Writes out/full/describe.json."""

import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "full"
PLAYERS = {"Curry": 201939, "LeBron": 2544, "Harden": 201935}
BANDS = [("0-10", 0, 10), ("10-22", 10, 22), ("22-30", 22, 30), ("30-47", 30, 47.0001)]
N_BOOT = 10_000


def q(x, ps=(0.25, 0.5, 0.75)):
    return [round(float(v), 2) for v in np.quantile(x, ps)] if len(x) else None


def prop_ci(y, rng):
    y = np.asarray(y)
    if len(y) == 0:
        return None
    b = rng.choice(y, (N_BOOT, len(y))).mean(1)
    return [round(float(y.mean()), 3), [round(float(v), 3) for v in np.quantile(b, [0.025, 0.975])]]


def gap_ci(o, y, rng):
    def gap(o, y):
        lo, hi = np.quantile(o, [1 / 3, 2 / 3])
        return y[o > hi].mean() - y[o <= lo].mean()

    bs = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(o), len(o))
        bs.append(gap(o[i], y[i]))
    return [
        round(float(gap(o, y)), 3),
        [round(float(v), 3) for v in np.nanquantile(bs, [0.025, 0.975])],
    ]


def main():
    c = pd.read_csv(OUT / "catches.csv", dtype={"game": str})
    s = pd.read_csv(OUT / "shots.csv", dtype={"game": str})
    meta = json.loads((OUT / "build_meta.json").read_text())
    rng = np.random.default_rng(0)
    res = {
        "git_commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "games_built": len(meta["games"]),
        "frames_per_game": q([g["frames"] for g in meta["games"].values()], (0, 0.5, 1)),
        "skipped_moments_per_game": q(
            [g["skipped_moments"] for g in meta["games"].values()], (0, 0.5, 1)
        ),
        "players": {},
    }
    s["located"] = s.reason.str.startswith("ok")
    res["release_located_all"] = [int(s.located.sum()), int(s.joined.sum())]
    for name, pid in PLAYERS.items():
        pc = c[c.pid == pid]
        games = sorted(pc.game.unique())
        cnt = pc[pc.valid_catch & pc.frontcourt & pc.sc_running].copy()
        cnt["cs"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 1.5)).astype(int)
        cnt["shot4"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 4.0)).astype(int)
        per_game = cnt.groupby("game").size().reindex(games, fill_value=0)
        med = per_game.median()
        r = {
            "games": len(games),
            "counted_catches": int(len(cnt)),
            "catches_per_game": {
                "mean": round(float(per_game.mean()), 1),
                "sd": round(float(per_game.std()), 1),
                "min_med_max": q(per_game.values, (0, 0.5, 1)),
                "outlier_games": {
                    g: int(v) for g, v in per_game.items() if v < 0.5 * med or v > 1.5 * med
                },
            },
            "source": cnt.source.value_counts().to_dict(),
            "share_shot4": round(float(cnt.shot4.mean()), 3),
            "share_cs": round(float(cnt.cs.mean()), 3),
        }
        r["open_catch_by_band"] = {}
        for lab, lo, hi in BANDS:
            x = cnt[(cnt.d_basket >= lo) & (cnt.d_basket < hi)]
            r["open_catch_by_band"][lab] = {
                "n": int(len(x)),
                "q1_med_q3_ft": q(x.open_catch),
                "iqr_ft": round(float(np.subtract(*np.quantile(x.open_catch, [0.75, 0.25]))), 2)
                if len(x)
                else None,
                "rim_prot_med_ft": round(float(x.rim_prot.median()), 2) if len(x) else None,
            }
        far = cnt[(cnt.d_basket >= 22) & (cnt.d_basket < 30)]
        o, ycs, y4 = far.open_catch.values, far.cs.values, far.shot4.values
        lo, hi = np.quantile(o, [1 / 3, 2 / 3])
        thirds = {}
        for lab, m in (("tight", o <= lo), ("middle", (o > lo) & (o <= hi)), ("open", o > hi)):
            thirds[lab] = {
                "n": int(m.sum()),
                "openness_range_ft": [round(float(o[m].min()), 2), round(float(o[m].max()), 2)],
                "p_shot_1p5s": prop_ci(ycs[m], rng),
                "p_shot_4s": prop_ci(y4[m], rng),
            }
        r["band_22_30"] = {
            "n": int(len(far)),
            "tercile_cuts_ft": [round(float(lo), 2), round(float(hi), 2)],
            "by_third": thirds,
            "gap_open_minus_tight_1p5s": gap_ci(o, ycs, rng),
            "gap_open_minus_tight_4s": gap_ci(o, y4, rng),
        }
        sh = cnt[cnt.catch_to_shot.notna()]
        hist, edges = np.histogram(sh.catch_to_shot, bins=np.arange(0, 24.5, 0.5))
        fine, fedges = np.histogram(
            sh.catch_to_shot[sh.catch_to_shot <= 4], bins=np.arange(0, 4.04, 0.08)
        )
        r["catch_to_shot"] = {
            "n_shots_after_counted_catch": int(len(sh)),
            "q1_med_q3_s": q(sh.catch_to_shot),
            "share_within_1p5s": round(float((sh.catch_to_shot <= 1.5).mean()), 3),
            "hist_0p5s": dict(zip([f"{e:.1f}" for e in edges[:-1]], hist.tolist())),
            "max_bin_share_0p08s_within_4s": round(float(fine.max() / max(fine.sum(), 1)), 3),
            "below_0p3s": int((sh.catch_to_shot < 0.3).sum()),
        }
        r["catch_vs_release"] = {
            "n": int(len(sh)),
            "open_catch_med_ft": round(float(sh.open_catch.median()), 2),
            "open_release_med_ft": round(float(sh.open_release.median()), 2),
            "corr": round(float(np.corrcoef(sh.open_catch, sh.open_release)[0, 1]), 3),
            "share_release_tighter": round(float((sh.open_release < sh.open_catch).mean()), 3),
            "by_band_22_30": {
                "n": int(len(sh[(sh.d_basket >= 22) & (sh.d_basket < 30)])),
                "open_catch_med_ft": round(
                    float(sh[(sh.d_basket >= 22) & (sh.d_basket < 30)].open_catch.median()), 2
                ),
                "open_release_med_ft": round(
                    float(sh[(sh.d_basket >= 22) & (sh.d_basket < 30)].open_release.median()), 2
                ),
            },
        }
        ps = s[s.shooter == pid]
        r["shots"] = {
            "pbp_fga": int(len(ps)),
            "located": int(ps.located.sum()),
            "linked_to_counted_catch": int(len(sh)),
        }
        # artefact checks
        r["artefacts"] = {
            "catches_per_quarter_per_game": {
                int(k): round(v / len(games), 2)
                for k, v in cnt.quarter.value_counts().sort_index().items()
            },
            "t_next_below_0p3s_share": round(float((cnt.t_next < 0.3).mean()), 3),
            "d_basket_45_47_share": round(float((cnt.d_basket >= 45).mean()), 3),
            "open_catch_below_1ft_share": round(float((cnt.open_catch < 1).mean()), 3),
            "brief_opp_touch_share": round(
                float(cnt.brief_opp_touch.fillna(False).astype(bool).mean()), 3
            ),
        }
        res["players"][name] = r
    (OUT / "describe.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
