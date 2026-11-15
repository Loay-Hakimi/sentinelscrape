"""Measure SentinelScrape's real, local performance characteristics.

These are deterministic, network-free measurements of the processing pipeline
(encryption, hashing, SQLite storage, deduplication). They deliberately exclude
network throughput, which is dominated by the configured jitter/rate-limit
delays and the target server, not by this code.

Run:  python benchmarks/benchmark.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.encryptor import Encryptor  # noqa: E402
from storage.db_manager import DBManager  # noqa: E402
from storage.deduplicator import record_hash  # noqa: E402

SAMPLE = {
    "title": "The Great Example: A Story of Benchmarks",
    "price": "£42.99",
    "availability": "In stock (19 available)",
    "rating": "Four",
    "url": "https://example-store.com/catalogue/the-great-example/index.html",
}


def bench_encryption(iterations: int = 20_000) -> dict[str, float]:
    enc = Encryptor(Encryptor.generate_key())
    # Encrypt-only
    start = time.perf_counter()
    tokens = [enc.encrypt_record(SAMPLE) for _ in range(iterations)]
    enc_elapsed = time.perf_counter() - start
    # Decrypt-only
    start = time.perf_counter()
    for t in tokens:
        enc.decrypt_record(t)
    dec_elapsed = time.perf_counter() - start
    return {
        "encrypt_us": enc_elapsed / iterations * 1e6,
        "decrypt_us": dec_elapsed / iterations * 1e6,
        "roundtrip_us": (enc_elapsed + dec_elapsed) / iterations * 1e6,
        "iterations": iterations,
    }


def bench_storage_throughput(count: int = 3_000) -> dict[str, float]:
    enc = Encryptor(Encryptor.generate_key())
    with tempfile.TemporaryDirectory() as d:
        db = DBManager(os.path.join(d, "bench.db"), enc)
        start = time.perf_counter()
        for i in range(count):
            db.insert("bench", "http://x", {"i": i, **SAMPLE})
        elapsed = time.perf_counter() - start
        total = db.count()
        db.close()
    return {
        "records": count,
        "stored": total,
        "seconds": elapsed,
        "records_per_sec": count / elapsed,
    }


def bench_dedup_accuracy() -> dict[str, float]:
    enc = Encryptor(Encryptor.generate_key())
    with tempfile.TemporaryDirectory() as d:
        db = DBManager(os.path.join(d, "dedup.db"), enc)
        unique = [{"i": i, **SAMPLE} for i in range(2000)]
        records = unique + unique  # every record duplicated exactly once
        inserted, duplicates = db.insert_many("s", "http://x", records)
        stored = db.count()
        db.close()
    return {
        "input": len(records),
        "unique_expected": len(unique),
        "inserted": inserted,
        "duplicates_detected": duplicates,
        "stored": stored,
        "accuracy_pct": 100.0 * (1 if stored == len(unique) and duplicates == len(unique) else 0),
    }


def bench_memory() -> dict[str, float]:
    enc = Encryptor(Encryptor.generate_key())
    tracemalloc.start()
    with tempfile.TemporaryDirectory() as d:
        db = DBManager(os.path.join(d, "mem.db"), enc)
        for i in range(1000):
            db.insert("s", "http://x", {"i": i, **SAMPLE})
        db.fetch_decrypted("s")
        _, peak = tracemalloc.get_traced_memory()
        db.close()
    tracemalloc.stop()
    return {"peak_mb": peak / (1024 * 1024)}


def main() -> None:
    enc = bench_encryption()
    store = bench_storage_throughput()
    dedup = bench_dedup_accuracy()
    mem = bench_memory()

    print("# SentinelScrape benchmark results\n")
    print(f"- Date: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    print(f"- Python: {sys.version.split()[0]} on {sys.platform}")
    print(f"- Scope: local processing pipeline (network excluded)\n")

    print("| Metric | Result |")
    print("|--------|--------|")
    print(f"| Encryption (Fernet) encrypt per record | {enc['encrypt_us']:.1f} µs |")
    print(f"| Encryption (Fernet) decrypt per record | {enc['decrypt_us']:.1f} µs |")
    print(f"| Encrypt+decrypt round-trip per record | {enc['roundtrip_us']:.1f} µs |")
    print(f"| Storage throughput (encrypt+hash+durable commit-per-insert) | ~{store['records_per_sec']:.0f} records/sec |")
    print(f"| Exact-duplicate detection accuracy | {dedup['accuracy_pct']:.0f}% ({dedup['duplicates_detected']}/{dedup['unique_expected']} dupes caught) |")
    print(f"| Peak Python heap (1k records, tracemalloc) | ~{mem['peak_mb']:.1f} MB |")


if __name__ == "__main__":
    main()
