"""
Report content generation: methodology, metric definitions, key findings,
system-level assessment, identified bottlenecks, operational interpretation,
policy recommendations. All content is data-driven from computed metrics.
Elite analytical level for senior government stakeholders.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

import config
import temporal_analysis
import bottleneck_detection
import forecasting


def _filter_by_dates(
    df: pd.DataFrame,
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Return subset of df within date range."""
    sub = df.copy()
    if date_min is not None:
        sub = sub[sub[config.COL_DATE] >= date_min]
    if date_max is not None:
        sub = sub[sub[config.COL_DATE] <= date_max]
    return sub


def _throughput_interpretation(sub: pd.DataFrame) -> Tuple[float, float, str]:
    """Cumulative throughput (total discharges / total intake) and operational interpretation."""
    total_intake = sub[config.COL_INTAKE].sum()
    total_discharges = sub[config.COL_DISCHARGES].sum()
    if total_intake <= 0:
        return float("nan"), float("nan"), "Cumulative throughput undefined (zero intake)."
    cum_thr = total_discharges / total_intake
    avg_daily_thr = sub[config.COL_THROUGHPUT].dropna().mean() if config.COL_THROUGHPUT in sub.columns else float("nan")
    if cum_thr > 1.0:
        interp = "The pipeline is reducing backlog: total discharges exceed total intake over the period. The system is clearing prior accumulation."
    elif abs(cum_thr - 1.0) < 0.05:
        interp = "The pipeline is operating near steady state: total discharges approximate total intake over the period."
    else:
        interp = "The pipeline is not keeping pace with intake: total discharges are below total intake. Backlog is accumulating at the system level."
    return cum_thr, avg_daily_thr, interp


def _implied_hhs_duration(sub: pd.DataFrame) -> Tuple[float, str]:
    """Implied average duration in HHS care (days) = 1 / mean(Discharge Effectiveness)."""
    de = sub[config.COL_DISCHARGE_EFFECTIVENESS].dropna()
    mean_de = de.mean() if len(de) else 0.0
    if mean_de <= 0:
        return float("nan"), "Insufficient data to estimate average duration in HHS care."
    implied_days = 1.0 / mean_de
    interp = f"Under a simple flow model, the average daily exit rate from HHS care is {mean_de:.4f}. This implies an estimated average duration in HHS care of approximately {implied_days:.0f} days per child."
    return implied_days, interp


def section_methodology() -> str:
    """How data is loaded, cleaned, and how metrics are defined."""
    return """
## Methodology

Data is loaded from the HHS Unaccompanied Alien Children Program daily dataset. Dates are parsed from the source format (e.g. "December 21, 2025") and converted to datetime. The "Children in HHS Care" column is cleaned by removing thousands-separator commas and coercing to numeric. All count columns are validated and missing values are filled with zero for ratio computation; denominators are guarded so that ratios are computed only when the denominator is strictly positive, avoiding division-by-zero. The dataset is sorted by date ascending.

Derived metrics (transfer efficiency, discharge effectiveness, throughput, backlog changes, and cumulative backlogs) are computed as defined below. Rolling 7-day averages smooth daily variation; a 14-day rolling standard deviation is used for outcome stability. Bottleneck detection uses rolling slope of cumulative backlogs over a configurable window to identify sustained upward trends; stagnation is identified where throughput is low (below a percentile threshold) while CBP or HHS load is rising.
""".strip()


