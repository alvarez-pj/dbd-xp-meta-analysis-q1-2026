"""
DbD vs DD mean comparison + Wald estimator (deltaY/deltaX).

Definitions:
- X (DbD) and Y (DD) = -1 (degrading), 0 (flat), 1 (improving) using p < 0.25 for directional.
- Include experiment if ANY P0 DbD metric present AND ANY P0 DD metric present; flag missing metrics.
- 3x3 (X x Y): counts and Wald per cell (mean DD lift / mean DbD lift in that cell).

Note: Valid CIs for Wald typically need covariance or individual-level data; summary data may not suffice.
"""

from pathlib import Path
import re
from typing import Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_CSV = REPO_ROOT / "experiments" / "experiment_list.csv"
RESULTS_DIR = REPO_ROOT / "experiment-results"

# Metric sets (include common Curie name variants)
DBD_METRICS = [
    "dbd_order_rate",
    "dbd_o2_gmv",
    "dbd_attach_rate_post_checkout",
    "dbd_attach_rate_pre_checkout",
    "dbd_attach_rate_pre_and_post",
]
DD_METRICS = [
    "consumers_mau",
    "dsmp_order_rate",
    "dsmp_order_rate_7d",
    "dsmp_order_rate_14d",
    "dsmp_order_rate_28d",
    "dsmp_gov",
    "order_rate_per_entity",
    "order_rate_per_entity_7d",
    "order_rate_per_entity_14d",
    "order_rate_per_entity_28d",
]
DIRECTIONAL_P = 0.25


def _parse_num(s):
    if pd.isna(s) or s in ("-", "", "N/A"):
        return None
    s = str(s).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _find_treatment_impact_columns(df: pd.DataFrame):
    """Find first treatment-arm 'Relative Impact' and matching 'P Value' column. Handles various Curie export formats."""
    cols = [c for c in df.columns if isinstance(c, str)]
    rel_cols = [c for c in cols if "Relative Impact" in c and "Confidence" not in c]
    if not rel_cols:
        return None, None
    rel_col = rel_cols[0]
    # Match prefix (e.g. "treatment M1" or "treatment M1-treatment_1") to find P Value
    prefix = rel_col.replace(" Relative Impact", "").strip()
    p_cols = [c for c in cols if prefix in c and "P Value" in c and "Confidence" not in c]
    p_col = p_cols[0] if p_cols else None
    return rel_col, p_col


def load_experiment_metrics(csv_path: Path) -> pd.DataFrame:
    """Load one result CSV; return rows with Metric Name, relative_impact (decimal), p_value."""
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return pd.DataFrame(columns=["Metric Name", "relative_impact", "p_value"])
    if "Metric Name" not in df.columns:
        return pd.DataFrame(columns=["Metric Name", "relative_impact", "p_value"])
    rel_col, p_col = _find_treatment_impact_columns(df)
    if rel_col is None:
        return pd.DataFrame(columns=["Metric Name", "relative_impact", "p_value"])
    out = df[["Metric Name"]].copy()
    out["relative_impact"] = df[rel_col].map(_parse_num)
    out["p_value"] = df[p_col].map(_parse_num) if p_col else None
    return out


def is_directional_positive(impact: float, p: float) -> bool:
    if impact is None or p is None:
        return False
    return impact > 0 and p < DIRECTIONAL_P


def is_directional_negative(impact: float, p: float) -> bool:
    if impact is None or p is None:
        return False
    return impact < 0 and p < DIRECTIONAL_P


def _classify_spectrum(rows: pd.DataFrame) -> int:
    """Return -1 (degrading), 0 (flat), or 1 (improving) if any P0 metric in rows is directional at p < 0.25."""
    if rows.empty:
        return None
    any_neg = rows.apply(
        lambda r: is_directional_negative(r["relative_impact"], r["p_value"]), axis=1
    ).any()
    any_pos = rows.apply(
        lambda r: is_directional_positive(r["relative_impact"], r["p_value"]), axis=1
    ).any()
    if any_neg:
        return -1
    if any_pos:
        return 1
    return 0


