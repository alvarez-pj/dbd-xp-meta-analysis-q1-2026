"""
Scatter plots: dbd_o2_gmv (x) vs selected DD metrics (y) with error bars.
Produces both zoomed (fixed axes) and un-zoomed (data-driven axes) versions.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_CSV = REPO_ROOT / "experiments" / "experiment_list.csv"
RESULTS_DIR = REPO_ROOT / "experiment-results"
DBD_X = "dbd_o2_gmv"

# (dd_metric, (xlim), (ylim)) — x/y in %
ZOOMED_METRICS = [
    ("o1_gmv", (-0.1, 2), (-0.5, 0.5)),
    ("o1_vp_per_cx", (-0.1, 2), (-0.5, 0.5)),
    ("consumers_mau", (-0.1, 2), (-0.5, 0.5)),
    ("o1_order_rate_7d", (-0.1, 2), (-0.5, 0.5)),
]

# Plain-English labels for axes and titles
DISPLAY_NAMES = {
    "consumers_mau": "O1 MAU",
    "o1_order_rate_7d": "7 Day O1 Order Rate",
    "o1_vp_per_cx": "O1 Variable Profit",
    "o1_gmv": "Total O1 GMV",
}


def _parse_num(s):
    if pd.isna(s) or s in ("-", "", "N/A"):
        return None
    try:
        return float(str(s).strip().replace(",", ""))
    except ValueError:
        return None


def _parse_ci(ci_str):
    if pd.isna(ci_str) or not isinstance(ci_str, str) or "[" not in ci_str:
        return None, None
    parts = re.findall(r"([+-]?\d*\.?\d+)\s*%?", str(ci_str))
    if len(parts) >= 2:
        try:
            return float(parts[0]) / 100.0, float(parts[1]) / 100.0
        except ValueError:
            pass
    return None, None


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
    ci_cols = [c for c in cols if prefix in c and "Relative Impact" in c and "Confidence" in c]
    ci_col = ci_cols[0] if ci_cols else None
    out = df[["Metric Name"]].copy()
    out["relative_impact"] = df[rel_col].map(_parse_num)
    out["p_value"] = df[p_col].map(_parse_num) if p_col else None
    if ci_col and ci_col in df.columns:
        parsed = df[ci_col].map(_parse_ci)
        out["rel_impact_lower"] = parsed.map(lambda x: x[0] if x and x[0] is not None else None)
        out["rel_impact_upper"] = parsed.map(lambda x: x[1] if x and x[1] is not None else None)
    else:
        out["rel_impact_lower"] = None
        out["rel_impact_upper"] = None
    return out


def load_merged():
    exp_list = pd.read_csv(EXPERIMENTS_CSV)
    with_aname = exp_list[
        exp_list["analysis_name"].notna()
        & (exp_list["analysis_name"].astype(str).str.strip() != "")
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


def main():
    if plt is None:
        print("matplotlib not installed; pip install matplotlib")
        return

    merged = load_merged()
    if merged.empty:
        print("No experiment data loaded.")
        return

    wide = merged.pivot_table(index="analysis_name", columns="Metric Name", values="relative_impact")
    wide_p = merged.pivot_table(index="analysis_name", columns="Metric Name", values="p_value")
    has_ci = "rel_impact_lower" in merged.columns and merged["rel_impact_lower"].notna().any()
    if has_ci:
        wide_lo = merged.pivot_table(index="analysis_name", columns="Metric Name", values="rel_impact_lower")
        wide_hi = merged.pivot_table(index="analysis_name", columns="Metric Name", values="rel_impact_upper")
    else:
        wide_lo = wide_hi = None

    if DBD_X not in wide.columns:
        print(f"'{DBD_X}' not found in any export.")
        return

    out_dir = REPO_ROOT / "analysis" / "scatter_plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    P_SIG = 0.05

    for dd_metric, xlim, ylim in ZOOMED_METRICS:
        if dd_metric not in wide.columns:
            print(f"Skipping {dd_metric}: not in exports.")
            continue
        data = wide[[DBD_X, dd_metric]].dropna()
        if len(data) < 1:
            print(f"Skipping {dd_metric}: no overlapping data.")
            continue

        display_name = DISPLAY_NAMES.get(dd_metric, dd_metric)
        x = data[DBD_X].values * 100
        y = data[dd_metric].values * 100

        # Wald for this metric (mean DD lift / mean DbD lift)
        mean_dbd = data[DBD_X].mean()
        mean_dd = data[dd_metric].mean()
        wald = (mean_dd / mean_dbd) if mean_dbd is not None and abs(mean_dbd) > 1e-10 else None
        wald_str = f", Wald={wald:.4f}" if wald is not None else ""

        # Points within zoom window
        in_view = (x >= xlim[0]) & (x <= xlim[1]) & (y >= ylim[0]) & (y <= ylim[1])
        n_in_view = int(in_view.sum())

        # Format by stat sig: both dbd_o2_gmv and dd_metric p < P_SIG -> bold (thick edge); else light/transparent
        COLOR_BOLD_GREEN = "#2E8B57"   # sea green
        COLOR_LIGHT_GREEN = "#90EE90"
        COLOR_BOLD_RED = "#CD5C5C"     # indian red
        COLOR_LIGHT_RED = "#FFB6C1"
        colors = []
        alphas = []
        linewidths = []
        for i, aname in enumerate(data.index):
            p_dbd = wide_p.loc[aname, DBD_X] if aname in wide_p.index and DBD_X in wide_p.columns else np.nan
            p_dd = wide_p.loc[aname, dd_metric] if aname in wide_p.index and dd_metric in wide_p.columns else np.nan
            both_sig = (
                pd.notna(p_dbd) and p_dbd < P_SIG
                and pd.notna(p_dd) and p_dd < P_SIG
            )
            if y[i] > 0:
                colors.append(COLOR_BOLD_GREEN if both_sig else COLOR_LIGHT_GREEN)
                alphas.append(1.0 if both_sig else 0.45)
            elif y[i] < 0:
                colors.append(COLOR_BOLD_RED if both_sig else COLOR_LIGHT_RED)
                alphas.append(1.0 if both_sig else 0.45)
            else:
                colors.append("gray")
                alphas.append(0.7)
            linewidths.append(1.5 if both_sig else 0.5)

        fig, ax = plt.subplots(figsize=(6, 5))
        n_pt = len(data)

        if has_ci and wide_lo is not None and wide_hi is not None:
            xerr_lo = np.full(n_pt, np.nan)
            xerr_hi = np.full(n_pt, np.nan)
            yerr_lo = np.full(n_pt, np.nan)
            yerr_hi = np.full(n_pt, np.nan)
            for i, (aname, row) in enumerate(data.iterrows()):
                xv, yv = row[DBD_X] * 100, row[dd_metric] * 100
                x_lo = wide_lo.loc[aname, DBD_X] * 100 if aname in wide_lo.index and DBD_X in wide_lo.columns and pd.notna(wide_lo.loc[aname, DBD_X]) else np.nan
                x_hi = wide_hi.loc[aname, DBD_X] * 100 if aname in wide_hi.index and DBD_X in wide_hi.columns and pd.notna(wide_hi.loc[aname, DBD_X]) else np.nan
                y_lo = wide_lo.loc[aname, dd_metric] * 100 if aname in wide_lo.index and dd_metric in wide_lo.columns and pd.notna(wide_lo.loc[aname, dd_metric]) else np.nan
                y_hi = wide_hi.loc[aname, dd_metric] * 100 if aname in wide_hi.index and dd_metric in wide_hi.columns and pd.notna(wide_hi.loc[aname, dd_metric]) else np.nan
                if np.isfinite(x_lo):
                    xerr_lo[i] = xv - x_lo
                if np.isfinite(x_hi):
                    xerr_hi[i] = x_hi - xv
                if np.isfinite(y_lo):
                    yerr_lo[i] = yv - y_lo
                if np.isfinite(y_hi):
                    yerr_hi[i] = y_hi - yv
            xerr = np.array([np.where(np.isfinite(xerr_lo), xerr_lo, 0), np.where(np.isfinite(xerr_hi), xerr_hi, 0)])
            yerr = np.array([np.where(np.isfinite(yerr_lo), yerr_lo, 0), np.where(np.isfinite(yerr_hi), yerr_hi, 0)])
            has_any = np.any(np.isfinite(xerr_lo)) or np.any(np.isfinite(xerr_hi)) or np.any(np.isfinite(yerr_lo)) or np.any(np.isfinite(yerr_hi))
            if has_any:
                ax.errorbar(
                    x, y, xerr=xerr, yerr=yerr, fmt="none",
                    ecolor="gray", capsize=2, capthick=0.8, alpha=0.35,
                )

        ax.scatter(x, y, c=colors, alpha=alphas, edgecolors="k", linewidths=linewidths, zorder=5)
        ax.axhline(0, color="black", linestyle="-", linewidth=2.5)
        ax.axvline(0, color="black", linestyle="-", linewidth=2.5)
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        ax.set_xlim(xlim[0], xlim[1])
        ax.set_ylim(ylim[0], ylim[1])
        ax.set_xlabel(f"{DBD_X} relative impact (%)", fontweight="bold")
        ax.set_ylabel(f"{display_name} relative impact (%)", fontweight="bold")
        ax.set_title(f"{display_name} (zoomed, n={len(data)} total, {n_in_view} in view{wald_str})")
        ax.grid(True, alpha=0.3)
        # Interpretation guide
        guide = (
            "Green: DD metric ↑  |  Red: DD metric ↓\n"
            "Bold border: both DbD O2 GMV and this metric stat sig (p<0.05).  "
            "Light fill: one or both not stat sig."
        )
        ax.text(0.02, 0.02, guide, transform=ax.transAxes, fontsize=7, verticalalignment="bottom",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.85))

        safe_name = dd_metric.replace("/", "_")
        out_path = out_dir / f"dbd_o2_gmv_vs_{safe_name}_zoomed.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved: {out_path}")

        # Un-zoomed: data-driven limits with margin
        x_min, x_max = np.nanmin(x), np.nanmax(x)
        y_min, y_max = np.nanmin(y), np.nanmax(y)
        x_margin = max(0.1, (x_max - x_min) * 0.1) if x_max > x_min else 0.2
        y_margin = max(0.05, (y_max - y_min) * 0.1) if y_max > y_min else 0.1
        xlim_u = (x_min - x_margin, x_max + x_margin)
        ylim_u = (y_min - y_margin, y_max + y_margin)
        fig2, ax2 = plt.subplots(figsize=(6, 5))
        n_pt = len(data)
        if has_ci and wide_lo is not None and wide_hi is not None:
            xerr_lo = np.full(n_pt, np.nan)
            xerr_hi = np.full(n_pt, np.nan)
            yerr_lo = np.full(n_pt, np.nan)
            yerr_hi = np.full(n_pt, np.nan)
            for i, (aname, row) in enumerate(data.iterrows()):
                xv, yv = row[DBD_X] * 100, row[dd_metric] * 100
                x_lo = wide_lo.loc[aname, DBD_X] * 100 if aname in wide_lo.index and DBD_X in wide_lo.columns and pd.notna(wide_lo.loc[aname, DBD_X]) else np.nan
                x_hi = wide_hi.loc[aname, DBD_X] * 100 if aname in wide_hi.index and DBD_X in wide_hi.columns and pd.notna(wide_hi.loc[aname, DBD_X]) else np.nan
                y_lo = wide_lo.loc[aname, dd_metric] * 100 if aname in wide_lo.index and dd_metric in wide_lo.columns and pd.notna(wide_lo.loc[aname, dd_metric]) else np.nan
                y_hi = wide_hi.loc[aname, dd_metric] * 100 if aname in wide_hi.index and dd_metric in wide_hi.columns and pd.notna(wide_hi.loc[aname, dd_metric]) else np.nan
                if np.isfinite(x_lo):
                    xerr_lo[i] = xv - x_lo
                if np.isfinite(x_hi):
                    xerr_hi[i] = x_hi - xv
                if np.isfinite(y_lo):
                    yerr_lo[i] = yv - y_lo
                if np.isfinite(y_hi):
                    yerr_hi[i] = y_hi - yv
            xerr = np.array([np.where(np.isfinite(xerr_lo), xerr_lo, 0), np.where(np.isfinite(xerr_hi), xerr_hi, 0)])
            yerr = np.array([np.where(np.isfinite(yerr_lo), yerr_lo, 0), np.where(np.isfinite(yerr_hi), yerr_hi, 0)])
            has_any = np.any(np.isfinite(xerr_lo)) or np.any(np.isfinite(xerr_hi)) or np.any(np.isfinite(yerr_lo)) or np.any(np.isfinite(yerr_hi))
            if has_any:
                ax2.errorbar(x, y, xerr=xerr, yerr=yerr, fmt="none", ecolor="gray", capsize=2, capthick=0.8, alpha=0.35)
        ax2.scatter(x, y, c=colors, alpha=alphas, edgecolors="k", linewidths=linewidths, zorder=5)
        ax2.axhline(0, color="black", linestyle="-", linewidth=2.5)
        ax2.axvline(0, color="black", linestyle="-", linewidth=2.5)
        for spine in ax2.spines.values():
            spine.set_linewidth(1.5)
        ax2.set_xlim(xlim_u[0], xlim_u[1])
        ax2.set_ylim(ylim_u[0], ylim_u[1])
        ax2.set_xlabel(f"{DBD_X} relative impact (%)", fontweight="bold")
        ax2.set_ylabel(f"{display_name} relative impact (%)", fontweight="bold")
        ax2.set_title(f"{display_name} (n={len(data)}{wald_str})")
        ax2.grid(True, alpha=0.3)
        ax2.text(0.02, 0.02, guide, transform=ax2.transAxes, fontsize=7, verticalalignment="bottom",
                 bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.85))
        out_path_u = out_dir / f"dbd_o2_gmv_vs_{safe_name}.png"
        fig2.savefig(out_path_u, dpi=150, bbox_inches="tight")
        plt.close(fig2)
        print(f"Saved: {out_path_u}")

    print(f"Done. Zoomed + un-zoomed plots in {out_dir}/")


if __name__ == "__main__":
    main()
