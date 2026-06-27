# Decision Log
## Amsterdam Airbnb Market Intelligence
## Expernetic Data Engineer Intern — Technical Assessment

**City:** Amsterdam, Netherlands  
**Last updated:** June 2026

---

> This log documents every significant technical, architectural, and analytical
> decision made during the project. Each entry follows the format:
> - **What options were considered**
> - **Why this approach was chosen**
> - **What trade-offs were accepted**
>
> This is the primary artifact for technical reviewers evaluating engineering judgment.

---

## Section 1 — Architecture & Tool Selection

### DEC-001 — Database: DuckDB over PostgreSQL or SQLite

**Decision:** Use DuckDB as the analytical database engine.

**Options considered:**

| Option | Pros | Cons |
|--------|------|------|
| PostgreSQL | Production-standard, concurrent access | Requires running server, setup overhead |
| SQLite | Zero setup, embedded | Limited analytical SQL (no window functions, slow aggregations) |
| DuckDB | Columnar, fast analytics, embedded, full SQL | Not suited for high-concurrency writes |
| BigQuery | Fully managed, scales infinitely | Requires GCP account, overkill for single city |

**Why DuckDB:**
DuckDB is a columnar analytical database that runs embedded (no server).
For this dataset (10,480 listings, 3.8M calendar rows), it executes GROUP BY,
window functions, and aggregations 10–50x faster than SQLite.
It reads directly from parquet files, integrating cleanly with the cleaning pipeline.
The star schema SQL runs unchanged if migrated to BigQuery or Snowflake later.

**Trade-offs accepted:**
Not suitable for concurrent writes from multiple processes.
For a production multi-city pipeline with parallel ingestion, a managed warehouse
(BigQuery, Snowflake) would replace DuckDB.

---

### DEC-002 — File format: Parquet over CSV for processed data

**Decision:** Save all cleaned datasets as `.parquet`, not `.csv`.

**Options considered:** CSV, JSON, Parquet, Feather

**Why Parquet:**
- **dtype preservation:** CSV loses all type information on save — datetime becomes
  string, bool becomes "True"/"False". Parquet preserves exact dtypes, so no
  re-parsing is needed when loading into notebooks or DuckDB.
- **File size:** listings_clean.parquet = 7.7 MB vs estimated ~40 MB as CSV.
  calendar_clean = 1.7 MB vs ~180 MB as CSV (columnar compression is highly
  effective on repetitive calendar data).
- **Read speed:** Parquet column pruning means only needed columns are read,
  not the full file. Critical for the 3.8M row calendar dataset.

**Trade-offs accepted:**
Parquet is not human-readable. For debugging, CSV is easier to inspect.
Mitigated by keeping raw `.gz` files untouched for reference.

---

### DEC-003 — Price parsing: explicit replace over regex character class

**Decision:** Use chained `str.replace("$", "", regex=False)` calls instead
of `str.replace(r"[\$€£,\s]", "", regex=True)`.

**Context:**
The regex character class `[\$€£,\s]` failed silently on Windows — the `$`
character inside a character class behaved differently than expected under
certain pandas/Python version combinations, resulting in 4,606 prices remaining
null after the regex ran.

**Why explicit replace:**
- `regex=False` uses Python's built-in string replacement — no regex engine,
  no platform differences, completely predictable behavior.
- Each character is handled in a separate, readable step.
- Easier to extend (add new currency symbols without debugging regex syntax).

**Trade-offs accepted:**
Slightly more verbose than a single regex. Acceptable for a utility function
that runs once per pipeline execution.

---

### DEC-004 — City selection: Amsterdam only

**Decision:** Analyze Amsterdam as a single city.

**Options considered:** Single city / 2–3 cities / 4+ cities

**Why Amsterdam only:**
- Assignment explicitly states quality outweighs quantity.
- Amsterdam has one of the richest Inside Airbnb datasets (10,480 listings,
  501,084 reviews, 3.8M calendar rows).
- A single city analyzed with exceptional depth (EDA, statistical tests, ML model,
  SHAP explainability, choropleth maps) outperforms 3 cities skimmed superficially.
