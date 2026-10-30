# Uncertainty display, range math, site scoring, valuation guardrails and fairness checks for 25x125 V1

Scope: how 25x125 should show ranges and confidence, combine uncertain inputs, build and validate the development score, stay clear of appraisal and advertising rules, and check comps for neighborhood bias. Research done 2026-10-30. Project files read: `CLAUDE.md`, `docs/v1-spec.md` (Development score, Feasibility math, Rents and sale values), `data/rules/development_score.json`, `data/rules/feasibility_defaults.json`.

Notation: "UNVERIFIED" marks a claim from memory or a secondary source that was not checked against the primary text in this session.

---

## 1. How do people read ranges vs point estimates, and which display formats work?

### Takeaway
A numeric range next to a clearly marked central figure costs little trust: trust in the number dips slightly and trust in the source does not move. Vague verbal hedges ("estimates may vary", "low confidence") cost more. Two kinds of uncertainty should be shown separately: the range itself (direct) and how good the evidence is (indirect: comp count, distance searched, date span). Every range has to say what probability it covers. Our sale range is a 50% range (P25-P75) and our cost margin is described as P80, so the two are not on the same footing today.

### Cited Findings
- van der Bles et al. (2019) set out a framework. Uncertainty attaches to facts, numbers or models. **Direct** uncertainty is about the number itself; **indirect** uncertainty is about the quality of the evidence behind it, and should be communicated separately. They list nine expressions from most to least precise: full distribution, summary such as an interval, rounded figure or range, predefined category, verbal qualifier, list of possibilities, general acknowledgment, no mention, explicit denial. *Royal Society Open Science* 6(5):181870, doi:10.1098/rsos.181870 — [PMC6549952](https://pmc.ncbi.nlm.nih.gov/articles/PMC6549952)
- In the same review, Johnson & Slovic found about half of respondents took the **highest value in a range** as the right figure (an upward bias). Han et al. found a numeric range in text raised worry compared with a point estimate, while a visual format lowered it. Motivated reasoning shapes how ranges are read, and explaining the correct reading reduced that bias — [van der Bles et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6549952)
- Its Box 5a advice: say what is uncertain and why (natural variation, measurement, limited knowledge, disagreement), communicate direct and indirect uncertainty separately, keep the size of the uncertainty apart from the strength of the evidence, and test with real users — [van der Bles et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6549952)
- van der Bles, van der Linden, Freeman & Spiegelhalter (2020), *PNAS*, doi:10.1073/pnas.1913678117. Five UK experiments with 5,780 people in total, including a preregistered replication (n=1,050) and a BBC News field test (n=1,700). Topics were unemployment, migration, temperature and tiger counts. A **numeric range** led to a small drop in trust in the number and **no significant change in trust in the source**. A **verbal statement** of uncertainty led to a larger drop in trust in the number and a small drop in trust in the source. The field test effects were not significant. Political ideology did not change how people reacted to uncertainty — [summary of the paper](https://blog.aiimpacts.org/p/paper-summary-the-effects-of-communicating) (secondary source; effect sizes are in the paper's Fig. 5, not checked here). Paper record: [RUG research portal](https://research.rug.nl/en/publications/the-effects-of-communicating-uncertainty-on-public-trust-in-facts/)
- Dieckmann, Peters & Gregory (2015), "At Home on the Range? Lay Interpretations of Numerical Uncertainty Ranges", *Risk Analysis* 35(7):1281-1295, doi:10.1111/risa.12358. People differ widely in the distribution they picture behind a bare range (uniform, normal, U-shaped). Higher numeracy pushes toward a normal reading. **Adding a best estimate** makes a normal reading more likely, and **simple graphics cut the variation** in interpretation — [IDEAS/RePEc](https://ideas.repec.org/a/wly/riskan/v35y2015i7p1281-1295.html)
- EFSA (2019), Guidance on Communication of Uncertainty in Scientific Assessments, *EFSA Journal* 17(1):e05520, doi:10.2903/j.efsa.2019.5520. Points relevant here:
  - A range alone does not state a probability, so the probability has to be given.
  - Give both a central estimate and a range and keep them visually distinct, because people fixate on one end of a range.
  - Use the word **"central" rather than "best"**, since "best" implies a preference.
  - People do badly at reading a central estimate off a density graph.
  - **Box plots are the best-understood graphic.** PDFs and CDFs are often misread and belong at the technical level only.
  - Label graphics as showing uncertainty, not variability.
  - Report the median with 50% and 95% ranges.
  - "More than X" is read as an extreme value.
  - Numbers reduce the spread in how verbal terms are read, and the number should come first.
  - Explain the concepts once in an FAQ rather than in every communication.
  - Source: [EFSA guidance table, PMC7292191](https://pmc.ncbi.nlm.nih.gov/articles/PMC7292191/table/nlm-table-wrap-1)
- Verbal probability terms vary widely between readers. The IPCC means "very likely" as ≥90%, but the median reader took it as about 65-75% — [van der Bles et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6549952)
- **Anchoring in property valuation, real-estate-specific:**
  - Northcraft & Neale (1987), "Experts, amateurs, and real estate: An anchoring-and-adjustment perspective on property pricing decisions", *Organizational Behavior and Human Decision Processes* 39(1):84-97 — [IDEAS](https://ideas.repec.org/a/eee/jobhdp/v39y1987i1p84-97.html). No abstract was available. The usual summary is that agents' and students' value estimates moved with the listing price they were given, and agents denied using it. UNVERIFIED against the full text.
  - Diaz (1997), *Journal of Real Estate Research* 13(1):57-66, doi:10.1080/10835547.1997.12090864. Expert and apprentice appraisers who saw an anonymous expert's prior value differed from controls in the anchored direction, but not significantly: "anchoring may be more subtle than generally believed" — [IDEAS](https://ideas.repec.org/a/taf/rjerxx/v13y1997i1p57-66.html)
  - Cypher & Hansz (2003), *Journal of Property Research* 20(4):305-318, doi:10.1080/0959991042000182001. **Non-appraisers anchored on a published assessed value; expert appraisers did not.** Experts seem to need the anchor to look relevant before they use it — [IDEAS](https://ideas.repec.org/a/taf/jpropr/v20y2003i4p305-318.html)
  - Gallimore's 1990s valuation-judgment work was not retrieved (gap).
- Zillow pairs one figure with a range: "In addition to a single Zestimate value, we provide an estimated sales range… The Zestimate represents the most likely outcome, while the range reflects how results may vary around that estimate." It publishes median error monthly: 1.77% on-market and 7.20% off-market nationally, refreshed 2026-09-30 — [Zillow Zestimate page](https://www.zillow.com/zestimate)
- Redfin publishes median error (1.92% for-sale, 7.55% off-market) and the share of estimates within 5%, 10% and 20% of the sale price. Off-market: 36.36% within 5%, 59.99% within 10%, 81.72% within 20%. Updated weekly, last 10/29/26 — [Redfin Estimate page](https://redfin.com/redfin-estimate)
- Repo practice: `feasibility_defaults.json` sets `sale_value_range` as the 25th-75th percentile of weighted comps (a 50% range), and `cost_confidence` shows P50 = central and **P80** = central × (1 + stage high margin). It also adds 10 points of margin per side when an area has fewer than 10 permits (`thin_data.extra_margin_points_when_thin`) — [local file](file:///home/user/25x125/data/rules/feasibility_defaults.json)

### Inferences
- The PNAS result supports CLAUDE.md rule 3: dollar ranges such as `$1,375,000 (-$275,000 / +$413,000)` should not erode trust in 25x125 as a source. The risk is in hedge words with no number, such as "data is thin" on its own.
- Dieckmann and EFSA both say the central figure should be visually dominant and the bounds secondary. Use bold central, lighter bounds, and a small horizontal bar or box-plot strip. A fan chart is not needed: V1 has no time series to fan out, and EFSA rates density-type graphics as often misread.
- Each range needs a plain probability label. For the sale range: "Half of the comparable sales fell in this range (25th-75th percentile)". For cost: "We expect about 8 in 10 projects at this stage to come in under the high figure". The low cost margin (-20%) has no stated percentile in the repo, and it should get one (for example P20, or relabel the pair P10/P90). Without that, the profit range mixes a 50% sale band with an undefined cost band.
- Johnson & Slovic found people take the high end of a range as the answer. Our users are buyers deciding what to pay, so the upside reading is the costly one. Showing max land price at the central figure and the low case, as the spec already does, fits that risk.
- The thin-data widening is indirect uncertainty. It should appear as a separate evidence line with numbers, not folded silently into the range. For example: "7 sales within 1.5 mi, Mar 2022-Aug 2026; range widened 10 points because this area has 6 permits (fewer than 10)". The Cypher & Hansz result suggests experienced brokers will discount weak anchors, but lay users will not, which argues for showing comp count next to the number every time.
- Accuracy should be published the way Zillow and Redfin do: median error plus within-10% and within-20% shares, by community area with counts, and with the refresh date. Our own leave-one-out result (spec: 24 of 37 within 15%, median error 12%) is the starting figure.

### Gaps
- Exact PNAS effect sizes were not read from the primary text. A secondary summary was used.
- No study found that tests dollar ranges for construction or development budgets with lay or small-developer audiences specifically.
- Northcraft & Neale and Gallimore full texts were not retrieved. Spiegelhalter's broader writing (e.g., "Risk and uncertainty communication", *Annual Review of Statistics* 2017) was not retrieved; UNVERIFIED.
- No evidence found on how best to label "range widened because data is thin". The recommended wording is inference from the direct/indirect framework.

---

## 2. How should ranges be combined when profit or max land price depends on several uncertain inputs?

### Takeaway
The spec's profit range is "low sale minus high cost, to high sale minus low cost". That is interval (corner) arithmetic. Its coverage is unknown, it mixes a 50% band with an 80% band, and it ignores correlation. It also hides that cost is right-skewed: with a -20%/+30% margin, the median profit is below "central sale minus central cost". A small Monte Carlo with rank correlation between sale and cost (Iman-Conover) gives labeled P10/P50/P90 bands at little compute cost, and it remains explainable if each run also shows a scenario table (low/central/high) and a one-at-a-time tornado chart.

### Cited Findings
- Evans (1992), "Monte Carlo Analysis: A Practical Application to Development Appraisal", *Journal of Property Finance* 3(2), doi:10.1108/09588689210033846. Criticizes the single-figure residual appraisal used at pre-purchase. Applies Monte Carlo to the residual land method and concludes it gives "a much more graphical impression than a deterministic method" — [Emerald](https://emerald.com/insight/content/doi/10.1108/09588689210033846/full/html)
- French & Gabrielli (2006), "Uncertainty and feasibility studies: an Italian case study", *Journal of Property Investment & Finance* 24(1):49-67, doi:10.1108/14635780610700732. A feasibility study must forecast the most likely sale price, construction cost and timing, plus financing. They propose a two-dimensional technique that separates **uncertainty** (lack of knowledge) from **variability** — [IDEAS](https://ideas.repec.org/a/eme/jpifpp/14635780610700732.html)
- A further *Journal of Property Investment & Finance* practice briefing proposes a disclosure guide for Monte Carlo valuations: say which inputs were simulated, which distributions were used and what correlation was assumed — [Heriot-Watt research portal](https://researchportal.hw.ac.uk/en/publications/practice-briefing-towards-a-disclosure-guide-for-monte-carlo-valu/) (abstract-level only; contents not checked)
- Iman & Conover (1982), "A distribution-free approach to inducing rank correlation among input variables", *Communications in Statistics – Simulation and Computation* 11(3):311-334. This is the standard way to correlate inputs that have arbitrary marginal distributions — [bibliography entry](https://ftp.math.utah.edu/pub/tex/bib/idx/communstatsimulcomput1980/11/3/311-334.html). It is implemented in R `mc2d::cornode` ([docs](https://search.r-project.org/CRAN/refmans/mc2d/html/cornode.html)), with a worked example at [SAS blog](https://blogs.sas.com/content/iml/2021/06/14/simulate-iman-conover-transformation.html)
- Homes England reference class forecasting and BCIS location indices are the repo's cited sources for P50/P80 and cost indices — [docs/international-practices.md](file:///home/user/25x125/docs/international-practices.md) (local; external sources not re-checked here)
- **Illustrative simulation run for these notes** (script: `/tmp/claude-0/-home-user-25x125/8b22a33b-54d0-5e07-8c9b-16c20823ced6/scratchpad/mc.py`, 200,000 draws).
  - Assumptions: central total cost $1,375,000 with -20% at P20 and +30% at P80 (split normal); central net sale $1,700,000 with ±10% at P25/P75; Gaussian copula between the two.
  - Corner arithmetic gives -$257,500 to +$770,000 around a $325,000 central.
  - Simulated profit percentiles:

    | Correlation | P10 | P25 | P50 | P75 | P90 | P(loss) |
    |---|---|---|---|---|---|---|
    | 0.0 | -$378,000 | -$51,000 | $290,000 | $595,000 | $852,000 | 28% |
    | 0.3 | -$289,000 | -$6,000 | $287,000 | $547,000 | $764,000 | 25% |
    | 0.6 | -$181,000 | $50,000 | $283,000 | $490,000 | $662,000 | 21% |

  - The P50 profit (~$285,000) sits about $40,000 below the "central minus central" $325,000, because the cost distribution is skewed to the high side.
  - Positive correlation narrows the profit range.
  - These numbers come from assumed inputs, not data. Use them only to show the direction of the effects.

### Inferences
- **Correlation direction is project-specific.** Over a whole market cycle, sale prices and build costs tend to move together (positive correlation), which narrows the profit range. A 12-18 month project, though, locks most cost at contract while the sale lands at completion, so for one project a sale-price drop is not offset by cost. A defensible default is a modest positive rank correlation (0.2-0.4) as an editable assumption that is shown on screen, with ρ=0 as the conservative toggle. No Chicago-specific estimate of this correlation was found (gap). One can be estimated from FHFA HPI (already used for time adjustment) and the FRED PPI series `WPUIP2311001` already in `feasibility_defaults.json`.
- **Max land price** (net sale/(1+target) − non-land cost) is roughly linear in the same inputs, so the same simulation gives its P10/P50/P90 for free. The spec's "central and low case" maps to P50 and P10, provided both are labeled.
- **Analytic error propagation** (summing variances) is fine for sums of nearly symmetric inputs, but our cost margin is asymmetric and the return-on-cost ratio is nonlinear. Monte Carlo avoids both problems. Our model has about 10 inputs and a 2-6 unit scope, so 10,000 draws per parcel per night is cheap. For the nightly score, use Latin hypercube or a fixed seed so the results are reproducible and the nightly job and live screen give the same answer.
- **Keep the explainable layer.** Users should still see a three-row scenario table (low sale/high cost, central, high sale/low cost) and a tornado chart of which input moves profit most. This follows "show the math" (rule 5) and the Monte Carlo disclosure guidance.
- Treat stage margins (-20%/+30%) as **epistemic** uncertainty (what we don't know about cost) and comp dispersion as **variability** (spread among buildings). That is the French & Gabrielli distinction, and it supports showing them on separate evidence lines.

### Gaps
- No published estimate found of the correlation between Chicago new-construction sale prices and hard costs at project horizon.
- Full texts of Evans 1992, French & Gabrielli 2006 and the Heriot-Watt disclosure briefing were not read, so their exact distribution choices and correlation treatments are unknown.
- The repo does not define the percentile of the -20% low cost margin.

---

## 3. How should the site score be built and validated? Is a points-based score defensible?

### Takeaway
A transparent points-based weighted linear combination (WLC) is a standard and defensible GIS-MCDA form, if three things hold: the parts are not double-counted, the weights are tested for how much rankings depend on them, and the score is backtested out-of-sample against parcels that were actually developed. The current `development_score.json` passes on transparency and user weights. It double-counts market strength (zoning upside and location both feed profit), ignores how wide the profit range is, and has not been validated. Chicago's permit history (519,875 permits, plus the 2-6 unit new-construction subset) supports a point-in-time backtest.

### Cited Findings
- Malczewski is the standard reference for GIS-MCDA. WLC and AHP are its most common combination rules: *GIS and Multicriteria Decision Analysis* (Wiley, 1999); Malczewski (2006), "GIS-based multicriteria decision analysis: a survey of the literature", *International Journal of Geographical Information Science* 20(7):703-726; Malczewski & Rinner (2015), *Multicriteria Decision Analysis in Geographic Information Science*, Springer — [Springer listing](https://link.springer.com/doi/10.1007/978-3-540-74757-4). Volume and page details from memory: UNVERIFIED.
- Ligmann-Zielinska & Jankowski (2014), *Environmental Modelling & Software* 57:235-247 — [reprint](https://project.geo.msu.edu/stsa/pubs/EMS2014_reprint.pdf):
  - "Criteria weights usually constitute the most subjective component of any multiple criteria decision analysis."
  - They sampled weights from uniform [0,1], normalized them, and ran 138,240 model runs using a Sobol' design.
  - The mean suitability map shows how suitable each place is. The standard-deviation map shows how much that place's rank depends on the weights. **High mean with low SD = robust sites; high mean with high SD = candidates that need more study.** In their case about 70% of high-suitability area was robust and 30% was candidate.
  - One-at-a-time sensitivity "has no guarantee" of capturing a criterion's real influence or interactions. Variance-based first-order (S) and total-effect (ST) indices are recommended instead.
- Commercial practice: Chicago Cityscape describes its Zoning Assessment as something that "estimates the number of dwelling units allowed on a given parcel" and dates its help pages ("Last updated July 23, 2026"). No disclosed validation method was found — [Chicago Cityscape vs CoStar help page](https://www.chicagocityscape.com/help/comparisontocostar)
- Repo facts:
  - Score = zoning upside 30 + profit 30 + acquisition signals 20 + location 10 + incentives 10, with penalties down to -20, clamped to 0-100.
  - Profit points use "return on cost at central estimate".
  - Location gives 5 points for "area_sales_12m_above_city_median".
  - `user_weights: true`.
  - Source: [development_score.json](file:///home/user/25x125/data/rules/development_score.json); [v1-spec.md §Development score](file:///home/user/25x125/docs/v1-spec.md)

### Inferences
- **Points-based is defensible.** Dawes (1979), "The robust beauty of improper linear models in decision making", *American Psychologist* 34(7):571-582 (doi:10.1037/0003-066X.34.7.571), found that unit or rough weights often predict nearly as well as fitted ones when the criteria point the right way. That supports a simple, readable score over a black box. Citation from memory, not fetched: UNVERIFIED. The usual critique of AHP is rank reversal when options are added (Belton & Gear 1983; UNVERIFIED). Our score has about 15 criteria and users edit the weights directly, so pairwise-comparison AHP adds friction without a validation gain.
- **Double counting.** More by-right units raise both zoning-upside points and profit points. Strong neighborhood sales raise both location points and profit points (sale price enters profit). The score therefore puts more weight on market strength than the 10-point location part suggests. Options:
  - (a) drop `area_sales_12m_above_city_median`, since it is already in profit;
  - (b) score profit per by-right scenario, so upside counts once;
  - (c) report the correlation between parts in the validation output.
- **Uncertainty-blind profit points.** Two parcels with the same central return of 15%, one resting on 40 comps within 0.75 mi and one on 6 comps at 3 mi, score the same. Fixes: base profit points on the P25 (or low-case) return, or show the score as a range (P10-P90 of score from the Monte Carlo) and sort on P50, tagging Ligmann-Zielinska-style "robust" and "rank depends on assumptions".
- **"Show the math, don't recommend" (rule 5) and the investor-network rule "no ranking of deals as good investments".**
  - Present the score as a sort key built from listed points. For example: "Development score: points from zoning, estimated return, signals, location and incentives. A sorting aid, not a rating of investment quality."
  - Always show the point breakdown.
  - Avoid words such as "best", "top opportunity", "recommended" or color scales labeled good/bad.
- **Validation plan against Chicago permits (backtest):**
  1. **Point-in-time snapshots.** For as-of dates T in {2018-01-01, 2019-01-01, 2020-01-01, 2021-01-01}, rebuild every input as it was known at T: zoning (only if historical zoning layers exist), violations and complaints before T, sales comps before T, cost index from permits before T. Leakage is the main threat; profit points built from today's comps would make the backtest meaningless.
  2. **Outcome.** A new-construction permit (or demolition plus new construction) for 1-6 units on the parcel within 36 months of T, from building permits `ydr8-5enu`. Secondary outcome: realized first sale above total cost (from `new_construction_sales.csv`) for the subset that sold.
  3. **Metrics.**
     - Lift and capture by score decile: share of later-developed parcels in the top 10% of scores, against 10% for random.
     - Precision@k for k = 100, 500, 1,000 citywide and per community area.
     - ROC AUC as a summary.
     - Calibration of the profit part: predicted P50 return against realized return on test parcels.
     - Rank stability under weight perturbation: share of the top 500 that stays in the top 500 when each weight moves ±50%, or under Dirichlet-sampled weights, following Ligmann-Zielinska & Jankowski.
  4. **Baselines.** Random; zoning-upside only; vacant-lot flag only. The score earns its complexity only if it beats these out-of-sample.
  5. **Hold out by time and by place.** Fit or tune on 2018-2019, test on 2020-2021. Report each community area separately so a few hot areas (e.g., Logan Square, West Town) cannot carry the citywide number.
  6. **Caveat to state on screen and in docs.** "Was developed" measures where developers built. It does not measure profitability or what should be built. A score tuned to past permits will reproduce past development patterns, including gentrification patterns (see §5). Treat backtest results as evidence that the score finds parcels developers acted on, not as a target to maximize.
- Our 35 test parcels are enough to calibrate profit and sale numbers but far too few to validate a citywide ranking. The permit history is the right base.

### Gaps
- No published validation of a commercial US parcel-scoring product (Cityscape, Reonomy, LandVision, Regrid etc.) against later development was found.
- Malczewski 2006 survey text and the Dawes and AHP rank-reversal critiques were not fetched this session.
- Whether historical Chicago zoning layers (as-of 2018) are available for a point-in-time backtest was not checked. If they are not, the zoning part can only be backtested with current zoning, which leaks a small amount where parcels were rezoned.

---

## 4. Regulatory guardrails: when is an estimate an "appraisal", and how do others label estimates?

### Takeaway
In Illinois, "appraisal" means "the act or process of developing an opinion of value" (225 ILCS 458/1-10). Two exemptions in the Act apply to us: procuring an AVM is exempt (§5-5(h)), and a broker's BPO or CMA prepared under the Real Estate License Act is exempt (§5-5(c)). The 7th Circuit (Patel v. Zillow, 2019) found no private right of action under the Appraiser Act, and held that values clearly labeled as estimates are opinions, not deceptive statements of fact. The 2024 federal AVM quality-control rule binds mortgage originators and secondary-market issuers making credit decisions, not tool vendors. Lenders who use our numbers would inherit its five factors, including nondiscrimination. The Illinois Act's §5-5 shows a scheduled repeal date of January 1, 2027, two months from now. Watch for the sunset extension.

### Cited Findings
- **225 ILCS 458/1-10 definitions** (as amended by P.A. 100-0604) — [ILGA P.A. 100-0604](https://ilga.gov/legislation/publicacts/100/100-0604.htm):
  - "Appraisal" (noun): "the act or process of developing an opinion of value".
  - "Appraisal report": "any communication, written or oral, of an appraisal or appraisal review" transmitted to a client.
  - "Appraisal assignment": "a valuation service provided as a consequence of an agreement between an appraiser and a client".
  - "Broker price opinion": "an estimate or analysis of the probable selling price of a particular interest in real estate". Ordinary brokerage activity is not a BPO or CMA "if no compensation is paid to the broker or managing broker" beyond the sale or rental commission.
- **225 ILCS 458/5-5** — [ILGA §5-5](https://ilga.gov/legislation/ilcs/documents/022504580K5-5.htm):
  - (a) It is unlawful to develop an appraisal or practice as an appraiser without a license. A first offense is a Class A misdemeanor; later offenses are a Class 4 felony.
  - (b) No one unlicensed may use titles suggesting licensure.
  - (c) The Act does not apply to a licensed broker or managing broker preparing a BPO or CMA in compliance with §10-45 of the Real Estate License Act of 2000.
  - (f) No license is needed for anyone appraising its own property solely for its own use.
  - (h) "The Act does not apply to procuring an automated valuation model."
  - The page notes the section is scheduled for repeal January 1, 2027.
- **Patel v. Zillow, Inc.**, No. 18-2130 (7th Cir. Feb. 8, 2019) (Easterbrook, J.), 915 F.3d 446 — [FindLaw](https://caselaw.findlaw.com/court/us-7th-circuit/1980489.html):
  - The court affirmed dismissal because the Appraiser Act has no private right of action. It did not decide whether a Zestimate is an appraisal ("need not consider the first").
  - Zestimates are opinions. "Having labeled Zestimates as estimates", Zillow is outside the Uniform Deceptive Trade Practices Act. "The Act prohibits deception rather than error."
  - The court noted Zillow tells users that no parcel has been inspected and Zestimates may be inaccurate. It quoted a median error under 6% but "off by more than 20% in about 15% of all sales".
  - Statutory backstops cited: §15-5 fines up to $25,000 per unlicensed appraisal and state injunctions.
- **USPAP**: "appraisal" is "the act or process of developing an opinion of value". An "appraiser" is one "expected to perform valuation services competently". USPAP binds those expected to act as appraisers (through licensing, representation, engagement or how they present themselves) and those required by law, regulation or agreement. It does not bind everyone who estimates value — [USPAP study guide summary](https://open-exam-prep.com/study-guides/real-estate-appraiser/uspap-rules-standards/uspap-definitions-ethics) (secondary; primary USPAP text from The Appraisal Foundation not fetched)
- **Interagency AVM QC rule**, 89 FR 64538 (Aug. 7, 2024), effective **October 1, 2025** — [Federal Register](https://www.federalregister.gov/documents/2024/08/07/2024-16197/quality-control-standards-for-automated-valuation-models); [govinfo PDF](https://govinfo.gov/content/pkg/FR-2024-08-07/pdf/2024-16197.pdf):
  - Applies to mortgage originators and secondary market issuers using AVMs in credit decisions (originate, modify, terminate, change a HELOC limit) or covered securitization determinations, for collateral that is a consumer's principal dwelling.
  - Excludes monitoring-only uses, AVMs used by certified appraisers, and reviews of completed valuations.
  - QC must: "ensure a high level of confidence in the estimates", "protect against the manipulation of data", "seek to avoid conflicts of interest", "require random sample testing and reviews", and comply with nondiscrimination laws (the fifth factor, added by the agencies).
  - The rule is principles-based. It does not directly regulate vendors, but institutions stay responsible for vendor models.
  - CFR parts: 12 CFR 34, 225, 323, 722/741, 1026 (Reg Z comment 42(i)), 1222.
  - Also: [CFPB small entity compliance guide](https://files.consumerfinance.gov/f/documents/cfpb_quality-control-standards-for-avm-small-entity-compliance-guide_2024-10.pdf); [OCC Bulletin 2024-17](https://occ.gov/news-issuances/bulletins/2024/bulletin-2024-17.html)
- **FTC Policy Statement Regarding Advertising Substantiation** (Nov. 23, 1984, appended to *Thompson Medical*, 104 F.T.C. 648): advertisers must have a reasonable basis for objective claims before running them. An express claim of support ("tests show") requires at least that support, and an implied claim requires "the amount and type of substantiation the ad actually communicates to consumers" — [FTC](https://www.ftc.gov/node/52431)
- **Exact labeling language used by others:**
  - Zillow: "It is not an appraisal and can't be used in place of an appraisal." "Most lending professionals and institutions will only use professional appraisals when making loan-related decisions." — [Zillow](https://www.zillow.com/zestimate)
  - Redfin: "the Redfin Estimate is not a formal appraisal or substitute for the in-person expertise of a real estate agent"; "it is not an appraisal or a substitute for the expert pricing advice of your real estate agent." — [Redfin](https://redfin.com/redfin-estimate)
  - Chicago Cityscape: the Zoning Assessment "estimates the number of dwelling units allowed on a given parcel." No formal disclaimer on that page — [Cityscape](https://www.chicagocityscape.com/help/comparisontocostar)
  - The City of Chicago zoning map has its own terms page — [gisapps.chicago.gov terms](https://gisapps.chicago.gov/ZoningMapWeb/terms.html) (not fetched)

### Inferences
- **Our exposure.** 25x125 computes sale values and max land prices by software from public comps. That is close to an AVM, and §5-5(h) exempts procuring an AVM, though the statute does not expressly cover *providing* one. That is a gap for counsel. Patel shows the main practical defense is clear labeling as an estimate with no inspection, plus published accuracy. Do not use the words "appraisal", "appraised value", "valuation report" or "certified".
- **Brokerage overlap.** The company is vertically integrated and includes brokerage. If a broker hands a client a 25x125 sale value in exchange for a fee outside a commissioned sale, that could become a BPO under the Real Estate License Act §10-45 and must meet its requirements. Keep in-product estimates free of per-report fees tied to a named property's value, or route them through §10-45 compliance. Flag for counsel.
- **Lenders.** Terms should say outputs are not for credit decisions or collateral valuation. Under the AVM rule, a lender relying on us would owe the five QC factors and would ask us for testing evidence and nondiscrimination checks. Running those checks (§5) anyway puts us in a better position if lenders come.
- **Marketing.** Under the FTC statement, any public claim such as "within 15% for 70% of buildings" needs the backtest on file, with the test set, date and method. Claim only what the current published accuracy table supports.
- **Sunset.** The Appraiser Act's §5-5 repeal date of 2027-01-01 was observed on the ILGA page today. Illinois usually extends these sunsets. Recheck in January 2027. Since this is an Illinois-only product, the outcome matters.

### Gaps
- No Illinois case or IDFPR guidance found on whether publishing an AVM-style estimate (as opposed to procuring one) needs a license.
- The current text of RELA §10-45 BPO/CMA requirements was not fetched.
- The primary USPAP 2024 edition text was not fetched. The Appraisal Foundation's definitions were taken from a study-guide summary.
- Chicago Cityscape's terms of service were not fetched, so its full disclaimer language is unknown.

---

## 5. Fairness: AVM and assessment bias by neighborhood race, and what checks we should run

### Takeaway
There is strong evidence that valuations in Chicago and the US have been biased by neighborhood. Cook County assessments were regressive under the previous assessor (bottom 5% of homes assessed at about 12.5% vs 8.2% for the top 5%). Appraisals in majority-Black and majority-Latino tracts come in below contract price about twice as often. Homes in majority-Black neighborhoods list about 23% lower after controls. Our comps are market prices, so they carry whatever bias the market has. Our own method can add more bias through wider fallback radii in thin areas and through the "above city median" location points. The fix is to measure: run sales-ratio statistics (median ratio, COD, PRD) on our leave-one-out estimates by community area and by tract racial composition, and publish them.

### Cited Findings
- **Berry (2018), Center for Municipal Finance, Harris School.** At least $2.2B in property taxes shifted from undervalued to overvalued Chicago homes in 2011-2015. The top 10% by value saved up to $1B. Method: arm's-length sales (about 2.5% of homes) and a "fair" tax rate, extrapolated with four methods — [ProPublica, 2018](https://www.propublica.org/article/cook-county-property-tax-shift-regressive-assessments)
- **Berry (2025), "An Evaluation of Progress on Residential Assessment Fairness in Cook County"**, using public open data for 2019-2024 — [PDF](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/6/2330/files/2025/09/Kaegi-Evaluation-9_04.pdf); [Assessor press release, 2025-09-08](https://www.cookcountyassessoril.gov/news/cook-county-homeowners-saved-19-billion-under-fritz-kaegis-reforms-university-chicago-study):
  - Sales-ratio results by assessment cycle:

    | Cycle | Sales | COD | PRD | Median ratio |
    |---|---|---|---|---|
    | 2016-18 | 182,859 | 20.01 | 1.036 | 0.088 |
    | 2019-21 | 193,820 | 19.47 | 1.008 | 0.086 |
    | 2022-24 | 161,943 | 18.87 | 1.007 | 0.082 |

  - Bottom-5% vs top-5% ratio fell from 153% (12.5% vs 8.2%) to 116%.
  - Regressivity was measured with 20 sale-price quantile bins, with condos analyzed separately.
  - Overall accuracy did not improve: the median ratio drifted down.
  - The bottom 70% pay about $1.9B less than under the prior office.
- **IAAO thresholds** (as applied to Cook County): COD 5-15 for large mixed jurisdictions, up to 20 for varied property; PRD 0.98-1.03, ideal 1.00. PRD = mean ratio / weighted mean ratio. Above 1.03 suggests regressivity — [IAAO PCS 2019 Cook County Sales Ratio Study](https://prodassets.cookcountyassessoril.gov/s3fs-public/reports/2019_IAAO_sales_ratio_study_final.pdf); confirmed in [Berry 2025](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/6/2330/files/2025/09/Kaegi-Evaluation-9_04.pdf). PRB (price-related bias; acceptable roughly ±0.05) comes from the 2013 IAAO Standard on Ratio Studies and was not verified in a fetched source: UNVERIFIED.
- **Freddie Mac (Sept 2021), "Racial and Ethnic Valuation Gaps in Home Purchase Appraisals"** — [research note PDF](https://www.FreddieMac.com/fmac-resources/research/pdf/202109-Note-Appraisal-Gap.pdf):
  - 12.75M single-family purchase appraisals, 2015-2020.
  - Share appraised below contract price: 7.4% in white tracts, 12.5% in majority-Black tracts (13.3% at 80-100% Black), 15.4% in majority-Latino tracts (16.7% at 80-100%).
  - Applicant-level, 2016-2020: white 6.5%, Black 8.6%, Latino 9.5%.
  - Caveats: contract price is the benchmark, the modeling is preliminary, and the root cause was not determined.
- **Perry, Rothwell & Harshbarger (Brookings, Nov 2018), "The Devaluation of Assets in Black Neighborhoods"** — [Brookings PDF](https://www.brookings.edu/wp-content/uploads/2018/11/2018.11_Brookings-Metro_Devaluation-Assets-Black-Neighborhoods_final.pdf):
  - After controlling for home features and neighborhood amenities (schools, walkability, commute), homes in 50%-Black neighborhoods were valued about **23% lower** per sq ft (list price).
  - That is about $48,000 per home and $156B in total ($39,000 / $126B on Census values).
  - The gap appeared in 117 of 119 metros. No Chicago-specific figure was given.
- The AVM QC rule adds nondiscrimination compliance as a fifth QC factor for covered institutions — [Federal Register](https://www.federalregister.gov/documents/2024/08/07/2024-16197/quality-control-standards-for-automated-valuation-models)

### Inferences
- **Where our method can add bias:**
  - (a) Thin-data fallback. Areas with few new-construction sales (more likely on the South and West Sides) search out to 1.5-3 miles, pulling comps from different markets. The direction of the error is unknown and must be measured.
  - (b) Location points. `area_sales_12m_above_city_median` gives 5 points only to areas already above the median, and the profit part already rewards high prices. Together they push lower-priced, often majority-Black and Latino, community areas down the sort order.
  - (c) The cost index. Reported permit costs run low (spec). If underreporting differs by area, the half-weight adjustment moves costs in a biased way.
  - (d) Backtesting against past permits (§3) rewards whatever predicts past investment flows.
- **Checks to run before launch and nightly/monthly, using leave-one-out sale estimates on `new_construction_sales.csv` (2,450 sales) and the 35 test parcels:**
  1. ratio = estimate / actual sale, per sale;
  2. by community area: n, median ratio, COD, PRD, share within 10% and 20%;
  3. by tract racial and ethnic majority (ACS 5-year: majority Black, majority Latino, majority white, no majority), using the same metrics. Flag any group whose median ratio differs from the citywide median by more than about 5 points, or whose PRD falls outside 0.98-1.03;
  4. by search ring reached (0.75 mi / 1.5 mi / 3 mi), to measure the fallback error directly;
  5. by price decile (20 bins as in Berry 2025), to check vertical equity;
  6. for the score: distribution of score by community area and by tract racial majority, with and without the location points, published as a table.
- **What to publish.** A methods page with the accuracy table by community area (n, median error, within-10% and within-20%), last refreshed date and the fairness table. Mark areas with n < 6 as "too few sales to measure". This follows the Zillow and Redfin practice and rule 2.
- **What not to do.** Do not "correct" market prices for race. That would be its own fair-housing problem and would break "present the math". Measure the error, widen ranges where error is high, disclose it, and let users toggle the location points. Never use race or ethnicity as a model input. Use it only in the audit.

### Gaps
- No study found that measures AVM error by neighborhood race specifically in Chicago. Freddie Mac and Brookings are national, and Berry measures assessments, not AVMs.
- No published analysis found of how comp-radius fallback affects AVM error in low-transaction areas.
- PRB thresholds were not verified from the IAAO standard text.

---

## 6. What should 25x125 build? Recommendations tied to the sources above

### Takeaway
Show central figures in bold with labeled dollar bounds and a one-line evidence note. Compute bands with a small correlated Monte Carlo and keep a scenario table for explanation. Keep the points score, but remove double-counting, base profit points on a downside or range figure, and backtest it point-in-time against permits. Label everything as an estimate with no inspection and not an appraisal. Publish accuracy and fairness tables by community area.

### Cited Findings
- The recommendations below rest on: [van der Bles 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6549952), [van der Bles 2020 summary](https://blog.aiimpacts.org/p/paper-summary-the-effects-of-communicating), [Dieckmann 2015](https://ideas.repec.org/a/wly/riskan/v35y2015i7p1281-1295.html), [EFSA 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC7292191/table/nlm-table-wrap-1), [Iman & Conover 1982](https://ftp.math.utah.edu/pub/tex/bib/idx/communstatsimulcomput1980/11/3/311-334.html), [Ligmann-Zielinska & Jankowski 2014](https://project.geo.msu.edu/stsa/pubs/EMS2014_reprint.pdf), [225 ILCS 458/5-5](https://ilga.gov/legislation/ilcs/documents/022504580K5-5.htm), [Patel v. Zillow](https://caselaw.findlaw.com/court/us-7th-circuit/1980489.html), [AVM rule](https://www.federalregister.gov/documents/2024/08/07/2024-16197/quality-control-standards-for-automated-valuation-models), [FTC substantiation](https://www.ftc.gov/node/52431), [Berry 2025](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/6/2330/files/2025/09/Kaegi-Evaluation-9_04.pdf), [Freddie Mac 2021](https://www.FreddieMac.com/fmac-resources/research/pdf/202109-Note-Appraisal-Gap.pdf), [Brookings 2018](https://www.brookings.edu/wp-content/uploads/2018/11/2018.11_Brookings-Metro_Devaluation-Assets-Black-Neighborhoods_final.pdf), [Zillow](https://www.zillow.com/zestimate), [Redfin](https://redfin.com/redfin-estimate).

### Inferences

**A. Display formats** (EFSA, Dieckmann, van der Bles)
1. Use the format `Central $1,375,000 · range $1,100,000 to $1,788,000 (-$275,000 / +$413,000)`, with the central figure bold and the bounds lighter. Under the numbers, show a horizontal box-strip: central tick, box for the 50% band, whiskers for the 80% band. No fan charts and no density curves in V1.
2. Use the word "central", not "best" or "likely" (EFSA).
3. Give each range one fixed probability label, as a tooltip and on the PDF:
   - Sale: "Middle half of 9 comparable sales (25th-75th percentile)".
   - Cost: "About 8 in 10 projects at feasibility stage finish below the high figure (P80)".
   - Define the low cost margin's percentile in `feasibility_defaults.json`. Today it has none.
4. Add an evidence line under every estimated number, with numbers, never a bare "low confidence":
   - "9 sales within 1.5 mi, Mar 2022-Aug 2026 · Assessor sales, pulled 2026-10-29".
   - When data is thin: "Range widened +10 points each side: 6 permits in this area (needs 10)" and "Search reached 3 mi: range widened".
   - Optional 3-level evidence badge (Strong / Fair / Thin) with its numeric rule shown on hover.
5. Show the scenario table (low/central/high) and a tornado bar of the 5 inputs that move profit most, on the feasibility screen and on the PDF one-pager.
6. Publish an accuracy box on the methods page and on hover: median error, within 10% and 20%, n and refresh date, citywide and for the parcel's community area.

**B. Range math**
1. Replace corner arithmetic with a 10,000-draw Monte Carlo per scenario: split-normal or lognormal cost per stage margin, empirical weighted comp distribution for sale, rank correlation sale↔cost (default 0.3, editable, with 0 as a toggle) using Iman-Conover or a Gaussian copula, and a fixed seed. Report P10/P50/P90 and P(profit < 0) as "share of simulated outcomes", not as a forecast of this deal.
2. Show P50 profit, not central-minus-central. Explain the gap where it matters ("costs run over more often than under").
3. Get max land price P50 and P10 from the same draws. This keeps the spec's "central and low case".
4. Keep the engine as the single source of truth (CLAUDE.md stack note), so the nightly score and live screen share the same draws.
5. Record the distributions and correlation used, in line with the Monte Carlo disclosure guidance, in `feasibility_defaults.json` with source and date.

**C. Score construction**
1. Keep the WLC points form and the user weights. Show the point breakdown on every parcel.
2. Remove double counting: drop or rework `area_sales_12m_above_city_median`. Compute zoning upside and profit from the same by-right scenario, and document that they overlap.
3. Base profit points on the P25 or P10 return on cost, or carry a score range (P10-P90 of score from the same Monte Carlo) and sort on P50. Tag "rank depends on assumptions" when the score's spread across weight samples is high.
4. Copy: "Development score: a sorting aid built from the points shown. It does not rate investment quality." Do not use "best", "top deals" or good/bad colors.

**D. Validation**
1. Run a point-in-time backtest: as-of 2018-2021 snapshots, outcome = new 1-6 unit construction permit within 36 months.
2. Metrics: decile lift, precision@k, AUC, and calibration of profit P50 on sold parcels.
3. Compare against random, zoning-only and vacant-only baselines.
4. Test rank stability under ±50% or Dirichlet weight perturbation.
5. Hold out by time and by community area.
6. Publish results with the caveat that "developed" is not the same as "profitable" or "should build".
7. Store each run's results with a date so later score changes can be compared.

**E. Disclaimers** (draft language for Marlon and counsel to review)
- On every estimate: "Estimate from public records and software. No property was inspected. Not an appraisal, and not zoning, legal, tax or investment advice."
- On the sale value: "Built from N recorded sales of new 2-6 unit buildings near this parcel. It is not an appraisal and can't be used in place of one. Lenders use licensed appraisals for loan decisions."
- In the terms: "Outputs may not be used as the basis for a credit decision or collateral valuation."
- Never use the words appraisal, appraised, certified value, or valuation report.
- Broker use: treat any paid, property-specific value opinion as a BPO under RELA §10-45. Check with counsel.
- Marketing: claim only accuracy figures supported by the dated backtest on file (FTC reasonable basis).

**F. Fairness checks** (Berry, IAAO, Freddie Mac, Brookings)
1. Run leave-one-out sales ratios monthly, by community area, tract racial majority (ACS), search ring and price decile. Report median ratio, COD, PRD and within-10% and within-20% shares against IAAO bands (COD ≤15-20, PRD 0.98-1.03).
2. Run a score distribution audit by community area and racial majority, with and without the location points.
3. Publish both tables. Mark n<6 areas as unmeasured. Widen ranges where measured error is high.
4. Never use race as an input. Use it only in the audit.

### Gaps
- Draft disclaimers need review by an Illinois attorney, especially on publishing (not procuring) an AVM-style estimate and on the brokerage BPO overlap.
- The sale↔cost correlation default (0.3) is an assumption. It needs a Chicago estimate from HPI and PPI history.
- The value of the backtest depends on whether point-in-time zoning and comp data can be rebuilt. This has not been checked.
