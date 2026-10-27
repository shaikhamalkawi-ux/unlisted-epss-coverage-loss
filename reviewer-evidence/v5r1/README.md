# UNLISTED — reviewer evidence and independently executed V5 historical holdout
**Research baseline:** UNLISTED56R3R1, *Before Ranking Begins: A Multi-Year Study of Coverage Loss in EPSS-Based Vulnerability Triage*.

**Status (27 October 2026):** The frozen retrospective July–September 2026 holdout was actually executed by GitHub Actions on raw public historical EPSS and CISA KEV files. Both synthetic integrity tests and the real-data job passed. The original manuscript is **unchanged**. No prospective/enterprise efficacy or full raw 2023–2026 archive access is claimed.

## Immutable file checks

| Download in this directory | Size | SHA-256 | Function |
|---|---:|---|---|
| `UNLISTED56R3R1_Reviewer_Bounded_Audit_Kit.zip` | 615,366 bytes | `780e4ab07a1e59c4a73d53e4b8d770be2378c8432fa0431464eb6c5b7f0a204c` | Replays the historical derived 749-CVE/Q1 partitions, R5 RSS bounded sensitivities, 30-day decision observations, and 4 corruption tests |
| `UNLISTED_V5R1_CorrectedHoldout_PUBLIC_SAFE_GITHUB_20261027.zip` | 36,889 bytes | `fe2b6db7744b0a14f228d211b3b377145aa5a6bdcaece27eebe24048dc069ed8` | Locked 15 EPSS + 16 KEV source identities, exact original-source reader, fixed budget warmup, 31 scenario policy replay |
| `UNLISTED_V5R1_HistoricalHoldout_DerivedResults_20261027.zip` | 8,885 bytes | `ab528d983de12b63f52894572ef8edd52342f0754600490602af6045e458e560` | Verified raw-source replay certificate, 15 source SHA-256 records, 31 policy outcomes and 744 weekly work records |

GitHub Actions run: https://github.com/shaikhamalkawi-ux/unlisted-epss-coverage-loss/actions/runs/40535462674 — **synthetic PASS**, **real raw-source PASS**, artifact #12748511259. The original immutable raw-source hashes/commits remain inside the pinned V5R1 ZIP.

## Bounded original paper replay

```bash
unzip UNLISTED56R3R1_Reviewer_Bounded_Audit_Kit.zip -d bounded
cd bounded
python RUN_ALL_REPLAYS.py
```

An independent Python 3.13 replay of these exact ZIP bytes reproduces `749 = 274 + 434 + 41`; `475 = 434 + 41`; official-state timing and per-year partitions; the separately bounded 76-date RSS comparison; and 4/4 intentional corruption rejection checks. These are replays of **archived derived records**, not independent acquisition of the original 174 daily EPSS source objects.

## V5 out-of-period raw-source replay

```bash
unzip UNLISTED_V5R1_CorrectedHoldout_PUBLIC_SAFE_GITHUB_20261027.zip -d v5
cd v5
python -m pip install pandas==2.2.3 requests==2.32.3
python code/check_v5_metadata_preflight.py
python tests/test_v5_gate_synthetic.py
python code/run_v5_pinned_holdout.py --manifest provenance/V5_SOURCE_LOCK.json --output results/v5
```

This downloads and validates 15 original Git-pinned compressed EPSS snapshots (3 warmup and 12 evaluation Tuesdays), 15 as-of CISA KEV JSON snapshots, and the frozen CISA 23 October 2026 outcome JSON. The code enforces exact Git blob SHA checks and refuses to output results if any source check fails.

**Real test results:** Under Top-1000 weekly decisions, the L1 repeat-allowed baseline captured **5** later-KEV CVEs and L4 four-week no-repeat captured **7** (two additional, zero lost). In **30** budget/affordability configurations, L4 captured more in **22**, tied in **8**, and lost in **zero**. This is a *small, retrospective, out-of-original-period result*, not a statistically established universal advantage. Explicit budget ceilings are equal, **actual work spent is not necessarily equal**. Assumed first/repeat work costs are not measured analyst hours.

**Protocol clock:** historical Tuesday **23:59:59 UTC**, a constructed public-source decision time. Git commit metadata supports provenance, not proof of third-party historical feed receipt. CISA KEV inclusion is the measured endpoint, not exploitation onset, remediation or prevented attacks. L4 and its four-week duration were chosen retrospectively from the original study; this test is not prospectively preregistered.

## Audit and access boundary

- This is a **public, bounded reviewer-facing artifact**, accessible on a GitHub branch without disclosing the separate large historical 174-EPSS raw archive, database or other controlled evidence.
- This public repository is linked to an identifiable GitHub account; it is **not** double-blind anonymization.
- Source ZIP, exact public derived results ZIP, and replay scripts are verifiable byte-by-byte here; independent third-party reviewer execution/approval has **not** been obtained.
- **HOLD:** complete manuscript-matched raw-source reviewer access; independent authentication of historical GitHub push/enterprise receipt; prospective operational performance; public DOI for the complete archive.
- The article and its authorless byline have not been changed or submitted.
