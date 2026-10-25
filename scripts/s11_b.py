"""Stage 6 B and D (registered 811c61b): identity effects, decision model (absolute/relative/both
openness), make-model falsification (rhythm, first shot, clock 5-24 s), exchange rate by zone,
rhythm response, defender tables. Writes out/s6/b.json and out/s6/catch_state.parquet-like CSV
for C.
"""

from collections.abc import Callable, Iterable
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit


sys.path.insert(0, str(Path(__file__).parent))
import contextlib

from s4_cont import logit_fit  # noqa: E402
from s4_data import GATED, ROOT, S4, load  # noqa: E402
from s4_make import X2  # noqa: E402
from s6_clock import cov  # noqa: E402


S5, S6 = ROOT / "out" / "s5", ROOT / "out" / "s6"
TAU = 0.15
NB = 500


def cat(pattern: Iterable[Path]) -> pd.DataFrame:
    return pd.concat([pd.read_csv(f, dtype={"game": str}) for f in sorted(pattern)])


def map_off(
    base_logit: np.ndarray, y: np.ndarray, groups: np.ndarray, tau: float = TAU
) -> pd.DataFrame:
    """Per-group MAP logit offsets with N(0, tau^2) prior.

    Returns DataFrame(group, n, offset, se).
    """
    out = []
    for g, ix in pd.Series(np.arange(len(groups))).groupby(groups):
        ix = ix.to_numpy()
        bl, yy = base_logit[ix], y[ix]
        d = 0.0
        for _ in range(30):
            p = expit(bl + d)
            gr = np.sum(yy - p) - d / tau**2
            hs = -np.sum(p * (1 - p)) - 1 / tau**2
            st = gr / hs
            d -= st
            if abs(st) < 1e-9:
                break
        p = expit(bl + d)
        out.append((g, len(ix), d, 1 / np.sqrt(np.sum(p * (1 - p)) + 1 / tau**2)))
    return pd.DataFrame(out, columns=["pid", "n", "offset", "se"])


def boot_games(
    d: pd.DataFrame, fn: Callable[[pd.DataFrame], Any], nb: int, seed: int
) -> np.ndarray:
    gi = {g: np.where(d.game.to_numpy() == g)[0] for g in d.game.unique()}
    gl = list(gi)
    r = np.random.default_rng(seed)
    res = []
    for _ in range(nb):
        with contextlib.suppress(np.linalg.LinAlgError, ValueError):
            res.append(fn(d.iloc[np.concatenate([gi[g] for g in r.choice(gl, len(gl))])]))
    return np.array(res)


def shot_margin() -> dict[tuple[str, int], int]:
    """Offence margin before each FGA, from PBP SCORE (visitor - home), by game/eventnum."""
    p = pd.read_csv(
        Path.home() / "Documents/nba-tracking/pbp/2015-16_pbp.csv",
        dtype={"GAME_ID": str},
        usecols=["GAME_ID", "EVENTNUM", "SCORE", "HOMEDESCRIPTION", "PLAYER1_TEAM_ID"],
    )
    out = {}
    for g, d in p.groupby("GAME_ID"):
        d = d.sort_values("EVENTNUM")
        hd = d[d.HOMEDESCRIPTION.notna() & d.PLAYER1_TEAM_ID.notna()]
        home = int(hd.PLAYER1_TEAM_ID.mode().iloc[0]) if len(hd) else None
        sc = d.SCORE.ffill().shift(1).fillna("0 - 0")
        for ev, s_, t in zip(d.EVENTNUM, sc, d.PLAYER1_TEAM_ID, strict=False):
            v, h = (int(x) for x in s_.split(" - "))
            out[(g, int(ev))] = (h - v) if (home is not None and t == home) else (v - h)
    return out


