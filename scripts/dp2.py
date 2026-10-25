"""Drive/pass retest, D-v2 detector (registered 4a1b93d + amendment 1dcdbba).

dp2.py tune     run D-v2 on the FIRST check's 60 (tuning set) and compare with those labels
dp2.py sample   draw the FRESH 60 (validation games, excluding the first 60; seed 43) and render sheets
dp2.py score    run D-v2 on the fresh 60 (only after checks/dp2_labels.json is committed) and score
dp2.py all      classify every counted catch in non-test games -> out/s3/actions_v2.csv
"""

import json
from pathlib import Path
import sys
from typing import Any

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
S3 = ROOT / "out" / "s3"
TOUCH_D, TOUCH_Z, TOUCH_N = 3.0, 12.0, 2
SHOTS = pd.read_csv(S3 / "shots.csv", dtype={"game": str})


def att_basket(meta: dict[str, Any], game: str, team: int, q: int) -> int | None:
    return meta[game]["attacking"].get(f"{team}_{q}")


def first_touch(tl: dict[str, Any], p: int, e: int) -> tuple[int | None, int | None]:
    """First non-P player with the ball within 3 ft and z <= 12 for 2 consecutive frames, within 2.0 s after e."""
    GC, Q = tl["GC"], tl["Q"]
    run_pid, run_n = None, 0
    f = e + 1
    while f < tl["n"] and Q[f] == Q[e] and GC[e] - GC[f] <= 2.0:
        cand = None
        if tl["B"][f, 2] <= TOUCH_Z:
            d = tl["dist"][f].copy()
            d[tl["PID"][f] == p] = np.inf
            k = int(d.argmin())
            if d[k] <= TOUCH_D:
                cand = int(tl["PID"][f, k])
        if cand is not None and cand == run_pid:
            run_n += 1
        else:
            run_pid, run_n = cand, (1 if cand is not None else 0)
        if run_pid is not None and run_n >= TOUCH_N:
            return run_pid, f
        f += 1
    return None, None


def classify(
    tl: dict[str, Any], r: Any, bk: int, ctx: dict[str, Any]
) -> tuple[bool, bool, int | None, int | None]:
    """Return (drive, pass, touch_pid, touch_frame). r has pid, start, end."""
    p, st, en = int(r.pid), int(r.start), int(r.end)
    GC = tl["GC"]
    seg = np.arange(st, en + 1)
    xy = [b.player_xy(tl, i, p) for i in seg]
    dP = np.array([np.linalg.norm(v - b.BASKETS[bk]) if v is not None else np.nan for v in xy])
    bP = np.array([b.ball_to_player(tl, i, p) for i in seg])
    drib = (tl["B"][seg, 2] <= 1.5) & (bP <= 5.0)
    cs = np.r_[0, np.cumsum(drib)]
    drive = False
    for jj in np.where(dP <= 10.0)[0]:
        ii = np.where((dP[:jj] >= 20.0) & (GC[seg[:jj]] >= GC[st] - 4.0))[0]
        if len(ii) and cs[jj + 1] - cs[ii[-1]] > 0:
            drive = True
            break
    team = b.team_of(tl, st, p)
    tp, tf = next_receiver(tl, p, en, team, ctx)
    passed = (
        (not drive)
        and (GC[st] - GC[en] <= 4.0)
        and tp is not None
        and b.team_of(tl, tf, tp) == team
    )
    return drive, bool(passed), tp, tf


def next_receiver(
    tl: dict[str, Any], p: int, en: int, team: int, ctx: dict[str, Any]
) -> tuple[int | None, int | None]:
    """D-v2 (amendment 2): the owner of the next D3 spell starting within 2.0 s after e; or, if a located FG release by
    a teammate falls in (e, e + 2.0 s] before any other spell starts, that shooter (lob / alley-oop)."""
    GC, Q = tl["GC"], tl["Q"]
    sp = ctx["spells"]
    nxt = next((x for x in sp if x[1] > en), None)
    nxt_ok = nxt is not None and Q[nxt[1]] == Q[en] and GC[en] - GC[nxt[1]] <= 2.0
    for t_r, shooter in ctx["releases"]:
        if (
            t_r > en
            and Q[t_r] == Q[en]
            and GC[en] - GC[t_r] <= 2.0
            and (nxt is None or t_r < nxt[1])
            and shooter != p
        ):
            if b.team_of(tl, t_r, shooter) == team:
                return shooter, t_r
    if nxt_ok and nxt[0] != p:
        return int(nxt[0]), int(nxt[1])
    return None, None


def load_ctx() -> tuple[dict[str, Any], dict[str, Any]]:
    split = json.loads((ROOT / "checks/split.json").read_text())
    meta = json.loads((S3 / "build_meta.json").read_text())["games"]
    return split, meta


