# Decision Log
## Amsterdam Airbnb Market Intelligence
## Expernetic Data Engineer Intern — Technical Assessment

**Author:** Chamodya  
**City:** Amsterdam, Netherlands  
**Last updated:** June 2026

---

> Every entry follows the required format:
> - **Options considered** — what alternatives were evaluated
> - **Why this approach** — the reasoning behind the choice
> - **Trade-offs accepted** — what was given up and why that is acceptable
>
> Decisions are grouped by category: Tools, Architecture, Schema, Cleaning, Analysis.

---

## Category 1 — Tool Selection

---

### DEC-001 — Analytical Database: DuckDB

**Decision:** Use DuckDB as the analytical database engine.

**Options considered:**

| Option | Description | Why rejected |
|--------|-------------|--------------|
| PostgreSQL | Full relational server, production-standard | Requires a running server, user accounts, connection strings — setup overhead with no benefit for single-analyst local work |
| SQLite | Embedded, zero setup | No window functions, slow aggregations on 3.8M calendar rows, not columnar |
| DuckDB | Embedded columnar analytical engine | Selected |
| BigQuery | Fully managed cloud warehouse | Requires GCP account and billing — overkill for a 5-day single-city assessment |
| Pandas only | Keep data in memory, no SQL | Cannot persist analytical results, no SQL interface for star schema demonstration |

**Why DuckDB:**
DuckDB is a columnar analytical database that runs embedded — no server, no setup, just a Python library and a single `.duckdb` file. For this dataset (10,480 listings, 3.8M calendar rows), it executes GROUP BY and window function queries 10–50x faster than SQLite because it reads only the columns needed (columnar storage) rather than entire rows. It also reads directly from parquet files, integrating cleanly with the cleaning pipeline output. The star schema SQL written for DuckDB is portable — it runs unchanged on BigQuery or Snowflake if the project scales.

**Trade-offs accepted:**
DuckDB is not designed for high-concurrency writes from multiple parallel processes. For a production multi-city pipeline running 50 cities simultaneously, a managed warehouse (BigQuery, Snowflake, Redshift) would replace DuckDB. For this single-city assessment, the simplicity advantage far outweighs this limitation.

---

### DEC-002 — File Format: Parquet over CSV

**Decision:** Save all cleaned and enriched datasets as `.parquet` files.

**Options considered:**

| Option | dtype preservation | File size | Read speed | Human readable |
|--------|--------------------|-----------|------------|----------------|
| CSV | No — everything becomes string | ~40 MB (listings) | Slow — re-parses all columns | Yes |
| JSON | Partial | ~60 MB | Slow | Yes |
| Parquet | Yes — exact dtypes preserved | 7.7 MB (listings) | Fast — column pruning | No |
| Feather | Yes | Similar to parquet | Very fast | No |

**Why Parquet:**
Three concrete benefits for this project.

First, dtype preservation. After cleaning, `host_since` is `datetime64`, `host_is_superhost` is `bool`, `price` is `float64`. If saved as CSV and reloaded, every column becomes a string and all cleaning work must be repeated. Parquet stores exact types — load once, use anywhere.

Second, file size. `listings_clean.parquet` = 7.7 MB. The equivalent CSV would be approximately 40 MB. `calendar_clean.parquet` = 1.7 MB vs approximately 180 MB as CSV. Columnar compression on repetitive calendar data (365 rows per listing with the same `listing_id`) is extremely effective.

Third, column pruning. When the EDA notebook only needs `price` and `neighbourhood_cleansed`, parquet reads only those two columns from disk. CSV reads all 85 columns then discards 83. For the 3.8M row calendar file, this difference is significant.

**Trade-offs accepted:**
Parquet files cannot be opened in Excel or a text editor for quick inspection. Mitigated by keeping the raw `.gz` files untouched as a human-readable reference. Profile CSV reports are also saved in CSV format for easy review.

---

### DEC-003 — Price Parsing: Explicit String Replace over Regex

**Decision:** Parse price column using chained `str.replace("$", "", regex=False)` calls instead of a regex character class `r"[\$€£,\s]"`.

**Options considered:**

