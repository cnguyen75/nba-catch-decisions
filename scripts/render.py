"""Render plays with the upstream linouk23 `Event` animation class (GIF + contact sheet).

Usage: render.py <game_id> <first_frame> <last_frame> <out_stem> [label=frame ...]
Frames are timeline indices from build.py. Labelled frames are marked in the clock box
and held for 0.5 s in the GIF. Upstream code is read from ~/Documents/nba-tracking/upstream
(commit f7d4cf2); it draws ball height as ball circle size.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import build as b  # noqa: E402

b.GAMES.update(b.GAMES_PASS2)

UP = Path.home() / "Documents" / "nba-tracking" / "upstream"
sys.path.append(str(UP))
import Event as up_event  # noqa: E402


class _TableShim:
    """Upstream reads table.properties()['child_artists'], removed in newer matplotlib."""

    def __init__(self, t):
        self._t = t

    def __getattr__(self, k):
        return getattr(self._t, k)

    def properties(self):
        return {"child_artists": self._t.get_children()}


_real_table = plt.table
_real_imread = plt.imread


def moments(tl, lo, hi):
    out = []
    for i in range(lo, hi + 1):
        rows = [[-1, -1, *tl["B"][i]]]
        order = np.argsort(tl["TEAM"][i], kind="stable")
        rows += [[int(tl["TEAM"][i, j]), int(tl["PID"][i, j]), *tl["PXY"][i, j], 0.0] for j in order]
        sc = tl["SC"][i]
        out.append([int(tl["Q"][i]), 0, float(tl["GC"][i]), 0.0 if np.isnan(sc) else float(sc), None, rows])
    return out


def render(gid, lo, hi, stem, marks, player=None):
    g, events, tl, _ = b.load_timeline(gid)
    roster = {}
    for ev in g["events"]:
        for side in ("home", "visitor"):
            for p in ev[side]["players"]:
                roster[p["playerid"]] = p
    base = g["events"][0]
    ev = {"moments": moments(tl, lo, hi),
          "home": {**base["home"], "players": list(roster.values())}, "visitor": {**base["visitor"], "players": []}}
    E = up_event.Event(ev)
    captured = {}
    real_fa = up_event.animation.FuncAnimation
    orig_update = E.update_radius
    frame_ids = list(range(lo, hi + 1))
    # hold marked frames so they are visible in the GIF
    seq = []
    for k, i in enumerate(frame_ids):
        seq += [k] * (12 if i in marks else 1)

    def update(k, *a):
        res = orig_update(k, *a)
        clock = a[3]
        i = frame_ids[k]
        tag = marks.get(i, "")
        clock.set_text(clock.get_text() + f"\n z={tl['B'][i, 2]:.1f}ft" + (f"\n>> {tag} <<" if tag else ""))
        clock.set_color("red" if tag else "black")
        return res

    E.update_radius = update

    def fa(fig, func, fargs, frames, interval):
        captured["fig"], captured["func"], captured["fargs"] = fig, func, fargs
        captured["anim"] = real_fa(fig, func, fargs=fargs, frames=seq, interval=40)
        return captured["anim"]

    up_event.animation.FuncAnimation = fa
    up_event.plt.show = lambda: None
    up_event.plt.table = lambda *a, **k: _TableShim(_real_table(*a, **k))
    up_event.plt.imread = lambda _: _real_imread(UP / "court.png")
    try:
        E.show()
    finally:
        up_event.animation.FuncAnimation = real_fa
    fig = captured["fig"]
    captured["anim"].save(f"{stem}.gif", writer=matplotlib.animation.PillowWriter(fps=25), dpi=110)
    # contact sheet: upstream frames zoomed on the player, plus a ball trace
    keys = sorted(marks)
    focus = player if player else int(tl["PID"][keys[-1], tl["dist"][keys[-1]].argmin()])
    picks = sorted({min(max(i + d, lo), hi) for i in keys for d in (-6, -3, 0, 3, 6)})[:15]
    home = tl["home_team"]
    imgs = []
    for i in picks:
        c = b.player_xy(tl, i, focus)
        f2, a2 = plt.subplots(figsize=(4, 3.2))
        for j in range(10):
            x, y = tl["PXY"][i, j]
            col = "#c8102e" if tl["TEAM"][i, j] == home else "#1d428a"
            a2.add_patch(plt.Circle((x, y), 1.0, color=col, alpha=0.9 if tl["PID"][i, j] == focus else 0.5))
            a2.text(x, y, str(roster[int(tl["PID"][i, j])]["jersey"]), color="w", ha="center", va="center", fontsize=8)
        bx, by, bz = tl["B"][i]
        a2.add_patch(plt.Circle((bx, by), 0.3 + bz / 12, color="#ff8c00", alpha=0.85))
        for bk in b.BASKETS:
            a2.add_patch(plt.Circle(bk, 0.75, fill=False, color="k"))
        a2.set_xlim(c[0] - 10, c[0] + 10)
        a2.set_ylim(c[1] - 8, c[1] + 8)
        a2.set_aspect("equal")
        a2.set_xticks([]); a2.set_yticks([])
        f2.canvas.draw()
        imgs.append((i, np.asarray(f2.canvas.buffer_rgba()).copy()))
        plt.close(f2)
    plt.close(fig)
    cols = 5
    rows = int(np.ceil(len(imgs) / cols)) + 1
    sheet, axs = plt.subplots(rows, cols, figsize=(cols * 3.6, rows * 2.9))
    for ax in np.ravel(axs):
        ax.axis("off")
    ref = keys[-1]
    for ax, (i, im) in zip(np.ravel(axs), imgs):
        ax.imshow(im)
        off = tl["GC"][ref] - tl["GC"][i]
        ax.set_title(f"{marks.get(i, '')} {off:+.2f}s  z={tl['B'][i, 2]:.1f} d={b.ball_to_player(tl, i, focus):.1f}",
                     color="red" if i in marks else "black", fontsize=9)
    tr = sheet.add_subplot(rows, 1, rows)
    t = np.array([tl["GC"][ref] - tl["GC"][i] for i in frame_ids])
    tr.plot(t, tl["B"][lo:hi + 1, 2], label="ball z (ft)")
    tr.plot(t, [b.ball_to_player(tl, i, focus) for i in frame_ids], label="ball to player (ft)")
    for i, lab in marks.items():
        tr.axvline(tl["GC"][ref] - tl["GC"][i], color="red", ls="--")
        tr.text(tl["GC"][ref] - tl["GC"][i], 0.5, lab, color="red", fontsize=8)
    tr.axhline(3, color="gray", lw=0.5)
    tr.set_ylim(0, 16)
    tr.set_xlabel(f"seconds relative to {marks[ref]}")
    tr.legend(fontsize=8, loc="upper left")
    sheet.tight_layout()
    sheet.savefig(f"{stem}_sheet.png", dpi=70)
    plt.close(sheet)


if __name__ == "__main__":
    gid, lo, hi, stem = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    kv = [m.split("=") for m in sys.argv[5:]]
    player = next((int(v) for k, v in kv if k == "player"), None)
    game_stem = next((v for k, v in kv if k == "stem"), None)
    if game_stem:
        b.GAMES[gid] = game_stem
    marks = {int(v): k for k, v in kv if k not in ("player", "stem")}
    render(gid, lo, hi, stem, marks, player)
