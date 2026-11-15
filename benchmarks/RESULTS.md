# SentinelScrape benchmark results

All numbers below are **real measurements** of the local processing pipeline,
produced by `python benchmarks/benchmark.py`. They deliberately **exclude
network throughput**, which is governed by the configured jitter/rate-limit
delays and the target server — not by this code.

## Environment

- Date: 2026-11-15
- Python: 3.14.6 on win32
- Scope: local processing pipeline (network excluded)

## Results

| Metric | Result |
|--------|--------|
| Fernet encrypt per record | 37.7 µs |
| Fernet decrypt per record | 32.2 µs |
| Encrypt+decrypt round-trip per record | 69.9 µs |
| Pure crypto+hash processing rate | ~26,000 records/sec |
| Storage throughput (encrypt+hash+**durable commit-per-insert**) | ~85 records/sec |
| Exact-duplicate detection accuracy | 100% (2000/2000 duplicates caught) |
| Peak Python heap (1k records, tracemalloc) | ~1.0 MB |

## Notes

- **Encryption is cheap** (~0.04 ms/record) — far below a human-perceptible
  cost and well within any scraping budget.
- **Storage throughput is fsync-bound.** `DBManager.insert` commits after every
  row for durability, so ~85 rows/sec reflects per-insert `COMMIT` cost on this
  machine, not the crypto/hash cost. Batching commits (a future `insert_batch`)
  would raise this by orders of magnitude; durability-per-row is the current
  deliberate default.
- **Deduplication is deterministic**, not probabilistic: identical record
  content yields an identical SHA-256, enforced by a `UNIQUE` constraint, so
  exact-duplicate detection is 100% by construction (no fuzzy/near-duplicate
  matching is claimed).