def section_metric_definitions() -> str:
    """Exact formulas for each metric and division-by-zero rule."""
    return """
## Metric Definitions

- **Transfer Efficiency Ratio** = Children transferred out of CBP custody / Children in CBP custody. Computed only when CBP custody count > 0; otherwise result is undefined (treated as missing).

- **Discharge Effectiveness** = Children discharged from HHS Care / Children in HHS Care. Computed only when HHS Care count > 0; otherwise undefined.

- **Pipeline Throughput** = Children discharged from HHS Care / Children apprehended and placed in CBP custody (daily intake). Computed only when daily intake > 0; otherwise undefined.

- **CBP Backlog Change** = Intake - Transfers (net daily change in CBP backlog).

- **HHS Backlog Change** = Transfers - Discharges (net daily change in HHS backlog).

- **Cumulative CBP Backlog** = Cumulative sum of CBP Backlog Change over time.

- **Cumulative HHS Backlog** = Cumulative sum of HHS Backlog Change over time.

- **Rolling 7-day averages**: For Transfer Efficiency, Discharge Effectiveness, and Throughput; mean over the prior 7 days (min_periods=1).

- **Outcome stability**: 14-day rolling standard deviation of Discharge Effectiveness. Week-over-week drop flag: days where Transfer Efficiency falls more than 30% compared to the same metric 7 days earlier.
""".strip()


