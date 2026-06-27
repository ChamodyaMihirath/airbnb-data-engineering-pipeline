"""
pipeline.py  —  Sections 3.3 / 3.4 / 3.5
------------------------------------------
Full Amsterdam Airbnb pipeline with:
    - Enrichment & joining        (Section 3.3)
    - Star schema in DuckDB       (Section 3.4)
    - Logging, error handling     (Section 3.5)
    - Metadata management         (Section 3.5)
    - Configurable for any city   (Section 3.5)
    - Data lineage documentation  (Section 3.5)

Usage:
    python pipeline.py
    python pipeline.py --city amsterdam   (future multi-city)
"""

import sys
import time
import traceback
import logging
from pathlib import Path
from datetime import datetime

# ── Configure logging (Section 3.5) ───────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ]
)
log = logging.getLogger("airbnb_pipeline")


# ── Imports ───────────────────────────────────────────────────────────────────
from ingestion.loader     import DataLoader
from ingestion.validator  import DataValidator
from profiling.profiler   import DataProfiler
from cleaning.cleaner     import DataCleaner
from enrichment.enricher  import DataEnricher
from database.db          import DatabaseManager


# =============================================================
# Configuration  (Section 3.5 — configurable for any city)
# =============================================================

CONFIG = {
    "city":        "amsterdam",
    "data_path":   Path(r"D:\Expernetic\airbnb-data-engineering-pipeline\Data\raw\amsterdam"),
    "output_path": Path(r"D:\Expernetic\airbnb-data-engineering-pipeline\Data\processed"),
    "db_path":     r"D:\Expernetic\airbnb-data-engineering-pipeline\Data\database\airbnb_amsterdam.duckdb",
    "max_retries": 3,
    "retry_delay": 2,   # seconds between retries
}


# =============================================================
# Retry decorator  (Section 3.5 — retry logic)
# =============================================================

