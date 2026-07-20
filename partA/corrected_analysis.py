"""A3 corrected analysis.

Tokenizers: gpt2 (exact GPT-2 BPE) and whisper-multilingual (a genuinely
multilingual byte-BPE), plus a tiny SentencePiece BPE trained on the Hindi
side itself as a third data point (demonstrates that fertility is a
property of the tokenizer's training data, not the script -- see caveat
in its printed output).

For your submission, swap in a real Indic-aware subword tokenizer once you
have normal internet access, e.g. ai4bharat/IndicBERTv2 or sarvamai/sarvam-1
via `transformers.AutoTokenizer` (see tok_common.py docstring).

Denominators: whitespace word, grapheme cluster, UTF-8 byte, and parallel
sentence (tokens vs. English tokens for the same content). No lowercasing.
Micro-averaged corpus totals (see A2 for why that matters).

Run: python3 corrected_analysis.py
Requires: pip install regex sentencepiece (+ tiktoken, or openai-whisper as
a fallback -- see tok_common.py)
"""
import os, sys, unicodedata
import regex  # \X = extended grapheme cluster
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tok_common import enc

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus")
GIVEN = os.path.join(HERE, "given")
LANGS = ["hin", "tam", "kan", "tel", "mal"]


def load(lang):
    pairs = []
    for line in open(f"{CORPUS}/{lang}.tsv", encoding="utf-8"):
        line = line.rstrip("\n")
        if not line:
            continue
        en, xx = line.split("\t")
        pairs.append((unicodedata.normalize("NFC", en),
                      unicodedata.normalize("NFC", xx)))
    return pairs


def stats(texts, encode):
    tok = sum(len(encode(t)) for t in texts)
    words = sum(len(t.split()) for t in texts)
    graph = sum(len(regex.findall(r"\X", t)) for t in texts)
    byts = sum(len(t.encode("utf-8")) for t in texts)
    return tok, words, graph, byts


def report(name, encode):
    print(f"\n--- tokenizer: {name} ---")
    print(f"{'lang':<5}{'n':>4}{'tok/word':>10}{'tok/graph':>11}"
          f"{'tok/byte':>10}{'tok/par.sent (xx/en)':>22}")
    for lang in LANGS:
        pairs = load(lang)
        en_texts = [p[0] for p in pairs]
        xx_texts = [p[1] for p in pairs]
        et, _, _, _ = stats(en_texts, encode)
        xt, xw, xg, xb = stats(xx_texts, encode)
        print(f"{lang:<5}{len(pairs):>4}{xt/xw:>10.2f}{xt/xg:>11.3f}"
              f"{xt/xb:>10.3f}{xt/et:>22.2f}")
    # english reference row (english side of the hin.tsv pairs)
    pairs = load("hin")
    en_texts = [p[0] for p in pairs]
    et, ew, eg, eb = stats(en_texts, encode)
    print(f"{'eng':<5}{len(pairs):>4}{et/ew:>10.2f}{et/eg:>11.3f}"
          f"{et/eb:>10.3f}{'1.00 (def)':>22}")


report("gpt2", enc("gpt2").encode)
report("whisper-multilingual", enc("multilingual").encode)

# SentencePiece BPE trained on the Hindi side only (tiny, demo).
import sentencepiece as spm
import tempfile

with tempfile.TemporaryDirectory() as td:
    hin_txt = os.path.join(td, "hin_train.txt")
    with open(hin_txt, "w", encoding="utf-8") as f:
        for _, xx in load("hin"):
            f.write(xx + "\n")
        sample_path = os.path.join(GIVEN, "corpus_sample", "hin_sample.txt")
        if os.path.exists(sample_path):
            for l in open(sample_path, encoding="utf-8"):
                f.write(l)
    model_prefix = os.path.join(td, "sp_hin")
    spm.SentencePieceTrainer.train(
        input=hin_txt, model_prefix=model_prefix,
        vocab_size=400, model_type="bpe", character_coverage=1.0)
    sp = spm.SentencePieceProcessor(model_file=model_prefix + ".model")
    pairs = load("hin")
    xt, xw, xg, xb = stats([p[1] for p in pairs], sp.encode)
    print("\n--- tokenizer: SP-BPE trained on the Hindi corpus itself (vocab 400) ---")
    print(f"hin  tok/word {xt/xw:.2f}  tok/graph {xt/xg:.3f}  tok/byte {xt/xb:.3f}")
    print("(demo only: trained ON the eval text, so it overfits; the point is "
          "direction -- a tokenizer trained on the target language always beats "
          "one that never saw it -- not the exact value.)")