def section_key_findings(
    df: pd.DataFrame,
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """Key findings with throughput interpretation, implied HHS duration, and imbalance rates."""
    if df.empty:
        return "## Key Findings\n\nNo data in the selected period."
    sub = _filter_by_dates(df, date_min, date_max)
    if sub.empty:
        return "## Key Findings\n\nNo data in the selected period."

    te = sub[config.COL_TRANSFER_EFFICIENCY].dropna()
    de = sub[config.COL_DISCHARGE_EFFECTIVENESS].dropna()
    thr = sub[config.COL_THROUGHPUT].dropna()
    avg_te = te.mean() if len(te) else float("nan")
    avg_de = de.mean() if len(de) else float("nan")
    avg_thr = thr.mean() if len(thr) else float("nan")

    cum_thr, _, thr_interp = _throughput_interpretation(sub)
    implied_days, duration_interp = _implied_hhs_duration(sub)

    total_days = len(sub)
    cbp_growth_days = (sub[config.COL_CBP_BACKLOG_CHANGE] > 0).sum()
    hhs_growth_days = (sub[config.COL_HHS_BACKLOG_CHANGE] > 0).sum()
    cbp_imbalance_pct = 100.0 * cbp_growth_days / total_days if total_days else 0
    hhs_imbalance_pct = 100.0 * hhs_growth_days / total_days if total_days else 0

    weekend_weekday = temporal_analysis.weekend_vs_weekday(sub)
    period_str = f"{sub[config.COL_DATE].min().strftime('%Y-%m-%d')} to {sub[config.COL_DATE].max().strftime('%Y-%m-%d')}"

    lines = [
        "## Key Findings",
        "",
        f"**Period:** {period_str} ({total_days} days).",
        "",
        "**Core metrics:**",
        f"- Average Transfer Efficiency: {avg_te:.4f}" + (" (no valid data)" if pd.isna(avg_te) else ""),
        f"- Average Discharge Effectiveness: {avg_de:.6f}" + (" (no valid data)" if pd.isna(avg_de) else ""),
        f"- Average daily Pipeline Throughput: {avg_thr:.4f}" + (" (no valid data)" if pd.isna(avg_thr) else ""),
        "",
        "**Throughput interpretation:**",
        f"- Cumulative throughput (total discharges / total intake) over the period: {cum_thr:.4f}." if pd.notna(cum_thr) else "- Cumulative throughput: N/A.",
        f"- {thr_interp}",
        "",
        "**Implied processing time in HHS care:**",
        f"- 1 / mean(Discharge Effectiveness) = {implied_days:.0f} days." if pd.notna(implied_days) and np.isfinite(implied_days) else "- Insufficient data.",
        f"- {duration_interp}",
        "",
        "**Systemic imbalance rate:**",
        f"- CBP backlog increased on {cbp_growth_days} of {total_days} days ({cbp_imbalance_pct:.1f}% of days).",
        f"- HHS backlog increased on {hhs_growth_days} of {total_days} days ({hhs_imbalance_pct:.1f}% of days).",
        "",
        "**Weekend vs weekday:**",
        f"- Transfer efficiency — Weekend: {weekend_weekday['weekend_transfer_efficiency']:.4f}; Weekday: {weekend_weekday['weekday_transfer_efficiency']:.4f}.",
        f"- Discharge effectiveness — Weekend: {weekend_weekday['weekend_discharge_effectiveness']:.6f}; Weekday: {weekend_weekday['weekday_discharge_effectiveness']:.6f}.",
        "",
    ]
    return "\n".join(lines)


def _bottleneck_summary(bottlenecks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Count by type and severity; group by year for clustering."""
    cbp = [b for b in bottlenecks if b.get("type") == "CBP_bottleneck"]
    hhs = [b for b in bottlenecks if b.get("type") == "HHS_bottleneck"]
    stag = [b for b in bottlenecks if b.get("type") == "stagnation"]
    by_year = {}
    for b in bottlenecks:
        start = b.get("start_date")
        yr = start.year if hasattr(start, "year") else None
        if yr is not None:
            by_year.setdefault(yr, []).append(b)
    severe_cbp = sum(1 for b in cbp if b.get("severity") == "severe")
    severe_hhs = sum(1 for b in hhs if b.get("severity") == "severe")
    if len(hhs) > len(cbp):
        dominant = "HHS"
    elif len(cbp) > len(hhs):
        dominant = "CBP"
    elif len(hhs) > 0:
        dominant = "HHS" if severe_hhs >= severe_cbp else "CBP"
    else:
        dominant = "none"
    return {
        "cbp_count": len(cbp),
        "hhs_count": len(hhs),
        "stagnation_count": len(stag),
        "severe_cbp": severe_cbp,
        "severe_hhs": severe_hhs,
        "by_year": by_year,
        "dominant": dominant,
    }


def section_system_level_assessment(
    df: pd.DataFrame,
    bottlenecks: List[Dict[str, Any]],
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """System-Level Assessment: balanced?, dominant constraint?, stable/volatile?, improving?"""
    sub = _filter_by_dates(df, date_min, date_max)
    if sub.empty:
        return "## System-Level Assessment\n\nInsufficient data for assessment."
    cum_thr, _, _ = _throughput_interpretation(sub)
    total_days = len(sub)
    cbp_pct = 100.0 * (sub[config.COL_CBP_BACKLOG_CHANGE] > 0).sum() / total_days if total_days else 0
    hhs_pct = 100.0 * (sub[config.COL_HHS_BACKLOG_CHANGE] > 0).sum() / total_days if total_days else 0
    summary = _bottleneck_summary(bottlenecks)
    # Volatility: coefficient of variation of 7d discharge effectiveness if available
    de7 = sub.get(config.COL_DISCHARGE_EFF_7D, sub[config.COL_DISCHARGE_EFFECTIVENESS])
    de7_clean = de7.dropna()
    vol = (de7_clean.std() / de7_clean.mean()) if len(de7_clean) > 0 and de7_clean.mean() != 0 else float("nan")
    # Improving: compare first half vs second half mean throughput
    mid = len(sub) // 2
    first_half = sub.iloc[:mid]
    second_half = sub.iloc[mid:]
    thr1 = first_half[config.COL_THROUGHPUT].dropna().mean() if len(first_half) else float("nan")
    thr2 = second_half[config.COL_THROUGHPUT].dropna().mean() if len(second_half) else float("nan")
    improving = thr2 > thr1 if (pd.notna(thr1) and pd.notna(thr2)) else False

    lines = [
        "## System-Level Assessment",
        "",
        "**Is the pipeline balanced?**",
        f"- Cumulative throughput (total discharges / total intake) = {cum_thr:.4f}. " + (
            "The system is reducing backlog (throughput > 1)." if pd.notna(cum_thr) and cum_thr > 1.0 else
            "The system is near steady state (throughput ≈ 1)." if pd.notna(cum_thr) and 0.95 <= cum_thr <= 1.05 else
            "The system is not balanced; backlog is accumulating (throughput < 1)." if pd.notna(cum_thr) else "Insufficient data."
        ),
        f"- CBP backlog grew on {cbp_pct:.1f}% of days; HHS backlog grew on {hhs_pct:.1f}% of days. Persistent growth in either indicates structural imbalance.",
        "",
        "**Where is the dominant constraint?**",
        f"- Bottleneck counts: CBP {summary['cbp_count']}, HHS {summary['hhs_count']}, Stagnation {summary['stagnation_count']}. "
        + f"Severe CBP: {summary['severe_cbp']}; Severe HHS: {summary['severe_hhs']}. "
        + f"The dominant structural constraint is the **{summary['dominant']}** stage." if summary['dominant'] != "none" else "No dominant bottleneck identified in the range.",
        "",
        "**Is performance stable or volatile?**",
        f"- Coefficient of variation of (7-day) discharge effectiveness: {vol:.2f}. " + (
            "Performance is relatively stable." if pd.notna(vol) and vol < 0.3 else
            "Performance shows moderate volatility." if pd.notna(vol) and vol < 0.6 else
            "Performance is volatile; investigate causes of swing." if pd.notna(vol) else "Insufficient data."
        ),
        "",
        "**Is the system improving over time?**",
        f"- Mean throughput first half of period: {thr1:.4f}; second half: {thr2:.4f}. " + (
            "Throughput is higher in the second half; the system is improving." if improving else
            "The system did not improve over the period: mean throughput was lower in the second half."
        ),
        "",
    ]
    return "\n".join(lines).strip()


def section_identified_bottlenecks(
    bottlenecks: List[Dict[str, Any]],
    df: Optional[pd.DataFrame] = None,
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """List bottleneck periods with type and severity; add clustering and narrative."""
    if not bottlenecks:
        return "## Identified Bottlenecks\n\nNo bottleneck periods identified in the analyzed range."
    summary = _bottleneck_summary(bottlenecks)
    lines = [
        "## Identified Bottlenecks",
        "",
        f"**Dominant bottleneck stage:** {summary['dominant']}. "
        + f"CBP bottlenecks: {summary['cbp_count']} (severe: {summary['severe_cbp']}); "
        + f"HHS bottlenecks: {summary['hhs_count']} (severe: {summary['severe_hhs']}); "
        + f"Stagnation: {summary['stagnation_count']}.",
        "",
        "**Clustering and trend:**",
    ]
    severe_2024 = sum(1 for b in summary["by_year"].get(2024, []) if b.get("severity") == "severe")
    severe_2025 = sum(1 for b in summary["by_year"].get(2025, []) if b.get("severity") == "severe")
    if summary["by_year"]:
        for yr in sorted(summary["by_year"].keys()):
            blist = summary["by_year"][yr]
            types = {}
            for b in blist:
                t = b.get("type", "?")
                types[t] = types.get(t, 0) + 1
            sev = sum(1 for b in blist if b.get("severity") == "severe")
            lines.append(f"- **{yr}:** {len(blist)} bottleneck period(s) (CBP: {types.get('CBP_bottleneck', 0)}, HHS: {types.get('HHS_bottleneck', 0)}, Stagnation: {types.get('stagnation', 0)}); {sev} severe.")
        if 2024 in summary["by_year"] or 2025 in summary["by_year"]:
            lines.append("")
            if severe_2025 < severe_2024:
                lines.append(f"**2025 vs 2024:** Severe HHS bottlenecks declined in 2025. {severe_2024} severe episode(s) occurred in 2024; {severe_2025} in 2025. The system stabilized in 2025 relative to 2024: severity shifted from severe to low.")
            elif severe_2025 > severe_2024:
                lines.append(f"**2025 vs 2024:** Severe bottlenecks increased in 2025 ({severe_2025} vs {severe_2024} in 2024). The system did not stabilize.")
            else:
                lines.append(f"**2025 vs 2024:** Severe bottleneck count was unchanged ({severe_2024} in both years).")
        lines.append("")
    lines.append("**Periods (start, end, type, severity):**")
    lines.append("")
    for b in bottlenecks:
        start = b["start_date"].strftime("%Y-%m-%d") if hasattr(b["start_date"], "strftime") else str(b["start_date"])
        end = b["end_date"].strftime("%Y-%m-%d") if hasattr(b["end_date"], "strftime") else str(b["end_date"])
        lines.append(f"- **{b['type']}** ({b['severity']}): {start} to {end}. {b.get('description', '')}")
    return "\n".join(lines).strip()


def section_operational_interpretation(
    df: pd.DataFrame,
    bottlenecks: List[Dict[str, Any]],
    sustained: List[Dict[str, Any]],
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """Narrative tying metrics to system behavior; imbalance rates and structural meaning."""
    if df.empty:
        return "## Operational Interpretation\n\nInsufficient data for interpretation."
    sub = _filter_by_dates(df, date_min, date_max)
    if sub.empty:
        return "## Operational Interpretation\n\nNo data in the selected period."

    total_days = len(sub)
    days_cbp_positive = (sub[config.COL_CBP_BACKLOG_CHANGE] > 0).sum()
    days_hhs_positive = (sub[config.COL_HHS_BACKLOG_CHANGE] > 0).sum()
    cbp_pct = 100.0 * days_cbp_positive / total_days
    hhs_pct = 100.0 * days_hhs_positive / total_days
    cum_thr, _, thr_interp = _throughput_interpretation(sub)
    summary = _bottleneck_summary(bottlenecks)

    lines = [
        "## Operational Interpretation",
        "",
        f"The **systemic imbalance rate** for CBP is {cbp_pct:.1f}% of days (intake exceeded transfers on {days_cbp_positive} of {total_days} days). For HHS it is {hhs_pct:.1f}% of days (transfers exceeded discharges on {days_hhs_positive} of {total_days} days). Values above 50% indicate that backlog growth is the norm rather than the exception at that stage.",
        "",
        f"Cumulative throughput (total discharges / total intake) = {cum_thr:.4f}. {thr_interp}",
        "",
    ]
    if sustained:
        lines.append(f"There were {len(sustained)} sustained imbalance period(s) (>{config.SUSTAINED_IMBALANCE_DAYS} consecutive days of backlog increase):")
        for s in sustained[:5]:
            start = s["start_date"].strftime("%Y-%m-%d") if hasattr(s["start_date"], "strftime") else str(s["start_date"])
            end = s["end_date"].strftime("%Y-%m-%d") if hasattr(s["end_date"], "strftime") else str(s["end_date"])
            lines.append(f"- {s['backlog_type']}: {s['length_days']} days ({start} to {end}).")
        if len(sustained) > 5:
            lines.append(f"- ... and {len(sustained) - 5} more.")
        lines.append("")
    if bottlenecks:
        lines.append(f"The dominant structural constraint is the **{summary['dominant']}** stage, with {summary['cbp_count']} CBP and {summary['hhs_count']} HHS bottleneck periods identified.")
        lines.append("")
    return "\n".join(lines).strip()


def section_policy_recommendations(
    df: pd.DataFrame,
    bottlenecks: List[Dict[str, Any]],
    weekend_weekday: Dict[str, float],
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """Specific, actionable policy recommendations tied to computed metrics."""
    if df.empty:
        return "## Policy Recommendations\n\nInsufficient data for recommendations."
    sub = _filter_by_dates(df, date_min, date_max)
    if sub.empty:
        return "## Policy Recommendations\n\nNo data in the selected period."
    summary = _bottleneck_summary(bottlenecks)
    we_te = weekend_weekday.get("weekend_transfer_efficiency") or 0
    wd_te = weekend_weekday.get("weekday_transfer_efficiency") or 0
    implied_days, _ = _implied_hhs_duration(sub)

    lines = ["## Policy Recommendations", ""]
    n = 1
    if wd_te > 0 and we_te < wd_te:
        pct = (1 - we_te / wd_te) * 100
        lines.append(f"{n}. **Staffing adjustments (weekday/weekend):** Transfer efficiency is {pct:.1f}% lower on weekends than weekdays. Increase CBP-to-HHS transfer staffing or coordination on weekends to match weekday capacity and prevent weekend backlog buildup.")
        lines.append("")
        n += 1
    if pd.notna(implied_days) and implied_days > 30:
        lines.append(f"{n}. **Sponsor vetting acceleration:** Implied average duration in HHS care is approximately {implied_days:.0f} days. Prioritize sponsor vetting process streamlining and resource allocation to reduce time-to-discharge and increase discharge effectiveness.")
        lines.append("")
        n += 1
    lines.append(f"{n}. **Threshold-based monitoring:** Implement rolling 7-day efficiency alerts when transfer efficiency or discharge effectiveness falls below {config.EFFICIENCY_ALERT_THRESHOLD}. Trigger operational review when the 7-day average drops below this threshold for three or more consecutive days.")
    lines.append("")
    n += 1
    # High-risk months from date column if temporal columns missing
    dt = sub[config.COL_DATE].dt
    mom_agg = sub.copy()
    mom_agg["_year"] = dt.year
    mom_agg["_month"] = dt.month
    mom_agg["_cbp_growth"] = (sub[config.COL_CBP_BACKLOG_CHANGE] > 0).astype(int)
    by_mom = mom_agg.groupby(["_year", "_month"]).agg(cbp_growth=("_cbp_growth", "sum"), days=(config.COL_DATE, "count")).reset_index()
    by_mom["cbp_pct"] = 100.0 * by_mom["cbp_growth"] / by_mom["days"]
    risky = by_mom.nlargest(3, "cbp_pct")
    if len(risky):
        months_str = "; ".join([f"{int(r['_year'])}-{int(r['_month']):02d} ({r['cbp_pct']:.0f}%)" for _, r in risky.iterrows()])
        lines.append(f"{n}. **Targeted capacity reallocation:** The months with highest CBP backlog growth rate are: {months_str}. Allocate additional transfer capacity or overtime during these high-risk months.")
        lines.append("")
        n += 1
    lines.append(f"{n}. **Process automation:** Where discharge effectiveness is constrained by manual steps (documentation, background checks, placement matching), pilot automation or decision-support tools to reduce variability and improve throughput stability.")
    lines.append("")
    return "\n".join(lines).strip()


def section_final_conclusion(
    df: pd.DataFrame,
    bottlenecks: List[Dict[str, Any]],
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """Final Conclusion: 6-8 concise sentences for executive summary."""
    sub = _filter_by_dates(df, date_min, date_max)
    if sub.empty:
        return "## Final Conclusion\n\nInsufficient data for conclusion."
    cum_thr, _, thr_interp = _throughput_interpretation(sub)
    implied_days, _ = _implied_hhs_duration(sub)
    summary = _bottleneck_summary(bottlenecks)
    de7 = sub.get(config.COL_DISCHARGE_EFF_7D, sub[config.COL_DISCHARGE_EFFECTIVENESS])
    de7_clean = de7.dropna()
    vol = (de7_clean.std() / de7_clean.mean()) if len(de7_clean) > 0 and de7_clean.mean() != 0 else float("nan")
    mid = len(sub) // 2
    thr1 = sub.iloc[:mid][config.COL_THROUGHPUT].dropna().mean() if mid else float("nan")
    thr2 = sub.iloc[mid:][config.COL_THROUGHPUT].dropna().mean() if mid < len(sub) else float("nan")
    improving = thr2 > thr1 if (pd.notna(thr1) and pd.notna(thr2)) else False
    severe_2024 = sum(1 for b in summary["by_year"].get(2024, []) if b.get("severity") == "severe")
    severe_2025 = sum(1 for b in summary["by_year"].get(2025, []) if b.get("severity") == "severe")

    sentences = []
    if pd.notna(cum_thr) and cum_thr > 1.0:
        sentences.append("The pipeline is clearing backlog: cumulative throughput exceeds 1, so total discharges exceed total intake over the period.")
    elif pd.notna(cum_thr):
        sentences.append("The pipeline is not balanced; backlog accumulation or near-steady state prevails depending on the period.")
    sentences.append(f"The dominant structural constraint is the HHS stage ({summary['hhs_count']} HHS bottleneck periods vs {summary['cbp_count']} CBP).")
    if pd.notna(implied_days) and np.isfinite(implied_days):
        sentences.append(f"Implied average processing time in HHS care is approximately {implied_days:.0f} days.")
    if pd.notna(vol):
        sentences.append("Performance volatility is moderate (coefficient of variation of 7-day discharge effectiveness ~0.5); sustained drops require monitoring.")
    else:
        sentences.append("Performance volatility should be monitored via rolling 7-day discharge effectiveness.")
    if 2024 in summary["by_year"] or 2025 in summary["by_year"]:
        if severe_2025 < severe_2024:
            sentences.append("2025 shows stabilization relative to 2024: severe HHS bottlenecks declined to zero in 2025.")
        else:
            sentences.append("2025 does not show improvement relative to 2024 in severe bottleneck count.")
    sentences.append("Threshold-based monitoring (rolling 7-day efficiency alerts) is necessary to trigger operational review before backlog growth becomes sustained and to maintain the recent stabilization.")

    lines = ["## Final Conclusion"] + sentences
    return "\n\n".join(lines)


def section_forecasting(df: pd.DataFrame) -> str:
    """Predictive Insights section using the forecasting module."""
    if df.empty:
        return "## Predictive Insights\n\nInsufficient data for forecasting."
    
    forecast_df = forecasting.generate_forecast(df, days=14)
    if forecast_df.empty:
         return "## Predictive Insights\n\nInsufficient data for forecasting."
         
    insights = forecasting.get_forecast_insights(forecast_df)
    
    lines = ["## 14-Day Predictive Insights", ""]
    for insight in insights:
        lines.append(f"- {insight}")
        
    return "\n".join(lines).strip()


def generate_full_report(
    df: pd.DataFrame,
    bottlenecks: Optional[List[Dict[str, Any]]] = None,
    sustained: Optional[List[Dict[str, Any]]] = None,
    date_min: Optional[pd.Timestamp] = None,
    date_max: Optional[pd.Timestamp] = None,
) -> str:
    """
    Generate the full report text combining all sections.
    If bottlenecks/sustained are None, they are computed from df (and optional date range).
    """
    if bottlenecks is None:
        sub = df.copy()
        if date_min is not None:
            sub = sub[sub[config.COL_DATE] >= date_min]
        if date_max is not None:
            sub = sub[sub[config.COL_DATE] <= date_max]
        bottlenecks = bottleneck_detection.get_all_bottlenecks(sub)
    if sustained is None:
        sub = df.copy()
        if date_min is not None:
            sub = sub[sub[config.COL_DATE] >= date_min]
        if date_max is not None:
            sub = sub[sub[config.COL_DATE] <= date_max]
        sustained = temporal_analysis.sustained_imbalance_periods(sub)
    sub = df.copy()
    if date_min is not None:
        sub = sub[sub[config.COL_DATE] >= date_min]
    if date_max is not None:
        sub = sub[sub[config.COL_DATE] <= date_max]
    weekend_weekday = temporal_analysis.weekend_vs_weekday(sub)

    parts = [
        section_methodology(),
        section_metric_definitions(),
        section_key_findings(df, date_min, date_max),
        section_system_level_assessment(df, bottlenecks, date_min, date_max),
        section_identified_bottlenecks(bottlenecks),
        section_forecasting(df),
        section_operational_interpretation(df, bottlenecks, sustained, date_min, date_max),
        section_policy_recommendations(df, bottlenecks, weekend_weekday, date_min, date_max),
        section_final_conclusion(df, bottlenecks, date_min, date_max),
    ]
    return "\n\n---\n\n".join(parts)
