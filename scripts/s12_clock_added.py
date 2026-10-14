"""Stage 7: clock-added shots (registered e5933e9).

  s12_clock_added.py power     power from the training pilot, scaled to the confirmatory size -> checks/s7_power.json
  s12_clock_added.py confirm   the confirmatory analysis, run once -> out/s7/stage7.json (+ figure)

Nuisance terms of the make model are fitted on TRAINING shots only and held fixed as an offset; clock-bin effects are
estimated on the confirmatory sample (validation + calibration games). Test rows are dropped at load and asserted absent.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).parent))
from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, ROOT, S4, load  # noqa: E402
from s4_make import OPEN_KNOTS  # noqa: E402
from vshoot2 import ns_basis  # noqa: E402

OUT = ROOT / "out" / "s7"
BINS = [0, 4, 8, 12, 16, 20, 24]
LAB = ["[0,4)", "[4,8)", "[8,12)", "[12,16)", "[16,20)", "[20,24)"]
ZONES3 = ["mid", "above_break3", "corner3"]
CONF = {"validation", "calib"}
NB = 1000


def frames():
    split = json.loads((ROOT / "checks/split_all.json").read_text())["split"]
    c, s = load()  # load() drops test rows on read
    ms = pd.concat([pd.read_csv(f, dtype={"game": str}) for f in sorted((ROOT / "out/s5").glob("motion_shots_*.csv"))])
    s = s.merge(ms, on=["game", "eventnum"], how="left")
    sh = s[s.reason.astype(str).str.startswith("ok") & s.jump.astype(bool) & ~s.shooter.isin(GATED)
           & (s.d_release >= 16) & (s.d_release <= 30) & s.sc_release.notna() & (s.sc_release < 24) & s.open_release_all.notna()].copy()
    n_before = len(sh)
    sh = sh[sh.s_closing_pre.notna() & sh.s_speed.notna() & sh.s_n_def6.notna()].copy()
    dropped = n_before - len(sh)
    sh["bin"] = pd.cut(sh.sc_release, BINS, right=False, labels=LAB)
    sh["cs"] = (sh.catch_to_shot.notna() & (sh.catch_to_shot <= 1.5)).astype(float)
    vs = pd.read_csv(S4 / "vshoot.csv", dtype={"game": str})
    ca = vs[~vs.pid.isin(GATED) & (vs.d_basket >= 16) & (vs.d_basket <= 30) & vs.shot_clock.notna() & (vs.shot_clock < 24)
            & vs.action.isin(["shoot", "continue"])].copy()
    ca["bin"] = pd.cut(ca.shot_clock, BINS, right=False, labels=LAB)
    ca["y"] = (ca.action == "shoot").astype(float)
    for d in (sh, ca):
        assert not (d.split == "test").any(), "test rows present"
        assert not d.game.map(split).eq("test").any(), "test games present"
    return sh, ca, int(dropped)


def nuisance_X(d):
    op = d.open_release_all.clip(upper=30).to_numpy(float)
    z = np.stack([(d.zone_release == q).to_numpy() for q in ZONES3[1:]], 1).astype(float)  # mid reference
    return np.column_stack([ns_basis(op, OPEN_KNOTS), ns_basis(d.d_release.to_numpy(float)), z, d.three.astype(float),
                            d.cs, d.s_closing_pre.clip(-15, 15), d.s_speed.clip(0, 25), d.s_n_def6.clip(upper=3)])


def bin_D(d, labels):
    return np.stack([(d.bin.astype(str) == b).to_numpy() for b in labels], 1).astype(float)


class Nuisance:
    """Full model on training shots (all bins 0-24, [20,24) reference); keeps the nuisance part as a fixed offset."""

    def __init__(self, tr):
        Xn = nuisance_X(tr)
        self.mu, self.sd = Xn.mean(0), Xn.std(0)
        self.sd[self.sd == 0] = 1
        D = bin_D(tr, LAB[:-1])
        b = logit_fit(np.column_stack([np.ones(len(tr)), (Xn - self.mu) / self.sd, D]), tr.made.to_numpy(float))
        self.beta = b[1:1 + Xn.shape[1]]

    def offset(self, d):
        return ((nuisance_X(d) - self.mu) / self.sd) @ self.beta


def clock_fit(d, off, labels):
    """Intercept + bin dummies (reference = last of LAB) with fixed offset. Returns per-bin adjusted mean prob function."""
    D = bin_D(d, labels)
    X = np.column_stack([np.ones(len(d)), D])
    # logit_fit has no offset argument: Newton with offset
    b = np.zeros(X.shape[1]); y = d.made.to_numpy(float)
    for _ in range(50):
        p = expit(X @ b + off)
        H = (X * (p * (1 - p))[:, None]).T @ X + 1e-8 * np.eye(X.shape[1])
        st = np.linalg.solve(H, X.T @ (y - p)); b += st
        if np.abs(st).max() < 1e-10:
            break
    coef = dict(zip(labels, b[1:]))
    def adj(label):  # mean predicted prob over these shots with every shot set to bin `label`
        return float(np.mean(expit(b[0] + coef.get(label, 0.0) + off)))
    return adj


def stats(sh, ca, nu):
    main = sh[sh.sc_release >= 4]
    off = nu.offset(main)
    adj = clock_fit(main, off, LAB[1:-1])
    n12, n16 = (main.bin.astype(str) == "[12,16)").sum(), (main.bin.astype(str) == "[16,20)").sum()
    w = n12 / max(n12 + n16, 1)
    pooled = w * adj("[12,16)") + (1 - w) * adj("[16,20)")
    ame = adj("[4,8)") - pooled
    cm = ca[ca.shot_clock >= 4]
    r48 = cm[cm.bin.astype(str) == "[4,8)"].y.mean()
    r1220 = cm[cm.bin.astype(str).isin(["[12,16)", "[16,20)"])].y.mean()
    m = (r48 - r1220) / r48
    out = {"ame": ame, "m": m, "delta": ame / m, "adj": {b: adj(b) for b in LAB[1:]}}
    # info: [0,4) vs pooled [12,20), on 0-24 shots
    allb = sh
    adj0 = clock_fit(allb, nu.offset(allb), LAB[:-1])
    n12b, n16b = (allb.bin.astype(str) == "[12,16)").sum(), (allb.bin.astype(str) == "[16,20)").sum()
    wb = n12b / max(n12b + n16b, 1)
    out["ame_0_4"] = adj0("[0,4)") - (wb * adj0("[12,16)") + (1 - wb) * adj0("[16,20)"))
    out["adj_0_4"] = adj0("[0,4)")
    # info: catch-and-shoot only
    csd = main[main.cs == 1]
    adjc = clock_fit(csd, nu.offset(csd), LAB[1:-1])
    n12c, n16c = (csd.bin.astype(str) == "[12,16)").sum(), (csd.bin.astype(str) == "[16,20)").sum()
    wc = n12c / max(n12c + n16c, 1)
    out["ame_cs"] = adjc("[4,8)") - (wc * adjc("[12,16)") + (1 - wc) * adjc("[16,20)"))
    return out


def boot(sh, ca, nu, seed):
    games = np.array(sorted(set(sh.game) | set(ca.game)))
    gs = {g: np.where(sh.game.to_numpy() == g)[0] for g in games}
    gc = {g: np.where(ca.game.to_numpy() == g)[0] for g in games}
    r = np.random.default_rng(seed)
    rows = []
    for _ in range(NB):
        pick = r.choice(games, len(games))
        bs = sh.iloc[np.concatenate([gs[g] for g in pick])]
        bc = ca.iloc[np.concatenate([gc[g] for g in pick])]
        try:
            st = stats(bs, bc, nu)
        except (np.linalg.LinAlgError, ZeroDivisionError):
            continue
        rows.append([st["ame"], st["m"], st["delta"], st["ame_0_4"], st["ame_cs"]] + [st["adj"][b] for b in LAB[1:]] + [st["adj_0_4"]])
    return np.array(rows)


def raw_table(sh, ca):
    t = []
    for b in LAB:
        s_, c_ = sh[sh.bin.astype(str) == b], ca[ca.bin.astype(str) == b]
        t.append({"bin": b, "shots": int(len(s_)), "raw_make": round(float(s_.made.mean()), 4) if len(s_) else None,
                  "catches": int(len(c_)), "shoot_rate": round(float(c_.y.mean()), 4) if len(c_) else None})
    return t


def ci(x):
    return [round(float(v), 4) for v in np.quantile(x, [.025, .975])]


def power():
    sh, ca, dropped = frames()
    tr_s, tr_c = sh[sh.split == "train"], ca[ca.split == "train"]
    cf_s, cf_c = sh[sh.split.isin(CONF)], ca[ca.split.isin(CONF)]
    nu = Nuisance(tr_s)
    pt = stats(tr_s, tr_c, nu)
    b = boot(tr_s, tr_c, nu, 0)
    g_tr = len(set(tr_s.game) | set(tr_c.game)); g_cf = len(set(cf_s.game) | set(cf_c.game))
    scale = np.sqrt(g_tr / g_cf)
    se_ame, se_d = float(np.std(b[:, 0])) * scale, float(np.std(b[:, 2])) * scale
    res = {"source": "training pilot (spent), game-bootstrap SEs scaled by sqrt(train games / confirmatory games)",
           "train_games": g_tr, "confirmatory_games": g_cf, "scale": round(float(scale), 4),
           "train_shots_main": int((tr_s.sc_release >= 4).sum()), "confirmatory_shots_main": int((cf_s.sc_release >= 4).sum()),
           "pilot_point": {"ame": round(pt["ame"], 4), "m": round(pt["m"], 4), "delta": round(pt["delta"], 4)},
           "expected_se_ame": round(se_ame, 4), "expected_se_delta": round(se_d, 4),
           "smallest_detectable_delta_80pct": round(2.8 * se_d, 4), "motion_dropped_all_splits": dropped}
    (ROOT / "checks/s7_power.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def confirm():
    OUT.mkdir(parents=True, exist_ok=True)
    sh, ca, dropped = frames()
    tr_s = sh[sh.split == "train"]
    cf_s, cf_c = sh[sh.split.isin(CONF)].copy(), ca[ca.split.isin(CONF)].copy()
    nu = Nuisance(tr_s)
    pt = stats(cf_s, cf_c, nu)
    b = boot(cf_s, cf_c, nu, 0)
    dl = ci(b[:, 2])
    reading = ("The added shots are not detectably worse" if dl[0] > -0.05 else
               "The added shots are worse" if dl[1] < -0.05 else "Unresolved at this sample size")
    res = {"confirmatory_games": int(len(set(cf_s.game) | set(cf_c.game))), "confirmatory_shots_0_24": int(len(cf_s)),
           "confirmatory_shots_main_4_24": int((cf_s.sc_release >= 4).sum()), "confirmatory_catches_0_24": int(len(cf_c)),
           "shots_dropped_missing_motion_confirmatory": int(dropped), "bootstrap_ok": int(len(b)),
           "m_marginal_share": [round(pt["m"], 4), ci(b[:, 1])],
           "ame_4_8_vs_12_20": [round(pt["ame"], 4), ci(b[:, 0])],
           "delta": [round(pt["delta"], 4), dl], "reading": reading,
           "info_ame_0_4_vs_12_20": [round(pt["ame_0_4"], 4), ci(b[:, 3])],
           "info_ame_catch_and_shoot_only": [round(pt["ame_cs"], 4), ci(b[:, 4])],
           "adjusted_make_by_bin": {bb: [round(pt["adj"][bb], 4), ci(b[:, 5 + i])] for i, bb in enumerate(LAB[1:])},
           "adjusted_make_0_4": [round(pt["adj_0_4"], 4), ci(b[:, -1])],
           "raw_table": raw_table(cf_s, cf_c)}
    (OUT / "stage7.json").write_text(json.dumps(res, indent=1))
    print("RAW"); print(pd.DataFrame(res["raw_table"]).to_string(index=False))
    print("ADJUSTED"); print(json.dumps({k: v for k, v in res.items() if k != "raw_table"}, indent=1))
    # figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = np.arange(len(LAB))
    raw = pd.DataFrame(res["raw_table"])
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(x[1:], raw.shoot_rate[1:], "o-", color="#1f6feb", label="shoot-now rate (catches)")
    ax.plot([0], [raw.shoot_rate[0]], "o", color="#1f6feb", alpha=.35)
    adjv = [res["adjusted_make_by_bin"][bb][0] for bb in LAB[1:]]
    lo = [res["adjusted_make_by_bin"][bb][1][0] for bb in LAB[1:]]; hi = [res["adjusted_make_by_bin"][bb][1][1] for bb in LAB[1:]]
    ax.errorbar(x[1:], adjv, yerr=[np.array(adjv) - lo, np.array(hi) - adjv], fmt="s-", color="#d1242f", capsize=3, label="adjusted make rate (taken shots)")
    a0 = res["adjusted_make_0_4"]
    ax.errorbar([0], [a0[0]], yerr=[[a0[0] - a0[1][0]], [a0[1][1] - a0[0]]], fmt="s", color="#d1242f", alpha=.35, capsize=3)
    ax.text(0, max(a0[1][1], raw.shoot_rate[0]) + 0.02, "rushed", ha="center", color="gray", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"{l} s" for l in LAB]); ax.set_xlabel("shot clock at the catch / release")
    ax.set_ylim(0, 0.6); ax.set_ylabel("rate"); ax.legend(loc="upper right", fontsize=9); ax.grid(alpha=.3)
    ax.set_title("League catches and jump shots, 16-30 ft (validation + calibration games)", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / "stage7_clock_added.svg"); fig.savefig(OUT / "stage7_clock_added.png", dpi=120)


if __name__ == "__main__":
    {"power": power, "confirm": confirm}[sys.argv[1]]()
