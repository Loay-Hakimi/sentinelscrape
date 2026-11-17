"""Tests for the offline demo pipeline and the HTML report generator."""

from __future__ import annotations

from demo_pipeline import run_demo
from reports.html_report import compute_stats, parse_price, render_report


def test_parse_price():
    assert parse_price("£51.77") == 51.77
    assert parse_price("45.17") == 45.17
    assert parse_price("free") is None
    assert parse_price(None) is None


def test_compute_stats():
    records = [
        {"category": "Fiction", "price": "£10.00", "rating": "3", "availability": "In stock"},
        {"category": "Fiction", "price": "£20.00", "rating": "5", "availability": "Out of stock"},
        {"category": "Sci-Fi", "price": "£30.00", "rating": "5", "availability": "In stock"},
    ]
    stats = compute_stats(records)
    assert stats["total"] == 3
    assert stats["price_min"] == 10.0
    assert stats["price_max"] == 30.0
    assert stats["price_avg"] == 20.0
    assert stats["by_category"] == {"Fiction": 2, "Sci-Fi": 1}
    assert stats["avg_price_by_category"]["Fiction"] == 15.0
    assert stats["by_rating"] == {"3": 1, "5": 2}


def test_render_report_contains_data():
    records = [{"title": "T1", "category": "Fiction", "price": "£10.00", "rating": "3", "availability": "In stock"}]
    html = render_report(records, title="Unit Test Report")
    assert "<!doctype html>" in html
    assert "Unit Test Report" in html
    assert "<svg" in html  # charts rendered
    assert "Fiction" in html
    assert "T1" in html  # record row present


def test_render_report_empty_is_safe():
    html = render_report([])
    assert "<svg" not in html or "No data" in html
    assert "0 records" in html


def test_run_demo_end_to_end(tmp_path):
    summary = run_demo(tmp_path / "out", pages=3)
    # Mock site has 12 books across 3 pages.
    assert summary["scraped"] == 12
    assert summary["inserted"] == 12
    assert summary["duplicates"] == 0

    report = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert "<svg" in report
    assert "Records by category" in report
    # Spot-check a known book made it through fetch -> parse -> encrypt -> db -> report.
    assert "The Silent Harbor" in report

    csv_text = (tmp_path / "out" / "records.csv").read_text(encoding="utf-8")
    assert "Quantum Shadows" in csv_text


def test_run_demo_dedup_on_second_run(tmp_path):
    # Re-using the same db + key means identical content hashes -> all duplicates.
    from security.encryptor import Encryptor

    enc = Encryptor(Encryptor.generate_key())
    db = str(tmp_path / "dedup.db")
    first = run_demo(tmp_path / "a", pages=3, db_path=db, encryptor=enc)
    second = run_demo(tmp_path / "b", pages=3, db_path=db, encryptor=enc)
    assert first["inserted"] == 12
    assert second["inserted"] == 0
    assert second["duplicates"] == 12