def main() -> None:
    rep = {}
    c, s = load()
    hts = pd.read_csv(S6 / "heights.csv").set_index("pid").height_cm
    s = s.merge(cat(S5.glob("motion_shots_*.csv")), on=["game", "eventnum"], how="left")
    s = s.merge(
        pd.read_csv(S6 / "state_shots.csv", dtype={"game": str}).drop(columns=["team"]),
        on=["game", "eventnum"],
        how="left",
    )
    s = s.merge(cat(S6.glob("frames_shots_*.csv")), on=["game", "eventnum"], how="left")
    s["cs"] = (s.catch_to_shot.notna() & (s.catch_to_shot <= 1.5)).astype(int)
    js = s[
        s.reason.astype(str).str.startswith("ok")
        & ~s.shooter.isin(GATED)
        & s.open_release_all.notna()
        & s.d_release.notna()
        & s.jump.astype(bool)
        & s.sc_release.notna()
        & s.s_closing_pre.notna()
        & s.s_speed.notna()
        & s.def_pid_rel.notna()
    ].copy()
    # base logit from the attempt-2 make model
    m = np.load(S4 / "make_model.npz")

    def base_logit(d: pd.DataFrame) -> np.ndarray:
        Xr = X2(d.d_release, d.zone_release, d.three, d.open_release_all, d.cs, d.sc_release)
        return float(m["A"]) * (
            ((Xr - m["mean"]) / m["scale"]) @ m["coef"].ravel() + m["intercept"][0]
        ) + float(m["B"])

    jtr = js[js.split == "train"].copy()
    ddef = map_off(
        base_logit(jtr), jtr.made.to_numpy(float), jtr.def_pid_rel.astype(int).to_numpy()
    )
    # rim protection: FGA within 6 ft (any type), opponent nearest the basket at release
    rim = s[
        s.reason.astype(str).str.startswith("ok")
        & ~s.shooter.isin(GATED)
        & (s.d_release <= 6)
        & s.rim_pid_rel.notna()
        & s.open_release_all.notna()
        & (s.split == "train")
    ].copy()
    Xb = np.column_stack(
        [np.ones(len(rim)), rim.d_release, np.log1p(rim.open_release_all.clip(upper=30))]
    )
    bb = logit_fit(Xb, rim.made.to_numpy(float))
    drim = map_off(Xb @ bb, rim.made.to_numpy(float), rim.rim_pid_rel.astype(int).to_numpy())
    c = c.merge(cat(S5.glob("motion_catches_*.csv")), on=["game", "pid", "start"], how="left")
    c = c.merge(
        pd.read_csv(S6 / "state_catches.csv", dtype={"game": str}),
        on=["game", "pid", "start"],
        how="left",
    )
    c = c.merge(cat(S6.glob("frames_catches_*.csv")), on=["game", "pid", "start"], how="left")
    dr = c[
        (c.split == "train")
        & ~c.pid.isin(GATED)
        & c.drive.astype(bool)
        & c.poss_points.notna()
        & c.rim_pid_catch.notna()
    ]
    res_ = dr.poss_points - dr.poss_points.mean()
    gg = res_.groupby(dr.rim_pid_catch.astype(int))
    ddrive = (gg.sum() / (gg.size() + 50)).rename("drive_eff")

    def mp(tab: pd.DataFrame) -> dict[int, float]:
        return dict(zip(tab.pid, tab.offset, strict=False))

    c["def_eff"] = c.def_pid_catch.map(mp(ddef)).fillna(0.0)
    c["rim_eff"] = c.rim_pid_catch.map(mp(drim)).fillna(0.0)
    c["drive_eff"] = c.rim_pid_catch.map(ddrive).fillna(0.0)
    c["def_h"] = c.def_pid_catch.map(hts)
    rep["height_coverage_catches_nearest_def"] = round(float(c.def_h.notna().mean()), 4)
    hmean = float(c.def_h.mean())
    c["def_h_missing"] = c.def_h.isna().astype(float)
    c["def_h"] = c.def_h.fillna(hmean)
    c["clutch"] = ((c.quarter >= 4) & (c.gc <= 300) & (c.margin.abs() <= 5)).astype(float)
    c.to_csv(S6 / "catch_state.csv", index=False)
    # ---------------- B6 decision model
    u = c[
        (c.d_basket >= 16)
        & (c.d_basket <= 30)
        & c.shot_clock.notna()
        & c.action.isin(["shoot", "continue"])
        & c.closing_pre.notna()
        & c.closing_post.notna()
        & c.catcher_speed.notna()
        & c.minutes_so_far.notna()
        & c.rel_open.notna()
    ].copy()
    u["y"] = (u.action == "shoot").astype(float)

    def feats(d: pd.DataFrame, variant: str, identity: bool = True) -> np.ndarray:
        X = cov(d)  # 1, clock, open, d10, d10sq, ab3, c3, best_tm
        if variant == "relative":
            X[:, 2] = d.rel_open.to_numpy(float)
        sp = d.catcher_speed.clip(0, 25).to_numpy(float)
        src = d.source5.fillna("other")
        mot = np.column_stack(
            [
                d.closing_pre.clip(-15, 15),
                d.closing_post.clip(-15, 15),
                sp,
                (sp < 3),
                d.n_def6.clip(upper=3),
                d.flight_time.clip(0, 3),
                d.flight_dist.clip(0, 60),
                src == "oreb",
                src == "inbound",
                src == "other",
            ]
        ).astype(float)
        A = np.column_stack(
            [
                d.m3,
                d.m5,
                d.none_yet,
                d.last_made.fillna(0),
                d.t_since_make,
                d.first_made.fillna(0),
                d.def_h / 10,
                d.def_h_missing,
                d.minutes_so_far / 10,
                d.b2b,
                d.clutch,
            ]
        ).astype(float)
        cols = [X, mot, A]
        if identity:
            cols.append(np.column_stack([d.def_eff, d.rim_eff, d.drive_eff]))
        if variant == "both":
            cols.append(d.rel_open.to_numpy(float)[:, None])
        return np.column_stack(cols)

    def fnames(variant: str, identity: bool = True) -> list[str]:
        return (
            [
                "intercept",
                "shot_clock",
                "rel_open" if variant == "relative" else "open_catch",
                "d10",
                "d10sq",
                "ab3",
                "c3",
                "best_tm",
                "closing_pre",
                "closing_post",
                "catcher_speed",
                "set",
                "n_def6",
                "flight_time",
                "flight_dist",
                "src_oreb",
                "src_inbound",
                "src_other",
                "m3",
                "m5",
                "none_yet",
                "last_made",
                "t_since_make",
                "first_made",
                "def_height_10cm",
                "def_h_missing",
                "minutes_10",
                "b2b",
                "clutch",
            ]
            + (["def_eff", "rim_eff", "drive_eff"] if identity else [])
            + (["rel_open"] if variant == "both" else [])
        )

    lt, lv = (
        u[~u.pid.isin(GATED) & (u.split == "train")],
        u[~u.pid.isin(GATED) & (u.split == "validation")],
    )

    def logloss(b: np.ndarray, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        p = np.clip(expit(X @ b), 1e-9, 1 - 1e-9)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))

    dec = {"n_train": int(len(lt)), "n_val": int(len(lv)), "variants": {}}
    coefs_by_variant = {}
    for v in ("absolute", "relative", "both"):
        b = logit_fit(feats(lt, v), lt.y.to_numpy())
        coefs_by_variant[v] = dict(zip(fnames(v), b, strict=False))
        dec["variants"][v] = {
            "val_logloss": round(float(logloss(b, feats(lv, v), lv.y.to_numpy()).mean()), 5),
            "m3": round(float(coefs_by_variant[v]["m3"]), 4),
            "m5": round(float(coefs_by_variant[v]["m5"]), 4),
            "last_made": round(float(coefs_by_variant[v]["last_made"]), 4),
        }
    # identity improvement (variant both)
    b_id = logit_fit(feats(lt, "both"), lt.y.to_numpy())
    b_no = logit_fit(feats(lt, "both", False), lt.y.to_numpy())
    dl = logloss(b_id, feats(lv, "both"), lv.y.to_numpy()) - logloss(
        b_no, feats(lv, "both", False), lv.y.to_numpy()
    )
    gi = {g: np.where(lv.game.to_numpy() == g)[0] for g in lv.game.unique()}
    gl = list(gi)
    r = np.random.default_rng(0)
    bsd = [dl[np.concatenate([gi[g] for g in r.choice(gl, len(gl))])].mean() for _ in range(1000)]
    dec["identity_val_logloss_change"] = [
        round(float(dl.mean()), 6),
        np.quantile(bsd, [0.025, 0.975]).round(6).tolist(),
    ]
    # window choice: larger |coef x SD| in the league "both" model
    sd3, sd5 = float(lt.m3.std()), float(lt.m5.std())
    w = (
        "m3"
        if abs(coefs_by_variant["both"]["m3"] * sd3) >= abs(coefs_by_variant["both"]["m5"] * sd5)
        else "m5"
    )
    dec["window_choice"] = {
        "m3_coef_x_sd": round(float(coefs_by_variant["both"]["m3"] * sd3), 4),
        "m5_coef_x_sd": round(float(coefs_by_variant["both"]["m5"] * sd5), 4),
        "chosen": w,
    }

    # coefficient intervals: league (both) and players (both, non-test catches)
    def coef_table(d: pd.DataFrame, seed: int) -> dict[str, list[Any]]:
        X, y = feats(d, "both"), d.y.to_numpy()
        b = logit_fit(X, y)
        bs = boot_games(d, lambda x: logit_fit(feats(x, "both"), x.y.to_numpy()), NB, seed)
        lo, hi = np.quantile(bs, [0.025, 0.975], axis=0)
        return {
            n: [round(float(b[i]), 4), [round(float(lo[i]), 4), round(float(hi[i]), 4)]]
            for i, n in enumerate(fnames("both"))
        }

    dec["coefficients"] = {"League": coef_table(lt, 0)}
    for k, (pid, name) in enumerate(GATED.items()):
        dec["coefficients"][name] = coef_table(u[u.pid == pid], 10 + k)
    rep["decision"] = dec
    print(
        "DECISION",
        json.dumps({kk: vv for kk, vv in dec.items() if kk != "coefficients"}, indent=1),
        flush=True,
    )
    # ---------------- B7 make model with all of A
    mg = shot_margin()
    jtr["margin_shot"] = [
        mg.get((g, int(e)), 0) for g, e in zip(jtr.game, jtr.eventnum, strict=False)
    ]
    jtr["def_h"] = jtr.def_pid_rel.map(hts)
    jtr["def_h_missing"] = jtr.def_h.isna().astype(float)
    jtr["def_h"] = jtr.def_h.fillna(hmean)
    jtr["def_eff_rel"] = jtr.def_pid_rel.map(mp(ddef)).fillna(0.0)
    jtr["clutch"] = (
        (jtr.q_release >= 4) & (jtr.gc_release <= 300) & (jtr.margin_shot.abs() <= 5)
    ).astype(float)
    jtr = jtr[jtr.shooter_minutes.notna()].reset_index(drop=True)

    def mfeats(d: pd.DataFrame) -> np.ndarray:
        base = X2(d.d_release, d.zone_release, d.three, d.open_release_all, d.cs, d.sc_release)[
            :, :-2
        ]
        sc = d.sc_release.to_numpy(float)
        sp = d.s_speed.clip(0, 25).to_numpy(float)
        return np.column_stack(
            [
                base,
                (sc <= 4),
                np.clip(sc, 4, 24) - 4,
                d.s_closing_pre.clip(-15, 15),
                sp,
                (sp < 3),
                d.s_n_def6.clip(upper=3),
                d[w],
                d.none_yet,
                d.last_made.fillna(0),
                d.t_since_make,
                d.first_made.fillna(0),
                d.def_h / 10,
                d.def_h_missing,
                d.shooter_minutes / 10,
                d.b2b.fillna(0),
                d.clutch,
                d.def_eff_rel,
            ]
        ).astype(float)

    K = mfeats(jtr.iloc[:5]).shape[1]
    _probe = mfeats(jtr.iloc[:200])
    assert np.allclose(_probe[:, K - 11], jtr.iloc[:200][w].to_numpy(float)) and np.allclose(
        _probe[:, K - 7], jtr.iloc[:200].first_made.fillna(0).to_numpy(float)
    )
    # columns from the end: def_eff_rel -1, clutch -2, b2b -3, minutes -4, def_h_missing -5, def_h
    # -6, first_made -7, t_since_make -8, last_made -9, none_yet -10, window -11, n_def6 -12, set
    # -13, speed -14, closing -15, clock_mid -16, late -17
    IDX = {"clock_mid": K - 16, "window": K - 11, "last_made": K - 9, "first_made": K - 7}

    def ames(d: pd.DataFrame) -> dict[str, float]:
        X = mfeats(d)
        mu, sdv = X.mean(0), X.std(0)
        sdv[sdv == 0] = 1
        Xs = np.column_stack([np.ones(len(X)), (X - mu) / sdv])
        b = logit_fit(Xs, d.made.to_numpy(float))
        p = expit(Xs @ b)
        dp = p * (1 - p)
        sc = d.sc_release.to_numpy(float) > 4
        has = d.none_yet.to_numpy() == 0
        out = {
            "clock_mid": float(np.mean(dp[sc]) * b[1 + IDX["clock_mid"]] / sdv[IDX["clock_mid"]]),
            "window": float(np.mean(dp[has]) * b[1 + IDX["window"]] / sdv[IDX["window"]]),
        }
        for nm in ("first_made", "last_made"):
            j = IDX[nm]
            X1, X0 = X[has].copy(), X[has].copy()
            X1[:, j] = 1
            X0[:, j] = 0

            def f(Z: np.ndarray) -> np.ndarray:
                return expit(np.column_stack([np.ones(len(Z)), (Z - mu) / sdv]) @ b)

            out[nm] = float(np.mean(f(X1) - f(X0)))
        return out

    pt = ames(jtr)
    bs = boot_games(jtr, lambda x: list(ames(x).values()), NB, 1)
    keys = list(pt)
    mk = {}
    for i, kname in enumerate(keys):
        lo, hi = np.quantile(bs[:, i], [0.025, 0.975])
        valid = abs(pt[kname]) < 0.02 and ((lo <= 0 <= hi) or (lo >= -0.03 and hi <= 0.03))
        mk[kname] = {
            "ame": round(pt[kname], 5),
            "ci95": [round(float(lo), 5), round(float(hi), 5)],
            "valid": bool(valid),
            "leak": bool(valid and not (lo <= 0 <= hi)),
        }
    mk["n_shots"] = int(len(jtr))
    mk["window_used"] = w
    mk["valid_instruments"] = [k for k in ("clock_mid", "window", "first_made") if mk[k]["valid"]]
    rep["make_falsification"] = mk
    print("MAKE", json.dumps(mk, indent=1), flush=True)

    # ---------------- D9 exchange rate by zone
    def er(d: pd.DataFrame) -> tuple[float, float]:
        b = logit_fit(cov(d), d.y.to_numpy())
        return -b[2] / b[1], b[1]

    zone_res = {}
    for gname, gd in [("League", lt)] + [(n, u[u.pid == p]) for p, n in GATED.items()]:
        zone_res[gname] = {}
        for zn, mask in (
            ("threes", gd.zone.isin(["above_break3", "corner3"])),
            ("mid", gd.zone == "mid"),
        ):
            dd = gd[mask]
            if (dd.y.sum() < 10) or len(dd) < 50:
                zone_res[gname][zn] = {
                    "n": int(len(dd)),
                    "shots": int(dd.y.sum()),
                    "note": "too thin",
                }
                continue
            e0, bc = er(dd)
            bsz = boot_games(dd, lambda x: er(x), 1000, 20)
            cc_ = np.quantile(bsz[:, 1], [0.025, 0.975])
            zone_res[gname][zn] = {
                "n": int(len(dd)),
                "shots": int(dd.y.sum()),
                "ER": round(float(e0), 3),
                "ER_ci": np.quantile(bsz[:, 0], [0.025, 0.975]).round(3).tolist(),
                "clock_resolved": bool(cc_[1] < 0 or cc_[0] > 0),
            }
    rep["er_by_zone"] = zone_res
    # ---------------- D10 rhythm response
    rr = {}
    for pid, name in GATED.items():
        d = u[(u.pid == pid) & (u.n_prior >= 3)]

        def resp(x: pd.DataFrame, col: str, hi_vals: list[int], lo_vals: list[int]) -> list[float]:
            a, b_ = x[x[col].isin(hi_vals)], x[x[col].isin(lo_vals)]
            sa, sb = a[a.y == 1], b_[b_.y == 1]
            return [
                a.y.mean() - b_.y.mean(),
                (sa.open_catch.median() if len(sa) else np.nan)
                - (sb.open_catch.median() if len(sb) else np.nan),
            ]

        out = {}
        for lab, col, hv, lv_ in (
            ("m3_2_3_vs_0_1", "m3", [2, 3], [0, 1]),
            ("first_made_1_vs_0", "first_made", [1], [0]),
        ):
            hi_d, lo_d = d[d[col].isin(hv)], d[d[col].isin(lv_)]
            pt_ = resp(d, col, hv, lv_)
            bsr = boot_games(d, lambda x: resp(x, col, hv, lv_), 1000, 30)
            out[lab] = {
                "n_hi": int(len(hi_d)),
                "n_lo": int(len(lo_d)),
                "shoot_rate_hi": round(float(hi_d.y.mean()), 3),
                "shoot_rate_lo": round(float(lo_d.y.mean()), 3),
                "shoot_rate_diff": [
                    round(float(pt_[0]), 3),
                    np.nanquantile(bsr[:, 0], [0.025, 0.975]).round(3).tolist(),
                ],
                "median_open_accepted_diff_ft": [
                    round(float(pt_[1]), 2),
                    np.nanquantile(bsr[:, 1], [0.025, 0.975]).round(2).tolist(),
                ],
            }
        rr[name] = out
    rep["rhythm_response"] = rr
    # ---------------- D11 defender tables
    names = pd.read_csv(S6 / "heights.csv").set_index("pid").name
    t1 = ddef[ddef.n >= 100].sort_values("offset").head(10)
    t2 = drim[drim.n >= 50].sort_values("offset").head(10)

    def fmt(t: pd.DataFrame) -> list[dict[str, Any]]:
        return [
            {
                "name": names.get(int(r.pid), str(int(r.pid))),
                "contests": int(r.n),
                "offset_logit": round(float(r.offset), 3),
                "ci95": [
                    round(float(r.offset - 1.96 * r.se), 3),
                    round(float(r.offset + 1.96 * r.se), 3),
                ],
            }
            for r in t.itertuples()
        ]

    rep["defenders"] = {
        "top10_jump_shot_defenders": fmt(t1),
        "top10_rim_protectors": fmt(t2),
        "n_defenders_ge100": int((ddef.n >= 100).sum()),
        "n_rim_ge50": int((drim.n >= 50).sum()),
        "caveat": "shots over the best defenders are the ones players chose to take",
    }
    (S6 / "b.json").write_text(json.dumps(rep, indent=1, default=float))
    print(
        "D",
        json.dumps(
            {k: rep[k] for k in ("er_by_zone", "rhythm_response", "defenders")},
            indent=1,
            default=float,
        ),
    )


if __name__ == "__main__":
    main()
