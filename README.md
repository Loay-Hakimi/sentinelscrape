<div align="center">

# 📊 SentinelScrape
### Advanced Stealth Scraper & Market Intelligence Core

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![MarTech](https://img.shields.io/badge/Domain-MarTech%20%2F%20DataOps-8B5CF6?style=for-the-badge)](https://github.com)
[![Security](https://img.shields.io/badge/Encryption-AES--256-EF4444?style=for-the-badge&logo=shield)](https://github.com)
[![Status](https://img.shields.io/badge/Status-Active-22C55E?style=for-the-badge)](https://github.com)

> A production-grade Python intelligence tool that collects, encrypts, and stores competitive market data using **stealth scraping techniques** — combining cybersecurity principles with data-driven marketing (MarTech) to build a fully automated, privacy-respecting market intelligence pipeline.

---

[Features](#-features) · [Architecture](#-system-architecture) · [Installation](#-installation) · [Usage](#-usage) · [Data Pipeline](#-data-pipeline) · [Ethics & Compliance](#-ethics--compliance)

</div>

---

## 🎯 Overview

**SentinelScrape** sits at the intersection of **cybersecurity** and **data-driven marketing**. It is designed for market researchers, growth engineers, and MarTech professionals who need reliable, structured competitive data — collected responsibly and stored securely.

| Capability | Description |
|-----------|-------------|
| 🕵️ **Stealth Collection** | Proxy & User-Agent rotation with Gaussian jitter delays |
| 🔐 **Encrypted Storage** | Fernet (default) or optional AES-256-GCM on every stored record |
| 🗄️ **Structured Database** | SQLite backend with content-hash deduplication (PostgreSQL: roadmap) |
| 📈 **MarTech Ready** | Export to CSV or JSON (direct BI feed: roadmap) |
| ⚙️ **Fully Configurable** | YAML-driven pipeline — no code changes for new targets |

---

## ✨ Features

### 🕵️ Stealth Scraping Engine
- **Proxy Rotation** — Cycles through a configurable proxy pool to distribute requests and avoid IP-based blocking
- **User-Agent Spoofing** — Rotates browser fingerprints from a curated database of real browser signatures
- **Jitter Delays** — Randomized, human-like timing between requests using Gaussian distribution
- **Session Persistence** — Maintains cookie sessions across request batches to mimic real user behavior
- **Retry Logic** — Exponential backoff with configurable retry limits on failed requests

### 🔐 Encrypted Data Pipeline
- All harvested data is encrypted immediately on collection using **Fernet (AES-128-CBC + HMAC-SHA256)**
- Optional **AES-256-GCM** mode for enterprise-grade storage requirements
- Encryption keys stored separately from the database — never hardcoded
- Decryption utility included for authorized data retrieval

### 🗄️ Secure Database Layer
- SQLite backend (stdlib `sqlite3`); PostgreSQL is on the roadmap
- Automatic deduplication on insert via a `UNIQUE` content-hash constraint
- Timestamped records with source URL, scrape session ID, and data hash
- Query/export interface for decryption and reporting

### 📊 Market Intelligence Outputs
- **Competitor Price Tracking** — Monitor pricing changes across e-commerce targets
- **SEO Signal Harvesting** — Extract meta tags, headings, structured data, and keyword density
- **Content Velocity Monitoring** — Track how frequently competitors publish and update content
- **Social Proof Aggregation** — Collect ratings, review counts, and engagement signals

### 🔧 Modular Pipeline Architecture
- Each stage (fetch → parse → encrypt → store → export) is an independent, swappable module
- Static HTML scraping via `requests` + BeautifulSoup, with an injectable HTTP
  transport (so the engine runs fully offline in tests)
- CSS-selector parsing with per-field attribute extraction (`selector@attr`) and
  optional item-scoped extraction

---

## 🏗️ System Architecture

```
sentinelscrape/
│
├── core/
│   ├── scraper_engine.py       # Request orchestration, robots.txt, retries, pagination
│   ├── stealth_manager.py      # Proxy rotation, UA rotation, Gaussian jitter
│   └── parser.py               # HTML extraction with CSS selectors (+ @attr support)
│
├── security/
│   ├── encryptor.py            # Fernet (default) + optional AES-256-GCM engine
│   ├── key_vault.py            # Key storage, creation & rotation
│   └── decryptor.py            # Authorized retrieval & key-rotation re-encryption
│
├── storage/
│   ├── db_manager.py           # SQLite interface (stdlib sqlite3)
│   ├── schema.sql              # Database schema
│   └── deduplicator.py         # SHA-256 content-hash deduplication
│
├── exporters/
│   ├── csv_exporter.py         # Flat-file export for spreadsheet tools
│   └── json_exporter.py        # Structured JSON output
│
├── config/
│   ├── targets.yaml            # Scrape targets & selector definitions
│   └── settings.yaml           # Global pipeline settings (incl. proxy pool)
│
├── tests/                      # Offline unit + integration tests (pytest)
├── benchmarks/
│   └── benchmark.py            # Reproducible local performance measurements
│
├── main.py                     # CLI entrypoint (scrape / export / targets)
└── requirements.txt
```

### 🔄 Data Flow

```
  [ Target URL List ]
         │
         ▼
  [ Stealth Manager ]
  Proxy + UA + Jitter
         │
         ▼
  [ Scraper Engine ]
  Fetch → Parse → Validate
         │
         ▼
  [ Encryptor ]
  AES-256 / Fernet
         │
         ▼
  [ Database Layer ]
  Deduplicate → Store
         │
         ▼
  [ Exporter ]
  CSV / JSON / BI Feed
```

---

## 🚀 Installation

### Prerequisites

- Python `3.10+`
- pip

### Clone & Install

```bash
git clone https://github.com/Loay-Hakimi/sentinelscrape.git
cd sentinelscrape

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Dependencies

```txt
requests>=2.31.0          # HTTP client
beautifulsoup4>=4.12.0    # HTML parsing
cryptography>=41.0.0      # Fernet / AES-256-GCM encryption
pyyaml>=6.0               # Config parsing
tenacity>=8.2.0           # Retry logic with exponential backoff
```

> Storage uses the Python standard library's `sqlite3` (no ORM dependency), and
> User-Agent rotation uses a small curated in-repo pool (no third-party UA
> database). Playwright-based JS rendering and a PostgreSQL backend are on the
> roadmap, not in this release — see [Roadmap](#-roadmap).

---

## ⚙️ Configuration

### `config/targets.yaml`

```yaml
targets:
  - name: "books_demo"
    url: "https://books.toscrape.com/"
    # Optional: treat each matching element as one record; fields are extracted
    # within it. Omit to zip each field's matches positionally.
    item_selector: "article.product_pod"
    selectors:
      title: "h3 a@title"          # "@attr" extracts an attribute instead of text
      price: "p.price_color"
      availability: "p.availability"
      url: "h3 a@href"
    pagination:
      type: "next_button"
      selector: "li.next a"
      max_pages: 3
```

### `config/settings.yaml`

```yaml
stealth:
  proxy_rotation: true
  ua_rotation: true
  jitter_min_ms: 800
  jitter_max_ms: 3500
  respect_robots: true
  max_retries: 3

encryption:
  algorithm: "fernet"          # Options: fernet, aes256gcm
  key_path: ".secrets/key.key" # Never commit this file (gitignored)

database:
  path: "./data/sentinel.db"

proxies: []                    # e.g. ["http://user:pass@host:port", ...]
```

---

## 🖥️ Usage

### List Configured Targets

```bash
python main.py targets
```

### Run a Scrape Job

```bash
python main.py scrape --target books_demo --pages 2
```

```
[SentinelScrape] scraping target 'books_demo' ...
[SentinelScrape] session 2cedab441b56: 40 scraped | 40 stored | 0 duplicates | 40 total in db
```

### Decrypt & Export Data

```bash
python main.py export --format csv --out exports/books.csv
python main.py export --format json --out exports/books.json
```

> Scheduling (cron-style recurring jobs) is on the roadmap — for now, schedule
> `main.py scrape` with your OS scheduler (cron, Task Scheduler, systemd timer).

---

## 📈 MarTech Integration Use Cases

| Use Case | How SentinelScrape Helps |
|---------|--------------------------|
| **Price Intelligence** | Track competitor pricing daily, trigger alerts on changes |
| **SEO Competitive Analysis** | Harvest keyword usage, meta strategies, content structure |
| **Content Gap Analysis** | Monitor competitor publishing frequency and topics |
| **Ad Copy Research** | Collect landing page copy and CTA patterns at scale |
| **Review Sentiment** | Aggregate customer reviews for NLP sentiment analysis |

---

## 🔐 Security Design

### Key Management
- Encryption keys are generated on first run and stored in `.secrets/` (gitignored)
- Key rotation supported without data loss — re-encryption utility included
- Environment variable support for CI/CD deployments: `SENTINEL_KEY`

### Data Handling
- Raw HTML is never persisted — only structured records
- Each record's payload is **encrypted at the field/record level** before it
  touches disk (authenticated Fernet or AES-256-GCM). Note: this is per-record
  payload encryption, **not** whole-file database encryption — clear-text
  metadata (session id, source URL, content hash, timestamp) is kept for
  querying and deduplication

---

## 📊 Performance Benchmarks

All numbers below are **real measurements** of the local processing pipeline,
produced by `python benchmarks/benchmark.py`. Full output and notes are in
[`benchmarks/RESULTS.md`](benchmarks/RESULTS.md).

Measured on: **Python 3.14.6, win32**. These exclude network throughput, which
is governed by the configured jitter/rate-limit delays and the target server —
not by this code.

| Metric | Result |
|--------|--------|
| Fernet encrypt per record | **37.7 µs** (~0.04 ms) |
| Encrypt+decrypt round-trip per record | **69.9 µs** |
| Pure crypto+hash processing rate | **~26,000 records/sec** |
| Storage throughput (durable commit-per-insert) | **~85 records/sec** |
| Exact-duplicate detection accuracy | **100%** (2000/2000 caught) |
| Peak Python heap (1k records, tracemalloc) | **~1.0 MB** |

> **Honest caveats:** storage throughput is `fsync`-bound because every row is
> committed individually for durability — the crypto/hash cost is ~0.04 ms, so
> batching commits would raise this substantially. Deduplication is
> deterministic (SHA-256 + `UNIQUE` constraint), so "100%" means exact-duplicate
> detection by construction — no fuzzy/near-duplicate matching is claimed.

---

## 🧪 Testing

The full suite runs **offline** — the scraper engine's HTTP transport is
injectable, so no network access is required.

```bash
pip install pytest
pytest -q          # 34 tests: security, storage, stealth, parser, engine, pipeline
```

---

## 🗺️ Roadmap

Not yet implemented in this release:

- [ ] Playwright support for JavaScript-rendered pages
- [ ] PostgreSQL storage backend
- [ ] Batched inserts (`insert_batch`) to lift the fsync-bound storage ceiling
- [ ] Built-in scheduler (cron-style recurring jobs)
- [ ] Direct BI feed exporters (Metabase / Grafana)
- [ ] Residential proxy pool integration (Bright Data / Oxylabs API)
- [ ] Slack / webhook alerts on price change detection
- [ ] REST API layer for querying the encrypted database

---

## ⚖️ Ethics & Compliance

> SentinelScrape is designed for **ethical, responsible data collection**.

- ✅ Respects `robots.txt` directives by default (configurable)
- ✅ Implements rate limiting to avoid server load impact
- ✅ Intended for collecting **publicly available** information only
- ✅ Not designed for bypassing authentication or accessing private data
- ✅ Users are responsible for ensuring compliance with the Terms of Service of any target website and applicable data protection laws (GDPR, CCPA, etc.)

The stealth techniques implemented are standard industry practices used by tools like Scrapy, Apify, and commercial market intelligence platforms. They exist to handle dynamic rate limiting on public-facing pages — not to circumvent security controls on protected systems.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built at the intersection of 🔐 **Cybersecurity** and 📈 **Data-Driven Marketing**

**[⭐ Star this repo](https://github.com/Loay-Hakimi/sentinelscrape)** · **[Connect on LinkedIn](https://linkedin.com)**

</div>
