import pandas as pd
import streamlit as st

@st.cache_data
def load_clean_data(file_path="Data/processed/master_listings.parquet"):
    """
    Loads and prepares the master listings Airbnb dataset.
    """
    df = pd.read_parquet(file_path)
    
    # Standardize types and fill missing values for visual analysis & predictions
    if 'bathrooms' in df.columns:
        df['bathrooms'] = pd.to_numeric(df['bathrooms'], errors='coerce').fillna(1.0)
    if 'bedrooms' in df.columns:
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce').fillna(1.0)
    if 'beds' in df.columns:
        df['beds'] = pd.to_numeric(df['beds'], errors='coerce').fillna(1.0)
    if 'accommodates' in df.columns:
        df['accommodates'] = pd.to_numeric(df['accommodates'], errors='coerce').fillna(2)
    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
    if 'review_scores_rating' in df.columns:
        df['review_scores_rating'] = pd.to_numeric(df['review_scores_rating'], errors='coerce').fillna(4.5)
    if 'availability_365' in df.columns:
        df['availability_365'] = pd.to_numeric(df['availability_365'], errors='coerce').fillna(0)
    if 'minimum_nights' in df.columns:
        df['minimum_nights'] = pd.to_numeric(df['minimum_nights'], errors='coerce').fillna(1)
    if 'number_of_reviews' in df.columns:
        df['number_of_reviews'] = pd.to_numeric(df['number_of_reviews'], errors='coerce').fillna(0)
    if 'occupancy_rate' in df.columns:
        df['occupancy_rate'] = pd.to_numeric(df['occupancy_rate'], errors='coerce').fillna(0.0)
    if 'estimated_annual_revenue_computed' in df.columns:
        df['estimated_annual_revenue_computed'] = pd.to_numeric(df['estimated_annual_revenue_computed'], errors='coerce').fillna(0.0)
        
    # Standardize boolean-like columns to True/False for robust matching
    bool_cols = ['host_is_superhost', 'instant_bookable']
    for col in bool_cols:
        if col in df.columns:
            # Map standard booleans and string representations
            df[col] = df[col].map({
                True: True, False: False,
                1: True, 0: False,
                't': True, 'f': False,
                'True': True, 'False': False
            }).fillna(False).astype(bool)
            
    return df

def apply_filters(df, neighbourhood_sel, room_type_sel, property_type_sel, 
                  superhost_sel, instant_bookable_sel, price_range, bedrooms_range, accommodates_range):
    """
    Applies sidebar filters to the dataframe.
    """
    filtered_df = df.copy()
    
    # 1. Neighbourhood Filter
    if neighbourhood_sel:
        filtered_df = filtered_df[filtered_df['neighbourhood_cleansed'].isin(neighbourhood_sel)]
        
    # 2. Room Type Filter
    if room_type_sel:
        filtered_df = filtered_df[filtered_df['room_type'].isin(room_type_sel)]
        
    # 3. Property Type Filter
    if property_type_sel:
        filtered_df = filtered_df[filtered_df['property_type'].isin(property_type_sel)]
        
    # 4. Superhost Filter
    if superhost_sel != "All":
        is_super = (superhost_sel == "Yes (Superhosts)")
        filtered_df = filtered_df[filtered_df['host_is_superhost'] == is_super]
        
    # 5. Instant Bookable Filter
    if instant_bookable_sel != "All":
        is_instant = (instant_bookable_sel == "Yes (Instant Bookable)")
        filtered_df = filtered_df[filtered_df['instant_bookable'] == is_instant]
        
    # 6. Price Range
    filtered_df = filtered_df[
        (filtered_df['price'] >= price_range[0]) & 
        (filtered_df['price'] <= price_range[1])
    ]
    
    # 7. Bedrooms Range
    filtered_df = filtered_df[
        (filtered_df['bedrooms'] >= bedrooms_range[0]) & 
        (filtered_df['bedrooms'] <= bedrooms_range[1])
    ]
    
    # 8. Accommodates Range
    filtered_df = filtered_df[
        (filtered_df['accommodates'] >= accommodates_range[0]) & 
        (filtered_df['accommodates'] <= accommodates_range[1])
    ]
    
    return filtered_df

