import os

import pytest
from cryptography.fernet import InvalidToken

from security.decryptor import reencrypt
from security.encryptor import AESGCMEncryptor, Encryptor
from security.key_vault import KeyVault


def test_fernet_roundtrip():
    enc = Encryptor(Encryptor.generate_key())
    token = enc.encrypt("hello world")
    assert token != b"hello world"
    assert enc.decrypt(token) == "hello world"


def test_fernet_record_roundtrip():
    enc = Encryptor(Encryptor.generate_key())
    record = {"price": "9.99", "title": "Widget"}
    token = enc.encrypt_record(record)
    assert enc.decrypt_record(token) == record


def test_fernet_tamper_detected():
    enc = Encryptor(Encryptor.generate_key())
    token = bytearray(enc.encrypt("secret"))
    token[-1] ^= 0x01  # flip a bit
    with pytest.raises(InvalidToken):
        enc.decrypt(bytes(token))


def test_aesgcm_roundtrip():
    key = AESGCMEncryptor.generate_key()
    assert len(key) == 32
    enc = AESGCMEncryptor(key)
    token = enc.encrypt_record({"a": 1, "b": "two"})
    assert enc.decrypt_record(token) == {"a": 1, "b": "two"}


def test_aesgcm_rejects_bad_key_length():
    with pytest.raises(ValueError):
        AESGCMEncryptor(b"too-short")


def test_key_vault_creates_and_reuses(tmp_path):
    key_file = tmp_path / ".secrets" / "key.key"
    vault = KeyVault(str(key_file), env_var="UNUSED_ENV_VAR_XYZ")
    key1 = vault.load_or_create()
    assert key_file.exists()
    key2 = vault.load_or_create()
    assert key1 == key2  # persisted, not regenerated


def test_key_vault_prefers_env(monkeypatch, tmp_path):
    env_key = Encryptor.generate_key().decode()
    monkeypatch.setenv("SENTINEL_KEY", env_key)
    vault = KeyVault(str(tmp_path / "key.key"))
    assert vault.load_or_create() == env_key.encode()
    assert not (tmp_path / "key.key").exists()  # env used, no file written


def test_reencrypt_migrates_key():
    old = Encryptor(Encryptor.generate_key())
    new = Encryptor(Encryptor.generate_key())
    record = {"x": "y"}
    old_token = old.encrypt_record(record)
    new_token = reencrypt(old, new, old_token)
    assert new.decrypt_record(new_token) == record
    with pytest.raises(InvalidToken):
        old.decrypt(new_token)  # old key can no longer read it
