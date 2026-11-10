"""Download raw data from the official World Bank API (v2).

What this script does
---------------------
* Downloads the two World Development Indicators (WDI) used in the study:
    - NY.GDP.PCAP.PP.KD  GDP per capita, PPP (constant 2021 international $)
    - SP.DYN.LE00.IN     Life expectancy at birth, total (years)
* Downloads the World Bank country list, which is how we tell real
  economies apart from aggregates (World, regions, income groups, ...).
* Downloads the official indicator metadata (definition, unit, licence).
* Handles pagination and checks that every page and every record arrived.
* Retries connection errors, time-outs, HTTP 5xx/429 and malformed
  responses with exponential back-off. Any other problem raises an error.
* Saves the unmodified API records to ``data/raw/`` along with a manifest
  that holds the UTC download time, request URLs, record counts and SHA-256
  checksums.

Usage
-----
    python src/download_data.py               # default range 2000:2025
    python src/download_data.py --start 1990 --end 2025

Note on revisions: the World Bank revises WDI series (new ICP PPP rounds,
new UN World Population Prospects editions, national-accounts revisions).
Re-running this script later may return different numbers, which can change
the results. The manifest records the API's ``lastupdated`` stamp so each
run can be traced to a specific database release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.worldbank.org/v2"
INDICATORS: dict[str, str] = {
    "NY.GDP.PCAP.PP.KD": "gdp_pc_ppp",
    "SP.DYN.LE00.IN": "life_expectancy",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

DEFAULT_TIMEOUT = 60  # seconds
MAX_RETRIES = 5
PER_PAGE = 1000


class WorldBankAPIError(RuntimeError):
    """Raised when the API returns an error or an unusable response."""


# --------------------------------------------------------------------------
# Low-level HTTP helpers
# --------------------------------------------------------------------------
def _get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    backoff: float = 2.0,
    sleep=time.sleep,
) -> Any:
    """GET ``url`` and return parsed JSON, retrying transient failures.

    Retried: connection errors, time-outs, HTTP 429/5xx and responses whose
    body is not valid JSON. Not retried: other 4xx codes, because repeating
    a bad request will not fix it.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise WorldBankAPIError(f"HTTP {resp.status_code} from {resp.url}")
            if resp.status_code >= 400:
                # Non-transient client error: fail immediately.
                raise _FatalAPIError(f"HTTP {resp.status_code} from {resp.url}: {resp.text[:300]}")
            try:
                return resp.json()
            except ValueError as exc:  # invalid JSON body
                raise WorldBankAPIError(f"Invalid JSON from {resp.url}") from exc
        except _FatalAPIError as exc:
            raise WorldBankAPIError(str(exc)) from None
        except (requests.ConnectionError, requests.Timeout, WorldBankAPIError) as exc:
            last_exc = exc
            if attempt < max_retries:
                sleep(backoff ** (attempt - 1))
    raise WorldBankAPIError(f"Giving up after {max_retries} attempts: {last_exc}")


class _FatalAPIError(Exception):
    pass


def _check_api_error_payload(payload: Any, url: str) -> None:
    """The WB API returns HTTP 200 with a ``message`` element when the request
    is wrong, for example an unknown indicator code. Detect that case."""
    if isinstance(payload, list) and payload and isinstance(payload[0], dict) and "message" in payload[0]:
        raise WorldBankAPIError(f"API error for {url}: {payload[0]['message']}")
    if isinstance(payload, dict) and "message" in payload:
        raise WorldBankAPIError(f"API error for {url}: {payload['message']}")


