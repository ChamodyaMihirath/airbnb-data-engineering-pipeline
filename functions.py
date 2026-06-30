import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# Thematic Color Constants
COLOR_PRIMARY = "#185FA5"  # Corporate Blue
COLOR_SUCCESS = "#1D9E75"  # Corporate Emerald
COLOR_WARNING = "#BA7517"  # Corporate Amber
COLOR_DANGER = "#A32D2D"   # Warning/Danger Red
COLOR_NEUTRAL = "#1e293b"  # Charcoal text
COLOR_BG_WHITE = "#ffffff"
COLOR_MUTED = "#64748b"    # Muted Slate

def apply_custom_css():
    """
    Injects custom executive styling stylesheets into the page.
    """
    try:
        with open("assets/style.css", "r") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except Exception:
        pass

def render_header(title, subtitle):
    """
    Renders a consistent corporate header with clean margins.
    """
    apply_custom_css()
    st.markdown(
        f"""
        <div style="margin-bottom: 25px;">
            <h1 style="color: {COLOR_PRIMARY}; font-size: 2.2rem; font-weight: 700; margin: 0 0 5px 0;">{title}</h1>
            <p style="color: {COLOR_MUTED}; font-size: 1.05rem; font-weight: 400; margin: 0;">{subtitle}</p>
            <hr style="border: 0; height: 1px; background: #e2e8f0; margin: 15px 0 0 0;">
        </div>
        """,
        unsafe_allow_html=True
    )

