# Sale-price estimation for new-construction 2-6 unit buildings and condo units in Chicago (comps / AVM methods review)

Prepared 2026-10-30. Scope: how to estimate the first-sale price of a new 2-6 unit building or condo unit from free public Cook County sale records, how to state a dollar range, and what accuracy target to hold V1 to.

Marking conventions:
- **[verified]**: read in the primary source this session (page fetched or PDF text extracted).
- **[ref]**: a standard citation given from reference knowledge. The bibliographic details are well known, but the full text was not reopened this session (the session's web-fetch budget ran out partway). Check before quoting numbers from it.
- **[local]**: computed this session from the repo's own data (`data/reference/new_construction_sales.csv`, `test_parcels.csv`, `permits_2to6_clean_city.json`). Scripts are in the scratchpad (`ratio.py`, `conf.py`, `svjoin.py`, `elas.py`) and can be ported to `jobs/` or `engine/` tests.

---

## 1. Methods in the literature: hedonic vs repeat-sales vs comp grid vs machine-learning AVMs, for small samples and thin markets

### Takeaway
For small, location-driven samples, the evidence favors (a) a sales-comparison or hedonic model on **log price**, (b) **fine geographic submarkets** (appraiser-style neighborhoods beat statistical clusters), and (c) a **spatial residual correction**. Gradient boosting is usually the most accurate learner once there are thousands of sales, but it is less stable than robust regression. Repeat-sales methods cannot value new construction directly; they are only for the time index. Our current method is a distance-weighted median comp model. It is a reasonable V1 baseline, but it makes no characteristic adjustments, and the IAAO AVM standard says comp models should adjust for attribute differences using quantitatively derived adjustments.

### Cited Findings
**Foundations**
- Rosen (1974) set out the hedonic price model: a good's price is a function of its characteristics, and implicit prices come from regressing price on those characteristics. "Hedonic Prices and Implicit Markets: Product Differentiation in Pure Competition," *Journal of Political Economy* 82(1):34-55. [ref] — [JSTOR](https://www.jstor.org/stable/1830899)
- Bailey, Muth and Nourse (1963) introduced the repeat-sales regression: the log price change between two sales of the same property is regressed on time dummies. *JASA* 58(304):933-942. [ref] — [JSTOR](https://www.jstor.org/stable/2283324). FHFA still uses an unweighted BMN regression for its tract-level indices [verified] — [Contat & Larson, FHFA WP 21-01](https://fhfa.gov/document/wp2101.pdf)
- Case and Shiller (1987, 1989) built the weighted repeat-sales index, which became S&P CoreLogic Case-Shiller. "Prices of single-family homes since 1970," *New England Economic Review* (Sept/Oct 1987); "The Efficiency of the Market for Single-Family Homes," *AER* 79(1):125-137 (1989). [ref; cited in FHFA WP 16-01, verified] — [FHFA WP 16-01 references](https://www.fhfa.gov/document/wp1601.pdf)
- A repeat-sales index needs two sales of the same unit. FHFA's indices drop pairs that both fall within 12 months and pairs with more than ±40% annual appreciation, and an area's index starts only once 25 half-pairs a year are observed (areas with more than 100 repeat sales). [verified] — [Bogin, Doerner & Larson, FHFA WP 16-01](https://www.fhfa.gov/document/wp1601.pdf). Published as *Real Estate Economics* 47(2):365-398 (2019). [verified on FHFA page] — [FHFA WP 16-01 page](https://www.fhfa.gov/research/papers/wp1601)
- Repeat-sales samples assume constant quality. FHFA notes depreciation of up to about 2% a year (Harding, Rosenthal & Sirmans 2007) and renovation ("flip") bias of 1.5% to 20%. [verified] — [FHFA WP 16-01](https://www.fhfa.gov/document/wp1601.pdf)

**Submarkets and spatial dependence (most relevant to our neighborhood fallback)**
- Bourassa, Hoesli & Peng, "Do Housing Submarkets Really Matter?" (Auckland; published in *Journal of Housing Economics* 12(1):12-28, 2003 [ref for journal details]). Results on out-of-sample predictions [verified from the author version]:
  - Citywide hedonic: 35.0% within 10% and 63.3% within 20% (sample 1).
  - Citywide with appraiser "sales group" dummies: 46.0% / 75.0%.
  - Separate sales-group equations: 48.2% / 76.8%.
  - Statistical clusters (all factors): 41.0% / 69.7%.
  - Adding a neighborhood-residual adjustment raises the citywide model to 43.5% / 70.7%, a gain of 7-10 points for broad models and almost nothing for models that already have fine location.
  - The authors conclude that "established neighborhood or other urban boundaries probably define suitable submarkets for mass appraisal purposes." — [UNIGE archive PDF](https://access.archive-ouverte.unige.ch/access/metadata/b023cc99-18b7-4f6b-8013-cbf6ce517016/download)
- Bourassa, Cantoni & Hoesli (2009, PRRES; 12,982 Louisville sales from 1999, 100 random 74/26 splits). Share of predictions within 10% / 20% [verified]:
  - OLS with no location: 36.5% / 63.4%.
  - OLS plus the mean residual of the 10 nearest neighbors: 41.9% / 70.6%.
  - Kriging (geostatistical): 42.3% / 71.1%.
  - 60 submarket dummies plus geostatistical errors: 47.4% / 75.2% (best).
  - Finer submarkets do better, up to the limit set by the number of transactions. — [PRRES PDF](https://www.prres.org/uploads/763/1688/Bourassa_Predicting_House_Prices_With_Spatial.pdf)
- Pace, Barry & Sirmans, "Spatial Statistics and Real Estate," *JREFE* 17(1):5-13 (1998), and Pace & Gilley, "Using the Spatial Configuration of the Data to Improve Estimation," *JREFE* 14(3):333-340 (1997). Both find that modeling spatial autocorrelation in errors (SAR/kriging) cuts prediction error substantially relative to OLS. [ref; exact percentages not re-checked] — [Springer JREFE](https://link.springer.com/journal/11146)

**Machine learning vs linear AVMs**
- Mayer, Bourassa, Hoesli & Scognamiglio (Swiss Finance Institute RP 18-76; *Journal of European Real Estate Research*, 2019) compared OLS, robust regression, mixed-effects, random forest, gradient boosting and neural networks on 123,000+ Swiss single-family sales (2005-2017), with moving or extending windows. Gradient boosting "yields the greatest accuracy" and robust regression "provides the least volatile predictions." The choice of window had only a "modest effect." [verified abstract] — [IDEAS RePEc](https://ideas.repec.org/p/chf/rpseri/rp1876.html); [DOI 10.1108/JERER-08-2018-0035](https://www.doi.org/10.1108/JERER-08-2018-0035)
- Bastos & Paquette (2025), *Journal of Property Research* 42(1):1-19 (8,249 Bay Area sales, 2020-2023, 10-fold CV). Out-of-sample MAPE: linear 26.5%, random forest 19.9%, LightGBM 18.1%. R²: 0.683 / 0.801 / 0.823. [verified] — [WP PDF](https://rem.rc.iseg.ulisboa.pt/wps/pdf/REM_WP_0314_2024.pdf); [IDEAS](https://ideas.repec.org/a/taf/jpropr/v42y2025i1p1-19.html)
- The Cook County Assessor's residential model is LightGBM with about 100 features, roughly 400K sales from the prior 9 years, out-of-time testing on the most recent 10% of sales, and rolling-origin cross-validation. [verified] — [ccao-data/model-res-avm](https://github.com/ccao-data/model-res-avm)

**Comparable-sales models in professional standards**
- IAAO *Standard on Automated Valuation Models* (revised and approved July 2018) [verified] — [IAAO PDF](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf):
  - "When adequate sales data are available, the sales comparison approach is the preferred method of valuing all property."
  - "When the comparable sales have significant attribute differences, the confidence of the adjustments begins to suffer."
  - Comp selection may use "a weighted selection model (e.g., regression coefficients, Minkowski or Euclidian distance metrics)," and selected comps "should be adjusted for attributes that are dissimilar to the subject."
  - "Comparable sales models that are supported by direct market models that use quantitative methods to derive the adjustments are more stable, reliable and statistically supported than simple matched pairs analysis."
  - The standard warns that "excessive stratification" can hurt and that geographic coordinates may be used in place of geographic strata.
- The IAAO AVM standard also requires holdout samples or cross-validation and checking samples for outlier influence. [verified] — [IAAO AVM standard](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf)

**Our method, measured with the same yardsticks [local]**
- I reran the current spec method on the 35-building test set: same unit-count group within 0.75 mi, widening to 1.5 / any-unit 1.5 / 3 mi; at least 6 comps; ±4 years; inverse-distance (1/(0.2+mi)) weighted median per unit; own building excluded.
  - Median ratio 0.983, COD 14.2, PRD 0.997, PRB 0.25.
  - MdAPE 7.8%; PPE10 51%, PPE15 69% (24/35), PPE20 74%.
  - 27 of 35 resolved at 0.75 mi, 7 at 1.5 mi, 1 at 3 mi.
  - This reproduces the calibration doc's 24 of 35 and 8%.
- Leave-one-out over the **whole 2,450-sale pool** (excluding sales within 0.02 mi, so the same building's other units are out) is clearly worse:
  - MdAPE 14.9%.
  - Random 600-sale subsample: condo units at PPE15 45%, COD 20.2, PRB -0.29 (regressive); whole buildings at PPE15 57%, COD 38.9, mean signed error +35% (pulled up by very low recorded building prices).
- The 35 permit-matched test buildings are an easier set than the pool as a whole. The headline 69% probably overstates accuracy on a random new building.

### Inferences
- The literature and IAAO both point to the same next step: keep the comp model (it explains itself and suits Rule 5, "show the numbers"), but add **quantitative adjustments** for size per unit, condo vs whole building, and time. Derive the coefficients from a hedonic regression on the pool, then apply them to each comp before taking the weighted median. That is the "comparable sales model supported by a direct market model" that IAAO calls more reliable.
- With 2,450 sales and roughly 30-43 areas holding 5+ sales, a LightGBM model is feasible as a **check model**, but it is unlikely to beat an adjusted comp model by much on this little data. Mayer et al. note gradient boosting's higher volatility. LightGBM also cannot show "the 6 comps behind this number," which our UI rules require. Keep it as a backtest benchmark, not the displayed estimate.
- Bourassa et al. support our neighborhood-first fallback: Assessor neighborhoods are appraiser-drawn submarkets, which beat statistical clusters. They also support adding a neighborhood residual (spatial) correction when falling back to a wider area.

### Gaps
- I could not open Pace et al. (1997, 1998) or Kok, Koponen & Martínez-Barbosa (2017, "Big Data in Real Estate? From Manual Appraisal to Automated Valuation," *Journal of Portfolio Management* 43(6)) [ref], so no error figures from them are given.
- I found no peer-reviewed study that benchmarks AVMs specifically on 2-6 unit new construction.

---

## 2. Accuracy metrics and thresholds; is "within 15% on 70%" right for new construction?

### Takeaway
There are two families of metrics, and they answer different questions.
- **Ratio-study metrics** (IAAO: median ratio, COD, PRD, PRB) measure level, uniformity and vertical equity across a group.
- **AVM point-accuracy metrics** (PPE10/15/20, MdAPE, FSD) measure how close a single estimate lands.

The 2024 federal AVM rule sets no numeric thresholds. Our test-set result (PPE15 69%, MdAPE 8%, COD 14) is in line with published hedonic models on full markets. On the whole pool, though, the method is at about PPE15 50% and MdAPE 15%. A target of 70% within 15% is reasonable to report, but it needs a confidence interval (24/35 has a 95% CI of about 52% to 81%) and a second test set that is not hand-picked.

### Cited Findings
**IAAO ratio-study standards** [verified] — [IAAO Standard on Ratio Studies 2013 (Georgia DOR mirror)](https://www.audits2.ga.gov/wp-content/uploads/2024/08/Standard_on_Ratio_Studies.pdf); same table in [IAAO AVM standard, Table 2](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf)
- COD ranges by property type:
  - Single-family including condos, newer or homogeneous areas: 5.0-10.0.
  - Single-family, older or heterogeneous areas: 5.0-15.0.
  - "Other residential: rural, seasonal, recreational, manufactured housing, 2-4-unit family housing": 5.0-20.0.
  - Income-producing, smaller samples: 5.0-20.0.
  - CODs below 5.0 "may indicate sales chasing or non-representative samples."
- Median ratio (level): 0.90-1.10. The IAAO AVM standard counts this as met "if a 90% two-tailed confidence interval around the median sales ratio overlaps the range of 90% to 110%."
- PRD: 0.98-1.03.
- PRB should generally fall between -0.05 and 0.05. A 95% CI entirely outside ±0.10 indicates "very serious vertical inequity." Negative PRB means regressive; positive means progressive.
- Sample size: "A ratio study sample with fewer than five sales tends to have exceptionally poor reliability." Sales may span up to 5 years if adjusted for time.
- The IAAO AVM standard recommends COD over COV because COD is less sensitive to outliers. It also notes the median ratio and median percent error resist outliers, and that ratio statistics "do not specify the accuracy of individual property estimates."
- IAAO on confidence scores: vendor methods "have not been standardized," and the standard "takes no position on the validity or usefulness" of them. [verified] — [IAAO AVM standard](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf)

**Cook County's own Chicago results (2024 reassessment, 2023 sales vs certified values; the township-to-number match comes from flattened PDF text, so re-check before quoting)** [verified with that caveat] — [CCAO 2024 Chicago Annual Report](https://prodassets.cookcountyassessoril.gov/s3fs-public/reports/cookCountyAssessor_annualReport_chicago-2024_v2_export-forWeb_20251020.pdf)

| Township | Sales | Median ratio | COD | PRD |
|---|---|---|---|---|
| Hyde Park | 1,782 | 0.95 | 33.6 | 1.13 |
| Jefferson | 2,703 | 0.96 | 22.2 | 1.07 |
| Lake | 3,930 | 0.95 | 18.5 | 1.09 |
| Lake View | 530 | 0.98 | 11.4 | 1.02 |
| West Chicago | 995 | 0.98 | 9.2 | 1.02 |

The page reports 10,527 sales in total. Even the county's 400K-sale LightGBM model misses the IAAO COD bands in several South and West Side townships. Our area (Humboldt Park, Hermosa, North Lawndale) is in the harder parts of the city.

**Industry AVM metrics**
- Freddie Mac (Douglas Gordon, "Metrics Matter," 2005) [verified] — [Freddie Mac PDF](https://my.sf.freddiemac.com/docs/pdf/fact-sheets/dougwhitepaper_metricsmatter.pdf):
  - FSD is "an AVM value's expected (forecasted) proportional standard deviation around actual subsequent sales price."
  - FSD 0.10 means about 68% of sales fall within ±10%. ±1.28 FSD gives about 80%, and ±1.65 FSD about 90%.
  - Home Value Explorer confidence bands: High = FSD ≤13%, Medium = 13-20%, Low = >20%.
  - Calibration test: at least 68% of "High" estimates must fall within ±13% on fresh out-of-sample sales.
- Clear Capital defines PPE10 as the share of estimates within 10% of benchmark and calls it a "standard industry measure." MdAE is the most common consumer-AVM metric and "tends to make an AVM look more accurate than it is." There is no standard FSD method across vendors. [verified] — [Clear Capital glossary](https://www.clearcapital.com/blog-avm-testing-glossary/)
- HouseCanary lists MdAPE, hit rate, mean error and "accuracy rate" (share within X%) and advertises a "2.7% median error" without naming the metric. Vendor figures like this are marketing and are mostly measured on homes with listing data. [verified] — [HouseCanary](https://www.housecanary.com/blog/real-estate-avm-accuracy)

**2024 interagency AVM quality-control rule** [verified] — [Federal Register 89 FR 64538, 2024-08-07](https://www.federalregister.gov/documents/2024/08/07/2024-16197/quality-control-standards-for-automated-valuation-models); [FHFA page](https://www.fhfa.gov/regulation/federal-register/final-rule/quality-control-standards-for-automated-valuation-models)
- Effective October 1, 2025.
- It applies to mortgage originators and secondary-market issuers using AVMs for credit decisions or securitization on a consumer's principal dwelling. It does **not** apply to AVM developers or vendors directly.
- It sets five factors: "high level of confidence," "protect against the manipulation of data," "avoid conflicts of interest," "random sample testing and reviews," and nondiscrimination.
- It sets **no numeric accuracy thresholds**; the agencies chose a principles-based approach.

**Benchmarks from the literature** [verified, see section 1]
- Hedonic models with good location controls reach about 46-48% within 10% and 75-77% within 20% (Auckland; Louisville best case 47.4% / 75.2%).
- LightGBM on the Bay Area: MAPE 18%.

**Our numbers [local]**
- Test set (n = 35):
  - PPE15 69%. The Wilson 95% CI is 52%-81%; the bootstrap CI is 54%-83%.
  - COD 14.2, bootstrap 95% CI 9.4-20.0.
  - PRB 0.25, CI -0.05 to 0.55. A positive PRB means estimates run high relative to sale price as value rises; the CI is wide.
- Pool leave-one-out (n = 2,450): MdAPE 14.9%.

### Inferences
- **Is 70% within 15% reasonable?** Yes as a target. It is roughly Freddie Mac's "Medium" confidence (FSD 13-20%) and in line with the best hedonic results in the literature (about 75% within 20% implies about 60-65% within 15%). The current 69% is statistically indistinguishable from 70%, and also from 55%. A target on 35 buildings cannot separate methods that differ by less than about 15 points.
- **Run a ratio study, not just a hit rate.** COD and PRB catch problems the hit rate hides. On the pool, condo-unit estimates are regressive (PRB -0.29): big or expensive units are underestimated and small ones overestimated, which is what a median that ignores size does. IAAO's 2-4 unit COD band (5-20) is the closest published yardstick for whole buildings; condos fall under the 5-15 single-family band.
- **AVM performance on new construction specifically** is weak in every source I found. New homes have no prior sale, often no listing photos, and sometimes no Assessor characteristics until a later year. Vendors do not publish new-construction splits. That is a reason to hold the range wider and to say so on screen.

### Gaps
- I found no published PPE10/MdAPE figures broken out for new construction from any vendor, FHFA, or the CCAO. This is unanswered.
- The CCAO publishes model performance per township and class in its Athena `performance` table (listed in the res-avm README) [verified that the table exists], but I did not find a public file with 2-6 unit class 211 or condo results for Chicago. The 2024 report's table looks single-family only.
- Zillow's published Zestimate accuracy (on- and off-market median error) could not be fetched (403). It is also off-limits for display under project rules.

---

## 3. Cook County Assessor (CCAO) models: features, sale filters, time handling, and what we can reuse

### Takeaway
The CCAO's public **training-data parquet files include the sales-validation flags** (`sv_is_outlier`, `sv_outlier_reason1-3`). The Socrata sales dataset `wvhk-k5uv` does **not**. The flags join to our pool on PIN plus sale date. In the 2025 and 2026 runs they cover 1,938 of our 2,450 comps and flag only 10 (9 "High price", 1 "Low price"). So the flags are a cheap extra filter, but they will not catch the low-price, before-completion sales that hurt us; our own 50%-of-median rule is still needed. The CCAO's certified values (`uzyt-m557`) can serve as an independent check value, but they lag new construction.

### Cited Findings
**Residential model (single- and multi-family, including class 211 and 212 apartments)** [verified] — [ccao-data/model-res-avm README](https://github.com/ccao-data/model-res-avm)
- LightGBM; about 100 features; sales from the 9 years before the assessment date (about 400K rows).
- `char_apts` (1-6) is a feature for classes 211 and 212. Other features: `char_yrblt`, building sq ft, location, ACS, proximity; `prox_nearest_new_construction_dist_ft` was added in 2025.
- Time is handled with sale-date features (`time_sale_day`, year, quarter, month, `time_sale_post_covid`). There is no separate price index; for assessment, every property's sale date is set to the lien date.
- Exclusions:
  - Sales under $10K, multi-PIN and multi-building sales.
  - Quit claim, executor and beneficial-interest deeds (they keep warranty, trustee and "Other").
  - Back-to-back same-price sales.
  - Related-party, corporate, REO, bank, government and foreclosure sales.
  - Price outliers flagged by the sales-validation model. Analyst decisions override the algorithm as of 2026.
- Testing is out-of-time (the most recent 10% of sales as test) with rolling-origin CV. The evaluation reports RMSE, MAE, MAPE, COD, PRD, PRB and MKI by geography and class. Outputs go to Athena tables including `performance`, `test_card` and `comp`; the `comp` table holds comparables computed from leaf-node assignments.

**Condo model** [verified] — [ccao-data/model-condo-avm](https://github.com/ccao-data/model-condo-avm)
- Separate model since the 2021 assessment year. Unit value = percent of ownership × building value.
- The key feature is a leave-one-out, time-weighted **rolling mean sale price of other units in the same building (PIN10)** over the prior 5 years. Time weights follow a logistic curve centered 3 years back. Outlier and non-livable unit sales are excluded.
- `meta_pin10_bldg_roll_pct_sold` gives the share of the building's units sold in the past 5 years.
- For buildings with no recent sales, the building mean is imputed from nearby buildings with similar unit counts and age.
- Multi-PIN unit-plus-parking sales are split by ownership share (example: $100,000 for a 4% unit plus 1% parking gives the unit $80,000).

**Sales-validation model** [verified] — [ccao-data/model-sales-val](https://github.com/ccao-data/model-sales-val)
- Groups sales by geography × property type × rolling time window. Within each group it computes the mean and SD of log price and log price per sq ft, and flags sales beyond a set number of SDs. The thresholds, `min_group_thresh` and `rolling_window`, are parameters in the `parameter` table; values were not published in the README.
- Only price-based reasons set `sv_is_outlier`. Informational reasons: PTAX-203 flags, short-term owner, family sale (matching last names), non-person sale, isolation-forest anomaly, home flip.
- Residential classes covered: 202-212, 218, 219, 234, 278, 295, excluding multi-card sales. Condo classes: 297, 299, 399, excluding parking and common areas.
- Common exclusions: duplicate price within 365 days, under $10K, multi-PIN.

**What is public where [local, verified by query on 2026-10-30]**
- Socrata `wvhk-k5uv` (Assessor - Parcel Sales) columns: pin, year, township_code, nbhd, class, sale_date, is_mydec_date, sale_price, doc_no, deed_type, mydec_deed_type, seller_name, is_multisale, num_parcels_sale, buyer_name, sale_type, `sale_filter_same_sale_within_365`, `sale_filter_less_than_10k`, `sale_filter_deed_type`, row_id.
  - Querying `sv_is_outlier` returns "No such column."
  - The dataset description says it "likely include[s] non-arms-length transactions" and that sales post "on a lag, with many records not populating until months after their official recording date." — [Socrata metadata](https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json)
- Public S3 parquet files are linked from the res-avm README:
  - `s3://ccao-data-public-us-east-1/models/inputs/res/2025/training_data.parquet`: 413,289 rows, sales 2016-01-01 to 2024-12-27.
  - `.../condo/2025/training_data.parquet`: 230,335 rows, same dates.
  - `.../res/2026/run_id=2026-07-30-ecstatic-carly/training_data.parquet`: 405,195 rows, 2017-01-01 to 2025-12-31.
  - All three include `sv_is_outlier`, `sv_outlier_reason1-3`, `meta_sale_document_num`, `char_yrblt`, `char_apts`, and the mailed, certified and board values. Anonymous read works. The 2026 res file without a run_id returns 403.
- Join to our pool on PIN plus sale date:
  - Condo units: 1,768 clean, 3 flagged, 396 not present (mostly 2025-2026 sales after the 2025 condo file's cutoff).
  - Whole buildings: 160 clean, 7 flagged, 116 not present (49 are 2026 sales; 67 fall inside the window but were excluded by CCAO filters, likely multi-card or deed/party exclusions).
  - All 9 "High price" flags are 2018-2021 sales in Near West Side, Logan Square, Lake View, North Lawndale and Near North; the one "Low price" flag is North Center in 2025.
- `uzyt-m557` (Assessed Values) gives mailed, certified and board building/land/total by PIN and year. For class 2, market value ≈ assessed value × 10, since Cook County residential is assessed at 10%. [ref for the 10% level: Cook County classification ordinance]

### Inferences
- **Reuse the flags.** Load `sv_is_outlier` from the newest public parquet each time the CCAO publishes a run, and join on `doc_no = meta_sale_document_num`, or on PIN plus date. Drop flagged sales and record the run_id as the source (Rule 2). Expect few drops (about 0.5% of our pool). That is still a defensible, citable filter that matches the county's own.
- **Keep our own pre-completion filter.** The CCAO's SD-based flags are computed against all housing in a group, not against new construction, so a new building selling at a "normal" existing-stock price is not flagged. Our pool leave-one-out shows a heavy low tail for whole buildings: the 10th-percentile ratio of sale to estimate is 0.44. The calibration doc's "below 50% of the comp median" rule targets exactly those sales.
- **Assessor values as a check, not an input.** Certified values for new construction often reflect partial or occupancy assessments in the first year, so a large gap between our estimate and AV × 10 should raise a "check" flag, not change the estimate. The CCAO's `comp` table (leaf-node comps) is internal-only (Athena), so it is not a free public input.
- **Borrow the condo design.** The CCAO's same-building rolling mean is the strongest single condo feature. For a new condo building with some units already sold, those sales should dominate the estimate for the remaining units. Our current method already gets this implicitly through the 0.75 mi IDW and same-location comps.

### Gaps
- The CCAO's numeric SD thresholds, minimum group size and rolling window were not in the README; they are in the Athena `parameter` table, which I did not access.
- I found no public CCAO ratio-study breakdown for class 211 or condos in Chicago townships.
- I did not test whether `uzyt-m557` values for 2014+ new buildings track their first sale prices. A quick backtest would settle it.

---

## 4. Time adjustment for 2014-2026 comps

### Takeaway
Use a **repeat-sales or hedonic index at the smallest geography with enough sales**: FHFA tract, then ZIP5, then the Chicago CBSA. Apply it to each comp from its sale date to today, and cap how far back a comp can go. Do **not** use the median price per unit of our own pool by year: it mixes in changes in what got built. On the test set it made accuracy worse (MdAPE 7.8% → 10.6%).

### Cited Findings
- FHFA tract-level indices: 63,122 tract indices (2010 tracts) from 1989 to 2021 across 581 CBSAs, built from 63M+ same-unit purchase pairs (Fannie Mae, Freddie Mac, FHA and CoreLogic deed records), unweighted BMN regression. [verified] — [Contat & Larson, FHFA WP 21-01](https://fhfa.gov/document/wp2101.pdf)
  - Low-count tracts are merged with their nearest neighbor into "supertracts" until each has **40 half-pairs per year** over a two-year window; 25 and 100 gave similar results.
  - Pair filters: same 12 months, |CAGR| > 30%, or cumulative change above 10× or below 25%.
  - Sample weighting matters: sample- vs value-weighted city indices differed by 0.2-0.6 percentage points a year.
- FHFA annual indices for ZIP5 and ZIP3 come from the "all-transactions" sample of Fannie/Freddie single-family conventional purchase and refinance loans. An area's index starts once 25 half-pairs a year are seen. [verified] — [FHFA WP 16-01](https://www.fhfa.gov/document/wp1601.pdf); data at [FHFA HPI datasets](https://www.fhfa.gov/data/hpi/datasets) (already cited in `feasibility_defaults.json`)
- IAAO AVM standard on time trends: a trend "can be used to adjust values to any point within the sales period," and extrapolating "beyond the sales period ... should be done with caution and grows increasingly unreliable." Median-per-period trends do "not account for the myriad of other factors that affect sales prices." Sales-ratio trend analysis "can isolate time trends better than the value per-unit method." [verified] — [IAAO AVM standard, Appendix](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf)
- IAAO ratio standard: sales up to 5 years old are acceptable "if prices are adjusted for time." [verified] — [IAAO Ratio Studies](https://www.audits2.ga.gov/wp-content/uploads/2024/08/Standard_on_Ratio_Studies.pdf)
- S&P CoreLogic Case-Shiller publishes a Chicago index and a separate Chicago condo index. Repeat-sales construction leaves out first sales of new homes because they have no prior pair. [ref, methodology not reopened this session] — [S&P Case-Shiller methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-corelogic-cs-home-price-indices.pdf). Display rights for S&P data are not free; FHFA is public domain.
- Our pool's citywide median price per unit by year [local]: 2017 $599K, 2018 $610K, 2019 $595K, 2020 $599K, 2021 $675K, 2022 $710K, 2023 $680K, 2024 $730K, 2025 $750K, 2026 (partial) $705K. These swings reflect where and what was built, not only price change.
- Pool sales by year [local]: 2015 4, 2016 15, 2017 90, 2018 121, 2019 173, 2020 263, 2021 384, 2022 352, 2023 278, 2024 274, 2025 321, 2026 175.

### Inferences
- **Recommended:** FHFA annual tract index → ZIP5 → Chicago-Naperville-Evanston CBSA quarterly (the cascade already in `feasibility_defaults.json`), at a fixed point. Show "adjusted +X% for time (FHFA tract 17031xxxxxx, 2021 → 2026)" on each comp row. Because FHFA tract data is annual, interpolate within the year and carry the last annual change forward for the current year, with a note.
- FHFA indices are single-family-loan based and mostly track existing homes. For condo comps, a hedonic time effect estimated within our own pool is a sensible cross-check: log(price per unit) regressed on year-quarter dummies plus neighborhood fixed effects plus log sq ft per unit plus condo flag. That is the "hedonic index" alternative, and with roughly 2,450 sales it gives a citywide, composition-controlled new-construction trend.
- The 4-year window is within IAAO's 5-year guidance. Adjusted comps up to 5 years old are acceptable; beyond that, widen the margin.

### Gaps
- I did not confirm whether FHFA's tract and ZIP indices include condos or 2-4 unit buildings. Fannie/Freddie "single-family" usually means 1-4 units, but the working paper did not say. Check the FHFA local HPI FAQ (`faqs_local_hpis-2025.pdf`, linked from the WP 16-01 page).
- No published index tracks Chicago new-construction prices specifically.

---

## 5. New-construction premium and the pre-sale or under-construction sale problem

### Takeaway
New homes sell for more than older homes, but once size, location and date are held fixed the gap is small and it varies with the market cycle. That is why comps should be **new construction only** (our pool already is), not adjusted existing stock. The bigger practical risk is sales recorded before the building was finished, or with a stale contract price, which show up as very low or very old prices. Filter them, and carry a lag variable.

### Cited Findings
- Coulson, Morris & Neill, "Are New Homes Special?" (working paper, July 2015; published in *Real Estate Economics*, 2019 [ref for journal details]). Data: 785,022 arm's-length Clark County, NV sales, 1994-2014. [verified] — [Brookings PDF](https://www.brookings.edu/wp-content/uploads/2016/06/Are-new-homes-special.pdf)
  - Raw new-vs-used gap: 17%-52%.
  - Conditional on characteristics, the new-home coefficient is about -1% to 0%, except developer inventory sales at about +8%.
  - The premium was negative before 2007 (about -8.5 points for non-developer, -6 for developer) and positive after (about +15 and +20).
  - When annual new-home sales exceeded about 5,000, the premium "largely disappeared."
  - Depreciation is about 1% a year for young houses.
  - They cite Kahn & Kok (2014): age-0 homes sell at about 20-22% and age 1-2 at about 24-27% above 50+-year-old homes.
- FHFA notes depreciation of up to about 2% a year in repeat-sales samples (Harding, Rosenthal & Sirmans 2007). [verified] — [FHFA WP 16-01](https://www.fhfa.gov/document/wp1601.pdf)
- The CCAO res model's 2025 feature `prox_nearest_new_construction_dist_ft` shows the county finds proximity to new construction predictive of nearby prices. [verified] — [model-res-avm](https://github.com/ccao-data/model-res-avm)
- Our own evidence [local; calibration doc]:
  - 3035 N Sheffield sold at $216/sq ft in Lake View, "likely sold before completion," and was removed.
  - In the pool, whole-building sales have a heavy low tail: leave-one-out 10th-percentile ratio 0.44 at 0.75 mi (n = 221), mean signed error +35% (n = 60 subsample).
  - Example row: a 2014 Logan Square 3-flat at $200,000 ($66,667/unit) on 2015-06-15.

### Inferences
- **Pre-sale problem, practical rules:**
  1. A building's first sale is a likely pre-completion or land-plus-shell sale when it records before or within a few months of the permit's final inspection or the Assessor's first full-value year. Use the permit issue date and `months_to_sale` (test-set column), plus the Assessor's `char_yrblt`. Keep the "< 50% of comp median per sq ft" rule as the backstop.
  2. Deeds record at closing, but condo prices are often set at contract 6-18 months earlier. The time adjustment should use the recording date (the only public date). A known pre-sale-heavy building (many unit deeds recorded within weeks) can be noted. Treat this as a source of uncertainty, not something to correct.
  3. Developer-to-buyer sales show the developer LLC as seller (`seller_name` in `wvhk-k5uv`). An "LLC seller" flag is a good marker that a sale is a true first developer sale. CCAO's "non-person sale" heuristic uses similar keyword logic.
- Coulson et al.'s cycle result (the premium flips sign with the market) supports using **recent new-construction comps only**, with time adjustment, rather than an existing-stock comp plus a fixed "new" premium.

### Gaps
- I found no Chicago-specific estimate of the new-construction premium.
- I found no paper that measures the contract-to-recording lag for Chicago condo pre-sales.

---

## 6. Thin data: shrinkage, hierarchical models, spatial smoothing, and how to state the dollar range

### Takeaway
Our fallback (Assessor neighborhood → community area → neighboring areas) is a hard-switch version of **hierarchical shrinkage**. Replace the hard switch with an empirical-Bayes blend: weight the local median by n/(n+k) and the parent level by k/(n+k). Calibrate the dollar range with **split-conformal or leave-one-out residual quantiles**, stratified by search tier and kind. Do not use the raw 25th-75th percentile of comps, which is a 50% band and is not calibrated as a prediction interval.

### Cited Findings
- Bastos & Paquette (2025) [verified] — [WP PDF](https://rem.rc.iseg.ulisboa.pt/wps/pdf/REM_WP_0314_2024.pdf)
  - Raw LightGBM quantile regression **undercovers**: nominal 70/80/90% gave empirical 56/66/78%.
  - **Conformal quantile regression** (Romano et al. 2019) hit nominal coverage exactly: 70/80/90%, with median relative widths 0.35 / 0.45 / 0.62 of price.
  - Larger and older properties, low- and high-income areas, and properties on the market under a year were hardest to value.
  - The authors: "Uncertainty quantification associated with real estate appraisal has largely been overlooked in the literature."
- Split conformal: fit on one part of the data, compute absolute residuals on a calibration set, and take their (1-α)(n+1)/n quantile as the interval half-width. This gives finite-sample marginal coverage under exchangeability; conditional coverage across all x "is rarely achieved." [verified, Bastos & Paquette section 2] — [WP PDF](https://rem.rc.iseg.ulisboa.pt/wps/pdf/REM_WP_0314_2024.pdf)
- Freddie Mac's practice is the same idea in older form: an FSD per estimate, validated by checking that 68% of sales fall within ±1 FSD on fresh data. [verified] — [Freddie Mac](https://my.sf.freddiemac.com/docs/pdf/fact-sheets/dougwhitepaper_metricsmatter.pdf)
- FHFA's supertract method merges a thin tract with its nearest neighbor until 40 half-pairs a year are reached. This is a working example of geographic fallback with a minimum-count rule. [verified] — [FHFA WP 21-01](https://fhfa.gov/document/wp2101.pdf)
- Bourassa et al.: adding the neighborhood mean residual to a broader model recovers 7-10 points of within-10/20% accuracy, which is the spatial-smoothing step. [verified] — [UNIGE PDF](https://access.archive-ouverte.unige.ch/access/metadata/b023cc99-18b7-4f6b-8013-cbf6ce517016/download)
- Empirical Bayes and multilevel shrinkage for small areas: Fay & Herriot (1979, *JASA* 74(366):269-277) is the small-area estimator used by the Census SAIPE program. Gelman & Hill (2007), *Data Analysis Using Regression and Multilevel/Hierarchical Models*, covers partial pooling with group size, the n/(n + σ²/τ²) weight. [ref] — [JSTOR Fay-Herriot](https://www.jstor.org/stable/2286322)
- The CCAO condo model imputes a missing building mean from nearby similar buildings, which is a nearest-neighbor shrinkage. [verified] — [model-condo-avm](https://github.com/ccao-data/model-condo-avm)

**Our calibration numbers [local, full-pool leave-one-out, n = 2,450, excluding comps within 0.02 mi]**

| Search tier, kind | n | MdAPE | 80% band (sale ÷ estimate, 10th-90th pct) |
|---|---|---|---|
| 0.75 mi, whole building | 221 | 10.6% | 0.44 to 1.15 |
| 0.75 mi, condo unit | 2,091 | 15.2% | 0.76 to 1.39 |
| 1.5 mi, whole building | 55 | 18.9% | 0.35 to 1.07 |
| 1.5 mi, condo unit | 66 | 16.7% | 0.76 to 1.50 |
| 3 mi, building / condo | 6 / 9 | 15-20% | too few to calibrate |

- Pooled across tiers, the leave-one-out 80% band is ×0.74 to ×1.36 and the 50% band ×0.86 to ×1.16.
- Applied to the 35 test buildings, the pooled 80% band covers 32 of 35 (91%) and the 50% band 24 of 35 (69%). The test set is easier than the pool.
- The current 25th-75th percentile comp range covers 17 of 35 (49%) of test sales. It is behaving like a 50% interval, which is what a P25-P75 range is.

**Size adjustment coefficient [local]**
- Within neighborhood × sale-year groups (3+ sales), the elasticity of price per unit to sq ft per unit is **0.50 for condo units** (n = 1,074) and **0.37 for whole buildings** (n = 145). A unit 10% larger than the comp sells for about 5% more (condo) or about 3.7% more (building).
- Caveat: the median condo `char_unit_sf` in the pool is 1,950 sq ft, which looks high for 2-6 unit condos. The Assessor's unit sq ft may include shares of common area. Verify before relying on it.

### Inferences
**Method a small Python team can build** (pandas, numpy, statsmodels; no LightGBM required):
1. **Adjust each comp** to the subject: time (FHFA index, section 4) × size ((subject sf/unit ÷ comp sf/unit)^β, with β = 0.50 condo and 0.37 building, re-estimated nightly) × kind (condo unit vs whole building per-unit ratio, estimated from the pool within neighborhood). Store β and its standard error with a source and date (Rule 1).
2. **Point estimate**: inverse-distance weighted median of adjusted comps, as now.
3. **Shrinkage instead of hard fallback**: estimate = w·(neighborhood adjusted median) + (1-w)·(community-area adjusted median), with w = n/(n+k). Fit k by minimizing leave-one-out error; k ≈ 5-10 is a typical start. Apply the same blend one level up for community area vs neighboring areas. Show the count n at each level (Rule 2) and the weight.
4. **Dollar range**: split-conformal on log residuals, Mondrian by (search tier × kind × n-bucket). Store the 10th and 90th percentile residual multipliers from the nightly leave-one-out run, and show "80% of past estimates like this landed between $A and $B" with the calibration count. That is exactly the "dollar margin with basis" Rules 2-3 ask for, and it widens itself when data is thin.
5. **Optional check model**: a LightGBM or statsmodels hedonic on the same pool. Report the gap between it and the comp estimate as a flag, not as the displayed value.

### Gaps
- I did not fit the empirical-Bayes k or test steps 1-3 end to end; only the pieces were measured (size elasticity, leave-one-out bands).
- I found no paper applying conformal intervals to thin new-construction samples specifically. Bastos & Paquette used 8,249 Bay Area sales.

---

## 7. Modeled quantity: price per unit vs price per sq ft vs whole-building price

### Takeaway
Model **log price per unit** and adjust for size per unit when the subject's size is known. Price per sq ft alone is worse when the subject size is a default guess (49% vs 65% within 15% in the calibration run). Whole-building price is the same as per unit × units for buildings, but it cannot use the 2,167 condo-unit sales, which are 88% of the pool.

### Cited Findings
- Calibration run, 2026-10-29, on 37 test buildings [local, from `docs/calibration-2026-10-29.md`]:
  - Weighted median per unit: 65% within 15%, median error 12%.
  - $/sq ft × default unit size: 49%, 16%.
  - Whole-building sales only: 57%, 13%.
- Hedonic practice uses log price with log living area as a regressor, so the size effect is an elasticity, not a fixed $/sq ft. Rosen (1974) [ref]; CCAO's res and condo models include building and unit sq ft as features [verified] — [model-res-avm](https://github.com/ccao-data/model-res-avm), [model-condo-avm](https://github.com/ccao-data/model-condo-avm)
- Measured size elasticities are below 1 (0.50 condo, 0.37 building [local]). That is why $/sq ft × size over-predicts large units and under-predicts small ones; price per sq ft is not constant across sizes.
- The IAAO AVM standard notes that per-unit and median-per-period methods do "not account for the myriad of other factors that affect sales prices." [verified] — [IAAO AVM standard](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf)
- The pool's mix [local]: 2,167 condo units / 283 whole buildings. By building unit count: 3-unit 1,120; 6-unit 577; 2-unit 310; 4-unit 307; 5-unit 136.

### Inferences
- Keep per unit as the modeled quantity. Add the size elasticity adjustment once the subject size comes from the user or a building pattern (`building_patterns.json` already gives sizes for the six standard buildings, so V1 can use them). Report $/sq ft as a secondary display only.
- Keep the condo-vs-whole-building distinction. Whole-building per-unit prices may carry a discount relative to selling units one at a time (one buyer, rental-investor pricing), and the pool can measure it within neighborhoods. Many test misses are "2-flats near pricier condo stock," which fits that pattern.

### Gaps
- I did not measure the whole-building vs condo-unit per-unit discount. It is easy to estimate from the pool with neighborhood × year fixed effects.

---

## Recommendations for V1 (each tied to sources above)

1. **Method: an adjusted comparable-sales model, with hedonic-derived adjustments.** Keep the IDW median comp engine. Before taking the median, adjust each comp for time (FHFA tract → ZIP → CBSA), size per unit (elasticity 0.50 condo / 0.37 building, refit nightly) and kind (condo unit vs whole building). Basis: IAAO AVM standard Appendix E (comps "should be adjusted for attributes that are dissimilar"; models backed by quantitative adjustments are "more stable, reliable"); Bourassa et al. 2003 and 2009 (location submarkets first). [IAAO](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf), [BHP](https://access.archive-ouverte.unige.ch/access/metadata/b023cc99-18b7-4f6b-8013-cbf6ce517016/download)
2. **Replace the hard fallback with empirical-Bayes blending** across Assessor neighborhood → community area → neighbors, with weight n/(n+k) and k fit by leave-one-out. Show n and the weight at each level. This satisfies CLAUDE.md Rule 4 without cliffs at the boundaries. Basis: Fay-Herriot / multilevel partial pooling [ref]; FHFA supertract minimum counts [verified]. [FHFA WP 21-01](https://fhfa.gov/document/wp2101.pdf)
3. **Fix time adjustment.** Drop the pool-median-by-year trend (it raised test MdAPE from 7.8% to 10.6% [local]) and use FHFA indices, with a within-pool hedonic year-quarter index as a check. Cap comp age at 5 years. Basis: IAAO (5-year limit with time adjustment; median-per-period trends ignore composition). [IAAO Ratio](https://www.audits2.ga.gov/wp-content/uploads/2024/08/Standard_on_Ratio_Studies.pdf)
4. **Sale filters:** add the CCAO `sv_is_outlier` flags from the public training-data parquet, joined on doc_no or PIN plus date, with run_id stored as the source. Keep our pre-completion filter (< 50% of the comp median per sq ft, plus a permit-to-sale timing check) and the deed and repeat-price rules. Correct `feasibility_defaults.json`: `wvhk-k5uv` publishes only `sale_filter_same_sale_within_365`, `sale_filter_less_than_10k`, `sale_filter_deed_type` and `is_multisale`, not the sales-validation flags. Basis: [model-sales-val](https://github.com/ccao-data/model-sales-val); our join (10 flagged of 1,938 matched [local]).
5. **Dollar range: a calibrated 80% interval from leave-one-out conformal residuals**, stratified by search tier × kind. Show it as "$X (-$a / +$b); 80% of past estimates from N similar comps landed in this range." Replace the P25-P75 comp spread, which is a 50% band (49% test coverage [local]). Today's pooled multipliers are ×0.74 / ×1.36. Basis: Bastos & Paquette 2025 (conformal QR hits nominal coverage; raw quantiles undercover by 12-14 points); Freddie Mac FSD validation. [Bastos](https://rem.rc.iseg.ulisboa.pt/wps/pdf/REM_WP_0314_2024.pdf), [Freddie Mac](https://my.sf.freddiemac.com/docs/pdf/fact-sheets/dougwhitepaper_metricsmatter.pdf)
6. **Metrics to report on every calibration run:**
   - Point accuracy: PPE10, PPE15, PPE20, MdAPE and signed median error.
   - IAAO ratio stats: median ratio with 90% CI, COD, PRD, and PRB with 95% CI, split by kind (whole building vs condo unit).
   - Interval coverage at 80%.
   - Results on two sets: the 35-building test set and a full-pool leave-one-out or out-of-time holdout (most recent 10% of sales, as the CCAO does).

   Basis: IAAO AVM standard 7.3-7.4; CCAO out-of-time testing. [IAAO](https://www.iaao.org/wp-content/uploads/Standard_on_Automated_Valuation_Models.pdf), [CCAO](https://github.com/ccao-data/model-res-avm)
7. **Targets for V1:**
   - Test set: keep PPE15 ≥ 70%, and report its 95% CI (today 52%-81% on n = 35).
   - Out-of-time pool holdout: PPE15 ≥ 55%, MdAPE ≤ 13% (today about 50% and 14.9%).
   - COD ≤ 20 for whole buildings and ≤ 15 for condo units (IAAO 2-4 unit and heterogeneous single-family bands).
   - PRB CI overlapping ±0.10 (condo PRB is -0.29 today; the size adjustment should fix most of it).
   - 80% interval coverage between 75% and 85%.

   Basis: IAAO Table 1-3 / Table 2; Freddie "Medium" FSD 13-20%; published hedonic results of about 75% within 20%. These are internal quality bars. The 2024 federal rule sets no numbers and does not apply to us as a non-lender. [Fed. Reg.](https://www.federalregister.gov/documents/2024/08/07/2024-16197/quality-control-standards-for-automated-valuation-models)
8. **LightGBM only as a shadow benchmark.** Run it nightly on the same pool and show its gap as a "models disagree" flag, not as the number. Basis: Mayer et al. (more accurate but more volatile); our Rule 5 (show the comps behind the number). [IDEAS](https://ideas.repec.org/p/chf/rpseri/rp1876.html)
9. **Assessor certified value × 10 as a sanity check** (from `uzyt-m557` or the parquet `meta_certified_tot`). Flag gaps over 30% for review and do not blend. This needs a backtest on 2014+ buildings first.
