"""Drive/pass detector held-out check (registered d3460a7).

dp_eye.py sample   draw 20 per proxy stratum from validation games (seed 41), render detector-
    free sheets
dp_eye.py score    compare detector classes (out/s3/catches.csv) with checks/dp_labels.json
"""

import json
from pathlib import Path
import sys

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent


def pool() -> pd.DataFrame:
    split = json.loads((ROOT / "checks/split.json").read_text())["split"]
    c = pd.read_csv(ROOT / "out/s3/catches.csv", dtype={"game": str})
    c = c[c.game.map(lambda g: split[g] == "validation")]
    c = c[~((c.catch_to_shot.notna()) & (c.catch_to_shot <= 1.5)) & ~c.f1_unknown]
    drive_like = (c.min_dbasket <= 10) & (c.max_dbasket >= 20)
    pass_like = (c.next_rel == "teammate") & ~drive_like
    c["stratum"] = np.where(drive_like, "drive_like", np.where(pass_like, "pass_like", "other"))
    return c


def sample() -> None:
    b.RULE = "d3"
    c = pool()
    pick = pd.concat(
        [
            c[c.stratum == s].sample(20, random_state=41)
            for s in ("drive_like", "pass_like", "other")
        ]
    )
    pick = pick.sample(frac=1, random_state=41).reset_index(drop=True)
    pick["did"] = [f"D{i:02d}" for i in range(60)]
    pick[["did", "game", "pid", "start", "end", "stratum"]].to_csv(
        ROOT / "checks/dp_sample.csv", index=False
    )
    files = json.loads((ROOT / "checks/split.json").read_text())["files"]
    out = ROOT / "out/dp_eye"
    out.mkdir(parents=True, exist_ok=True)
    cache = {}
    for r in pick.sort_values("game").itertuples():
        b.GAMES[r.game] = files[r.game]
        if r.game not in cache:
            cache = {r.game: b.load_timeline(r.game)[2]}
        tl = cache[r.game]
        team = b.team_of(tl, r.start, r.pid)
        # attacking basket: the basket nearer the player's catch position in the frontcourt
        pxy = b.player_xy(tl, r.start, r.pid)
        bk = int(np.argmin(np.linalg.norm(b.BASKETS - pxy, axis=1)))
        lo = max(r.start - 12, 0)
        hi = min(r.end + 40, tl["n"] - 1)
        idx = np.arange(lo, hi + 1)
        t = tl["GC"][r.start] - tl["GC"][idx]
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
        fig = plt.figure(figsize=(15, 6))
        ax = fig.add_subplot(1, 2, 1)
        ax.plot(t, np.minimum(dP, 40), label="player to basket")
        ax.plot(t, tl["B"][idx, 2], label="ball z")
        ax.plot(t, np.minimum(bP, 40), label="ball to player")
        for v in (10, 20):
            ax.axhline(v, color="gray", ls=":", lw=1)
        ax.axvline(0, color="r", label="catch")
        ax.axvline(tl["GC"][r.start] - tl["GC"][r.end], color="k", ls="--", label="possession end")
        ax.set_ylim(0, 40)
        ax.set_xlabel("s after catch")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        ax.set_title(r.did)
        ax2 = fig.add_subplot(1, 2, 2)
        sc = ax2.scatter(tl["B"][idx, 0], tl["B"][idx, 1], c=t, s=5, cmap="viridis")
        ax2.plot(pp[:, 0], pp[:, 1], "r-", lw=2, label="player")
        ax2.plot(*pp[0], "ro", ms=8)
        last = hi
        for j in range(10):
            col = "#1d428a" if tl["TEAM"][last, j] == team else "#e88"
            if tl["PID"][last, j] != r.pid:
                ax2.add_patch(plt.Circle(tl["PXY"][last, j], 0.9, color=col, alpha=0.6))
        for rad in (10, 20):
            ax2.add_patch(plt.Circle(b.BASKETS[bk], rad, fill=False, ls=":", color="gray"))
        ax2.add_patch(plt.Circle(b.BASKETS[bk], 0.75, fill=False, color="k"))
        ax2.set_xlim(0, 94)
        ax2.set_ylim(0, 50)
        ax2.set_aspect("equal")
        fig.colorbar(sc, ax=ax2, label="s after catch")
        ax2.set_title(
            "ball dots by time; player red (dot = catch); "
            "others at window end (blue team, pink opp)",
            fontsize=8,
        )
        fig.tight_layout()
        fig.savefig(out / f"{r.did}.png", dpi=65)
        plt.close(fig)
    print(pick.stratum.value_counts().to_dict())


def score() -> None:
    smp = pd.read_csv(ROOT / "checks/dp_sample.csv", dtype={"game": str})
    lab = {x["did"]: x for x in json.loads((ROOT / "checks/dp_labels.json").read_text())["labels"]}
    c = pd.read_csv(ROOT / "out/s3/catches.csv", dtype={"game": str}).set_index(
        ["game", "pid", "start"]
    )
    rows = []
    for r in smp.itertuples():
        x = c.loc[(r.game, r.pid, r.start)]
        det = "drive" if x.drive else ("pass" if x["pass"] else "hold")
        rows.append(
            dict(
                did=r.did,
                stratum=r.stratum,
                eye=lab[r.did]["label"],
                detector=det,
                correct=det == lab[r.did]["label"],
                note=lab[r.did].get("note", ""),
            )
        )
    df = pd.DataFrame(rows)
    by = df.groupby("stratum").correct.sum().to_dict()
    res = dict(
        correct=int(df.correct.sum()),
        n=len(df),
        by_stratum={k: int(v) for k, v in by.items()},
        passes=bool(df.correct.sum() >= 54 and min(by.values()) >= 16),
        confusion_eye_vs_detector=pd.crosstab(df.eye, df.detector).to_dict(),
        errors=df[~df.correct].to_dict("records"),
    )
    (ROOT / "checks/dp_score.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"sample": sample, "score": score}[sys.argv[1]]()
