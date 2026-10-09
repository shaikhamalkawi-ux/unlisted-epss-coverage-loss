# Frozen E01 methodology — implementation specification, not manuscript prose

## Inputs and scope

Use x=logit(clip(current EPSS, 1e-8, 1-1e-8)), the one-week logit change d, and a Boolean history-unavailable flag u. Primary u is missing_lag_1w. Version-aware u is missing_lag_1w OR differing current/lag1 provider-version headers. Both matched models receive x, d*=0 when u=1, and u; no additional asymmetric metadata is supplied. Missing and cross-version reasons remain separately recorded in audits. No current-source absence is imputed or assigned low priority. The full original comparator retains its eight saved features and coefficients as a gated historical reference.

## Twelve rules

Rules 1–9: for each L in {low,middle,high} and D in {falling,stable,rising},
IF level is L AND trend is D AND u=0 THEN consequent b_(L,D).
Rules 10–12: for each L, IF level is L AND u=1 THEN consequent b_(L,unavailable).
All rule weights are one. AND is product. Consequents are learned rather than called Low/High/Critical by assumption.

Let mu_L(x) and nu_D(d) be three shoulder/hat linear memberships whose sums are one. Valid-history firing strengths are (1-u) mu_L nu_D; unavailable-history strengths are u mu_L. Thus their 12-way sum is one, up to floating arithmetic, and the implementation normalizes and verifies positivity explicitly.

F_it = sum_r w_itr b_r / sum_r w_itr.

This is a numerical ranking score. Fuzzy membership and b_r are not calibrated exploitation probabilities.

Level knots are inverse-probability-weighted empirical training quantiles q10,q50,q90. The weighted quantile is the first sorted value at which cumulative weight reaches q*sum(weight). Repeated knots cause HOLD. Trend knots are [-a,0,a], where a is the corresponding weighted q90 of absolute available training changes; when q90=0 use the largest positive observed training absolute change, and if none exists HOLD. Shoulders saturate outside outer knots. Prediction cannot change these knots.

## Weighted fitting

For training outcome y_j (future KEV within 30 days) and sampling weight a_j,

L(b) = -[sum_j a_j {y_j log(F_j) + (1-y_j) log(1-F_j)}] / sum_j a_j,

with 1e-8 <= b_r <= 1-1e-8.

Retain all y=1 rows and archived deterministic sampling_uniform<0.005 non-events. Weights are 1 and 200 respectively; they correct sampling, not risk or class importance. With fixed firing weights, F is affine in b and Bernoulli negative log loss is convex, so this is a box-constrained convex optimization problem; no novel theorem is asserted. For numerical conditioning only, optimize u_r=b_r/pi and L/pi, where pi is weighted training prevalence. This invertible positive scaling does not change the minimizer or model. L-BFGS-B uses analytic gradients, max_iter=5000, maxls=50, ftol=1e-12, gtol=1e-8; projected-gradient acceptance is 1e-5 in these scaled coordinates. Initialize b_r=pi. Record effective total and positive rule support; unsupported coefficients are not identified knowledge.

Reduced logistic uses the same x,d*,u, an unweighted training-only StandardScaler (matching the inherited implementation), no penalty, lbfgs, max_iter=1000,tol=1e-4, and the same sample weights. Both versions are fitted independently for each fold. F04 is separately trained through 2025-02-11 and held fixed for its first-v4 test block; it is NOT a reuse of F03 coefficients.

## Data and evaluation gates

Training checks run on archive-hashed derived samples; they are not raw-source reconstruction. Evaluation must first possess all 106 full raw score files at recorded sizes and SHA-256. Exclude prior KEV dateAdded<=decision, label only decision<dateAdded<=decision+30, reconstruct current/1w/4w features, and check exact candidate/event counts. Re-evaluated original EPSS and saved full-logistic AP must match the locked date-level table within absolute 1e-12 before admitting E01 comparisons. Failure leaves four-way interpretation HOLD rather than changing the original numbers.

The 37/13/52 date partitions are fixed. AP handles full exact tie groups; AUC uses average ranks. Top-K reports aggregate minimum/maximum true-positive counts and individual sure/possible event sets under ties. Common-support unique-event coverage uses only outcomes with eligible windows on shared test dates; it is not compared to the broader historic 41/749 count as if the supports were equal.

Bootstrap uses 5-week circular blocks and 5000 paired resamples, with 4/8/13-week sensitivity. Include zero-event dates as missing metrics, not artificial zeroes. Save actual sampled indices under a NEW E01 registry and hash them. A block at least as long as its regime is uninformative. Intervals are exploratory, not multiplicity-controlled confirmation, equivalence or causal effects.

## Bounded references checked 7 October 2026

FIRST historical population format/version-shift documentation: https://www.first.org/epss/data
Official archive: https://github.com/empiricalsec/epss_scores
Sugeno weighted-average/constant-consequent specification: https://www.mathworks.com/help/fuzzy/sugfis.html
L-BFGS-B bound-constrained minimization and convergence options: https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html

These sources ground existing method/data interfaces, not novelty or a positive result of this experiment.