def with_retry(func, *args, max_retries=3, retry_delay=2, step_name="", **kwargs):
    """
    Execute a function with retry logic.
    Retries up to max_retries times on failure with delay between attempts.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries:
                log.warning(
                    f"[{step_name}] Attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {retry_delay}s ..."
                )
                time.sleep(retry_delay)
            else:
                log.error(f"[{step_name}] All {max_retries} attempts failed.")
                raise


# =============================================================
# Data lineage documentation  
# =============================================================

LINEAGE = {
    "listings_clean.parquet": {
        "source":         "listings.csv.gz (Inside Airbnb Amsterdam)",
        "transformations": [
            "Price: strip '$', cast to float, zero → NaN",
            "Dates: parse to datetime (host_since, first_review, last_review)",
            "Booleans: 't'/'f' → True/False",
            "Percentages: '97%' → 97.0",
            "room_type: normalized to 4 canonical values",
            "minimum_nights: capped at 365",
            "beds: imputed as ceil(accommodates/2) where null",
            "Added: host_tenure_years, price_per_bedroom, host_segment, city, _is_valid",
        ],
        "sink": "data/processed/listings_clean.parquet",
    },
    "calendar_clean.parquet": {
        "source":         "calendar.csv.gz (Inside Airbnb Amsterdam)",
        "transformations": [
            "date: parse to datetime",
            "price: strip '$', cast to float",
            "available: 't'/'f' → bool",
            "adjusted_price: dropped (100% null)",
            "maximum_nights: INT_MAX (2147483647) → NaN",
            "minimum_nights: capped at 365",
            "Added: month, month_name, day_of_week, is_weekend, quarter, year",
        ],
        "sink": "data/processed/calendar_clean.parquet",
    },
    "reviews_clean.parquet": {
        "source":         "reviews.csv.gz (Inside Airbnb Amsterdam)",
        "transformations": [
            "date: parse to datetime",
            "IDs: cast to numeric",
            "comments: strip whitespace",
            "Added: review_year, review_month, _has_text, _is_auto_review",
        ],
        "sink": "data/processed/reviews_clean.parquet",
    },
    "master_listings.parquet": {
        "source":         "listings_clean + calendar_clean + reviews_clean",
        "transformations": [
            "LEFT JOIN review summary (aggregated per listing_id)",
            "LEFT JOIN calendar summary (occupancy_rate, weekend_occupancy_rate)",
            "LEFT JOIN neighbourhood aggregates (median_price, avg_rating, etc.)",
            "Added: review_count, review_frequency, occupancy_rate",
            "Added: estimated_annual_revenue_computed, price_tier",
            "Added: price_vs_neighbourhood_median, is_high_performer",
            "Added: days_since_last_review, neighbourhood_price_rank",
        ],
        "sink": "data/processed/master_listings.parquet + DuckDB star schema",
    },
}


def print_lineage():
    log.info("\n── Data Lineage ─────────────────────────────────────")
    for table, info in LINEAGE.items():
        log.info(f"\n  {table}")
        log.info(f"    Source : {info['source']}")
        log.info(f"    Sink   : {info['sink']}")
        log.info(f"    Steps  : {len(info['transformations'])} transformations")


# =============================================================
# Pipeline
# =============================================================

def main():
    start_time = time.time()
    city       = CONFIG["city"].upper()

    log.info("=" * 60)
    log.info(f"  AIRBNB DATA ENGINEERING PIPELINE — {city}")
    log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    # Track metadata
    db       = DatabaseManager(CONFIG["db_path"])
    metadata = {}

    try:
        # ------------------------------------------------------
        # Step 1 — Load
        # ------------------------------------------------------
        log.info("\n[Step 1/6] Loading datasets ...")
        t0 = time.time()

        loader   = DataLoader(CONFIG["data_path"])
        datasets = with_retry(
            loader.load_all,
            max_retries=CONFIG["max_retries"],
            retry_delay=CONFIG["retry_delay"],
            step_name="Load"
        )

        for name, df in datasets.items():
            log.info(f"     {name:20s}: {df.shape[0]:>10,} rows × {df.shape[1]:>3} cols")
            metadata[name] = {"rows_raw": df.shape[0]}

        log.info(f"     Load time: {time.time()-t0:.1f}s")

        # ------------------------------------------------------
        # Step 2 — Validate
        # ------------------------------------------------------
        log.info("\n[Step 2/6] Validating ...")
        t0 = time.time()

        validator = DataValidator(CONFIG["data_path"])
        results   = validator.validate_all(datasets)

        if not all(results.values()):
            failed = [k for k, v in results.items() if not v]
            log.warning(f"  Validation failed for: {failed} — continuing with warnings")
        else:
            log.info("   4/4 datasets passed validation")

        log.info(f"     Validate time: {time.time()-t0:.1f}s")
        db.update_metadata("all", "validated", sum(df.shape[0] for df in datasets.values()))

        # ------------------------------------------------------
        # Step 3 — Profile
        # ------------------------------------------------------
        log.info("\n[Step 3/6] Profiling ...")
        t0 = time.time()

        profiler = DataProfiler()
        report   = with_retry(
            profiler.profile_all, datasets,
            max_retries=CONFIG["max_retries"],
            step_name="Profile"
        )
        profiler.save_report(report, CONFIG["output_path"])

        log.info(f"     Profile time: {time.time()-t0:.1f}s")
        db.update_metadata("all", "profiled", 0, "Quality report saved")

        # ------------------------------------------------------
        # Step 4 — Clean
        # ------------------------------------------------------
        log.info("\n[Step 4/6] Cleaning ...")
        t0 = time.time()

        cleaner        = DataCleaner()
        clean_datasets = with_retry(
            cleaner.clean_all, datasets,
            max_retries=CONFIG["max_retries"],
            step_name="Clean"
        )
        cleaner.save_cleaned(clean_datasets, CONFIG["output_path"])

        for name, df in clean_datasets.items():
            log.info(f"     {name:20s}: {df.shape[0]:>10,} rows × {df.shape[1]:>3} cols")
            db.update_metadata(name, "cleaned", df.shape[0])

        log.info(f"     Clean time: {time.time()-t0:.1f}s")

        # ------------------------------------------------------
        # Step 5 — Enrich  
        # ------------------------------------------------------
        log.info("\n[Step 5/6] Enriching ...")
        t0 = time.time()

        enricher = DataEnricher()
        master   = with_retry(
            enricher.build_master, clean_datasets,
            max_retries=CONFIG["max_retries"],
            step_name="Enrich"
        )
        enricher.save(master, CONFIG["output_path"])

        log.info(f"     master_listings: {master.shape[0]:,} rows × {master.shape[1]} cols")
        log.info(f"     Enrich time: {time.time()-t0:.1f}s")
        db.update_metadata("master_listings", "enriched", master.shape[0])

        # ------------------------------------------------------
        # Step 6 — Database  
        # ------------------------------------------------------
        log.info("\n[Step 6/6] Loading to DuckDB & building star schema ...")
        t0 = time.time()

        db.load_all(master, clean_datasets["calendar"])

        log.info(f"     DB time: {time.time()-t0:.1f}s")
        db.update_metadata("duckdb", "star_schema_built", master.shape[0])

        # ------------------------------------------------------
        # Lineage report
        # ------------------------------------------------------
        print_lineage()

        # ------------------------------------------------------
        # Done
        # ------------------------------------------------------
        total_time = time.time() - start_time
        log.info("\n" + "=" * 60)
        log.info(f"  ✅ Pipeline completed in {total_time:.1f}s")
        log.info(f"  Outputs: {CONFIG['output_path']}")
        log.info(f"  Database: {CONFIG['db_path']}")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"\n❌ Pipeline failed: {e}")
        log.error(traceback.format_exc())
        db.update_metadata("pipeline", "FAILED", 0, str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
