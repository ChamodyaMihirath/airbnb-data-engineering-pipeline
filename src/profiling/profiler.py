"""
profiler.py
-----------
Generates a comprehensive data quality report for all Amsterdam Airbnb datasets.
Covers: row counts, null rates, cardinality, outliers, duplicates, domain validation.

Usage:
    from profiling.profiler import DataProfiler
    profiler = DataProfiler()
    report   = profiler.profile_all(datasets)
    profiler.save_report(report, output_path)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from difflib import SequenceMatcher


class DataProfiler:

    # ── Column-level profile ───────────────────────────────────────

    def profile_dataframe(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """
        Column-level profile: dtype, null rate, cardinality, sample values,
        min/max/mean/std for numerics.
        """
        print(f"\nProfiling [{name}] — {df.shape[0]:,} rows × {df.shape[1]} cols")
        records = []

        for col in df.columns:
            s = df[col]
            null_count = int(s.isna().sum())
            null_pct   = round(null_count / len(s) * 100, 2)
            unique     = int(s.nunique(dropna=True))
            samples    = str(s.dropna().head(3).tolist())

            row = {
                "dataset":       name,
                "column":        col,
                "dtype":         str(s.dtype),
                "null_count":    null_count,
                "null_pct":      null_pct,
                "unique_values": unique,
                "sample_values": samples,
                "min":  None, "max": None,
                "mean": None, "std": None,
            }

            if pd.api.types.is_numeric_dtype(s):
                row.update({
                    "min":  round(float(s.min()), 4) if not s.isna().all() else None,
                    "max":  round(float(s.max()), 4) if not s.isna().all() else None,
                    "mean": round(float(s.mean()), 4) if not s.isna().all() else None,
                    "std":  round(float(s.std()), 4) if not s.isna().all() else None,
                })

            records.append(row)

        profile = pd.DataFrame(records)

        high_null = profile[profile["null_pct"] > 50]["column"].tolist()
        if high_null:
            print(f"  ⚠️  High-null columns (>50%): {high_null}")

        return profile

    # ── Outlier detection ──────────────────────────────────────────

    def detect_outliers(self, df: pd.DataFrame, columns: list, name: str) -> pd.DataFrame:
        """IQR-based outlier detection for specified numeric columns."""
        print(f"\nDetecting outliers in [{name}]")
        records = []

        for col in columns:
            if col not in df.columns:
                continue

            s = df[col]
            # Handle price strings like "$150.00"
            if s.dtype == object:
                s = pd.to_numeric(
                    s.astype(str).str.replace(r"[\$,]", "", regex=True),
                    errors="coerce"
                )

            s = s.dropna()
            if len(s) == 0:
                continue

            Q1  = s.quantile(0.25)
            Q3  = s.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR

            outliers      = s[(s < lower) | (s > upper)]
            outlier_pct   = round(len(outliers) / len(s) * 100, 2)
            extreme_high  = s[s > (Q3 + 3 * IQR)]

            records.append({
                "dataset":            name,
                "column":             col,
                "count":              len(s),
                "Q1":                 round(Q1, 2),
                "median":             round(float(s.median()), 2),
                "Q3":                 round(Q3, 2),
                "IQR":                round(IQR, 2),
                "lower_fence":        round(lower, 2),
                "upper_fence":        round(upper, 2),
                "outlier_count":      len(outliers),
                "outlier_pct":        outlier_pct,
                "extreme_high_count": len(extreme_high),
                "max_value":          round(float(s.max()), 2),
            })

            if len(outliers) > 0:
                print(
                    f"  ⚠️  [{col}] {len(outliers):,} outliers ({outlier_pct}%)"
                    f" | fence: [{round(lower,2)}, {round(upper,2)}]"
                    f" | max: {round(float(s.max()),2)}"
                )

        return pd.DataFrame(records)

    # ── Duplicate detection ────────────────────────────────────────

    def detect_exact_duplicates(self, df: pd.DataFrame, id_col: str, name: str) -> dict:
        """Detect exact duplicate rows and duplicate primary key values."""
        row_dupes = int(df.duplicated().sum())
        id_dupes  = int(df[id_col].duplicated().sum()) if id_col in df.columns else 0

        print(
            f"\n[{name}] Exact duplicate rows: {row_dupes} | "
            f"Duplicate {id_col}s: {id_dupes}"
        )
        return {
            "dataset":             name,
            "duplicate_rows":      row_dupes,
            "duplicate_rows_pct":  round(row_dupes / len(df) * 100, 3),
            f"duplicate_{id_col}": id_dupes,
        }

    # ── Fuzzy duplicate detection ──────────────────────────────────

    def detect_fuzzy_duplicates(
        self,
        df: pd.DataFrame,
        col: str,
        name: str,
        threshold: float = 0.90,
        sample_size: int = 500,
    ) -> pd.DataFrame:
        """
        Fuzzy duplicate detection using SequenceMatcher on a text column.
        Samples for performance — full scan on 10k listings is too slow.
        Returns pairs of similar strings above the similarity threshold.
        """
        print(f"\n[Fuzzy check] {name}.{col} (threshold={threshold})")

        values = (
            df[col].dropna()
                   .astype(str)
                   .str.strip()
                   .str.lower()
                   .drop_duplicates()
                   .sample(min(sample_size, df[col].nunique()), random_state=42)
                   .tolist()
        )

        pairs = []
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                ratio = SequenceMatcher(None, values[i], values[j]).ratio()
                if ratio >= threshold:
                    pairs.append({
                        "value_a":    values[i],
                        "value_b":    values[j],
                        "similarity": round(ratio, 3),
                    })

        result = pd.DataFrame(pairs).sort_values(
            "similarity", ascending=False
        ) if pairs else pd.DataFrame(columns=["value_a", "value_b", "similarity"])

        print(f"  Fuzzy pairs found: {len(result)}")
        return result

    # ── Completeness assessment ────────────────────────────────────

    def assess_completeness(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """
        Rank columns by null rate. Flag business-critical fields and add
        implication text explaining the impact of missingness.
        """
        print(f"\nChecking completeness [{name}]")

        # Business-critical fields and what their missingness means
        CRITICAL_FIELDS = {
            "listings": {
                "price":                   "Cannot price-analyse this listing",
                "latitude":                "Cannot map or geo-analyse",
                "longitude":               "Cannot map or geo-analyse",
                "neighbourhood_cleansed":  "Cannot assign to neighbourhood",
                "room_type":               "Cannot segment by room type",
                "review_scores_rating":    "Cannot assess listing quality",
                "bedrooms":                "Cannot compute price-per-bedroom",
                "host_is_superhost":       "Cannot segment by host tier",
            },
            "calendar": {
                "price":     "Cannot perform seasonal price analysis",
                "date":      "Cannot perform temporal analysis",
                "available": "Cannot estimate occupancy",
            },
            "reviews": {
                "comments":   "Cannot perform sentiment/NLP analysis",
                "date":       "Cannot perform temporal review trend analysis",
                "listing_id": "Cannot link review to listing",
            },
        }

        null_summary = (
            df.isnull().sum()
              .reset_index()
              .rename(columns={"index": "column", 0: "null_count"})
        )
        null_summary["null_pct"]    = (null_summary["null_count"] / len(df) * 100).round(2)
        null_summary["is_critical"] = null_summary["column"].isin(
            CRITICAL_FIELDS.get(name, {}).keys()
        )
        null_summary["implication"] = null_summary["column"].map(
            CRITICAL_FIELDS.get(name, {})
        ).fillna("")
        null_summary = null_summary.sort_values("null_pct", ascending=False)

        # Warn on critical fields that are missing
        critical_high = null_summary[
            null_summary["is_critical"] & (null_summary["null_pct"] > 5)
        ]
        for _, row in critical_high.iterrows():
            print(
                f"  ⚠️  CRITICAL '{row['column']}' is {row['null_pct']}% null"
                f" → {row['implication']}"
            )

        return null_summary

    # ── Domain validation ──────────────────────────────────────────

    def validate_domain_rules(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """
        Check business domain rules per dataset.
        Returns a violations summary DataFrame.
        """
        print(f"\nValidating domain rules [{name}]")
        violations = []

        if name == "listings":
            price_raw = pd.to_numeric(
                df["price"].astype(str).str.replace(r"[\$,]", "", regex=True),
                errors="coerce"
            )
            violations = [
                {
                    "rule":       "price > 0",
                    "violations": int((price_raw <= 0).sum()),
                    "action":     "Set to NaN, exclude from price analysis",
                },
                {
                    "rule":       "price parseable",
                    "violations": int(price_raw.isna().sum()),
                    "action":     "Strip $ and , symbols, cast to float",
                },
                {
                    "rule":       "latitude in [50.7, 53.6]",
                    "violations": int((~df["latitude"].between(50.7, 53.6)).sum())
                                  if "latitude" in df.columns else 0,
                    "action":     "Flag as invalid, exclude from spatial analysis",
                },
                {
                    "rule":       "longitude in [3.3, 7.3]",
                    "violations": int((~df["longitude"].between(3.3, 7.3)).sum())
                                  if "longitude" in df.columns else 0,
                    "action":     "Flag as invalid, exclude from spatial analysis",
                },
                {
                    "rule":       "availability_365 in [0, 365]",
                    "violations": int((~df["availability_365"].between(0, 365)).sum())
                                  if "availability_365" in df.columns else 0,
                    "action":     "Cap at 365 or set to NaN",
                },
            ]

        elif name == "calendar":
            violations = [
                {
                    "rule":       "available in {t, f}",
                    "violations": int((~df["available"].isin(["t", "f"])).sum())
                                  if "available" in df.columns else 0,
                    "action":     "Map to bool, set others to NaN",
                },
                {
                    "rule":       "date is parseable",
                    "violations": int(pd.to_datetime(df["date"], errors="coerce").isna().sum())
                                  if "date" in df.columns else 0,
                    "action":     "Drop rows with unparseable dates",
                },
            ]

        elif name == "reviews":
            violations = [
                {
                    "rule":       "date is parseable",
                    "violations": int(pd.to_datetime(df["date"], errors="coerce").isna().sum())
                                  if "date" in df.columns else 0,
                    "action":     "Drop rows with unparseable dates",
                },
                {
                    "rule":       "listing_id not null",
                    "violations": int(df["listing_id"].isna().sum())
                                  if "listing_id" in df.columns else 0,
                    "action":     "Drop orphan reviews",
                },
            ]

        result = pd.DataFrame(violations)
        if not result.empty:
            result.insert(0, "dataset", name)

        return result

    # ── Master pipeline ────────────────────────────────────────────

    def profile_all(self, datasets: dict) -> dict:
        """
        Run full profiling suite on all datasets.

        Returns dict with keys:
            column_profiles, outliers, completeness,
            domain_violations, duplicate_summary
        """
        print("\n" + "=" * 55)
        print("  FULL DATA QUALITY PROFILING")
        print("=" * 55)

        all_profiles     = []
        all_outliers     = []
        all_dupes        = []
        all_completeness = []
        all_violations   = []

        # Per-dataset configuration
        config = {
            "listings": {
                "id_col":        "id",
                "fuzzy_col":     "name",
                "outlier_cols":  [
                    "price", "availability_365", "number_of_reviews",
                    "minimum_nights", "estimated_revenue_l365d",
                    "estimated_occupancy_l365d",
                ],
            },
            "calendar": {
                "id_col":       "listing_id",
                "fuzzy_col":    None,
                "outlier_cols": ["price", "minimum_nights", "maximum_nights"],
            },
            "reviews": {
                "id_col":       "id",
                "fuzzy_col":    None,
                "outlier_cols": [],
            },
            "neighbourhoods": {
                "id_col":       None,
                "fuzzy_col":    None,
                "outlier_cols": [],
            },
        }

        for name, df in datasets.items():
            if not isinstance(df, pd.DataFrame):
                continue

            cfg = config.get(name, {})

            # 1. Column profile
            all_profiles.append(self.profile_dataframe(df, name))

            # 2. Outliers
            if cfg.get("outlier_cols"):
                all_outliers.append(
                    self.detect_outliers(df, cfg["outlier_cols"], name)
                )

            # 3. Exact duplicates
            if cfg.get("id_col"):
                all_dupes.append(
                    self.detect_exact_duplicates(df, cfg["id_col"], name)
                )

            # 4. Fuzzy duplicates (listings only — too slow on large datasets)
            if name == "listings" and cfg.get("fuzzy_col"):
                fuzzy = self.detect_fuzzy_duplicates(
                    df, cfg["fuzzy_col"], name, threshold=0.90
                )
                if not fuzzy.empty:
                    print(f"  ⚠️  {len(fuzzy)} near-duplicate listing names found")

            # 5. Completeness
            all_completeness.append(self.assess_completeness(df, name))

            # 6. Domain rules
            all_violations.append(self.validate_domain_rules(df, name))

        return {
            "column_profiles":   pd.concat(all_profiles,     ignore_index=True),
            "outliers":          pd.concat(all_outliers,      ignore_index=True)
                                 if all_outliers else pd.DataFrame(),
            "completeness":      pd.concat(all_completeness,  ignore_index=True),
            "domain_violations": pd.concat(all_violations,    ignore_index=True)
                                 if all_violations else pd.DataFrame(),
            "duplicate_summary": all_dupes,
        }

    # ── Save report ────────────────────────────────────────────────

    def save_report(self, report: dict, output_dir) -> None:
        """
        Save all profiling outputs to CSV files.
        Accepts a string path or a Path object.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        files_saved = []

        report["column_profiles"].to_csv(
            out / "profile_columns.csv", index=False
        )
        files_saved.append("profile_columns.csv")

        report["completeness"].to_csv(
            out / "profile_completeness.csv", index=False
        )
        files_saved.append("profile_completeness.csv")

        if not report["domain_violations"].empty:
            report["domain_violations"].to_csv(
                out / "profile_violations.csv", index=False
            )
            files_saved.append("profile_violations.csv")

        if not report["outliers"].empty:
            report["outliers"].to_csv(
                out / "profile_outliers.csv", index=False
            )
            files_saved.append("profile_outliers.csv")

        print(f"\n✅ Quality report saved to: {out}")
        for f in files_saved:
            print(f"   → {f}")

        # ── Console summary ────────────────────────────────────────
        print("\n" + "=" * 55)
        print("  DATA QUALITY SUMMARY")
        print("=" * 55)

        if not report["domain_violations"].empty:
            print("\n📋 DOMAIN VIOLATIONS:")
            has_violations = report["domain_violations"][
                report["domain_violations"]["violations"] > 0
            ]
            if has_violations.empty:
                print("  ✅ No violations found")
            else:
                for _, row in has_violations.iterrows():
                    print(
                        f"  [{row['dataset']}] {row['rule']}: "
                        f"{row['violations']:,} violations → {row['action']}"
                    )

        if not report["outliers"].empty:
            print("\n📊 OUTLIERS:")
            for _, row in report["outliers"].iterrows():
                if row["outlier_count"] > 0:
                    print(
                        f"  [{row['dataset']}] {row['column']}: "
                        f"{row['outlier_count']:,} outliers ({row['outlier_pct']}%)"
                        f" | upper fence: {row['upper_fence']}"
                    )

        print("\n🔍 TOP MISSING CRITICAL FIELDS (listings):")
        completeness = report["completeness"]
        if "is_critical" in completeness.columns:
            critical_missing = completeness[
                completeness["is_critical"] & (completeness["null_pct"] > 0)
            ].head(8)
            if critical_missing.empty:
                print("  ✅ All critical fields complete")
            else:
                for _, row in critical_missing.iterrows():
                    print(f"  {row['column']}: {row['null_pct']}% null")

        print("=" * 55)
