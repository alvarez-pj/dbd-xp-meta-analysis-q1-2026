# DbD vs DD metrics (meta-analysis)

## DbD / input metrics (X)
- **dbd_o2_gmv** — Primary X. Total topline GMV from DoubleDash (O2) orders. Ground truth for "did DbD move?"
- **dbd_order_rate** — Secondary DbD metric (orders per customer per day for O2). Used in mean_comparison_by_metric only.

## DD core / output metrics (Y)
DoorDash-level guardrails and outcomes (ex-DbD or platform-wide). Used as Y in 3x3 and single-metric Wald.

- **consumers_mau** — pMAU (unique customers with ≥1 order in month). DoorDash Check.
- **dsmp_gov** — GOV (discovery/search/merch/personalization). DoorDash Check.
- **o1_order_rate**, **o1_order_rate_7d**, **o1_order_rate_14d**, **o1_order_rate_28d** — Primary (O1) order rate only; ex-DbD.
- **o1_subtotal**, **o1_aov**, **o1_gmv**, **o1_vp**, **o1_vp_per_cx** — O1 value metrics (DoorDash Check).
- **active_share**, **active_share_7d** — Company pMAU guardrail (% visitors ordering O1 or O2).
- **consumer_order_frequency_l_28_d**, **consumers_order_frequency_l_28_d** — Orders per consumer L28d (alias).
