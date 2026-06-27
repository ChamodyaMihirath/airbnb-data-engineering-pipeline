# src/ingestion/validator.py

from pathlib import Path
import pandas as pd


class DataValidator:

    REQUIRED_COLUMNS = {
        "listings": ["id", "host_id", "price", "room_type",
                     "latitude", "longitude", "neighbourhood_cleansed"],
        "calendar": ["listing_id", "date", "available", "price",
                     "adjusted_price", "minimum_nights", "maximum_nights"],
        "reviews":  ["listing_id", "id", "date", "reviewer_id",
                     "reviewer_name", "comments"],
        "neighbourhoods": ["neighbourhood"]
    }

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    # ── File-level checks ──────────────────────────────────────────
    def file_exists(self, filename: str) -> bool:
        return (self.data_dir / filename).exists()

    def file_not_empty(self, df: pd.DataFrame) -> bool:
        return not df.empty

    def required_columns_exist(self, df: pd.DataFrame, name: str) -> bool:
        required = self.REQUIRED_COLUMNS[name]
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"    Missing columns: {missing}")
        return len(missing) == 0

    # ── Domain-level checks (the valuable additions) ───────────────
    def check_listings(self, df: pd.DataFrame) -> list:
        """Business rule checks specific to listings."""
        issues = []

        # Price must be positive (after stripping $ sign)
        prices = df["price"].astype(str).str.replace(r"[\$,]", "", regex=True)
        prices = pd.to_numeric(prices, errors="coerce")
        zero_price = (prices <= 0).sum()
        null_price = prices.isna().sum()
        if zero_price > 0:
            issues.append(f"  {zero_price:,} listings with price ≤ 0")
        if null_price > 0:
            issues.append(f"  {null_price:,} listings with unparseable price")

        # Coordinates must be within Netherlands bounding box
        # Netherlands: lat 50.7–53.6, lon 3.3–7.3
        invalid_lat = (~df["latitude"].between(50.7, 53.6)).sum()
        invalid_lon = (~df["longitude"].between(3.3, 7.3)).sum()
        if invalid_lat > 0:
            issues.append(f"  {invalid_lat} listings with invalid latitude")
        if invalid_lon > 0:
            issues.append(f"  {invalid_lon} listings with invalid longitude")

        # Duplicate listing IDs
        dupes = df["id"].duplicated().sum()
        if dupes > 0:
            issues.append(f"  {dupes} duplicate listing IDs")

        # Availability sanity check (0–365)
        if "availability_365" in df.columns:
            bad_avail = (~df["availability_365"].between(0, 365)).sum()
            if bad_avail > 0:
                issues.append(f"  {bad_avail} listings with availability_365 out of range")

        # Your dataset has pre-computed estimated_revenue_l365d — check it
        if "estimated_revenue_l365d" in df.columns:
            neg_rev = (pd.to_numeric(df["estimated_revenue_l365d"],
                                     errors="coerce") < 0).sum()
            if neg_rev > 0:
                issues.append(f"  {neg_rev} listings with negative estimated revenue")

        return issues

    def check_calendar(self, df: pd.DataFrame) -> list:
        """Business rule checks specific to calendar."""
        issues = []

        # available must only be 't' or 'f'
        valid_vals = {"t", "f"}
        invalid_avail = (~df["available"].isin(valid_vals)).sum()
        if invalid_avail > 0:
            issues.append(f"  {invalid_avail} calendar rows with invalid 'available' value")

        # Date range check — should be ~365 days from scrape date
        dates = pd.to_datetime(df["date"], errors="coerce")
        null_dates = dates.isna().sum()
        if null_dates > 0:
            issues.append(f"  {null_dates} calendar rows with unparseable dates")
        else:
            date_range = (dates.max() - dates.min()).days
            if date_range < 300:
                issues.append(f"  Calendar only spans {date_range} days (expected ~365)")

        # adjusted_price exists in your dataset — check for nulls
        if "adjusted_price" in df.columns:
            null_adj = df["adjusted_price"].isna().sum()
            pct = round(null_adj / len(df) * 100, 1)
            if pct > 20:
                issues.append(f"  adjusted_price is {pct}% null")

        return issues

    def check_reviews(self, df: pd.DataFrame) -> list:
        """Business rule checks specific to reviews."""
        issues = []

        # Duplicate review IDs
        dupes = df["id"].duplicated().sum()
        if dupes > 0:
            issues.append(f"  {dupes} duplicate review IDs")

        # Empty comments
        empty = df["comments"].isna().sum()
        pct = round(empty / len(df) * 100, 1)
        if pct > 10:
            issues.append(f"  {pct}% of reviews have null comments")

        # Date check
        dates = pd.to_datetime(df["date"], errors="coerce")
        if dates.isna().sum() > 0:
            issues.append(f"  {dates.isna().sum()} reviews with invalid dates")

        return issues

    # ── Main validate methods ──────────────────────────────────────
    def validate_dataset(self, df: pd.DataFrame, name: str, filename: str) -> bool:
        print(f"\n── Validating {name} ──────────────────────────")
        print(f"   Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

        if not self.file_exists(filename):
            print("    File does not exist.")
            return False

        if not self.file_not_empty(df):
            print("    Dataset is empty.")
            return False

        if not self.required_columns_exist(df, name):
            print("    Required columns missing.")
            return False

        # Domain checks
        domain_checker = {
            "listings":  self.check_listings,
            "calendar":  self.check_calendar,
            "reviews":   self.check_reviews,
        }
        if name in domain_checker:
            issues = domain_checker[name](df)
            if issues:
                for issue in issues:
                    print(f"   {issue}")
            else:
                print("   ✅ All domain checks passed")

        print(f"   ✅ Validation passed")
        return True

    def validate_all(self, datasets: dict) -> dict:
        print("=" * 50)
        print("  DATA VALIDATION REPORT")
        print("=" * 50)

        results = {}
        for name, filename in [
            ("listings",      "listings.csv.gz"),
            ("calendar",      "calendar.csv.gz"),
            ("reviews",       "reviews.csv.gz"),
            ("neighbourhoods","neighbourhoods.csv"),
        ]:
            results[name] = self.validate_dataset(datasets[name], name, filename)

        passed = sum(results.values())
        print(f"\n{'='*50}")
        print(f"  Result: {passed}/{len(results)} datasets passed validation")
        print("=" * 50)
        return results