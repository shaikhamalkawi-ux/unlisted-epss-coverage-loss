# Secondary Q2b historical EPSS comparator — code and aggregated outputs

This directory documents a **retrospective exploratory** robustness comparison, not a new vulnerability-risk or exploitation model. It compares a 12-rule zero-order Sugeno scoring rule, a matched reduced-input logistic model, the EPSS baseline, and a saved full logistic reference.

## Public release boundary

This is a **code, frozen-protocol, saved-model, and aggregated-output release**. It is *not* a self-contained end-to-end rerun archive: the original 150 derived trajectory training samples, exact frozen KEV input, and other input-trace files are not in this public repository. They remain part of the internally audited, source-pinned research archive. The 106 official historical EPSS files are excluded from this repository; their names and expected sizes/hashes appear in `inputs/required_test_source_manifest.csv` and must be acquired from the original sources.

Consequently, the available code can be inspected and the kernel unit tests run, but `run_experiment.py`, `evaluate_e02_chunk.py`, and `combine_e02.py` must not be described as successfully rerunnable from this repository alone. Do **not** silently create, impute or replace missing inputs, and do **not** report a new full-evaluation run without passing all source gates.

## Execute the isolated scientific unit tests

In a Python environment with the pinned packages from `requirements.txt`:

```bash
python code/test_fuzzy_core.py
```

The internal evaluation used 102 held-out decision dates with a 106-file exact-source gate. All 102 candidate counts, event counts and EPSS AP values were reproduced; the historical full-logistic AP table replayed on 101/102 dates. The **single predeclared exception** is `F03 / 2025-01-28` and must remain visible.

## Conclusions, properly bounded

Within EPSS v3 the fuzzy rule comparator improved AP relative to EPSS but did **not** establish superiority to the matched reduced logistic model. Positive incremental benefit relative to EPSS was not established in either first-v4 transport or later-v4 adaptation. These are candidate-panel, outcome- and model-version-conditional retrospective observations, not direct exploitation outcomes, prospective validation or empirical human interpretability evidence.

See `E02_SCIENTIFIC_RESULT_EN.md`, `E02_PROTOCOL_AMENDMENT.json`, and aggregated results under `E02_RESULTS_COMPLETE/`. The original training inputs and other withheld material are not available here. Publicizing the code does not confer ownership or a separate license on third-party EPSS/CISA data.