def run_on(rows: pd.DataFrame, split: dict[str, Any], meta: dict[str, Any]) -> pd.DataFrame:
    out, cache = [], {}
    for r in rows.sort_values("game").itertuples():
        b.GAMES[r.game] = split["files"][r.game]
        if r.game not in cache:
            tl0 = b.load_timeline(r.game)[2]
            sh = SHOTS[(SHOTS.game == r.game) & SHOTS.t_r.notna()]
            cache = {
                r.game: (
                    tl0,
                    {
                        "spells": b.spells(tl0),
                        "releases": list(zip(sh.t_r.astype(int), sh.shooter)),
                    },
                )
            }
        tl, ctx = cache[r.game]
        bk = att_basket(meta, r.game, int(r.team), int(r.quarter))
        dv, pv, tp, tf = classify(tl, r, bk, ctx)
        out.append(dict(game=r.game, pid=r.pid, start=r.start, drive_v2=dv, pass_v2=pv))
    return pd.DataFrame(out)


def cls(row: pd.Series) -> str:
    return "drive" if row.drive_v2 else ("pass" if row.pass_v2 else "hold")


def tune() -> None:
    b.RULE = "d3"
    split, meta = load_ctx()
    c = pd.read_csv(S3 / "catches.csv", dtype={"game": str})
    smp = pd.read_csv(ROOT / "checks/dp_sample.csv", dtype={"game": str})
    rows = smp.merge(c, on=["game", "pid", "start"], suffixes=("", "_c"))
    det = run_on(rows, split, meta).merge(smp, on=["game", "pid", "start"])
    lab = {
        x["did"]: x["label"]
        for x in json.loads((ROOT / "checks/dp_labels.json").read_text())["labels"]
    }
    det["eye"] = det.did.map(lab)
    det["det"] = det.apply(cls, axis=1)
    print("tuning set agreement:", int((det.eye == det.det).sum()), "/ 60")
    print(det[det.eye != det.det][["did", "eye", "det"]].to_string())


