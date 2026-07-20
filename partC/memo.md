# Part C: making the assistant sound less like a textbook in six languages

**My call: (a) SFT on synthetic casualized pairs, with (c) prompt-engineering shipped on day 1**, as both the immediate baseline and the safety net if the SFT run doesn't pan out.

Why not (b): a small rewriter model still needs the exact same casualized training data that (a) does, it doesn't save you the hard part, which is generating and validating that data. What it adds instead is a permanent second hop of latency and GPU cost on every production request, plus a new failure mode where the rewriter garbles something the main model already said correctly. Given there's no external API budget and three weeks to launch review, standing up and validating an entirely new serving component is the most expensive way to spend the time we don't have.

## Assumptions I'm making

The load-bearing one: the main model can be prompted to generate its own casualized rewrites of formal responses, well enough to bootstrap a training set. If that's false, most of this plan falls apart, which is exactly why it's the first thing I'd test, not the fifth.

Beyond that, a LoRA pass on a 4-8B model over roughly 100k pairs fits comfortably on one A100-80GB within the two-week window, and the reviewer can get through something like 60 pairs an hour. And I'm assuming, because the constraints say so plainly, that Tamil, Telugu, Bengali, and Marathi have no native reviewer at all. I'm not going to pretend that's a small gap, it's the biggest constraint in this whole memo and it shapes everything below.

## The arithmetic

Six languages at roughly 15k pairs each gets you to about 90k casualized pairs total. Generating those (prompt plus formal response plus generated casual rewrite, call it 2k tokens per pair) is around 180M tokens of self-generation, at a few thousand tokens per second batched on an A100, that's a day or two of compute, nowhere close to using up the two-week allocation. Training a LoRA adapter on those 90k pairs for a few epochs is maybe another day. So the GPU time isn't the bottleneck here, the bottleneck is review capacity.

Ten hours a week at 60 pairs an hour is 600 judged pairs a week, 1,800 over three weeks. That's genuinely enough for a proper 300-pair held-out eval per checkpoint on Hindi and Kannada, with room to iterate two or three times. It is nowhere near enough to human-validate the other four languages, not even close. Those four have to run on automatic checks instead: language-ID confidence, some kind of formality or casualness classifier, back-translation adequacy against the original response, plus a manual spot check after launch rather than before. I want to say this plainly rather than bury it, if someone asks whether we validated Tamil, the honest answer is no, not with a human, and that needs to be said out loud to the product team rather than quietly assumed away.

## What success looks like, with a number

On a held-out 300-prompt Hindi and Kannada set, the SFT checkpoint needs to beat the day-1 prompt-only baseline on casualness at least 70 percent of the time in blind pairwise comparison, while keeping meaning intact (the reviewer judging whether it still says the same thing) on at least 95 percent of pairs.

## When I'd pull the plug

Day 10, a bit past the halfway point of the three weeks, leaving a full week to fall back cleanly instead of scrambling at the deadline. If by then the SFT checkpoint isn't beating the baseline on casualness at least 60 percent of the time, or it's degrading meaning on more than 5 percent of pairs, I'd stop and ship the prompt-only baseline for launch review. That 60 percent threshold is deliberately below the 70 percent bar I actually want, so there's still runway left to fall back gracefully rather than finding out on day 21 that it didn't work.

## What I'd do on day one

Build the prompt-only baseline immediately, it ships regardless of anything else, and in parallel have the main model generate 200 casualized Hindi pairs from its own existing formal responses. Get the reviewer to grade 100 of them that same day, which at the assumed 60 pairs an hour rate is about two hours of their time. That one experiment does three things at once: tests whether the model can actually self-generate usable data in the first place, produces the baseline that ships no matter what, and tells me on day one whether 60 pairs an hour is a realistic number before I've budgeted 1,800 judgments against it. It's the cheapest way I can find to know by day one whether the whole plan is going to work.

## On "there's no single right answer"

If someone weighted the three-week deadline heavier than long-run quality, going with prompt-engineering alone would be a reasonable call, zero training risk, ships immediately. What I don't think is defensible, under any weighting, is a plan that claims to have validated all six languages when the reviewer only covers two, or one that skips the day-1 test and only discovers on day ten that the model can't self-generate usable data in the first place.
