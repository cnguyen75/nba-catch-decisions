"""Stage 3b-prep data: merge the parallel build parts, extend the split to new games (80/20, seed 2027), load frames."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
S4 = ROOT / "out" / "s4"
GATED = {201939: "Curry", 2544: "LeBron", 201935: "Harden"}
ZONES = ["rim", "mid", "above_break3", "corner3"]


def merge_parts() -> None:
    parts = sorted(S4.glob("part*"))
    for name in ("catches.csv", "shots.csv", "join_check.csv"):
        pd.concat(
            [pd.read_csv(p / name, dtype={"game": str}) for p in parts if (p / name).exists()]
        ).to_csv(S4 / name, index=False)
    meta = {"games": {}, "skipped_games": []}
    for p in parts:
        m = json.loads((p / "build_meta.json").read_text())
        meta["games"].update(m["games"])
        meta["skipped_games"] += m.get("skipped_games", [])
    (S4 / "build_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    old = json.loads((ROOT / "checks/split.json").read_text())
    new_games = sorted(g for g in meta["games"] if g not in old["split"])
    perm = np.random.default_rng(2027).permutation(len(new_games))
    n_tr = int(round(0.8 * len(new_games)))
    split = dict(old["split"])
    for rank, i in enumerate(perm):
        split[new_games[i]] = "train" if rank < n_tr else "validation"
    files = {g: m["file"] for g, m in meta["games"].items()}
    out = {
        "seed_new": 2027,
        "split": split,
        "files": files,
        "counts": {k: list(split.values()).count(k) for k in ("train", "validation", "test")},
        "n_new_games": len(new_games),
        "skipped": meta["skipped_games"],
    }
    (ROOT / "checks/split_all.json").write_text(json.dumps(out, indent=1))
    print(out["counts"], "new", len(new_games), "skipped", len(meta["skipped_games"]))


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    c = pd.read_csv(S4 / "catches.csv", dtype={"game": str})
    s = pd.read_csv(S4 / "shots.csv", dtype={"game": str})
    c["split"] = c.game.map(split)
    s["split"] = s.game.map(split)
    c = c[c.split != "test"].copy()
    s = s[s.split != "test"].copy()
    calib_f = ROOT / "checks/calib_games.json"
    if (
        calib_f.exists()
    ):  # calibration attempt 2 (0812282): league rows in the 60 games become "calib"
        calib = set(json.loads(calib_f.read_text())["calib_games"])
        c.loc[c.game.isin(calib) & ~c.pid.isin(GATED), "split"] = "calib"
        s.loc[s.game.isin(calib) & ~s.shooter.isin(GATED), "split"] = "calib"
    p = pd.read_csv(S4 / "poss.csv", dtype={"game": str})
    c = c.merge(p, on=["game", "pid", "start"], how="left")
    sh = s.set_index(["game", "eventnum"])
    key = list(zip(c.game, c.shot_event))
    c["made"] = [sh.made.get(k, np.nan) if not np.isnan(k[1]) else np.nan for k in key]
    c["three_pbp"] = [sh.three.get(k, np.nan) if not np.isnan(k[1]) else np.nan for k in key]
    c["open_release_all"] = [
        sh.open_release_all.get(k, np.nan) if not np.isnan(k[1]) else np.nan for k in key
    ]
    c["d_release"] = [sh.d_release.get(k, np.nan) if not np.isnan(k[1]) else np.nan for k in key]
    c["zone_release"] = [sh.zone_release.get(k, None) if not np.isnan(k[1]) else None for k in key]
    c["sc_release"] = [sh.sc_release.get(k, np.nan) if not np.isnan(k[1]) else np.nan for k in key]
    shoot = c.catch_to_shot.notna() & (c.catch_to_shot <= 1.5)
    c["action"] = np.where(shoot, "shoot", np.where(c.f1_unknown, "unknown", "continue"))
    c["points3"] = c.zone.isin(["above_break3", "corner3"]).astype(int)
    feats = [
        "d_basket",
        "zone",
        "open_catch",
        "rim_prot",
        "shot_clock",
        "best_tm_open",
        "margin",
        "poss_points",
    ]
    c["ok"] = (c.action != "unknown") & c[feats].notna().all(axis=1)
    return c, s


if __name__ == "__main__":
    merge_parts()
