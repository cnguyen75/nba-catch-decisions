"""R3 eye check (registered d3460a7). `sample`: draw 30 close-range FGAs and render detector-free
sheets. `score`: compare R3 releases (out/r3_check/shots.csv) to checks/r3_labels.json.
"""

import json
from pathlib import Path
import re
import sys

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
CLOSE = re.compile(r"Layup|Dunk|Tip|Hook|Putback|Finger Roll|Alley Oop")
PASS1 = {"0021500003", "0021500035", "0021500002", "0021500011", "0021500010"}


def is_close(desc: str) -> bool:
    m = re.search(r"(\d+)' ", desc)
    return bool(CLOSE.search(desc)) or (m is not None and int(m.group(1)) <= 8)


def descs() -> pd.Series:
    pbp = pd.read_csv(
        b.DATA / "pbp" / "2015-16_pbp.csv",
        dtype={"GAME_ID": str},
        usecols=["GAME_ID", "EVENTNUM", "HOMEDESCRIPTION", "VISITORDESCRIPTION"],
    )
    pbp["desc"] = pbp.HOMEDESCRIPTION.fillna("") + " " + pbp.VISITORDESCRIPTION.fillna("")
    return pbp.set_index(["GAME_ID", "EVENTNUM"]).desc


def sample() -> None:
    split = json.loads((ROOT / "checks/split.json").read_text())
    s = pd.read_csv(ROOT / "out/full/shots.csv", dtype={"game": str})
    d = descs()
    s["desc"] = [d.get((g, e), "") for g, e in zip(s.game, s.eventnum, strict=False)]
    s = s[
        s.joined
        & s.desc.map(is_close)
        & s.game.map(lambda g: split["split"].get(g) in ("train", "validation"))
        & ~s.game.isin(PASS1)
    ]
    s["loc"] = s.reason.str.startswith("ok")
    pick = pd.concat(
        [s[~s["loc"]].sample(20, random_state=31), s[s["loc"]].sample(10, random_state=31)]
    )
    pick = pick.sample(frac=1, random_state=31).reset_index(drop=True)
    pick["sid"] = [f"S{i:02d}" for i in range(30)]
    pick[["sid", "game", "eventnum", "shooter", "period", "pctime", "desc", "loc"]].to_csv(
        ROOT / "checks/r3_sample.csv", index=False
    )
    files = json.loads((ROOT / "checks/split.json").read_text())["files"]
    outdir = ROOT / "out/r3_eye"
    outdir.mkdir(parents=True, exist_ok=True)
    cache = {}
    for r in pick.itertuples():
        b.GAMES[r.game] = files[r.game]
        if r.game not in cache:
            cache = {r.game: b.load_timeline(r.game)[2]}
        tl = cache[r.game]
        pg = b.pc_seconds(r.pctime)
        idx = b.window(tl, int(r.period), pg + 6.0, pg - 0.5)
        if len(idx) == 0:
            fig = plt.figure(figsize=(6, 2))
            fig.text(0.1, 0.5, f"{r.sid}: no tracking frames in window")
            fig.savefig(outdir / f"{r.sid}.png", dpi=70)
            plt.close(fig)
            continue
        t = tl["GC"][idx[0]] - tl["GC"][idx]
        dsh = np.array([b.ball_to_player(tl, i, r.shooter) for i in idx])
        dbk = np.linalg.norm(tl["B"][idx, None, :2] - b.BASKETS[None], axis=2).min(1)
        fig = plt.figure(figsize=(15, 6))
        ax = fig.add_subplot(1, 3, (1, 2))
        ax.plot(t, tl["B"][idx, 2], label="ball z")
        ax.plot(t, np.minimum(dsh, 20), label="ball to shooter")
        ax.plot(t, np.minimum(dbk, 20), label="ball to nearest basket")
        ax.axhline(3, color="gray", lw=0.5)
        ax.axhline(10, color="gray", lw=0.5, ls=":")
        ax.set_xticks(np.arange(0, t.max() + 0.01, 0.2), minor=True)
        ax.grid(which="both", alpha=0.3)
        ax.set_ylim(0, 20)
        ax.set_xlabel("seconds since window start")
        ax.legend(fontsize=8)
        ax.set_title(f"{r.sid}  {r.desc.strip()[:70]}", fontsize=10)
        ax2 = fig.add_subplot(1, 3, 3)
        sxy = np.array(
            [
                b.player_xy(tl, i, r.shooter)
                if b.player_xy(tl, i, r.shooter) is not None
                else [np.nan, np.nan]
                for i in idx
            ]
        )
        sc = ax2.scatter(tl["B"][idx, 0], tl["B"][idx, 1], c=t, s=6, cmap="viridis")
        ax2.plot(sxy[:, 0], sxy[:, 1], "r-", lw=1)
        for bk in b.BASKETS:
            ax2.add_patch(plt.Circle(bk, 0.75, fill=False))
        c = np.nanmean(sxy, 0)
        ax2.set_xlim(c[0] - 15, c[0] + 15)
        ax2.set_ylim(c[1] - 15, c[1] + 15)
        ax2.set_aspect("equal")
        fig.colorbar(sc, ax=ax2, label="s since start")
        ax2.set_title("ball (dots), shooter (red)", fontsize=9)
        fig.tight_layout()
        fig.savefig(outdir / f"{r.sid}.png", dpi=70)
        plt.close(fig)
    print(pick["loc"].value_counts().to_dict())


def score() -> None:
    lab = {x["sid"]: x for x in json.loads((ROOT / "checks/r3_labels.json").read_text())["labels"]}
    smp = pd.read_csv(ROOT / "checks/r3_sample.csv", dtype={"game": str})
    r3 = pd.read_csv(ROOT / "out/r3_check/shots.csv", dtype={"game": str})
    files = json.loads((ROOT / "checks/split.json").read_text())["files"]
    rows, cache = [], {}
    for r in smp.itertuples():
        b.GAMES[r.game] = files[r.game]
        if r.game not in cache:
            cache = {r.game: b.load_timeline(r.game)[2]}
        tl = cache[r.game]
        pg = b.pc_seconds(r.pctime)
        idx = b.window(tl, int(r.period), pg + 6.0, pg - 0.5)
        L = lab[r.sid]
        if len(idx) == 0:
            idx = np.array([0])
        det = r3[(r3.game == r.game) & (r3.eventnum == r.eventnum)].iloc[0]
        det_ok = str(det.reason).startswith("ok")
        if L["release_s"] is None:
            ok = not det_ok
            off = None
        else:
            gc_lab = tl["GC"][idx[0]] - L["release_s"]
            f_lab = idx[np.argmin(np.abs(tl["GC"][idx] - gc_lab))]
            off = None if not det_ok else int(det.t_r - f_lab)
            ok = det_ok and abs(off) <= 5
        rows.append(
            dict(
                sid=r.sid,
                was_located=bool(r.loc),
                label=L["release_s"],
                det_reason=det.reason,
                offset_frames=off,
                correct=bool(ok),
            )
        )
    df = pd.DataFrame(rows)
    res = dict(
        correct=int(df.correct.sum()),
        n=len(df),
        passes=bool(df.correct.sum() >= 27),
        by_prior_status=df.groupby("was_located").correct.agg(["sum", "size"]).to_dict(),
        rows=rows,
    )
    (ROOT / "checks/r3_score.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"sample": sample, "score": score}[sys.argv[1]]()
