"""
3x3 Wald and single-metric Wald (dbd_o2_gmv as primary X).
Uses DD_METRICS from dd_metrics_reference; writes experiment_level_xy, wald_3x3, wald_single_metric_by_dd_o2_gmv.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from dd_metrics_reference import DD_METRICS

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_CSV = REPO_ROOT / "experiments" / "experiment_list.csv"
RESULTS_DIR = REPO_ROOT / "experiment-results"
ANALYSIS_DIR = Path(__file__).resolve().parent

DBD_X = "dbd_o2_gmv"
DBD_X_TRIALS = "dbd_o2_trials_per_cx"
P_ALPHA = 0.25  # directional threshold for 3-level classification


def _parse_num(s):
    if pd.isna(s) or s in ("-", "", "N/A"):
        return None
    try:
        return float(str(s).strip().replace(",", ""))
    except ValueError:
        return None


def _resolve_csv_path(analysis_name: str):
    exact = RESULTS_DIR / f"{analysis_name}.csv"
    pattern = re.compile(re.escape(analysis_name) + r" \((\d+)\)\.csv$", re.IGNORECASE)
    numbered = []
    for p in RESULTS_DIR.glob("*.csv"):
        m = pattern.match(p.name)
        if m:
            numbered.append((int(m.group(1)), p))
    numbered.sort(key=lambda x: x[0])
    if numbered:
        return numbered[0][1]
    if exact.exists():
        return exact
    for p in RESULTS_DIR.glob("*.csv"):
        if p.stem.lower() == analysis_name.lower():
            return p
    return None


def load_experiment_metrics(csv_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame()
    if "Metric Name" not in df.columns:
        return pd.DataFrame()
    cols = [c for c in df.columns if isinstance(c, str)]
    rel_cols = [c for c in cols if "Relative Impact" in c and "Confidence" not in c]
    if not rel_cols:
        return pd.DataFrame()
    rel_col = rel_cols[0]
    prefix = rel_col.replace(" Relative Impact", "").strip()
    p_cols = [c for c in cols if prefix in c and "P Value" in c and "Confidence" not in c]
    p_col = p_cols[0] if p_cols else None
    out = df[["Metric Name"]].copy()
    out["relative_impact"] = df[rel_col].map(_parse_num)
    out["p_value"] = df[p_col].map(_parse_num) if p_col else None
    return out


def load_merged() -> pd.DataFrame:
    exp_list = pd.read_csv(EXPERIMENTS_CSV)
    with_aname = exp_list[
        exp_list["analysis_name"].notna() & (exp_list["analysis_name"].astype(str).str.strip() != "")
    ]
    all_metrics = []
    for _, row in with_aname.iterrows():
        aname = str(row["analysis_name"]).strip()
        path = _resolve_csv_path(aname)
        if path is None:
            continue
        df = load_experiment_metrics(path)
        if df.empty:
            continue
        df["analysis_name"] = aname
        df["experiment_name"] = row.get("name", aname)
        all_metrics.append(df)
    if not all_metrics:
        return pd.DataFrame()
    return pd.concat(all_metrics, ignore_index=True)


def _to_3lev(lift, p_val):
    if lift is None or p_val is None or p_val > P_ALPHA:
        return 0
    return -1 if lift < 0 else 1


def run():
    merged = load_merged()
    if merged.empty:
        print("No experiment data loaded.")
        return

    wide_impact = merged.pivot_table(
        index="analysis_name", columns="Metric Name", values="relative_impact"
    )
    wide_p = merged.pivot_table(
        index="analysis_name", columns="Metric Name", values="p_value"
    )
    exp_names = merged.drop_duplicates("analysis_name").set_index("analysis_name")["experiment_name"]

    if DBD_X not in wide_impact.columns:
        print(f"'{DBD_X}' not in any export. Cannot run Wald.")
        return

    # --- Experiment-level XY (for 3x3) ---
    # X = dbd_o2_gmv, Y = mean of available DD metrics per experiment
    available_dd = [m for m in DD_METRICS if m in wide_impact.columns]
    if not available_dd:
        print("No DD metrics found in exports.")
        return

    rows = []
    for aname in wide_impact.index:
        x_lift = wide_impact.loc[aname, DBD_X]
        if pd.isna(x_lift):
            continue  # require primary X for 3x3
        x_p = wide_p.loc[aname, DBD_X] if DBD_X in wide_p.columns else None
        dd_lifts = [wide_impact.loc[aname, m] for m in available_dd if pd.notna(wide_impact.loc[aname, m])]
        dd_ps = [wide_p.loc[aname, m] for m in available_dd if pd.notna(wide_impact.loc[aname, m]) and m in wide_p.columns and pd.notna(wide_p.loc[aname, m])]
        if not dd_lifts:
            continue
        y_lift = np.mean(dd_lifts)
        min_p_dd = min(dd_ps) if dd_ps else None
        x_3 = _to_3lev(x_lift, x_p)
        y_3 = _to_3lev(y_lift, min_p_dd)
        present_dd = [m for m in available_dd if pd.notna(wide_impact.loc[aname, m])]
        rows.append({
            "experiment_name": exp_names.get(aname, aname),
            "analysis_name": aname,
            "X_binary": 1 if x_lift and x_lift > 0 else (0 if x_lift and x_lift < 0 else 0),
            "Y_binary": 1 if y_lift and y_lift > 0 else (0 if y_lift and y_lift < 0 else 0),
            "X_3lev": x_3,
            "Y_3lev": y_3,
            "dbd_avg_lift": x_lift,
            "dd_avg_lift": y_lift,
            "missing_dbd": "" if pd.notna(x_lift) else DBD_X,
            "missing_dd": "|".join(present_dd),
        })
    xy_df = pd.DataFrame(rows)
    xy_path = ANALYSIS_DIR / "experiment_level_xy.csv"
    xy_df.to_csv(xy_path, index=False)
    print(f"Saved: {xy_path} ({len(xy_df)} experiments)")

    # --- 3x3 Wald ---
    levs = [-1, 0, 1]
    labels = {-1: "DbD deg", 0: "DbD flat", 1: "DbD imp"}
    dd_labels = {-1: "DD deg", 0: "DD flat", 1: "DD imp"}
    grid = {}
    for xi in levs:
        for yi in levs:
            cell = xy_df[(xy_df["X_3lev"] == xi) & (xy_df["Y_3lev"] == yi)]
            n = len(cell)
            if n == 0:
                grid[(xi, yi)] = "n=0"
                continue
            mean_dbd = cell["dbd_avg_lift"].mean()
            mean_dd = cell["dd_avg_lift"].mean()
            if mean_dbd is not None and abs(mean_dbd) > 1e-10:
                wald = mean_dd / mean_dbd
                grid[(xi, yi)] = f"{wald:.4f} (n={n})"
            else:
                grid[(xi, yi)] = f"n={n}"

    wald_3x3 = pd.DataFrame(
        index=[labels[i] for i in levs],
        columns=[dd_labels[j] for j in levs],
    )
    for (xi, yi), v in grid.items():
        wald_3x3.loc[labels[xi], dd_labels[yi]] = v
    wald_3x3_path = ANALYSIS_DIR / "wald_3x3.csv"
    wald_3x3.to_csv(wald_3x3_path)
    print(f"Saved: {wald_3x3_path}")

    # --- Single-metric Wald (X = dbd_o2_gmv) ---
    single_rows = []
    for dd_metric in DD_METRICS:
        if dd_metric not in wide_impact.columns:
            continue
        valid = wide_impact[[DBD_X, dd_metric]].dropna(how="any")
        n = len(valid)
        if n < 1:
            continue
        mean_dbd = valid[DBD_X].mean()
        mean_dd = valid[dd_metric].mean()
        wald = (mean_dd / mean_dbd) if mean_dbd is not None and abs(mean_dbd) > 1e-10 else None
        single_rows.append({
            "dd_metric": dd_metric,
            "n_experiments": n,
            "mean_dbd_o2_gmv_lift_pct": round(mean_dbd * 100, 4) if mean_dbd is not None else None,
            "mean_dd_lift_pct": round(mean_dd * 100, 4) if mean_dd is not None else None,
            "wald": round(wald, 4) if wald is not None else None,
        })
    single_df = pd.DataFrame(single_rows)
    out_single = ANALYSIS_DIR / "wald_single_metric_by_dd_o2_gmv.csv"
    single_df.to_csv(out_single, index=False)
    print(f"Saved: {out_single}")
    # Alias for compatibility
    out_single_alias = ANALYSIS_DIR / "wald_single_metric_by_dd.csv"
    single_df.to_csv(out_single_alias, index=False)
    print(f"Saved: {out_single_alias} (alias)")

    # --- Single-metric Wald (X = dbd_o2_trials_per_cx) ---
    if DBD_X_TRIALS in wide_impact.columns:
        single_trials_rows = []
        for dd_metric in DD_METRICS:
            if dd_metric not in wide_impact.columns:
                continue
            valid = wide_impact[[DBD_X_TRIALS, dd_metric]].dropna(how="any")
            n = len(valid)
            if n < 1:
                continue
            mean_trials = valid[DBD_X_TRIALS].mean()
            mean_dd = valid[dd_metric].mean()
            wald = (mean_dd / mean_trials) if mean_trials is not None and abs(mean_trials) > 1e-10 else None
            single_trials_rows.append({
                "dd_metric": dd_metric,
                "n_experiments": n,
                "mean_trials_lift_pct": round(mean_trials * 100, 4) if mean_trials is not None else None,
                "mean_dd_lift_pct": round(mean_dd * 100, 4) if mean_dd is not None else None,
                "wald": round(wald, 4) if wald is not None else None,
            })
        single_trials_df = pd.DataFrame(single_trials_rows)
        out_trials = ANALYSIS_DIR / "wald_single_metric_by_dd_trials.csv"
        single_trials_df.to_csv(out_trials, index=False)
        print(f"Saved: {out_trials} (X = dbd_o2_trials_per_cx)")
    else:
        print(f"'{DBD_X_TRIALS}' not in exports; skipping single-metric Wald by trials.")

    # --- Mean comparison by metric (DbD + DD) ---
    dbd_metrics = [DBD_X, "dbd_order_rate"]
    mean_rows = []
    for metric in dbd_metrics:
        if metric not in wide_impact.columns:
            continue
        vals = wide_impact[metric].dropna()
        mean_rows.append({
            "metric": metric,
            "type": "DbD",
            "n": len(vals),
            "mean_lift_pct": round(vals.mean() * 100, 4) if len(vals) else None,
        })
    for metric in DD_METRICS:
        if metric not in wide_impact.columns:
            continue
        vals = wide_impact[metric].dropna()
        mean_rows.append({
            "metric": metric,
            "type": "DD",
            "n": len(vals),
            "mean_lift_pct": round(vals.mean() * 100, 4) if len(vals) else None,
        })
    mean_df = pd.DataFrame(mean_rows)
    mean_path = ANALYSIS_DIR / "mean_comparison_by_metric.csv"
    mean_df.to_csv(mean_path, index=False)
    print(f"Saved: {mean_path}")

    print("Done. Primary X = dbd_o2_gmv.")


if __name__ == "__main__":
    run()
