"""
Bottleneck detection: CBP bottleneck, HHS bottleneck, and stagnation periods.
Returns structured summaries with start_date, end_date, type, severity (low/moderate/severe).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any

import config


def _slope_severity(slope: float) -> str:
    """Map slope magnitude to severity using config thresholds."""
    abs_slope = abs(slope)
    if abs_slope >= config.SEVERITY_SEVERE_SLOPE:
        return "severe"
    if abs_slope >= config.SEVERITY_MODERATE_SLOPE:
        return "moderate"
    return "low"


def _detect_trend_periods(
    df: pd.DataFrame,
    value_col: str,
    window: int,
    min_consecutive_positive_slopes: int = 4,
) -> List[Dict[str, Any]]:
    """
    Find periods where value_col has upward trend: rolling slope over `window` days
    is positive for at least min_consecutive_positive_slopes consecutive windows.
    Returns list of {start_date, end_date, severity, description}.
    """
    if len(df) < window + 1 or value_col not in df.columns:
        return []
    date_col = df[config.COL_DATE].values
    vals = df[value_col].values
    slopes = []
    for i in range(len(vals) - window):
        y = vals[i : i + window]
        x = np.arange(window)
        if np.isfinite(y).sum() < 2:
            slopes.append(np.nan)
        else:
            coefs = np.polyfit(x, np.nan_to_num(y, nan=0), 1)
            slopes.append(coefs[0])
    slopes = np.array(slopes)
    # Consecutive positive slopes
    positive = slopes > 0
    periods = []
    i = 0
    n = len(positive)
    while i < n:
        if not positive[i]:
            i += 1
            continue
        j = i
        while j < n and positive[j]:
            j += 1
        length = j - i
        if length >= min_consecutive_positive_slopes:
            start_idx = i
            end_idx = min(j + window - 1, len(df) - 1)
            mean_slope = np.nanmean(slopes[i:j])
            severity = _slope_severity(mean_slope)
            periods.append({
                "start_date": pd.Timestamp(date_col[start_idx]),
                "end_date": pd.Timestamp(date_col[end_idx]),
                "severity": severity,
                "mean_slope": float(mean_slope),
                "description": f"Cumulative backlog trend upward (mean slope {mean_slope:.2f})",
            })
        i = j
    return periods


def detect_cbp_bottlenecks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """CBP bottleneck: cumulative CBP backlog trending upward over BOTTLENECK_TREND_WINDOW."""
    window = config.BOTTLENECK_TREND_WINDOW
    periods = _detect_trend_periods(df, config.COL_CUM_CBP_BACKLOG, window)
    for p in periods:
        p["type"] = "CBP_bottleneck"
    return periods


def detect_hhs_bottlenecks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """HHS bottleneck: cumulative HHS backlog trending upward over BOTTLENECK_TREND_WINDOW."""
    window = config.BOTTLENECK_TREND_WINDOW
    periods = _detect_trend_periods(df, config.COL_CUM_HHS_BACKLOG, window)
    for p in periods:
        p["type"] = "HHS_bottleneck"
    return periods


def detect_stagnation_periods(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Stagnation: low throughput (below STAGNATION_THROUGHPUT_PERCENTILE) and rising load
    (CBP or HHS load increasing over same window). Return periods with start_date, end_date, severity.
    """
    if len(df) < config.BOTTLENECK_TREND_WINDOW or config.COL_THROUGHPUT not in df.columns:
        return []
    pct = config.STAGNATION_THROUGHPUT_PERCENTILE
    thr = df[config.COL_THROUGHPUT].quantile(pct / 100.0)
    low_throughput = df[config.COL_THROUGHPUT] <= thr
    # Rising CBP load: diff of CBP load > 0 over window
    cbp_load = df[config.COL_CBP_LOAD].values
    hhs_load = df[config.COL_HHS_LOAD].values
    w = config.BOTTLENECK_TREND_WINDOW
    rising_cbp = np.zeros(len(df), dtype=bool)
    rising_hhs = np.zeros(len(df), dtype=bool)
    for i in range(w, len(df)):
        rising_cbp[i] = cbp_load[i] > cbp_load[i - w]
        rising_hhs[i] = hhs_load[i] > hhs_load[i - w]
    stagnation = low_throughput & (rising_cbp | rising_hhs)
    # Consecutive stagnation periods
    date_col = df[config.COL_DATE]
    periods = []
    i = 0
    n = len(df)
    min_days = config.SUSTAINED_IMBALANCE_DAYS
    while i < n:
        if not stagnation.iloc[i]:
            i += 1
            continue
        j = i
        while j < n and stagnation.iloc[j]:
            j += 1
        if j - i >= min_days:
            severity = "moderate" if (j - i) >= 10 else "low"
            periods.append({
                "start_date": date_col.iloc[i],
                "end_date": date_col.iloc[j - 1],
                "type": "stagnation",
                "severity": severity,
                "description": "Low throughput with rising CBP or HHS load",
            })
        i = j
    return periods


def get_all_bottlenecks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Run all bottleneck detectors and return a single list of structured summaries.
    Each item: start_date, end_date, type (CBP_bottleneck / HHS_bottleneck / stagnation), severity.
    """
    results = []
    results.extend(detect_cbp_bottlenecks(df))
    results.extend(detect_hhs_bottlenecks(df))
    results.extend(detect_stagnation_periods(df))
    # Sort by start_date
    results.sort(key=lambda x: x["start_date"])
    return results
