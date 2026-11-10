"""Storage of archived WDI releases (WDI Database Archives, API source 57).

Archive files are stored as deterministic gzip files
(``data/raw/archive/SP.DYN.LE00.IN_v{version}.json.gz``). Their header has
mtime = 0 and no file name, so the same input always produces the same
bytes. ``ARCHIVE_MANIFEST.json`` records, for every version:

* ``original_sha256``: SHA-256 of the uncompressed JSON, exactly as first
  downloaded on 2026-11-10;
* ``gz_sha256``: SHA-256 of the compressed file;
* sizes and the retrieval date.

``read_archive_bytes`` decompresses a file and refuses it unless its SHA-256
matches ``original_sha256``. Compression is therefore checked to be lossless
every time the audit runs.

Command line (run once, from the project root):
    python audit/archive_io.py compress 202503 202504   # .json -> .json.gz, verified
    python audit/archive_io.py verify                   # check every .gz in the manifest
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "data" / "raw" / "archive"
MANIFEST = ARCH / "ARCHIVE_MANIFEST.json"
SERIES = "SP.DYN.LE00.IN"
RETRIEVED = "2026-11-10"


class ArchiveIntegrityError(RuntimeError):
    pass


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gz_path(version: str, arch: Path = ARCH) -> Path:
    return arch / f"{SERIES}_v{version}.json.gz"


def json_path(version: str, arch: Path = ARCH) -> Path:
    return arch / f"{SERIES}_v{version}.json"


def deterministic_gzip(data: bytes) -> bytes:
    # mtime=0 and no filename in the header, so the output is reproducible
    return gzip.compress(data, compresslevel=9, mtime=0)


def load_manifest(path: Path = MANIFEST) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"series": SERIES, "source": "World Bank WDI Database Archives (API source 57)",
            "compression": "gzip, level 9, mtime=0, no filename (deterministic)", "versions": {}}


def save_manifest(m: dict, path: Path = MANIFEST) -> None:
    # write with '\n' explicitly so the manifest bytes are platform-independent
    path.write_bytes((json.dumps(m, indent=1, sort_keys=True) + "\n").encode("utf-8"))


def store_bytes(version: str, raw: bytes, arch: Path = ARCH, retrieved: str = RETRIEVED) -> Path:
    """Compress ``raw`` for ``version``, verify the round trip and record it in the manifest."""
    gz = deterministic_gzip(raw)
    if gzip.decompress(gz) != raw:
        raise ArchiveIntegrityError(f"gzip round trip failed for {version}")
    out = gz_path(version, arch)
    out.write_bytes(gz)
    m = load_manifest(arch / MANIFEST.name)
    m["versions"][version] = {
        "file": out.name,
        "original_file": json_path(version, arch).name,
        "original_sha256": sha256(raw),
        "original_bytes": len(raw),
        "gz_sha256": sha256(gz),
        "gz_bytes": len(gz),
        "retrieved": retrieved,
    }
    save_manifest(m, arch / MANIFEST.name)
    return out


def read_archive_bytes(version: str, arch: Path = ARCH) -> bytes:
    """Return the original (uncompressed) bytes, checked against the manifest.
    Prefers the .gz file. A plain .json file is accepted only if the manifest
    knows it, or if there is no manifest entry for that version."""
    m = load_manifest(arch / MANIFEST.name)
    entry = m["versions"].get(version)
    if gz_path(version, arch).exists():
        raw = gzip.decompress(gz_path(version, arch).read_bytes())
    elif json_path(version, arch).exists():
        raw = json_path(version, arch).read_bytes()
    else:
        raise FileNotFoundError(f"No archive file for version {version} in {arch}")
    if entry is not None and sha256(raw) != entry["original_sha256"]:
        raise ArchiveIntegrityError(
            f"SHA-256 mismatch for {version}: {sha256(raw)} != {entry['original_sha256']}")
    return raw


def available(version: str, arch: Path = ARCH) -> bool:
    return gz_path(version, arch).exists() or json_path(version, arch).exists()


def _cli(argv):
    if not argv or argv[0] not in {"compress", "verify"}:
        print(__doc__)
        return 2
    if argv[0] == "compress":
        for v in argv[1:]:
            raw = json_path(v).read_bytes()
            out = store_bytes(v, raw)
            print(f"{v}: {len(raw):,} -> {out.stat().st_size:,} bytes; round trip OK; sha256 {sha256(raw)}")
        return 0
    m = load_manifest()
    ok = True
    for v, e in sorted(m["versions"].items()):
        gzb = gz_path(v).read_bytes()
        raw = gzip.decompress(gzb)
        good = sha256(raw) == e["original_sha256"] and sha256(gzb) == e["gz_sha256"] and len(raw) == e["original_bytes"]
        ok &= good
        print(f"{v}: original sha256 {sha256(raw)} {'OK' if good else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
