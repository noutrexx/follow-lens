"""Unit tests for the pure, offline parts of FollowLens."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import igweb
import storage


class DiffTests(unittest.TestCase):
    def test_baseline_when_no_previous_snapshot(self):
        result = storage.diff(None, {"1": "alice"})
        self.assertTrue(result["is_baseline"])
        self.assertEqual(result["added"], {})
        self.assertEqual(result["removed"], {})

    def test_added_and_removed_are_computed(self):
        old = {"users": {"1": "alice", "2": "bob"}}
        result = storage.diff(old, {"2": "bob", "3": "carol"})
        self.assertFalse(result["is_baseline"])
        self.assertEqual(result["added"], {"3": "carol"})
        self.assertEqual(result["removed"], {"1": "alice"})

    def test_no_change_returns_empty_deltas(self):
        old = {"users": {"1": "alice"}}
        result = storage.diff(old, {"1": "alice"})
        self.assertEqual(result["added"], {})
        self.assertEqual(result["removed"], {})


class _StubResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _StubSession:
    """Stands in for ``requests.Session``, replaying a queued list of responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return self._responses.pop(0)


class PaginationTests(unittest.TestCase):
    """A failed page must abort the walk instead of truncating the list."""

    def _client(self, responses):
        client = igweb.IGWeb("1%3Ax", delay=0, jitter=0)
        client.session = _StubSession(responses)
        return client

    def test_failed_page_raises_instead_of_returning_partial_list(self):
        page = {"users": [{"pk": 1, "username": "alice"}], "next_max_id": "cursor"}
        client = self._client([_StubResponse(200, page), _StubResponse(500)])
        with self.assertRaises(igweb.FetchError):
            client.following("42")

    def test_full_walk_unions_pages(self):
        first = {"users": [{"pk": 1, "username": "alice"}], "next_max_id": "cursor"}
        second = {"users": [{"pk": 2, "username": "bob"}], "next_max_id": None}
        repeat = {"users": [{"pk": 1, "username": "alice"},
                            {"pk": 2, "username": "bob"}], "next_max_id": None}
        client = self._client([_StubResponse(200, first), _StubResponse(200, second),
                               _StubResponse(200, repeat)])
        self.assertEqual(client.following("42"), {"1": "alice", "2": "bob"})

    def test_single_pass_is_honoured(self):
        page = {"users": [{"pk": 1, "username": "alice"}], "next_max_id": None}
        client = self._client([_StubResponse(200, page)])
        self.assertEqual(client.following("42", max_passes=1), {"1": "alice"})
        self.assertEqual(client.session.calls, 1)


class UnionRecoveryTests(unittest.TestCase):
    """An account missing from one pass must be recovered by a later pass.

    Instagram answers 200 and still omits accounts, so a single pass reads as
    an unfollow. Both friendship lists union their passes to absorb that.
    """

    def _client(self, responses):
        client = igweb.IGWeb("1%3Ax", delay=0, jitter=0)
        client.session = _StubSession(responses)
        return client

    def _pages(self):
        incomplete = {"users": [{"pk": 1, "username": "alice"}], "next_max_id": None}
        complete = {"users": [{"pk": 1, "username": "alice"},
                              {"pk": 2, "username": "bob"}], "next_max_id": None}
        settled = dict(complete)
        return [_StubResponse(200, incomplete), _StubResponse(200, complete),
                _StubResponse(200, settled)]

    def test_following_recovers_account_missing_from_first_pass(self):
        client = self._client(self._pages())
        self.assertEqual(client.following("42"), {"1": "alice", "2": "bob"})

    def test_followers_recovers_account_missing_from_first_pass(self):
        client = self._client(self._pages())
        self.assertEqual(client.followers("42"), {"1": "alice", "2": "bob"})


class SessionParsingTests(unittest.TestCase):
    def test_self_id_extracted_from_sessionid(self):
        client = igweb.IGWeb("42120983%3Ademosession%3A17")
        self.assertEqual(client.self_id, "42120983")

    def test_known_ids_are_lowercased_and_stringified(self):
        client = igweb.IGWeb("1%3Ax", known_ids={"SomeUser": 99})
        self.assertEqual(client.known_ids, {"someuser": "99"})

    def test_empty_sessionid_raises(self):
        with self.assertRaises(ValueError):
            igweb.IGWeb("")


if __name__ == "__main__":
    unittest.main()
