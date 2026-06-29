"""Unit tests for the pure, offline parts of FollowLens."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import igweb  # noqa: E402
import storage  # noqa: E402


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


class SessionParsingTests(unittest.TestCase):
    def test_self_id_extracted_from_sessionid(self):
        client = igweb.IGWeb("42120983%3Asometoken%3A17")
        self.assertEqual(client.self_id, "42120983")

    def test_known_ids_are_lowercased_and_stringified(self):
        client = igweb.IGWeb("1%3Ax", known_ids={"SomeUser": 99})
        self.assertEqual(client.known_ids, {"someuser": "99"})

    def test_empty_sessionid_raises(self):
        with self.assertRaises(ValueError):
            igweb.IGWeb("")


if __name__ == "__main__":
    unittest.main()
