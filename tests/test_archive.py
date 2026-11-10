"""Tests for audit/archive_io.py: lossless, deterministic, integrity-checked storage."""

import gzip
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "audit"))
import archive_io as aio  # noqa: E402

SAMPLE = b'{"version": "209901", "series": "X", "records": [{"value": 1.5}]}\r\n\xc3\xa7'


def test_round_trip_is_byte_identical(tmp_path):
    aio.store_bytes("209901", SAMPLE, tmp_path)
    assert aio.read_archive_bytes("209901", tmp_path) == SAMPLE
    assert gzip.decompress(aio.gz_path("209901", tmp_path).read_bytes()) == SAMPLE


def test_compression_is_deterministic(tmp_path):
    a = aio.deterministic_gzip(SAMPLE)
    b = aio.deterministic_gzip(SAMPLE)
    assert a == b
    assert a[4:8] == b"\x00\x00\x00\x00"  # gzip header mtime = 0


def test_manifest_records_original_hash(tmp_path):
    aio.store_bytes("209901", SAMPLE, tmp_path)
    m = aio.load_manifest(tmp_path / aio.MANIFEST.name)
    e = m["versions"]["209901"]
    assert e["original_sha256"] == aio.sha256(SAMPLE)
    assert e["original_bytes"] == len(SAMPLE)
    assert e["gz_sha256"] == aio.sha256(aio.gz_path("209901", tmp_path).read_bytes())


def test_corrupted_archive_is_rejected(tmp_path):
    aio.store_bytes("209901", SAMPLE, tmp_path)
    aio.gz_path("209901", tmp_path).write_bytes(aio.deterministic_gzip(SAMPLE + b"tampered"))
    with pytest.raises(aio.ArchiveIntegrityError):
        aio.read_archive_bytes("209901", tmp_path)


def test_missing_version_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        aio.read_archive_bytes("209912", tmp_path)
    assert not aio.available("209912", tmp_path)


@pytest.mark.skipif(not aio.MANIFEST.exists(), reason="archive manifest not present")
def test_stored_archives_match_original_sha256():
    m = aio.load_manifest()
    assert {"202503", "202504"} <= set(m["versions"])
    for v, e in m["versions"].items():
        gz = aio.gz_path(v).read_bytes()
        assert aio.sha256(gz) == e["gz_sha256"]
        raw = aio.read_archive_bytes(v)  # raises if the SHA-256 differs
        assert len(raw) == e["original_bytes"]
