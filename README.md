# The Audit, my submission

Layout follows what the assignment doc asks for:

```
NOTEBOOK.md          # chronological lab notebook (hypothesis -> experiment -> result -> revision, incl. dead ends)
AI_USAGE.md           # honest AI-usage summary
partA/                # A1-A4: tokenizer audit, code, corpus, corrected analysis, memo
partB/                # B1-B4: capacity reconciliation, code, calculations, written answers
partC/memo.md         # C: decision memo
```

## Scoring map

| component | pts | where |
|---|---|---|
| A1 corpus construction and caveats | 10 | `partA/corpus/PROVENANCE.md` |
| A2 script and metric audit (evidence rule) | 20 | `partA/RESULTS.md` (plus `partA/bug_isolation.py`) |
| A3 corrected analysis and denominator reasoning | 12 | `partA/RESULTS.md` (plus `partA/corrected_analysis.py`) |
| A4 recommendation memo | 8 | `partA/memo.md` |
| B1-B4 capacity reconciliation | 20 | `partB/ANSWERS.md` (plus `partB/partB_check.py`) |
| C decision memo | 15 | `partC/memo.md` |
| Defense | 15 | live session |

## Quick start

```
pip install tiktoken regex sentencepiece   # partA
python3 partA/bug_isolation.py
python3 partA/corrected_analysis.py
python3 partB/partB_check.py               # stdlib only
```

Every number in `RESULTS.md`, `ANSWERS.md`, and the memos came out of running these, nothing's typed in by hand.
