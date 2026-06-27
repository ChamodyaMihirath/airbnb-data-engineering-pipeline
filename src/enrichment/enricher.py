"""
enricher.py  —  Section 3.3: Enrichment Orchestrator
-----------------------------------------------------
Coordinates joins.py, feature_engineering.py, neighbourhood_stats.py
to produce the final master_listings table.

Usage:
    from enrichment.enricher import DataEnricher
    enricher = DataEnricher()
    master   = enricher.build_master(clean_datasets)
    enricher.save(master, output_path)
"""

import sys
from pathlib import Path

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from enrichment.joins import DataJoiner
    from enrichment.feature_engineering import FeatureEngineer
    from enrichment.neighbourhood_stats import NeighbourhoodStats
else:
    from .joins import DataJoiner
    from .feature_engineering import FeatureEngineer
    from .neighbourhood_stats import NeighbourhoodStats


class DataEnricher:

    def __init__(self):
        self.joiner    = DataJoiner()
        self.features  = FeatureEngineer()
        self.nbh_stats = NeighbourhoodStats()

    def build_master(self, clean_datasets: dict) -> pd.DataFrame:
        """
        Build the enriched master listings table.

        Order:
            1. Join all datasets          (joins.py)
            2. Engineer derived features  (feature_engineering.py)
            3. Add neighbourhood stats    (neighbourhood_stats.py)

        Why this order:
            Neighbourhood stats depend on occupancy_rate and price fields
            that are computed in feature_engineering. So feature engineering
            must run before neighbourhood aggregation.
        """
        print("\n" + "=" * 55)
        print("  SECTION 3.3 — ENRICHMENT PIPELINE")
        print("=" * 55)

        # Step 1: Join
        master = self.joiner.build_master(clean_datasets)

        # Step 2: Feature engineering
        master = self.features.engineer_all(master)

        # Step 3: Neighbourhood aggregates
        master = self.nbh_stats.enrich(master)

        print(f"\n  Master table final: {master.shape[0]:,} rows × {master.shape[1]} cols")
        return master

    def save(self, master: pd.DataFrame, output_dir) -> None:
        """Save master listings to parquet."""
        out  = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "master_listings.parquet"
        master.to_parquet(path, index=False)
        size_mb = path.stat().st_size / 1_048_576
        print(f"  ✅ Saved master_listings.parquet ({master.shape[0]:,} rows | {size_mb:.1f} MB)")
