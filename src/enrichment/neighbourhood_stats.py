"""
neighbourhood_stats.py  —  Section 3.3: Neighbourhood-Level Aggregates
----------------------------------------------------------------------
Computes area-level statistics and joins them back to the master table.

Why neighbourhood aggregates matter:
    Individual listing analysis misses market context.
    A listing priced at €150 looks expensive in a €100 median neighbourhood
    but cheap in a €250 median neighbourhood.
    Neighbourhood-level features are among the strongest predictors
    in Airbnb price models (SHAP analysis typically shows neighbourhood
    as top-3 feature).

Aggregates computed:
    neighbourhood_median_price      : median nightly price
    neighbourhood_mean_price        : mean nightly price
    neighbourhood_listing_count     : total listings
    neighbourhood_avg_rating        : average review score
    neighbourhood_avg_occupancy     : average occupancy rate
    neighbourhood_price_rank        : rank by median price (1 = most expensive)
    neighbourhood_listing_density   : listings per neighbourhood (proxy for density)
    price_vs_neighbourhood_median   : how this listing's price compares to its area

Usage:
    from enrichment.neighbourhood_stats import NeighbourhoodStats
    ns     = NeighbourhoodStats()
    master = ns.enrich(master)
"""

import pandas as pd
import numpy as np


class NeighbourhoodStats:

    def compute_neighbourhood_aggregates(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute neighbourhood-level summary statistics.

        Uses only valid-price listings for price aggregates
        (WHERE _is_valid = True) to avoid null prices skewing medians.
        Uses all listings for count and rating aggregates.

        Returns:
            DataFrame with one row per neighbourhood, all aggregate fields.
        """
        print("  [neighbourhood_stats] Computing neighbourhood aggregates ...")

        nbh_col = "neighbourhood_cleansed"
        if nbh_col not in df.columns:
            print("  WARNING: neighbourhood_cleansed not found — skipping")
            return pd.DataFrame()

        # ── Price aggregates (valid listings only) ────────────────
        valid_df = df[df["_is_valid"] == True] if "_is_valid" in df.columns else df

        price_agg = valid_df.groupby(nbh_col).agg(
            neighbourhood_median_price = ("price", "median"),
            neighbourhood_mean_price   = ("price", "mean"),
            neighbourhood_min_price    = ("price", "min"),
            neighbourhood_max_price    = ("price", "max"),
            neighbourhood_price_std    = ("price", "std"),
        ).round(2).reset_index()

        # ── Listing count (all listings) ──────────────────────────
        count_agg = df.groupby(nbh_col).agg(
            neighbourhood_listing_count = ("id", "count"),
        ).reset_index()

        # ── Rating aggregates (listings with ratings) ─────────────
        rated_df = df[df["review_scores_rating"].notna()]
        rating_agg = rated_df.groupby(nbh_col).agg(
            neighbourhood_avg_rating        = ("review_scores_rating", "mean"),
            neighbourhood_avg_cleanliness   = ("review_scores_cleanliness", "mean"),
            neighbourhood_avg_location      = ("review_scores_location", "mean"),
        ).round(3).reset_index()

        # ── Occupancy aggregates ──────────────────────────────────
        if "occupancy_rate" in df.columns:
            occ_agg = df.groupby(nbh_col).agg(
                neighbourhood_avg_occupancy = ("occupancy_rate", "mean"),
            ).round(4).reset_index()
        else:
            occ_agg = pd.DataFrame(columns=[nbh_col, "neighbourhood_avg_occupancy"])

        # ── Superhost concentration ───────────────────────────────
        if "host_is_superhost" in df.columns:
            superhost_agg = df.groupby(nbh_col).agg(
                neighbourhood_superhost_pct = (
                    "host_is_superhost",
                    lambda x: (x == True).sum() / len(x) * 100
                ),
            ).round(1).reset_index()
        else:
            superhost_agg = pd.DataFrame(
                columns=[nbh_col, "neighbourhood_superhost_pct"]
            )

        # ── Merge all neighbourhood aggregates ────────────────────
        stats = (
            price_agg
            .merge(count_agg,     on=nbh_col, how="left")
            .merge(rating_agg,    on=nbh_col, how="left")
            .merge(occ_agg,       on=nbh_col, how="left")
            .merge(superhost_agg, on=nbh_col, how="left")
        )

        # ── Price rank (1 = most expensive neighbourhood) ─────────
        stats["neighbourhood_price_rank"] = (
            stats["neighbourhood_median_price"]
            .rank(ascending=False, method="min")
            .astype("Int64")
        )

        print(f"     Neighbourhood aggregates computed: {len(stats)} neighbourhoods")
        print(f"     Price range: "
              f"€{stats['neighbourhood_median_price'].min():.0f} – "
              f"€{stats['neighbourhood_median_price'].max():.0f} median")
        print(f"     Most expensive: "
              f"{stats.loc[stats['neighbourhood_price_rank']==1, nbh_col].values[0]}")
        print(f"     Most listings: "
              f"{stats.loc[stats['neighbourhood_listing_count'].idxmax(), nbh_col]}"
              f" ({stats['neighbourhood_listing_count'].max():,})")

        return stats

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute neighbourhood aggregates and join back to master listings.

        Also adds:
            price_vs_neighbourhood_median : % above/below neighbourhood median
                Positive = listing priced above its neighbourhood average
                Negative = listing priced below its neighbourhood average
                Used to identify over/under-priced listings.

        Args:
            df: master listings DataFrame

        Returns:
            DataFrame with neighbourhood aggregate columns added
        """
        nbh_col = "neighbourhood_cleansed"

        # Compute aggregates
        stats = self.compute_neighbourhood_aggregates(df)
        if stats.empty:
            return df

        # Join back to master (LEFT JOIN — all listings preserved)
        df = df.merge(stats, on=nbh_col, how="left")

        # Price vs neighbourhood median
        # How much more/less expensive is this listing vs its area?
        if "price" in df.columns and "neighbourhood_median_price" in df.columns:
            df["price_vs_neighbourhood_median"] = np.where(
                df["price"].notna() & df["neighbourhood_median_price"].notna(),
                (
                    (df["price"] - df["neighbourhood_median_price"]) /
                    df["neighbourhood_median_price"] * 100
                ).round(2),
                np.nan
            )
            print(f"     price_vs_neighbourhood_median: "
                  f"median deviation = "
                  f"{df['price_vs_neighbourhood_median'].median():.1f}%")

        print(f"  ✅ Neighbourhood enrichment complete: "
              f"{df.shape[0]:,} rows × {df.shape[1]} cols")
        return df
