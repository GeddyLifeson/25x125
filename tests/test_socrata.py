import io
import json
import urllib.error

import pytest

from core.socrata import Socrata, SocrataError


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_from(responses, seen):
    def _open(req, timeout):
        seen.append(req)
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return FakeResponse(json.dumps(r).encode())

    return _open


def test_pages_until_short_page():
    seen = []
    pages = [[{"a": 1}, {"a": 2}], [{"a": 3}, {"a": 4}], [{"a": 5}]]
    s = Socrata("example.org", app_token="", opener=opener_from(pages, seen), sleep=lambda s: None)
    got = [r["a"] for page in s.pages("abcd-1234", order=":id", page_size=2) for r in page]
    assert got == [1, 2, 3, 4, 5]
    assert "%24offset=4" in seen[2].full_url
    assert "%24order=%3Aid" in seen[0].full_url


def test_app_token_header():
    seen = []
    s = Socrata("example.org", app_token="tok", opener=opener_from([[]], seen), sleep=lambda s: None)
    s.get("abcd-1234", {"$limit": 1})
    assert seen[0].get_header("X-app-token") == "tok"


def test_retries_throttling_then_succeeds():
    seen, waits = [], []
    err = urllib.error.HTTPError("u", 429, "slow down", {}, None)
    s = Socrata(
        "example.org", app_token="", opener=opener_from([err, err, [{"ok": 1}]], seen), sleep=waits.append
    )
    assert s.get("abcd-1234", {}) == [{"ok": 1}]
    assert waits == [2.0, 4.0]


def test_gives_up_on_client_error():
    err = urllib.error.HTTPError("u", 400, "bad query", {}, None)
    s = Socrata("example.org", app_token="", opener=opener_from([err], []), sleep=lambda s: None)
    with pytest.raises(SocrataError, match="HTTP 400"):
        s.get("abcd-1234", {})


def test_since_clause():
    assert (
        Socrata("example.org", app_token="").since("issue_date", "2026-10-01") == "issue_date > '2026-10-01'"
    )
