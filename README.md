# DoubleDash (DbD) Experiment Meta-Analysis

### Owner: Pedro Alvarez
### Created: Feb 27, 2026
---
## Purpose
Repository for collecting and analyzing past DoubleDash experiments to evaluate the relationship between DbD adoption and core DD outcomes. Part of a broader Q1 '26 initiative evaluating the incrementality of Doubledash to Doordash in general. Complementary to ongoing profitability work. [link to analysis doc for more context](https://docs.google.com/document/d/1rxrIHvbbD_usz8y1Hzg22hzbhbQsR186QzhdjWYwvnw/edit?tab=t.0#heading=h.76o6sxd7nfi)

We use the resources in this repo to specifically:

- **Collect data** experiment list, product briefs/readouts, and metric definitions in one place.
- **Analyze** whether DbD gains are associated with non-DbD order rate and other core outcomes across experiments.
- **Inform** our evaluation of net incrementality through a robust, recursive meta-analysis of experiment results. 

---

## Repo Structure

```
.
├── README.md                 # This file
├── experiments/              # Experiment list (name, launch date, surface, and links to prd/briefs/readouts/curies)
│   └── experiment_list.csv   # Master list of DbD launches (see template below)
├── metric_reference/              # Metric definitions and P0/core sets
│   └── dbd-metric-reference.csv # Pulled over from DbD semantic layer; a list  of key DbD /DD core metrics. 
└── experiment-results/                 # CSV exports of curie results for each of the 61 experiments selected
    └── .gitkeep
```

---

## 1. Experiment List

**File:** `experiments/experiment_list.csv`

One row per DbD-focused launch. Add columns as needed; minimum suggested:

| Column | Description |
|--------|-------------|
| `name` | Short name (e.g. "PCO ranker v6", "DbD entry placement") |
| `launch_date` | Ship date (YYYY-MM-DD) |
| `analysis_name` | field to be used to map to the corresponding CSV in the experiment-results folder |
| `surface` | PCO, PCC, Both|
| `prd/brief/context` | Link(s) to PRD or product brief|
| `readout` | Link or path to readout for initiatives that have one ( blank if none) |
| `curie_link` | Link to curie analysis used for CSV generation |

---

## 2. Metric Reference

**File:** `metric_reference/dbd-metric-reference.csv`

This file, created by the DbD Ax team for their semantic layer, ensures the consistet, sanctioned metric-level interpretation is executed across experiments. 

---

## 3. Analysis

**Directory:** `experiment-results/`

 **Metric result CSVs** — Store experiment metric results here as CSVs (do not rely on warehoused Curie metric tables in Snowflake). This ensures fidelity: snowflake-native Curie tables do not have perfect vintage/alignment with final readout results.
- **Matching** — Link to the experiment list by experiment name (same `analysis_name` as in `experiments/experiment_list.csv`).

---

## How to Use

Data Ingestion is a 3 step process:

1. **Add experiments** — Append rows to `experiments/experiment_list.csv` for each DbD launch in scope (e.g. last X quarters/years). Put PRD/brief and readout links in the `prd/brief` and `readout` columns.
2. **Maintain metric sets** — Update `metric_sets/dbd_metric_reference.csv` when P0 or core metrics change.
3. **Run comparative analysis** — Use `analysis/` to produce evidence for “DbD ↔ core” comparisons

--
