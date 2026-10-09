#!/usr/bin/env python3
"""Offline integrity/integration test for the frozen reconstruction artifact."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
ARTIFACT = ROOT / "supplements/UNLISTED40_Supplementary_Material_3_CVE_PUBLISHED_State_Reconstruction_v1.2.0.zip"
EXPECTED_SHA256 = "a321400b6100b698ecb0fbeda394fdc22d99422fa7691f3dd157b9a4516fbe78"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    require(hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == EXPECTED_SHA256, "reconstruction ZIP hash mismatch")
    require((ROOT / "THIRD_PARTY_CVE_LICENSE.txt").is_file(), "CVE license notice missing")
    require((ROOT / "THIRD_PARTY_DATA_NOTICE.md").is_file(), "third-party data notice missing")
    with ZipFile(ARTIFACT) as archive:
        require(archive.testzip() is None, "ZIP integrity failure")
        files = [item.filename for item in archive.infolist() if not item.is_dir()]
        require(len(files) == len(set(files)), "duplicate ZIP members")
        for name in files:
            relative = PurePosixPath(name)
            require(not relative.is_absolute() and ".." not in relative.parts and ":" not in name and "\\" not in name, "unsafe ZIP member")
        manifest = {}
        for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines():
            if not line.strip():
                continue
            digest, name = line.split(None, 1)
            name = name.strip()
            require(name not in manifest, "duplicate hash manifest entry")
            manifest[name] = digest
        require(set(manifest) == set(files) - {"SHA256SUMS.txt"}, "hash manifest coverage mismatch")
        for name, digest in manifest.items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == digest, "internal hash mismatch: " + name)
        for notice in ("LICENSE.txt", "THIRD_PARTY_CVE_LICENSE.txt", "THIRD_PARTY_DATA_NOTICE.md"):
            # Git checkouts may normalize CRLF/LF; notice text must still match.
            packaged_notice = archive.read(notice).decode("utf-8").replace("\r\n", "\n")
            require(packaged_notice == (ROOT / notice).read_text(encoding="utf-8"), "packaged license/notice differs: " + notice)

        shared_input = archive.read("inputs/reported_public_event_input.csv")
        require(shared_input == gzip.decompress((ROOT / "reported_public_event_input.csv.gz").read_bytes()), "stagewise/reconstruction input mismatch")
        rows = list(csv.DictReader(io.StringIO(shared_input.decode("utf-8-sig"))))
        require(len(rows) == 749 and len({row["outcome_id"] for row in rows}) == 749, "cohort identity mismatch")
        summary = json.loads(archive.read("outputs/reconstruction_summary.json"))
        locked = {
            "cohort": 749,
            "epss_observable": 475,
            "epss_unobservable": 274,
            "top1000_captured": 41,
            "A_no_admitted_published_state_before_eligible_decision": 251,
            "B_published_state_present_but_absent_from_epss": 0,
            "U_unresolved_hold": 23,
        }
        require(all(summary["counts"].get(key) == value for key, value in locked.items()), "locked reconstruction counts mismatch")
        clean = json.loads(archive.read("outputs/clean_root_rerun_comparison.json"))
        require(clean["status"] == "PASS" and clean["files_compared"] == clean["byte_identical_files"] == 8, "recorded clean-root comparison is not PASS")
        fail_closed = json.loads(archive.read("outputs/fail_closed_test_results.json"))
        require(fail_closed["status"] == "PASS" and fail_closed["passed"] == fail_closed["total"] == 20, "recorded fail-closed suite is not PASS")
        with tempfile.TemporaryDirectory(prefix="unlisted40_release_test_") as temporary:
            archive.extractall(temporary)
            result = subprocess.run(
                [sys.executable, "-B", str(Path(temporary) / "code/test_packaged_inputs.py")],
                check=True, capture_output=True, text=True,
            )
            checked = json.loads(result.stdout)
            require(checked["status"] == "PASS" and checked["checks_passed"] == 5, "fresh packaged-input test failed")
    print("RELEASE_PACKAGE_TEST: PASS")


if __name__ == "__main__":
    main()
