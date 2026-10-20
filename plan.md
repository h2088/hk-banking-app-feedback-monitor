# SC Mobile Hong Kong Customer Feedback Intelligence — Execution Plan

**Task deadline:** 2026-10-25 (end of day)  
**Scope:** SC Mobile Hong Kong vs. competitor mobile banking apps (starting with HSBC HK Mobile Banking)  
**Period:** Previous six months, with exact dates documented in the final deliverable  
**Deliverable:** A self-contained web app or HTML report documenting comments, analysis, and trends

## 1. Objective and decision questions

Build a reproducible customer-feedback monitoring prototype that answers:

1. What are customers praising or complaining about in SC Mobile Hong Kong?
2. How have review volume, star ratings, sentiment, and major themes changed over the six-month period?
3. How does SC Mobile compare with HSBC HK Mobile Banking on comparable sources and time windows?
4. Which issues are most severe, increasing, or actionable for the product team?
5. What evidence supports each finding, and where are the data gaps?

## 2. Source and collection strategy

### Primary sources
- Apple App Store reviews for the Hong Kong listings of SC Mobile and the competitor app.
- Google Play reviews for the Hong Kong listings of both apps.
- Public social channels/search results mentioning the apps or relevant product names, where accessible and attributable.

### Collection rules
- Record source URL, app/product, review ID if available, date, rating if available, text, language, and collection timestamp.
- Use public, permitted access methods and respect platform terms, rate limits, and privacy expectations.
- Do not collect personal account details or infer customer identity.
- Do not treat search snippets as a complete social-media dataset.
- If a source cannot be reliably accessed, document the limitation and do not fabricate replacement records.

## 3. Data model and quality checks

Create a normalized table with fields such as:
`source`, `app`, `review_id`, `review_date`, `rating`, `text`, `language`, `collected_at`, `url`, `is_duplicate`, `analysis_eligible`.

Checks:
- Six-month date-window validation.
- Missing date/text/rating checks.
- Duplicate detection across source IDs and normalized text.
- App identity and Hong Kong market verification.
- Language detection and handling of English, Traditional Chinese, and other observed languages.
- Sampling and coverage report by app, source, month, language, and rating.
- Keep raw data immutable; store cleaned/derived data separately.

## 4. Analysis plan

### Descriptive metrics
- Review/comment volume by week or month.
- Average rating and rating distribution, where ratings exist.
- Sentiment distribution and trend.
- Theme/topic volume and trend.
- Source, language, and app coverage.

### Text analytics
- Multilingual preprocessing appropriate for English and Traditional Chinese.
- Sentiment classification with documented method and a manually checked validation sample.
- Theme taxonomy developed from observed comments; candidate themes may include login/authentication, registration, transfers/payments, card controls, app stability/performance, biometrics, usability/navigation, customer support, and security. Do not force a theme when evidence is insufficient.
- Severity/actionability tags based on explicit evidence, not sentiment alone.
- Representative anonymized quotations with source/date references.

### Competitive benchmarking
- Compare the same six-month window and equivalent sources where possible.
- Show source coverage and sample sizes beside every comparison.
- Avoid interpreting differences as statistically meaningful when samples are small or collection methods differ.
- Distinguish app-store ratings from social-media sentiment; do not merge them without explanation.

## 5. Validation and evidence checks

- Manually inspect a stratified sample of classified comments across app, source, language, rating, and month.
- Check sentiment/theme label errors and revise rules or model prompts.
- Verify that trend charts use the intended date window and correct denominators.
- Trace every key insight to example comments and source links.
- Label observations, interpretations, and recommendations separately.
- Clearly label any illustrative/demo data; never present synthetic data as actual customer feedback.

## 6. Web app / HTML design

Recommended sections:
1. **Executive summary** — 3–5 evidence-backed findings and priority actions.
2. **Data coverage** — sources, collection window, sample sizes, gaps, and limitations.
3. **Trend monitor** — volume, ratings, sentiment, and theme trends.
4. **Voice of customer** — searchable/filterable comments with source, date, rating, sentiment, and theme.
5. **Competitor benchmark** — side-by-side comparison with coverage caveats.
6. **Priority issues** — impact/evidence/trajectory and suggested next action.
7. **Methodology & limitations** — collection approach, definitions, validation, and known blind spots.

The deliverable should be self-contained where practical, work locally in a browser, and include a clear “last updated” timestamp.

## 7. Acceptance criteria

Final review on 2026-10-19 applies these criteria to the user's narrowed scope: English app-store comments, SC versus HSBC, overall app-level reporting. Sections 1–6 retain the original design intent; checking the items below does not certify all original extensions. See [Checkpoint F](checkpoint_F_final_review.md) for evidence and qualified acceptance.