def sample() -> None:
    b.RULE = "d3"
    split, meta = load_ctx()
    c = pd.read_csv(S3 / "catches.csv", dtype={"game": str})
    first = pd.read_csv(ROOT / "checks/dp_sample.csv", dtype={"game": str})
    used = set(zip(first.game, first.pid, first.start))
    c = c[c.game.map(lambda g: split["split"][g] == "validation")]
    c = c[~((c.catch_to_shot.notna()) & (c.catch_to_shot <= 1.5)) & ~c.f1_unknown]
    c = c[[(g, p, s) not in used for g, p, s in zip(c.game, c.pid, c.start)]]
    drive_like = (c.min_dbasket <= 10) & (c.max_dbasket >= 20)
    pass_like = (c.next_rel == "teammate") & ~drive_like
    c["stratum"] = np.where(drive_like, "drive_like", np.where(pass_like, "pass_like", "other"))
    pick = pd.concat(
        [
            c[c.stratum == s].sample(20, random_state=43)
            for s in ("drive_like", "pass_like", "other")
        ]
    )
    pick = pick.sample(frac=1, random_state=43).reset_index(drop=True)
    pick["fid"] = [f"F{i:02d}" for i in range(60)]
    pick[["fid", "game", "pid", "start", "end", "team", "quarter", "stratum"]].to_csv(
        ROOT / "checks/dp2_sample.csv", index=False
    )
    out = ROOT / "out/dp2_eye"
    out.mkdir(parents=True, exist_ok=True)
    cache = {}
    for r in pick.sort_values("game").itertuples():
        b.GAMES[r.game] = split["files"][r.game]
        if r.game not in cache:
            cache = {r.game: b.load_timeline(r.game)[2]}
        tl = cache[r.game]
        bk = att_basket(meta, r.game, int(r.team), int(r.quarter))
        GC = tl["GC"]
        hi = r.end
        while hi + 1 < tl["n"] and GC[r.end] - GC[hi + 1] <= 2.0:
            hi += 1
        idx = np.arange(max(r.start - 12, 0), hi + 1)
        t = GC[r.start] - GC[idx]
        pp = np.array(
            [
                b.player_xy(tl, i, r.pid)
                if b.player_xy(tl, i, r.pid) is not None
                else [np.nan, np.nan]
                for i in idx
            ]
        )
        dP = np.linalg.norm(pp - b.BASKETS[bk], axis=1)
        bP = np.array([b.ball_to_player(tl, i, r.pid) for i in idx])
        # display aid: first frame after the end where a non-P player is within 3 ft of the ball below 12 ft
        disp = hi
        for f in range(r.end + 1, hi + 1):
            d = tl["dist"][f].copy()
            d[tl["PID"][f] == r.pid] = np.inf
            if tl["B"][f, 2] <= 12 and d.min() <= 3:
                disp = f
                break
        fig = plt.figure(figsize=(15, 6))
        ax = fig.add_subplot(1, 2, 1)
        ax.plot(t, np.minimum(dP, 40), label="player to basket")
        ax.plot(t, tl["B"][idx, 2], label="ball z")
        ax.plot(t, np.minimum(bP, 40), label="ball to player")
        ax.plot(
            t,
            np.minimum(np.linalg.norm(tl["B"][idx, :2] - b.BASKETS[bk], axis=1), 40),
            label="ball to basket",
            color="k",
            lw=0.8,
        )
        for v in (10, 12, 20):
            ax.axhline(v, color="gray", ls=":", lw=1)
        ax.axvline(0, color="r", label="catch")
        ax.axvline(GC[r.start] - GC[r.end], color="k", ls="--", label="possession end")
        ax.axvline(4.0, color="purple", ls=":", lw=1, label="4 s")
        ax.axvline(GC[r.start] - GC[disp], color="green", ls=":", label="players drawn at")
        ax.set_ylim(0, 40)
        ax.set_xlabel("s after catch")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        ax.set_title(r.fid)
        ax2 = fig.add_subplot(1, 2, 2)
        sc = ax2.scatter(tl["B"][idx, 0], tl["B"][idx, 1], c=t, s=5, cmap="viridis")
        ax2.plot(pp[:, 0], pp[:, 1], "r-", lw=2)
        ax2.plot(*pp[0], "ro", ms=8)
        team = b.team_of(tl, r.start, r.pid)
        for j in range(10):
            if tl["PID"][disp, j] != r.pid:
                col = "#1d428a" if tl["TEAM"][disp, j] == team else "#e88"
                ax2.add_patch(plt.Circle(tl["PXY"][disp, j], 0.9, color=col, alpha=0.7))
        ax2.plot(*tl["B"][disp, :2], "*", color="orange", ms=14)
        for rad in (10, 20):
            ax2.add_patch(plt.Circle(b.BASKETS[bk], rad, fill=False, ls=":", color="gray"))
        ax2.add_patch(plt.Circle(b.BASKETS[bk], 0.75, fill=False, color="k"))
        ax2.set_xlim(0, 94)
        ax2.set_ylim(0, 50)
        ax2.set_aspect("equal")
        fig.colorbar(sc, ax=ax2, label="s after catch")
        ax2.set_title(
            f"players at green line; ball there = star; ball z then {tl['B'][disp, 2]:.1f} ft",
            fontsize=8,
        )
        fig.tight_layout()
        fig.savefig(out / f"{r.fid}.png", dpi=65)
        plt.close(fig)
    print(pick.stratum.value_counts().to_dict())


def score() -> None:
    b.RULE = "d3"
    split, meta = load_ctx()
    smp = pd.read_csv(ROOT / "checks/dp2_sample.csv", dtype={"game": str})
    det = run_on(smp, split, meta).merge(smp, on=["game", "pid", "start"])
    lab = {x["fid"]: x for x in json.loads((ROOT / "checks/dp2_labels.json").read_text())["labels"]}
    det["eye"] = det.fid.map(lambda f: lab[f]["label"])
    det["note"] = det.fid.map(lambda f: lab[f].get("note", ""))
    det["det"] = det.apply(cls, axis=1)
    det["correct"] = det.eye == det.det
    by = det.groupby("stratum").correct.sum().to_dict()
    res = dict(
        correct=int(det.correct.sum()),
        n=60,
        by_stratum={k: int(v) for k, v in by.items()},
        passes=bool(det.correct.sum() >= 54 and min(by.values()) >= 16),
        confusion_rows_eye_cols_detector=pd.crosstab(det.eye, det.det).to_dict("index"),
        errors=det[~det.correct][["fid", "stratum", "eye", "det", "note"]].to_dict("records"),
    )
    (ROOT / "checks/dp2_score.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def all_catches() -> None:
    b.RULE = "d3"
    split, meta = load_ctx()
    c = pd.read_csv(S3 / "catches.csv", dtype={"game": str})
    c = c[c.game.map(lambda g: split["split"][g] != "test")]
    det = run_on(c, split, meta)
    det.to_csv(S3 / "actions_v2.csv", index=False)
    print(len(det), det[["drive_v2", "pass_v2"]].mean().round(3).to_dict())


if __name__ == "__main__":
    {"tune": tune, "sample": sample, "score": score, "all": all_catches}[sys.argv[1]]()