| Option | Code | Risk |
|--------|------|------|
| Regex character class | `.str.replace(r"[\$€£,\s]", "", regex=True)` | Failed silently on Windows — regex engine handled `\$` inside character class differently |
| Explicit replace chain | `.str.replace("$", "", regex=False)` × 4 | Slightly more verbose but completely predictable |
| Locale-aware parsing | `locale.atof()` | Requires setting system locale — fragile, not portable |
| Custom regex | `r"\$([0-9,]+\.?[0-9]*)` | More complex, still has platform risk |

**Why explicit replace:**
The regex character class `[\$€£,\s]` failed on Windows (Python 3.10, pandas 2.x) — the `\$` character inside a character class was not being stripped, causing 4,606 prices to remain null after cleaning. Diagnosis: `repr(listings["price"].iloc[0])` showed `'$132.00'` — the string was present but `$` was not being removed.

`regex=False` uses Python's built-in `str.replace()` — no regex engine, no platform differences, completely deterministic behavior. Each currency symbol is handled in a separate, readable step. Simple is better than clever.

**Trade-offs accepted:**
Four `.str.replace()` calls instead of one regex. Minimal performance difference on 10,480 rows. Readability and correctness outweigh the marginal verbosity cost.

---

### DEC-004 — Load `.gz` Directly, No Manual Extraction

**Decision:** Read all `.gz` files directly via `compression="gzip"` in pandas. No manual unzipping.

**Options considered:**

| Option | Risk |
|--------|------|
| Manual extraction then load | Creates duplicate files — loader picks up wrong file |
| Load `.gz` directly | Single file, no ambiguity |
| Programmatic extraction with `gzip` module | Unnecessary intermediate step |

**Why direct `.gz` loading:**
Inside Airbnb provides two listings files: `listings.csv` (summary, 18 columns, no price) and `listings.csv.gz` (detailed, 79 columns, has price). When `listings.csv.gz` was manually extracted, both files existed in the same folder. The loader loaded `listings.csv` — the wrong file — causing the price column to appear 100% null for several pipeline runs.

Direct `.gz` reading via `pd.read_csv(path, compression="gzip")` means only one file exists for each dataset. The path is explicit. There is no ambiguity about which file is loaded.

**Trade-offs accepted:**
Slightly slower load time since decompression happens every run (6.3 seconds total for all files). Acceptable because raw files are loaded once per pipeline run, not repeatedly. The correctness guarantee outweighs the minor performance cost.

---

### DEC-005 — Logging: Python logging module over print statements

**Decision:** Use Python's `logging` module with dual output (console + file) instead of `print()` statements.

**Options considered:**

| Option | Persistent? | Level control? | Timestamps? |
|--------|-------------|----------------|-------------|
| print() | No | No | No |
| logging module | Yes (file handler) | Yes (DEBUG/INFO/WARNING/ERROR) | Yes |
| loguru | Yes | Yes | Yes |
| structlog | Yes | Yes | JSON format |

**Why logging module:**
Three requirements drove this choice.

First, persistence. Pipeline logs are saved to `logs/pipeline_YYYYMMDD_HHMMSS.log`. If the pipeline fails at Step 4, the log file shows exactly which step failed and why — without re-running.

Second, level control. `logging.WARNING` messages (outlier counts, null fields) are visually distinct from `logging.INFO` progress messages. In production, you would set level to WARNING to suppress verbose progress output.

Third, zero dependencies. The `logging` module is in Python's standard library — no installation required, works in any environment.

**Trade-offs accepted:**
Windows terminal (cp1252 encoding) cannot display Unicode emoji characters (✅, ⚠️) used in some log messages — causing a `UnicodeEncodeError`. Fixed by removing emoji from log messages and using plain ASCII equivalents. `sys.stdout.reconfigure(encoding='utf-8')` is an alternative fix.

---

## Category 2 — Architectural Decisions

---

### DEC-006 — Modular Cleaning Architecture: 3 Sub-modules

**Decision:** Split cleaning into `standardizer.py`, `missing_values.py`, and `geo_cleaner.py` rather than one monolithic `cleaner.py`.

**Options considered:**

| Option | Pros | Cons |
|--------|------|------|
| Single cleaner.py (all logic together) | Fewer files | Hard to test, update, or explain. One 500-line file doing everything |
| Two files (cleaner + helpers) | Slight improvement | Still mixes concerns |
| Three files by concern | Clear single responsibility per file | More files to navigate |

