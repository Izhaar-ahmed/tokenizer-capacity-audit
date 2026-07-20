# A2 + A3: what's actually wrong with fertility.py, and the corrected numbers

Everything below comes straight out of `bug_isolation.py` and `corrected_analysis.py`. If a number looks wrong, run the script, that's the whole point of this exercise.

## A2: auditing the script

First thing I did was just run `given/fertility.py` unmodified, to make sure I was auditing the same numbers the report quotes. Got eng 1.265 tok/word, hin 7.448, ratio 5.89x. Matches `REPORT_v0.md` exactly, so that's my baseline for everything below.

I'm arguing three code bugs and one conceptual problem here, not a longer list of half-confident maybes. Better to defend a handful of things properly than pad the list.

**Bug 1: `line.split(" ")` instead of `line.split()`.**

Splitting on a literal single space means two consecutive spaces produce an empty string that still counts as a word. It quietly inflates the word count and deflates fertility. Both toy corpora have a double space planted in them for exactly this reason (eng sample line 7, "books  in the cupboard"; hindi sample line 10, "किताबें  अलमारी"). Checked it directly: `split(" ")` on line 7 gives 8 words, `split()` gives 7. Fixing just this one thing moves the ratio from 5.89x to 5.92x. Not a huge move on a 10 line toy corpus, but real corpora carry a lot more whitespace noise than this, tabs, non breaking spaces, double spaces from copy paste, and `split(" ")` breaks on all of them.

**Bug 2: `line.lower()` before tokenizing.**

This is the one I actually got wrong on my first guess, so it's worth walking through honestly. My assumption going in was that lowercasing would make the English/Hindi ratio look worse than it should, since lowercasing throws away information and I figured it'd hurt English more. I was wrong. GPT-2's BPE vocabulary has separate learned merges for capitalized and lowercase versions of common words, so lowercasing English text actually increases its token count in a lot of cases, you lose the merge built around the capitalized form and fall back to smaller pieces. Devanagari has no case at all, so lowercasing does nothing to Hindi. I measured it directly: lowering added 3 tokens to the English toy corpus (96 to 99) and changed exactly zero for Hindi. So this bug doesn't make the report's number look worse, it makes it look better than it actually is. Fixing just this one thing moves the ratio from 5.89x to 6.06x. The comment in the script itself ("so casing doesn't add noise to the comparison") has the direction backwards; production traffic isn't lowercased, so the lowered measurement is the one adding noise, not removing it.

**Bug 3: averaging per-line ratios instead of averaging corpus totals.**

`analyze()` computes tokens/words separately for each line and then averages those ratios across lines. That's the wrong kind of average. A 3-word line and a 40-word line end up counting equally toward the final number, when the 40-word line obviously represents a lot more of the corpus's actual content. The correct way to aggregate is to sum tokens and words separately across the whole corpus first, then divide once (a micro-average), not average a bunch of small per-line ratios (a macro-average). These give the same answer only when every line is the same length, which real text never is.

On this 10-line toy corpus the two conventions are close because the sample lines happen to be fairly uniform in length, so fixing it alone only moves the ratio from 5.89x to 5.91x. I don't want to oversell that as a dramatic finding, it isn't, on this corpus. But I think it's still worth arguing properly rather than waving it away, because the size of the bias scales directly with how much line-length variance a corpus has, and production traffic (a two-word reply next to a three-paragraph explanation) has a lot more variance than ten sample sentences. I switched to totals-based averaging in `corrected_analysis.py` for exactly this reason, it's the version of the calculation that stays correct once you're not dealing with a toy corpus anymore.

With all three fixes applied together, the ratio on the toy corpus comes out to roughly 6.0x to 6.1x depending on exact ordering, barely different from where v0 started. Worth being upfront about that: the code bugs mostly offset each other and don't move the headline number much in either direction on this small sample. The real distortion isn't in the code at all, it's in what the metric is measuring in the first place, which is the next section.

### The conceptual problem

This is the part that actually matters, and it isn't a coding mistake, the script computes tokens-per-whitespace-word exactly as intended. The problem is that tokens-per-word isn't a meaningful thing to compare across languages in the first place.

A word doesn't carry the same amount of information in every language. Hindi packs more into a word than English does through agglutination, and the Dravidian languages (Tamil, Kannada, Telugu, Malayalam) go further still, a single word in these languages routinely does the work of three or four separate English words (a verb stem plus tense, person, and case markers all attached). So tok/word is quietly measuring two different things at once: how well the tokenizer handles the script, and how the language's grammar happens to chunk words. Those get mixed into one number and you can't tell which one is actually driving it.

tok/byte and tok/grapheme are cleaner because they don't depend on word boundaries at all, but they're still tangled up with the script itself. A Devanagari or Telugu character costs about three bytes in UTF-8 versus one for plain ASCII, so even a perfect tokenizer would show a higher tok/byte number for Hindi than English on structural grounds alone. The only denominator that actually holds meaning constant is the parallel sentence: how many tokens it takes to say the same thing, tok(target) divided by tok(english) on aligned text. That's the number that should drive a routing decision, because it tracks what you're actually paying for, tokens per unit of content delivered to a user, not tokens per some language-specific counting convention.

Two more things wrong with the report's reasoning that I'd argue alongside the denominator issue, since "at least one" conceptual problem doesn't mean there's only one:

The report treats tok/word and tok/char agreeing as evidence the result is robust. It isn't, they're computed from the same token count on the same corpus, so of course they move together, that's not independent confirmation of anything. And they don't even actually agree in the strict sense: 7.0x and 5.89x are called "confirming" each other when they're just two different numbers in the same rough range.

