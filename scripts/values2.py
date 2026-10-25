"""Values for the binary model (registered 4a1b93d): fixed V_shoot (vshoot2 model, Platt map) on the
possession scale, V_shoot = P(make) * points + g(zone); also the immediate-scale V_shoot_imm =
P(make) * points (sensitivity only). Player per-zone make offsets refit on the new logits (MAP,
prior N(0, 0.3^2), train games only). V_continue is the part-2 league model + shrunk player
offset (unchanged). Writes out/s3/values2.csv.
"""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).parent))
from values import GATED, ZONES, load, map_offset  # noqa: E402
from vshoot2 import X  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
S3 = ROOT / "out" / "s3"


def main() -> None:
    m = np.load(S3 / "vshoot2_model.npz")
    g_zone = {z: v["g"] for z, v in json.loads((S3 / "vshoot2.json").read_text())["g_zone"].items()}
    c = load()
    old = pd.read_csv(S3 / "values.csv", dtype={"game": str})[
        ["game", "pid", "start", "V_continue"]
    ]
    g = c[(c.excluded == "") & c.pid.isin(GATED) & c.shot_clock.notna()].merge(
        old, on=["game", "pid", "start"]
    )
    z = (X(g) - m["mean"]) / m["scale"]
    raw = z @ m["coef"].ravel() + m["intercept"][0]
    g["logit"] = float(m["a"]) * raw + float(m["b"])
    rep = {}
    for pid, name in GATED.items():
        mine = g[(g.pid == pid) & (g.split == "train") & (g.action == "shoot") & g.made.notna()]
        off = {
            zz: (
                map_offset(mine[mine.zone == zz].logit.values, mine[mine.zone == zz].made.values)
                if (mine.zone == zz).any()
                else 0.0
            )
            for zz in ZONES
        }
        rep[name] = {
            zz: {"n": int((mine.zone == zz).sum()), "offset_logit": round(off[zz], 4)}
            for zz in ZONES
        }
        sel = g.pid == pid
        p = 1 / (1 + np.exp(-(g.loc[sel, "logit"] + g.loc[sel, "zone"].map(off))))
        pts = 2 + g.loc[sel, "points3"]
        g.loc[sel, "V_shoot_imm"] = p * pts
        g.loc[sel, "V_shoot"] = p * pts + g.loc[sel, "zone"].map(g_zone)
    cols = [
        "game",
        "split",
        "pid",
        "start",
        "d_basket",
        "zone",
        "open_catch",
        "action",
        "V_shoot",
        "V_shoot_imm",
        "V_continue",
    ]
    g[cols].to_csv(S3 / "values2.csv", index=False)
    (S3 / "values2_offsets.json").write_text(json.dumps(rep, indent=1))
    tr = g[g.split == "train"]
    print(json.dumps(rep, indent=1))
    print(
        tr.groupby("pid")[["V_shoot", "V_shoot_imm", "V_continue"]]
        .describe()
        .round(3)
        .T.to_string()
    )


if __name__ == "__main__":
    main()