**Why three files:**
Each file has exactly one responsibility.

`standardizer.py` — format standardization only. Strips `$`, parses dates, maps `t`/`f` to bool. If Inside Airbnb changes their price format next year, only this file changes.

`missing_values.py` — null strategy decisions only. Caps `minimum_nights` at 365, replaces INT_MAX, imputes beds from accommodates. These are analytical decisions — keeping them separate makes the reasoning auditable.

`geo_cleaner.py` — geographic normalization only. Rounds coordinates, validates Amsterdam bounding box, standardizes neighbourhood names to Title Case. Adding a second city with different bounds requires only updating this file.

`cleaner.py` orchestrates all three in the correct order: standardizer → missing_values → geo_cleaner → _is_valid flag. Order matters because missing value strategies depend on correct dtypes (set by standardizer) and geo cleaning depends on string types (also set by standardizer).

**Trade-offs accepted:**
Four files instead of one. A reviewer must open multiple files to understand the full cleaning logic. Mitigated by clear naming, docstrings, and the orchestrator comments explaining why the order matters.

---

### DEC-007 — City Selection: Amsterdam Only

**Decision:** Analyze Amsterdam as a single city rather than multiple cities.

**Options considered:**

| Option | Depth possible | Complexity | Cross-city insights |
|--------|---------------|-----------|---------------------|
| 1 city (Amsterdam) | Very high | Low | None |
| 2–3 cities | Medium | Medium | Basic comparisons |
| 4+ cities | Low (time constraint) | High | Broad patterns |

**Why Amsterdam only:**
The assignment explicitly states: "A candidate who completes two sections with exceptional depth, clean code, and insightful storytelling will outperform one who attempts all sections superficially."

Amsterdam has one of Inside Airbnb's richest datasets: 10,480 listings, 501,084 reviews, 3.8M calendar rows, 22 neighbourhoods with GeoJSON boundaries. There is enough data for statistically meaningful hypothesis tests, a credible ML model, and detailed choropleth mapping. A second city analyzed in the same depth would require an additional 5-day timeline.

**Scalability design:** The pipeline is architected to be city-agnostic. `DATA_PATH` is a CONFIG variable. The `city = "Amsterdam"` column added during geo cleaning means a multi-city master table can be built by UNION of individual city outputs. Adding Paris requires changing two CONFIG values — no code changes.

**Trade-offs accepted:**
No cross-city comparisons. Assignment bonus credit for multi-city analysis not pursued. This trade-off is deliberately made and documented — honest prioritization is itself evaluated (15% weight in rubric).

---

### DEC-008 — Flag Invalid Records, Never Drop

**Decision:** Listings that fail validation (missing price, missing coordinates) are flagged via `_is_valid = False` rather than dropped from the dataset.

**Options considered:**

| Option | Pros | Cons |
|--------|------|------|
| Drop invalid rows | Cleaner dataset, no null handling needed | Permanently loses data — 4,606 listings with valid location/host/review data gone |
| Flag with _is_valid column | All data preserved, analysts choose filter | Every query must remember to filter WHERE _is_valid = TRUE for price analysis |
| Separate invalid table | Full separation | Complexity — two tables to maintain |

**Why flag:**
4,606 listings (43.95%) have no price in the source data — confirmed as genuine empty strings, not parsing errors. These listings still have valid neighbourhood, host, review, and coordinate data. Dropping them would:
- Reduce geographic coverage — some neighbourhoods have fewer valid-price listings
- Undercount total host activity — commercial operators may list properties without published prices
- Lose all review data for those listings

Flagging preserves all information. Price analysis uses `WHERE _is_valid = TRUE` (5,874 listings). Host count, neighbourhood density, and review analysis use all 10,480 listings. Each analysis chooses its own filter based on what it needs.

This follows standard data warehouse practice: raw and cleaned data is annotated, not deleted.

**Trade-offs accepted:**
All downstream queries must be aware of `_is_valid`. Mitigated by documenting this in the README, notebook preambles, and this decision log. The DuckDB view `fact_listings` can be pre-filtered to only valid listings for convenience.

---

### DEC-009 — Pre-aggregate Before Joining

