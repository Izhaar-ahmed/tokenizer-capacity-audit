# A4: recommendation memo

**To:** Leadership
**Re:** Correcting REPORT_v0's tokenizer numbers before they drive a capacity decision

## What the numbers actually say

Under the tokenizer we're currently serving with, Indic content costs 6.9x to 15.9x English per equivalent request, not the flat 6x the report recommended. Hindi comes in at 6.9x, Telugu 10.6x, Kannada 13.7x, Malayalam 13.8x, and Tamil 15.9x. That's tokens per parallel sentence, i.e. what it actually costs to say the same thing in each language, which is the number that maps to real serving cost (full reasoning in `RESULTS.md`).

The bigger finding, honestly, isn't the multiplier, it's that the multiplier isn't fixed. Swap in a tokenizer that's actually seen these languages during training and the same comparison drops to roughly 4.7x to 8.0x across the board. That's a bigger lever than any routing decision we could make.

## What I'd do

Don't adopt a flat 6x budget for Indic traffic, it under-provisions Tamil, Kannada, and Malayalam and over-provisions Hindi. Before locking in a number, I'd rerun this on FLORES-200 (I used a smaller corpus for this pass, see the caveat below) and I'd push on evaluating a tokenizer swap before a routing scheme, since it's the bigger lever. If routing has to happen in the meantime, budget per language from the ratios above, not one number for all of them.

## The thing I'd flag hardest

I built this eval corpus out of OPUS-100, mostly movie subtitles and forum text, not FLORES-200, because I hit some access issues pulling FLORES-200 directly. That's documented in `corpus/PROVENANCE.md`, along with a second caveat worth mentioning here directly: for Telugu specifically, which I can read myself, a real chunk of the surviving translations after filtering still read like rough machine translation rather than natural sentences. That's a quality problem on top of the domain mismatch, and I only caught it because I happen to speak the language, which makes me suspicious that similar quality issues exist in the other languages too, I just can't personally verify them.

The direction of every finding here held up across two independently trained tokenizers and got more, not less, pronounced as I grew the corpus. I'm confident in the direction. I'd want the exact numbers reconfirmed against FLORES-200 before they go into a capacity plan, both because subtitle text runs shorter and more colloquial than production traffic, and because FLORES is professionally translated rather than scraped.

## What I'd watch in production

Tokens per request (or tokens per character of response), broken out by detected input language. If the real-world Hindi/English or Tamil/English ratio starts drifting more than about 20% from what's in `RESULTS.md`, that's the signal this whole analysis needs to be redone, probably because of code-mixing, romanized input, or a model or tokenizer change that wasn't accounted for here.
