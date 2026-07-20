"""A2 bug isolation: reproduce v0 numbers, then toggle one fix at a time.

Variants:
  v0            : exactly what fertility.py does (lower + split(" ") + macro avg)
  fix_split     : split() instead of split(" ")           [empty-string words]
  fix_lower     : don't lowercase                          [cased BPE distortion]
  fix_avg       : micro average (corpus totals) not macro  [line-weighting]
  all_fixed     : all three fixes
Red-herring checks:
  NFC on/off, random.seed presence (never used -> zero effect by inspection)
"""
import os, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tok_common import enc

HERE = os.path.dirname(os.path.abspath(__file__))
GIVEN = os.path.join(HERE, "given")
encode = enc("gpt2").encode

def read_lines(path, nfc=True):
    out = []
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if line:
            out.append(unicodedata.normalize("NFC", line) if nfc else line)
    return out

def analyze(lines, *, lower=True, split_fixed=False, micro=False, nfc_lines=None):
    fert, tpc = [], []
    tot_tok = tot_w = tot_c = 0
    for line in lines:
        if lower:
            line = line.lower()
        tokens = encode(line)
        words = line.split() if split_fixed else line.split(" ")
        chars = len(line)
        fert.append(len(tokens) / len(words))
        tpc.append(len(tokens) / chars)
        tot_tok += len(tokens); tot_w += len(words); tot_c += chars
    if micro:
        return tot_tok / tot_w, tot_tok / tot_c
    return sum(fert) / len(fert), sum(tpc) / len(tpc)

def show(tag, kw):
    e = analyze(eng, **kw); h = analyze(hin, **kw)
    print(f"{tag:<12} eng {e[0]:6.3f} tok/w {e[1]:6.4f} tok/c | "
          f"hin {h[0]:6.3f} tok/w {h[1]:6.4f} tok/c | ratio {h[0]/e[0]:5.2f}x")

eng = read_lines(f"{GIVEN}/corpus_sample/eng_sample.txt")
hin = read_lines(f"{GIVEN}/corpus_sample/hin_sample.txt")

print("== one-at-a-time (vs v0) ==")
show("v0", dict())
show("fix_split", dict(split_fixed=True))
show("fix_lower", dict(lower=False))
show("fix_avg", dict(micro=True))
show("all_fixed", dict(split_fixed=True, lower=False, micro=True))

print("\n== red herring: NFC off (v0 otherwise) ==")
eng_r = read_lines(f"{GIVEN}/corpus_sample/eng_sample.txt", nfc=False)
hin_r = read_lines(f"{GIVEN}/corpus_sample/hin_sample.txt", nfc=False)
e = analyze(eng_r); h = analyze(hin_r)
print(f"no-NFC       eng {e[0]:6.3f} tok/w | hin {h[0]:6.3f} tok/w | ratio {h[0]/e[0]:5.2f}x")
raw_h = [r.rstrip("\n") for r in open(f"{GIVEN}/corpus_sample/hin_sample.txt") if r.strip()]
changed = sum(unicodedata.normalize("NFC", l) != l for l in raw_h)
print(f"hin lines altered by NFC: {changed}/{len(raw_h)}")

print("\n== per-line word-count check for split(' ') ==")
for name, lines in (("eng", eng), ("hin", hin)):
    for i, l in enumerate(lines):
        a, b = len(l.split(" ")), len(l.split())
        if a != b:
            print(f"{name} line {i+1}: split(' ')={a} vs split()={b} -> {l[:50]!r}")

print("\n== lowercase effect on tokens, per language ==")
for name, lines in (("eng", eng), ("hin", hin)):
    t_low = sum(len(encode(l.lower())) for l in lines)
    t_raw = sum(len(encode(l)) for l in lines)
    print(f"{name}: tokens raw={t_raw} lowered={t_low} delta={t_low - t_raw:+d}")