- 5-day timeline makes multi-city analysis impractical without sacrificing report quality.

**Scalability design:** Pipeline is architected to be city-agnostic.
`DATA_PATH` is a single configuration variable. Adding a second city requires
only a new path and a second pipeline run. The `city = "Amsterdam"` column
added during cleaning means a multi-city master table can be built by UNION
of individual city tables.

**Trade-offs accepted:**
No cross-city comparisons. Assignment bonus credit for multi-city not achieved.

---

### DEC-005 — Load .gz files directly, no manual extraction

**Decision:** Read `.csv.gz` files directly via `compression="gzip"` in pandas.
No manual extraction or decompression step.

**Why:**
Manual extraction (unzipping `.csv.gz` → `.csv`) creates two files in the raw
directory. The loader then picks up the original summary `listings.csv` (18 cols,
no price column) instead of the extracted detailed file (79 cols, has price).
This caused the price column to appear 100% null for several pipeline runs.

Direct `.gz` reading eliminates ambiguity entirely — only one file exists,
and its path is explicit in the loader.

**Trade-offs accepted:**
Slightly slower load time (decompression on every run). Acceptable because
the raw files are only loaded once per pipeline run, not repeatedly.

---

## Section 2 — Data Cleaning Decisions

### DEC-006b — 4,606 listings with no price: flag vs drop

**Decision:** Flag via _is_valid=False, retain in dataset.

**Finding:** 4,606 listings have genuinely empty price fields in the
source data (confirmed via empty string check with keep_default_na=False).
This is a real data quality limitation of the Inside Airbnb scrape.

**Why retain:**
- 5,874 valid-price listings are sufficient for all pricing analyses
- Flagged listings still have valid neighbourhood, host, and review data
- Dropping permanently loses 43.95% of geographic and host coverage
- _is_valid flag lets each analysis choose its own filter

**Impact on analyses:**
- Price distribution, neighbourhood pricing, ML model → filter _is_valid=True
- Host count, neighbourhood density, review analysis → use all 10,480 rows

### DEC-007 — calendar.price empty: use listing price for seasonal analysis

**Decision:** Since `calendar.price` is entirely null in the Amsterdam dataset,
all price-based analysis (including seasonal trends) uses `listings.price`
as the base price.

**Context:**
`calendar.csv.gz` for Amsterdam contains daily availability data but the price
column is entirely empty. This is a known Inside Airbnb data publication issue
for some cities — not all markets publish daily calendar pricing.

**Implication for analysis:**
- Seasonal price trends cannot be computed from actual daily prices.
- Instead, listings are grouped by `neighbourhood_cleansed` and availability
  patterns are analyzed from `calendar.available` to infer seasonal demand.
- Pricing analysis uses the static `listings.price` as the representative price.

**Alternative considered:**
Scraping live Airbnb prices was considered but rejected — out of scope for this
assignment and would introduce data not from Inside Airbnb.

---

### DEC-008 — beds imputed from accommodates, not dropped

**Decision:** Null `beds` values are imputed as `ceil(accommodates / 2)`.

**Why impute instead of drop or leave null:**
Approximately 44% of listings have null `beds`. Dropping would lose nearly
half the dataset for any beds-based analysis.
`accommodates` is available for all listings and has a strong empirical
relationship to beds (correlation > 0.7 in non-null data).
`ceil(accommodates / 2)` is a conservative estimate — it slightly underestimates
beds for large properties (e.g. 8 accommodates → 4 beds, may actually be 5).

**Why not mean imputation:**
Mean imputation would assign the same beds value to all null listings regardless
of size. A studio and a 10-person villa would get the same imputed beds,
introducing systematic bias into price-per-bedroom calculations.

**Trade-offs accepted:**
Imputed values are estimates. Flagged in assumptions_log A-02.
`price_per_bedroom` using imputed beds is labelled as approximate.

---

### DEC-009 — minimum_nights capped at 365, not dropped

**Decision:** `minimum_nights > 365` records are capped at 365.

**Context:** Profiling found minimum_nights max = 1,001. A minimum stay of
1,001 nights is not a short-term rental — this is a data entry error.

