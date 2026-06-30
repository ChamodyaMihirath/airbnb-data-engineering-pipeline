import streamlit as st
import pandas as pd
import numpy as np
import json
from load_data import load_clean_data, render_sidebar_filters
from predict import preprocess_and_predict
from functions import render_header, kpi_card, plot_shap_contributions

# Page Setup
st.set_page_config(layout="wide", page_title="Price Prediction | Amsterdam Airbnb")

# Load raw and filtered data
raw_df = load_clean_data()
filtered_df = render_sidebar_filters(raw_df)

# Header
render_header("Machine Learning Price Predictor", "Predict nightly rental rates using our trained XGBoost model and dissect pricing drivers using SHAP.")

# Get distinct options from data for input matching
all_neighbourhoods = sorted(raw_df['neighbourhood_cleansed'].dropna().unique().tolist())
all_room_types = sorted(raw_df['room_type'].dropna().unique().tolist())
all_prop_types = sorted(raw_df['property_type'].dropna().unique().tolist())

# Split into two columns: Left for input form, Right for prediction output
col_input, col_output = st.columns([1, 1.1])

with col_input:
    st.markdown("### 📝 Listing Characteristics")
    
    with st.form("prediction_form"):
        # Categorical Inputs
        selected_neigh = st.selectbox("District / Neighbourhood", options=all_neighbourhoods, index=0)
        selected_room = st.selectbox("Room Type", options=all_room_types, index=0)
        selected_prop = st.selectbox("Property Type", options=all_prop_types, index=0)
        
        # Operational Inputs
        c1, c2 = st.columns(2)
        with c1:
            val_bedrooms = st.slider("Bedrooms count", min_value=0, max_value=8, value=1, step=1)
            val_bathrooms = st.slider("Bathrooms count", min_value=1.0, max_value=6.0, value=1.0, step=0.5)
            val_beds = st.slider("Beds count", min_value=1, max_value=12, value=2, step=1)
            val_accommodates = st.slider("Guest Capacity (Accommodates)", min_value=1, max_value=16, value=2, step=1)
        with c2:
            val_availability = st.slider("Availability (Days/Year)", min_value=0, max_value=365, value=180, step=10)
            val_min_nights = st.slider("Minimum Stay (Nights)", min_value=1, max_value=30, value=2, step=1)
            val_num_reviews = st.number_input("Number of Cumulative Reviews", min_value=0, max_value=1000, value=15, step=5)
            val_rating = st.slider("Review Scores Rating (0-5)", min_value=0.0, max_value=5.0, value=4.7, step=0.1)
            
        c3, c4 = st.columns(2)
        with c3:
            val_superhost = st.checkbox("Host is Superhost?", value=False)
        with c4:
            val_instant = st.checkbox("Instant Bookable?", value=False)
            
        submit_btn = st.form_submit_button("🔮 Predict Nightly Price", use_container_width=True)

with col_output:
    st.markdown("### 🎯 Valuation Results")
    
    # Calculate medians from raw dataset for comparisons
    overall_median = float(raw_df['price'].median())
    
    # Filter by selected neighbourhood to get local baseline
    neigh_df = raw_df[raw_df['neighbourhood_cleansed'] == selected_neigh]
    neigh_median = float(neigh_df['price'].median()) if not neigh_df.empty else overall_median
    
    # Trigger model inference
    inputs = {
        'accommodates': val_accommodates,
        'bedrooms': val_bedrooms,
        'bathrooms': val_bathrooms,
        'beds': val_beds,
        'availability_365': val_availability,
        'minimum_nights': val_min_nights,
        'number_of_reviews': val_num_reviews,
        'review_scores_rating': val_rating,
        'is_superhost': val_superhost,
        'room_type': selected_room
    }
    
    # Perform prediction
    res = preprocess_and_predict(inputs)
    pred_price = res['predicted_price']
    shap_df = res['shap_df']
    explanation_text = res['explanation_text']
    
    # Compute relative metric difference
    price_diff = pred_price - neigh_median
    diff_percent = (price_diff / neigh_median) * 100
    
    # Suggested Range
    range_min = int(pred_price * 0.95)
    range_max = int(pred_price * 1.05)
    
    # Determine Category
    # Budget (< 35th percentile of raw data), Luxury (> 85th percentile), Mid-range in between
    p35 = raw_df['price'].quantile(0.35)
    p85 = raw_df['price'].quantile(0.85)
    if pred_price <= p35:
        price_tier = "Budget Option"
    elif pred_price >= p85:
        price_tier = "Luxury Option"
    else:
        price_tier = "Mid-Range Option"
        
    # Recommendation System
    if diff_percent > 15:
        rec_status = "Premium Pricing"
        rec_desc = "Above neighbourhood average. Recommend boosting amenities or ratings to justify rate."
        trend_dir = "up"
    elif diff_percent < -15:
        rec_status = "Underpriced Opportunity"
        rec_desc = "Highly competitive. Opportunity to raise nightly price to capture wider margin."
        trend_dir = "down"
    else:
        rec_status = "Highly Competitive"
        rec_desc = "Aligned with local neighbourhood expectations. Optimal for steady occupancy."
        trend_dir = "up"

    # KPI Layout
    out_c1, out_c2 = st.columns(2)
    with out_c1:
        kpi_card("Predicted Price", f"€{pred_price:.2f}", f"Tier: {price_tier}")
        kpi_card("Suggested Pricing Range", f"€{range_min} - €{range_max}", "Optimized yield boundaries")
    with out_c2:
        kpi_card("District Median", f"€{neigh_median:.2f}", f"{abs(diff_percent):.1f}% {'above' if price_diff >= 0 else 'below'} average", "up" if price_diff >= 0 else "down")
        kpi_card("Valuation Feedback", rec_status, rec_desc, trend_dir)

    st.markdown("---")
    
    # 2. Plain English Explainability & SHAP
    st.markdown("#### 🔍 AI Explainability Analysis")
    
    # Format nice box
    st.markdown(
        f"""
        <div style="background-color: #f0f7ff; padding: 20px; border-radius: 12px; border-left: 5px solid #185FA5; margin-bottom: 25px;">
            <p style="margin: 0; color: #1e293b; font-size: 1.02rem; line-height: 1.5;">
                <strong>Executive Valuation Interpretation:</strong><br>
                {explanation_text}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 3. Plotly SHAP Chart
    fig_shap = plot_shap_contributions(shap_df, res['expected_value'], pred_price)
    st.plotly_chart(fig_shap, use_container_width=True)

    # 4. Download Prediction Summary (Extra feature)
    pred_summary = {
        "inputs": inputs,
        "district": selected_neigh,
        "property_type": selected_prop,
        "predicted_price": round(pred_price, 2),
        "district_median": round(neigh_median, 2),
        "price_difference": round(price_diff, 2),
        "difference_percentage": round(diff_percent, 2),
        "tier": price_tier,
        "valuation_recommendation": rec_status,
        "suggested_range": f"€{range_min} - €{range_max}"
    }
    
    pred_json = json.dumps(pred_summary, indent=4)
    st.download_button(
        label="📥 Download Prediction Report (JSON)",
        data=pred_json,
        file_name="airbnb_valuation_report.json",
        mime="application/json",
        use_container_width=True
    )
