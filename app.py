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
            """
            **1. Transfer Efficiency**
            - **Formula:** `Transfers / CBP Load`
            - **Meaning:** Measures how quickly children are transferred from CBP custody into HHS care.
            - **Interpretation:** Higher values (closer to 1.0) are better. Low values mean children are spending too much time in initial processing centers.

            **2. Discharge Effectiveness**
            - **Formula:** `Discharges / HHS Load`
            - **Meaning:** Represents the daily rate of successful sponsor placements relative to HHS care load.
            - **Interpretation:** *Low values do NOT necessarily mean failure.* Because HHS care operates as a larger holding system with longer processing times, discharge ratios are naturally small. It indicates the daily outflux speed.

            **3. Pipeline Throughput**
            - **Formula:** `Discharges / Intake`
            - **Meaning:** Measures how effectively the overall pipeline converts intake into successful exits.
            - **Interpretation:** > 1 means the system is clearing backlog. < 1 means the backlog is accumulating at the system level.

            **4. Backlog Accumulation**
            - **Meaning:** The total accumulated surplus or deficit of daily processing.
            - **Interpretation:** If the line trends upwards, operations are creating a bottleneck.
            """
        )

def render_smart_insights(sub, bottlenecks, sustained, df):
    """Render Automated Insights & Recommendations section dynamically."""
    st.subheader("💡 Automated Insights Engine")
    
    total_days = len(sub)
    if total_days == 0:
        return
        
    cbp_growth_days = sum(sub[config.COL_CBP_BACKLOG_CHANGE] > 0)
    cbp_pct = (cbp_growth_days / total_days) * 100
    
    hhs_growth_days = sum(sub[config.COL_HHS_BACKLOG_CHANGE] > 0)
    hhs_pct = (hhs_growth_days / total_days) * 100

    severe_bottlenecks = [b for b in bottlenecks if b["severity"] == "severe"]
    severe_2024 = sum(1 for b in severe_bottlenecks if hasattr(b["start_date"], "year") and b["start_date"].year == 2024)
    
    weekend_weekday = temporal_analysis.weekend_vs_weekday(sub)
    weekend_drop = False
    wd_te = weekend_weekday.get("weekday_transfer_efficiency", 0)
    we_te = weekend_weekday.get("weekend_transfer_efficiency", 0)
    if pd.notna(wd_te) and pd.notna(we_te) and wd_te > 0 and we_te < wd_te:
        weekend_drop = True

    thr_series = sub[config.COL_THROUGHPUT].dropna()
    mid = len(thr_series) // 2
    improving = False
    decreasing_throughput = False
    if mid > 0:
        thr1 = thr_series.iloc[:mid].mean()
        thr2 = thr_series.iloc[mid:].mean()
        if thr2 > thr1:
            improving = True
        elif thr2 < (thr1 * 0.9):
            decreasing_throughput = True

    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### Dynamic Analytical Insights")
        
        st.info(f"📊 **HHS Backlog Increased** on {hhs_pct:.0f}% of observed days. High processing concentration detected.")
        if cbp_pct > 30:
            st.info(f"📊 **CBP Backlog Increased** on {cbp_pct:.0f}% of observed days.")
        
        if severe_2024 > 0:
            st.warning(f"⚠️ **Most severe bottlenecks** occurred during 2024 ({severe_2024} registered incidents).")
            
        te_series = sub[config.COL_TRANSFER_EFFICIENCY].dropna()
        if len(te_series) > 30:
            if te_series.iloc[-30:].mean() < te_series.mean() * 0.8:
                st.error("📉 **Transfer efficiency declined** significantly in the recent period compared to historical average.")
                
        if weekend_drop:
            st.warning("📉 **Weekend discharge/transfer performance is lower** than weekday performance.")

    with cols[1]:
        st.markdown("#### Actionable Recommendations")
        recs = []
        
        if len(severe_bottlenecks) > 0:
             recs.append("🚨 **Severe Constraints Detected:** Recommend **increasing HHS processing capacity** to elevate throughput immediately.")
        if decreasing_throughput:
             recs.append("🔍 **Throughput Declining:** Recommend triggering a full **operational review** of intake vs placement constraints.")
        if weekend_drop:
             recs.append("📅 **Weekend Staffing Offset:** Recommend **weekend staffing adjustments** to align output closer to weekday efficiency.")
        
        if not recs:
            recs.append("✅ **System Nominal:** System is performing within expected margins. Continue standard operating procedures.")
        
        for r in recs:
            if "🚨" in r:
                st.error(r)
            elif "🔍" in r or "📅" in r:
                st.warning(r)
            else:
                st.success(r)

