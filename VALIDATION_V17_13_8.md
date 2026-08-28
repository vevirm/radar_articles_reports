# Validation V17.13.8

Checks performed:
- Stuff page loads the same `radar.json` and Matrix classifier as the main Matrix;
- live Matrix slice export supports all / row / column / exact cell;
- packaged XLSX contains START, Matrix_All, 4 row sheets, 4 column sheets, 16 cell sheets, Literature and Important;
- current Matrix distribution remains 3/6/1/1, 2/1/7/7, 6/5/8/2, 1/7/2/3;
- priority-publication ranking is an attention aid only and does not change admission;
- primary/official EU sources receive ranking priority over secondary reporting when present;
- reader navigation exposes Stuff as a utility page;
- black / white / red palette retained;
- package remains at or below 100 files.


## V17.13.9 source-bound consequence checks

- `RadarInsights.whyFor()` derives displayed consequences from the individual record rather than broad topic templates.
- The two reported generic phrases are absent from the runtime fallback path.
- Empty source-bound consequences are omitted in the main Radar instead of filled with generic text.
- Reader consequence outputs are checked for complete sentence punctuation, explicit starts and <=120 characters.
- Presentation smoke remains network-free.

Runtime reader-copy check on the current 240 A/B/C records:
- 187 records produce a source-bound separate “why it matters”.
- 53 records omit the line because the saved source text does not support a separate safe consequence.
- 0 displayed consequences use the two reported generic fallback sentences.
- 0 displayed consequences fail the explicit-start / complete-sentence / 120-character check.
- Maximum displayed consequence length: 120 characters.

Focused regression tests: 20 passed (`test_v17_13_1_subject_language_easy_view.py` + `test_v17_13_0_feedback_round.py`). Presentation smoke passed. The repository-wide pytest collection still hits the existing `tests/test_findings.py` import of `make_finding`, which is not exported by the packaged scanner; that unrelated legacy collection issue was not changed in this reader-copy patch.
