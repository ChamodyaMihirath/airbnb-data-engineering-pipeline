"""
cleaner.py  —  Section 3.2: Data Cleaning & Standardization
------------------------------------------------------------
Orchestrator that coordinates all cleaning sub-modules:

    standardizer.py      → price, dates, booleans, percentages, categoricals
    missing_values.py    → missing value strategies per column
    geo_cleaner.py       → coordinates, neighbourhood names, city field

Pipeline per dataset:
    1. Standardize       (standardizer.py)
    2. Handle missing    (missing_values.py)
    3. Clean geographic  (geo_cleaner.py)
    4. Add validity flag (_is_valid)
    5. Save to parquet

Known data issues handled here (from profiling output):
    - listings.price       : 43.95% null  → "$150.00" strings need parsing
    - calendar.price       : 100% null    → same $ string issue
    - adjusted_price       : 100% null    → dropped entirely
    - minimum_nights       : max = 1001   → capped at 365
    - maximum_nights       : max = 2,147,483,647 (INT_MAX sentinel) → NaN
    - estimated_occupancy  : max = 255    → capped at 365
    - neighbourhood        : >50% null    → use neighbourhood_cleansed instead

Usage:
    from cleaning.cleaner import DataCleaner
    cleaner        = DataCleaner()
    clean_datasets = cleaner.clean_all(datasets)
    cleaner.save_cleaned(clean_datasets, output_path)
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from cleaning.standardizer import DataStandardizer
    from cleaning.missing_values import MissingValueHandler
    from cleaning.geo_cleaner import GeoCleaner
else:
    from .standardizer import DataStandardizer
    from .missing_values import MissingValueHandler
    from .geo_cleaner import GeoCleaner


class DataCleaner:
    """
    Orchestrates all cleaning sub-modules.
    Each sub-module handles one specific concern:
        DataStandardizer    → format standardization
        MissingValueHandler → null treatment strategies
        GeoCleaner          → geographic field normalization
    """

    def __init__(self):
        self.standardizer = DataStandardizer()
        self.missing      = MissingValueHandler()
        self.geo          = GeoCleaner()

    # =========================================================
    # Listings  (10,480 rows × 79 cols)
    # =========================================================

    def clean_listings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full cleaning pipeline for listings.

        Why this order:
            1. Standardize first  — so missing handler works on correct dtypes
            2. Handle missing     — after types are fixed, strategies are accurate
            3. Geo clean last     — depends on neighbourhood_cleansed being a string
            4. Validity flag      — after all cleaning, flag what is usable
        """
        print("\n  -- Cleaning listings ------------------------------------------")
        df = df.copy()

        # Step 1: Standardize
        # price "$150.00" -> 150.0
        # dates -> datetime
        # "t"/"f" -> True/False
        # "97%" -> 97.0
        # room_type / property_type -> normalized categories
        df = self.standardizer.standardize_listings(df)

        # Step 2: Handle missing values
        # minimum_nights > 365 -> cap at 365
        # availability_365 -> clip [0, 365]
        # estimated_occupancy > 365 -> cap at 365
        # review_scores_* -> keep NaN (no imputation)
        # bedrooms / beds -> keep NaN (no imputation)
        df = self.missing.handle_listings(df)

        # Step 3: Geographic cleaning
        # coordinates -> round to 5 decimal places
        # neighbourhood_cleansed -> Title Case, strip whitespace
        # add city = "Amsterdam"
        df = self.geo.clean_listings_geo(df)

        # Step 4: Validity flag
        # A listing is valid for analysis if it has:
        # price + coordinates + room_type (minimum for any analysis)
        df["_is_valid"] = (
            df["price"].notna() &
            df["latitude"].notna() &
            df["longitude"].notna() &
            df["room_type"].notna()
        )
        n_valid   = int(df["_is_valid"].sum())
        n_invalid = int((~df["_is_valid"]).sum())
        print(f"     _is_valid: {n_valid:,} valid | {n_invalid:,} flagged as invalid")

        if n_invalid > 0:
            null_price  = int(df[~df["_is_valid"]]["price"].isna().sum())
            null_coords = int(df[~df["_is_valid"]]["latitude"].isna().sum())
            print(f"     Invalid breakdown -> null price: {null_price} | null coords: {null_coords}")

        print(f"     OK Listings done: {df.shape[0]:,} rows x {df.shape[1]} cols")
        return df

    # =========================================================
    # Calendar  (3,825,200 rows × 7 cols)
    # =========================================================

    def clean_calendar(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full cleaning pipeline for calendar.

        Key issues from profiling:
            - price is 100% null in raw ($ strings not parsed) -> standardizer fixes
            - adjusted_price is 100% null -> standardizer drops it
            - maximum_nights = 2,147,483,647 (INT_MAX) -> missing handler replaces with NaN
            - minimum_nights max = 1001 -> missing handler caps at 365
        """
        print("\n  -- Cleaning calendar ------------------------------------------")
        df = df.copy()

        # Step 1: Standardize
        # date -> datetime + temporal features (month, day_of_week, is_weekend)
        # price "$150.00" -> float
        # available "t"/"f" -> bool
        # adjusted_price (100% null) -> dropped
        df = self.standardizer.standardize_calendar(df)

        # Step 2: Handle missing values
        # maximum_nights INT_MAX sentinel -> NaN
        # minimum_nights > 365 -> cap at 365
        df = self.missing.handle_calendar(df)

        print(f"     OK Calendar done: {df.shape[0]:,} rows x {df.shape[1]} cols")
        return df

    # =========================================================
    # Reviews  (501,084 rows × 6 cols)
    # =========================================================

    def clean_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full cleaning pipeline for reviews.
        Columns: listing_id, id, date, reviewer_id, reviewer_name, comments
        """
        print("\n  -- Cleaning reviews -------------------------------------------")
        df = df.copy()

        # Step 1: Standardize
        # date -> datetime + review_year, review_month
        # IDs -> numeric
        # comments -> strip whitespace
        # _has_text flag (len > 10)
        # _is_auto_review flag (auto-generated text detection)
        df = self.standardizer.standardize_reviews(df)

        # Step 2: Handle missing values
        # null comments -> keep NaN (cannot impute text)
        # null dates -> keep NaN (flag for temporal analysis)
        df = self.missing.handle_reviews(df)

        print(f"     OK Reviews done: {df.shape[0]:,} rows x {df.shape[1]} cols")
        return df

    # =========================================================
    # Neighbourhoods  (22 rows × 2 cols)
    # =========================================================

    def clean_neighbourhoods(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize to Title Case, strip whitespace."""
        print("\n  -- Cleaning neighbourhoods ------------------------------------")
        df = df.copy()
        df = self.geo.clean_neighbourhoods(df)
        print(f"     OK Neighbourhoods done: {df.shape[0]} rows x {df.shape[1]} cols")
        return df

    # =========================================================
    # Run all datasets
    # =========================================================

    def clean_all(self, datasets: dict) -> dict:
        """
        Run full cleaning pipeline on all datasets.

        Args:
            datasets: dict from DataLoader.load_all()

        Returns:
            dict of cleaned DataFrames with same keys
        """
        print("\n" + "=" * 55)
        print("  SECTION 3.2 - DATA CLEANING & STANDARDIZATION")
        print("=" * 55)

        cleaned = {
            "listings":       self.clean_listings(datasets["listings"]),
            "calendar":       self.clean_calendar(datasets["calendar"]),
            "reviews":        self.clean_reviews(datasets["reviews"]),
            "neighbourhoods": self.clean_neighbourhoods(datasets["neighbourhoods"]),
        }

        print("\n-- Cleaning Summary " + "-" * 35)
        for name, df in cleaned.items():
            print(f"  {name:20s}: {df.shape[0]:>10,} rows x {df.shape[1]:>3} cols")

        print("\nOK All datasets cleaned successfully")
        return cleaned

    # =========================================================
    # Save cleaned files
    # =========================================================

    def save_cleaned(self, clean_datasets: dict, output_dir) -> None:
        """
        Save all cleaned DataFrames as parquet files.

        Why parquet and not CSV:
            - Preserves dtypes exactly (datetime, bool, float - no re-parsing)
            - Roughly 5x smaller file size than CSV for this dataset
            - Much faster to read back in notebooks and enrichment pipeline

        Args:
            clean_datasets: dict of cleaned DataFrames
            output_dir:     Path or string to output directory
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        print("\n-- Saving cleaned files " + "-" * 30)
        for name, df in clean_datasets.items():
            if isinstance(df, pd.DataFrame):
                path = out / f"{name}_clean.parquet"
                df.to_parquet(path, index=False)
                size_mb = path.stat().st_size / 1_048_576
                print(f"  OK {name}_clean.parquet  "
                      f"({df.shape[0]:,} rows | {size_mb:.1f} MB)")

        print(f"\n  All files saved to: {out}")
