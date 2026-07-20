# AI usage

I used Claude for this, agentically, writing code, running it, fetching data, not just as a chat assistant I copy pasted from. Here's where it actually helped and where it got things wrong, as honestly as I can put it.

## Where it helped

Most of the scaffolding code, the tokenizer loader, the bug isolation script, the corrected analysis script, the KV cache math script, got written from me describing what each experiment needed to isolate. That was genuinely faster than typing out the tokenizer loading boilerplate myself, especially once it turned out direct downloads from HuggingFace and tiktoken's servers were blocked and I needed a fallback path.

It's also the one that found that the `openai-whisper` PyPI package happens to bundle the exact GPT-2 BPE rank table as one of its assets, which is what got me past the download block. I didn't know that package shipped those files. I didn't just take that on faith either, checked the vocab size and spot checked a handful of token IDs against what `tiktoken`'s public gpt2 encoding actually produces before trusting it for anything.

Same story with finding a working real corpus source, several FLORES-200 mirrors turned out to be dead ends before landing on OPUS-100 through HuggingFace's datasets-server API, which actually returns usable per language rows. That took a few wrong turns, documented in the notebook, not a clean first try.

It also drafted the first version of the results writeups and the memos from whatever the scripts had already produced. I rewrote a fair amount of that, mostly places where the first draft stated something more confidently than the actual numbers supported, and later a full pass to strip out a writing tic (overusing em dashes) that made the whole thing read like it came out of a template rather than a person.

## Where it got things wrong, or I got things wrong following it

The KV cache calculation used 24 attention heads on the first pass, the Q head count from the spec, instead of the 8 KV heads that actually matter under grouped query attention. That gave a wrong prediction for how many sequences fit in memory. Only caught it because the number didn't line up with the log, went back to the spec, and noticed it lists Q heads and KV heads as two separate numbers for exactly this reason. I made a point of actually understanding why it's 8 and not 24, not just plugging in the number that happened to match afterward, because this is exactly the kind of thing that'd get asked live.

The lowercasing bug is the other one worth being honest about. Going in, the assumption was that lowercasing would make the English/Hindi ratio look smaller than it should. That's backwards, lowercasing actually inflates the English token count (you lose GPT-2's learned merges for capitalized forms) and does nothing to Hindi, so the bug understates the true ratio, not overstates it. I only trust that because I reran the isolation script myself and read the actual per language token counts, rather than accepting whatever explanation sounded right first.

The first corpus pull was small, a dozen or two sentences for Tamil and Kannada, and for a bit I was fine treating that as good enough, the direction is already clear. Went back and pushed for more data anyway, because a memo recommending an actual cost multiplier shouldn't rest on 12 sentences, even if the conclusion doesn't end up changing once the sample grows.

One thing I want to be specific about since it's the part I actually caught myself, not the AI: the first pass at the Telugu corpus was assembled the same way as every other language, filter out obvious junk, keep the rest. Since Telugu is my first language, I went back and actually read every line in `tel.tsv` myself, and a chunk of what survived the automated filtering is still bad Telugu, scrambled word order, words run together where they shouldn't be. That's not something an automated pipeline (or an AI that doesn't read Telugu at native level) would reliably catch, it took someone who actually speaks the language sitting down and reading each line. I added that as its own caveat in `corpus/PROVENANCE.md` rather than quietly cleaning the file further, because it's a real limitation of scraped bitext that I don't think most people auditing a language they don't speak would ever notice.

Also worth mentioning, at one point I tried to parallelize the FLORES-200 search by handing part of it off, and that run hit a limit partway through and stopped. Nothing was lost, I just had to pick it back up and finish it myself, but it's a decent reminder that an agent saying something is handled isn't the same as checking that it actually is.

## What I made sure I actually own

Which flaws in the script count as code bugs versus the conceptual issue versus the things that just look suspicious but aren't, that's my call, and I can defend why NFC normalization and the unused random seed genuinely aren't bugs, not just that a script told me they aren't. Same for why the GQA head count matters, not just that 8 is the right number. Same for the Part C recommendation, the Telugu translation quality read, and every number quoted in the memos, checked against actual script output or my own reading before it went into a document, not taken on faith from a first draft.