**Decision:** Aggregate reviews (501,084 rows) and calendar (3.8M rows) to one row per listing_id before joining to listings (10,480 rows).

**Options considered:**

| Option | Result rows | Correctness |
|--------|-------------|-------------|
| Direct join reviews → listings | 501,084 rows — row explosion | Wrong — multiple rows per listing |
| Pre-aggregate reviews, then join | 10,480 rows | Correct — one row per listing |
| SQL window functions in DuckDB | 10,480 rows | Correct — alternative approach |

**Why pre-aggregate:**
Joining 501,084 review rows directly to 10,480 listing rows creates a many-to-one explosion — every review becomes a separate row for the listing. The result would have 501,084 rows, not 10,480. That is not the intended grain (one row per listing).

Pre-aggregating: `reviews.groupby("listing_id").agg(review_count=("id","count"), latest_review_date=("date","max"), ...)` collapses 501,084 rows to 9,383 rows (one per listing with reviews). The join to listings is then a clean 1-to-1 (or 1-to-null for listings with no reviews).

Same logic for calendar: 3.8M rows collapsed to 10,480 rows by computing occupancy_rate per listing before joining.

**Trade-offs accepted:**
Two-step process (aggregate then join) instead of a single join. The intermediate aggregation DataFrames use memory briefly. At this dataset size (well under 1 GB), memory is not a concern.

---

## Category 3 — Schema Design

---

### DEC-010 — Star Schema: Fact + 4 Dimensions

**Decision:** Implement a dimensional star schema with `fact_listings`, `fact_calendar`, `dim_host`, `dim_neighbourhood`, `dim_room_type`, and `dim_date`.

**Options considered:**

| Option | Query complexity | Storage | Flexibility |
|--------|-----------------|---------|-------------|
| Single flat table (all columns) | Simple queries | Redundant (host_name repeated per listing) | Poor for analytical slicing |
| 3NF normalized (full normalization) | Complex queries — many JOINs | Minimal redundancy | High for OLTP, poor for analytics |
| Star schema (fact + dimensions) | Simple analytical queries | Moderate redundancy | High for analytics |
| Snowflake schema | Medium query complexity | Less redundancy than star | More complex than needed |

**Why star schema:**
This is an analytical workload, not a transactional one. The primary queries are: "average price by neighbourhood", "superhost vs non-superhost rating comparison", "seasonal occupancy by month". These are GROUP BY aggregations across dimensions — exactly what star schema optimizes for.

In a star schema, these queries require one JOIN between fact_listings and one dimension table. In 3NF, the same query might require 3–4 JOINs. In DuckDB's columnar engine, fewer JOINs on small dimension tables = much faster execution.

**Grain definitions:**
- `fact_listings` — one row per listing (10,480 rows)
- `fact_calendar` — one row per listing × date (3,825,200 rows)
- `dim_host` — one row per unique host (9,201 hosts)
- `dim_neighbourhood` — one row per neighbourhood (22 neighbourhoods)
- `dim_room_type` — one row per room type (4 canonical types)
- `dim_date` — one row per calendar date (365 dates)

**Trade-offs accepted:**

*Denormalization:* Some host attributes appear in both `dim_host` and `fact_listings`. This redundancy is intentional — it allows listing-level queries without joining to `dim_host`. Acceptable at this scale (10,480 rows, not billions).

*No Slowly Changing Dimensions (SCD Type 2):* Host attributes (superhost status, response rate) are treated as current snapshot — no history tracking. Inside Airbnb is a point-in-time scrape anyway, so historical host attributes are not available. SCD Type 2 would add complexity with no benefit for this dataset.

*No partitioning on fact_listings:* At 10,480 rows, partitioning adds no query performance benefit. For `fact_calendar` (3.8M rows), queries are typically filtered by month — a `WHERE month = 6` filter is fast enough without explicit partitioning at this scale.

---

### DEC-011 — neighbourhood_cleansed as Canonical Geo Field

**Decision:** Use `neighbourhood_cleansed` (Inside Airbnb standardized) as the canonical neighbourhood field. Never use raw `neighbourhood`.

**Options considered:**