def fetch_paginated(
    session: requests.Session,
    path: str,
    params: dict[str, Any] | None = None,
    per_page: int = PER_PAGE,
    **kwargs: Any,
) -> tuple[list[dict], dict]:
    """Fetch every page of a v2 list endpoint.

    Returns ``(records, first_page_header)``. Raises ``WorldBankAPIError``
    when the structure is unexpected or when the number of records received
    differs from the ``total`` the API reports.
    """
    url = f"{API_BASE}/{path}"
    base_params = {"format": "json", "per_page": per_page, **(params or {})}
    records: list[dict] = []
    page, pages, header0 = 1, None, None
    while pages is None or page <= pages:
        payload = _get_json(session, url, params={**base_params, "page": page}, **kwargs)
        _check_api_error_payload(payload, url)
        if not (isinstance(payload, list) and len(payload) == 2 and isinstance(payload[0], dict)):
            raise WorldBankAPIError(f"Unexpected response structure from {url} page {page}")
        header, data = payload
        if data is None:  # the API sends null when a query matches nothing
            data = []
        if not isinstance(data, list):
            raise WorldBankAPIError(f"Data element is not a list ({url} page {page})")
        if header0 is None:
            header0 = header
            pages = int(header["pages"])
        elif int(header["pages"]) != pages:
            raise WorldBankAPIError("Page count changed during download; retry later.")
        records.extend(data)
        page += 1
    total = int(header0["total"]) if header0 else 0
    if len(records) != total:
        raise WorldBankAPIError(f"Expected {total} records from {url}, received {len(records)}")
    return records, header0 or {}


# --------------------------------------------------------------------------
# High-level download
# --------------------------------------------------------------------------
def download_indicator(session, indicator: str, start: int, end: int, **kw) -> dict:
    records, header = fetch_paginated(
        session, f"country/all/indicator/{indicator}", {"date": f"{start}:{end}"}, **kw
    )
    return {"indicator": indicator, "header": header, "records": records}


def download_countries(session, **kw) -> dict:
    records, header = fetch_paginated(session, "country", **kw)
    return {"header": header, "records": records}


def download_indicator_metadata(session, indicator: str, **kw) -> dict:
    url = f"{API_BASE}/sources/2/series/{indicator}/metadata"
    payload = _get_json(session, url, params={"format": "json"}, **kw)
    _check_api_error_payload(payload, url)
    try:
        metatypes = payload["source"][0]["concept"][0]["variable"][0]["metatype"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WorldBankAPIError(f"Unexpected metadata structure for {indicator}") from exc
    return {m["id"]: m["value"] for m in metatypes}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(obj: Any, path: Path) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def main(start: int = 2000, end: int = 2025, out_dir: Path = RAW_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "economic-development-life-expectancy research script"
    retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    manifest: dict[str, Any] = {
        "retrieved_at_utc": retrieved,
        "api_base": API_BASE,
        "requested_years": f"{start}:{end}",
        "files": {},
    }

    for ind in INDICATORS:
        blob = download_indicator(session, ind, start, end)
        fname = out_dir / f"{ind}.json"
        _write_json(blob, fname)
        manifest["files"][fname.name] = {
            "request": f"{API_BASE}/country/all/indicator/{ind}?format=json&date={start}:{end}",
            "records": len(blob["records"]),
            "api_total": int(blob["header"]["total"]),
            "api_lastupdated": blob["header"].get("lastupdated"),
            "sha256": _sha256(fname),
        }
        print(f"{ind}: {len(blob['records'])} records (lastupdated {blob['header'].get('lastupdated')})")

    countries = download_countries(session)
    fname = out_dir / "countries.json"
    _write_json(countries, fname)
    manifest["files"][fname.name] = {
        "request": f"{API_BASE}/country?format=json",
        "records": len(countries["records"]),
        "sha256": _sha256(fname),
    }
    print(f"countries: {len(countries['records'])} entries")

    meta = {ind: download_indicator_metadata(session, ind) for ind in INDICATORS}
    fname = out_dir / "indicator_metadata.json"
    _write_json(meta, fname)
    manifest["files"][fname.name] = {
        "request": f"{API_BASE}/sources/2/series/<indicator>/metadata?format=json",
        "sha256": _sha256(fname),
    }

    _write_json(manifest, out_dir / "download_manifest.json")
    print(f"Saved raw files to data/raw/ (retrieved {retrieved})")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--start", type=int, default=2000)
    ap.add_argument("--end", type=int, default=2025)
    a = ap.parse_args()
    main(a.start, a.end)
