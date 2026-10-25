"""Compute the pre-registered gate from out/catches.csv and out/shots.csv. Writes out/results.json."""

import json
import math
from pathlib import Path
import subprocess
from typing import Any

import numpy as np
import pandas as pd


OUT = Path(__file__).resolve().parent.parent / "out"
BANDS = [("0-10", 0, 10), ("10-22", 10, 22), ("22+", 22, 47.0001)]
TARGET_IDS = {"Curry": 201939, "LeBron": 2544, "Harden": 201935}
MIN_CATCHES = 60
N_BOOT = 10_000


def iqr(x: np.ndarray) -> tuple[float, float, float]:
    q1, q3 = np.quantile(x, [0.25, 0.75])
    return float(q3 - q1), float(q1), float(q3)


def tercile_gap(openness: np.ndarray, cs: np.ndarray) -> tuple[float, int, int]:
    lo, hi = np.quantile(openness, [1 / 3, 2 / 3])
    bot, top = cs[openness <= lo], cs[openness > hi]
    if len(bot) == 0 or len(top) == 0:
        return np.nan, len(bot), len(top)
    return float(top.mean() - bot.mean()), len(bot), len(top)


def counted(c: pd.DataFrame, pid: int) -> pd.DataFrame:
    cnt = c[(c.pid == pid) & c.valid_catch & c.frontcourt & c.sc_running].copy()
    cnt["cs"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 1.5)).astype(int)
    cnt["shot4"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 4.0)).astype(int)
    return cnt