| Field | Null rate | Source | Consistency |
|-------|-----------|--------|-------------|
| `neighbourhood` | >50% null | Host-entered free text | Inconsistent — "Centrum", "centrum", "De Centrum", "Center" all appear |
| `neighbourhood_cleansed` | 0% null | Standardized by Inside Airbnb from official Amsterdam district map | Consistent — exactly 22 values |
| `neighbourhood_group_cleansed` | >50% null | Inside Airbnb | Not used in Amsterdam (borough groupings not applicable) |

**Why neighbourhood_cleansed:**
The raw `neighbourhood` field is user-entered. Hosts type it themselves when creating their listing. Result: "Centrum", "centrum", "De Centrum", "Amsterdam Centrum", and "Center" all refer to the same neighbourhood but are treated as 5 different groups by `groupby()`. This makes any neighbourhood analysis completely unreliable.

`neighbourhood_cleansed` is assigned by Inside Airbnb using official Amsterdam district boundary polygons (GeoJSON). Every listing gets exactly one of 22 standard values. It is always populated (0% null). It matches the `neighbourhoods.geojson` file used for choropleth mapping.

**Trade-offs accepted:**
We lose host-reported neighbourhood context (some hosts describe their area differently from official boundaries). This is the correct trade-off — analytical consistency outweighs subjective host perception. The raw `neighbourhood` column is retained in the dataset for reference but never used in groupby operations.

---

## Category 4 — Cleaning Decisions

---

### DEC-012 — Missing Price: Explicit NaN, Not Imputation

**Decision:** Listings with no price are set to NaN and flagged via `_is_valid = False`. No price imputation is attempted.

**Options considered:**

| Strategy | Risk |
|----------|------|
| Impute with neighbourhood median | Introduces bias — all imputed listings cluster at the median, distorting price distribution |
| Impute with room type median | Same bias problem, just at room type level |
| Impute with regression model | Circular — building a price model to impute prices we then use to train a price model |
| Explicit NaN + flag | Honest representation of data quality |

**Why explicit NaN:**
Price is the primary target variable in this analysis. Imputing it would mean we are making up the very thing we are trying to understand and predict. A listing with no published price genuinely has no price — it is likely inactive, in draft state, or the host chose not to publish pricing. Imputing a price for it would misrepresent the market.

5,874 listings with valid prices is a sufficient sample for all analyses. Amsterdam's total active Airbnb market is approximately 15,000 listings — 5,874 represents ~39% of the market.

**Trade-offs accepted:**
44% of listings are excluded from price analysis. This reduces statistical power for some neighbourhood-level comparisons (some areas have fewer valid-price listings). Mitigated by reporting confidence intervals and sample sizes alongside all price statistics.

---

### DEC-013 — Beds Imputation: ceil(accommodates/2)

**Decision:** Null `beds` values are imputed as `ceil(accommodates / 2)`.

**Options considered:**

| Strategy | Risk |
|----------|------|
| Drop rows with null beds | Loses 44% of listings for bed-based analysis |
| Impute with dataset mean | All imputed listings get the same value regardless of size — a studio and a 10-person villa both get ~3 beds |
| Impute with room type median | Better than overall mean but still ignores listing-specific size |
| Impute as ceil(accommodates/2) | Uses listing-specific context |

**Why ceil(accommodates/2):**
`accommodates` is the number of guests a listing can hold. A 2-person studio typically has 1 bed. A 4-person apartment typically has 2 beds. The relationship `beds ≈ accommodates / 2` holds empirically in the non-null data (correlation > 0.7).

`ceil()` is used rather than `floor()` or round because it is conservative — better to slightly overestimate beds than underestimate (understating beds would make price_per_bedroom look artificially high).

**Trade-offs accepted:**
Imputed beds values are estimates. Studios with sofa beds or bunk beds may be overcounted. All price_per_bedroom calculations using imputed beds are labelled as approximate in the report. The imputation is documented in assumptions_log entry A-02.

---

### DEC-014 — minimum_nights Cap at 365

**Decision:** `minimum_nights` values above 365 are capped at 365, not dropped.

**Context from profiling:** maximum value = 1,001 nights in both listings (2 records) and calendar (731 records).

**Options considered:**

| Strategy | Outcome |
|----------|---------|
| Drop rows where minimum_nights > 365 | Loses the listing entirely — even though price, location, reviews are valid |
| Cap at 365 | Fixes the erroneous value, preserves all other listing attributes |
| Keep as-is | Distorts any analysis involving minimum_nights |
| Cap at 30 (max typical short-term rental) | Too aggressive — some listings genuinely require longer stays |

