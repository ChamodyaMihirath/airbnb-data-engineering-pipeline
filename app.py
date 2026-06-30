import streamlit as st
from load_data import load_clean_data, render_sidebar_filters
from functions import render_header, kpi_card, apply_custom_css

# Page Setup
st.set_page_config(layout="wide", page_title="Amsterdam Airbnb Analytics Platform")

# Apply styling stylesheet
apply_custom_css()

# Load raw and filtered data
raw_df = load_clean_data()
filtered_df = render_sidebar_filters(raw_df)

# Header
render_header(
    "Amsterdam Airbnb Analytics Platform", 
    "Executive Business Intelligence & Machine Learning Price Prediction Dashboard."
)

# Landing Content
st.markdown("### 🏛️ Executive Summary & Navigation Guide")

# Grid layout for summary and KPIs
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown(
        """
        Welcome to the **Amsterdam Airbnb Executive Analytics Platform**. This interactive system is 
        designed for Airbnb corporate managers, real-estate investors, and hospitality operational teams. 
        It integrates advanced descriptive diagnostics with predictive machine learning models to analyze the 
        Amsterdam market structure.
        
        #### 🗺️ How to Navigate the Platform:
        Use the sidebar navigation links to access specialized tabs:
        1. **Market Overview**: Core market metrics, listing totals, and key performance distributions.
        2. **Geographical Analysis**: Interactive geospatial mapping and district-level price rankings.
        3. **Host Analytics**: Profiling of host portfolios, Superhost margins, and operational KPIs.
        4. **Market Insights**: Price sensitivities, correlation matrices, and model feature importances.
        5. **Price Predictor (ML)**: Interactive price estimation tool powered by XGBoost with SHAP explainability.
        6. **Business Intelligence**: Data-driven recommendations for hosts, investors, and platform managers.
        
        #### 🛠️ Technology Stack:
        - **Pipeline Engine**: DuckDB & Pandas for raw data ingestion and feature engineering.
        - **Visualization Suite**: Interactive Plotly charts styled to corporate specifications.
        - **Predictive Modeling**: Gradient Boosted Decision Trees via XGBoost.
        - **Model Explainability**: Game-theoretic SHAP values calculated through Random Forest explainer models.
        """
    )

with col_right:
    st.markdown("#### 📊 Amsterdam Market Baselines")
    
    # Calculate baseline metrics
    total_listings = len(raw_df)
    avg_price = raw_df['price'].mean()
    avg_occ = raw_df['occupancy_rate'].mean()
    superhost_pct = raw_df['host_is_superhost'].sum() / total_listings if total_listings > 0 else 0
    
    kpi_card("Baseline Total Listings", f"{total_listings:,}", "Amsterdam city limits")
    kpi_card("Baseline Average Price", f"€{avg_price:.2f}", "Per-night standard listing price")
    kpi_card("Baseline Average Occupancy", f"{avg_occ:.1%}", "Calculated based on calendar bookings")
    kpi_card("Superhost Ratio", f"{superhost_pct:.1%}", "Percentage of qualified premium hosts")

# Visual separator
st.markdown("---")

# Informative architecture block
st.markdown("### 🧬 Architecture Overview")
st.markdown(
    """
    ```mermaid
    graph LR
        A[Raw Airbnb Scraped Data] --> B[Data Cleaning & Engineering Pipeline]
        B --> C[DuckDB SQL Database Storage]
        C --> D[Model Training: XGBoost & Random Forest]
        D --> E[Interactive Dashboard Application]
        E --> F[Business Decision Support System]
    ```
    """,
    unsafe_allow_html=True
)

st.info("💡 **Tip:** Use the sidebar controls to filter the dataset. Every page will automatically refresh to represent the selected filters.")

# Footer
st.markdown(
    """
    <div class="footer">
        <p>Created by: <strong>Chamodya Mihirath</strong> | Airbnb Analytics Division & Antigravity Coding Assistant</p>
        <p>Data Scrapes Source: Inside Airbnb | Technology Stack: Python, Streamlit, XGBoost, DuckDB, Plotly, SHAP</p>
    </div>
    """,
    unsafe_allow_html=True
)
