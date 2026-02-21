"""
Streamlit dashboard for Care Transition Efficiency & Placement Outcome Analytics.
Orchestrates data_loader, metrics, temporal_analysis, bottleneck_detection, report_generator.
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

import config
import data_loader
import metrics
import temporal_analysis
import bottleneck_detection
import report_generator


@st.cache_data
def load_and_prepare():
    """Load data, compute metrics, add temporal columns. Cached."""
    df = data_loader.load_data()
    df = metrics.compute_all_metrics(df)
    df = temporal_analysis.get_temporal_dataframe(df)
    return df


def main():
    st.set_page_config(
        page_title="Care Transition Efficiency & Placement Outcome Analytics",
        layout="wide",
    )
    st.title("Care Transition Efficiency & Placement Outcome Analytics")
    st.caption("3-stage pipeline: CBP custody → HHS care → Discharge to sponsors")

    df = load_and_prepare()
    if df.empty:
        st.error("No data loaded. Check that the CSV path is correct.")
        return

    date_min_data = df[config.COL_DATE].min()
    date_max_data = df[config.COL_DATE].max()
    if hasattr(date_min_data, "date"):
        date_min_data = date_min_data.date()
    if hasattr(date_max_data, "date"):
        date_max_data = date_max_data.date()

    # --- Sidebar: filters and toggles ---
    with st.sidebar:
        st.header("Filters & options")
        range_min = st.date_input(
            "Start date",
            value=date_min_data,
            min_value=date_min_data,
            max_value=date_max_data,
        )
        range_max = st.date_input(
            "End date",
            value=date_max_data,
            min_value=date_min_data,
            max_value=date_max_data,
        )
        if range_min > range_max:
            st.warning("Start date must be before end date; using full range.")
            range_min, range_max = date_min_data, date_max_data
        show_rolling = st.checkbox("Show 7-day rolling averages on ratio charts", value=True)
        st.divider()

    # Filter by date range
    mask = (df[config.COL_DATE].dt.date >= range_min) & (df[config.COL_DATE].dt.date <= range_max)
    sub = df.loc[mask].copy()
    if sub.empty:
        st.warning("No data in the selected date range. Adjust the filters.")
        return

    # --- Alerts ---
    latest = sub.iloc[-1]
    te = latest.get(config.COL_TRANSFER_EFFICIENCY)
    de = latest.get(config.COL_DISCHARGE_EFFECTIVENESS)
    alert_te = pd.notna(te) and te < config.EFFICIENCY_ALERT_THRESHOLD
    alert_de = pd.notna(de) and de < config.EFFICIENCY_ALERT_THRESHOLD
    sustained = temporal_analysis.sustained_imbalance_periods(sub)
    bottlenecks = bottleneck_detection.get_all_bottlenecks(sub)
    latest_date = sub[config.COL_DATE].max()
    try:
        cutoff = latest_date - pd.Timedelta(days=14)
        recent_sustained = [s for s in sustained if s["end_date"] >= cutoff]
    except Exception:
        recent_sustained = sustained
    if alert_te or alert_de:
        st.warning(
            f"**Efficiency alert:** Current transfer efficiency or discharge effectiveness is below threshold ({config.EFFICIENCY_ALERT_THRESHOLD}). "
            + (f"Transfer efficiency (latest): {te:.4f}. " if pd.notna(te) else "")
            + (f"Discharge effectiveness (latest): {de:.4f}." if pd.notna(de) else "")
        )
    if recent_sustained:
        st.info(f"**Sustained backlog growth:** {len(recent_sustained)} period(s) of >{config.SUSTAINED_IMBALANCE_DAYS} consecutive days of backlog increase detected near the end of the range.")

    # --- KPI cards ---
    st.subheader("Current KPIs (latest date in range)")
    as_of = sub[config.COL_DATE].max().strftime("%Y-%m-%d") if hasattr(sub[config.COL_DATE].max(), "strftime") else str(sub[config.COL_DATE].max())
    st.caption(f"As of {as_of}")
    col1, col2, col3 = st.columns(3)
    with col1:
        val_te = latest.get(config.COL_TRANSFER_EFFICIENCY)
        st.metric(
            "Transfer Efficiency",
            f"{val_te:.4f}" if pd.notna(val_te) else "N/A",
            delta=None,
        )
    with col2:
        val_de = latest.get(config.COL_DISCHARGE_EFFECTIVENESS)
        st.metric(
            "Discharge Effectiveness",
            f"{val_de:.6f}" if pd.notna(val_de) else "N/A",
            delta=None,
        )
    with col3:
        val_thr = latest.get(config.COL_THROUGHPUT)
        st.metric(
            "Pipeline Throughput",
            f"{val_thr:.4f}" if pd.notna(val_thr) else "N/A",
            delta=None,
        )

    # --- Chart: CBP load vs HHS load ---
    st.subheader("CBP load vs HHS load")
    fig_load = make_subplots(specs=[[{"secondary_y": True}]])
    fig_load.add_trace(
        go.Scatter(x=sub[config.COL_DATE], y=sub[config.COL_CBP_LOAD], name="CBP custody", mode="lines"),
        secondary_y=False,
    )
    fig_load.add_trace(
        go.Scatter(x=sub[config.COL_DATE], y=sub[config.COL_HHS_LOAD], name="HHS care", mode="lines"),
        secondary_y=True,
    )
    fig_load.update_xaxes(title_text="Date")
    fig_load.update_yaxes(title_text="CBP load", secondary_y=False)
    fig_load.update_yaxes(title_text="HHS load", secondary_y=True)
    fig_load.update_layout(height=350, margin=dict(l=40, r=40))
    st.plotly_chart(fig_load, use_container_width=True)

    # --- Chart: Transfer & discharge ratios (raw vs rolling toggle) ---
    st.subheader("Transfer efficiency & discharge effectiveness")
    if show_rolling:
        col_te = config.COL_TRANSFER_EFF_7D
        col_de = config.COL_DISCHARGE_EFF_7D
        label_te, label_de = "Transfer efficiency (7d avg)", "Discharge effectiveness (7d avg)"
    else:
        col_te = config.COL_TRANSFER_EFFICIENCY
        col_de = config.COL_DISCHARGE_EFFECTIVENESS
        label_te, label_de = "Transfer efficiency (raw)", "Discharge effectiveness (raw)"
    fig_ratios = go.Figure()
    fig_ratios.add_trace(go.Scatter(x=sub[config.COL_DATE], y=sub[col_te], name=label_te, mode="lines"))
    fig_ratios.add_trace(go.Scatter(x=sub[config.COL_DATE], y=sub[col_de], name=label_de, mode="lines"))
    fig_ratios.update_layout(
        xaxis_title="Date",
        yaxis_title="Ratio",
        height=350,
        margin=dict(l=40, r=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_ratios, use_container_width=True)

    # --- Chart: Cumulative backlogs ---
    st.subheader("Cumulative backlog trends")
    fig_backlog = go.Figure()
    fig_backlog.add_trace(
        go.Scatter(
            x=sub[config.COL_DATE],
            y=sub[config.COL_CUM_CBP_BACKLOG],
            name="Cumulative CBP backlog",
            mode="lines",
        )
    )
    fig_backlog.add_trace(
        go.Scatter(
            x=sub[config.COL_DATE],
            y=sub[config.COL_CUM_HHS_BACKLOG],
            name="Cumulative HHS backlog",
            mode="lines",
        )
    )
    fig_backlog.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative change",
        height=350,
        margin=dict(l=40, r=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_backlog, use_container_width=True)

    # --- Weekday analysis bar chart ---
    st.subheader("Average efficiency by weekday")
    by_weekday = temporal_analysis.efficiency_by_weekday(sub)
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_weekday["day_name"] = by_weekday[config.COL_WEEKDAY].map(lambda i: weekday_names[i] if 0 <= i < 7 else str(i))
    fig_weekday = go.Figure()
    fig_weekday.add_trace(
        go.Bar(
            x=by_weekday["day_name"],
            y=by_weekday["transfer_efficiency_mean"],
            name="Transfer efficiency (mean)",
        )
    )
    fig_weekday.add_trace(
        go.Bar(
            x=by_weekday["day_name"],
            y=by_weekday["discharge_effectiveness_mean"],
            name="Discharge effectiveness (mean)",
        )
    )
    fig_weekday.update_layout(
        barmode="group",
        xaxis_title="Weekday",
        yaxis_title="Mean ratio",
        height=350,
        margin=dict(l=40, r=40),
    )
    st.plotly_chart(fig_weekday, use_container_width=True)

    # --- Month-on-month trend chart ---
    st.subheader("Month-over-month trends")
    mom = temporal_analysis.month_over_month_trends(sub)
    if not mom.empty:
        fig_mom = go.Figure()
        fig_mom.add_trace(
            go.Scatter(
                x=mom["period"],
                y=mom["transfer_efficiency_mean"],
                name="Transfer efficiency (mean)",
                mode="lines+markers",
            )
        )
        fig_mom.add_trace(
            go.Scatter(
                x=mom["period"],
                y=mom["discharge_effectiveness_mean"],
                name="Discharge effectiveness (mean)",
                mode="lines+markers",
            )
        )
        fig_mom.update_layout(
            xaxis_title="Period (YYYY-MM)",
            yaxis_title="Mean ratio",
            height=350,
            margin=dict(l=40, r=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_mom, use_container_width=True)
    else:
        st.caption("Not enough data for month-over-month aggregation.")

    # --- Report generation ---
    st.divider()
    st.subheader("Executive report")
    if st.button("Generate report"):
        date_min_ts = pd.Timestamp(range_min) if hasattr(range_min, "isoformat") else pd.Timestamp(str(range_min))
        date_max_ts = pd.Timestamp(range_max) if hasattr(range_max, "isoformat") else pd.Timestamp(str(range_max))
        report_text = report_generator.generate_full_report(
            df, bottlenecks=bottlenecks, sustained=sustained, date_min=date_min_ts, date_max=date_max_ts
        )
        st.text_area("Report content", report_text, height=400)
        st.download_button(
            "Download report (Markdown)",
            report_text,
            file_name="care_transition_report.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
