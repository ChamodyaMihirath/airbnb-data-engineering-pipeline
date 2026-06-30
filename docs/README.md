# 🏠 Airbnb Data Engineering & Market Intelligence Platform

> An enterprise-grade, end-to-end Data Engineering, Advanced Analytics, Statistical Inference, Explainable Machine Learning, and Business Intelligence platform built upon the Amsterdam Airbnb ecosystem.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![DuckDB](https://img.shields.io/badge/DuckDB-Analytics-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-success)
![Architecture](https://img.shields.io/badge/Architecture-Modular-blueviolet)

---

## 📋 Project Overview

The **Airbnb Data Engineering & Market Intelligence Platform** is a comprehensive, production-ready data product designed to ingest, process, 
model, and visualize complex short-term rental ecosystem data. 

Moving beyond isolated exploratory scripting, this platform establishes a robust, reproducible multi-stage data architecture. 
It seamlessly bridges structural data engineering pipelines with scientific statistical inference, gradient-boosted machine learning frameworks, 
and localized geographic information systems (GIS). The final system transforms raw, chaotic open-source rental matrices into granular, 
high-fidelity market intelligence and explainable pricing recommendations tailored for operators, real estate investors, and platform analysts.

---

## 🎯 Core Capabilities & Objectives

* **Reproducible Data Engineering**: Build an automated, modular, and type-safe Python data processing pipeline.
* **OLAP Data Warehousing**: Structural transformation and optimized column storage of dense rental logs into a
high-performance DuckDB analytical warehouse using Apache Parquet data matrices.
* **Rigid Statistical Inference**: Execution of non-parametric significance testing frameworks to rigorously isolate underlying market pricing drivers and
spatial dynamics.
* **Explainable Machine Learning (XAI)**: Training of predictive ensemble pricing models coupled with game-theoretic SHAP frameworks to expose
real-world model decision logic.
* **Interactive Operational Dashboard**: Development of a secure, responsive Streamlit portal containing executive KPIs, dynamic pricing simulation modules,
and interactive geographic heatmaps.

---

## 📊 Technical Architecture & System Flow

```text
       [ Raw Multi-Source Data ]
         (CSVs, GeoJSON, Maps)
                   │
                   ▼
       [ Modular Ingestion Layer ] ───> Log Engine / Profiler
                   │
                   ▼
       [ Type-Safe Cleaning Stage ] ──> Outlier / Missing Value Masks
                   │
                   ▼
     [ Vector Feature Engineering ] ──> Target & Interaction Encodings
                   │
                   ▼
      [ Embedded DuckDB Warehouse ] <── Stored via Parquet Arrays
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  [ EDA & Inference ]   [ Machine Learning ]
  - Non-Parametric Tests - Gradient Boosting (XGBoost)
  - Driver Diagnostics  - Game-Theoretic SHAP XAI
         │                   │
         └─────────┬─────────┘
                   ▼
     [ Streamlit Business Portal ] ───> Executive KPIs & Simulations
```

## 📂 Repository Structure
```text
airbnb-data-engineering-pipeline/
├── assets/                  # Frontend user interface presentation styles
│   └── style.css            # Global Streamlit appearance adjustments
├── Data/
│   ├── raw/                 # Unprocessed system listings, calendars, and GIS vectors
│   ├── processed/           # Standardized, target-masked feature tables & validation profiles
│   └── database/            # Localized analytical DuckDB instance binaries (.duckdb)
├── docs/                    # Structural architecture logs, assumptions, and disclosures
├── logs/                    # Automated runtime pipeline execution tracking log streams
├── ML/
│   ├── notebooks/           # Hyperparameter tuning logs and feature engineering protocols
│   └── models/              # Serialized weight vectors and predictive model binaries (.pkl)
├── Notebooks/               # Core data science sandboxes and prototype sheets
├── pages/                   # Multi-page responsive Streamlit dashboard sub-modules
├── reports/                 # Formatted final analytics reports and generated figures
├── sql/                     # Structured OLAP data definition and business analytical views
├── src/                     # Core Object-Oriented Production Packages
│   ├── cleaning/            # Missing values parsing and outlier containment modules
│   ├── database/            # ACID database connectivity layer
│   ├── enrichment/          # Feature transformation and neighborhood aggregation packages
│   ├── ingestion/           # Raw file parsing and schema validation classes
│   ├── profiling/           # Real-time summary statistics engine
│   └── statistics/          # Mathematical significance testing inference engines
├── app.py                   # Main interactive Streamlit application entry point
├── predict.py               # Standalone programmatic model inference entry point
├── load_data.py             # Performance caching ingestion bridge utilizing @st.cache_data
├── functions.py             # Utility helper functions
├── requirements.txt         # Deterministic python dependency manifestation
└── README.md                # System documentation manual
```

## 💡 System Features
### ⚙️ Data Engineering & Infrastructure
Automated Pipeline Architecture: Executes clean, isolated ingestion, cleaning, transformation, and profiling stages wrapped within a 
production-ready package structure.

Data Quality Safeguards: Incorporates defensive data profiling that logs completeness metrics, flags distribution violations, 
and handles missing geographic records seamlessly.

Advanced Feature Engineering: Implements target-encoded geographical layers, custom transaction review densities, 
and structural property clustering to capture granular market variation.

High-Performance Storage: Utilizes an optimal columnar pipeline layout, exporting stage-by-stage results into 
highly optimized Apache Parquet binaries loaded directly into a decoupled local DuckDB database instance.

## 🔬 Advanced Analytics & Non-Parametric Inference
Macro-Level Segmentation: Computes neighborhood concentration matrices across 22 distinct administrative areas, 
extracting density indicators and supply power-law structures.

Rigid Hypothesis Testing: Deploys non-parametric significance testing frameworks (Mann-Whitney U and Kruskal-Wallis diagnostics) 
to analytically validate price floor divergence across room classifications, overriding standard parametric assumptions that fail 
when handling heavily skewed market data.

## 🤖 Explainable Machine Learning Pipeline
Algorithmic Benchmarking: Implements a rigorous validation framework that fits, hyper-tunes, and contrasts multiple model generations, 
scaling from Baseline Ridge Regression (R²: 0.31) up to an Optimized XGBoost Regressor (R²: 0.58).

Leakage Prevention: Enforces a strict technical separation between parameter extraction and valuation validation spaces, 
protecting the modeling pipeline against target leakage.

#### Game-Theoretic Explainability (XAI): 
Connects global feature importance hierarchies, directional beeswarm graphs, and interaction scatter plots directly to the 
underlying model booster via game-theoretic SHAP frameworks.

## 💼 Streamlit Market Intelligence Portal
Executive KPI Summaries: Renders clear macro performance indicators, dynamic supply distributions, and occupancy trackers.

Geographic & Host Analytics: Connects spatial coordinate maps with interactive host portfolio concentration breakdowns.

Real-Time Inference Simulations: Provides a dedicated pricing calculator interface that hooks into the production model weight binary, 
enabling stakeholders to instantly test valuation changes based on custom listing configurations.

## 🛠️ Tech Stack

| Category                    | Technologies                          |
|----------------------------|---------------------------------------|
| **Core Programming**       | Python 3.11+                          |
| **OLAP Storage**           | DuckDB, Apache Parquet                |
| **Data Processing**        | Pandas, NumPy, Polars                 |
| **Visualization**          | Plotly, Matplotlib, Seaborn           |
| **Spatial Analysis**       | GeoPandas                             |
| **Machine Learning**       | Scikit-learn, XGBoost                 |
| **Explainable AI**         | SHAP                                  |
| **UI / Dashboard**         | Streamlit                             |
| **Logging & Orchestration**| Loguru, Modular Pipeline              |

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/airbnb-data-engineering-pipeline.git
cd airbnb-data-engineering-pipeline
```
## 2. Configure Dedicated Virtual Environment
```bash
python -m venv .venv
Windows Activation: .venv\Scripts\activate

Linux / macOS Activation: source .venv/bin/activate
```
## 3. Install Pinpoint System Dependencies
```bash
pip install -r requirements.txt
```
## 🎮 System Execution
Step 1: Execute End-to-End Data Pipeline
Run the fully automated engineering, storage transformation, data quality profiling, and database loading sequence:

```bash
python load_data.py
```
Step 2: Model Training and Verification (Optional)
To review experimental sandboxes or recalculate hyperparameter validation loops, execute core notebook paths sequentially:
```bash
Plaintext
ML/notebooks/01_Data_Preparation.ipynb
ML/notebooks/02_Feature_Engineering.ipynb
ML/notebooks/03_Model_Training.ipynb
ML/notebooks/04_Model_Evaluation.ipynb
ML/notebooks/05_Model_Explainability.ipynb
```
Step 3: Initialize Market Intelligence Portal
Boot up the multi-page visualization interface locally:

```bash
streamlit run app.py
```
## 📊 Production Figure Inventory
The platform auto-generates, updates, and exports high-resolution visual assets directly into the reports/ folder during pipeline execution. 
Key verified assets include:

<img width="2080" height="770" alt="fig_01_overall_price_distribution" src="https://github.com/user-attachments/assets/a2059e23-43dc-40cc-947f-bdbac67dcaea" />
<img width="2380" height="2732" alt="fig_03_price_by_neighbourhood" src="https://github.com/user-attachments/assets/4e437c03-636f-48ba-a278-1e4fcdbc0638" />
<img width="2080" height="770" alt="fig_05_host_portfolio_distribution" src="https://github.com/user-attachments/assets/a224a6b5-2a5f-49ed-8a00-f993478f7b9d" />
<img width="1480" height="880" alt="fig_06_price_by_room_type" src="https://github.com/user-attachments/assets/5ac5c3f2-bad8-4e13-a244-0c29d26a0d72" />
<img width="2080" height="770" alt="fig_07_listing_count_per_host" src="https://github.com/user-attachments/assets/84afaaa2-860e-4ece-b8a8-7b2d3b1d85b8" />
<img width="1480" height="880" alt="fig_07_price_by_room_type" src="https://github.com/user-attachments/assets/7bc53b9b-d7bb-443e-b4ff-3dbbf99eccab" />
<img width="2230" height="887" alt="fig_09_listing_density" src="https://github.com/user-attachments/assets/0e1a52c6-ec87-4327-9fe6-cc2a71c4acc3" />
<img width="2380" height="1181" alt="fig_09_review_scores" src="https://github.com/user-attachments/assets/f4fa4d6a-4f32-4b4e-b1d4-3615e8b27fb4" />
<img width="2230" height="887" alt="fig_10_geographic_pricing_gradient" src="https://github.com/user-attachments/assets/5e97d194-1841-407f-ab21-b65503db304f" />
<img width="1629" height="1331" alt="fig_16_correlation_matrix" src="https://github.com/user-attachments/assets/f8478b61-5c30-4de4-a708-390304e00ac1" />
<img width="2381" height="742" alt="fig_17_nonlinear_relationships" src="https://github.com/user-attachments/assets/81c9528a-360d-4bb6-bf95-0693e66d1fb5" />
<img width="2230" height="740" alt="fig_23_review_sub_dimensions" src="https://github.com/user-attachments/assets/4737fc86-2ef1-495a-85b5-4bc1f263a609" />

<img width="1546" height="515" alt="fig_ml_log_transform" src="https://github.com/user-attachments/assets/98346514-f43f-4722-acba-765260034041" />
<img width="1806" height="514" alt="fig_ml_data_overview" src="https://github.com/user-attachments/assets/fffd9b22-cc5f-490a-a4e8-2d07d391a2c0" />
<img width="1803" height="1278" alt="fig_ml_residuals" src="https://github.com/user-attachments/assets/3de1d241-9647-444c-91a3-663305e72636" />




## 🚀 Roadmap & System Scaling
[ ] Migrate local analytical DuckDB database tables into centralized cloud data warehouses (Snowflake / Google BigQuery).

[ ] Convert pipeline orchestration steps into containerized serverless workflows using Apache Airflow or Prefect.

[ ] Package the predictive inference layer (predict.py) into an isolated Docker container deployed as an independent REST API microservice.

[ ] Extend feature enrichment layers to pull real-time competitor calendars by connecting pipeline extraction hooks directly to live platform APIs.

## 👨‍💻 Project Engineering Auther
Chamodya Mihirath * Credentials: B.Sc. Computer Science (Hons) Specialization in Data Science

Institution: University of Kelaniya

Professional Channels: GitHub Profile | LinkedIn Network

⚖️ License & Terms
This project is released under standard academic distribution protocols. 
Source architectures, system pipelines, and final analytical documentation profiles remain completely open for inspection, optimization, 
and replication under standard attribution frameworks.


