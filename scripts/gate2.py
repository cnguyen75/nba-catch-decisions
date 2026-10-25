"""Second-pass gate (registered 4a18241, C1a aefe72f). Reads out/v2/, writes out/v2/results.json."""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).parent))
from gate import BANDS, MIN_CATCHES, counted, crit2, iqr  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "v2"
CURRY_GAMES = [
    "0021500003",
    "0021500035",
    "0021500051",
    "0021500069",
    "0021500083",
    "0021500092",
    "0021500104",
    "0021500120",
    "0021500125",
    "0021500144",
]
PLAYERS = {"Curry": 201939, "LeBron": 2544, "Harden": 201935}


def label(n: int, c1: bool, c2: bool, c3: bool, ci: list[float]) -> str:
    lo, hi = ci
    if n < MIN_CATCHES:
        return "sample too small"
    if not c1:
        return "no variation"
    if c1 and c2 and c3:
        return "pass"
    if hi < 0.10:
        return "no prediction"
    if lo <= 0 <= hi and lo <= 0.10 <= hi:
        return "underpowered"
    reasons = []
    if c2 and not c3:
        reasons.append("criteria 1 and 2 hold, criterion 3 fails")
    if not c2 and lo > 0:
        reasons.append("CI excludes 0 and includes +0.10, point gap below 0.10")
    return "unlabelled: " + ("; ".join(reasons) or "other")


def evaluate(cnt: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    r = {
        "counted_catches": int(len(cnt)),
        "games": sorted(cnt.game.unique().tolist()),
        "source": cnt.source.value_counts().to_dict(),
        "brief_opp_touch_relabelled": int(cnt.brief_opp_touch.fillna(False).astype(bool).sum()),
    }
    r["catches_per_game"] = len(cnt) / len(r["games"])
    bands, c1 = {}, True
    for lab, lo, hi in BANDS:
        x = cnt[(cnt.d_basket >= lo) & (cnt.d_basket < hi)]
        b = {"n": int(len(x))}
        if len(x):
            q, q1, q3 = iqr(x.open_catch.values)
            b.update(
                iqr=q,
                q1=q1,
                median=float(x.open_catch.median()),
                q3=q3,
                p_cs=float(x.cs.mean()),
                p_shot4=float(x.shot4.mean()),
            )
        if len(x) >= 10 and b["iqr"] < 3.0:
            c1 = False
        if lab == "22+" and len(x) < 10:
            c1 = False
        bands[lab] = b
    r["bands"] = bands
    far = cnt[(cnt.d_basket >= 22) & (cnt.d_basket < 30)]
    c2 = crit2(far, rng)
    o, y = far.open_catch.values, far.cs.values
    lo_c, hi_c = np.quantile(o, [1 / 3, 2 / 3])
    c2.update(
        p_cs_bottom=float(y[o <= lo_c].mean()),
        p_cs_top=float(y[o > hi_c].mean()),
        n_bottom=int((o <= lo_c).sum()),
        n_top=int((o > hi_c).sum()),
        cut_ft=[float(lo_c), float(hi_c)],
    )
    r["crit2_22_30"] = c2
    share4 = float(cnt.shot4.mean())
    c3 = 0.20 <= share4 <= 0.80
    r["crit3"] = {"share_shot4": share4, "share_cs": float(cnt.cs.mean())}
    r["criteria"] = {
        "1_variation": bool(c1),
        "2_prediction": bool(c2["passes"]),
        "3_choice": bool(c3),
    }
    r["label_if_gated"] = label(len(cnt), c1, c2["passes"], c3, c2["ci95"])
    sh = cnt[cnt.catch_to_shot.notna()]
    r["descriptive"] = {
        "open_catch_q1_med_q3": np.quantile(cnt.open_catch, [0.25, 0.5, 0.75]).round(2).tolist(),
        "rim_prot_median": float(cnt.rim_prot.median()),
        "shot_clock_median": float(cnt.shot_clock.median()),
        "t_next_median": float(cnt.t_next.median()),
        "shots_linked_to_counted_catch": int(len(sh)),
        "open_catch_median_on_shots": float(sh.open_catch.median()),
        "open_release_median": float(sh.open_release.median()),
        "corr_open_catch_release": float(np.corrcoef(sh.open_catch, sh.open_release)[0, 1]),
    }
    return r


def main() -> None:
    c = pd.read_csv(OUT / "catches.csv", dtype={"game": str})
    s = pd.read_csv(OUT / "shots.csv", dtype={"game": str})
    old = pd.read_csv(ROOT / "out" / "catches.csv", dtype={"game": str})
    rng = np.random.default_rng(0)
    res = {
        "git_commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "eye_check_c1": json.loads((ROOT / "checks" / "eye_c1.json").read_text()),
    }
    two = ["0021500003", "0021500035"]
    ba = {}
    for lab, d in (("before_nearest_rule", old), ("after_c1_c1a", c)):
        d = d[(d.pid == 201939) & d.game.isin(two)]
        k = d[d.valid_catch & d.frontcourt & d.sc_running]
        ba[lab] = {
            "spells": int(len(d)),
            "valid_catches": int(d.valid_catch.sum()),
            "counted": int(len(k)),
            "source": k.source.value_counts().to_dict(),
            "linked_shots": int(k.catch_to_shot.notna().sum()),
        }
    res["curry_two_games_before_after"] = ba
    s["located"] = s.reason.str.startswith("ok")
    cs = s[(s.shooter == 201939) & s.game.isin(CURRY_GAMES)]
    res["curry_release"] = {"fga": int(len(cs)), "located": int(cs.located.sum())}
    res["players"] = {}
    for name, pid in PLAYERS.items():
        cnt = counted(c, pid)
        if name == "Curry":
            cnt = cnt[cnt.game.isin(CURRY_GAMES)]
        r = evaluate(cnt, rng)
        r["gated"] = name == "Curry"
        res["players"][name] = r
    res["verdict_curry"] = res["players"]["Curry"]["label_if_gated"]
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
