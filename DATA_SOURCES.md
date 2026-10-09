# Data sources and reproducibility boundaries

**FIRST / Empirical Security EPSS** — EPSS daily scores and the official model-version transitions must be handled by historical date, not substituted with today's values. Source: https://www.first.org/epss/data and https://github.com/empiricalsec/epss_scores. Historical EPSS model boundaries in the study: v3 began 2023-03-07; v4 began 2025-03-17; v5 began 2026-06-15 (outside the 102-date Q2 held-out support ending 2026-06-09).

**CISA KEV** — outcome is later catalog admission. Source: https://www.cisa.gov/known-exploited-vulnerabilities-catalog and https://github.com/cisagov/kev-data. Admission is not identical to first observed exploitation.

**Official CVE / cvelistV5** — PUBLISHED-state reconstruction uses pinned official history and does not assert earliest independent disclosure. Source: https://github.com/CVEProject/cvelistV5 and https://www.cve.org/Legal/TermsOfUse.

**Derived records in this repo** are for source-bounded reproducibility. The bundled `stagewise/` event summary was already publicly released in the linked stagewise project; raw EPSS daily candidate panels (106 files for Q2), bulk upstream CVE repositories, raw KEV backups, any enterprise export, private author documents, pre-submission PDFs and other research archives are not republished here. Copyrights and terms for upstream data remain with their providers.

**Interpretation:** a candidate not in EPSS is ineligible for EPSS-based ranking; an EPSS-observable candidate missed at Top-*K* is an allocation outcome. Neither state proves exploit absence, vulnerability irrelevance, successful remediation, nor any causal impact.
