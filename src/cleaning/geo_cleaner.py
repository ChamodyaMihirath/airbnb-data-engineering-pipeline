"""
geo_cleaner.py  —  Section 3.2: Geographic Field Standardization
----------------------------------------------------------------
Handles all geographic normalization across datasets.

WHY a separate geo module:
    Geographic data has unique normalization concerns (coordinate precision,
    canonical naming, bounding box validation) that are distinct from
    general type standardization or missing value handling.

What this module does:
    1. Round coordinates to appropriate precision
    2. Validate coordinates within Netherlands bounding box
    3. Standardize neighbourhood names to Title Case
    4. Add explicit city column for future multi-city pipeline
    5. Standardize neighbourhood table

Amsterdam bounding box used for validation:
    Latitude:  52.2 – 52.5  (city proper)
    Longitude: 4.7  – 5.1   (city proper)

    WHY these bounds (not Netherlands-wide):
        Inside Airbnb Amsterdam data should only contain listings
        within the city. Listings outside these bounds are either
        data errors or misclassified listings from other cities.
"""

import pandas as pd
import numpy as np


# Amsterdam geographic bounds
AMSTERDAM_LAT_MIN = 52.20
AMSTERDAM_LAT_MAX = 52.50
AMSTERDAM_LON_MIN = 4.70
AMSTERDAM_LON_MAX = 5.10

# Coordinate precision
# 5 decimal places ≈ 1.1m precision — sufficient for neighbourhood-level analysis
# Inside Airbnb already jitters coordinates ~150m for host privacy,
# so storing more than 5 decimal places adds no real precision
COORDINATE_PRECISION = 5


class GeoCleaner:

    # =========================================================
    # Listings geographic cleaning
    # =========================================================

    def clean_listings_geo(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize all geographic fields in listings.

        Changes made:
            latitude               : rounded to 5 decimal places
            longitude              : rounded to 5 decimal places
            latitude/longitude     : values outside Amsterdam bounds → NaN
            neighbourhood_cleansed : Title Case, stripped whitespace
            neighbourhood_group_cleansed: Title Case, stripped whitespace
            city                   : NEW column = "Amsterdam"

        WHY neighbourhood_cleansed and NOT neighbourhood:
            From profiling: raw 'neighbourhood' column is >50% null.
            'neighbourhood_cleansed' is standardized by Inside Airbnb
            and is always populated. We use this as the canonical field.
        """
        print("     [geo_cleaner] Cleaning listings geography ...")
        df = df.copy()

        # ── Coordinate rounding ───────────────────────────────────
        # WHY round to 5 decimal places:
        #   - 5 dp ≈ 1.1m ground precision
        #   - Inside Airbnb jitters coords ~150m for privacy anyway
        #   - Rounding reduces false "uniqueness" in spatial joins
        if "latitude" in df.columns:
            df["latitude"] = pd.to_numeric(
                df["latitude"], errors="coerce"
            ).round(COORDINATE_PRECISION)

        if "longitude" in df.columns:
            df["longitude"] = pd.to_numeric(
                df["longitude"], errors="coerce"
            ).round(COORDINATE_PRECISION)

        # ── Bounding box validation ───────────────────────────────
        # WHY: listings outside Amsterdam city bounds are data errors.
        # Setting coords to NaN flags them via _is_valid=False.
        # We do NOT drop — the listing may still have valid price/review data.
        if "latitude" in df.columns and "longitude" in df.columns:
            outside_bounds = ~(
                df["latitude"].between(AMSTERDAM_LAT_MIN, AMSTERDAM_LAT_MAX) &
                df["longitude"].between(AMSTERDAM_LON_MIN, AMSTERDAM_LON_MAX)
            )
            # Exclude NaN from count (they are already null, not "outside")
            n_outside = int(
                outside_bounds[df["latitude"].notna() & df["longitude"].notna()].sum()
            )
            if n_outside > 0:
                df.loc[outside_bounds, ["latitude", "longitude"]] = np.nan
                print(f"       Coords: {n_outside} listings outside Amsterdam "
                      f"bounds → set to NaN")
            else:
                print("       Coords: all listings within Amsterdam bounds ✅")

        # ── neighbourhood_cleansed ────────────────────────────────
        # WHY Title Case + strip:
        #   Prevents "centrum" and "Centrum" being treated as different
        #   neighbourhoods in groupby operations.
        if "neighbourhood_cleansed" in df.columns:
            df["neighbourhood_cleansed"] = (
                df["neighbourhood_cleansed"]
                  .astype(str)
                  .str.strip()
                  .str.title()
            )
            n_unique = df["neighbourhood_cleansed"].nunique()
            print(f"       neighbourhood_cleansed: {n_unique} unique neighbourhoods")

        # ── neighbourhood_group_cleansed ──────────────────────────
        if "neighbourhood_group_cleansed" in df.columns:
            df["neighbourhood_group_cleansed"] = (
                df["neighbourhood_group_cleansed"]
                  .astype(str)
                  .str.strip()
                  .str.title()
                  .where(lambda s: s != "Nan", other=np.nan)   # convert "Nan" string back to NaN
            )

        # ── City column ───────────────────────────────────────────
        # WHY add city:
        #   Enables multi-city pipeline in future — when we add Paris, London
        #   etc., the master table needs a city discriminator column.
        #   Adding it now costs nothing and makes enrichment joins cleaner.
        df["city"] = "Amsterdam"

        print("       [geo_cleaner] Listings geography cleaned ✅")
        return df

    # =========================================================
    # Neighbourhoods table cleaning
    # =========================================================

    def clean_neighbourhoods(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize the neighbourhoods reference table (22 rows × 2 cols).

        Columns: neighbourhood, neighbourhood_group

        Changes made:
            neighbourhood       : Title Case, stripped whitespace
            neighbourhood_group : Title Case, stripped whitespace

        WHY Title Case:
            Must match the Title Case applied to neighbourhood_cleansed
            in clean_listings_geo() so that JOIN operations work correctly
            in enrichment/joins.py.
        """
        print("     [geo_cleaner] Cleaning neighbourhoods table ...")
        df = df.copy()

        for col in df.columns:
            df[col] = (
                df[col]
                  .astype(str)
                  .str.strip()
                  .str.title()
                  .replace("Nan", np.nan)
            )

        print(f"       {df.shape[0]} neighbourhoods standardized ✅")
        return df
