"""Stage 3a value models (registered 4a3a3d3). Trains on league train-game catches, reports validation calibration,
fits shrunk per-player offsets on train games, writes out/s3/values.csv (gated players' train+validation catches)
and out/s3/values_report.json. Test games are never read past the split filter."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
S3 = ROOT / "out" / "s3"
GATED = {201939: "Curry", 2544: "LeBron", 201935: "Harden"}
ZONES = ["rim", "mid", "above_break3", "corner3"]
SHRINK_K = 50.0
PRIOR_SD = 0.3


def load():
    split = json.loads((ROOT / "checks/split.json").read_text())["split"]
    c = pd.read_csv(S3 / "catches.csv", dtype={"game": str})
    c["split"] = c.game.map(split)
    c = c[c.split != "test"].copy()  # test games are never touched in 3a
    p = pd.read_csv(S3 / "poss.csv", dtype={"game": str})
    c = c.merge(p, on=["game", "pid", "start"], how="left")
    s = pd.read_csv(S3 / "shots.csv", dtype={"game": str})
    made = {(g, e): m for g, e, m in zip(s.game, s.eventnum, s.made)}
    c["made"] = [made.get((g, e), np.nan) if not np.isnan(e) else np.nan for g, e in zip(c.game, c.shot_event)]
    shoot = c.catch_to_shot.notna() & (c.catch_to_shot <= 1.5)
    c["action"] = np.where(shoot, "shoot", np.where(c.f1_unknown, "unknown",
                           np.where(c.drive, "drive", np.where(c["pass"], "pass", "hold"))))
    c["excluded"] = np.where(c.action == "unknown", "unknown",
                             np.where((c.action == "drive") & (c.d_basket < 20), "drive_inside20", ""))
    feats = ["d_basket", "zone", "open_catch", "rim_prot", "shot_clock", "best_tm_open", "margin", "poss_points"]
    c.loc[c[feats].isna().any(axis=1) & (c.excluded == ""), "excluded"] = "missing_feature"
    c["points3"] = c.zone.isin(["above_break3", "corner3"]).astype(int)
    return c


def shoot_X(df):
    d = df.d_basket.values / 10.0
    z = np.stack([(df.zone == k).values for k in ZONES], 1).astype(float)
    lo = np.log1p(df.open_catch.clip(upper=30).values)
    return np.column_stack([d, d ** 2, z, lo, lo * df.points3.values])


def cont_X(df):
    d = df.d_basket.values / 10.0
    z = np.stack([(df.zone == k).values for k in ZONES], 1).astype(float)
    return np.column_stack([d, d ** 2, z, df.open_catch.clip(upper=15), df.rim_prot.clip(upper=20), df.shot_clock,
                            df.best_tm_open.clip(upper=20), df.margin.clip(-20, 20)])


def ece(p, y, bins=10):
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    tab = pd.DataFrame({"p": p, "y": y, "b": q}).groupby("b").agg(n=("y", "size"), pred=("p", "mean"), obs=("y", "mean"))
    return float((tab.n / tab.n.sum() * (tab.pred - tab.obs).abs()).sum()), tab.round(4).reset_index().to_dict("records")


def map_offset(logit, y, sd=PRIOR_SD):
    """MAP of a single additive logit offset with N(0, sd^2) prior (Newton)."""
    d = 0.0
    for _ in range(50):
        p = 1 / (1 + np.exp(-(logit + d)))
        g = np.sum(y - p) - d / sd ** 2
        h = -np.sum(p * (1 - p)) - 1 / sd ** 2
        step = g / h
        d -= step
        if abs(step) < 1e-10:
            break
    return float(d)


def main():
    c = load()
    use = c[c.excluded == ""]
    league = use[~use.pid.isin(GATED)]
    tr, va = league[league.split == "train"], league[league.split == "validation"]
    rep = {"n_league_train_catches": int(len(tr)), "n_league_val_catches": int(len(va)),
           "exclusions_all_nontest": c.excluded.replace("", "kept").value_counts().to_dict()}
    # --- V_shoot
    st, sv = tr[(tr.action == "shoot") & tr.made.notna()], va[(va.action == "shoot") & va.made.notna()]
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000).fit(shoot_X(st), st.made.astype(int))
    pv = lr.predict_proba(shoot_X(sv))[:, 1]
    e, tab = ece(pv, sv.made.values)
    rep["V_shoot"] = {"n_train_shots": int(len(st)), "n_val_shots": int(len(sv)), "ece_val": round(e, 4), "ece_limit": 0.03,
                      "passes_limit": bool(e <= 0.03), "decile_table_val": tab,
                      "val_brier": round(float(np.mean((pv - sv.made.values) ** 2)), 4),
                      "val_base_rate": round(float(sv.made.mean()), 4)}
    # --- continuation values
    scaler = StandardScaler().fit(cont_X(tr))
    models, rep["V_cont"] = {}, {}
    groups = {"drive": tr.action == "drive", "pass": tr.action == "pass", "hold": tr.action == "hold", "continue": tr.action != "shoot"}
    vgroups = {"drive": va.action == "drive", "pass": va.action == "pass", "hold": va.action == "hold", "continue": va.action != "shoot"}
    for a, m in groups.items():
        d = tr[m]
        models[a] = Ridge(alpha=1.0).fit(scaler.transform(cont_X(d)), d.poss_points)
        dv = va[vgroups[a]]
        pr = models[a].predict(scaler.transform(cont_X(dv)))
        q = pd.qcut(pr, 10, labels=False, duplicates="drop")
        tab = pd.DataFrame({"pred": pr, "obs": dv.poss_points.values, "b": q}).groupby("b").agg(n=("obs", "size"), pred=("pred", "mean"), obs=("obs", "mean")).round(3)
        rep["V_cont"][a] = {"n_train": int(len(d)), "n_val": int(len(dv)), "train_mean": round(float(d.poss_points.mean()), 3),
                            "val_rmse": round(float(np.sqrt(np.mean((pr - dv.poss_points) ** 2))), 4),
                            "val_rmse_intercept_only": round(float(np.sqrt(np.mean((d.poss_points.mean() - dv.poss_points) ** 2))), 4),
                            "decile_table_val": tab.reset_index().to_dict("records")}
    # shot-value mismatch size (league train shoot-now catches)
    sp = st.copy()
    sp["vshoot"] = lr.predict_proba(shoot_X(sp))[:, 1] * (2 + sp.points3)
    rep["shoot_value_mismatch"] = {"mean_poss_points_after_shoot_now": round(float(sp.poss_points.mean()), 3),
                                   "mean_V_shoot": round(float(sp.vshoot.mean()), 3),
                                   "gap": round(float(sp.poss_points.mean() - sp.vshoot.mean()), 3)}
    # --- gated players: values + offsets from their train games only
    g = use[use.pid.isin(GATED)].copy()
    g["logit_league"] = lr.decision_function(shoot_X(g))
    for a in models:
        g[f"V_{a}_league"] = models[a].predict(scaler.transform(cont_X(g)))
    rep["offsets"] = {}
    for pid, name in GATED.items():
        mine = g[(g.pid == pid) & (g.split == "train")]
        off = {"shoot_zone": {}, "cont": {}}
        sh = mine[(mine.action == "shoot") & mine.made.notna()]
        for z in ZONES:
            zz = sh[sh.zone == z]
            off["shoot_zone"][z] = {"n": int(len(zz)), "offset_logit": map_offset(zz.logit_league.values, zz.made.values) if len(zz) else 0.0}
        for a in models:
            m = (mine.action != "shoot") if a == "continue" else (mine.action == a)
            r = mine[m].poss_points - mine[m][f"V_{a}_league"]
            off["cont"][a] = {"n": int(m.sum()), "offset_points": float(r.sum() / (m.sum() + SHRINK_K))}
        rep["offsets"][name] = off
        sel = g.pid == pid
        zoff = g.loc[sel, "zone"].map({z: off["shoot_zone"][z]["offset_logit"] for z in ZONES})
        g.loc[sel, "V_shoot"] = (1 / (1 + np.exp(-(g.loc[sel, "logit_league"] + zoff)))) * (2 + g.loc[sel, "points3"])
        for a in models:
            g.loc[sel, f"V_{a}"] = g.loc[sel, f"V_{a}_league"] + off["cont"][a]["offset_points"]
    rep["gated_catches"] = {name: {"train": int(((g.pid == pid) & (g.split == "train")).sum()),
                                   "validation": int(((g.pid == pid) & (g.split == "validation")).sum()),
                                   "actions_train": g[(g.pid == pid) & (g.split == "train")].action.value_counts().to_dict()}
                            for pid, name in GATED.items()}
    rep["gated_exclusions_nontest"] = {name: c[c.pid == pid].excluded.replace("", "kept").value_counts().to_dict() for pid, name in GATED.items()}
    cols = ["game", "split", "pid", "start", "d_basket", "zone", "open_catch", "action", "V_shoot", "V_drive", "V_pass", "V_hold", "V_continue"]
    g[cols].to_csv(S3 / "values.csv", index=False)
    (S3 / "values_report.json").write_text(json.dumps(rep, indent=1, default=float))
    print(json.dumps({k: rep[k] for k in ("n_league_train_catches", "exclusions_all_nontest", "shoot_value_mismatch")}, indent=1))
    print("V_shoot ECE", rep["V_shoot"]["ece_val"], "n", rep["V_shoot"]["n_val_shots"])
    for a, r in rep["V_cont"].items():
        print(a, {k: r[k] for k in ("n_train", "val_rmse", "val_rmse_intercept_only")})
    print(json.dumps(rep["offsets"], indent=1))


if __name__ == "__main__":
    main()