def crit2(far: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    o, y = far.open_catch.values, far.cs.values
    gap = tercile_gap(o, y)[0]
    boots = np.array(
        [
            tercile_gap(o[i], y[i])[0]
            for i in (rng.integers(0, len(o), len(o)) for _ in range(N_BOOT))
        ]
    )
    lo95, hi95 = np.quantile(boots[~np.isnan(boots)], [0.025, 0.975])
    return dict(
        n=int(len(far)),
        gap=float(gap),
        ci95=[float(lo95), float(hi95)],
        p_cs=float(y.mean()),
        passes=bool(abs(gap) >= 0.10 and (lo95 > 0 or hi95 < 0)),
    )


def sensitivity(c: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    """POST HOC, not part of the verdict. (a) catches from a teammate's pass only (drops 'opponent' catches,
    mostly a defender momentarily nearest the ball); (b) criterion 2 on catches 22-30 ft out."""
    out = {}
    for name, pid in TARGET_IDS.items():
        cnt = counted(c, pid)
        tm = cnt[cnt.source == "teammate"]
        out[name] = {
            "teammate_only": dict(
                n=int(len(tm)),
                share_shot4=float(tm.shot4.mean()),
                iqr_by_band={
                    lab: (iqr(x.open_catch.values)[0] if len(x) >= 10 else None, int(len(x)))
                    for lab, lo, hi in BANDS
                    for x in [tm[(tm.d_basket >= lo) & (tm.d_basket < hi)]]
                },
                crit2_22plus=crit2(tm[tm.d_basket >= 22], rng),
            ),
            "crit2_22_to_30ft": crit2(cnt[(cnt.d_basket >= 22) & (cnt.d_basket < 30)], rng),
        }
    return out


def power_crit2(res: dict[str, Any], reps: int = 500, seed: int = 0) -> dict[str, Any]:
    """Simulated power of criterion 2 for a true top-minus-bottom tercile gap of 15 or 20 pp centred on the
    player's own 22+ catch-and-shoot rate. (A true gap of exactly 10 pp caps power at 50%, since the rule
    needs the estimate itself to reach 10 pp.) Planning number only; 200 bootstrap draws per replicate."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, r in res["players"].items():
        base = r["bands"]["22+"]["p_cs"]
        per_game = r["bands"]["22+"]["n"] / len(r["games"])
        entry = dict(base_p_cs=base, catches22_per_game=per_game)
        for true_gap in (0.15, 0.20):
            pb, pt = max(base - true_gap / 2, 0.0), base + true_gap / 2
            table = {}
            for n in (60, 120, 240, 480, 960):
                m = n // 3
                hits = 0
                for _ in range(reps):
                    y = np.r_[rng.random(m) < pb, rng.random(m) < base, rng.random(m) < pt].astype(
                        int
                    )
                    o = np.r_[np.zeros(m), np.ones(m), 2 * np.ones(m)] + rng.random(3 * m) * 0.5
                    bt = [
                        tercile_gap(o[i], y[i])[0]
                        for i in (rng.integers(0, 3 * m, 3 * m) for _ in range(200))
                    ]
                    lo, hi = np.nanquantile(bt, [0.025, 0.975])
                    hits += abs(tercile_gap(o, y)[0]) >= 0.10 and lo > 0
                table[n] = hits / reps
            need = next((n for n, pw in table.items() if pw >= 0.8), None)
            entry[f"gap_{int(true_gap * 100)}pp"] = dict(
                power_by_n22=table,
                n22_for_80pct=need,
                games_for_80pct=None if need is None else math.ceil(need / per_game),
            )
        out[name] = entry
    return out


def main() -> None:
    c = pd.read_csv(OUT / "catches.csv", dtype={"game": str})
    s = pd.read_csv(OUT / "shots.csv", dtype={"game": str})
    rng = np.random.default_rng(0)
    res = {
        "git_commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=OUT.parent
        ).stdout.strip(),
        "players": {},
    }
    s["located"] = s.reason.str.startswith("ok")
    res["join"] = {"fga_pbp": int(len(s)), "fga_joined": int(s.joined.sum())}
    res["release"] = {
        "located": int(s.located.sum()),
        "of_joined": int(s.joined.sum()),
        "reasons": s.reason.value_counts().to_dict(),
    }
    for name, pid in TARGET_IDS.items():
        pc = c[c.pid == pid].copy()
        games = sorted(pc.game.unique())
        n_games = len(games)
        cnt = pc[pc.valid_catch & pc.frontcourt & pc.sc_running].copy()
        cnt["cs"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 1.5)).astype(int)
        cnt["shot4"] = (cnt.catch_to_shot.notna() & (cnt.catch_to_shot <= 4.0)).astype(int)
        n = len(cnt)
        r = {
            "games": games,
            "spells_all": int(len(pc)),
            "valid_catches": int(pc.valid_catch.sum()),
            "counted_catches": n,
            "catches_per_game": n / n_games if n_games else None,
            "excluded": {
                "no_valid_pre_window": int((~pc.valid_catch).sum()),
                "backcourt": int((pc.valid_catch & ~pc.frontcourt).sum()),
                "shot_clock_not_running": int(
                    (pc.valid_catch & pc.frontcourt & ~pc.sc_running).sum()
                ),
            },
            "source": cnt.source.value_counts().to_dict(),
        }
        # bands
        bands = {}
        crit1_ok = True
        for lab, lo, hi in BANDS:
            x = cnt[(cnt.d_basket >= lo) & (cnt.d_basket < hi)]
            b = {"n": int(len(x))}
            if len(x) >= 1:
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
            c2.update(
                gap_top_minus_bottom=gap,
                n_bottom=nb,
                n_top=nt,
                ci95=[float(lo95), float(hi95)],
                p_cs_bottom=float(y[o <= np.quantile(o, 1 / 3)].mean()),
                p_cs_top=float(y[o > np.quantile(o, 2 / 3)].mean()),
                cut_ft=[float(np.quantile(o, 1 / 3)), float(np.quantile(o, 2 / 3))],
            )
            crit2_ok = bool(abs(gap) >= 0.10 and (lo95 > 0 or hi95 < 0))
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
            "open_catch_all": dict(
                zip(
                    ["q1", "median", "q3"],
                    np.quantile(cnt.open_catch, [0.25, 0.5, 0.75]).round(2).tolist(),
                )
            )
            if n
            else None,
            "rim_prot_median": float(cnt.rim_prot.median()) if n else None,
            "t_next_median": float(cnt.t_next.median()) if n else None,
            "shot_clock_median": float(cnt.shot_clock.median()) if n else None,
        }
        ps = s[s.shooter == pid]
        linked = (
            ps.get("linked", pd.Series(dtype=object)).astype("boolean").fillna(False).astype(bool)
        )
        linked_counted = cnt.catch_to_shot.notna().sum()
        sh = cnt[cnt.catch_to_shot.notna()]
        r["shots"] = {
            "pbp_fga": int(len(ps)),
            "located": int(ps.located.sum()),
            "linked_to_any_spell": int(linked.sum()),
            "linked_to_counted_catch": int(linked_counted),
            "unlinked_or_unlocated": int(len(ps) - linked.sum()),
            "open_catch_median_on_shots": float(sh.open_catch.median()) if len(sh) else None,
            "open_release_median": float(sh.open_release.median()) if len(sh) else None,
            "corr_open_catch_release": float(np.corrcoef(sh.open_catch, sh.open_release)[0, 1])
            if len(sh) > 2
            else None,
            "catch_to_shot_median": float(sh.catch_to_shot.median()) if len(sh) else None,
        }
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
    res["post_hoc_sensitivity"] = sensitivity(c, rng)
    res["power_crit2"] = power_crit2(res)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
