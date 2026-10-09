#!/usr/bin/env python3
"""Compute stagewise coverage and miss-location accounting from event summaries."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from datetime import date
from pathlib import Path

REQUIRED = [
    "outcome_id",
    "future_outcome_type",
    "future_outcome_date",
    "source_provider",
    "decision_schedule",
    "outcome_horizon_days",
    "source_observable",
    "best_conservative_rank_within_horizon",
]
NONEMPTY_TEXT = ["future_outcome_type", "source_provider", "decision_schedule"]
WEEKDAYS = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def parse_bool(value, field, rownum):
    normalized = (value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"row {rownum}: invalid Boolean in {field}: {value!r}")


def parse_date(value, field, rownum):
    text = (value or "").strip()
    if not text:
        raise ValueError(f"row {rownum}: blank {field}")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"row {rownum}: invalid ISO date in {field}: {value!r}") from exc


def parse_positive_int(value, field, rownum):
    text = (value or "").strip()
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError(f"row {rownum}: invalid integer in {field}: {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"row {rownum}: {field} must be a positive integer")
    return parsed


def parse_optional_number(value, field, rownum):
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"row {rownum}: invalid number in {field}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"row {rownum}: non-finite number in {field}: {value!r}")
    return parsed


def parse_rank(value, rownum):
    parsed = parse_optional_number(value, "best_conservative_rank_within_horizon", rownum)
    if parsed is None:
        return None
    if parsed < 1:
        raise ValueError(f"row {rownum}: invalid rank {value!r}")
    return parsed


def _open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8-sig")
    return path.open(newline="", encoding="utf-8-sig")


def load_rows(path):
    with _open_text(path) as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        if len(fieldnames) != len(set(fieldnames)):
            raise ValueError("input contains duplicate column names")
        missing = [column for column in REQUIRED if column not in fieldnames]
        if missing:
            raise ValueError(f"missing required columns: {missing}")

        rows = []
        seen = set()
        for n, row in enumerate(reader, start=2):
            extra_values = row.get(None) or []
            if any((value or "").strip() for value in extra_values):
                raise ValueError(f"row {n}: more values than header columns")

            oid = (row["outcome_id"] or "").strip()
            if not oid:
                raise ValueError(f"row {n}: blank outcome_id")
            if oid in seen:
                raise ValueError(f"row {n}: duplicate outcome_id {oid}")
            seen.add(oid)

            text_values = {}
            for field in NONEMPTY_TEXT:
                text_values[field] = (row[field] or "").strip()
                if not text_values[field]:
                    raise ValueError(f"row {n}: blank {field}")

            outcome_date = parse_date(row["future_outcome_date"], "future_outcome_date", n)
            horizon = parse_positive_int(row["outcome_horizon_days"], "outcome_horizon_days", n)
            observable = parse_bool(row["source_observable"], "source_observable", n)
            rank = parse_rank(row["best_conservative_rank_within_horizon"], n)
            score = parse_optional_number(row.get("best_score_within_horizon"), "best_score_within_horizon", n)
            decision_date_text = (row.get("best_decision_date_within_horizon") or "").strip()
            decision_date = parse_date(decision_date_text, "best_decision_date_within_horizon", n) if decision_date_text else None

            if observable and rank is None:
                raise ValueError(f"row {n}: source-observable outcome lacks a finite rank")
            if not observable and any(value is not None for value in (rank, score, decision_date)):
                raise ValueError(f"row {n}: source-unobservable outcome carries rank, score, or decision date")
            if rank is None and any(value is not None for value in (score, decision_date)):
                raise ValueError(f"row {n}: score or decision date is present without a finite rank")
            if decision_date is not None:
                lead_days = (outcome_date - decision_date).days
                if not 1 <= lead_days <= horizon:
                    raise ValueError(f"row {n}: decision date is not strictly pre-outcome within the declared horizon")
                schedule = text_values["decision_schedule"].upper()
                if schedule in WEEKDAYS and decision_date.weekday() != WEEKDAYS[schedule]:
                    raise ValueError(f"row {n}: decision date does not match the declared weekday schedule")

            top1 = None
            top1_text = (row.get("top1pct_captured") or "").strip()
            if top1_text:
                top1 = parse_bool(top1_text, "top1pct_captured", n)
                if top1 and not observable:
                    raise ValueError(f"row {n}: source-unobservable outcome cannot be Top-1% captured")

            rows.append({"outcome_id": oid, "observable": observable, "rank": rank, "top1": top1})

    if not rows:
        raise ValueError("input contains no rows")
    top1_presence = [row["top1"] is not None for row in rows]
    if any(top1_presence) and not all(top1_presence):
        raise ValueError("top1pct_captured must be populated for every row or left blank for every row")
    return rows


def compute(rows, capacities):
    if not capacities:
        raise ValueError("at least one capacity is required")
    if len(capacities) != len(set(capacities)):
        raise ValueError("capacities must not contain duplicates")
    if any(isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0 for capacity in capacities):
        raise ValueError("capacities must be positive integers")

    cohort_size = len(rows)
    observable_count = sum(row["observable"] for row in rows)
    unobservable_count = cohort_size - observable_count
    result = {
        "cohort_size": cohort_size,
        "source_observable": observable_count,
        "source_unobservable": unobservable_count,
        "source_observability": observable_count / cohort_size,
        "policies": [],
    }
    for capacity in capacities:
        captured = sum(
            1
            for row in rows
            if row["observable"] and row["rank"] is not None and row["rank"] <= capacity
        )
        observable_not_captured = observable_count - captured
        total_misses = cohort_size - captured
        result["policies"].append(
            {
                "policy": f"Top-{capacity}",
                "K": capacity,
                "captured": captured,
                "total_misses": total_misses,
                "source_unobservable_misses": unobservable_count,
                "observable_not_captured": observable_not_captured,
                "conditional_capture": captured / observable_count if observable_count else None,
                "full_denominator_coverage": captured / cohort_size,
                "source_stage_share_of_misses": unobservable_count / total_misses if total_misses else None,
                "post_source_share_of_misses": observable_not_captured / total_misses if total_misses else None,
            }
        )

    if all(row["top1"] is not None for row in rows):
        captured = sum(row["top1"] for row in rows)
        result["top1pct"] = {
            "captured": captured,
            "conditional_capture": captured / observable_count if observable_count else None,
            "full_denominator_coverage": captured / cohort_size,
        }
    return result


def write_outputs(result, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "coverage_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (outdir / "miss_location_by_capacity.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = list(result["policies"][0].keys())
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["policies"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("coverage_output"))
    parser.add_argument("--capacities", type=int, nargs="+", default=[100, 500, 1000])
    args = parser.parse_args()
    result = compute(load_rows(args.input_csv), args.capacities)
    write_outputs(result, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
