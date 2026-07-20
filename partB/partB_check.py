"""Part B verification: KV-cache math + bench_log cross-checks.

Run: python3 partB_check.py  (stdlib only, no dependencies)
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# --- B1: KV bytes/token from model_spec.md ---
layers, kv_heads, head_dim, fp16 = 28, 8, 128, 2
kv_per_tok = 2 * layers * kv_heads * head_dim * fp16  # K and V
print(f"KV bytes/token = 2*{layers}*{kv_heads}*{head_dim}*{fp16} = {kv_per_tok} B "
      f"= {kv_per_tok/1024:.0f} KiB")

gpu = 24 * 1024**3 * 0.92          # gpu_memory_utilization budget
weights = 4.2e9 * 2                # fp16
overhead = 1.6 * 1024**3
kv_budget = gpu - weights - overhead
seq_bytes = kv_per_tok * 4096
print(f"budget for KV = 24GiB*0.92 - 8.4GB weights - 1.6GiB overhead "
      f"= {kv_budget/1024**3:.2f} GiB")
print(f"per 4096-tok seq = {seq_bytes/1024**3:.3f} GiB "
      f"-> max concurrent = {kv_budget/seq_bytes:.1f}")

# --- check against log ---
rows = list(csv.DictReader(open(
    os.path.join(HERE, "given", "bench_log.csv"))))
print("\nlog cross-checks (long-prompt sweep, 3584+512=4096 tok/seq):")
print(f"{'bs':>3}{'kv_util':>8}{'implied capacity bs/util':>26}"
      f"{'rep_tok/s':>10}{'goodput=bs*512/wall':>20}{'goodput from ITL':>17}{'preempt':>8}")
for r in rows:
    if r["prompt_len"] != "3584":
        continue
    bs = int(r["batch_size"]); util = float(r["kv_cache_util"])
    wall = float(r["wall_clock_s"])
    good = bs * 512 / wall
    itl = float(r["itl_ms_p50"])
    good_itl = bs * 1000 / itl  # decode-phase only, ignores prefill
    print(f"{bs:>3}{util:>8}{bs/util:>26.1f}{r['reported_tok_s']:>10}"
          f"{good:>20.1f}{good_itl:>17.1f}{r['preempted_seqs']:>8}")

print("\nreported_tok_s reconstruction (proof it counts prompt tokens):")
for r in rows:
    n = int(r["num_requests"]); p = int(r["prompt_len"]); g = int(r["gen_len"])
    wall = float(r["wall_clock_s"])
    pred = n * (p + g) / wall
    print(f"bs={r['batch_size']:>3} p={p} rep={r['reported_tok_s']:>7} "
          f"n*(p+g)/wall={pred:7.1f}  gen-only={n*g/wall:6.1f}")

# arithmetic-intensity sanity: decode is bandwidth-bound
bw = 300e9
w = 4.2e9 * 2
print(f"\nbandwidth ceiling, weights only: {bw/w:.0f} tok/s per forward pass "
      f"(x batch for total decode tok/s, ignoring KV reads)")
