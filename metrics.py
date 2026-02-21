"""
Derived metrics for care transition efficiency and placement outcomes.
All ratio calculations use safe division (denominator > 0) to avoid division-by-zero.
"""

import pandas as pd
import numpy as np

import config


def _safe_ratio(num: pd.Series, denom: pd.Series) -> pd.Series:
    """Return num/denom where denom > 0, else NaN."""
    return np.where(denom > 0, num / denom, np.nan)


def compute_all_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all Phase 2 metrics and add as columns.
    - Transfer Efficiency = Transfers / CBP load (guard: CBP load > 0)
    - Discharge Effectiveness = Discharges / HHS load (guard: HHS load > 0)
    - Pipeline Throughput = Discharges / Intake (guard: Intake > 0)
    - CBP/HHS backlog change and cumulative backlogs
    - Rolling 7-day averages for efficiency, discharge effectiveness, throughput
    - Outcome stability: 14-day rolling std, week-over-week drop flag (>30%)
    """
    out = df.copy()
    intake = out[config.COL_INTAKE]
    cbp_load = out[config.COL_CBP_LOAD]
    transfers = out[config.COL_TRANSFERS]
    hhs_load = out[config.COL_HHS_LOAD]
    discharges = out[config.COL_DISCHARGES]

    # 1) Transfer Efficiency Ratio = Transfers / CBP load
    out[config.COL_TRANSFER_EFFICIENCY] = _safe_ratio(transfers, cbp_load)

    # 2) Discharge Effectiveness = Discharges / HHS load
    out[config.COL_DISCHARGE_EFFECTIVENESS] = _safe_ratio(discharges, hhs_load)

    # 3) Pipeline Throughput = Discharges / Intake
    out[config.COL_THROUGHPUT] = _safe_ratio(discharges, intake)

    # 4) CBP Backlog Change = Intake - Transfers
    out[config.COL_CBP_BACKLOG_CHANGE] = intake - transfers

    # 5) HHS Backlog Change = Transfers - Discharges
    out[config.COL_HHS_BACKLOG_CHANGE] = transfers - discharges

    # 6) Cumulative Backlogs
    out[config.COL_CUM_CBP_BACKLOG] = out[config.COL_CBP_BACKLOG_CHANGE].cumsum()
    out[config.COL_CUM_HHS_BACKLOG] = out[config.COL_HHS_BACKLOG_CHANGE].cumsum()

    # 7) Rolling 7-day averages
    w = config.ROLLING_DAYS
    out[config.COL_TRANSFER_EFF_7D] = out[config.COL_TRANSFER_EFFICIENCY].rolling(w, min_periods=1).mean()
    out[config.COL_DISCHARGE_EFF_7D] = out[config.COL_DISCHARGE_EFFECTIVENESS].rolling(w, min_periods=1).mean()
    out[config.COL_THROUGHPUT_7D] = out[config.COL_THROUGHPUT].rolling(w, min_periods=1).mean()

    # 8) Outcome stability: rolling 14-day std (e.g. on Discharge Effectiveness)
    out[config.COL_OUTCOME_STD_14D] = (
        out[config.COL_DISCHARGE_EFFECTIVENESS]
        .rolling(config.STABILITY_WINDOW_DAYS, min_periods=2)
        .std()
    )

    # Week-over-week change: (metric_t - metric_t-7) / metric_t-7; flag drop > 30%
    eff = out[config.COL_TRANSFER_EFFICIENCY]
    eff_7d_ago = eff.shift(7)
    wow_change = _safe_ratio(eff - eff_7d_ago, eff_7d_ago)
    out[config.COL_WOW_DROP_FLAG] = wow_change <= (-config.EFFICIENCY_DROP_WOW_PCT)

    return out
