# Confidence-interval provenance audit — code and reproducibility reports

A separate scientific audit accompanying working manuscript UNLISTED42. Its objective is to distinguish **numerical reproduction of particular archived bootstrap artifacts** from **recovery of historical output-generation provenance**.

Verified in the frozen audit package:

- 576/576 archived date-resampling bootstrap rows were reproducible from saved derived inputs using their saved stream seeds (max endpoint discrepancy 2.274e-13).
- A separate historical 5-week circular moving-block *ablation* table reproduced 18/18 rows (max endpoint discrepancy 9.021e-17).
- An independent new retrospective sensitivity analysis, with newly saved indices, supported the qualitative within-v3 versus v4 interpretation under the tested block lengths.

**Unresolved:** these successes do not recover the original registry for the distinct **18/30 inherited confidence-interval endpoints**. The SHA-256 of that missing registry is `3518700e8779bdcf4ce8745ffc0c3aa87f58515cfbb991729ffb5a5bd604226b`. A newly created bootstrap registry is not a replacement for the historical registry. Results must not be merged across estimands or bootstrap schemes.

The scripts and aggregate replay summaries are published here for inspectability. **Frozen derived matrices and the separately created NPZ registry are not in this GitHub release** pending completion of the public-release/data-rights review. Therefore, the full archived replay commands are not runnable from this repository alone. The internal complete archive is maintained separately. This directory must not be called an end-to-end public replication package.

Software audit files retain the stated MIT notice in `LICENSE_CODE_MIT.txt`; no new license is granted for upstream third-party raw source materials.
