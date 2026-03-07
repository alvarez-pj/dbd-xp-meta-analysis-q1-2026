"""
Reference list of DD (DoorDash core) metrics for the meta-analysis.
Used by mean_comparison_wald.py for inclusion logic, mean comparison, and Wald tables.
Includes all o1_ prefix metrics (ex-DbD) and active_share.
"""

DD_METRICS = [
    "consumers_mau",
    "dsmp_gov",
    # O1 order rate (ex-DbD)
    "o1_order_rate",
    "o1_order_rate_7d",
    "o1_order_rate_14d",
    "o1_order_rate_28d",
    # O1 value metrics (DoorDash Check)
    "o1_subtotal",
    "o1_aov",
    "o1_gmv",
    "o1_vp",
    "o1_vp_per_cx",
    # Active share (company pMAU guardrail)
    "active_share",
    "active_share_7d",
    "consumer_order_frequency_l_28_d",
    "consumers_order_frequency_l_28_d",
]
