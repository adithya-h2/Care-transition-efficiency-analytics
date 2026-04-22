"""
Predictive analytics module for Care Transition Efficiency.
Implements simple moving average / linear regression forecasting.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import config

def generate_forecast(df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """
    Generate a simple forecast for the next `days` days based on the last 30 days of data.
    Forecasts Transfer Efficiency, Cumulative HHS Backlog, and Throughput.
    """
    if df.empty:
        return pd.DataFrame()

    last_date = df[config.COL_DATE].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    
    forecast_df = pd.DataFrame({config.COL_DATE: future_dates})
    hist = df.tail(30).copy()
    
    def predict_series(series_name, allow_negative=False):
        if series_name not in hist.columns:
            return np.zeros(days), np.zeros(days), np.zeros(days)
            
        y = hist[series_name].values
        x = np.arange(len(y))
        
        try:
            mask = ~np.isnan(y)
            if mask.sum() > 2:
                coefs = np.polyfit(x[mask], y[mask], 1)
                slope, intercept = coefs[0], coefs[1]
                future_x = np.arange(len(y), len(y) + days)
                y_pred = future_x * slope + intercept
                
                residuals = y[mask] - (x[mask] * slope + intercept)
                std_err = np.std(residuals) if len(residuals) > 0 else 0
                
                lower = y_pred - (std_err * 1.5)
                upper = y_pred + (std_err * 1.5)
            else:
                last_val = y[-1] if not np.isnan(y[-1]) else 0
                y_pred = np.full(days, last_val)
                lower = y_pred * 0.9
                upper = y_pred * 1.1

        except Exception:
            last_val = y[-1] if len(y) > 0 and not np.isnan(y[-1]) else 0
            y_pred = np.full(days, last_val)
            lower = y_pred * 0.9
            upper = y_pred * 1.1

        if not allow_negative:
            y_pred = np.maximum(0, y_pred)
            lower = np.maximum(0, lower)
            upper = np.maximum(0, upper)
            
        return y_pred, lower, upper

    # Generate predictions
    te_pred, te_lower, te_upper = predict_series(config.COL_TRANSFER_EFFICIENCY)
    hhs_pred, hhs_lower, hhs_upper = predict_series(config.COL_CUM_HHS_BACKLOG, allow_negative=True)
    thr_pred, thr_lower, thr_upper = predict_series(config.COL_THROUGHPUT)
    
    forecast_df["te_forecast"] = np.clip(te_pred, 0, 1) if te_pred is not None else np.zeros(days)
    forecast_df["te_lower"] = np.clip(te_lower, 0, 1) if te_lower is not None else np.zeros(days)
    forecast_df["te_upper"] = np.clip(te_upper, 0, 1) if te_upper is not None else np.zeros(days)
    
    forecast_df["hhs_forecast"] = hhs_pred
    forecast_df["hhs_lower"] = hhs_lower
    forecast_df["hhs_upper"] = hhs_upper
    
    forecast_df["thr_forecast"] = thr_pred
    forecast_df["thr_lower"] = thr_lower
    forecast_df["thr_upper"] = thr_upper
    
    return forecast_df

def get_forecast_insights(forecast_df: pd.DataFrame) -> list:
    """Generate textual interpretation of the forecast."""
    insights = []
    if forecast_df.empty:
        return insights
        
    te_trend = forecast_df["te_forecast"].iloc[-1] - forecast_df["te_forecast"].iloc[0]
    if te_trend < -0.05:
        insights.append("Transfer Efficiency is forecast to **drop**. This could precipitate severe CBP bottlenecks without intervention.")
    elif te_trend > 0.05:
        insights.append("Transfer Efficiency is forecast to **improve** over the next 30 days.")

    hhs_trend = forecast_df["hhs_forecast"].iloc[-1] - forecast_df["hhs_forecast"].iloc[0]
    if hhs_trend > 50:
        insights.append("HHS Backlog shows a distinct **upward trend**. Capacity management may be required soon.")
    
    thr_trend = forecast_df["thr_forecast"].iloc[-1] - forecast_df["thr_forecast"].iloc[0]
    if thr_trend < -0.05:
        insights.append("System throughput is projected to **slow down**, meaning backlog is accumulating at the system level.")
    
    if not insights:
        insights.append("Operational metrics are projected to remain relatively **stable** under current conditions.")
        
    return insights

def create_forecast_figure(hist_df: pd.DataFrame, forecast_df: pd.DataFrame, title: str, 
                           hist_col: str, forecast_col: str, lower_col: str, upper_col: str) -> go.Figure:
    """Creates a line chart with a forecast and confidence band."""
    fig = go.Figure()

    recent_hist = hist_df.tail(60).dropna(subset=[hist_col]) 
    if len(recent_hist) > 0:
        fig.add_trace(go.Scatter(
            x=recent_hist[config.COL_DATE], 
            y=recent_hist[hist_col],
            name="Historical",
            mode="lines",
            line=dict(color='#1f77b4')
        ))

    fig.add_trace(go.Scatter(
        x=pd.concat([forecast_df[config.COL_DATE], forecast_df[config.COL_DATE][::-1]]),
        y=pd.concat([forecast_df[upper_col], forecast_df[lower_col][::-1]]),
        fill='toself',
        fillcolor='rgba(255, 165, 0, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        showlegend=True,
        name="Confidence Band"
    ))

    fig.add_trace(go.Scatter(
        x=forecast_df[config.COL_DATE], 
        y=forecast_df[forecast_col],
        name="Forecast",
        mode="lines",
        line=dict(color='#ff7f0e', dash='dash')
    ))

    fig.update_layout(
        title=f"{title} <br><sup>Exploratory Forecast — not operational prediction</sup>",
        height=350,
        margin=dict(l=40, r=40, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
        template="plotly_white"
    )
    
    return fig
