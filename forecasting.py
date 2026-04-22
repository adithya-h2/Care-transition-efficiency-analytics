"""
Predictive analytics module for Care Transition Efficiency.
Implements lightweight forecasting using linear regression and moving constants.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import config

def generate_forecast(df: pd.DataFrame, days: int = 14) -> pd.DataFrame:
    """
    Generate a simple forecast for the next `days` days based on the last 30 days of data.
    Forecasts CBP Load, HHS Load, and Transfer Efficiency.
    """
    if df.empty:
        return pd.DataFrame()

    last_date = df[config.COL_DATE].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    
    forecast_df = pd.DataFrame({config.COL_DATE: future_dates})
    
    # Use last 30 days for trend
    hist = df.tail(30).copy()
    
    def predict_series(series_name, allow_negative=False):
        if series_name not in hist.columns:
            return np.zeros(days), np.zeros(days), np.zeros(days)
            
        y = hist[series_name].values
        x = np.arange(len(y))
        
        # Simple linear fit
        try:
            mask = ~np.isnan(y)
            if mask.sum() > 2:
                coefs = np.polyfit(x[mask], y[mask], 1)
                slope, intercept = coefs[0], coefs[1]
                
                # Predict next `days`
                future_x = np.arange(len(y), len(y) + days)
                y_pred = future_x * slope + intercept
                
                # Confidence intervals based on std error residuals
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
    cbp_pred, cbp_lower, cbp_upper = predict_series(config.COL_CBP_LOAD)
    hhs_pred, hhs_lower, hhs_upper = predict_series(config.COL_HHS_LOAD)
    te_pred, te_lower, te_upper = predict_series(config.COL_TRANSFER_EFFICIENCY)
    
    forecast_df["cbp_load_forecast"] = cbp_pred
    forecast_df["cbp_load_lower"] = cbp_lower
    forecast_df["cbp_load_upper"] = cbp_upper
    
    forecast_df["hhs_load_forecast"] = hhs_pred
    forecast_df["hhs_load_lower"] = hhs_lower
    forecast_df["hhs_load_upper"] = hhs_upper
    
    forecast_df["te_forecast"] = np.clip(te_pred, 0, 1) if te_pred is not None else np.zeros(days)
    forecast_df["te_lower"] = np.clip(te_lower, 0, 1) if te_lower is not None else np.zeros(days)
    forecast_df["te_upper"] = np.clip(te_upper, 0, 1) if te_upper is not None else np.zeros(days)
    
    return forecast_df

def get_forecast_insights(forecast_df: pd.DataFrame) -> list:
    """Generate textual interpretation of the forecast."""
    insights = []
    if forecast_df.empty:
        return insights
        
    cbp_trend = forecast_df["cbp_load_forecast"].iloc[-1] - forecast_df["cbp_load_forecast"].iloc[0]
    if cbp_trend > 10:
        insights.append("CBP Load is projected to **increase** over the next 14 days, indicating rising operational pressure at intake.")
    elif cbp_trend < -10:
        insights.append("CBP Load is projected to **decrease**, suggesting some clearing of the intake backlog.")

    hhs_trend = forecast_df["hhs_load_forecast"].iloc[-1] - forecast_df["hhs_load_forecast"].iloc[0]
    if hhs_trend > 20:
        insights.append("HHS Load shows a distinct **upward trend**. Capacity management may be required soon.")
    
    te_trend = forecast_df["te_forecast"].iloc[-1] - forecast_df["te_forecast"].iloc[0]
    if te_trend < -0.05:
        insights.append("Transfer Efficiency is forecast to **drop**. This could precipitate severe CBP bottlenecks without intervention.")
    
    if not insights:
        insights.append("Operational metrics are projected to remain relatively **stable** under current conditions.")
        
    return insights

def create_forecast_figure(hist_df: pd.DataFrame, forecast_df: pd.DataFrame, title: str, 
                           hist_col: str, forecast_col: str, lower_col: str, upper_col: str) -> go.Figure:
    """Creates a line chart with a forecast and confidence band."""
    fig = go.Figure()

    # Historical Data
    recent_hist = hist_df.tail(60) # Show last 60 days of history for context
    fig.add_trace(go.Scatter(
        x=recent_hist[config.COL_DATE], 
        y=recent_hist[hist_col],
        name="Historical",
        mode="lines",
        line=dict(color='blue')
    ))

    # Forecast Confidence Band
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

    # Forecast Line
    fig.add_trace(go.Scatter(
        x=forecast_df[config.COL_DATE], 
        y=forecast_df[forecast_col],
        name="Forecast",
        mode="lines",
        line=dict(color='orange', dash='dash')
    ))

    fig.update_layout(
        title=title,
        height=350,
        margin=dict(l=40, r=40, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
        template="plotly_dark" # Streamlit handles theme usually, but this falls back cleanly
    )
    
    return fig
