import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pickle
from load_data import load_clean_data, render_sidebar_filters
from functions import (
    render_header, plot_bar_group, plot_scatter_relation, 
    plot_correlation_heatmap, apply_chart_theme, COLOR_PRIMARY
)

# Page Setup
st.set_page_config(layout="wide", page_title="Market Insights | Amsterdam Airbnb")

# Load raw and filtered data
raw_df = load_clean_data()
filtered_df = render_sidebar_filters(raw_df)

# Header
render_header("Market Insights", "Advanced statistical analysis of pricing elasticities, listing attributes, and predictive feature importance.")

if filtered_df.empty:
    st.warning("⚠️ No active listings match the selected filters. Please adjust your criteria.")
else:
    # 1. Price Drivers (Categorical Analysis)
    st.markdown("### 🏷️ Nightly Pricing by Category")
    col1, col2 = st.columns(2)
    
    with col1:
        fig_room = plot_bar_group(filtered_df, "room_type", "price", "Median Nightly Price by Room Type")
        fig_room.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_room, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 20px;">
                <strong>💡 Room Type Elasticity:</strong><br>
                Entire homes/apartments command a significant premium over private or shared rooms. 
                Shared rooms represent the cheapest market tier, while hotel rooms offer a premium business case.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col2:
        # Group property types, filtering to top 8 most frequent to keep it clean
        top_props = filtered_df['property_type'].value_counts().head(8).index
        prop_df = filtered_df[filtered_df['property_type'].isin(top_props)]
        fig_prop = plot_bar_group(prop_df, "property_type", "price", "Median Price by Top Property Types")
        fig_prop.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_prop, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-bottom: 20px;">
                <strong>💡 Property Type Selection:</strong><br>
                Condos, lofts, and boat/houseboats command high median pricing, reflecting their unique tourist appeal in Amsterdam. 
                Standard apartments or rental units represent the volume baseline.
            </div>
            """,
            unsafe_allow_html=True
        )

    col3, col4 = st.columns(2)
    
    with col3:
        fig_bed = plot_bar_group(filtered_df, "bedrooms", "price", "Median Price by Bedrooms Count")
        fig_bed.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_bed, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #BA7517; margin-bottom: 20px;">
                <strong>💡 Bedrooms Scaling:</strong><br>
                Prices scale linearly with the number of bedrooms. Listings with 4+ bedrooms target premium family and group travel, 
                capturing pricing power that scales faster than proportional operational overhead.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col4:
        # Limit accommodates to clean ranges
        max_accom = min(10, int(filtered_df['accommodates'].max()))
        accom_df = filtered_df[filtered_df['accommodates'] <= max_accom]
        fig_accom = plot_bar_group(accom_df, "accommodates", "price", "Median Price by Capacity (Accommodates)")
        fig_accom.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_accom, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #A32D2D; margin-bottom: 20px;">
                <strong>💡 Capacity Economics:</strong><br>
                Pricing correlates strongly with guest capacity. Increasing capacity (accommodates) per bedroom 
                can represent a high-yield optimization strategy for properties with flexible configurations.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 2. Scatter Analyses (Pricing Sensitivities)
    st.markdown("### 📈 Elasticity Scatter Analyses")
    
    col5, col6 = st.columns(2)
    
    with col5:
        fig_scat_rating = plot_scatter_relation(filtered_df, "review_scores_rating", "price", "Price vs. Review Rating Score")
        fig_scat_rating.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_scat_rating, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 20px;">
                <strong>💡 Review-Price Elasticity:</strong><br>
                The positive regression slope indicates that higher review ratings justify premium pricing. 
                A solid rating profile is a structural prerequisite for maintaining rates above the market median.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col6:
        fig_scat_reviews = plot_scatter_relation(filtered_df, "number_of_reviews", "price", "Price vs. Cumulative Reviews Count")
        fig_scat_reviews.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_scat_reviews, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-bottom: 20px;">
                <strong>💡 Review Volumetric Influence:</strong><br>
                Listings with high review counts trend toward stable pricing. Highly reviewed listings represent 
                established market participants who compete on trust rather than raw pricing fluctuations.
            </div>
            """,
            unsafe_allow_html=True
        )

    col7, col8 = st.columns(2)
    
    with col7:
        fig_scat_occ = plot_scatter_relation(filtered_df, "price", "occupancy_rate", "Occupancy Rate vs. Nightly Price")
        fig_scat_occ.update_yaxes(tickformat=".0%")
        fig_scat_occ.update_xaxes(tickprefix="€")
        st.plotly_chart(fig_scat_occ, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #BA7517; margin-bottom: 20px;">
                <strong>💡 Occupancy-Pricing Tradeoff:</strong><br>
                The negative regression slope confirms standard supply-demand price elasticity. 
                As price rises, average occupancy falls. Finding the optimal sweet spot that maximizes <i>Price × Occupancy</i> 
                is the primary challenge of host asset management.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col8:
        # Limit minimum nights to check standard ranges
        night_df = filtered_df[filtered_df['minimum_nights'] <= 14]
        fig_scat_nights = plot_scatter_relation(night_df, "minimum_nights", "price", "Nightly Price vs. Minimum Nights Stay")
        fig_scat_nights.update_yaxes(tickprefix="€")
        st.plotly_chart(fig_scat_nights, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #A32D2D; margin-bottom: 20px;">
                <strong>💡 Stay Policy Constraints:</strong><br>
                A high minimum stay requirement is associated with lower nightly prices, as hosts discount rates 
                to attract long-term bookings and reduce check-in overhead. Short-stay listings capture maximum pricing margins.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 3. Correlation & ML Importance
    st.markdown("### 🔬 Statistical Correlation & Predictive Drivers")
    col9, col10 = st.columns(2)
    
    with col9:
        fig_heat = plot_correlation_heatmap(filtered_df)
        st.plotly_chart(fig_heat, use_container_width=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #185FA5; margin-bottom: 20px;">
                <strong>💡 Correlation Interpretation:</strong><br>
                Price correlates positively with accommodates, bedrooms, and bathrooms. 
                Occupancy rate is negatively correlated with price, confirming that competitive pricing drives volume. 
                Annual revenue is strongly tied to occupancy and capacity.
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col10:
        # Load XGBoost feature importances
        try:
            with open("models/xgboost.pkl", "rb") as f:
                model = pickle.load(f)
            
            features = ['accommodates', 'bedrooms', 'bathrooms', 'beds', 'availability_365', 
                        'minimum_nights', 'number_of_reviews', 'review_scores_rating', 
                        'guests_per_bedroom', 'review_density', 'is_superhost', 'has_reviews', 
                        'is_popular', 'room_Hotel room', 'room_Private room', 'room_Shared room']
            
            importances = model.feature_importances_
            
            feat_imp = pd.DataFrame({
                'Feature': [f.replace('_', ' ').title() for f in features],
                'Importance': importances
            }).sort_values(by='Importance', ascending=True)
            
            fig_imp = px.bar(
                feat_imp,
                y='Feature',
                x='Importance',
                orientation='h',
                color_discrete_sequence=[COLOR_PRIMARY],
                title="XGBoost Feature Importance Drivers"
            )
            
            st.plotly_chart(apply_chart_theme(fig_imp, height=450), use_container_width=True)
            st.markdown(
                """
                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #1D9E75; margin-bottom: 20px;">
                    <strong>💡 ML Importance Insight:</strong><br>
                    The XGBoost model identifies listing capacity metrics (accommodates, bedrooms) and rooms types (Hotel room, Private room) 
                    as the most critical price predictors. This confirms that spatial utility is the primary driver of market valuation.
                </div>
                """,
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Could not render Feature Importance chart: {e}")