And the claim that "any tokenizer will struggle, it's a property of the script" is a testable statement, and it's false. GPT-2's BPE was trained almost entirely on English web text, so it never learned useful merges for Devanagari or the Dravidian scripts and mostly falls back to encoding them byte by byte. I checked this directly: Tamil comes out at 0.996 tokens per byte under gpt2, essentially one token per byte, which is the textbook signature of byte level fallback. Swap in a tokenizer that was actually trained on multilingual text (I used Whisper's multilingual byte-BPE as a stand in) and Tamil's per-sentence ratio drops from 15.92x to 4.89x. That's not a property of the Tamil script, that's a property of what the tokenizer saw during training.

### Things that look like bugs but aren't

The assignment specifically asks for at least one thing that looks suspicious but is actually fine, so here it is: `unicodedata.normalize("NFC", line)`. This is good practice, not a bug. NFC normalization makes sure visually identical Unicode sequences (this matters a lot for Devanagari, where the same character can be represented as either one composed codepoint or a base character plus a combining mark) get collapsed to one canonical form before tokenizing, so you don't get silently different token counts depending on which encoding the source text happened to use. I checked whether it actually changes anything on the sample corpus, it doesn't, zero of the ten Hindi lines are altered by it, because the file was already normalized. That's expected, the value of NFC shows up on messier real world corpora pulled from multiple sources, not on a clean 10-line toy file. Point is, I looked, and it's not doing anything wrong here or anywhere I checked.

One more thing that's trivially not a bug, `random.seed(1337)` at the top of the file. `random` is never called anywhere else in the script, grep for it and you'll only find the import and the seed line. It's dead code, probably left over from an earlier version that did sampling. Nothing to isolate here because there's nothing for it to affect.

## A3: the corrected analysis

Same corpus (see `corpus/PROVENANCE.md`), two tokenizers, four denominators, all three fixes from A2 applied (real `split()`, no lowercasing, totals not per-line averages).

**gpt2**, the tokenizer the report used:

| lang | n | tok/word | tok/grapheme | tok/byte | tok/parallel-sentence |
|---|---|---|---|---|---|
| eng | 68 | 1.23 | 0.230 | 0.230 | 1.00 (ref) |
| hin | 68 | 7.03 | 2.220 | 0.590 | 6.94 |
| tam | 41 | 24.93 | 4.184 | 0.996 | 15.92 |
| kan | 8 | 21.41 | 3.778 | 0.966 | 13.69 |
| tel | 34 | 17.43 | 4.300 | 0.984 | 10.56 |
| mal | 39 | 24.82 | 5.359 | 0.988 | 13.80 |

**whisper-multilingual**, an actually multilingual byte-BPE:

| lang | n | tok/word | tok/grapheme | tok/byte | tok/parallel-sentence |
|---|---|---|---|---|---|
| eng | 68 | 1.25 | 0.234 | 0.233 | 1.00 (ref) |
| hin | 68 | 4.88 | 1.541 | 0.410 | 4.74 |
| tam | 41 | 7.93 | 1.330 | 0.317 | 4.89 |
| kan | 8 | 13.54 | 2.389 | 0.611 | 8.00 |
| tel | 34 | 11.99 | 2.957 | 0.677 | 7.23 |
| mal | 39 | 19.36 | 4.179 | 0.770 | 10.67 |

A couple of things I'd actually defend from this table, not everything in it:

The report's "budget 6x for Hindi" undersells the real problem. Tamil is 15.9x under gpt2, not 6x, so a flat 6x multiplier would leave Tamil, Kannada, Telugu, and Malayalam badly under-provisioned. But the bigger issue is that the whole "pick a multiplier" framing is wrong, because the ratio isn't fixed, it's a property of which tokenizer you're serving with, and that single lever moves Tamil from 15.9x down to 4.9x, a bigger swing than any traffic-routing scheme could produce.

If I had to pick one number for a leadership deck, it's tokens-per-parallel-sentence, under whichever tokenizer is actually in production. It's the one denominator that holds the content being communicated constant, which is what actually determines compute, KV-cache footprint, and latency per request. Word counts and byte counts both move around for reasons that have nothing to do with what's actually being said.

I also trained a tiny SentencePiece model directly on the Hindi text, see the script output, which gets Hindi down to 1.96 tok/word. That's overfit and not a fair benchmark since it trained on the exact eval sentences, but it's a decent sanity check from a third angle: any tokenizer that's actually seen the target language does dramatically better than one that hasn't.

One more note specific to Telugu, since it's the language I know well enough to actually read the translations rather than just trust the pairing. Going through `corpus/tel.tsv` line by line, a good chunk of the surviving pairs still read like rough machine translation even after I'd already filtered out the obvious junk (UI strings, translator credits, and so on). Some examples that made it through the filter but are genuinely awkward Telugu: "నేను మేము అధిక పాఠశాల లో మహిళలు తో వెళ్లండి ఉపయోగించారు ఎలా చెప్పాడు" (word order is scrambled, "నేను మేము" puts "I" and "we" next to each other, which doesn't happen in natural Telugu), and "అడవియొక్కనిశ్శబ్దం అధిగమించేఇదిఅన్నిప్రారంభమైంది ఒకతెలియనిశబ్దం" where the words are run together without proper spacing, clearly a tokenization artifact from whatever produced this bitext rather than something a person actually wrote. I left these in rather than quietly deleting them, because they're a real, checkable example of a caveat the assignment asks for directly: this corpus can tell you the tokenizer's fertility on the text as given, but it can't tell you whether that text is itself natural language, and for Telugu specifically I can say with some confidence that a meaningful fraction of it isn't. More on this in `corpus/PROVENANCE.md`.
