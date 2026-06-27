"""
missing_values.py  —  Section 3.2: Missing Value Strategies
------------------------------------------------------------
Handles all missing value decisions across datasets.

WHY a separate module:
    Missing value treatment is a deliberate analytical decision —
    not just a technical cleanup step. Each column needs its own
    strategy based on what the null means in the business domain.

Strategies used in this dataset:

    EXPLICIT NaN (keep as null):
        Used when: the absence of a value IS meaningful information
        Examples:
            review_scores_rating  → listing has no reviews yet (not score=0)
            bedrooms              → unknown layout (not 0 bedrooms)
            host_response_rate    → host has not responded (not 0%)
            price                 → unknown price (not free)

    IMPUTATION (fill with computed value):
        Used when: missing is random and filling won't distort analysis
        Examples:
            beds → fill with accommodates/2 (reasonable proxy)
            reviews_per_month → fill with 0 if number_of_reviews = 0

    SENTINEL VALUE (fill with special flag):
        Used when: we want to keep the row but mark the missing clearly
        Examples:
            host_response_time → fill "unknown" (categorical, not ordinal)

    CAP / CLIP (replace extreme values):
        Used when: outlier is a data error, not a real value
        Examples:
            minimum_nights > 365  → cap at 365 (profiling found max=1001)
            maximum_nights = INT_MAX → replace with NaN (sentinel value)
            estimated_occupancy > 365 → cap at 365 (profiling found max=255)

    DROP ROW:
        Used when: row is unusable without this field
        Examples:
            calendar rows with null date → drop (date is the primary key)

All decisions are documented with reasoning below each method.
"""

import pandas as pd
import numpy as np


