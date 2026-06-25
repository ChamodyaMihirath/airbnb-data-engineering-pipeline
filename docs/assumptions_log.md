# Challenge 2: Dataset Familiarization & Assumptions Log

**Market Focused:** Amsterdam, Netherlands  
**Snapshot Baseline Date:** September 11, 2025  
**Ecosystem Operational Boundary:** Short-Term Rental Marketplace Analytics  

---

## 1. Business Domain Context & Entity Definitions

To build a high-fidelity business intelligence engine, the primary data entities from the Inside Airbnb schema are mapped to their respective marketplace roles:

* **The Listing (`listings.csv.gz`):** Represents the core capital asset (the unit of inventory) circulating in the marketplace ecosystem. It defines capacity boundaries (`accommodates`, `bedrooms`, `beds`), geographical positioning (`latitude`, `longitude`, `neighbourhood_cleansed`), and fixed master parameters set by the provider.
* **The Host (Master Attributes within `listings`):** Represents the supply-side entrepreneur or institutional property management partner. Behavioral metadata allows the platform to segment the market into peer-to-peer single-property casual hosts versus highly commercial multi-listing portfolio corporations.
* **The Calendar (`calendar.csv.gz`):** Represents the forward-looking operational ledger and yield-management layer. It tracks daily inventory state and pricing fluctuations across a 365-day strategic horizon, capturing temporal supply spikes, weekends, and seasonal pricing models.
* **The Review (`reviews.csv.gz`):** Represents the consumer transaction proxy and platform trust loop. Because true transaction volumes, financial conversion invoices, and cancellations are proprietary, historic review velocity serves as our core analytical proxy for transactional demand.

---

## 2. Entity-Relationship (ER) Topology & Key Mapping

The relational structure of the raw staging area relies on the following primary and foreign key constraints:

* **`listings` Dimension:** Relational Anchor.
    * *Primary Key:* `id` (verified programmatic uniqueness: `listings['id'].is_unique == True`).
* **`calendar` Fact Layer:** High-volume time-series ledger (~3.82M entries).
    * *Composite Primary Key:* (`listing_id`, `date`).
    * *Foreign Key:* `listing_id` references `listings.id` ($N:1$ cardinality relation).
* **`reviews` Fact Layer:** Unstructured historical log (~501K entries).
    * *Primary Key:* `id` (Unique review signature).
    * *Foreign Key:* `listing_id` references `listings.id` ($N:1$ cardinality relation).

---

## 3. Scheme Observations & Explicit Interpretation Gotchas

Based on programmatic column profiling (`.dtypes`), the following attributes require custom structural transformations within the cleaning layer before downstream numerical execution can occur:

| Raw Column Name | Native Data Type | Target Engine Schema | Interpretive Hazard / Engineering Choice |
| :--- | :--- | :--- | :--- |
| `listings.price` | `object` (String) | `float64` (Dropped) | **The Price Trap:** Contains text characters (`$`, `,`) and registers a **43.95% missingness rate**. This column will be treated as corrupted/unreliable. Pricing figures will be fetched exclusively from `calendar.price`. |
| `calendar.price` | `float64` | `float64` | Stable time-series matrix registering **0.00% missing values**. This serves as the definitive pricing source. |
| `calendar.available`| `object` (String) | `bool` | Logged as `'t'` or `'f'`. Must be mapped into `True` or `False`. |
| `listings.beds` | `float64` | `int64` | Registers an exceptionally high **43.66% missingness rate** in the raw profile. Requires fallback imputation logic. |
| `bathrooms_text` | `object` (String) | `float64` | No numeric bathroom column exists. Text string details (e.g., `"1.5 private baths"`) require regular expression (regex) parsing. |

---

## 4. Dataset Limitations & Scraping Artifacts

* **Transactional Blind Spot:** The dataset completely lacks historical payment statements, cancellations, or actual booked reservations.
* **Calendar Volatility Noise:** A future date marked as unavailable (`available == 'f'`) does not guarantee a guest booked it. It may reflect a host blocking dates out for personal maintenance, private use, or local legal compliance gaps.
* **Review Sparsity Bias:** Guest feedback loops are voluntary. Not every completed transaction yields a review, meaning raw review counts introduce a natural underestimation of total marketplace transaction volume.

---

## 5. Explicit Analytical & Pipeline Transformation Rules

To eliminate ambiguity across our ETL and data science routines, the following operational logic definitions are frozen into effect:

### Rule 1: Missing 'Beds' Imputation Architecture
For any listing record presenting a null value in the `beds` column, the cleaning pipeline will programmatically infer the asset capacity based on its `accommodates` value:
$$\text{imputed\_beds} = \max\left(1, \text{round}\left(\frac{\text{accommodates}}{2}\right)\right)$$

### Rule 2: Demand Volume Estimation (The San Francisco Model Proxy)
To account for the transactional blind spot, demand calculations will assume an industry-standard review-to-stay conversion rate of **50%**. Every historical review entry represents exactly **2 completed transactions**:
$$\text{Estimated Stays} = \text{Total Historical Reviews} \times 2$$

### Rule 3: Length of Stay (LOS) Derivation
Where a historical stay is inferred from a review record, the duration of that reservation is assumed to equal the listing's configured `minimum_nights` metric, bounded by a strict protection limit:
* If `minimum_nights` $< 1$: Force default to **1 night**.
* If `minimum_nights` $> 30$ (Mid/Long-term corporate rentals): Cap the short-term stay velocity estimation at a conservative industry baseline of **3 nights** to prevent massive metric inflation.

### Rule 4: Future Capacity Booking Proxy
When conducting forward-looking vacancy or predictive market pricing modeling via the `calendar` tables, any day flagged as `available == False` is explicitly assumed to represent a **revenue-generating booking** secured by an active market traveler.