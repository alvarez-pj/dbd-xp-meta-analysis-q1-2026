"""
Dedupe experiment-results: for each test (analysis_name), keep only the most recent
CSV (by file modification time) and move older duplicates to a backup folder.
Run after re-uploading files in batches so only one file per test remains.

Usage:
  cd analysis && python dedupe_experiment_results.py [--dry-run]
"""
import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "experiment-results"
BACKUP_DIR = RESULTS_DIR / "_deduped_removed"


def stem_to_analysis_name(stem: str) -> str:
    """'name (2)' -> 'name'; 'name' -> 'name'."""
    if " (" in stem and re.search(r"\s*\(\d+\)\s*$", stem):
        return re.sub(r"\s*\(\d+\)\s*$", "", stem).strip()
    return stem.strip()


def main():
    ap = argparse.ArgumentParser(description="Dedupe experiment-results by keeping only most recent file per test.")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be moved, do not move files.")
    args = ap.parse_args()

    if not RESULTS_DIR.exists():
        print(f"Results dir not found: {RESULTS_DIR}")
        return

    # Group each CSV by analysis_name (normalized stem)
    by_analysis: dict[str, list[Path]] = {}
    for p in sorted(RESULTS_DIR.glob("*.csv")):
        if p.name.startswith("_"):
            continue
        aname = stem_to_analysis_name(p.stem)
        by_analysis.setdefault(aname, []).append(p)

    # Find tests with more than one file
    duplicates = {k: v for k, v in by_analysis.items() if len(v) > 1}
    if not duplicates:
        print("No duplicate files found (each test has at most one CSV).")
        return

    if not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    moved = 0
    for aname, paths in sorted(duplicates.items()):
        # Sort by modification time, newest first; keep first, move rest
        paths_sorted = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        keep, to_remove = paths_sorted[0], paths_sorted[1:]
        print(f"\n{aname}: keep {keep.name} (newest), remove {len(to_remove)} older")
        for p in to_remove:
            print(f"  -> {p.name}")
            if not args.dry_run:
                dest = BACKUP_DIR / p.name
                if dest.exists():
                    dest.unlink()
                shutil.move(str(p), str(dest))
                moved += 1

    if args.dry_run:
        print(f"\n[DRY RUN] Would move {sum(len(v)-1 for v in duplicates.values())} file(s). Run without --dry-run to apply.")
    else:
        print(f"\nMoved {moved} duplicate file(s) to {BACKUP_DIR}")


if __name__ == "__main__":
    main()
