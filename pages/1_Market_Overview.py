import streamlit as st
from load_data import load_clean_data, render_sidebar_filters
from functions import (
    render_header, kpi_card, plot_price_distribution, 
    plot_occupancy_distribution, plot_rating_distribution
)

# Page Setup
st.set_page_config(layout="wide", page_title="Market Overview | Amsterdam Airbnb")

# Load raw and filtered data
raw_df = load_clean_data()
filtered_df = render_sidebar_filters(raw_df)

# Header
render_header("Market Overview", "Executive high-level summary of Amsterdam's active Airbnb listings and performance indicators.")

if filtered_df.empty:
    st.warning("⚠️ No active listings match the selected filters. Please adjust your criteria.")
else:
    # 1. KPI Cards Grid (4 columns, 2 rows)
    st.markdown("### 📈 Key Performance Indicators")
    
    total_listings = len(filtered_df)
    avg_price = filtered_df['price'].mean()
    med_price = filtered_df['price'].median()
    avg_rating = filtered_df['review_scores_rating'].mean()
    avg_occupancy = filtered_df['occupancy_rate'].mean()
    avg_revenue = filtered_df['estimated_annual_revenue_computed'].mean()
    num_superhosts = filtered_df['host_is_superhost'].sum()
    avg_reviews = filtered_df['number_of_reviews'].mean()
    
    # Grid Row 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Listings", f"{total_listings:,}", "Active in market")
    with c2:
        kpi_card("Average Nightly Price", f"€{avg_price:.2f}", f"Median: €{med_price:.0f}")
    with c3:
        kpi_card("Average Rating", f"{avg_rating:.2f}/5", "Guest reviews score")
    with c4:
        kpi_card("Average Occupancy", f"{avg_occupancy:.1%}", "Estimated booking rate")
        
    # Grid Row 2
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        kpi_card("Avg Annual Revenue", f"€{avg_revenue:,.0f}", "Computed per listing")
    with c6:
        superhost_pct = num_superhosts / total_listings if total_listings > 0 else 0
        kpi_card("Superhost Listings", f"{num_superhosts:,}", f"{superhost_pct:.1%} of market")
    with c7:
        kpi_card("Avg Reviews / Listing", f"{avg_reviews:.1f}", "Cumulative count")
    with c8:
        # Extra KPI for context
        median_nights = filtered_df['minimum_nights'].median()
        kpi_card("Median Min Nights", f"{int(median_nights)} night(s)", "Policy constraint")

    st.markdown("---")

    # 2. Distributions Layout
    st.markdown("### 📊 Distribution Analysis")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_price = plot_price_distribution(filtered_df)
        st.plotly_chart(fig_price, use_container_width=True)
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 20px;">
                <strong>💡 Market Pricing Insight:</strong><br>
                The nightly pricing distribution is heavily skewed right, with a median price of <strong>€{med_price:.0f}</strong>. 
                Most listings cluster between €120 and €280. Supply drops sharply above €400, representing the premium/luxury tier. 
                Management should target optimization services to hosts priced in the €150-€250 range to maximize yield.
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with chart_col2:
        fig_occ = plot_occupancy_distribution(filtered_df)
        st.plotly_chart(fig_occ, use_container_width=True)
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-bottom: 20px;">
                <strong>💡 Occupancy Performance Insight:</strong><br>
                Amsterdam's average occupancy rate is robust at <strong>{avg_occupancy:.1%}</strong>. 
                A significant subset of properties operates at near-capacity (>85% occupancy), indicating structural under-supply or highly competitive pricing. 
                Properties with below-average occupancy represent key targets for revenue optimization audits.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    chart_col3, _ = st.columns([2, 2])
    with chart_col3:
        fig_rating = plot_rating_distribution(filtered_df)
        st.plotly_chart(fig_rating, use_container_width=True)
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #BA7517; margin-bottom: 20px;">
                <strong>💡 Guest Quality & Ratings Insight:</strong><br>
                The ratings distribution is highly concentrated near the top, with a mean of <strong>{avg_rating:.2f} out of 5</strong>. 
                This high skew suggests that listings with scores below 4.75 are underperforming relative to the market standard. 
                Quality control initiatives should focus on listings dropping below the 4.70 threshold to protect the platform's brand equity.
            </div>
            """,
            unsafe_allow_html=True
        )
