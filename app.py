"""
Streamlit dashboard for Care Transition Efficiency & Placement Outcome Analytics.
Orchestrates data_loader, metrics, temporal_analysis, bottleneck_detection, report_generator, and forecasting.
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
import forecasting


@st.cache_data
def load_and_prepare():
    """Load data, compute metrics, add temporal columns. Cached."""
    df = data_loader.load_data()
    df = metrics.compute_all_metrics(df)
    df = temporal_analysis.get_temporal_dataframe(df)
    return df


def render_metric_explanations():
    """Render the 'Understanding the Metrics' section."""
    with st.expander("ℹ️ Understanding the Metrics", expanded=False):
        st.markdown(
            \"\"\"
            **1. Transfer Efficiency**
            - **Formula:** `Transfers / CBP Load`
            - **Meaning:** Shows the daily rate at which children are moved out of CBP facilities.
            - **Interpretation:** Higher values (closer to 1.0) are better. Low values mean children are spending too much time in initial processing centers.

            **2. Discharge Effectiveness**
            - **Formula:** `Discharges / HHS Load`
            - **Meaning:** Measures how quickly children leave HHS care relative to the total number of children currently in HHS care.
            - **Interpretation:** *Low values do NOT necessarily mean failure.* Because HHS care operates as a larger holding system with longer processing times, discharge ratios are naturally small. It indicates the daily outflux speed.

            **3. Pipeline Throughput**
            - **Formula:** `Discharges / Intake`
            - **Meaning:** Shows if the system as a whole is keeping up with new arrivals.
            - **Interpretation:** > 1 means the backlog is shrinking. < 1 means the backlog is growing.

            **4. Backlog Accumulation**
            - **Meaning:** The total accumulated surplus or deficit of daily processing.
            - **Interpretation:** If the line trends upwards, operations are creating a bottleneck.
            \"\"\"
        )


def render_smart_insights(sub, bottlenecks, sustained):
    """Render Automated Insights & Recommendations section."""
    st.subheader("💡 Automated Insights & Recommendations")
    
    total_days = len(sub)
    if total_days == 0:
        return
        
    cbp_growth_days = sum(sub[config.COL_CBP_BACKLOG_CHANGE] > 0)
    cbp_pct = (cbp_growth_days / total_days) * 100
    
    hhs_growth_days = sum(sub[config.COL_HHS_BACKLOG_CHANGE] > 0)
    hhs_pct = (hhs_growth_days / total_days) * 100
    
    # Generate insights
    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### System Insights")
        if hhs_pct > 30:
            st.warning(f"📈 **HHS Backlog Increased** on {hhs_pct:.0f}% of observed days. High processing concentration detected.")
        else:
            st.success(f"✅ **HHS Backlog Stable**: Increased on only {hhs_pct:.0f}% of days.")
            
        if cbp_pct > 30:
            st.warning(f"📈 **CBP Backlog Increased** on {cbp_pct:.0f}% of observed days.")
            
        if severe_bottlenecks := sum(1 for b in bottlenecks if b["severity"] == "severe"):
            st.error(f"🚨 **Severe Bottlenecks**: {severe_bottlenecks} critical constraints detected during the selected period.")
            
    with cols[1]:
        st.markdown("#### Actionable Recommendations")
        recs = []
        if hhs_pct > 30:
            recs.append("- **Increase sponsor processing capacity** to accelerate HHS discharge effectiveness.")
        if cbp_pct > 30:
            recs.append("- **Improve transfer coordination** from CBP to HHS facilities.")
        if len(sustained) > 0:
            recs.append("- **Trigger an operational review** to address sustained low throughput periods.")
        if not recs:
            recs.append("- System is performing within expected margins. Continue current standard operating procedures.")
        
        for r in recs:
            st.markdown(r)
            

def main():
    st.set_page_config(
        page_title="Care Transition Efficiency Analytics",
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
        st.header("⚙️ Filters & Options")
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

    # Analytics computations
    sustained = temporal_analysis.sustained_imbalance_periods(sub)
    bottlenecks = bottleneck_detection.get_all_bottlenecks(sub)
    
    # Organize layout
    tab_overview, tab_kpi, tab_bottlenecks, tab_forecasting, tab_executive = st.tabs([
        "📊 Overview & Insights",
        "📈 KPI Analysis",
        "⚠️ Bottlenecks",
        "🔮 Forecasting",
        "📄 Executive Summary"
    ])

    # --- TAB: OVERVIEW & INSIGHTS ---
    with tab_overview:
        latest = sub.iloc[-1]
        
        # Alerts
        te = latest.get(config.COL_TRANSFER_EFFICIENCY)
        de = latest.get(config.COL_DISCHARGE_EFFECTIVENESS)
        alert_te = pd.notna(te) and te < config.EFFICIENCY_ALERT_THRESHOLD
        alert_de = pd.notna(de) and de < config.EFFICIENCY_ALERT_THRESHOLD
        
        if alert_te or alert_de:
            st.error(
                f"**Efficiency Alert:** Current transfer efficiency or discharge effectiveness is below threshold ({config.EFFICIENCY_ALERT_THRESHOLD})."
            )

        st.subheader("Current KPIs")
        as_of = sub[config.COL_DATE].max().strftime("%Y-%m-%d") if hasattr(sub[config.COL_DATE].max(), "strftime") else str(sub[config.COL_DATE].max())
        st.caption(f"Latest data as of {as_of}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            val_te = latest.get(config.COL_TRANSFER_EFFICIENCY)
            st.metric("Transfer Efficiency", f"{val_te:.4f}" if pd.notna(val_te) else "N/A")
        with col2:
            val_de = latest.get(config.COL_DISCHARGE_EFFECTIVENESS)
            st.metric("Discharge Effectiveness", f"{val_de:.6f}" if pd.notna(val_de) else "N/A")
        with col3:
            val_thr = latest.get(config.COL_THROUGHPUT)
            st.metric("Pipeline Throughput", f"{val_thr:.4f}" if pd.notna(val_thr) else "N/A")
        with col4:
            # Contextual Discharge Validation
            de_series = sub[config.COL_DISCHARGE_EFFECTIVENESS].dropna()
            mean_de = de_series.mean() if len(de_series) > 0 else 0
            if mean_de > 0:
                est_stay = 1 / mean_de
                st.metric("Estimated HHS Stay", f"~{est_stay:.0f} Days")
            else:
                st.metric("Estimated HHS Stay", "N/A")
                
        st.divider()
        if mean_de > 0:
            avg_historical_de = df[config.COL_DISCHARGE_EFFECTIVENESS].mean()
            if mean_de < (avg_historical_de * 0.7):
                st.warning(f"⚠️ **Note:** Discharge Effectiveness is significantly below the historical average. Current metric implies an estimated average HHS stay of approximately **{est_stay:.0f} days**.")

        render_metric_explanations()
        st.divider()
        render_smart_insights(sub, bottlenecks, sustained)

    # --- TAB: KPI ANALYSIS ---
    with tab_kpi:
        st.subheader("CBP Load vs HHS Load")
        fig_load = make_subplots(specs=[[{"secondary_y": True}]])
        fig_load.add_trace(go.Scatter(x=sub[config.COL_DATE], y=sub[config.COL_CBP_LOAD], name="CBP custody", mode="lines", line=dict(color="#1f77b4")), secondary_y=False)
        fig_load.add_trace(go.Scatter(x=sub[config.COL_DATE], y=sub[config.COL_HHS_LOAD], name="HHS care", mode="lines", line=dict(color="#ff7f0e")), secondary_y=True)
        fig_load.update_layout(height=400, margin=dict(l=40, r=40), title="Relative Custody Distribution Over Time", hovermode="x unified")
        st.plotly_chart(fig_load, use_container_width=True)

        st.subheader("Efficiency & Effectiveness Trends")
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
        fig_ratios.update_layout(xaxis_title="Date", yaxis_title="Ratio", height=400, margin=dict(l=40, r=40), legend=dict(orientation="h", yanchor="bottom", y=1.02), hovermode="x unified")
        st.plotly_chart(fig_ratios, use_container_width=True)
        
        cols = st.columns(2)
        with cols[0]:
            st.subheader("Weekday Efficiency")
            by_weekday = temporal_analysis.efficiency_by_weekday(sub)
            weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            by_weekday["day_name"] = by_weekday[config.COL_WEEKDAY].map(lambda i: weekday_names[i] if 0 <= i < 7 else str(i))
            fig_weekday = go.Figure()
            fig_weekday.add_trace(go.Bar(x=by_weekday["day_name"], y=by_weekday["transfer_efficiency_mean"], name="Transfer Efficiency"))
            fig_weekday.add_trace(go.Bar(x=by_weekday["day_name"], y=by_weekday["discharge_effectiveness_mean"], name="Discharge Effectiveness"))
            fig_weekday.update_layout(barmode="group", height=350, margin=dict(l=40, r=40, t=10))
            st.plotly_chart(fig_weekday, use_container_width=True)

        with cols[1]:
            st.subheader("Monthly Trends")
            mom = temporal_analysis.month_over_month_trends(sub)
            if not mom.empty:
                fig_mom = go.Figure()
                fig_mom.add_trace(go.Scatter(x=mom["period"], y=mom["transfer_efficiency_mean"], name="Transfer Efficiency", mode="lines+markers"))
                fig_mom.add_trace(go.Scatter(x=mom["period"], y=mom["discharge_effectiveness_mean"], name="Discharge Effectiveness", mode="lines+markers"))
                fig_mom.update_layout(height=350, margin=dict(l=40, r=40, t=10), hovermode="x unified")
                st.plotly_chart(fig_mom, use_container_width=True)
            else:
                st.caption("Not enough data for month-over-month aggregation.")

    # --- TAB: BOTTLENECKS ---
    with tab_bottlenecks:
        st.subheader("Cumulative Backlog Overview & Constraints")
        st.markdown("Visual highlighting of periods where systemic constraints caused significant backlog increases.")
        
        fig_backlog = go.Figure()
        fig_backlog.add_trace(go.Scatter(x=sub[config.COL_DATE], y=sub[config.COL_CUM_CBP_BACKLOG], name="Cumulative CBP Backlog", mode="lines"))
        fig_backlog.add_trace(go.Scatter(x=sub[config.COL_DATE], y=sub[config.COL_CUM_HHS_BACKLOG], name="Cumulative HHS Backlog", mode="lines"))
        
        # Annotate severe bottlenecks
        severe_bs = [b for b in bottlenecks if b["severity"] == "severe"]
        for b in severe_bs:
            fig_backlog.add_vrect(
                x0=b["start_date"], x1=b["end_date"],
                fillcolor="red", opacity=0.15,
                layer="below", line_width=0,
                annotation_text="Severe Constraint",
                annotation_position="top left"
            )
            
        fig_backlog.update_layout(xaxis_title="Date", yaxis_title="Cumulative Change", height=500, margin=dict(l=40, r=40), legend=dict(orientation="h", yanchor="bottom", y=1.02), hovermode="x unified")
        st.plotly_chart(fig_backlog, use_container_width=True)
        
        if severe_bs:
            st.warning(f"Found {len(severe_bs)} severe bottleneck periods in the selected timestamp.")
        else:
            st.success("No severe bottlenecks detected in this range.")

    # --- TAB: FORECASTING ---
    with tab_forecasting:
        st.subheader("14-Day Predictive Analytics")
        st.markdown("Based on recent historical trends.")
        
        with st.spinner("Generating forecasts..."):
            forecast_df = forecasting.generate_forecast(df, days=14)
            insights = forecasting.get_forecast_insights(forecast_df)
            
        if not forecast_df.empty:
            for insight in insights:
                st.info(f"💡 {insight}")
                
            fig_cbp = forecasting.create_forecast_figure(
                df, forecast_df, "CBP Load Forecast", config.COL_CBP_LOAD, 
                "cbp_load_forecast", "cbp_load_lower", "cbp_load_upper"
            )
            st.plotly_chart(fig_cbp, use_container_width=True)
            
            cols = st.columns(2)
            with cols[0]:
                fig_hhs = forecasting.create_forecast_figure(
                    df, forecast_df, "HHS Load Forecast", config.COL_HHS_LOAD, 
                    "hhs_load_forecast", "hhs_load_lower", "hhs_load_upper"
                )
                st.plotly_chart(fig_hhs, use_container_width=True)
                
            with cols[1]:
                fig_te = forecasting.create_forecast_figure(
                    df, forecast_df, "Transfer Efficiency Forecast", config.COL_TRANSFER_EFFICIENCY, 
                    "te_forecast", "te_lower", "te_upper"
                )
                st.plotly_chart(fig_te, use_container_width=True)
        else:
            st.error("Insufficient data to generate forecasts.")

    # --- TAB: EXECUTIVE SUMMARY ---
    with tab_executive:
        st.subheader("Automated Executive Report")
        st.markdown("Generate a data-driven, comprehensive Markdown report tailored for operational leaders.")
        if st.button("Generate Full Report"):
            date_min_ts = pd.Timestamp(range_min) if hasattr(range_min, "isoformat") else pd.Timestamp(str(range_min))
            date_max_ts = pd.Timestamp(range_max) if hasattr(range_max, "isoformat") else pd.Timestamp(str(range_max))
            
            with st.spinner("Compiling analysis..."):
                report_text = report_generator.generate_full_report(
                    df, bottlenecks=bottlenecks, sustained=sustained, date_min=date_min_ts, date_max=date_max_ts
                )
            
            st.markdown("### Report Preview")
            st.text_area("Content", report_text, height=500, label_visibility="collapsed")
            st.download_button("Download Report (Markdown)", report_text, file_name="care_transition_report.md", mime="text/markdown")

if __name__ == "__main__":
    main()
