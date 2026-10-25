"""Held-out eye check for detector D1-D3 (protocol registered 25c4336).

heldout.py sample   build the candidate pool from the two earlier detectors, draw 20 per openness third
                    (seed 5), write checks/heldout_sample.csv and the render list. No D-detector output used.
heldout.py score    after checks/heldout_labels.json is committed and D1-D3 has been run (out/heldout_d3),
                    score each candidate and write checks/heldout_score.json.
"""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
CURRY = 201939
STEMS = {
    "0021500200": "11.22.2015.GSW.at.DEN",
    "0021500259": "11.30.2015.GSW.at.UTA",
    "0021500300": "12.06.2015.GSW.at.BKN",
    "0021500548": "01.08.2016.GSW.at.POR",
}


def counted(path):
    c = pd.read_csv(path, dtype={"game": str})
    return c[(c.pid == CURRY) & c.valid_catch & c.frontcourt & c.sc_running]


def sample():
    a = counted(ROOT / "out/heldout_sticky/catches.csv").assign(src="sticky")
    b = counted(ROOT / "out/heldout_nearest/catches.csv").assign(src="nearest")
    rows = a[["game", "start", "open_catch", "src"]].to_dict("records")
    for r in b.itertuples():
        same = a[(a.game == r.game) & ((a.start - r.start).abs() <= 5)]
        if len(same) == 0:
            rows.append(
                dict(game=r.game, start=r.start, open_catch=r.open_catch, src="nearest_only")
            )
    pool = pd.DataFrame(rows)
    cuts = np.quantile(pool.open_catch, [1 / 3, 2 / 3])
    pool["third"] = np.where(
        pool.open_catch <= cuts[0], "low", np.where(pool.open_catch <= cuts[1], "mid", "high")
    )
    picks = pd.concat(
        [pool[pool.third == t].sample(20, random_state=5) for t in ("low", "mid", "high")]
    )
    picks = picks.sample(frac=1, random_state=5).reset_index(
        drop=True
    )  # shuffle so labelling is blind to third
    picks["cid"] = [f"H{i:02d}" for i in range(len(picks))]
    picks.to_csv(ROOT / "checks/heldout_sample.csv", index=False)
    meta = dict(
        pool_size=len(pool),
        pool_by_src=pool.src.value_counts().to_dict(),
        tercile_cuts_ft=cuts.tolist(),
    )
    (ROOT / "checks/heldout_pool.json").write_text(json.dumps(meta, indent=1))
    with open(ROOT / "out/heldout_render.txt", "w") as f:
        for r in picks.itertuples():
            f.write(
                f"{r.game} {r.start - 50} {r.start + 25} out/heldout_eye/{r.cid} CATCH={r.start} "
                f"player={CURRY} stem={STEMS[r.game]}\n"
            )
    print(meta)


def score():
    picks = pd.read_csv(ROOT / "checks/heldout_sample.csv", dtype={"game": str})
    labels = {
        x["cid"]: x for x in json.loads((ROOT / "checks/heldout_labels.json").read_text())["labels"]
    }
    d3 = counted(ROOT / "out/heldout_d3/catches.csv")
    rows = []
    for r in picks.itertuples():
        lab = labels[r.cid]
        ref = lab["t_star"] if lab["label"] == "real" else r.start
        hit = d3[(d3.game == r.game) & ((d3.start - ref).abs() <= 5)]
        ok = len(hit) > 0 if lab["label"] == "real" else len(hit) == 0
        rows.append(
            dict(
                cid=r.cid,
                third=r.third,
                label=lab["label"],
                note=lab.get("note", ""),
                correct=bool(ok),
                d3_nearest_catch_offset=None
                if len(hit) == 0
                else int((hit.start - ref).abs().min()),
            )
        )
    df = pd.DataFrame(rows)
    by = df.groupby("third").correct.sum().to_dict()
    res = dict(
        correct=int(df.correct.sum()),
        n=len(df),
        by_third={k: int(v) for k, v in by.items()},
        labels=df.label.value_counts().to_dict(),
        passes=bool(df.correct.sum() >= 54 and min(by.values()) >= 16),
        errors=df[~df.correct].to_dict("records"),
    )
    (ROOT / "checks/heldout_score.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"sample": sample, "score": score}[sys.argv[1]]()
