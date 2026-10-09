#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

root = Path(__file__).resolve().parent
runner_path = root / "run_stagewise_coverage.py"
runner_spec = importlib.util.spec_from_file_location("stagewise_runner", runner_path)
if runner_spec is None or runner_spec.loader is None:
    raise RuntimeError("could not load run_stagewise_coverage.py")
runner = importlib.util.module_from_spec(runner_spec)
runner_spec.loader.exec_module(runner)
compute = runner.compute
load_rows = runner.load_rows

input_path = root / "reported_public_event_input.csv.gz"
if not input_path.exists():
    input_path = root / "reported_public_event_input.csv"


def read_input(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write_input(path: Path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def assert_rejected(temp_root: Path, fields, rows, name: str):
    path = temp_root / f"{name}.csv"
    write_input(path, fields, rows)
    try:
        load_rows(path)
    except ValueError:
        return
    raise AssertionError(f"malformed input was accepted: {name}")


with tempfile.TemporaryDirectory() as temp_dir:
    subprocess.run(
        [sys.executable, str(runner_path), str(input_path), "--output-dir", temp_dir],
        check=True,
        capture_output=True,
        text=True,
    )
    reproduced = json.loads((Path(temp_dir) / "coverage_summary.json").read_text(encoding="utf-8"))

expected_output = json.loads((root / "reported_output" / "coverage_summary.json").read_text(encoding="utf-8"))
assert reproduced == expected_output
assert reproduced["cohort_size"] == 749
assert reproduced["source_observable"] == 475
assert reproduced["source_unobservable"] == 274
expected_captures = {100: 14, 500: 29, 1000: 41}
for policy in reproduced["policies"]:
    assert policy["captured"] == expected_captures[policy["K"]]
assert reproduced["top1pct"]["captured"] == 69
top1000 = next(policy for policy in reproduced["policies"] if policy["K"] == 1000)
assert top1000["total_misses"] == 708
assert top1000["source_unobservable_misses"] == 274
assert top1000["observable_not_captured"] == 434
assert abs(top1000["source_stage_share_of_misses"] - 274 / 708) < 1e-12
assert abs(top1000["post_source_share_of_misses"] - 434 / 708) < 1e-12

fields, rows = read_input(input_path)
observable_index = next(index for index, row in enumerate(rows) if row["source_observable"].strip().lower() == "true")
unobservable_index = next(index for index, row in enumerate(rows) if row["source_observable"].strip().lower() == "false")

with tempfile.TemporaryDirectory() as temp_dir:
    temp_root = Path(temp_dir)

    malformed_fields = [field for field in fields if field != "source_provider"]
    malformed_rows = [{key: value for key, value in row.items() if key != "source_provider"} for row in rows]
    assert_rejected(temp_root, malformed_fields, malformed_rows, "missing_required_column")

    cases = {}

    def add_case(name, index, field, value):
        changed = deepcopy(rows)
        changed[index][field] = value
        cases[name] = changed

    add_case("duplicate_outcome_id", 1, "outcome_id", rows[0]["outcome_id"])
    add_case("invalid_boolean", 0, "source_observable", "maybe")
    add_case("blank_future_outcome_type", 0, "future_outcome_type", "")
    add_case("invalid_future_outcome_date", 0, "future_outcome_date", "not-a-date")
    add_case("blank_source_provider", 0, "source_provider", "")
    add_case("blank_decision_schedule", 0, "decision_schedule", "")
    add_case("zero_horizon", 0, "outcome_horizon_days", "0")
    add_case("zero_rank", observable_index, "best_conservative_rank_within_horizon", "0")
    add_case("observable_without_rank", observable_index, "best_conservative_rank_within_horizon", "")
    add_case("unobservable_with_rank", unobservable_index, "best_conservative_rank_within_horizon", "1")
    add_case("unobservable_with_score", unobservable_index, "best_score_within_horizon", "0.5")
    add_case("unobservable_top1pct_true", unobservable_index, "top1pct_captured", "true")
    add_case("decision_date_after_outcome", observable_index, "best_decision_date_within_horizon", "2099-01-01")
    add_case("weekday_mismatch", observable_index, "decision_schedule", "MONDAY")
    add_case("partial_top1pct", 0, "top1pct_captured", "")

    for name, malformed_rows in cases.items():
        assert_rejected(temp_root, fields, malformed_rows, name)

    assert_rejected(temp_root, fields, [], "empty_input")

try:
    compute(load_rows(input_path), [0])
except ValueError:
    pass
else:
    raise AssertionError("non-positive capacity was accepted")

print("REPORTED_RESULTS_TEST: PASS")
