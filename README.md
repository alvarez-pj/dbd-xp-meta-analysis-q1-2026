# DoubleDash (DbD) Experiment Meta-Analysis

### Owner: Pedro Alvarez
### Created: Feb 27, 2026
---
## Purpose
Repository for collecting and analyzing past DoubleDash experiments to evaluate the relationship between DbD adoption and core DD outcomes. Part of a broader Q1 '26 initiative evaluating the incrementality of Doubledash to Doordash in general. Complementary to ongoing profitability work. [link to analysis doc for more context](https://docs.google.com/document/d/1rxrIHvbbD_usz8y1Hzg22hzbhbQsR186QzhdjWYwvnw/edit?tab=t.0#heading=h.76o6sxd7nfi)

We use the resources in this repo to specifically:

- **Collect data** experiment list, product briefs/readouts, and metric definitions in one place.
- **Analyze** whether DbD gains are associated with non-DbD order rate and other core outcomes across experiments.

---

## Repo Structure

```
.
├── README.md                 # This file
├── experiments/              # Experiment list (briefs & readouts linked in CSV)
│   └── experiment_list.csv   # Master list of DbD launches (see template below)
├── metric_sets/              # Metric definitions and P0/core sets
│   └── metric_definitions.md # DbD P0 vs core/DoorDash metrics
└── analysis/                 # Scripts and outputs for comparative analysis
    └── .gitkeep
```

---

## 1. Experiment List

**File:** `experiments/experiment_list.csv`

One row per DbD-focused launch. Add columns as needed; minimum suggested:

| Column | Description |
|--------|-------------|
| `experiment_id` | Internal or platform experiment ID |
| `name` | Short name (e.g. "PCO ranker v6", "DbD entry placement") |
| `launch_date` | Ship date (YYYY-MM-DD) |
| `surface` | PCO, PCC|
| `primary_focus` | Brief description of what was tested |
| `dbd_primary_metric` | Main DbD metric (e.g. DbD attach rate, DbD orders) |
| `core_metrics_measured` | Y/N or list: were core/ halo metrics in the test? |
| `prd/brief` | Link(s) to PRD or product brief (single field; comma-separate if multiple) |
| `readout` | Link or path to readout for initiatives that have one (leave blank if none) |
| `notes` | Power for halo, caveats, link to dashboard |

Starter CSV header (copy to `experiments/experiment_list.csv`):

```csv
experiment_id,name,launch_date,surface,primary_focus,dbd_primary_metric,core_metrics_measured,prd/brief,readout,notes
```

Keep experiments in reverse chronological order (newest first). Briefs and readouts are linked only via the `prd/brief` and `readout` columns (URLs or paths to docs elsewhere); nothing is stored in this repo.

---

## 2. Metric Reference

**File:** `metric_sets/dbd_metric_reference.csv`

This file, created by the DbD Ax team for their semantic layer, ensures the consistet, sanctioned metric-level interpretation is executed across experiments. 

---

## 3. Analysis

**Directory:** `analysis/`

 **Metric result CSVs** — Store experiment metric results here as CSVs (do not rely on warehoused Curie metric tables in Snowflake). This ensures fidelity: snowflake-native Curie tables do not have perfect vintage/alignment with final readout results.
- **Matching** — Link to the experiment list by experiment name (same `name` as in `experiments/experiment_list.csv`).
- **Scripts** — Cross-experiment analysis (e.g. correlation of DbD lift vs core lift, ITT on core outcomes, power audit) reads from these CSVs.
- **Outputs** — Tables, plots, and a short summary of findings (indisputable vs unclear → Phase 2).

---

## How to Use

Data Ingestion is a 3 step process:

1. **Add experiments** — Append rows to `experiments/experiment_list.csv` for each DbD launch in scope (e.g. last X quarters/years). Put PRD/brief and readout links in the `prd/brief` and `readout` columns.
2. **Maintain metric sets** — Update `metric_sets/dbd_metric_reference.csv` when P0 or core metrics change.
3. **Run comparative analysis** — Use `analysis/` to produce evidence for “DbD ↔ core” and the go/no-go for a holdout.

--
