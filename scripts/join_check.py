"""Join check on 20 random joined PBP events (seed 0): period, clock, shooter, and a still per
event.
"""

from pathlib import Path
import sys

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402


TYPES = {
    1: "made FG",
    2: "missed FG",
    3: "free throw",
    4: "rebound",
    5: "turnover",
    6: "foul",
    7: "violation",
    8: "substitution",
    9: "timeout",
    10: "jump ball",
    12: "period start",
    13: "period end",
    18: "instant replay",
}


def main() -> None:
    j = pd.read_csv(b.OUT / "join_check.csv", dtype={"game": str})
    shots = pd.read_csv(b.OUT / "shots.csv", dtype={"game": str})
    pick = j[j.joined].sample(20, random_state=0)
    rows = []
    fig, axs = plt.subplots(5, 4, figsize=(20, 16))
    cache = {}
    for ax, r in zip(np.ravel(axs), pick.itertuples(), strict=False):
        if r.game not in cache:
            cache[r.game] = b.load_timeline(r.game)[2]
        tl = cache[r.game]
        pbp_gc = b.pc_seconds(r.pctime)
        period_ok = int(r.ev_q) == r.period
        clock_ok = r.ev_gmin - 2 <= pbp_gc <= r.ev_gmax + 2
        rec = dict(
            game=r.game,
            eventnum=r.eventnum,
            type=TYPES.get(r.msgtype, r.msgtype),
            desc=r.desc,
            period_ok=period_ok,
            clock_ok=clock_ok,
            shooter_nearest_at_release=None,
            shooter_nearest_0p2s_before=None,
        )
        frame = None
        if r.msgtype in (1, 2):
            s = shots[(shots.game == r.game) & (shots.eventnum == r.eventnum)].iloc[0]
            if not np.isnan(s.t_r):
                t = int(s.t_r)
                frame = t
                rec["shooter_nearest_at_release"] = bool(
                    tl["PID"][t, tl["dist"][t].argmin()] == s.shooter
                )
                rec["shooter_nearest_0p2s_before"] = bool(
                    tl["PID"][t - 5, tl["dist"][t - 5].argmin()] == s.shooter
                )
        if frame is None:
            cand = np.where((tl["Q"] == r.period) & (tl["GC"] >= pbp_gc))[0]
            frame = cand[-1] if len(cand) else None
        if frame is not None:
            for k in range(10):
                x, y = tl["PXY"][frame, k]
                home = tl["TEAM"][frame, k] == tl["home_team"]
                hit = tl["PID"][frame, k] == r.p1
                ax.add_patch(
                    plt.Circle(
                        (x, y),
                        1.2,
                        color="#c8102e" if home else "#1d428a",
                        alpha=0.95 if hit else 0.4,
                    )
                )
                if hit:
                    ax.add_patch(plt.Circle((x, y), 2.0, fill=False, color="k", lw=2))
            bx, by, bz = tl["B"][frame]
            ax.add_patch(plt.Circle((bx, by), 0.5 + bz / 10, color="#ff8c00"))
            for bk in b.BASKETS:
                ax.add_patch(plt.Circle(bk, 0.75, fill=False, color="k"))
            ax.set_title(
                f"{r.game[-3:]}#{r.eventnum} Q{r.period} {r.pctime} "
                f"(frame {tl['GC'][frame]:.1f}s, z={bz:.1f})\n"
                f"{rec['type']}: {str(r.desc)[:55]}",
                fontsize=9,
            )
        ax.set_xlim(0, 94)
        ax.set_ylim(0, 50)
        ax.set_aspect("equal")
        ax.plot([47, 47], [0, 50], color="gray", lw=0.5)
        ax.set_xticks([])
        ax.set_yticks([])
        rows.append(rec)
    fig.tight_layout()
    fig.savefig(b.OUT / "join20_sheet.png", dpi=60)
    out = pd.DataFrame(rows)
    out.to_csv(b.OUT / "join20.csv", index=False)
    print(out.to_string())


if __name__ == "__main__":
    main()
