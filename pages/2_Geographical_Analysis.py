import streamlit as st
from load_data import load_clean_data, render_sidebar_filters
from functions import render_header, plot_listings_map, plot_neighbourhood_bar

# Page Setup
st.set_page_config(layout="wide", page_title="Geographical Analysis | Amsterdam Airbnb")

# Load raw and filtered data
raw_df = load_clean_data()
filtered_df = render_sidebar_filters(raw_df)

# Header
render_header("Geographical Analysis", "Interactive spatial visualization and performance metrics across Amsterdam's urban districts.")

if filtered_df.empty:
    st.warning("⚠️ No active listings match the selected filters. Please adjust your criteria.")
else:
    # 1. Map Container
    st.markdown("### 🗺️ Amsterdam Listings Distribution")
    fig_map = plot_listings_map(filtered_df)
    st.plotly_chart(fig_map, use_container_width=True)
    
    st.markdown(
        """
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 25px; margin-top: -10px;">
            <strong>💡 Spatial Analysis:</strong><br>
            The map reveals strong concentration and premium pricing inside the historical Centrum-West and Centrum-Oost zones. 
            Listing sizes (representing occupancy rates) are distributed relatively evenly across outer areas (such as Oud-West and De Baarsjes), 
            suggesting solid demand outside the commercial center where nightly prices are significantly lower.
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")

    # 2. Rankings Side-by-Side
    st.markdown("### 📊 District Price Rankings")
    col1, col2 = st.columns(2)
    
    with col1:
        fig_exp = plot_neighbourhood_bar(filtered_df, "Top 10 Most Expensive Districts", ascending=False)
        st.plotly_chart(fig_exp, use_container_width=True)
        
    with col2:
        fig_chp = plot_neighbourhood_bar(filtered_df, "Top 10 Cheapest Districts", ascending=True)
        st.plotly_chart(fig_chp, use_container_width=True)

    st.markdown("---")

    # 3. Neighbourhood Summary Table
    st.markdown("### 📋 District Performance Metrics Table")
    
    # Calculate district performance metrics
    neigh_stats = filtered_df.groupby('neighbourhood_cleansed').agg(
        total_listings=('id', 'count'),
        median_price=('price', 'median'),
        average_price=('price', 'mean'),
        average_occupancy=('occupancy_rate', 'mean'),
        average_rating=('review_scores_rating', 'mean')
    ).reset_index()
    
    # Rename columns for presentation
    neigh_stats.columns = [
        'District', 'Listings Count', 'Median Price (€)', 
        'Mean Price (€)', 'Mean Occupancy', 'Mean Guest Rating'
    ]
    
    neigh_stats = neigh_stats.sort_values(by='Median Price (€)', ascending=False).reset_index(drop=True)
    
    # Render interactive formatted table
    st.dataframe(
        neigh_stats.style.format({
            'Listings Count': '{:,}',
            'Median Price (€)': '€{:.2f}',
            'Mean Price (€)': '€{:.2f}',
            'Mean Occupancy': '{:.1%}',
            'Mean Guest Rating': '{:.2f}/5'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown(
        """
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-top: 15px;">
            <strong>💡 Performance Table Commentary:</strong><br>
            Executive investors should cross-reference Median Price against Mean Occupancy. Districts showing high occupancy rates (e.g. above 70%) 
            combined with moderate pricing represent highly stable cash-flow options. Conversely, high-price, low-occupancy areas are exposed to 
            higher seasonal volatility.
        </div>
        """,
        unsafe_allow_html=True
    )
