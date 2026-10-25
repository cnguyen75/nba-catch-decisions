"""Game-level 60/20/20 train/validation/test split (registered d3460a7). Writes checks/split.json."""

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
meta = json.loads((ROOT / "out/full/build_meta.json").read_text())["games"]
games = sorted(meta)
rng = np.random.default_rng(2026)
order = [games[i] for i in rng.permutation(len(games))]
PLAYERS = ["Curry", "LeBron", "Harden"]
TARGET = {"train": 0.6, "validation": 0.2, "test": 0.2}
total = {p: sum(p in meta[g]["present_targets"] for g in games) for p in PLAYERS}
count = {p: {k: 0 for k in TARGET} for p in PLAYERS}
split = {}
for g in order:
    ps = [p for p in PLAYERS if p in meta[g]["present_targets"]]
    if not ps:
        split[g] = "train"
        continue
    deficit = {k: sum(TARGET[k] * total[p] - count[p][k] for p in ps) for k in TARGET}
    best = max(TARGET, key=lambda k: (deficit[k], -list(TARGET).index(k)))
    split[g] = best
    for p in ps:
        count[p][best] += 1
out = {
    "seed": 2026,
    "split": split,
    "per_player_counts": count,
    "files": {g: meta[g]["file"] for g in games},
}
(ROOT / "checks/split.json").write_text(json.dumps(out, indent=1))
print(count, {k: list(split.values()).count(k) for k in TARGET})
