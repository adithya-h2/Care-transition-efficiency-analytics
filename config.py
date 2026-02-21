"""
Configuration for Care Transition Efficiency & Placement Outcome Analytics.
All column names and thresholds live here — no hardcoding in logic modules.
"""

import os

# --- Data file ---
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "Data", "HHS_Unaccompanied_Alien_Children_Program.csv"
)

# --- Raw CSV column names (exact as in file) ---
COL_DATE = "Date"
COL_INTAKE = "Children apprehended and placed in CBP custody*"
COL_CBP_LOAD = "Children in CBP custody"
COL_TRANSFERS = "Children transferred out of CBP custody"
COL_HHS_LOAD = "Children in HHS Care"
COL_DISCHARGES = "Children discharged from HHS Care"

# --- Derived metric column names (used in metrics.py and downstream) ---
COL_TRANSFER_EFFICIENCY = "transfer_efficiency"
COL_DISCHARGE_EFFECTIVENESS = "discharge_effectiveness"
COL_THROUGHPUT = "throughput"
COL_CBP_BACKLOG_CHANGE = "cbp_backlog_change"
COL_HHS_BACKLOG_CHANGE = "hhs_backlog_change"
COL_CUM_CBP_BACKLOG = "cumulative_cbp_backlog"
COL_CUM_HHS_BACKLOG = "cumulative_hhs_backlog"

# Rolling and stability
COL_TRANSFER_EFF_7D = "transfer_efficiency_7d"
COL_DISCHARGE_EFF_7D = "discharge_effectiveness_7d"
COL_THROUGHPUT_7D = "throughput_7d"
COL_OUTCOME_STD_14D = "outcome_std_14d"
COL_WOW_DROP_FLAG = "wow_drop_flag"

# Temporal (temporal_analysis.py)
COL_WEEKDAY = "weekday"
COL_WEEKDAY_NAME = "weekday_name"
COL_MONTH = "month"
COL_YEAR = "year"
COL_IS_WEEKEND = "is_weekend"

# --- Thresholds for alerts and detection ---
EFFICIENCY_DROP_WOW_PCT = 0.30  # 30% week-over-week drop to flag
SUSTAINED_IMBALANCE_DAYS = 5    # Consecutive days of backlog increase to flag
ROLLING_DAYS = 7
STABILITY_WINDOW_DAYS = 14
BOTTLENECK_TREND_WINDOW = 7    # Days to assess "continuous" upward trend
STAGNATION_THROUGHPUT_PERCENTILE = 25  # Below this = low throughput
EFFICIENCY_ALERT_THRESHOLD = 0.1  # Below this show dashboard alert

# Severity thresholds for bottleneck (slope or level-based)
SEVERITY_LOW_SLOPE = 0.0
SEVERITY_MODERATE_SLOPE = 5.0
SEVERITY_SEVERE_SLOPE = 15.0
