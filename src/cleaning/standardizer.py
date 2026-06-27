"""
standardizer.py  —  Section 3.2: Price, Dates, Booleans, Categoricals
----------------------------------------------------------------------
Handles ALL format standardization across datasets.

Why a separate standardizer module:
    - Format issues are the same pattern across all datasets ($ prices, t/f booleans)
    - Keeping format logic separate from missing-value logic makes each easier to test
    - If Inside Airbnb changes their format, only this file needs updating

Methods:
    standardize_listings()   → listings.csv (79 cols)
    standardize_calendar()   → calendar.csv (7 cols)
    standardize_reviews()    → reviews.csv  (6 cols)

Shared utilities:
    _clean_price()           → strips $, commas → float, zero/negative → NaN
    _parse_percentage()      → "97%" → 97.0
    _map_bool()              → "t"/"f" → True/False
"""

import pandas as pd
import numpy as np


class DataStandardizer:

    # =========================================================
    # Normalization maps  (Section 3.2 - free-text fields)
    # =========================================================

    # Why map room_type explicitly:
    #   Inside Airbnb uses consistent values but we normalize defensively.
    #   Any unknown value → "Other" so analysis never breaks on new categories.
    ROOM_TYPE_MAP = {
        "Entire home/apt": "Entire home/apt",
        "Private room":    "Private room",
        "Shared room":     "Shared room",
        "Hotel room":      "Hotel room",
    }

    # Why map property_type:
    #   Amsterdam has 30+ raw property types (from profiling).
    #   We normalize to ~15 meaningful categories for EDA and ML features.
    #   Long-tail rare types → "Other" to avoid sparse one-hot columns.
    PROPERTY_TYPE_MAP = {
        "Entire rental unit":                "Entire rental unit",
        "Private room in rental unit":       "Private room in rental unit",
        "Entire condo":                      "Entire condo",
        "Entire home":                       "Entire home",
        "Private room in home":              "Private room in home",
        "Entire loft":                       "Entire loft",
        "Entire serviced apartment":         "Entire serviced apartment",
        "Room in hotel":                     "Hotel room",
        "Shared room in rental unit":        "Shared room",
        "Entire guest suite":                "Entire guest suite",
        "Private room in guest suite":       "Private room in guest suite",
        "Private room in bed and breakfast": "Bed and breakfast",
        "Entire vacation home":              "Entire vacation home",
        "Boat":                              "Boat",
        "Houseboat":                         "Houseboat",
        "Tiny home":                         "Tiny home",
    }

    # =========================================================
    # Shared utility methods
    # =========================================================

    # @staticmethod
    # def _clean_price(series: pd.Series) -> pd.Series:
    #     """
    #     Strip currency symbols and thousands separators, cast to float.

    #     WHY THIS METHOD:
    #         From profiling: listings.price is 43.95% null because the raw
    #         column contains strings like "$150.00" — pandas reads these as
    #         object dtype and treats them as NaN when you try numeric operations.
    #         Stripping $ and , then casting recovers ~4,606 listings.

    #         calendar.price had the SAME issue — 100% null in profiling
    #         because all values were "$XX.XX" strings never parsed.

    #     Handles: "$150.00", "EUR 1,234.50", "150", NaN, "nan"
    #     Zero or negative → NaN (a price of $0 is a blocked/invalid listing)
    #     """
    #     cleaned = (
    #         series.astype(str)
    #               .str.replace(r"[\$€£,\s]", "", regex=True)
    #               .str.strip()
    #     )
    #     numeric = pd.to_numeric(cleaned, errors="coerce")
    #     # Zero or negative prices are invalid — set to NaN not 0
    #     # WHY NaN not 0: imputing 0 would make the listing appear free,
    #     # completely distorting median price calculations
    #     return numeric.where(numeric > 0, other=np.nan)


   # standardizer.py — replace _clean_price() with this exact code

    # Add 'self' right here:
    def _clean_price(self, series: pd.Series) -> pd.Series:
        # 1. Track original state for accurate auditing
        before_null = int(series.isna().sum())
        
        # 2. Filter out null entries upfront so we don't stringify them into "nan"
        working_series = series.copy()
        
        if working_series.dtype == object:
            working_series = (
                working_series.astype(str)
                .str.replace("$", "", regex=False)
                .str.replace("€", "", regex=False)
                .str.replace("£", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
        
        # 3. Cast cleanly to numeric
        numeric = pd.to_numeric(working_series, errors="coerce")
        
        # 4. Enforce domain rule (Prices must be greater than 0)
        final_series = numeric.where(numeric > 0, other=np.nan)
        
        # 5. Compile your high-clarity metrics audit summary
        after_null = int(final_series.isna().sum())
        valid_count = int(final_series.notna().sum())
        induced_nans = after_null - before_null

        print(f"""
            Price Cleaning Summary
            ----------------------
            Valid prices      : {valid_count:,}
            Missing prices    : {after_null:,}
            New null values   : {induced_nans:+,}
            """)

        return final_series

    @staticmethod
    def _parse_percentage(series: pd.Series) -> pd.Series:
        """
        Convert percentage strings to float.

        WHY: host_response_rate and host_acceptance_rate are stored as
        "97%" strings. We need numeric values for correlation analysis
        and superhost segmentation.

        "97%" → 97.0   |   "N/A" → NaN   |   NaN → NaN
        """
        return pd.to_numeric(
            series.astype(str)
                  .str.replace("%", "", regex=False)
                  .str.strip(),
            errors="coerce"
        )

    @staticmethod
    def _map_bool(series: pd.Series) -> pd.Series:
        """
        Map Airbnb "t"/"f" string booleans to Python True/False.

        WHY: Inside Airbnb stores booleans as "t" and "f" strings.
        Without mapping, pandas treats these as object dtype and boolean
        operations (e.g. filtering superhosts) break silently.

        "t" → True  |  "f" → False  |  anything else → NaN
        """
        return series.map({"t": True, "f": False})

    # =========================================================
    # Listings standardization
    # =========================================================

    def standardize_listings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize all format issues in listings.csv.

        Changes made:
            price              : "$150.00" → 150.0
            host_since         : "2015-03-01" → datetime64
            first_review       : string → datetime64
            last_review        : string → datetime64
            last_scraped       : string → datetime64
            calendar_last_scraped: string → datetime64
            host_is_superhost  : "t"/"f" → True/False
            host_has_profile_pic: "t"/"f" → True/False
            host_identity_verified: "t"/"f" → True/False
            instant_bookable   : "t"/"f" → True/False
            has_availability   : "t"/"f" → True/False
            host_response_rate : "97%" → 97.0
            host_acceptance_rate: "85%" → 85.0
            room_type          : normalized to 4 canonical values
            property_type      : normalized to ~15 categories
            all numeric cols   : cast to float/int, non-parseable → NaN
        """
        print("     [standardizer] Standardizing listings ...")
        df = df.copy()

        # ── Price ─────────────────────────────────────────────────
        # FINDING: 43.95% null because raw = "$150.00" strings
        # AFTER cleaning: expect ~95%+ valid prices
        if "price" in df.columns:
            before_null = int(df["price"].isna().sum())
            df["price"] = self._clean_price(df["price"])
            after_null  = int(df["price"].isna().sum())
            recovered   = before_null - after_null
            print(f"       price: recovered {recovered:,} values "
                  f"(null: {before_null:,} → {after_null:,})")

        # ── Date columns ──────────────────────────────────────────
        date_cols = [
            "host_since", "first_review", "last_review",
            "last_scraped", "calendar_last_scraped",
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # ── Boolean columns ───────────────────────────────────────
        bool_cols = [
            "host_is_superhost", "host_has_profile_pic",
            "host_identity_verified", "instant_bookable",
            "has_availability",
        ]
        for col in bool_cols:
            if col in df.columns:
                df[col] = self._map_bool(df[col])

        # ── Percentage columns ────────────────────────────────────
        pct_cols = ["host_response_rate", "host_acceptance_rate"]
        for col in pct_cols:
            if col in df.columns:
                df[col] = self._parse_percentage(df[col])

        # ── Numeric columns ───────────────────────────────────────
        # Cast all numeric fields — non-parseable values → NaN
        numeric_cols = [
            "accommodates", "bedrooms", "beds",
            "minimum_nights", "maximum_nights",
            "minimum_minimum_nights", "maximum_minimum_nights",
            "minimum_maximum_nights", "maximum_maximum_nights",
            "minimum_nights_avg_ntm", "maximum_nights_avg_ntm",
            "number_of_reviews", "number_of_reviews_ltm",
            "number_of_reviews_l30d", "number_of_reviews_ly",
            "availability_30", "availability_60",
            "availability_90", "availability_365", "availability_eoy",
            "review_scores_rating", "review_scores_accuracy",
            "review_scores_cleanliness", "review_scores_checkin",
            "review_scores_communication", "review_scores_location",
            "review_scores_value",
            "host_listings_count", "host_total_listings_count",
            "calculated_host_listings_count",
            "calculated_host_listings_count_entire_homes",
            "calculated_host_listings_count_private_rooms",
            "calculated_host_listings_count_shared_rooms",
            "reviews_per_month",
            "estimated_occupancy_l365d",
            "estimated_revenue_l365d",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ── Room type normalization ───────────────────────────────
        # WHY: Ensures consistent categories for EDA groupby and ML encoding
        # Unknown values → "Other" (safer than NaN — still categorizable)
        if "room_type" in df.columns:
            df["room_type"] = (
                df["room_type"].map(self.ROOM_TYPE_MAP).fillna("Other")
            )
            print(f"       room_type distribution: "
                  f"{df['room_type'].value_counts().to_dict()}")

        # ── Property type normalization ───────────────────────────
        # WHY: Amsterdam has 30+ raw property types from profiling.
        # Normalizing reduces sparsity in ML features.
        # Stored as new column to preserve original for reference.
        if "property_type" in df.columns:
            df["property_type_normalized"] = df["property_type"].apply(
                lambda x: self.PROPERTY_TYPE_MAP.get(str(x).strip(), "Other")
                if pd.notna(x) else np.nan
            )

        print("       [standardizer] Listings standardized ✅")
        return df

    # =========================================================
    # Calendar standardization
    # =========================================================

    def standardize_calendar(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize calendar.csv.

        Changes made:
            date           : "2024-01-15" → datetime64
            month          : NEW — extracted from date (1–12)
            month_name     : NEW — "January", "February" etc.
            day_of_week    : NEW — "Monday", "Tuesday" etc.
            is_weekend     : NEW — True if Saturday or Sunday
            quarter        : NEW — 1, 2, 3, 4
            year           : NEW — extracted from date
            price          : "$150.00" → 150.0
            available      : "t"/"f" → True/False
            adjusted_price : DROPPED (100% null in Amsterdam)
            minimum_nights : cast to numeric
            maximum_nights : cast to numeric
        """
        print("     [standardizer] Standardizing calendar ...")
        df = df.copy()

        # ── Date + temporal features ──────────────────────────────
        # WHY extract temporal features here:
        # These are needed for EVERY temporal analysis in EDA and stats.
        # Computing them once at cleaning time is more efficient than
        # recomputing in every notebook.
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            n_null = int(df["date"].isna().sum())
            if n_null > 0:
                print(f"       Dropping {n_null:,} rows with unparseable dates")
                df = df.dropna(subset=["date"])

            df["month"]       = df["date"].dt.month
            df["month_name"]  = df["date"].dt.month_name()
            df["day_of_week"] = df["date"].dt.day_name()
            df["is_weekend"]  = df["date"].dt.dayofweek >= 5
            df["quarter"]     = df["date"].dt.quarter
            df["year"]        = df["date"].dt.year

        # ── Price ─────────────────────────────────────────────────
        # FINDING from profiling: calendar.price was 100% null
        # REASON: same "$150.00" string format as listings — never parsed
        # AFTER cleaning: will have valid numeric prices for seasonal analysis
        if "price" in df.columns:
            df["price"] = self._clean_price(df["price"])
            n_valid = int(df["price"].notna().sum())
            print(f"       calendar price: {n_valid:,} valid values after cleaning")

        # ── adjusted_price ────────────────────────────────────────
        # FINDING from profiling: 100% null in Amsterdam dataset
        # DECISION: drop entirely — zero analytical value, wastes memory
        # DOCUMENTED in: docs/decision_log.md  +  docs/assumptions_log.md
        if "adjusted_price" in df.columns:
            null_pct = df["adjusted_price"].isna().mean() * 100
            if null_pct == 100.0:
                df = df.drop(columns=["adjusted_price"])
                print("       adjusted_price dropped (100% null)")

        # ── Availability ──────────────────────────────────────────
        if "available" in df.columns:
            df["available"] = self._map_bool(df["available"])

        # ── Numeric ───────────────────────────────────────────────
        for col in ["minimum_nights", "maximum_nights"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        print("       [standardizer] Calendar standardized ✅")
        return df

    # =========================================================
    # Reviews standardization
    # =========================================================

    def standardize_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize reviews.csv.

        Changes made:
            date             : "2023-06-15" → datetime64
            review_year      : NEW — extracted from date
            review_month     : NEW — extracted from date
            id / listing_id / reviewer_id : cast to numeric
            comments         : strip leading/trailing whitespace
            _has_text        : NEW — True if comment length > 10 chars
            _is_auto_review  : NEW — True if auto-generated text detected
        """
        print("     [standardizer] Standardizing reviews ...")
        df = df.copy()

        # ── Date ──────────────────────────────────────────────────
        if "date" in df.columns:
            df["date"]         = pd.to_datetime(df["date"], errors="coerce")
            df["review_year"]  = df["date"].dt.year
            df["review_month"] = df["date"].dt.month

        # ── Numeric IDs ───────────────────────────────────────────
        for col in ["id", "listing_id", "reviewer_id"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ── Comments ──────────────────────────────────────────────
        if "comments" in df.columns:
            df["comments"] = df["comments"].astype(str).str.strip()

            # Flag: does this review have meaningful text?
            # WHY: short/empty reviews are useless for NLP/sentiment analysis
            df["_has_text"] = df["comments"].str.len() > 10

            # Flag: auto-generated reviews (host cancellation notices, etc.)
            # WHY: these inflate review counts without reflecting guest experience
            df["_is_auto_review"] = df["comments"].str.lower().str.contains(
                r"the host canceled|automatically collected|this is an automated",
                na=False,
                regex=True
            )
            n_auto = int(df["_is_auto_review"].sum())
            if n_auto > 0:
                print(f"       _is_auto_review: {n_auto:,} auto-generated reviews flagged")

        print("       [standardizer] Reviews standardized ✅")
        return df