**Why cap instead of drop:**
The listing itself is valid (has price, location, reviews). Only the
minimum_nights value is erroneous. Dropping the row would lose valid data.
Capping at 365 (1 year) is the maximum reasonable short-term rental minimum.

**Scope:** 2 listings in listings.csv.gz, 731 records in calendar.csv.gz.

---

### DEC-010 — maximum_nights INT_MAX replaced with NaN

**Decision:** `maximum_nights = 2,147,483,647` (INT_MAX) replaced with `NaN`.

**Context:** 730 calendar records had this value. It is the maximum value of
a 32-bit signed integer — used by Airbnb's system as a sentinel meaning
"no maximum night restriction."

**Why NaN and not a large number:**
Keeping INT_MAX would make average maximum_nights calculations meaningless
(average would be in the millions). NaN correctly excludes these records
from max_nights aggregations while retaining them for availability analysis.

---

### DEC-011 — neighbourhood_cleansed used as canonical geo field

**Decision:** `neighbourhood_cleansed` (always populated, standardized by
Inside Airbnb) is used instead of raw `neighbourhood` (>50% null,
user-entered, inconsistent casing).

**Options considered:**

| Field | Null rate | Source | Consistency |
|-------|-----------|--------|-------------|
| neighbourhood | >50% null | Host-entered | Inconsistent casing, typos |
| neighbourhood_cleansed | 0% null | Inside Airbnb standardized | Consistent, matches GeoJSON |
| neighbourhood_group_cleansed | >50% null | Inside Airbnb | Not used in Amsterdam |

**Why this matters:**
Using raw `neighbourhood` would mean "Centrum", "centrum", and "De Centrum"
are treated as 3 different neighbourhoods in GROUP BY operations. Using
`neighbourhood_cleansed` ensures all 10,480 listings are correctly assigned
to exactly 22 Amsterdam neighbourhoods, matching the GeoJSON boundaries
used for choropleth mapping.

---

### DEC-012 — Modular cleaning architecture (3 sub-modules)

**Decision:** Splitting cleaning into `standardizer.py`, `missing_values.py`,
and `geo_cleaner.py` rather than one monolithic `cleaner.py`.

**Why:**
- **Separation of concerns:** Format issues (standardizer) are completely
  different from null treatment decisions (missing_values) and geographic
  normalization (geo_cleaner). Mixing them makes each harder to reason about.
- **Testability:** Each module can be unit tested independently.
- **Maintainability:** If Inside Airbnb changes their price format, only
  `standardizer.py` needs updating.
- **Order dependency is explicit:** The orchestrator (`cleaner.py`) calls
  standardizer → missing_values → geo_cleaner in a defined order that is
  documented and enforced.

**Trade-offs accepted:**
More files to navigate. Mitigated by clear naming and docstrings in each file.

---

## Section 3 — Analysis Decisions

### DEC-013 — Median used instead of mean for price comparisons

**Decision:** All neighbourhood and room-type price comparisons use **median**
rather than mean.

**Why:**
Profiling found 301 price outliers (5.12%) with prices up to €80,018/night.
These extreme values pull the mean significantly upward, misrepresenting the
typical listing price. Median is robust to outliers and better represents
"what a typical listing costs" in each neighbourhood.

**Used consistently in:**
- Neighbourhood price ranking
- Room type price comparison
- Host segment pricing analysis
- All EDA visualizations

---

### DEC-014 — Star schema: fact_listings + 3 dimensions

**Decision:** Dimensional model with `fact_listings` as the central fact table
and `dim_host`, `dim_neighbourhood`, `dim_room_type` as dimensions.

**Why star schema over 3NF:**
- Optimized for analytical queries (fewer JOINs, faster GROUP BY)
- Matches the query patterns needed: "avg price by neighbourhood", "superhost vs non-superhost"
- DuckDB's columnar storage benefits from denormalized fact tables

**Trade-offs accepted:**
Some redundancy (host attributes repeated if host has multiple listings).
For 10,480 listings this is negligible. In a production multi-city system,
slowly changing dimensions (SCD Type 2) would be implemented for host attributes.

---

*Entries will be added as EDA, statistical analysis, and ML modelling decisions are made.*
