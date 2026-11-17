"""Static HTML report with inline SVG charts.

Dependency-free: charts are hand-rendered SVG (no matplotlib, no JS, no CDN), so
the report is a single self-contained file that renders anywhere. All figures
are computed from the records passed in — nothing is fabricated.
"""

from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

_PRICE_RE = re.compile(r"[-+]?\d*\.?\d+")


def parse_price(value: Any) -> float | None:
    """Extract a float from a price string like ``"£51.77"``; None if absent."""
    if value is None:
        return None
    match = _PRICE_RE.search(str(value))
    return float(match.group()) if match else None


def _counts(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    c = Counter(str(r.get(field)) for r in records if r.get(field) is not None)
    return dict(sorted(c.items(), key=lambda kv: kv[0]))


def _avg_price_by(records: list[dict[str, Any]], field: str) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in records:
        price = parse_price(r.get("price"))
        key = r.get(field)
        if price is not None and key is not None:
            buckets[str(key)].append(price)
    return {k: round(mean(v), 2) for k, v in sorted(buckets.items())}


def compute_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate records into the figures the report renders."""
    prices = [p for p in (parse_price(r.get("price")) for r in records) if p is not None]
    return {
        "total": len(records),
        "price_min": round(min(prices), 2) if prices else None,
        "price_max": round(max(prices), 2) if prices else None,
        "price_avg": round(mean(prices), 2) if prices else None,
        "by_category": _counts(records, "category"),
        "by_rating": _counts(records, "rating"),
        "by_availability": _counts(records, "availability"),
        "avg_price_by_category": _avg_price_by(records, "category"),
    }


def _svg_bar_chart(data: dict[str, float], *, title: str, unit: str = "") -> str:
    """Render a vertical bar chart as inline SVG. Empty data -> a note."""
    if not data:
        return f'<div class="chart"><h3>{html.escape(title)}</h3><p class="muted">No data.</p></div>'

    width, height = 420, 240
    pad_left, pad_bottom, pad_top = 36, 48, 16
    plot_w = width - pad_left - 16
    plot_h = height - pad_bottom - pad_top
    n = len(data)
    gap = 14
    bar_w = max(8, (plot_w - gap * (n + 1)) / n)
    max_val = max(data.values()) or 1

    bars: list[str] = []
    x = pad_left + gap
    for label, value in data.items():
        bar_h = (value / max_val) * plot_h
        y = pad_top + (plot_h - bar_h)
        cx = x + bar_w / 2
        val_label = f"{value:g}{unit}"
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
            f'rx="3" fill="#38bdf8"><title>{html.escape(label)}: {val_label}</title></rect>'
            f'<text x="{cx:.1f}" y="{y - 5:.1f}" text-anchor="middle" '
            f'class="val">{html.escape(val_label)}</text>'
            f'<text x="{cx:.1f}" y="{height - pad_bottom + 16:.1f}" text-anchor="middle" '
            f'class="lab">{html.escape(label)}</text>'
        )
        x += bar_w + gap

    axis = (
        f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - 16}" '
        f'y2="{pad_top + plot_h}" stroke="#334155" />'
    )
    return (
        f'<div class="chart"><h3>{html.escape(title)}</h3>'
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{html.escape(title)}">{axis}{"".join(bars)}</svg></div>'
    )


def render_report(records: list[dict[str, Any]], *, title: str = "SentinelScrape Report") -> str:
    """Return a complete, self-contained HTML report string for ``records``."""
    stats = compute_stats(records)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def stat_card(label: str, value: Any) -> str:
        shown = "—" if value is None else html.escape(str(value))
        return f'<div class="card"><div class="num">{shown}</div><div class="cap">{html.escape(label)}</div></div>'

    cards = "".join(
        [
            stat_card("Records", stats["total"]),
            stat_card("Min price", f'£{stats["price_min"]}' if stats["price_min"] is not None else None),
            stat_card("Avg price", f'£{stats["price_avg"]}' if stats["price_avg"] is not None else None),
            stat_card("Max price", f'£{stats["price_max"]}' if stats["price_max"] is not None else None),
        ]
    )

    charts = "".join(
        [
            _svg_bar_chart(dict(stats["by_category"]), title="Records by category"),
            _svg_bar_chart(dict(stats["avg_price_by_category"]), title="Avg price by category", unit=""),
            _svg_bar_chart(dict(stats["by_rating"]), title="Records by rating (stars)"),
            _svg_bar_chart(dict(stats["by_availability"]), title="Records by availability"),
        ]
    )

    rows = "".join(
        "<tr>"
        f'<td>{html.escape(str(r.get("title", "")))}</td>'
        f'<td>{html.escape(str(r.get("category", "")))}</td>'
        f'<td>{html.escape(str(r.get("price", "")))}</td>'
        f'<td>{html.escape(str(r.get("rating", "")))}</td>'
        f'<td>{html.escape(str(r.get("availability", "")))}</td>'
        "</tr>"
        for r in records
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #0f172a; color: #e2e8f0;
         font: 15px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 32px 16px; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
  .muted {{ color: #94a3b8; }}
  .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; }}
  .num {{ font-size: 1.5rem; font-weight: 700; color: #38bdf8; }}
  .cap {{ color: #94a3b8; font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; }}
  .charts {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
  .chart {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 12px 16px; }}
  .chart h3 {{ margin: 0 0 8px; font-size: .95rem; }}
  svg {{ width: 100%; height: auto; }}
  .val {{ fill: #e2e8f0; font-size: 11px; }}
  .lab {{ fill: #94a3b8; font-size: 11px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 24px; font-size: .9rem; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #334155; }}
  th {{ color: #94a3b8; text-transform: uppercase; font-size: .72rem; letter-spacing: .05em; }}
  @media (max-width: 680px) {{ .cards, .charts {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>{html.escape(title)}</h1>
    <p class="muted">Generated {generated} · {stats["total"]} records · all figures computed from collected data.</p>
    <div class="cards">{cards}</div>
    <div class="charts">{charts}</div>
    <h2>Records</h2>
    <table>
      <thead><tr><th>Title</th><th>Category</th><th>Price</th><th>Rating</th><th>Availability</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</body>
</html>
"""


def write_report(records: Iterable[dict[str, Any]], path: str, *, title: str = "SentinelScrape Report") -> int:
    """Write an HTML report to ``path``; returns the number of records included."""
    records = list(records)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(records, title=title), encoding="utf-8")
    return len(records)