def render_sidebar_filters(df):
    """
    Renders the unified filters in the Streamlit sidebar and returns the filtered dataframe.
    """
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding: 10px 0;">
            <h2 style="color: #185FA5; font-size: 1.4rem; font-weight: 700; margin: 0;">AMSTERDAM AIRBNB</h2>
            <p style="color: #64748b; font-size: 0.85rem; font-weight: 500; margin: 0 0 15px 0;">EXECUTIVE ANALYTICS</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Reset Filters Button
    if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("### 📊 Market Controls")

    # Get distinct options
    all_neighbourhoods = sorted(df['neighbourhood_cleansed'].dropna().unique().tolist())
    all_room_types = sorted(df['room_type'].dropna().unique().tolist())
    all_prop_types = sorted(df['property_type'].dropna().unique().tolist())
    
    min_price = float(df['price'].min())
    max_price = float(df['price'].quantile(0.99))  # Clip range at 99th percentile for easier sliding
    
    max_bedrooms = int(df['bedrooms'].max())
    max_accommodates = int(df['accommodates'].max())

    # 1. Search & Select Neighbourhood
    search_q = st.sidebar.text_input("🔍 Search Neighbourhood", key="neigh_search").lower()
    
    filtered_neigh_options = all_neighbourhoods
    if search_q:
        filtered_neigh_options = [n for n in all_neighbourhoods if search_q in n.lower()]
        
    neigh_sel = st.sidebar.multiselect(
        "Neighbourhoods",
        options=filtered_neigh_options,
        default=st.session_state.get('neigh_sel', []),
        key="neigh_sel",
        help="Select one or more Amsterdam districts"
    )

    # 2. Room Type Select
    room_sel = st.sidebar.multiselect(
        "Room Types",
        options=all_room_types,
        default=st.session_state.get('room_sel', []),
        key="room_sel"
    )

    # 3. Property Type Select
    prop_sel = st.sidebar.multiselect(
        "Property Types",
        options=all_prop_types,
        default=st.session_state.get('prop_sel', []),
        key="prop_sel"
    )

    # 4. Superhost Toggle
    superhost_sel = st.sidebar.selectbox(
        "Superhost Status",
        options=["All", "Yes (Superhosts)", "No (Non-Superhosts)"],
        index=0,
        key="superhost_sel"
    )

    # 5. Instant Bookable Toggle
    instant_sel = st.sidebar.selectbox(
        "Instant Bookable",
        options=["All", "Yes (Instant Bookable)", "No (Non-Instant Bookable)"],
        index=0,
        key="instant_sel"
    )

    # 6. Price Slider
    price_range = st.sidebar.slider(
        "Price Range (€ / Night)",
        min_value=min_price,
        max_value=max_price,
        value=st.session_state.get('price_range', (min_price, max_price)),
        step=10.0,
        key="price_range"
    )

    # 7. Bedrooms Slider
    bedrooms_range = st.sidebar.slider(
        "Bedrooms",
        min_value=0,
        max_value=max_bedrooms,
        value=st.session_state.get('bedrooms_range', (0, max_bedrooms)),
        step=1,
        key="bedrooms_range"
    )

    # 8. Accommodates Slider
    accommodates_range = st.sidebar.slider(
        "Guest Capacity (Accommodates)",
        min_value=1,
        max_value=max_accommodates,
        value=st.session_state.get('accommodates_range', (1, max_accommodates)),
        step=1,
        key="accommodates_range"
    )
    
    # Filtering DataFrame
    filtered_df = apply_filters(
        df, neigh_sel, room_sel, prop_sel,
        superhost_sel, instant_sel, price_range,
        bedrooms_range, accommodates_range
    )
    
    # Download as CSV button in the sidebar (extra feature)
    st.sidebar.markdown("---")
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name="filtered_airbnb_listings.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    return filtered_df