def _resolve_csv_path(analysis_name: str) -> Optional[Path]:
    """Return path to CSV for this analysis_name. Matches exact or 'analysis_name (x).csv' for x = 1,2,3,...; prefers (1) over (2) over exact."""
    exact = RESULTS_DIR / f"{analysis_name}.csv"
    # Prefer numbered variants (re-downloads): (1), (2), (3), ...
    pattern = re.compile(re.escape(analysis_name) + r" \((\d+)\)\.csv$", re.IGNORECASE)
    numbered = []
    for p in RESULTS_DIR.glob("*.csv"):
        if p.name == exact.name:
            continue
        m = pattern.match(p.name)
        if m:
            numbered.append((int(m.group(1)), p))
    numbered.sort(key=lambda x: x[0])
    if numbered:
        return numbered[0][1]
    if exact.exists():
        return exact
    # Case-insensitive fallback
    lower = analysis_name.lower()
    for p in RESULTS_DIR.glob("*.csv"):
        if p.stem.lower() == lower:
            return p
    return None


def _print_diagnostic(total_list, n_with_aname, no_file, empty_load, no_dbd, no_dd, included):
    """Print why experiment count is lower than list count."""
    print("--- Experiment coverage ---")
    print(f"  In experiment_list.csv: {total_list} rows")
    print(f"  With non-empty analysis_name: {n_with_aname}")
    print(f"  No matching CSV file: {len(no_file)}")
    if no_file:
        for name, aname in no_file[:5]:
            print(f"    - {name}: {aname}")
        if len(no_file) > 5:
            print(f"    ... and {len(no_file) - 5} more")
    print(f"  CSV loaded but no 'Relative Impact' column (unrecognized format): {len(empty_load)}")
    if empty_load:
        for a in empty_load[:5]:
            print(f"    - {a}")
        if len(empty_load) > 5:
            print(f"    ... and {len(empty_load) - 5} more")
    print(f"  Has CSV but no P0 DbD metric in export: {len(no_dbd)}")
    print(f"  Has CSV but no P0 DD metric in export: {len(no_dd)}")
    print(f"  Included (>=1 P0 DbD or >=1 P0 DD): {included}")
    print()


