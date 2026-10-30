"""Schema drift detection comparing baseline and current schema fingerprints."""

from __future__ import annotations

from typing import List
from datasentinel.core.types import DriftItem, DriftReport, DriftType, SchemaFingerprint


class SchemaDriftDetector:
    """Detects structural and type differences between a baseline and current schema."""

    @classmethod
    def compare(
        cls,
        baseline: SchemaFingerprint,
        current: SchemaFingerprint,
    ) -> DriftReport:
        """Compare two schema fingerprints and report any schema drift."""
        diffs: List[DriftItem] = []

        baseline_cols = baseline.columns
        current_cols = current.columns

        # 1. Detect removed columns (in baseline, missing from current)
        for col_name, base_schema in baseline_cols.items():
            if col_name not in current_cols:
                diffs.append(
                    DriftItem(
                        drift_type=DriftType.REMOVED,
                        column_name=col_name,
                        baseline_value=f"{base_schema.dtype} (nullable={base_schema.nullable})",
                        current_value=None,
                        message=f"Column '{col_name}' was removed from current dataset.",
                    )
                )

        # 2. Detect added columns (in current, missing from baseline)
        for col_name, curr_schema in current_cols.items():
            if col_name not in baseline_cols:
                diffs.append(
                    DriftItem(
                        drift_type=DriftType.ADDED,
                        column_name=col_name,
                        baseline_value=None,
                        current_value=f"{curr_schema.dtype} (nullable={curr_schema.nullable})",
                        message=f"New column '{col_name}' was added to current dataset.",
                    )
                )

        # 3. Detect type changes & nullability changes for common columns
        for col_name in baseline_cols.keys() & current_cols.keys():
            base_schema = baseline_cols[col_name]
            curr_schema = current_cols[col_name]

            # Simplify dtype comparisons (e.g. normalize int64 vs int32 if needed, or exact match)
            if base_schema.dtype != curr_schema.dtype:
                diffs.append(
                    DriftItem(
                        drift_type=DriftType.TYPE_CHANGED,
                        column_name=col_name,
                        baseline_value=base_schema.dtype,
                        current_value=curr_schema.dtype,
                        message=(
                            f"Column '{col_name}' type changed from '{base_schema.dtype}' "
                            f"to '{curr_schema.dtype}'."
                        ),
                    )
                )

            # Nullability change: baseline was strictly non-nullable, but current received nulls
            if not base_schema.nullable and curr_schema.nullable:
                diffs.append(
                    DriftItem(
                        drift_type=DriftType.NULLABILITY_CHANGED,
                        column_name=col_name,
                        baseline_value="not-null",
                        current_value=f"nullable ({curr_schema.null_count} nulls)",
                        message=(
                            f"Column '{col_name}' was strictly non-nullable in baseline "
                            f"but now contains {curr_schema.null_count} null values."
                        ),
                    )
                )

        has_drift = len(diffs) > 0

        summary = (
            f"Schema drift detected: {len(diffs)} difference(s) found against baseline."
            if has_drift
            else "No schema drift detected. Schema matches baseline perfectly."
        )

        return DriftReport(
            baseline_name=baseline.dataset_name,
            current_name=current.dataset_name,
            has_drift=has_drift,
            diffs=diffs,
            summary=summary,
        )