- [x] Scope and exact six-month dates are stated; latest observed English review is 2026-10-16, not the 2026-10-19 as-of date.
- [x] SC Mobile and the named HSBC benchmark are included.
- [x] Each collected source's availability and coverage are documented; social sources remain excluded.
- [x] Raw/cleaned data distinction and quality checks are documented; original and derived data hashes are intact.
- [x] Displayed monthly trends and overall comparisons use traceable, consistent denominators; no per-theme monthly trend is claimed.
- [x] Classifications have a documented method and 10-row plausibility spot-check; this is not an accuracy evaluation.
- [x] Key insights link back to saved evidence; current live source-page visibility was not revalidated in F.
- [x] Limitations and inaccessible or excluded sources are explicit.
- [x] Source records are retained without synthetic replacements; report rows trace back to the saved source exports.
- [x] HTML opens and renders in a clean local desktop Edge profile; broader browser/device compatibility is not certified.
- [x] Final deliverable and [handover notes](handover.md) are ready on 2026-10-19, before 2026-10-25 EOD; no external submission has been made.

## 8. Work sequence and checkpoints

### Checkpoint A — Source feasibility
Verify official app listings, available review endpoints/pages, date coverage, and public social search access. Record source URLs and limitations before committing to a collection method.

### Checkpoint B — Data collection
Collect a defensible sample for both apps and platforms, preserving source/date/rating metadata. If six-month complete coverage is not feasible, disclose actual coverage and avoid implying completeness.

### Checkpoint C — Data QA
Run duplicate, date, missingness, app identity, language, and sample-size checks. Produce a coverage table.

### Checkpoint D — Analysis
Generate descriptive trends, sentiment/theme labels, benchmark comparisons, and a manually reviewed validation sample.

### Checkpoint E — Build and test
Create the HTML/web app, validate chart calculations and filters, verify evidence links, and test in a clean browser.

### Checkpoint F — Final review
Check factual claims, limitations, visual clarity, file portability, and submission-ready handover.

## 9. Risk register

| Risk | Mitigation |
|---|---|
| Reviews are not fully accessible by date | Document coverage; use permitted APIs or accessible public pages; do not claim completeness |
| Social platforms restrict search/access | Use accessible public results and label them as a non-exhaustive sample |
| English/Cantonese/Traditional Chinese classification errors | Use language-aware processing and manually inspect a stratified sample |
| Competitor sources differ in coverage | Compare matched sources/windows and show sample sizes |
| Small or biased samples distort trends | Include denominators and caution labels; avoid overclaiming |
| Time constraint | Prioritize reliable app-store review evidence, then add social coverage where feasible |
| Sensitive information appears in comments | Avoid collecting personal identifiers; redact sensitive details in displayed examples |

## 10. Final deliverables

- `plan.md` — this plan.
- Data coverage / QA summary.
- Self-contained HTML report or web app.
- Methodology and limitations section.
- Brief handover note explaining how to open the deliverable and interpret the findings.

## 11. Current execution status — 2026-10-19

The active reporting scope follows the user's later instructions: English customer comments only, SC Mobile as the primary app, HSBC as benchmark, and overall app-level reporting without Google Play / Apple App Store metric splits. Source fields and raw evidence remain in the underlying project for traceability. Social-media collection and multilingual reporting are not part of this iteration.

- Checkpoints A–C: completed; see the corresponding checkpoint documents.
- Checkpoint D: first descriptive analysis completed; rating-derived sentiment and conservative multi-label theme rules, with a small documented spot-check.
- Checkpoint E: build and desktop test completed. See [checkpoint_E_build_test.md](checkpoint_E_build_test.md) and [the offline HTML report](report_customer_feedback_2026-10-19.html). All 311 records are browsable; 12 integrity tests and 1,398 browser assertions passed. These are software checks, not classification accuracy estimates.
- Checkpoint F: completed for the current scope. See [checkpoint_F_final_review.md](checkpoint_F_final_review.md), [handover.md](handover.md) and [final review results](data/checkpoint_F_review_2026-10-19/final_review_results.json). The 12 static tests were rerun and passed; all 9 final-review check groups passed, including 30 existing artifact hashes and 311 source-row mappings. The unchanged HTML retains E's browser-test hash, so the browser test was not rerun in F.

Current deliverable: a static, offline-readable customer-feedback monitoring snapshot with traceable data and qualified descriptive benchmarking. No recrawl, source-text change, relabeling or HTML rebuild occurred in F. Earlier checkpoint handoff statements describe their stage at the time; F records final acceptance. The project is ready for user review and submission within this scope, not a certification of the original broader scope or an automated production monitoring service.
