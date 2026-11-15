from security.encryptor import Encryptor
from storage.db_manager import DBManager
from storage.deduplicator import record_hash


def _db(tmp_path):
    enc = Encryptor(Encryptor.generate_key())
    return DBManager(str(tmp_path / "test.db"), enc)


def test_record_hash_is_order_independent():
    assert record_hash({"a": 1, "b": 2}) == record_hash({"b": 2, "a": 1})


def test_record_hash_differs_on_content():
    assert record_hash({"a": 1}) != record_hash({"a": 2})


def test_insert_and_count(tmp_path):
    db = _db(tmp_path)
    assert db.insert("s1", "http://x", {"title": "A", "price": "1"}) is True
    assert db.count() == 1
    assert db.count("s1") == 1
    assert db.count("other") == 0
    db.close()


def test_duplicate_is_rejected(tmp_path):
    db = _db(tmp_path)
    rec = {"title": "A", "price": "1"}
    assert db.insert("s1", "http://x", rec) is True
    assert db.insert("s1", "http://x", dict(rec)) is False  # same content
    assert db.count() == 1
    db.close()


def test_insert_many_counts_duplicates(tmp_path):
    db = _db(tmp_path)
    records = [{"n": 1}, {"n": 2}, {"n": 1}, {"n": 3}, {"n": 2}]
    inserted, duplicates = db.insert_many("s1", "http://x", records)
    assert inserted == 3
    assert duplicates == 2
    assert db.count() == 3
    db.close()


def test_payload_is_encrypted_at_rest(tmp_path):
    enc = Encryptor(Encryptor.generate_key())
    path = str(tmp_path / "enc.db")
    db = DBManager(path, enc)
    db.insert("s1", "http://x", {"secret_field": "TOP-SECRET-VALUE"})
    db.close()
    # The plaintext must not appear anywhere in the raw database file.
    raw = open(path, "rb").read()
    assert b"TOP-SECRET-VALUE" not in raw


def test_fetch_decrypted_roundtrip(tmp_path):
    db = _db(tmp_path)
    db.insert("s1", "http://x", {"title": "A"})
    db.insert("s1", "http://x", {"title": "B"})
    out = db.fetch_decrypted("s1")
    titles = sorted(r["title"] for r in out)
    assert titles == ["A", "B"]
    assert all("_source_url" in r and "_scraped_at" in r for r in out)
    db.close()