**Why cap at 365:**
A minimum stay of 1,001 nights (2.7 years) is not a short-term rental listing. This is almost certainly a data entry error — host typed "1001" meaning "1" or "100". The listing itself is valid: it has a price, location, host, and reviews.

Capping at 365 (one year) is the maximum reasonable short-term rental minimum. It corrects the error while preserving all other listing attributes for analysis.

**Trade-offs accepted:**
2 listings in `listings.csv.gz` and 731 calendar records are modified. The modification is logged. In a production pipeline, these records would be quarantined for manual review rather than automatically corrected.

---

### DEC-015 — calendar.price: Use listings.price for Seasonal Analysis

**Decision:** Since `calendar.price` is entirely null in Amsterdam, all price-based temporal analysis uses `listings.price` as the base price.

**Context:** Confirmed that `calendar.csv.gz` for Amsterdam has genuinely empty price cells — not a parsing issue. This is a known Inside Airbnb data publication gap for some cities.

**Options considered:**

| Option | Feasibility |
|--------|-------------|
| Scrape live Airbnb prices | Out of scope, would introduce non-Inside Airbnb data |
| Use calendar.price | Impossible — 100% null |
| Use listings.price for all analyses | Feasible — represents the host's base listed price |
| Exclude all temporal price analysis | Loses an entire analytical dimension |

**Why listings.price:**
`listings.price` represents the host's base published nightly price. While it does not capture dynamic pricing adjustments (surge pricing for peak dates), it is the best available price signal in this dataset. Seasonal analysis focuses on availability patterns from `calendar.available` (which is populated) combined with the static listing price.

**Trade-offs accepted:**
Weekend vs. weekday price differences cannot be measured (only availability differences can be measured). Seasonal price surge analysis is not possible. Both limitations are clearly stated in the report wherever temporal price analysis appears.

---

## Category 5 — Pipeline Design

---

### DEC-016 — Retry Logic with Exponential Backoff Concept

**Decision:** Implement retry logic wrapping each pipeline step (3 attempts, 2-second delay between attempts).

**Options considered:**

| Option | Resilience |
|--------|-----------|
| No retry — fail immediately | One transient network error aborts entire 77-second pipeline |
| Retry with fixed delay (2 seconds) | Handles most transient failures |
| Retry with exponential backoff (2s, 4s, 8s) | Better for rate-limited APIs |
| Circuit breaker pattern | Production-grade but complex for this scope |

**Why retry with fixed delay:**
The most common failure modes in this pipeline are transient: brief file lock while another process reads the same parquet file, momentary memory spike causing a pandas operation to fail, network hiccup if data were being downloaded live. Fixed 2-second delay handles these without over-engineering.

Exponential backoff is more appropriate for API calls with rate limits — not relevant here since all data is local files.

**Trade-offs accepted:**
3 attempts × 2-second delay means a genuinely broken step (wrong file path, missing column) waits 4 extra seconds before failing. Acceptable for a pipeline that provides clear error messages on failure.

---

### DEC-017 — Metadata Management in DuckDB

**Decision:** Track pipeline execution metadata in a `pipeline_metadata` table within the same DuckDB database.

**Options considered:**

| Option | Persistence | Queryable | Setup |
|--------|-------------|-----------|-------|
| Print to console only | No | No | None |
| Write to text log file | Yes | Difficult | None |
| Write to separate SQLite | Yes | Yes | Extra file |
| Write to pipeline_metadata in DuckDB | Yes | Yes | Same connection |

**Why DuckDB metadata table:**
Storing metadata in the same database means one connection handles both analytical queries and pipeline monitoring. A single SQL query shows the full pipeline history: `SELECT * FROM pipeline_metadata ORDER BY run_timestamp DESC`. No additional infrastructure.

**Trade-offs accepted:**
If the DuckDB database is corrupted (unlikely), metadata is lost along with the analytical tables. In production, metadata would be written to a separate monitoring system (Airflow, Prefect, Datadog) independent of the data store.

---

*This log covers all significant decisions made through June 2026. New entries will be added for EDA methodology choices, statistical test selection rationale, and ML model selection decisions.*
