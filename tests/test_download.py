"""download_data.py tests.

Unit tests replace the HTTP session with a fake one, so they never touch the
network. The live test at the bottom is marked ``network`` and runs only
with ``pytest --run-network``.
"""

import pytest
import requests

import download_data as dd


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False, url="http://x"):
        self.status_code = status
        self._payload = payload
        self._bad = bad_json
        self.url = url
        self.text = "" if payload is None else str(payload)

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


class FakeSession:
    """Returns queued responses (or raises queued exceptions) in order."""

    def __init__(self, items):
        self.items = list(items)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _page(page, pages, total, records):
    return FakeResponse(payload=[{"page": page, "pages": pages, "per_page": 2, "total": total}, records])


NO_SLEEP = {"sleep": lambda s: None}


def test_pagination_collects_all_pages():
    s = FakeSession([_page(1, 3, 5, [{"a": 1}, {"a": 2}]), _page(2, 3, 5, [{"a": 3}, {"a": 4}]),
                     _page(3, 3, 5, [{"a": 5}])])
    recs, header = dd.fetch_paginated(s, "x", per_page=2, **NO_SLEEP)
    assert [r["a"] for r in recs] == [1, 2, 3, 4, 5]
    assert [c["page"] for c in s.calls] == [1, 2, 3]
    assert header["total"] == 5


def test_record_count_mismatch_raises():
    s = FakeSession([_page(1, 1, 3, [{"a": 1}])])
    with pytest.raises(dd.WorldBankAPIError, match="Expected 3"):
        dd.fetch_paginated(s, "x", **NO_SLEEP)


def test_null_data_element_means_empty():
    s = FakeSession([_page(1, 0, 0, None)])
    recs, _ = dd.fetch_paginated(s, "x", **NO_SLEEP)
    assert recs == []


def test_api_error_message_payload_raises():
    s = FakeSession([FakeResponse(payload=[{"message": [{"id": "120", "value": "Invalid value"}]}])])
    with pytest.raises(dd.WorldBankAPIError, match="API error"):
        dd.fetch_paginated(s, "x", **NO_SLEEP)


def test_unexpected_structure_raises():
    s = FakeSession([FakeResponse(payload={"unexpected": True})])
    with pytest.raises(dd.WorldBankAPIError):
        dd.fetch_paginated(s, "x", **NO_SLEEP)


def test_retries_transient_errors_then_succeeds():
    s = FakeSession([requests.Timeout(), requests.ConnectionError(), FakeResponse(status=503),
                     FakeResponse(bad_json=True), _page(1, 1, 1, [{"a": 1}])])
    recs, _ = dd.fetch_paginated(s, "x", max_retries=5, **NO_SLEEP)
    assert recs == [{"a": 1}]
    assert len(s.calls) == 5


def test_gives_up_after_max_retries():
    s = FakeSession([requests.Timeout()] * 3)
    with pytest.raises(dd.WorldBankAPIError, match="Giving up"):
        dd.fetch_paginated(s, "x", max_retries=3, **NO_SLEEP)


def test_client_error_is_not_retried():
    s = FakeSession([FakeResponse(status=404)])
    with pytest.raises(dd.WorldBankAPIError, match="HTTP 404"):
        dd.fetch_paginated(s, "x", **NO_SLEEP)
    assert len(s.calls) == 1


@pytest.mark.network
def test_live_api_indicator_small_query():
    s = requests.Session()
    recs, header = dd.fetch_paginated(s, "country/TUR/indicator/SP.DYN.LE00.IN", {"date": "2019:2020"})
    assert len(recs) == 2
    assert {r["countryiso3code"] for r in recs} == {"TUR"}
    meta = dd.download_indicator_metadata(s, "NY.GDP.PCAP.PP.KD")
    assert meta["License_Type"].startswith("CC BY")
