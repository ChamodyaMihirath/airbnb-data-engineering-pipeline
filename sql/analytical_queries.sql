-- ============================================================
-- analytical_queries.sql  —  Section 3.4
-- Key business queries demonstrating the star schema
-- Amsterdam Airbnb Market Intelligence
-- ============================================================
-- Run against: data/database/airbnb_amsterdam.duckdb
-- ============================================================


-- ── Q1: Neighbourhood price ranking ──────────────────────────
-- Business question: Which Amsterdam neighbourhoods command
-- the highest prices, and how do they compare?
SELECT
    n.neighbourhood,
    n.neighbourhood_price_tier,
    n.neighbourhood_price_rank,
    ROUND(n.neighbourhood_median_price, 2)      AS median_price,
    ROUND(n.neighbourhood_mean_price, 2)        AS mean_price,
    n.neighbourhood_listing_count               AS listing_count,
    ROUND(n.neighbourhood_avg_rating, 2)        AS avg_rating,
    ROUND(n.neighbourhood_avg_occupancy * 100, 1) AS occupancy_pct
FROM dim_neighbourhood n
ORDER BY n.neighbourhood_price_rank ASC;


-- ── Q2: Room type pricing comparison ─────────────────────────
-- Business question: How much premium do entire homes command
-- over private rooms? (Used in hypothesis test H1)
SELECT
    r.room_type,
    r.room_category,
    COUNT(f.listing_id)                         AS listing_count,
    ROUND(MEDIAN(f.price), 2)                   AS median_price,
    ROUND(AVG(f.price), 2)                      AS mean_price,
    ROUND(PERCENTILE_CONT(0.25)
        WITHIN GROUP (ORDER BY f.price), 2)     AS p25_price,
    ROUND(PERCENTILE_CONT(0.75)
        WITHIN GROUP (ORDER BY f.price), 2)     AS p75_price,
    ROUND(AVG(f.review_scores_rating), 3)       AS avg_rating
FROM fact_listings f
JOIN dim_room_type r ON f.room_type = r.room_type
WHERE f._is_valid = TRUE
GROUP BY r.room_type, r.room_category
ORDER BY median_price DESC;


-- ── Q3: Superhost vs non-superhost comparison ────────────────
-- Business question: Do superhosts achieve better ratings
-- and higher prices? (Used in hypothesis test H2)
SELECT
    h.host_is_superhost,
    COUNT(f.listing_id)                             AS listing_count,
    ROUND(MEDIAN(f.price), 2)                       AS median_price,
    ROUND(AVG(f.price), 2)                          AS mean_price,
    ROUND(AVG(f.review_scores_rating), 3)           AS avg_rating,
    ROUND(AVG(f.occupancy_rate) * 100, 1)           AS avg_occupancy_pct,
    ROUND(AVG(f.estimated_annual_revenue_computed), 0)
                                                    AS avg_est_revenue
FROM fact_listings f
JOIN dim_host h ON f.host_id = h.host_id
WHERE f._is_valid = TRUE
GROUP BY h.host_is_superhost
ORDER BY h.host_is_superhost DESC;


-- ── Q4: Host market concentration ────────────────────────────
-- Business question: What % of the market is controlled by
-- commercial operators (Airbnb "professionalization")?
SELECT
    h.host_segment,
    COUNT(DISTINCT h.host_id)                   AS host_count,
    COUNT(f.listing_id)                         AS total_listings,
    ROUND(
        COUNT(f.listing_id) * 100.0 /
        SUM(COUNT(f.listing_id)) OVER (), 1
    )                                           AS pct_of_market,
    ROUND(MEDIAN(f.price), 2)                   AS median_price,
    ROUND(AVG(f.review_scores_rating), 3)       AS avg_rating
FROM fact_listings f
JOIN dim_host h ON f.host_id = h.host_id
GROUP BY h.host_segment
ORDER BY total_listings DESC;


-- ── Q5: Weekend vs weekday occupancy ─────────────────────────
-- Business question: Is there a statistically meaningful
-- weekend pricing/occupancy premium? (Hypothesis H5)
SELECT
    is_weekend,
    COUNT(*)                                    AS day_count,
    ROUND(
        SUM(CASE WHEN available = FALSE THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 2
    )                                           AS occupancy_pct,
    ROUND(AVG(price), 2)                        AS avg_price
FROM fact_calendar
WHERE price IS NOT NULL
GROUP BY is_weekend
ORDER BY is_weekend DESC;


-- ── Q6: Top revenue neighbourhoods ───────────────────────────
-- Business question: Where should an investor buy a property
-- to maximise Airbnb revenue?
SELECT
    f.neighbourhood,
    COUNT(f.listing_id)                             AS listing_count,
    ROUND(MEDIAN(f.price), 2)                       AS median_price,
    ROUND(AVG(f.occupancy_rate) * 100, 1)           AS avg_occupancy_pct,
    ROUND(AVG(f.estimated_annual_revenue_computed), 0)
                                                    AS avg_est_revenue,
    ROUND(MAX(f.estimated_annual_revenue_computed), 0)
                                                    AS max_est_revenue
FROM fact_listings f
WHERE f._is_valid = TRUE
  AND f.estimated_annual_revenue_computed IS NOT NULL
GROUP BY f.neighbourhood
ORDER BY avg_est_revenue DESC
LIMIT 10;


-- ── Q7: Review score sub-dimensions by room type ─────────────
-- Business question: Do entire homes score better on cleanliness
-- but worse on value than private rooms?
SELECT
    room_type,
    ROUND(AVG(review_scores_rating), 3)         AS overall,
    ROUND(AVG(review_scores_cleanliness), 3)    AS cleanliness,
    ROUND(AVG(review_scores_location), 3)       AS location,
    ROUND(AVG(review_scores_communication), 3)  AS communication,
    ROUND(AVG(review_scores_checkin), 3)        AS checkin,
    ROUND(AVG(review_scores_value), 3)          AS value
FROM fact_listings
WHERE review_scores_rating IS NOT NULL
GROUP BY room_type
ORDER BY overall DESC;


-- ── Q8: Seasonal availability trend ──────────────────────────
-- Business question: When is Amsterdam Airbnb demand highest?
SELECT
    month_name,
    month,
    COUNT(*)                                    AS total_days,
    ROUND(
        SUM(CASE WHEN available = FALSE THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 2
    )                                           AS occupancy_pct
FROM fact_calendar
GROUP BY month_name, month
ORDER BY month ASC;
