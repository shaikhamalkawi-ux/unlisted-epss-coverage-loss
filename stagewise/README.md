# Stagewise Coverage Reproducibility Package

Reproducibility repository for the manuscript:

**Before Ranking Begins: A Multi-Year Study of Coverage Loss in EPSS-Based Vulnerability Triage**

Active scientific baseline: **UNLISTED40 — Official CVE PUBLISHED-State Reconstruction**.

Reproducibility release: **v1.2.0**. The stagewise accounting implementation retains the accepted v1.1.1 fail-closed corrections and locked outputs. This release adds the accepted official-CVE `PUBLISHED`-state reconstruction artifact.

Author: Ghassan Malkawi, Higher Colleges of Technology, United Arab Emirates. Correspondence: gmalkawi@hct.ac.ae.

This repository reproduces the paper's stagewise coverage and miss-location measurements from a compact derived event summary. It does **not** rank vulnerabilities and does **not** claim to predict exploitation.

## Reproduce the reported result

Python 3 standard library only:

```bash
python run_stagewise_coverage.py reported_public_event_input.csv.gz --output-dir reproduced_output
python test_reported_results.py
python test_release_package.py
```

Expected locked counts:

- cohort = 749
- source-observable = 475
- source-unobservable = 274
- Top-100 / Top-500 / Top-1000 capture = 14 / 29 / 41
- Top-1% capture = 69
- Top-1000 misses = 708
- source-stage misses = 274
- observable but not captured = 434

The original uncompressed derived input is 72,318 bytes with SHA-256:

`10a9d3c4b0e53511d017afb567cf45798e63f97228902b6ea703c9b1f7ecd762`

The repository stores the same input as `reported_public_event_input.csv.gz`.

## Official CVE PUBLISHED-state reconstruction

The companion artifact is [`supplements/UNLISTED40_Supplementary_Material_3_CVE_PUBLISHED_State_Reconstruction_v1.2.0.zip`](supplements/UNLISTED40_Supplementary_Material_3_CVE_PUBLISHED_State_Reconstruction_v1.2.0.zip), SHA-256:

`a321400b6100b698ecb0fbeda394fdc22d99422fa7691f3dd157b9a4516fbe78`

Among the 274 EPSS-unobservable outcomes, the accepted partition is 251 with no admitted preceding official CVE `PUBLISHED` state, 0 with an admitted preceding state but no eligible EPSS observation, and 23 unresolved/HOLD. Deterministic bounds are A = 251–274 and B = 0–23. The full-cohort cross-tab retains three EPSS-observable events with unresolved publication-state ordering, so a scalar publication → observability → capture chain is not asserted.

The artifact contains deterministic code, derived ledgers, source manifests, fail-closed tests, and recorded clean-root comparison evidence. Its packaging correction aligns four exact input-hash pins with documented line-ending normalization and removal of machine-specific cache paths; the scientific CSV cells and reconstruction algorithm are unchanged.

The repository test checks the exact artifact hash, ZIP integrity, every internal manifest hash, the locked counts, shared event input, and the packaged-input regression test. It does not re-download or rescan the complete historical source caches. Full reconstruction instructions are in the artifact README and require the pinned cvelistV5 history plus the 174 historical EPSS snapshots identified in its manifests.

The artifact includes the existing project license, the verified [CVE copyright and license notice](THIRD_PARTY_CVE_LICENSE.txt), and third-party source notices. Keep these notices with redistributed copies. All 35 scientific code/input/evidence/output files remain byte-identical to the accepted production-corrected artifact; the release provenance records the documentation and notice additions. Source caches are not included.

## Interpretation boundary

- Outcome = future CISA KEV admission, not exploit onset.
- Source absence = absence from the declared historical EPSS path.
- Selection != remediation or enterprise risk reduction.
- The 38.70% / 61.30% miss split is pipeline-location accounting, not causal attribution.
- The public event summary reproduces the stagewise accounting only; it is not the complete 174-snapshot replication archive.
- Official CVE `PUBLISHED` state is source-bounded and does not establish first availability in vendor advisories or every public source.
- Unresolved publication-state ordering remains HOLD; no exposure, remediation, or new predictive result is introduced.

## Repository contents

- `run_stagewise_coverage.py` — reference implementation
- `test_reported_results.py` — locked-result regression test
- `reported_public_event_input.csv.gz` — compressed derived 749-event public accounting input
- `event_summary_schema.csv/.json` — compact event-summary schema
- `full_decision_record_schema.csv` — fuller decision-record specification
- `enterprise_adapter_template.csv` — empty enterprise extension template
- `reported_output/` — expected outputs
- `REPRODUCTION_STDOUT.json` — expected console result
- `TEST_STATUS.txt` — package test status
- `CITATION.cff` — citation metadata
- `LICENSE.txt` — MIT license
- `THIRD_PARTY_DATA_NOTICE.md` — third-party source notice
- `THIRD_PARTY_CVE_LICENSE.txt` — CVE copyright, license, disclaimer, and authoritative provenance
- `supplements/` — accepted publication-state reconstruction artifact
- `test_release_package.py` — artifact integrity and integration checks
- `release_notes/v1.2.0.md` — release scope and verification boundary

## Fail-closed behavior

The implementation rejects incomplete or internally inconsistent input rather than returning a partial result. Checks cover missing or blank required fields, duplicate identifiers or headers, invalid dates/Booleans/numbers, non-positive horizons or capacities, incomplete Top-1% flags, schedule/date mismatches, decision dates outside the declared pre-outcome horizon, and source-unobservable outcomes carrying rank, score, decision-date, or Top-1% capture values.

## Enterprise-field context

The enterprise template is intentionally empty. Product documentation shows that relevant lifecycle fields can exist in enterprise exports; this establishes field availability, not field validation:

- Tenable: https://docs.tenable.com/vulnerability-management/Content/Explore/findings-columns.htm
- Tenable export keys: https://docs.tenable.com/vulnerability-management/Content/Explore/export-findings-csv-keys.htm
- Rapid7 bulk export: https://docs.rapid7.com/insightvm/bulk-export-api/
- Rapid7 vulnerability workflow: https://docs.rapid7.com/insightvm/working-with-vulnerabilities/
- Qualys vulnerability status: https://docs.qualys.com/en/vm/latest/scans/vulnerability_status.htm

## Verification status

Clean local execution before repository publication:

`REPORTED_RESULTS_TEST: PASS`

The artifact integration test reports `RELEASE_PACKAGE_TEST: PASS`. The GitHub Actions workflow runs both repository tests. Release-specific commit and workflow URLs are recorded on the published release.