def kpi_card(title, value, subtext="", trend="up"):
    """
    Generates a premium, responsive rounded HTML KPI Card with hover shading.
    """
    trend_color = COLOR_SUCCESS if trend == "up" else COLOR_DANGER
    trend_arrow = "▲" if trend == "up" else "▼"
    subtext_html = f"<div style='color: {trend_color}; font-size: 0.8rem; font-weight: 600; margin-top: 4px;'>{trend_arrow} {subtext}</div>" if subtext else ""
    
    card_html = f"""
    <div style="
        background-color: {COLOR_BG_WHITE}; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04); 
        border: 1px solid #e2e8f0; 
        text-align: center;
        margin-bottom: 15px;
        transition: transform 0.2s ease-in-out;
    ">
        <div style="color: {COLOR_MUTED}; font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{title}</div>
        <div style="color: {COLOR_PRIMARY}; font-size: 2.1rem; font-weight: 700; margin-top: 8px; line-height: 1.1;">{value}</div>
        {subtext_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def apply_chart_theme(fig, height=350):
    """
    Applies our strict executive minimal styling to any Plotly figure.
    """
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_family="Inter, system-ui, -apple-system, sans-serif",
        font_color=COLOR_NEUTRAL,
        title_font_size=16,
        title_font_color=COLOR_PRIMARY,
        title_font_family="Inter, system-ui, -apple-system, sans-serif",
        margin=dict(l=40, r=20, t=50, b=40),
        height=height,
        hovermode="closest"
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#f1f5f9',
        linecolor='#cbd5e1',
        tickfont=dict(color=COLOR_MUTED)
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#f1f5f9',
        linecolor='#cbd5e1',
        tickfont=dict(color=COLOR_MUTED)
    )
    return fig

# --- Page 1 Visualization Helpers ---

def plot_price_distribution(df):
    """
    Plots the price distribution histogram.
    """
    # Clip prices at 95th percentile to avoid extremely long tails
    max_price = df['price'].quantile(0.95)
    clipped_df = df[df['price'] <= max_price]
    
    fig = px.histogram(
        clipped_df, 
        x="price", 
        nbins=40,
        color_discrete_sequence=[COLOR_PRIMARY],
        labels={"price": "Nightly Price (€)", "count": "Listings"},
        title="Listing Prices (Clipped at 95th Percentile)",
        opacity=0.85
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig)

def plot_occupancy_distribution(df):
    """
    Plots the occupancy rate distribution histogram.
    """
    fig = px.histogram(
        df, 
        x="occupancy_rate", 
        nbins=30,
        color_discrete_sequence=[COLOR_SUCCESS],
        labels={"occupancy_rate": "Occupancy Rate", "count": "Listings"},
        title="Listing Occupancy Rates",
        opacity=0.85
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickformat=".0%")
    return apply_chart_theme(fig)

def plot_rating_distribution(df):
    """
    Plots the review rating score distribution histogram.
    """
    # Filter listings that have ratings
    rated_df = df[df['review_scores_rating'] > 0]
    
    fig = px.histogram(
        rated_df, 
        x="review_scores_rating", 
        nbins=25,
        color_discrete_sequence=[COLOR_WARNING],
        labels={"review_scores_rating": "Average Rating (out of 5)", "count": "Listings"},
        title="Review Rating Score Distribution",
        opacity=0.85
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig)

# --- Page 2 Visualization Helpers ---

def plot_listings_map(df):
    """
    Creates an interactive Mapbox plot mapping Amsterdam Airbnbs.
    Marker color maps to price, marker size maps to occupancy.
    """
    if df.empty:
        # Fallback empty map
        fig = go.Figure(go.Scattermapbox())
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=10,
            mapbox_center={"lat": 52.3676, "lon": 4.9041},
            title="No Listing Coordinates Fit the Filters"
        )
        return apply_chart_theme(fig)
        
    # Scale price color for clean mapping (clip colors at 95th percentile price)
    max_price = df['price'].quantile(0.95)
    color_scale_max = max(50.0, max_price)
    
    # Calculate a sizing column: minimum size is 3, maximum is 15 based on occupancy
    sizes = df['occupancy_rate'].fillna(0.0).clip(0, 1) * 12 + 3
    
    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        color="price",
        size=sizes,
        color_continuous_scale=px.colors.sequential.Plotly3,
        range_color=[0, color_scale_max],
        zoom=11,
        mapbox_style="carto-positron",
        title="Amsterdam Listing Matrix Map",
        hover_name="id",
        hover_data={
            "neighbourhood_cleansed": True,
            "room_type": True,
            "price": ":.2f",
            "review_scores_rating": ":.2f",
            "occupancy_rate": ":.1%"
        },
        height=500
    )
    
    # Clean map center coordinates
    map_center = {"lat": df["latitude"].median(), "lon": df["longitude"].median()}
    fig.update_layout(
        mapbox_center=map_center,
        coloraxis_colorbar=dict(title="Nightly Price (€)", thickness=15),
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def plot_neighbourhood_bar(df, title, ascending=False):
    """
    Plots average pricing by neighbourhood.
    """
    grouped = df.groupby('neighbourhood_cleansed')['price'].median().reset_index()
    grouped = grouped.sort_values(by='price', ascending=ascending).head(10)
    
    fig = px.bar(
        grouped,
        x="price",
        y="neighbourhood_cleansed",
        orientation="h",
        color="price",
        color_continuous_scale="Blues" if ascending else "Reds",
        labels={"price": "Median Price (€)", "neighbourhood_cleansed": "Neighbourhood"},
        title=title
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    fig.update_yaxes(categoryorder="total ascending" if ascending else "total descending")
    return apply_chart_theme(fig)

# --- Page 3 Visualization Helpers ---

def plot_host_segments(df):
    """
    Host segment share distribution.
    """
    grouped = df['host_segment'].value_counts().reset_index()
    grouped.columns = ['Segment', 'Count']
    
    fig = px.pie(
        grouped,
        names="Segment",
        values="Count",
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER],
        title="Host Segmentation Share"
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return apply_chart_theme(fig)

def plot_host_metrics(df, group_by_col="host_segment", y_col="occupancy_rate", title="Occupancy Rate by Segment", is_pct=True):
    """
    Plots averages of continuous metrics by host features.
    """
    grouped = df.groupby(group_by_col)[y_col].mean().reset_index()
    
    fig = px.bar(
        grouped,
        x=group_by_col,
        y=y_col,
        color=group_by_col,
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER],
        labels={y_col: y_col.replace('_', ' ').title(), group_by_col: group_by_col.replace('_', ' ').title()},
        title=title
    )
    fig.update_layout(showlegend=False)
    if is_pct:
        fig.update_yaxes(tickformat=".0%")
    return apply_chart_theme(fig)

# --- Page 4 Visualization Helpers ---

def plot_bar_group(df, x_col, y_col="price", title="Median Price by Feature", agg="median"):
    """
    Reusable bar chart for category analysis.
    """
    if agg == "median":
        grouped = df.groupby(x_col)[y_col].median().reset_index()
    else:
        grouped = df.groupby(x_col)[y_col].mean().reset_index()
        
    fig = px.bar(
        grouped,
        x=x_col,
        y=y_col,
        color_discrete_sequence=[COLOR_PRIMARY],
        title=title
    )
    fig.update_layout(showlegend=False)
    return apply_chart_theme(fig)

def plot_scatter_relation(df, x_col, y_col="price", title="Price relationship"):
    """
    Reusable scatter chart showing trends between variables.
    """
    # Sample data to avoid sluggish plotting
    sample_df = df.sample(min(2000, len(df)), random_state=42) if len(df) > 2000 else df.copy()
    
    # Apply reasonable clipping
    if y_col == "price":
        sample_df = sample_df[sample_df['price'] <= sample_df['price'].quantile(0.95)]
        
    fig = px.scatter(
        sample_df,
        x=x_col,
        y=y_col,
        trendline="ols",
        trendline_color_override=COLOR_DANGER,
        color_discrete_sequence=[COLOR_PRIMARY],
        opacity=0.4,
        title=title
    )
    return apply_chart_theme(fig)

def plot_correlation_heatmap(df):
    """
    Plots correlation coefficients between continuous variables.
    """
    num_cols = [
        'price', 'accommodates', 'bedrooms', 'bathrooms', 'beds',
        'availability_365', 'minimum_nights', 'number_of_reviews',
        'review_scores_rating', 'occupancy_rate', 'estimated_annual_revenue_computed'
    ]
    
    # Filter variables present in the df
    num_cols = [c for c in num_cols if c in df.columns]
    
    corr_matrix = df[num_cols].corr()
    
    fig = px.imshow(
        corr_matrix,
        text_auto=".2f",
        color_continuous_scale="RdBu",
        range_color=[-1, 1],
        title="Variable Correlation Heatmap"
    )
    fig.update_layout(coloraxis_colorbar=dict(title="Correlation"))
    return apply_chart_theme(fig, height=450)

# --- Page 5 Prediction Explainability Chart ---

def plot_shap_contributions(shap_df, expected_value, predicted_price):
    """
    Plots a highly informative horizontal bar chart representing SHAP value contributions.
    """
    # Map raw features to human readable descriptions
    name_map = {
        'accommodates': 'Guest Capacity',
        'bedrooms': 'Bedrooms Count',
        'bathrooms': 'Bathrooms Count',
        'beds': 'Beds Count',
        'availability_365': 'Yearly Availability',
        'minimum_nights': 'Minimum Stay Nights',
        'number_of_reviews': 'Number of Reviews',
        'review_scores_rating': 'Review Score Rating',
        'guests_per_bedroom': 'Guests-per-Bedroom Density',
        'review_density': 'Booking Frequency Ratio',
        'is_superhost': 'Superhost Credentials',
        'has_reviews': 'Has Reviews Active',
        'is_popular': 'Listing Popularity Rating',
        'room_Hotel room': 'Room Type: Hotel Room',
        'room_Private room': 'Room Type: Private Room',
        'room_Shared room': 'Room Type: Shared Room'
    }
    
    shap_df = shap_df.copy()
    shap_df['Feature_Label'] = shap_df['Feature'].map(name_map)
    
    # Filter features with meaningful impact (non-zero SHAP value)
    shap_df = shap_df[shap_df['SHAP'].abs() > 0.001].sort_values(by='SHAP', ascending=True)
    
    # Assign custom colors: Corporate Blue for positive contribution, Corporate Amber for negative contribution
    shap_df['Color'] = np.where(shap_df['SHAP'] >= 0, COLOR_PRIMARY, COLOR_WARNING)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=shap_df['Feature_Label'],
        x=shap_df['SHAP'],
        orientation='h',
        marker_color=shap_df['Color'],
        hovertemplate='<b>%{y}</b><br>SHAP Influence: %{x:.4f} log points<extra></extra>',
        opacity=0.9
    ))
    
    # Add title and labels
    fig.update_layout(
        title="ML Price Decision Driver Weightings (SHAP Values)",
        xaxis_title="Directional Impact on log(price) <br>◄ Discounting Price | Enhancing Price ►",
        yaxis_title="",
        showlegend=False,
    )
    
    return apply_chart_theme(fig, height=450)