def main():
    exp_list = pd.read_csv(EXPERIMENTS_CSV)
    with_aname = exp_list[
        exp_list["analysis_name"].notna()
        & (exp_list["analysis_name"].astype(str).str.strip() != "")
    ]
    total_list = len(exp_list)
    n_with_aname = len(with_aname)

    no_file = []
    empty_load = []
    no_dbd = []
    no_dd = []
    all_metrics = []
    exp_level = []

    for _, row in with_aname.iterrows():
        aname = str(row["analysis_name"]).strip()
        path = _resolve_csv_path(aname)
        if path is None:
            no_file.append((row.get("name", aname), aname))
            continue
        meta = row.to_dict()
        df = load_experiment_metrics(path)
        if df.empty:
            empty_load.append(aname)
            continue
        df["experiment_name"] = row.get("name", aname)
        df["analysis_name"] = aname
        for k, v in meta.items():
            if k not in df.columns:
                df[k] = v
        all_metrics.append(df)

        dbd_rows = df[df["Metric Name"].isin(DBD_METRICS)]
        dd_rows = df[df["Metric Name"].isin(DD_METRICS)]
        # Include if at least one of DbD or DD has data (so we count all experiments with accompanying CSV data)
        if dbd_rows.empty and dd_rows.empty:
            no_dd.append(aname)  # treat as no DD for diagnostic
            continue
        if dbd_rows.empty:
            no_dbd.append(aname)
        if dd_rows.empty:
            no_dd.append(aname)

        X_3lev = _classify_spectrum(dbd_rows) if not dbd_rows.empty else None
        Y_3lev = _classify_spectrum(dd_rows) if not dd_rows.empty else None
        present_dbd = set(dbd_rows["Metric Name"].dropna().unique()) if not dbd_rows.empty else set()
        present_dd = set(dd_rows["Metric Name"].dropna().unique()) if not dd_rows.empty else set()
        missing_dbd = [m for m in DBD_METRICS if m not in present_dbd]
        missing_dd = [m for m in DD_METRICS if m not in present_dd]

        dbd_positive = dbd_rows.apply(
            lambda r: is_directional_positive(r["relative_impact"], r["p_value"]), axis=1
        ).any() if not dbd_rows.empty else False
        dd_positive = dd_rows.apply(
            lambda r: is_directional_positive(r["relative_impact"], r["p_value"]), axis=1
        ).any() if not dd_rows.empty else False
        dbd_impacts = dbd_rows["relative_impact"].dropna() if not dbd_rows.empty else pd.Series(dtype=float)
        dd_impacts = dd_rows["relative_impact"].dropna() if not dd_rows.empty else pd.Series(dtype=float)

        exp_level.append({
            "experiment_name": row.get("name", aname),
            "analysis_name": aname,
            "X_binary": 1 if dbd_positive else 0,
            "Y_binary": 1 if dd_positive else 0,
            "X_3lev": X_3lev,
            "Y_3lev": Y_3lev,
            "dbd_avg_lift": dbd_impacts.mean() if len(dbd_impacts) else None,
            "dd_avg_lift": dd_impacts.mean() if len(dd_impacts) else None,
            "missing_dbd": "|".join(missing_dbd) if missing_dbd else "",
            "missing_dd": "|".join(missing_dd) if missing_dd else "",
        })

    if not all_metrics:
        print("No experiment result CSVs could be loaded.")
        _print_diagnostic(total_list, n_with_aname, no_file, empty_load, no_dbd, no_dd, 0)
        return

    _print_diagnostic(
        total_list, n_with_aname, no_file, empty_load, no_dbd, no_dd, len(exp_level)
    )
    n_both = sum(1 for r in exp_level if r.get("X_3lev") is not None and r.get("Y_3lev") is not None)
    print(f"  With both P0 DbD and P0 DD (in 3x3 / Wald): {n_both}")
    print()

    merged = pd.concat(all_metrics, ignore_index=True)
    exp_df = pd.DataFrame(exp_level)

    # ----- Mean comparison table (key metrics) -----
    key_metrics = DBD_METRICS + DD_METRICS
    key_metrics = list(dict.fromkeys(key_metrics))
    means = []
    for m in key_metrics:
        sub = merged[merged["Metric Name"] == m]["relative_impact"].dropna()
        if len(sub) == 0:
            means.append({"metric": m, "type": "DbD" if m in DBD_METRICS else "DD", "n": 0, "mean_lift_pct": None})
        else:
            mean_dec = sub.mean()
            means.append({
                "metric": m,
                "type": "DbD" if m in DBD_METRICS else "DD",
                "n": len(sub),
                "mean_lift_pct": round(mean_dec * 100, 4),
            })
    mean_table = pd.DataFrame(means)
    print("--- Mean comparison (relative impact, %) ---")
    print(mean_table.to_string(index=False))
    mean_table.to_csv(REPO_ROOT / "analysis" / "mean_comparison_by_metric.csv", index=False)

    # ----- Binary X, Y and Wald = deltaY / deltaX -----
    exp_valid = exp_df[exp_df["X_binary"].notna() & exp_df["Y_binary"].notna()]
    n_exp = len(exp_valid)
    mean_X = exp_valid["X_binary"].mean()
    mean_Y = exp_valid["Y_binary"].mean()
    deltaX_bin = mean_X
    deltaY_bin = mean_Y
    if deltaX_bin > 0:
        wald_binary = deltaY_bin / deltaX_bin
    else:
        wald_binary = None

    print("\n--- Binary X (DbD directional+), Y (DD directional+) ---")
    print(f"Experiments with result data: n = {n_exp}")
    print(f"X = 1 (any DbD metric p<{DIRECTIONAL_P} and positive): mean(X) = {mean_X:.4f}")
    print(f"Y = 1 (any DD metric p<{DIRECTIONAL_P} and positive): mean(Y) = {mean_Y:.4f}")
    print(f"Wald (deltaY/deltaX) = mean(Y)/mean(X) = {wald_binary if wald_binary is not None else 'N/A (deltaX=0)'}")

    # 2x2
    cross = pd.crosstab(exp_valid["X_binary"], exp_valid["Y_binary"], margins=True)
    print("\n2x2 (X vs Y):")
    print(cross)

    # ----- 3x3: X_3lev (-1, 0, 1) x Y_3lev (-1, 0, 1): counts + Wald per cell -----
    exp_3 = exp_df[["X_3lev", "Y_3lev", "dbd_avg_lift", "dd_avg_lift"]].dropna(subset=["X_3lev", "Y_3lev"])
    if len(exp_3) > 0:
        cross_3x3 = pd.crosstab(exp_3["X_3lev"], exp_3["Y_3lev"], margins=True)
        cross_3x3.index = cross_3x3.index.map(lambda x: {-1: "DbD deg", 0: "DbD flat", 1: "DbD imp"}.get(x, x))
        cross_3x3.columns = cross_3x3.columns.map(lambda x: {-1: "DD deg", 0: "DD flat", 1: "DD imp"}.get(x, x))
        print("\n--- 3x3 (X = DbD spectrum, Y = DD spectrum) ---")
        print("Counts:")
        print(cross_3x3)
        wald_grid = []
        for x in (-1, 0, 1):
            row_vals = []
            for y in (-1, 0, 1):
                cell = exp_3[(exp_3["X_3lev"] == x) & (exp_3["Y_3lev"] == y)]
                n = len(cell)
                if n == 0:
                    row_vals.append("")
                    continue
                mx = cell["dbd_avg_lift"].mean()
                my = cell["dd_avg_lift"].mean()
                if mx is not None and abs(mx) > 1e-10:
                    wald = my / mx
                    row_vals.append(f"{wald:.4f} (n={n})")
                else:
                    row_vals.append(f"n={n}")
            wald_grid.append(row_vals)
        wald_df = pd.DataFrame(
            wald_grid,
            index=["DbD deg", "DbD flat", "DbD imp"],
            columns=["DD deg", "DD flat", "DD imp"],
        )
        print("\nWald (deltaY/deltaX) per cell [mean DD lift / mean DbD lift]:")
        print(wald_df)
        wald_df.to_csv(REPO_ROOT / "analysis" / "wald_3x3.csv")
    else:
        print("\n--- 3x3: no experiments with both X_3lev and Y_3lev. ---")

    # ----- Single-metric Wald: for each DD metric, Wald = mean(DD lift) / mean(dbd_order_rate lift) -----
    DBD_X_METRIC = "dbd_order_rate"
    DD_METRICS_FOR_WALD = [m for m in DD_METRICS if m in merged["Metric Name"].values]
    single_metric_rows = []
    for dd_metric in DD_METRICS_FOR_WALD:
        exps_with_dbd = set(
            merged[(merged["Metric Name"] == DBD_X_METRIC) & merged["relative_impact"].notna()]["analysis_name"]
        )
        exps_with_dd = set(
            merged[(merged["Metric Name"] == dd_metric) & merged["relative_impact"].notna()]["analysis_name"]
        )
        exps_both = exps_with_dbd & exps_with_dd
        if len(exps_both) == 0:
            single_metric_rows.append({
                "dd_metric": dd_metric,
                "n_experiments": 0,
                "mean_dbd_order_rate_lift_pct": None,
                "mean_dd_lift_pct": None,
                "wald": None,
            })
            continue
        mean_dbd = merged[
            (merged["analysis_name"].isin(exps_both)) & (merged["Metric Name"] == DBD_X_METRIC)
        ]["relative_impact"].mean()
        mean_dd = merged[
            (merged["analysis_name"].isin(exps_both)) & (merged["Metric Name"] == dd_metric)
        ]["relative_impact"].mean()
        wald = (mean_dd / mean_dbd) if mean_dbd is not None and abs(mean_dbd) > 1e-10 else None
        single_metric_rows.append({
            "dd_metric": dd_metric,
            "n_experiments": len(exps_both),
            "mean_dbd_order_rate_lift_pct": round(mean_dbd * 100, 4) if mean_dbd is not None else None,
            "mean_dd_lift_pct": round(mean_dd * 100, 4) if mean_dd is not None else None,
            "wald": round(wald, 4) if wald is not None else None,
        })
    single_metric_wald = pd.DataFrame(single_metric_rows)
    print("\n--- Single-metric Wald (X = dbd_order_rate, Y = each DD metric) ---")
    print("Per 1% dbd_order_rate lift, DD metric moves (wald × 1%):")
    print(single_metric_wald.to_string(index=False))
    single_metric_wald.to_csv(REPO_ROOT / "analysis" / "wald_single_metric_by_dd.csv", index=False)

    # ----- Single-metric Wald: X = dbd_o2_gmv, Y = each DD metric -----
    DBD_X_O2_GMV = "dbd_o2_gmv"
    single_metric_o2_rows = []
    for dd_metric in DD_METRICS_FOR_WALD:
        exps_with_dbd = set(
            merged[(merged["Metric Name"] == DBD_X_O2_GMV) & merged["relative_impact"].notna()]["analysis_name"]
        )
        exps_with_dd = set(
            merged[(merged["Metric Name"] == dd_metric) & merged["relative_impact"].notna()]["analysis_name"]
        )
        exps_both = exps_with_dbd & exps_with_dd
        if len(exps_both) == 0:
            single_metric_o2_rows.append({
                "dd_metric": dd_metric,
                "n_experiments": 0,
                "mean_dbd_o2_gmv_lift_pct": None,
                "mean_dd_lift_pct": None,
                "wald": None,
            })
            continue
        mean_dbd = merged[
            (merged["analysis_name"].isin(exps_both)) & (merged["Metric Name"] == DBD_X_O2_GMV)
        ]["relative_impact"].mean()
        mean_dd = merged[
            (merged["analysis_name"].isin(exps_both)) & (merged["Metric Name"] == dd_metric)
        ]["relative_impact"].mean()
        wald = (mean_dd / mean_dbd) if mean_dbd is not None and abs(mean_dbd) > 1e-10 else None
        single_metric_o2_rows.append({
            "dd_metric": dd_metric,
            "n_experiments": len(exps_both),
            "mean_dbd_o2_gmv_lift_pct": round(mean_dbd * 100, 4) if mean_dbd is not None else None,
            "mean_dd_lift_pct": round(mean_dd * 100, 4) if mean_dd is not None else None,
            "wald": round(wald, 4) if wald is not None else None,
        })
    single_metric_wald_o2 = pd.DataFrame(single_metric_o2_rows)
    print("\n--- Single-metric Wald (X = dbd_o2_gmv, Y = each DD metric) ---")
    print("Per 1% dbd_o2_gmv lift, DD metric moves (wald × 1%):")
    print(single_metric_wald_o2.to_string(index=False))
    single_metric_wald_o2.to_csv(REPO_ROOT / "analysis" / "wald_single_metric_by_dd_o2_gmv.csv", index=False)

    # ----- Missing-metric flags -----
    if "missing_dbd" in exp_df.columns and "missing_dd" in exp_df.columns:
        print("\n--- Missing P0 metrics (experiments included if any DbD + any DD present) ---")
        for col, label in [("missing_dbd", "DbD"), ("missing_dd", "DD")]:
            nonempty = exp_df[exp_df[col].astype(str).str.len() > 0]
            if len(nonempty) > 0:
                # Count how many experiments miss each metric
                all_missing = exp_df[col].dropna().str.split("|").explode()
                vc = all_missing[all_missing != ""].value_counts()
                if len(vc) > 0:
                    print(f"  {label} metrics missing (count of experiments): {vc.to_dict()}")
        exp_df.to_csv(REPO_ROOT / "analysis" / "experiment_level_xy.csv", index=False)
    else:
        exp_df.to_csv(REPO_ROOT / "analysis" / "experiment_level_xy.csv", index=False)

    # ----- Continuous Wald: deltaY/deltaX using avg lifts per experiment -----
    exp_cont = exp_df[exp_df["dbd_avg_lift"].notna() & exp_df["dd_avg_lift"].notna()]
    if len(exp_cont) > 0:
        deltaX_cont = exp_cont["dbd_avg_lift"].mean()
        deltaY_cont = exp_cont["dd_avg_lift"].mean()
        if abs(deltaX_cont) > 1e-10:
            wald_continuous = deltaY_cont / deltaX_cont
        else:
            wald_continuous = None
        print("\n--- Continuous Wald (avg relative impact per experiment) ---")
        print(f"Experiments with both DbD and DD lifts: n = {len(exp_cont)}")
        print(f"deltaX (mean of experiment-level avg DbD lift): {deltaX_cont:.6f} ({deltaX_cont*100:.4f}%)")
        print(f"deltaY (mean of experiment-level avg DD lift):  {deltaY_cont:.6f} ({deltaY_cont*100:.4f}%)")
        print(f"Wald = deltaY/deltaX = {wald_continuous if wald_continuous is not None else 'N/A'}")
    else:
        wald_continuous = None
        print("\n--- Continuous Wald: no experiments with both DbD and DD lifts. ---")

    # ----- CI note -----
    print("\n--- CIs for Wald ---")
    print(
        "Valid CIs for the Wald estimator typically require Cov(X,Y) or individual-level data; "
        "with summary data we only have marginal means. Delta method or bootstrap over experiments "
        "could give approximate CIs if we store per-experiment (X,Y) or (deltaX_i, deltaY_i)."

    )

    # Save exp-level for inspection (includes missing_dbd, missing_dd, X_3lev, Y_3lev)
    # (saved above in missing-metrics block)
    print(f"\nSaved: analysis/mean_comparison_by_metric.csv, analysis/experiment_level_xy.csv, analysis/wald_3x3.csv, analysis/wald_single_metric_by_dd.csv, analysis/wald_single_metric_by_dd_o2_gmv.csv")


if __name__ == "__main__":
    main()
