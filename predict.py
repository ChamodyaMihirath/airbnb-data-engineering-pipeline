import pickle
import numpy as np
import pandas as pd
import streamlit as st
import shap

@st.cache_resource
def load_models():
    """
    Loads and caches the XGBoost and Random Forest models.
    """
    with open("models/xgboost.pkl", "rb") as f:
        xgb_model = pickle.load(f)
    with open("models/random_forest.pkl", "rb") as f:
        rf_model = pickle.load(f)
    return xgb_model, rf_model

@st.cache_resource
def get_shap_explainer():
    """
    Loads the Random Forest model and creates a cached SHAP TreeExplainer.
    """
    _, rf_model = load_models()
    explainer = shap.TreeExplainer(rf_model)
    return explainer

def preprocess_and_predict(inputs):
    """
    Preprocesses the user inputs and generates predictions.
    
    Inputs dict contains:
    - accommodates
    - bedrooms
    - bathrooms
    - beds
    - availability_365
    - minimum_nights
    - number_of_reviews
    - review_scores_rating
    - is_superhost (bool)
    - room_type (string: 'Entire home/apt', 'Private room', 'Shared room', 'Hotel room')
    """
    xgb_model, _ = load_models()
    explainer = get_shap_explainer()
    
    # 1. Feature Engineering
    accommodates = int(inputs.get('accommodates', 2))
    bedrooms = float(inputs.get('bedrooms', 1.0))
    bathrooms = float(inputs.get('bathrooms', 1.0))
    beds = float(inputs.get('beds', 1.0))
    availability_365 = int(inputs.get('availability_365', 180))
    minimum_nights = int(inputs.get('minimum_nights', 2))
    number_of_reviews = int(inputs.get('number_of_reviews', 10))
    review_scores_rating = float(inputs.get('review_scores_rating', 4.5))
    
    is_super = 1 if inputs.get('is_superhost', False) else 0
    has_rev = 1 if number_of_reviews > 0 else 0
    is_pop = 1 if number_of_reviews >= 20 else 0
    
    guests_per_bed = accommodates / bedrooms if bedrooms > 0 else accommodates
    rev_density = round(number_of_reviews / availability_365, 4) if availability_365 > 0 else 0.0
    
    room_type = inputs.get('room_type', 'Entire home/apt')
    room_hotel = 1 if room_type == 'Hotel room' else 0
    room_private = 1 if room_type == 'Private room' else 0
    room_shared = 1 if room_type == 'Shared room' else 0
    
    # Order must match model feature_names_in_ exactly
    features = ['accommodates', 'bedrooms', 'bathrooms', 'beds', 'availability_365', 
                'minimum_nights', 'number_of_reviews', 'review_scores_rating', 
                'guests_per_bedroom', 'review_density', 'is_superhost', 'has_reviews', 
                'is_popular', 'room_Hotel room', 'room_Private room', 'room_Shared room']
    
    X_pred = pd.DataFrame(columns=features)
    X_pred.loc[0] = [
        accommodates, bedrooms, bathrooms, beds, availability_365,
        minimum_nights, number_of_reviews, review_scores_rating,
        guests_per_bed, rev_density, is_super, has_rev,
        is_pop, room_hotel, room_private, room_shared
    ]
    
    # Cast to numeric
    for col in X_pred.columns:
        X_pred[col] = pd.to_numeric(X_pred[col])
        
    # 2. XGBoost Prediction (log scale)
    pred_log_xgb = xgb_model.predict(X_pred)[0]
    pred_price_xgb = np.expm1(pred_log_xgb)
    
    # 3. Random Forest SHAP values
    shap_vals = explainer.shap_values(X_pred)[0]
    expected_val = explainer.expected_value[0]
    
    # Map SHAP values to features for explainability
    shap_explanation = []
    for feat, val in zip(features, shap_vals):
        # Format feature value for printing
        raw_val = X_pred.loc[0, feat]
        shap_explanation.append({
            'Feature': feat,
            'Value': raw_val,
            'SHAP': val
        })
        
    shap_df = pd.DataFrame(shap_explanation)
    # Sort by magnitude of SHAP impact
    shap_df['Abs_SHAP'] = shap_df['SHAP'].abs()
    shap_df = shap_df.sort_values(by='Abs_SHAP', ascending=False).reset_index(drop=True)
    
    # Generate Natural Language Explanation
    explanation_sentences = []
    
    # Key Positive drivers (SHAP > 0.05)
    pos_drivers = shap_df[shap_df['SHAP'] > 0.02].head(3)
    # Key Negative drivers (SHAP < -0.02)
    neg_drivers = shap_df[shap_df['SHAP'] < -0.02].head(3)
    
    def format_feat_name(f, v):
        name_map = {
            'accommodates': f"guest capacity of {int(v)}",
            'bedrooms': f"{int(v)} bedroom(s)",
            'bathrooms': f"{v} bathroom(s)",
            'beds': f"{int(v)} bed(s)",
            'availability_365': f"availability of {int(v)} days per year",
            'minimum_nights': f"minimum stay of {int(v)} night(s)",
            'number_of_reviews': f"review count ({int(v)})",
            'review_scores_rating': f"rating of {v:.2f}/5",
            'guests_per_bedroom': f"density of {v:.1f} guests per bedroom",
            'review_density': f"high booking-review density",
            'is_superhost': "host's Superhost status",
            'room_Hotel room': "being a Hotel room",
            'room_Private room': "being a Private room",
            'room_Shared room': "being a Shared room",
        }
        return name_map.get(f, f.replace('_', ' '))
    
    pos_terms = [format_feat_name(r['Feature'], r['Value']) for _, r in pos_drivers.iterrows()]
    neg_terms = [format_feat_name(r['Feature'], r['Value']) for _, r in neg_drivers.iterrows()]
    
    if pos_terms:
        explanation_sentences.append(f"This listing is priced higher mainly because of its {', '.join(pos_terms[:-1])}{' and ' if len(pos_terms) > 1 else ''}{pos_terms[-1]}.")
    if neg_terms:
        explanation_sentences.append(f"Conversely, its price is moderated or reduced due to its {', '.join(neg_terms[:-1])}{' and ' if len(neg_terms) > 1 else ''}{neg_terms[-1]}.")
    
    explanation_text = " ".join(explanation_sentences)
    if not explanation_text:
        explanation_text = "This listing's price is close to the average market baseline, with no single feature dominating the valuation."
        
    return {
        'predicted_price': max(10.0, float(pred_price_xgb)),  # Floor price at 10
        'shap_df': shap_df,
        'expected_value': np.expm1(expected_val),
        'explanation_text': explanation_text
    }