class MissingValueHandler:

    # =========================================================
    # Listings
    # =========================================================

    def handle_listings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply missing value strategies to listings.

        Called AFTER standardizer — so dtypes are already correct.
        """
        print("     [missing_values] Handling listings ...")
        df = df.copy()

        # ── price: keep NaN ───────────────────────────────────────
        # STRATEGY: explicit NaN
        # WHY: We cannot impute price — it is the primary target variable.
        # Imputing with mean/median would introduce bias into price analysis.
        # Listings with null price are flagged via _is_valid=False.
        # (Already NaN after standardizer — no action needed here)

        # ── bedrooms / beds: keep NaN ────────────────────────────
        # STRATEGY: explicit NaN
        # WHY: Imputing 0 would mean "studio/no bedroom" which is a real
        # category, not a substitute for missing data. NaN is more honest.
        # These columns are used in price_per_bedroom — NaN propagates correctly.

        # ── review_scores_*: keep NaN ────────────────────────────
        # STRATEGY: explicit NaN
        # WHY: A null review score means the listing has no reviews yet.
        # Filling with 0 would make it look like a bad listing.
        # Filling with mean would artificially inflate the score distribution.
        # NaN correctly represents "not yet rated".

        # ── host_response_rate: keep NaN ─────────────────────────
        # STRATEGY: explicit NaN
        # WHY: Missing response rate means the host hasn't received messages
        # yet, or has hidden it. This is different from "0% response rate".
        # Keep NaN and exclude from response rate analysis.

        # ── host_response_time: sentinel value ───────────────────
        # STRATEGY: sentinel value "Unknown"
        # WHY: This is a categorical column used for segmentation.
        # NaN would be excluded from groupby counts.
        # "Unknown" keeps the row in categorical analysis as its own group.
        if "host_response_time" in df.columns:
            df["host_response_time"] = df["host_response_time"].fillna("Unknown")

        # ── beds: impute from accommodates ───────────────────────
        # STRATEGY: imputation (rule-based)
        # WHY: beds is only 2.92% null (from profiling).
        # A reasonable proxy: beds ≈ ceil(accommodates / 2)
        # This is better than mean imputation because it uses listing context.
        # CAVEAT: documented in assumptions_log.md
        if "beds" in df.columns and "accommodates" in df.columns:
            mask = df["beds"].isna() & df["accommodates"].notna()
            df.loc[mask, "beds"] = np.ceil(df.loc[mask, "accommodates"] / 2)
            n_imputed = int(mask.sum())
            if n_imputed > 0:
                print(f"       beds: imputed {n_imputed} nulls from accommodates/2")

        # ── reviews_per_month: fill 0 if no reviews ──────────────
        # STRATEGY: imputation (conditional)
        # WHY: If number_of_reviews = 0, then reviews_per_month should be 0.
        # Missing here is a data gap, not meaningful absence.
        if "reviews_per_month" in df.columns and "number_of_reviews" in df.columns:
            mask = (
                df["reviews_per_month"].isna() &
                (df["number_of_reviews"].fillna(0) == 0)
            )
            df.loc[mask, "reviews_per_month"] = 0.0
            n_filled = int(mask.sum())
            if n_filled > 0:
                print(f"       reviews_per_month: filled {n_filled} with 0.0 "
                      f"(listings with 0 reviews)")

        # ── minimum_nights: cap at 365 ───────────────────────────
        # STRATEGY: cap outlier
        # FINDING from profiling: minimum_nights max = 1001
        # WHY: A minimum stay of 1001 nights is not a valid short-term rental.
        # This is almost certainly a data entry error.
        # DECISION: cap at 365 (1 year) — not drop, because the listing
        # itself is valid for all other analyses (price, location, reviews).
        if "minimum_nights" in df.columns:
            n_capped = int((df["minimum_nights"] > 365).sum())
            df["minimum_nights"] = df["minimum_nights"].clip(upper=365)
            if n_capped > 0:
                print(f"       minimum_nights: capped {n_capped} values at 365 "
                      f"(was up to 1001)")

        # ── availability_365: clip to [0, 365] ───────────────────
        # STRATEGY: clip to valid domain range
        # WHY: availability_365 must be between 0 and 365 by definition.
        # Values outside this range are data errors.
        if "availability_365" in df.columns:
            df["availability_365"] = df["availability_365"].clip(lower=0, upper=365)

        # ── estimated_occupancy_l365d: cap at 365 ────────────────
        # STRATEGY: cap outlier
        # FINDING from profiling: max = 255 (unusual but within range)
        # Cap defensively at 365 — occupancy days cannot exceed days in year
        if "estimated_occupancy_l365d" in df.columns:
            n_capped = int((df["estimated_occupancy_l365d"] > 365).sum())
            df["estimated_occupancy_l365d"] = df["estimated_occupancy_l365d"].clip(
                lower=0, upper=365
            )
            if n_capped > 0:
                print(f"       estimated_occupancy_l365d: capped {n_capped} values")

        # ── Derived fields (added here, not in standardizer) ─────

        # Host tenure in years since joining platform
        # WHY here: depends on host_since being datetime (set by standardizer)
        if "host_since" in df.columns:
            df["host_tenure_years"] = (
                (pd.Timestamp.now() - df["host_since"]).dt.days / 365.25
            ).round(2).clip(lower=0)

        # Price per bedroom
        # WHY: strong pricing signal for EDA and ML feature engineering
        # NaN when bedrooms = 0 or NaN (avoids division by zero)
        if "price" in df.columns and "bedrooms" in df.columns:
            df["price_per_bedroom"] = np.where(
                df["bedrooms"].fillna(0) > 0,
                (df["price"] / df["bedrooms"]).round(2),
                np.nan
            )

        # Review frequency (per month, derived)
        # WHY: reviews_per_month may be null for new hosts — derive from raw counts
        if ("reviews_per_month" not in df.columns or
                df.get("reviews_per_month", pd.Series()).isna().all()):
            if "number_of_reviews" in df.columns and "host_since" in df.columns:
                months_active = (
                    (pd.Timestamp.now() - df["host_since"]).dt.days / 30.44
                ).clip(lower=1)
                df["review_frequency"] = (
                    df["number_of_reviews"] / months_active
                ).round(4)

        # Host segment by portfolio size
        # WHY: needed for supply-side analysis (Section 4.4)
        # Segments: single-listing casual hosts vs. commercial operators
        if "host_total_listings_count" in df.columns:
            df["host_segment"] = pd.cut(
                df["host_total_listings_count"].fillna(1),
                bins=[0, 1, 5, 20, np.inf],
                labels=[
                    "Single-listing",
                    "Small (2-5)",
                    "Medium (6-20)",
                    "Commercial (20+)"
                ],
                right=True
            )

        print("       [missing_values] Listings handled ✅")
        return df

    # =========================================================
    # Calendar
    # =========================================================

    def handle_calendar(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply missing value strategies to calendar.

        Called AFTER standardizer — date is already datetime,
        price is already float, available is already bool.
        """
        print("     [missing_values] Handling calendar ...")
        df = df.copy()

        # ── maximum_nights INT_MAX sentinel → NaN ─────────────────
        # STRATEGY: replace sentinel with NaN
        # FINDING from profiling: max value = 2,147,483,647 (= 2^31 - 1 = INT_MAX)
        # WHY: This is a programming sentinel meaning "no maximum nights limit".
        # It is NOT a real value. Using it in calculations would produce
        # nonsensical results (e.g. average max nights = millions).
        # DECISION: replace with NaN — "no maximum" is best represented as null.
        INT_MAX = 2_147_483_647
        if "maximum_nights" in df.columns:
            n_sentinel = int((df["maximum_nights"] == INT_MAX).sum())
            if n_sentinel > 0:
                df["maximum_nights"] = df["maximum_nights"].replace(INT_MAX, np.nan)
                print(f"       maximum_nights: replaced {n_sentinel:,} INT_MAX "
                      f"sentinels with NaN")

        # ── minimum_nights: cap at 365 ────────────────────────────
        # STRATEGY: cap outlier (same as listings)
        # FINDING: calendar minimum_nights also has values up to 1001
        if "minimum_nights" in df.columns:
            n_capped = int((df["minimum_nights"].fillna(0) > 365).sum())
            df["minimum_nights"] = df["minimum_nights"].clip(upper=365)
            if n_capped > 0:
                print(f"       minimum_nights: capped {n_capped:,} values at 365")

        # ── price: keep NaN ───────────────────────────────────────
        # STRATEGY: explicit NaN
        # WHY: Cannot impute daily price — too variable (weekend vs weekday,
        # seasonal spikes). NaN days are excluded from seasonal price analysis.

        print("       [missing_values] Calendar handled ✅")
        return df

    # =========================================================
    # Reviews
    # =========================================================

    def handle_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply missing value strategies to reviews.

        Called AFTER standardizer — date is already datetime,
        _has_text and _is_auto_review flags are already set.
        """
        print("     [missing_values] Handling reviews ...")
        df = df.copy()

        # ── comments: keep NaN ────────────────────────────────────
        # STRATEGY: explicit NaN
        # WHY: Cannot impute text — every review is unique.
        # Null comments are flagged via _has_text=False.
        # They are excluded from NLP/sentiment analysis but
        # retained for review COUNT metrics (number_of_reviews still valid).

        # ── date: keep NaN ────────────────────────────────────────
        # STRATEGY: explicit NaN
        # WHY: Null dates (0.01% from profiling) cannot be reliably imputed.
        # These rows are excluded from temporal trend analysis only.
        # All other fields (listing_id, reviewer, comments) remain usable.

        print("       [missing_values] Reviews handled ✅")
        return df
