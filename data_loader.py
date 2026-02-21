"""
Data loading, parsing, and validation for the care transition dataset.
Handles date parsing, numeric cleaning (e.g. HHS column with commas), and safe structure.
"""

import pandas as pd
from typing import Tuple, Optional

import config


def load_data(path: Optional[str] = None) -> pd.DataFrame:
    """
    Load CSV, parse dates, clean numerics, sort by date, handle missing values.
    Returns a single validated DataFrame. Division-by-zero is handled in metrics.py.
    """
    file_path = path or config.DEFAULT_DATA_PATH
    df = pd.read_csv(file_path)

    # Ensure required columns exist
    required = [
        config.COL_DATE,
        config.COL_INTAKE,
        config.COL_CBP_LOAD,
        config.COL_TRANSFERS,
        config.COL_HHS_LOAD,
        config.COL_DISCHARGES,
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse date: format "December 21, 2025"
    df[config.COL_DATE] = pd.to_datetime(df[config.COL_DATE], format="%B %d, %Y", errors="coerce")
    # Drop rows with invalid dates
    df = df.dropna(subset=[config.COL_DATE])

    # HHS Care column may have commas (e.g. "2,484")
    df[config.COL_HHS_LOAD] = (
        df[config.COL_HHS_LOAD]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", float("nan"))
    )
    df[config.COL_HHS_LOAD] = pd.to_numeric(df[config.COL_HHS_LOAD], errors="coerce")

    # Ensure all numeric columns are numeric; fill NaN with 0 for counts where appropriate
    numeric_cols = [
        config.COL_INTAKE,
        config.COL_CBP_LOAD,
        config.COL_TRANSFERS,
        config.COL_HHS_LOAD,
        config.COL_DISCHARGES,
    ]
    for col in numeric_cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Fill missing counts with 0 so ratios can be guarded in metrics (denom > 0)
    df[numeric_cols] = df[numeric_cols].fillna(0)
    # Clamp to non-negative
    df[numeric_cols] = df[numeric_cols].clip(lower=0)

    # Sort by date ascending
    df = df.sort_values(config.COL_DATE).reset_index(drop=True)

    return df


def get_validation_summary(df: pd.DataFrame) -> dict:
    """Return a small summary: date range, row count, any columns with all NaN."""
    if df.empty:
        return {"row_count": 0, "date_min": None, "date_max": None, "all_nan_columns": []}
    date_min = df[config.COL_DATE].min()
    date_max = df[config.COL_DATE].max()
    all_nan = [c for c in df.columns if df[c].isna().all()]
    return {
        "row_count": len(df),
        "date_min": date_min,
        "date_max": date_max,
        "all_nan_columns": all_nan,
    }
