# Assumptions Log
## Amsterdam Airbnb Market Intelligence
## Expernetic Data Engineer Intern — Technical Assessment

**City:** Amsterdam, Netherlands  
**Data source:** Inside Airbnb (https://insideairbnb.com/get-the-data/)  
**Scrape date:** As published on Inside Airbnb (single point-in-time snapshot)  
**Last updated:** June 2026

---

> This log documents every assumption made during ingestion, profiling, cleaning,
> enrichment, and analysis. Each entry explains what was assumed, why, and what
> the implications are for downstream analysis.
> Assumptions are numbered for traceability to the decision log.

---

## A. Data Source Assumptions

### A-01 — Single point-in-time scrape
Inside Airbnb data represents a **single scrape**, not a continuous feed.
All listings, prices, and availability reflect conditions on the scrape date only.
Longitudinal trends are approximated using:
- `calendar.csv.gz` for forward-looking availability (365 days from scrape)
- `first_review` / `last_review` dates for historical activity
- `number_of_reviews` as a proxy for cumulative demand

**Implication:** We cannot detect listings that were active between scrapes but
are now inactive, or prices that changed after the scrape date.

### A-02 — Reviews as a booking demand proxy
Actual booking counts are **not available** in the Inside Airbnb dataset.
`number_of_reviews` and `reviews_per_month` are used as proxies for demand.

**Known limitation:** Not all guests leave reviews. Review rates vary by host,
nationality, and listing type. Estimates based on reviews undercount true bookings.
Inside Airbnb estimates approximately 50–70% of guests leave reviews.

**Implication:** Occupancy and demand estimates are directionally correct but
not precise. All demand metrics are labelled as estimates in the report.

### A-03 — Data covers active listings only
Inside Airbnb scrapes only listings **visible on Airbnb at scrape time**.
Delisted, suspended, or hidden listings are not included.
The dataset therefore represents the currently active supply, not historical supply.

---

## B. Price Assumptions

### B-01 — Currency is EUR
All price values are treated as **Euro (€)**.
Amsterdam is the only city in this analysis and Airbnb NL displays prices in EUR.
No currency conversion is applied.

### B-02 — listings.price format is "$132.00" string
The raw `listings.price` column is stored as a **string with a dollar sign prefix**
(e.g. `"$132.00"`) by Inside Airbnb regardless of actual currency.
Cleaning strips the `$` and `,` characters and casts to float.
### B-02 — 4,606 listings have no price in source data (genuine missing)

Profiling confirmed that 4,606 listings (43.95%) have an **empty price field**
in the raw `listings.csv.gz` source file. This is NOT a parsing issue —
the source data genuinely contains no price for these listings.

Verified by: `(raw["price"] == "").sum() == 4606` with `keep_default_na=False`
and `dtype={"price": str}` — confirming empty strings, not unparseable formats.

Likely causes (Inside Airbnb known limitation):
  - Host deactivated pricing without removing the listing
  - Listing is in draft/inactive state but still scraped
  - Airbnb API returned no price at scrape time

Decision: Set to NaN, flagged via _is_valid=False.
Excluded from price analysis only. Location, reviews, and host
data for these listings remain valid and used in non-price analyses.
5,874 listings (56.05%) have valid prices for all pricing analyses.

**Profiling finding:** 4,606 listings (43.95%) appeared null before cleaning
because pandas read `"$132.00"` strings as NaN. After cleaning, all 10,480
listings have a valid price.

**Decision:** Used `str.replace("$", "", regex=False)` instead of regex
character class — more reliable across platforms. See DEC-003.

### B-03 — Price = 0 is invalid
Listings with `price = 0` after cleaning are treated as **invalid** and
flagged via `_is_valid = False`. A price of zero indicates either:
- A data entry error by the host
- A blocked/unavailable listing not properly excluded

**Decision:** Set to NaN rather than drop — the listing may still have valid
review, location, and host data useful for non-price analyses.

### B-04 — calendar.price is empty in Amsterdam dataset
The `calendar.csv.gz` price column is **entirely null** for Amsterdam.
This is a known data publication issue for some cities in Inside Airbnb —
the calendar file records availability but not daily price for this market.

**Implication:** Seasonal price analysis uses `listings.price` (the base listed
price) rather than calendar-derived daily prices. Weekend/weekday pricing
differences cannot be computed from calendar data for Amsterdam.

**Documented in:** decision_log.md DEC-007

### B-05 — adjusted_price dropped
`adjusted_price` in `calendar.csv.gz` is **100% null** for Amsterdam.
Column dropped entirely during cleaning to reduce memory footprint.
No analytical value lost.

### B-06 — Extreme price outliers retained
301 listings (5.12%) have prices above the IQR upper fence of €543.50,
with a maximum of €80,018/night.
These are **retained but noted** — they likely represent luxury properties,
entire canal houses, or data errors. Median is used instead of mean for all
neighbourhood price comparisons to be robust to these outliers.

---

## C. Availability and Occupancy Assumptions

### C-01 — availability = FALSE means booked
In the calendar, `available = "f"` (false) is treated as **booked**.
Inside Airbnb uses this methodology (Murray Cox / San Francisco model).

**Known limitation:** Hosts can also block dates for personal use without
a booking. These blocked-but-not-booked days are indistinguishable from
actual bookings in the data. Occupancy rates are therefore **upper bound
estimates**, not confirmed booking rates.

### C-02 — estimated_occupancy_l365d is pre-computed
Inside Airbnb pre-computes `estimated_occupancy_l365d` using their own
methodology. This column is used **directly** rather than recomputed from
calendar availability. This ensures consistency with Inside Airbnb's published
figures and avoids double-counting.

**Capping applied:** Values above 365 (found: max=255 in profiling, cap set at
365 defensively) are capped — occupancy days cannot exceed days in the year.

### C-03 — estimated_revenue_l365d is pre-computed
Same as C-02 — `estimated_revenue_l365d` is used directly from Inside Airbnb's
pre-computation. Formula: estimated_occupancy × listing price (approximate).
This is an estimate, not actual host earnings (Airbnb fees not deducted).

---

## D. Geographic Assumptions

### D-01 — neighbourhood_cleansed is the canonical neighbourhood field
The raw `neighbourhood` column is **>50% null** (user-entered by hosts,
inconsistent casing and spelling). `neighbourhood_cleansed` is used as the
canonical neighbourhood field — standardized by Inside Airbnb from official
Amsterdam district boundaries.

All neighbourhood-level analysis uses `neighbourhood_cleansed`.

### D-02 — 22 neighbourhoods are complete and correct
Amsterdam has exactly **22 neighbourhoods** in this dataset, matching the
official Amsterdam district map. All 10,480 listings have a valid
`neighbourhood_cleansed` value. No neighbourhood imputation was needed.

### D-03 — Coordinate precision rounded to 5 decimal places
Coordinates are rounded to **5 decimal places** (~1.1m ground precision).
Inside Airbnb already applies a ~150m privacy jitter to all listing coordinates,
so storing more than 5 decimal places adds no real precision and wastes storage.

### D-04 — All listings within Amsterdam bounding box
Bounding box used: lat [52.20, 52.50], lon [4.70, 5.10].
**Profiling result:** 0 listings fell outside this box — all coordinates are
valid Amsterdam locations. No coordinate invalidation was needed.

### D-05 — neighbourhood_group_cleansed is mostly null
`neighbourhood_group_cleansed` is **>50% null** in the Amsterdam dataset.
Amsterdam does not use borough-level groupings in the same way as NYC.
This column is retained but not used as a primary grouping variable.
`neighbourhood_cleansed` (22 values) is used instead.

---

## E. Host and Listing Assumptions

### E-01 — host_since used for tenure calculation
`host_tenure_years` is computed as `(today - host_since) / 365.25`.
This measures time since the host first joined Airbnb, not time since
this specific listing was created. A host may have listed this property
long after joining the platform.

**Implication:** host_tenure_years is a proxy for host experience, not
listing age. Used for host segmentation analysis only.

### E-02 — beds imputed from accommodates
`beds` is null for ~44% of listings (not 2.92% as initially estimated from
profiling — the profiling ran on raw data before dtype casting revealed more nulls).
Imputed as `ceil(accommodates / 2)` where null.

**Why this imputation:**
- Strong correlation between accommodates and beds in non-null data
- Better than mean imputation (uses listing-specific context)
- Better than dropping (would lose 44% of listings for bed-based analysis)

**Caveat:** Studios and sofa-beds may be over-counted as beds.
Documented for any beds-based analysis.

### E-03 — host_segment based on host_total_listings_count
Hosts are segmented as:
- **Single-listing:** 1 listing (casual/home-sharer)
- **Small (2–5):** small portfolio host
- **Medium (6–20):** semi-professional operator
- **Commercial (20+):** professional/commercial operator

Thresholds based on Inside Airbnb's own research and common academic
definitions of commercial hosting.

### E-04 — minimum_nights > 365 treated as data error
2 listings in `listings.csv.gz` and 731 records in `calendar.csv.gz`
have `minimum_nights > 365`. A minimum stay longer than one year is
not consistent with short-term rental operations.
**Decision:** Cap at 365, not drop — listing is otherwise valid.

### E-05 — maximum_nights INT_MAX is "no maximum" sentinel
730 calendar records have `maximum_nights = 2,147,483,647` (= 2³¹ − 1,
the maximum value of a 32-bit signed integer).
This is a **sentinel value** used by Airbnb's system to mean "no maximum
night restriction." It is replaced with `NaN` — not a real value.

---

## F. Reviews Assumptions

### F-01 — review_scores_rating null means no reviews yet
10.47% of listings have null `review_scores_rating`.
This means the listing has **not yet received any reviews**, not that the
rating is zero or unknown. These listings are excluded from rating analysis
but retained for price and availability analysis.

**Decision:** Explicit NaN retained — filling with 0 or mean would distort
rating distributions.

### F-02 — 1 auto-generated review detected and flagged
1 review was flagged as auto-generated based on text pattern matching
("the host canceled", "automatically collected", etc.).
Flagged via `_is_auto_review = True`, not dropped.
Excluded from sentiment/NLP analysis but counted in review metrics.

### F-03 — Review date used for temporal trend analysis
Review dates represent when a guest **submitted** the review, which is
typically within days of checkout. Review date is used as a proxy for
booking date in temporal demand analysis.

---

## G. Pipeline and Technical Assumptions

### G-01 — .gz files read directly, no manual extraction
All `.gz` files (listings, calendar, reviews) are read directly by pandas
using `compression="gzip"`. No manual extraction is performed.

**Why:** Manual extraction creates duplicate files (both `.csv.gz` and extracted
`.csv` present), causing the loader to potentially read the wrong file.
Direct `.gz` reading eliminates this ambiguity entirely.

### G-02 — Parquet used for processed files
Cleaned datasets are saved as `.parquet` rather than `.csv`.
Reasons: preserves dtypes exactly, ~5x smaller file size, faster read times.

### G-03 — Single city analysis (Amsterdam only)
Only Amsterdam is analyzed. `city = "Amsterdam"` column added to all tables
to support future multi-city pipeline extension without schema changes.

---

*This log is a living document. New entries are added as new assumptions
are identified during EDA, statistical analysis, and modelling.*
