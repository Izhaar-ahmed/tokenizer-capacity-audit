# Part A, tokenizer audit

Covers A1-A4 (50 pts).

## What's in here

- `given/`: the original files, untouched, `fertility.py`, the 10-sentence toy corpora, `REPORT_v0.md`. Kept around so there's always a clean diff against the original and so nothing here depends on files outside this folder.
- `corpus/`: the real eval corpus I built for A1 (6 languages), plus `PROVENANCE.md` explaining where it came from and where it falls short.
- `tok_common.py`: the tokenizer loader both scripts share (its docstring explains the network access workaround, and how to swap in a proper Indic-aware tokenizer once that's not an issue).
- `bug_isolation.py`: A2, reproduces the original script's numbers, then isolates each bug one at a time.
- `corrected_analysis.py`: A3, the corrected comparison, two tokenizers, four denominators.
- `RESULTS.md`: the actual write-up of A2 and A3, with the reasoning behind each claim.
- `memo.md`: A4, the recommendation memo.

## How to run

```
pip install tiktoken regex sentencepiece
# tiktoken needs network access to fetch the gpt2 vocab; if that's blocked,
# pip install openai-whisper instead (see tok_common.py docstring)
python3 bug_isolation.py
python3 corrected_analysis.py
```

Both scripts use paths relative to their own location, so they'll run from anywhere, and they produce exactly the tables quoted in `RESULTS.md`, nothing there is hand-typed.
