# Before Ranking Begins: EPSS Coverage Loss in Vulnerability Triage

This repository collects **reproducibility materials** for the research project *VULN-PU / UNLISTED*, currently represented by the working manuscript **UNLISTED42**:

> Before Ranking Begins: A Multi-Year Study of Coverage Loss in EPSS-Based Vulnerability Triage

**Repository status: pre-publication research artifact (2026-10-09).** This is not a final, journal-approved release or a claim of full end-to-end historical interval provenance.

## Scientific question

Which future CISA Known Exploited Vulnerabilities (KEV) could be considered by an EPSS-based prioritization system at a prior decision date, and how many of the eligible items enter a finite Top-*K* review list?

The locked descriptive event accounting currently reports **749** later KEV additions: **475** were observable beforehand in the historical EPSS source, and **274** were not; under the specified 30-day Top-1000 policy, **41** were captured. These are observations about **future KEV admission**, not direct measurements of exploitation onset, remediation, or enterprise risk reduction.

A secondary history-aware comparison evaluates logistic and compact fuzzy scoring across historical EPSS model regimes. It is **not** presented as a new superior classifier; improvements found within EPSS v3 do not establish transfer to v4.

## Contents

- [`stagewise/`](stagewise/) — public, standard-library-only accounting reproducibility code, a derived public event summary, schemas and fixed-output tests. This corresponds to the separately archived Stagewise Coverage Reproducibility Package v1.1.1.
- [`q2b/`](q2b/) — secondary comparator implementation and diagnostic outputs; evaluation requires the exact historical input dates and frozen experiment inputs.
- [`ci-audit/`](ci-audit/) — historical interval provenance and audit scripts, with explicit boundaries on which archived bootstrap outputs have been reproduced.
- [`DATA_SOURCES.md`](DATA_SOURCES.md) — source acquisition, versions and redistribution limits.
- [`RELEASE_STATUS.md`](RELEASE_STATUS.md) — what is verified, what is still on hold, and what is deliberately not published.

## First reproducibility check

From the repository root:

```bash
cd stagewise
python run_stagewise_coverage.py reported_public_event_input.csv.gz --output-dir reproduced_output
python test_reported_results.py
```

This check needs Python 3 standard library only. It reproduces the stagewise descriptive counts from the supplied **derived** example. It is not a substitute for reconstructing the historical EPSS archive and candidate panels.

## Source boundaries and disclosure

The raw EPSS daily archive belongs to its original publisher(s); obtain the exact dated files from [Empirical Security's historical EPSS repository](https://github.com/empiricalsec/epss_scores), described by [FIRST EPSS data](https://www.first.org/epss/data). CISA KEV is available from its official catalog. **No bulk raw EPSS, proprietary enterprise exports, access tokens, internal correspondence, or PREAUTHOR manuscript PDF are included.**

The **historical saved-output lineage for 18 of 30 inherited confidence intervals remains on HOLD**, despite successful separate reproduction of other archived bootstrap tables. New 2026-10-09 audit indices must not be represented as the missing historical indices. See [RELEASE_STATUS.md](RELEASE_STATUS.md).

The `stagewise/` software includes its historical MIT license. Distinct code and derived-data materials may have different rights; nothing here relicenses FIRST, CISA or other third-party source data. No DOI or final manuscript author list is asserted.
