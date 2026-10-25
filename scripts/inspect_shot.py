"""Print a frame-by-frame trace of one FG attempt's event window (diagnostic)."""

import sys

import numpy as np
import pandas as pd


sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import build as b


gid, evn = sys.argv[1], int(sys.argv[2])
step = int(sys.argv[3]) if len(sys.argv) > 3 else 5
g, events, tl, _ = b.load_timeline(gid)
pbp = pd.read_csv(b.DATA / "pbp" / "2015-16_pbp.csv", dtype={"GAME_ID": str})
row = pbp[(gid == pbp.GAME_ID) & (evn == pbp.EVENTNUM)].iloc[0]
sh = int(row.PLAYER1_ID)
print(row.PCTIMESTRING, row.HOMEDESCRIPTION, row.VISITORDESCRIPTION)
e = events[evn]
print("window q", e[0], e[1], e[2])
idx = b.window(tl, e[0], e[1], e[2])
for i in idx[::step]:
    db = np.linalg.norm(tl["B"][i, :2] - b.BASKETS, axis=1).min()
    near = tl["PID"][i, tl["dist"][i].argmin()]
    print(
        f"{tl['GC'][i]:7.2f} sc={tl['SC'][i]:5.1f} z={tl['B'][i, 2]:5.2f} "
        f"dsh={b.ball_to_player(tl, i, sh):6.2f} dbask={db:6.2f} near={near} ctrl={tl['ctrl'][i]}"
    )
