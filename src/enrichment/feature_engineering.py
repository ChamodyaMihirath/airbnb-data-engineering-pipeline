"""
feature_engineering.py  —  Section 3.3: Derived Calculated Fields
------------------------------------------------------------------
Computes all derived metrics on the master listings table.

Fields computed here (per assignment requirements):
    host_tenure_years       : years since host joined platform
    review_frequency        : reviews per month (active period)
    price_per_bedroom       : nightly price divided by bedroom count
    occupancy_rate          : from calendar (booked / total days)
    estimated_revenue       : occupancy_rate × price × 365
    price_tier              : categorical price band for each listing
    is_high_performer       : listing with above-average rating AND reviews
    days_since_last_review  : recency of demand signal

Why a separate feature_engineering module:
    Feature engineering is analytically distinct from joining.
    These fields require business domain knowledge to define correctly,
    and keeping them separate makes it easy to add new features without
    touching join logic.

Usage:
    from enrichment.feature_engineering import FeatureEngineer
    fe     = FeatureEngineer()
    master = fe.engineer_all(master)
"""

import pandas as pd
import numpy as np


class FeatureEngineer:

    def engineer_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all feature engineering to the master listings table.
        Called after joins.py has merged all datasets.

        Args:
            df: master listings DataFrame from DataJoiner.build_master()

        Returns:
            DataFrame with all derived fields added
        """
        print("\n  [feature_engineering] Computing derived fields ...")
        df = df.copy()

        df = self._host_tenure(df)
        df = self._price_per_bedroom(df)
        df = self._review_frequency(df)
        df = self._revenue_estimate(df)
        df = self._price_tier(df)
        df = self._performance_flag(df)
        df = self._review_recency(df)
        df = self._host_segment(df)

        print(f"  ✅ Feature engineering complete: {df.shape[1]} total columns")
        return df

    # =========================================================
    # Individual feature methods
    # =========================================================

    def _host_tenure(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Host tenure: years since host joined Airbnb.

        Why useful:
            Experienced hosts (high tenure) tend to price more strategically,
            maintain higher ratings, and have more reviews.
            Used in host segmentation and price driver analysis.

        Formula: (today - host_since) / 365.25
        Clipped at 0 (prevents negative values from future-dated host_since)
        """
        if "host_since" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["host_since"]):
                df["host_since"] = pd.to_datetime(df["host_since"], errors="coerce")

            df["host_tenure_years"] = (
                (pd.Timestamp.now() - df["host_since"]).dt.days / 365.25
            ).round(2).clip(lower=0)

            print(f"     host_tenure_years: median = "
                  f"{df['host_tenure_years'].median():.1f} years")
        return df

    def _price_per_bedroom(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Price per bedroom: nightly price / number of bedrooms.

        Why useful:
            Normalizes price by listing size — allows fair comparison
            between studios (1 bedroom) and large apartments (4 bedrooms).
            Key feature in price prediction model.

        NaN when: bedrooms = 0, bedrooms = NaN, or price = NaN
        Why NaN not 0: division by zero or missing inputs = unknown, not free.
        """
        if "price" in df.columns and "bedrooms" in df.columns:
            df["price_per_bedroom"] = np.where(
                (df["bedrooms"].fillna(0) > 0) & df["price"].notna(),
                (df["price"] / df["bedrooms"]).round(2),
                np.nan
            )
            valid = df["price_per_bedroom"].notna().sum()
            print(f"     price_per_bedroom: {valid:,} valid values, "
                  f"median = €{df['price_per_bedroom'].median():.0f}")
        return df

    def _review_frequency(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Review frequency: reviews per month over the listing's active life.

        Why useful:
            High review frequency = high booking demand.
            Used as a demand proxy when calendar occupancy is unavailable.

        Two sources (use best available):
            1. reviews_per_month_computed from review join (most accurate)
            2. reviews_per_month from listings.csv (Inside Airbnb pre-computed)
            3. Derived from number_of_reviews / host_tenure_months (fallback)
        """
        # Use pre-computed from review join if available
        if "reviews_per_month_computed" in df.columns:
            df["review_frequency"] = df["reviews_per_month_computed"]
        elif "reviews_per_month" in df.columns:
            df["review_frequency"] = df["reviews_per_month"]
        elif "number_of_reviews" in df.columns and "host_tenure_years" in df.columns:
            months = (df["host_tenure_years"] * 12).clip(lower=1)
            df["review_frequency"] = (
                df["number_of_reviews"] / months
            ).round(4)

        if "review_frequency" in df.columns:
            print(f"     review_frequency: median = "
                  f"{df['review_frequency'].median():.2f} reviews/month")
        return df

    def _revenue_estimate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimated annual revenue: occupancy_rate × price × 365.

        Why compute here (even though Inside Airbnb provides estimated_revenue_l365d):
            Inside Airbnb's pre-computed value may use a different methodology.
            Our computed value is transparent and traceable.
            Both are retained — analysts can compare them.

        Note: This is a gross revenue estimate.
            Airbnb's service fee (~14%) and host taxes are not deducted.
            Documented in assumptions_log C-03.
        """
        if "occupancy_rate" in df.columns and "price" in df.columns:
            df["estimated_annual_revenue_computed"] = np.where(
                df["occupancy_rate"].notna() & df["price"].notna(),
                (df["occupancy_rate"] * df["price"] * 365).round(2),
                np.nan
            )
            valid = df["estimated_annual_revenue_computed"].notna().sum()
            median_rev = df["estimated_annual_revenue_computed"].median()
            print(f"     estimated_annual_revenue_computed: "
                  f"{valid:,} values, median = €{median_rev:,.0f}")
        return df

    def _price_tier(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Price tier: categorical band based on nightly price.

        Thresholds based on Amsterdam market quartiles from profiling:
            Budget    : ≤ €80/night    (below Q1)
            Mid-range : €81–€150/night (Q1 to median)
            Premium   : €151–€300/night (median to Q3)
            Luxury    : > €300/night   (above Q3)

        Why categorical tiers:
            Continuous price is hard to segment in business reporting.
            Tiers allow "what % of listings are luxury?" type questions.
            Also useful as a feature in price prediction model.
        """
        if "price" in df.columns:
            df["price_tier"] = pd.cut(
                df["price"],
                bins=[0, 80, 150, 300, np.inf],
                labels=["Budget (≤€80)",
                        "Mid-range (€81–€150)",
                        "Premium (€151–€300)",
                        "Luxury (>€300)"],
                right=True
            )
            print(f"     price_tier distribution:")
            if df["price_tier"].notna().sum() > 0:
                for tier, count in df["price_tier"].value_counts().items():
                    pct = count / df["price"].notna().sum() * 100
                    print(f"       {str(tier):30s}: {count:,} ({pct:.1f}%)")
        return df

    def _performance_flag(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        High performer flag: listing with above-median rating AND
        above-median review count.

        Why useful:
            Identifies listings that are both highly rated AND frequently
            booked — the "best in class" segment.
            Used in host analysis and pricing strategy recommendations.
        """
        if "review_scores_rating" in df.columns and "number_of_reviews" in df.columns:
            median_rating  = df["review_scores_rating"].median()
            median_reviews = df["number_of_reviews"].median()

            df["is_high_performer"] = (
                (df["review_scores_rating"] >= median_rating) &
                (df["number_of_reviews"]    >= median_reviews)
            )
            n_high = df["is_high_performer"].sum()
            print(f"     is_high_performer: {n_high:,} listings "
                  f"({n_high/len(df)*100:.1f}%) above median rating "
                  f"({median_rating:.2f}) AND reviews ({median_reviews:.0f})")
        return df

    def _review_recency(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Days since last review: recency of booking demand signal.

        Why useful:
            A listing with 500 reviews but the last one 3 years ago
            may be inactive. Recency captures current market activity.
            Used to flag potentially inactive listings.
        """
        if "latest_review_date" in df.columns:
            df["days_since_last_review"] = (
                (pd.Timestamp.now() - df["latest_review_date"]).dt.days
            )
            median_days = df["days_since_last_review"].median()
            print(f"     days_since_last_review: median = {median_days:.0f} days")
        elif "last_review" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["last_review"]):
                df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")
            df["days_since_last_review"] = (
                (pd.Timestamp.now() - df["last_review"]).dt.days
            )
        return df

    def _host_segment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Host segment: portfolio size classification.

        Segments:
            Single-listing  : 1 listing  (casual home-sharer)
            Small (2-5)     : 2-5 listings (occasional operator)
            Medium (6-20)   : 6-20 listings (semi-professional)
            Commercial (20+): 20+ listings (professional operator)

        Why useful:
            Supply-side analysis (Section 4.4) — what % of the market
            is controlled by commercial operators vs casual hosts?
        """
        if "host_total_listings_count" in df.columns:
            df["host_segment"] = pd.cut(
                df["host_total_listings_count"].fillna(1),
                bins=[0, 1, 5, 20, np.inf],
                labels=["Single-listing",
                        "Small (2-5)",
                        "Medium (6-20)",
                        "Commercial (20+)"],
                right=True
            )
        return df