def build_footer():
    """Renders a professional footer."""
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; font-size: 0.9em; opacity: 0.7;">
            <strong>Care Transition Efficiency & Placement Outcome Analytics</strong><br>
            Developed by Adithya N C, Data Science Intern<br>
            <a href="https://github.com/adithya-h2/Care-transition-efficiency-analytics" target="_blank" style="text-decoration: none;">GitHub Repository</a> | Operational Intelligence Platform
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    st.set_page_config(
        page_title="Care Transition Efficiency Analytics",
        layout="wide",
        page_icon="📊"
    )
    
    # Hero Section
    with st.container():
        st.title("📊 Care Transition Efficiency Analytics")
        st.markdown("**Enterprise Dashboard for 3-stage pipeline capacity:** CBP custody → HHS care → Discharge to sponsors.")
        st.markdown(
            "This application provides real-time monitoring, metric intelligence, and predictive capability to ensure "
            "safe and stable throughput of the care network."
        )
    st.divider()

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
        st.header("⚙️ Operational Filters")
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
            
        st.divider()
        st.markdown("**Chart Options**")
        show_rolling = st.checkbox("Apply 7-day smoothing to ratio charts", value=True)

    # Filter by date range
    mask = (df[config.COL_DATE].dt.date >= range_min) & (df[config.COL_DATE].dt.date <= range_max)
    sub = df.loc[mask].copy()
    if sub.empty:
        st.warning("No data in the selected date range. Adjust the filters.")
        return

    # Analytics computations
    sustained = temporal_analysis.sustained_imbalance_periods(sub)
    bottlenecks = bottleneck_detection.get_all_bottlenecks(sub)
    
    # Establish Tabs
    tab_overview, tab_kpi, tab_bottlenecks, tab_forecasting, tab_executive = st.tabs([
        "🔭 Overview & Insights",
        "📈 KPI Deep Dive",
        "⚠️ Bottlenecks",
        "🔮 Predictive Analytics",
        "📄 Executive Summary"
    ])

    # --- TAB: OVERVIEW & INSIGHTS ---
    with tab_overview:
        latest = sub.iloc[-1]
        
        st.subheader("Live Operational KPIs")
        as_of = sub[config.COL_DATE].max().strftime("%Y-%m-%d") if hasattr(sub[config.COL_DATE].max(), "strftime") else str(sub[config.COL_DATE].max())
        st.caption(f"System metrics assessed as of {as_of}")
        
        val_te = latest.get(config.COL_TRANSFER_EFFICIENCY)
        val_de = latest.get(config.COL_DISCHARGE_EFFECTIVENESS)
        val_thr = latest.get(config.COL_THROUGHPUT)
        
        # Determine duration context
        de_series = sub[config.COL_DISCHARGE_EFFECTIVENESS].dropna()
        mean_de = de_series.mean() if len(de_series) > 0 else 0
        est_stay = 1 / mean_de if mean_de > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Transfer Efficiency", 
                f"{val_te:.4f}" if pd.notna(val_te) else "N/A",
                help="Measures how quickly children are transferred from CBP custody into HHS care."
            )
        with col2:
            st.metric(
                "Discharge Effectiveness", 
                f"{val_de:.6f}" if pd.notna(val_de) else "N/A",
                help="Represents the daily rate of successful sponsor placements relative to HHS care load."
            )
        with col3:
            st.metric(
                "Pipeline Throughput", 
                f"{val_thr:.4f}" if pd.notna(val_thr) else "N/A",
                help="Measures how effectively the overall pipeline converts intake into successful exits."
            )
            
        if est_stay > 0:
            st.info(f"⏱️ **Contextual Intelligence:** Average Discharge Effectiveness implies an **estimated HHS processing duration of ~{est_stay:.0f} days**. Low daily discharge effectiveness is structurally expected because HHS population levels are naturally large compared to daily exit bandwidths.")
            
        render_metric_explanations()
        st.divider()
        render_smart_insights(sub, bottlenecks, sustained, df)

    # --- TAB: KPI DEEP DIVE ---
    with tab_kpi:
        st.subheader("Custody Density Over Time")
        fig_load = make_subplots(specs=[[{"secondary_y": True}]])
        clean_cbp = sub.dropna(subset=[config.COL_CBP_LOAD, config.COL_DATE])
        clean_hhs = sub.dropna(subset=[config.COL_HHS_LOAD, config.COL_DATE])
        
        fig_load.add_trace(go.Scatter(x=clean_cbp[config.COL_DATE], y=clean_cbp[config.COL_CBP_LOAD], name="CBP Custody Volume", mode="lines", line=dict(color="#1f77b4")), secondary_y=False)
        fig_load.add_trace(go.Scatter(x=clean_hhs[config.COL_DATE], y=clean_hhs[config.COL_HHS_LOAD], name="HHS Care Volume", mode="lines", line=dict(color="#ff7f0e")), secondary_y=True)
        fig_load.update_layout(height=400, margin=dict(l=40, r=40), hovermode="x unified", title="Relative System Load Levels")
        st.plotly_chart(fig_load, use_container_width=True)

        st.divider()
        st.subheader("Transfer Efficiency & Effectiveness Momentum")
        
        if show_rolling:
            col_te = config.COL_TRANSFER_EFF_7D
            col_de = config.COL_DISCHARGE_EFF_7D
            label_te, label_de = "Transfer Efficiency (7d avg)", "Discharge Effectiveness (7d avg)"
        else:
            col_te = config.COL_TRANSFER_EFFICIENCY
            col_de = config.COL_DISCHARGE_EFFECTIVENESS
            label_te, label_de = "Transfer Efficiency (Raw)", "Discharge Effectiveness (Raw)"
            
        clean_ratios = sub.dropna(subset=[col_te, col_de, config.COL_DATE], how='all')
        fig_ratios = go.Figure()
        fig_ratios.add_trace(go.Scatter(x=clean_ratios[config.COL_DATE], y=clean_ratios[col_te], name=label_te, mode="lines"))
        fig_ratios.add_trace(go.Scatter(x=clean_ratios[config.COL_DATE], y=clean_ratios[col_de], name=label_de, mode="lines"))
        fig_ratios.update_layout(xaxis_title="Date", yaxis_title="Ratio", height=400, margin=dict(l=40, r=40), legend=dict(orientation="h", yanchor="bottom", y=1.02), hovermode="x unified")
        st.plotly_chart(fig_ratios, use_container_width=True)
        
        st.divider()
        cols = st.columns(2)
        with cols[0]:
            st.subheader("Lifecycle Distribution (Weekday)")
            by_weekday = temporal_analysis.efficiency_by_weekday(sub)
            weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            by_weekday["day_name"] = by_weekday[config.COL_WEEKDAY].map(lambda i: weekday_names[i] if 0 <= i < 7 else str(i))
            fig_weekday = go.Figure()
            fig_weekday.add_trace(go.Bar(x=by_weekday["day_name"], y=by_weekday["transfer_efficiency_mean"], name="Mean Transfer Efficiency"))
            fig_weekday.add_trace(go.Bar(x=by_weekday["day_name"], y=by_weekday["discharge_effectiveness_mean"], name="Mean Discharge Effectiveness"))
            fig_weekday.update_layout(barmode="group", height=350, margin=dict(l=40, r=40, t=10), title="Throughput by Day of Week")
            st.plotly_chart(fig_weekday, use_container_width=True)

        with cols[1]:
            st.subheader("Seasonal Velocity (Monthly)")
            mom = temporal_analysis.month_over_month_trends(sub)
            if not mom.empty:
                fig_mom = go.Figure()
                fig_mom.add_trace(go.Scatter(x=mom["period"], y=mom["transfer_efficiency_mean"], name="Mean Transfer Efficiency", mode="lines+markers"))
                fig_mom.add_trace(go.Scatter(x=mom["period"], y=mom["discharge_effectiveness_mean"], name="Mean Discharge Effectiveness", mode="lines+markers"))
                fig_mom.update_layout(height=350, margin=dict(l=40, r=40, t=10), hovermode="x unified", title="Month-over-month Efficiency Profile")
                st.plotly_chart(fig_mom, use_container_width=True)
            else:
                st.caption("Insufficient chronological breadth for monthly plotting.")

    # --- TAB: BOTTLENECKS ---
    with tab_bottlenecks:
        st.subheader("System Constraint Detection")
        st.markdown("Automated detection of cumulative structural backlogs via severe operational deceleration periods.")
        
        clean_backlog = sub.dropna(subset=[config.COL_CUM_CBP_BACKLOG, config.COL_CUM_HHS_BACKLOG, config.COL_DATE], how='all')
        fig_backlog = go.Figure()
        fig_backlog.add_trace(go.Scatter(x=clean_backlog[config.COL_DATE], y=clean_backlog[config.COL_CUM_CBP_BACKLOG], name="Cumulative CBP Backlog Surplus", mode="lines"))
        fig_backlog.add_trace(go.Scatter(x=clean_backlog[config.COL_DATE], y=clean_backlog[config.COL_CUM_HHS_BACKLOG], name="Cumulative HHS Backlog Surplus", mode="lines"))
        
        # Annotate severe bottlenecks
        severe_bs = [b for b in bottlenecks if b["severity"] == "severe"]
        for b in severe_bs:
            fig_backlog.add_vrect(
                x0=b["start_date"], x1=b["end_date"],
                fillcolor="rgba(255,0,0,0.1)", opacity=1,
                layer="below", line_width=0,
                annotation_text="Severe Constraint Triggered",
                annotation_position="top left",
                annotation_font_color="red"
            )
            
        fig_backlog.update_layout(xaxis_title="Date Range", yaxis_title="Variance Density", height=500, margin=dict(l=40, r=40), legend=dict(orientation="h", yanchor="bottom", y=1.02), hovermode="x unified")
        st.plotly_chart(fig_backlog, use_container_width=True)

    # --- TAB: FORECASTING ---
    with tab_forecasting:
        st.subheader("30-Day Extrapolative Projection Horizon")
        st.markdown("Utilizing recent moving linear gradients to project near-term operational strain.")
        
        with st.spinner("Generating 30-day lightweight forecasts..."):
            forecast_df = forecasting.generate_forecast(df, days=30)
            insights = forecasting.get_forecast_insights(forecast_df)
            
        if not forecast_df.empty:
            for insight in insights:
                st.info(f"💡 {insight}")
                
            fig_te = forecasting.create_forecast_figure(
                df, forecast_df, "Transfer Efficiency Extrapolation", config.COL_TRANSFER_EFFICIENCY, 
                "te_forecast", "te_lower", "te_upper"
            )
            st.plotly_chart(fig_te, use_container_width=True)
            
            cols = st.columns(2)
            with cols[0]:
                fig_hhs = forecasting.create_forecast_figure(
                    df, forecast_df, "Cumulative HHS Backlog Trajectory", config.COL_CUM_HHS_BACKLOG, 
                    "hhs_forecast", "hhs_lower", "hhs_upper"
                )
                st.plotly_chart(fig_hhs, use_container_width=True)
                
            with cols[1]:
                fig_thr = forecasting.create_forecast_figure(
                    df, forecast_df, "System Throughput Projection", config.COL_THROUGHPUT, 
                    "thr_forecast", "thr_lower", "thr_upper"
                )
                st.plotly_chart(fig_thr, use_container_width=True)
        else:
            st.error("Insufficient dataset depth to plot statistical forecasts.")

    # --- TAB: EXECUTIVE SUMMARY ---
    with tab_executive:
        st.subheader("Automated Stakeholder Summary")
        st.markdown("Generates a data-driven document summarizing high-level findings, key risks, operational interpretation, and actionable recommendations suitable for distribution.")
        if st.button("Generate Executive Document", type="primary"):
            date_min_ts = pd.Timestamp(range_min) if hasattr(range_min, "isoformat") else pd.Timestamp(str(range_min))
            date_max_ts = pd.Timestamp(range_max) if hasattr(range_max, "isoformat") else pd.Timestamp(str(range_max))
            
            with st.spinner("Compiling tactical documentation..."):
                report_text = report_generator.generate_full_report(
                    df, bottlenecks=bottlenecks, sustained=sustained, date_min=date_min_ts, date_max=date_max_ts
                )
            
            st.download_button("↓ Download Report (Markdown)", report_text, file_name="executive_summary.md", mime="text/markdown")
            
            st.markdown("### Report Render")
            st.markdown(report_text) # Render it cleanly in the UI for a better feel!
            
    build_footer()

if __name__ == "__main__":
    main()
