import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from load_data import load_clean_data, render_sidebar_filters
from functions import (
    render_header, kpi_card, plot_host_segments, 
    plot_host_metrics, apply_chart_theme, COLOR_PRIMARY, COLOR_SUCCESS
)

# Page Setup
st.set_page_config(layout="wide", page_title="Host Analytics | Amsterdam Airbnb")

# Load raw and filtered data
raw_df = load_clean_data()
filtered_df = render_sidebar_filters(raw_df)

# Header
render_header("Host Analytics", "Operational profiling, portfolio distribution, and revenue comparison by host segments.")

if filtered_df.empty:
    st.warning("⚠️ No active listings match the selected filters. Please adjust your criteria.")
else:
    # 1. Host Operational KPI Row
    st.markdown("### 🔑 Host Operational Metrics")
    
    avg_response = filtered_df['host_response_rate'].mean()
    avg_acceptance = filtered_df['host_acceptance_rate'].mean()
    avg_tenure = filtered_df['host_tenure_years'].mean()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        val = f"{avg_response:.1f}%" if not pd.isna(avg_response) else "N/A"
        kpi_card("Average Host Response Rate", val, "Operational responsiveness")
    with c2:
        val = f"{avg_acceptance:.1f}%" if not pd.isna(avg_acceptance) else "N/A"
        kpi_card("Average Host Acceptance Rate", val, "Booking transaction friction")
    with c3:
        val = f"{avg_tenure:.1f} Yrs" if not pd.isna(avg_tenure) else "N/A"
        kpi_card("Average Host Tenure", val, "Experience / Loyalty metrics")
        
    st.markdown("---")

    # 2. Segment Share & Performance
    st.markdown("### 🏢 Host Portfolio Segments")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_segments = plot_host_segments(filtered_df)
        st.plotly_chart(fig_segments, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 20px;">
                <strong>💡 Portfolio Share Analysis:</strong><br>
                Amsterdam's market contains a healthy mix of individual and portfolio hosts. 
                Single-listing hosts represent the foundational core of the platform's supply. 
                However, commercial operators and professional management companies occupy a growing portion, 
                demanding tailormade software solutions and enterprise dashboard systems.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        # Host tenure histogram
        fig_tenure = px.histogram(
            filtered_df,
            x="host_tenure_years",
            nbins=20,
            color_discrete_sequence=[COLOR_PRIMARY],
            labels={"host_tenure_years": "Host Tenure (Years)", "count": "Count"},
            title="Host Tenure Distribution"
        )
        st.plotly_chart(apply_chart_theme(fig_tenure), use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-bottom: 20px;">
                <strong>💡 Tenure & Experience Analysis:</strong><br>
                The host tenure distribution shows a highly experienced host base. Many hosts have been active for 
                over 5 years, suggesting a mature and saturated market environment. 
                Platform operators must offer sophisticated tooling to keep these veteran hosts engaged and profitable.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 3. Performance by Host Segment
    st.markdown("### 📊 Performance by Host Portfolio Size")
    col3, col4 = st.columns(2)
    
    with col3:
        fig_seg_occ = plot_host_metrics(
            filtered_df, 
            group_by_col="host_segment", 
            y_col="occupancy_rate", 
            title="Average Occupancy Rate by Host Segment",
            is_pct=True
        )
        st.plotly_chart(fig_seg_occ, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #BA7517; margin-bottom: 20px;">
                <strong>💡 Occupancy Performance:</strong><br>
                Commercial and professional operators generally achieve higher occupancy rates. This is driven by 
                professional calendar settings, dynamic pricing systems, and faster response times. 
                Individual hosts should adopt automated pricing workflows to close this efficiency gap.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col4:
        fig_seg_rev = plot_host_metrics(
            filtered_df, 
            group_by_col="host_segment", 
            y_col="estimated_annual_revenue_computed", 
            title="Average Annual Revenue by Host Segment",
            is_pct=False
        )
        # Format y-axis as Euros
        fig_seg_rev.update_yaxes(tickprefix="€", tickformat=",")
        st.plotly_chart(fig_seg_rev, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #A32D2D; margin-bottom: 20px;">
                <strong>💡 Revenue Accumulation:</strong><br>
                Annual revenue averages scale with portfolio professionalization. While commercial operators hold fewer listings overall, 
                their revenue contribution per listing is disproportionately high due to elevated price points and optimization.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 4. Superhost Performance Impact
    st.markdown("### 👑 Performance Comparison: Superhosts vs. Non-Superhosts")
    col5, col6 = st.columns(2)
    
    superhost_perf = filtered_df.groupby('host_is_superhost').agg(
        avg_price=('price', 'mean'),
        avg_occupancy=('occupancy_rate', 'mean'),
        avg_revenue=('estimated_annual_revenue_computed', 'mean')
    ).reset_index()
    
    superhost_perf['host_is_superhost'] = superhost_perf['host_is_superhost'].map({True: 'Superhost', False: 'Standard Host'})
    
    with col5:
        # Comparison of Occupancy
        fig_sup_occ = px.bar(
            superhost_perf,
            x="host_is_superhost",
            y="avg_occupancy",
            color="host_is_superhost",
            color_discrete_map={"Superhost": COLOR_SUCCESS, "Standard Host": COLOR_PRIMARY},
            labels={"avg_occupancy": "Average Occupancy Rate", "host_is_superhost": "Host Status"},
            title="Occupancy Boost from Superhost Credentials"
        )
        fig_sup_occ.update_layout(showlegend=False)
        fig_sup_occ.update_yaxes(tickformat=".0%")
        st.plotly_chart(apply_chart_theme(fig_sup_occ), use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-bottom: 20px;">
                <strong>💡 Superhost Occupancy Analysis:</strong><br>
                Superhosts achieve a measurable lift in occupancy compared to standard hosts. 
                This validation badge enhances conversion rates by improving search ranking placement and reducing booking hesitation.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col6:
        # Comparison of Revenue
        fig_sup_rev = px.bar(
            superhost_perf,
            x="host_is_superhost",
            y="avg_revenue",
            color="host_is_superhost",
            color_discrete_map={"Superhost": COLOR_SUCCESS, "Standard Host": COLOR_PRIMARY},
            labels={"avg_revenue": "Average Annual Revenue", "host_is_superhost": "Host Status"},
            title="Revenue Comparison: Superhost Advantage"
        )
        fig_sup_rev.update_layout(showlegend=False)
        fig_sup_rev.update_yaxes(tickprefix="€", tickformat=",")
        st.plotly_chart(apply_chart_theme(fig_sup_rev), use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 20px;">
                <strong>💡 Superhost Revenue Analysis:</strong><br>
                The combination of high prices and strong occupancy results in a substantial annual revenue advantage for Superhosts. 
                Investing in guest satisfaction pays direct dividends in bottom-line yields.
            </div>
            """,
            unsafe_allow_html=True
        )
