"""
joins.py  —  Section 3.3: Data Enrichment & Joining
----------------------------------------------------
Joins all cleaned datasets to produce the enriched master listings table.

Join strategy:
    Base: listings_clean           (10,480 rows — all listings)
    LEFT JOIN reviews summary      (aggregated per listing_id)
    LEFT JOIN calendar summary     (aggregated per listing_id)
    LEFT JOIN neighbourhood stats  (aggregated per neighbourhood)

Why LEFT JOIN everywhere:
    We never want to lose a listing row because it has no reviews or
    no calendar data. LEFT JOIN preserves all 10,480 listings and fills
    unmatched columns with NaN — which is the correct representation
    (no reviews = NaN review stats, not excluded from dataset).

Output: master_listings DataFrame
    One row per listing, all enriched fields included.
    Saved to data/processed/master_listings.parquet

Usage:
    from enrichment.joins import DataJoiner
    joiner = DataJoiner()
    master = joiner.build_master(clean_datasets)
"""

import pandas as pd
import numpy as np
from pathlib import Path


class DataJoiner:

    # =========================================================
    # Review summary aggregation
    # =========================================================

    def build_review_summary(self, reviews: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate reviews to one row per listing_id.

        Why aggregate before joining:
            reviews has 501,084 rows. Joining directly to listings would
            create a many-to-one explosion — 10,480 listings × many reviews.
            We pre-aggregate to one row per listing, then join cleanly.

        Computed fields:
            review_count        : total reviews for this listing
            latest_review_date  : most recent review date
            earliest_review_date: first review date
            active_months       : months between first and last review
            reviews_per_month_computed : review_count / active_months
        """
        print("  [joins] Building review summary ...")

        # Filter to reviews with valid listing_id
        reviews = reviews[reviews["listing_id"].notna()].copy()

        summary = reviews.groupby("listing_id").agg(
            review_count          = ("id",           "count"),
            latest_review_date    = ("date",         "max"),
            earliest_review_date  = ("date",         "min"),
            has_text_review_count = ("_has_text",    "sum"),
        ).reset_index()

        # Compute active months (time between first and last review)
        summary["active_review_months"] = (
            (summary["latest_review_date"] - summary["earliest_review_date"])
            .dt.days / 30.44
        ).round(2)

        # Review frequency: reviews per active month
        # Avoid division by zero for listings with only 1 review
        summary["reviews_per_month_computed"] = np.where(
            summary["active_review_months"] > 0,
            (summary["review_count"] / summary["active_review_months"]).round(4),
            0.0
        )

        print(f"     Review summary: {len(summary):,} listings have reviews")
        return summary

    # =========================================================
    # Calendar summary aggregation
    # =========================================================

    def build_calendar_summary(self, calendar: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate calendar to one row per listing_id.

        Why aggregate before joining:
            calendar has 3,825,200 rows (365 days × ~10,480 listings).
            We aggregate to per-listing occupancy and availability stats.

        Computed fields:
            total_days          : total calendar days available in dataset
            booked_days         : days where available = False
            available_days      : days where available = True
            occupancy_rate      : booked_days / total_days
            weekend_booked_days : booked days on weekends
            weekday_booked_days : booked days on weekdays
            peak_month          : month with highest booked days

        Note on occupancy:
            available=False is treated as booked (Inside Airbnb methodology).
            Host-blocked days are indistinguishable — occupancy is upper bound.
            Documented in assumptions_log C-01.
        """
        print("  [joins] Building calendar summary ...")

        cal = calendar.copy()

        # Overall occupancy
        overall = cal.groupby("listing_id").agg(
            total_days     = ("available", "count"),
            booked_days    = ("available", lambda x: (x == False).sum()),
            available_days = ("available", lambda x: (x == True).sum()),
        ).reset_index()

        overall["occupancy_rate"] = (
            overall["booked_days"] / overall["total_days"]
        ).round(4)

        # Weekend vs weekday bookings
        weekend_cal = cal[cal["is_weekend"] == True]
        weekday_cal = cal[cal["is_weekend"] == False]

        weekend_summary = weekend_cal.groupby("listing_id").agg(
            weekend_booked_days = ("available", lambda x: (x == False).sum()),
            weekend_total_days  = ("available", "count"),
        ).reset_index()

        weekday_summary = weekday_cal.groupby("listing_id").agg(
            weekday_booked_days = ("available", lambda x: (x == False).sum()),
            weekday_total_days  = ("available", "count"),
        ).reset_index()

        # Peak month (month with most booked days)
        booked_cal = cal[cal["available"] == False].copy()
        if len(booked_cal) > 0:
            peak = (
                booked_cal.groupby(["listing_id", "month"])
                          .size()
                          .reset_index(name="booked_count")
                          .sort_values("booked_count", ascending=False)
                          .drop_duplicates("listing_id")
                          .rename(columns={"month": "peak_month"})
                [["listing_id", "peak_month"]]
            )
        else:
            peak = pd.DataFrame(columns=["listing_id", "peak_month"])

        # Merge all calendar summaries
        summary = (
            overall
            .merge(weekend_summary, on="listing_id", how="left")
            .merge(weekday_summary, on="listing_id", how="left")
            .merge(peak,            on="listing_id", how="left")
        )

        # Weekend vs weekday occupancy rates
        summary["weekend_occupancy_rate"] = (
            summary["weekend_booked_days"] / summary["weekend_total_days"]
        ).round(4)
        summary["weekday_occupancy_rate"] = (
            summary["weekday_booked_days"] / summary["weekday_total_days"]
        ).round(4)

        print(f"     Calendar summary: {len(summary):,} listings with calendar data")
        return summary

    # =========================================================
    # Master join
    # =========================================================

    def build_master(self, clean_datasets: dict) -> pd.DataFrame:
        """
        Join all cleaned datasets into the enriched master listings table.

        Join sequence:
            1. Start with listings_clean (base — 10,480 rows)
            2. LEFT JOIN review_summary  (on listing_id = id)
            3. LEFT JOIN calendar_summary (on listing_id = id)
            4. LEFT JOIN neighbourhood_stats (on neighbourhood_cleansed)

        All joins are LEFT to preserve all listing rows.

        Args:
            clean_datasets: dict from DataCleaner.clean_all()

        Returns:
            master DataFrame — one row per listing, all enriched fields
        """
        print("\n" + "=" * 55)
        print("  SECTION 3.3 — DATA ENRICHMENT & JOINING")
        print("=" * 55)

        listings = clean_datasets["listings"].copy()
        calendar = clean_datasets["calendar"]
        reviews  = clean_datasets["reviews"]

        print(f"\n  Base listings: {len(listings):,} rows")

        # ── Step 1: Review summary join ───────────────────────────
        review_summary = self.build_review_summary(reviews)
        listings = listings.merge(
            review_summary,
            left_on="id",
            right_on="listing_id",
            how="left",
            suffixes=("", "_from_reviews")
        )
        # Drop duplicate listing_id column from merge
        if "listing_id_from_reviews" in listings.columns:
            listings = listings.drop(columns=["listing_id_from_reviews"])
        if "listing_id" in listings.columns and "id" in listings.columns:
            listings = listings.drop(columns=["listing_id"], errors="ignore")

        matched_reviews = listings["review_count"].notna().sum()
        print(f"     After review join: {matched_reviews:,} listings matched reviews")

        # ── Step 2: Calendar summary join ─────────────────────────
        calendar_summary = self.build_calendar_summary(calendar)
        listings = listings.merge(
            calendar_summary,
            left_on="id",
            right_on="listing_id",
            how="left",
            suffixes=("", "_from_calendar")
        )
        if "listing_id" in listings.columns:
            listings = listings.drop(columns=["listing_id"], errors="ignore")

        matched_cal = listings["occupancy_rate"].notna().sum()
        print(f"     After calendar join: {matched_cal:,} listings matched calendar")

        print(f"\n  Master table: {listings.shape[0]:,} rows × {listings.shape[1]} cols")
        print("  ✅ Master listings built")
        return listings
