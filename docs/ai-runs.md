# AI runs

One row per paid model run: date, task, model, rows, tokens in/out, cost, who approved.

| Date | Task | Model | Rows | Tokens in / out | Cost | Approved |
|---|---|---|---|---|---|---|
| 2026-11-01 | Rezoning districts from ordinance scans (`jobs/extract_rezoning_districts.py`), 50-row check, batch `msgbatch_01E4Aiu8P6CAcBL5rWuBnNnH` | claude-haiku-5-5 (Batch, thinking off, effort low, JSON schema) | 50 | 158,623 / 6,172 (cache 0 / 0) | $0.01 | Marlon, 2026-11-01 ("go for it all"; cap $5) |
| 2026-11-01 | Same job, full run, batch `msgbatch_014khqohrSDrK81oRKxBp8ti` | claude-haiku-5-5 (Batch, thinking off, effort low, JSON schema) | 6,653 | 22,540,942 / 845,501 (cache 0 / 0) | $1.34 | Marlon, 2026-11-01 (estimate $1.34 measured with count_tokens before submit) |

Notes on the 2026-11-01 rezoning run:
- No prompt cache: the shared prompt is about 450 tokens, under the 512-token minimum, and each scan is sent once, so the Files API does not apply.
- 6,727 ordinances listed, 6,703 with a readable PDF; 0 failed requests; 28 answered `readable: false`.
- Spot check: 20 of the 50 check rows read by hand against the scan or its OCR text, 20 right (one skipped an RT-4 to RT-4 piece of a four-district ordinance).
- Free cross-checks on the full run: the new district from Section 1's OCR text ("to those of a ...") matches one of the model's changes in 4,025 of 4,065 rows (99.0%); the application's present/proposed district (Q9) matches in 596 of 605 rows. The repeat error is OCR "Cl-1" or "Bl-3" read as B1-1 or B3-1.
- 282 rows (4.2%) carry `needs_check = True` (invalid code, low confidence, unreadable, or a cross-check mismatch) and should be checked by hand before they reach a screen.
