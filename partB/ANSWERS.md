# B1-B4

Everything here is straight from `partB_check.py`, run it, don't take my word for the arithmetic.

## B1: KV-cache bytes per token, and how many sequences fit

From `given/model_spec.md`: 28 layers, 8 KV heads, head_dim 128, fp16 everywhere. I want to flag the one place this is easy to get wrong: the spec lists 24 attention heads and 8 KV heads separately, because this model uses grouped-query attention, so the KV cache is sized by the 8, not the 24. I actually used 24 on my first pass through this and only caught it because the predicted capacity didn't line up with the log at all. More on that in a second.

Bytes per token = 2 (one for K, one for V) x 28 layers x 8 KV heads x 128 head_dim x 2 bytes for fp16 = 114,688 bytes = 112 KiB per token.

For the memory budget: `gpu_memory_utilization` gives us 0.92 of the 24 GiB card, so 22.08 GiB. Take out the weights (4.2B params x 2 bytes = 8.4 GB) and the stated 1.6 GiB of runtime overhead, and there's about 12.66 GiB left over for the KV cache.

A full 4096-token sequence needs 112 KiB x 4096 = 0.438 GiB, so 12.66 divided by 0.438 works out to roughly 29 concurrent sequences.

Checking that against the actual log: in the long-prompt sweep, `batch_size / kv_cache_util` sits at 25.0 to 25.8 across every row that isn't already thrashing (batch 24 at 0.93 util implies a capacity of 25.8, for instance). My estimate says about 29, the log says about 26, off by roughly 10 percent. That gap is believable, real serving stacks allocate KV cache in fixed-size blocks rather than exact byte counts, so there's always a bit of waste from internal fragmentation, and the spec's 1.6 GiB overhead figure is probably a rough number rather than exact. I'm not chasing an exact match here, getting within 10 percent of the empirical number from pure arithmetic is the actual point.

## B2: the throughput cliff

Long-prompt sweep, where goodput = batch times 512 generated tokens divided by wall clock:

| batch | kv_util | preempted | goodput (tok/s) | ttft p50 (ms) | e2e p95 (s) |
|---|---|---|---|---|---|
| 16 | 0.62 | 0 | 163.9 | 498 | 54.6 |
| 24 | 0.93 | 0 | 200.9 | 500 | 69.2 |
| 32 | 0.97 | 7 | 173.0 | 637 | 97.5 |
| 48 | 0.97 | 23 | 162.3 | 955 | 105.4 |

Throughput peaks at batch 24 and then goes down, which shouldn't happen if you believe more batch always means more throughput.

Here's why: batch 24 is already close to filling the KV cache (0.93 util, and B1 says the real ceiling is around 26 sequences). Push past that, batch 32, batch 48, and there's simply nowhere for the extra sequences' KV cache to live, so the scheduler starts preempting running sequences to free up room. That's 7 preemptions at batch 32 and 23 at batch 48. A preempted sequence loses its progress and has to redo prefill when it comes back, which is wasted work on top of everything else. You can see the cache pinned at 0.97, not just busy, genuinely full, while wall clock nearly triples going from batch 24 to batch 48, for only twice the requests, and both TTFT and p95 latency blow up along with it. More requests "in flight" doesn't mean more throughput once you're past the wall.

For a fix, I'd pick one of these two, and be ready to defend either.

Cap concurrency at 24. Run two back-to-back batch-24 requests instead of one batch-48 request, and you get roughly double the goodput of a single batch-24 run (2 x 200.9 is about 402 tok/s equivalent over about 122s) against the observed single batch-48 run's 162.3 tok/s over 151s, call it a 24 percent improvement, plus admitted requests see roughly 500ms TTFT instead of 955ms.

Or quantize the KV cache to fp8. That halves the per-token footprint to 56 KiB, roughly doubling capacity to about 52 sequences, which would let batch 48 run without hitting the preemption wall at all. Extrapolating the pre-cliff trend (163.9 at batch 16, 200.9 at batch 24) suggests something north of 300 tok/s at batch 48 once it's not thrashing, roughly an 85 percent jump over what's observed now, assuming output quality holds up under fp8, which would need its own check.

## B3: the column that's been misread

`reported_tok_s` counts prompt tokens and generated tokens together, not just what actually gets delivered to a user. I proved this the boring way: `n * (prompt_len + gen_len) / wall_clock` reproduces the reported number on every single row in the log, to within 0.1 percent. Batch 16 on the long-prompt row, for instance: 16 x 4096 divided by 49.97 gives 1311.5, and the log says 1311.4.

That one fact takes down both of the report's Section 2 claims at once.

"Longer prompts give better throughput" isn't true. 1311 vs 883 tok/s at batch 16 is just the counter picking up 7x more prompt tokens per request (3584 vs 512) going through prefill, it has nothing to do with generation speed. If you look at goodput instead, tokens actually generated per second, which is what a user experiences as response speed, short prompts win: 294.5 tok/s vs 163.9 at the same batch size.

"Batch 48 will deliver around 3200 tok/s" is also false, and for two separate reasons. It's a straight line extrapolation off the best observed reported number (1607 at batch 24), which already double counts prefill, and batch 48 is past the capacity cliff from B2, where throughput drops rather than rises. The real reported number at batch 48 is 1298.5, and the honest goodput is 162.3 tok/s, roughly 20x below the report's extrapolation.

For the batch-24 long-prompt row, I got the honest goodput two independent ways and they agree. From totals: 24 requests x 512 tokens divided by 61.16s gives 200.9 tok/s. From inter-token latency: 24 sequences x 1000ms divided by 96.07ms p50 ITL gives 249.8 tok/s during the decode phase specifically (this one leaves out the roughly 10 seconds of prefill at the start, which is why it comes out a bit higher). Both numbers are correct, they're just describing different phases of the same run, end-to-end delivery is around 200 tok/s, decode phase only is around 250 tok/s.

What the report should have said: the harness counts total tokens processed, not tokens delivered, so under a correct reading, longer prompts reduce delivered throughput, and end-to-end throughput actually peaks around batch 24, right where the cache is nearly full but not yet forcing preemptions, and gets worse from there. Batch 48 delivers about 20 percent less than batch 24, not double.

## B4: what I'd check to confirm this

Pull the serving stack's preemption counter, in vLLM this is the "sequences preempted" log line or `num_preemptions`, read next to `gpu_cache_usage_perc` (this log's `kv_cache_util`). I'd expect zero preemptions up through roughly batch 24 to 26, then a jump to non-zero right as `gpu_cache_usage_perc` pins near 0.97 to 1.0, matching the 7 and 23 preemptions already visible at batch 32 and 48. If the stack separately tracks prefill vs decode token throughput, I'd also expect to see those two lines cross right around the same batch size where preemptions start, prefill throughput still climbing, decode throughput starting to fall.
