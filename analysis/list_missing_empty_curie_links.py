"""
List experiments with no CSV file or CSV that loads empty (for re-download from Curie).
Output: analysis/missing_or_empty_curie_links.csv
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
from mean_comparison_wald import _resolve_csv_path, load_experiment_metrics

EXPERIMENTS_CSV = REPO_ROOT / "experiments" / "experiment_list.csv"
RESULTS_DIR = REPO_ROOT / "experiment-results"
OUT_CSV = REPO_ROOT / "analysis" / "missing_or_empty_curie_links.csv"


def main():
    exp = pd.read_csv(EXPERIMENTS_CSV)
    exp = exp[exp["analysis_name"].notna() & (exp["analysis_name"].astype(str).str.strip() != "")]

    no_csv = []
    empty_load = []

    for _, row in exp.iterrows():
        aname = str(row["analysis_name"]).strip()
        path = _resolve_csv_path(aname)
        curie = row.get("curie_link", "")
        name = row.get("name", aname)
        if path is None:
            no_csv.append({"reason": "no_csv", "name": name, "analysis_name": aname, "curie_link": curie})
            continue
        df = load_experiment_metrics(path)
        if df.empty:
            empty_load.append({"reason": "empty_load", "name": name, "analysis_name": aname, "curie_link": curie})

    out = pd.DataFrame(no_csv + empty_load)
    out.to_csv(OUT_CSV, index=False)
    print(f"no_csv: {len(no_csv)}, empty_load: {len(empty_load)}")
    print(f"Saved: {OUT_CSV}")
    return out


if __name__ == "__main__":
    main()
