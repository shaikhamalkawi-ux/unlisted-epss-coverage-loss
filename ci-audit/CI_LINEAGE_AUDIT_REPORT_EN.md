# UNLISTED42 — Historical Interval Lineage Audit (2026-10-09)

**Status:** Internal scientific audit only; **NO manuscript change**, historical 18/30 saved-output lineage HOLD remains.

## Verified outcomes

- Original Unlisted14 archive `af8f...`: manifest **908/908 PASS**, ZIP integrity PASS.
- **576/576** saved bootstrap output rows were numerically reconstructed within `1e-12` from frozen derived date-level/budget-level tables, using **saved `bootstrap_stream_seed`** from each archived output record. Both locked-result and current-environment copies (288 each) match. Maximum endpoint discrepancy `2.274e-13`.
- The separate 5-week **Unlisted9 ablation** table was reproduced **18/18** at B=5000 and base seed=260711, from its frozen 102-date ablation input, maximum endpoint discrepancy `9.021e-17`.
- Replaying upstream A5 against archived primary-rate date-level values matched 101/102 at `1e-12`. Sole discrepancy: F03, 2025-01-28, absolute AP difference `9.67659466e-8`. Nothing overwritten.
- This audit newly froze **26** independent MBB index arrays, SHA-256 `18fb321d80b99fa5173f02e11b6ad6020b0594eef14b6b41c44c03a7ecbf1c40`. The new registry explicitly does not have the missing original SHA-256 `3518700e8779bdcf4ce8745ffc0c3aa87f58515cfbb991729ffb5a5bd604226b`.

## Scientific boundary

The legacy `bootstrap_mean_by_date` in `07_evaluate_epss_kev_alignment.py` independently resamples individual decision-date observations (2,000 repetitions); naming those files `date_block_bootstrap` does **not** mean five-week moving-block inference. The separate `compute_ablation_intervals.py` applies a five-week circular moving-block scheme (5,000 repetitions). Therefore the 576/576 archived-date replay and 18/18 ablation replay cannot be counted as recovery of the separately untraced **18/30 later inherited interval endpoints**. Without an exact list-to-output crosswalk and the original draw registry, that separate provenance gap remains unresolved. A post-hoc new registry must never be labelled historical.

An independently rerun block-length sensitivity on A5 confirmed positive within-v3 intervals at 4/5/8/13 weeks and intervals crossing zero in both v4 families (except 13-week transport, classed uninformative because the window contains only 13 dates). This is a newly documented reproducibility probe, not a replacement for the original paper's S12 intervals.

## Next scientific decision

Either recover the original hash-identified draw registry and missing original output-generation records, or in a later separately labelled scientific revision prospectively regenerate **all affected** intervals, preserve the new draw indices, report old/new endpoint differences, and update any inference only if supported. Do not silently change UNLISTED42. Administrative author approvals are a separate hold.
