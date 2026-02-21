"""
Temporal analysis: weekday, month, weekend vs weekday, month-over-month trends,
and sustained imbalance periods (>5 consecutive days of backlog increase).
"""

import pandas as pd
from typing import List, Dict, Any

import config


def add_temporal_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add weekday, weekday_name, month, year, is_weekend. Modifies copy."""
    out = df.copy()
    dt = out[config.COL_DATE].dt
    out[config.COL_WEEKDAY] = dt.weekday
    out[config.COL_WEEKDAY_NAME] = dt.day_name()
    out[config.COL_MONTH] = dt.month
    out[config.COL_YEAR] = dt.year
    out[config.COL_IS_WEEKEND] = out[config.COL_WEEKDAY].isin([5, 6])
    return out


def efficiency_by_weekday(df: pd.DataFrame) -> pd.DataFrame:
    """Average transfer efficiency and discharge effectiveness by weekday (0–6)."""
    if config.COL_WEEKDAY not in df.columns:
        df = add_temporal_columns(df)
    agg = df.groupby(config.COL_WEEKDAY).agg(
        transfer_efficiency_mean=(config.COL_TRANSFER_EFFICIENCY, "mean"),
        discharge_effectiveness_mean=(config.COL_DISCHARGE_EFFECTIVENESS, "mean"),
        throughput_mean=(config.COL_THROUGHPUT, "mean"),
    ).reset_index()
    return agg


def weekend_vs_weekday(df: pd.DataFrame) -> Dict[str, float]:
    """Compare mean efficiency and discharge effectiveness: weekend vs weekday."""
    if config.COL_IS_WEEKEND not in df.columns:
        df = add_temporal_columns(df)
    weekend = df[df[config.COL_IS_WEEKEND]]
    weekday = df[~df[config.COL_IS_WEEKEND]]
    return {
        "weekend_transfer_efficiency": weekend[config.COL_TRANSFER_EFFICIENCY].mean(),
        "weekday_transfer_efficiency": weekday[config.COL_TRANSFER_EFFICIENCY].mean(),
        "weekend_discharge_effectiveness": weekend[config.COL_DISCHARGE_EFFECTIVENESS].mean(),
        "weekday_discharge_effectiveness": weekday[config.COL_DISCHARGE_EFFECTIVENESS].mean(),
        "weekend_throughput": weekend[config.COL_THROUGHPUT].mean(),
        "weekday_throughput": weekday[config.COL_THROUGHPUT].mean(),
    }


def month_over_month_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Group by year and month; aggregate mean transfer efficiency and discharge effectiveness."""
    if config.COL_MONTH not in df.columns:
        df = add_temporal_columns(df)
    mom = (
        df.groupby([config.COL_YEAR, config.COL_MONTH])
        .agg(
            transfer_efficiency_mean=(config.COL_TRANSFER_EFFICIENCY, "mean"),
            discharge_effectiveness_mean=(config.COL_DISCHARGE_EFFECTIVENESS, "mean"),
            throughput_mean=(config.COL_THROUGHPUT, "mean"),
        )
        .reset_index()
    )
    mom["period"] = mom[config.COL_YEAR].astype(str) + "-" + mom[config.COL_MONTH].astype(str).str.zfill(2)
    return mom


def _consecutive_periods(series: pd.Series, min_days: int) -> List[Dict[str, Any]]:
    """
    Find runs where series is True for at least min_days consecutive days.
    Returns list of {start_idx, end_idx, length} (integer indices).
    """
    periods = []
    i = 0
    n = len(series)
    while i < n:
        if not series.iloc[i]:
            i += 1
            continue
        j = i
        while j < n and series.iloc[j]:
            j += 1
        length = j - i
        if length >= min_days:
            periods.append({"start_idx": i, "end_idx": j - 1, "length": length})
        i = j
    return periods


def sustained_imbalance_periods(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Flag periods with > SUSTAINED_IMBALANCE_DAYS consecutive days where backlog increased.
    Backlog increase: CBP backlog change > 0 or HHS backlog change > 0.
    Returns list of {start_date, end_date, backlog_type: 'CBP'|'HHS'|'both', length}.
    """
    if df.empty or config.COL_CBP_BACKLOG_CHANGE not in df.columns:
        return []
    out = []
    min_days = config.SUSTAINED_IMBALANCE_DAYS
    date_col = df[config.COL_DATE]

    cbp_increase = df[config.COL_CBP_BACKLOG_CHANGE] > 0
    hhs_increase = df[config.COL_HHS_BACKLOG_CHANGE] > 0

    for name, series in [("CBP", cbp_increase), ("HHS", hhs_increase)]:
        for p in _consecutive_periods(series, min_days):
            start_date = date_col.iloc[p["start_idx"]]
            end_date = date_col.iloc[p["end_idx"]]
            out.append({
                "start_date": start_date,
                "end_date": end_date,
                "backlog_type": name,
                "length_days": p["length"],
            })

    # Optionally merge overlapping CBP and HHS into "both" where same date range
    return out


def get_temporal_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with temporal columns added (for dashboard)."""
    if config.COL_WEEKDAY in df.columns:
        return df
    return add_temporal_columns(df)
