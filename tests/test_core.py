"""Unit tests for the pure, offline parts of FollowLens."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import i18n
import igweb
import scanner
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

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


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


class SessionErrorTests(unittest.TestCase):
    """A 401 means different things depending on what the run already read."""

    def test_blames_the_account_when_another_one_was_read(self):
        msg = scanner.session_error(igweb.SessionRejected("401."), ["alex.rivers"])
        self.assertIn("alex.rivers", msg)
        self.assertIn("refusing this account", msg)
        self.assertNotIn("expired", msg)

    def test_blames_the_session_when_nothing_was_read(self):
        msg = scanner.session_error(igweb.SessionRejected("401."), [])
        self.assertIn("expired", msg)

    def test_rejection_is_still_a_permission_error(self):
        self.assertTrue(issubclass(igweb.SessionRejected, PermissionError))


class TranslationTests(unittest.TestCase):
    """Every language must cover every string the dashboard asks for."""

    def test_every_language_has_every_key(self):
        table = i18n.table()
        for code, _ in i18n.LANGS:
            self.assertEqual(set(table[code]), set(i18n.KEYS), code)

    def test_no_translation_is_empty(self):
        for code, strings in i18n.table().items():
            for key, text in strings.items():
                self.assertTrue(text.strip(), f"{code}.{key} is empty")

    def test_placeholders_survive_translation(self):
        table = i18n.table()
        for key, text in table["en"].items():
            if "{n}" not in text:
                continue
            for code in table:
                self.assertIn("{n}", table[code][key], f"{code}.{key} dropped the {{n}} placeholder")


class LandingTranslationTests(unittest.TestCase):
    """The landing table and the markup that consumes it must agree."""

    def test_every_language_has_every_landing_key(self):
        table = i18n.landing_table()
        for code, _ in i18n.LANGS:
            self.assertEqual(set(table[code]), set(i18n.LANDING_KEYS), code)

    def test_code_placeholder_survives(self):
        for code, strings in i18n.landing_table().items():
            for key in ("s1_d", "a3"):
                self.assertIn("{code}", strings[key], f"{code}.{key} lost {{code}}")

    def test_every_key_is_used_by_the_page_and_nothing_else_is(self):
        import re
        html = (Path(__file__).resolve().parents[1] / "frontend" / "landing.html").read_text(encoding="utf-8")
        used = set(re.findall(r'data-i18n(?:-alt)?="([a-z0-9_]+)"', html))
        self.assertEqual(used, set(i18n.LANDING_KEYS))


class ScanEndpointTests(unittest.TestCase):
    """Only this dashboard, or a local tool, may start a scan."""

    def setUp(self):
        import server
        self.server = server
        self.calls = 0

        def fake_scan(force=False, only=None):
            self.calls += 1
            return {"ok": True, "targets": []}

        self.real = server.scanner.run_scan
        server.scanner.run_scan = fake_scan
        self.client = server.app.test_client()

    def tearDown(self):
        self.server.scanner.run_scan = self.real

    def test_get_is_refused(self):
        self.assertEqual(self.client.get("/scan").status_code, 405)
        self.assertEqual(self.calls, 0)

    def test_foreign_origin_is_refused(self):
        r = self.client.post("/scan", headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, 0)

    def test_cross_site_fetch_is_refused(self):
        r = self.client.post("/scan", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, 0)

    def test_dashboard_origin_is_allowed(self):
        r = self.client.post("/scan", headers={"Origin": "http://localhost"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.calls, 1)

    def test_local_tool_without_headers_is_allowed(self):
        self.assertEqual(self.client.post("/scan").status_code, 200)
        self.assertEqual(self.calls, 1)


class CooldownTests(unittest.TestCase):
    """A scan only counts towards the cooldown if it actually read an account."""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {name: getattr(scanner, name) for name in ("load_config", "LAST_SCAN")}
        self.saved_ig = scanner.igweb.IGWeb
        self.saved_gen = scanner.report_html.generate
        self.saved_store = (scanner.storage.latest_snapshot, scanner.storage.save_snapshot)
        scanner.LAST_SCAN = self.tmp / ".last_scan"
        scanner.load_config = lambda: {"sessionid": "1%3Ax", "username": "me", "targets": ["a", "b"],
                                       "known_ids": {"a": "1", "b": "2"}}
        scanner.report_html.generate = lambda: None
        scanner.storage.latest_snapshot = lambda *a: None
        scanner.storage.save_snapshot = lambda *a: None

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(scanner, name, value)
        scanner.igweb.IGWeb = self.saved_ig
        scanner.report_html.generate = self.saved_gen
        scanner.storage.latest_snapshot, scanner.storage.save_snapshot = self.saved_store

    def _client(self, fail):
        class Fake:
            self_id = "1"

            def __init__(self, *a, **k):
                pass

            def resolve_uid(self, name):
                return {"id": "1"}

            def following(self, uid, max_passes=4):
                if fail:
                    raise igweb.SessionRejected("401.")
                return {"10": "x"}

            followers = following
        scanner.igweb.IGWeb = Fake

    def test_failed_run_leaves_the_cooldown_alone(self):
        self._client(fail=True)
        result = scanner.run_scan(force=True)
        self.assertTrue(all("error" in t for t in result["targets"]))
        self.assertFalse(scanner.LAST_SCAN.exists())

    def test_successful_run_starts_the_cooldown(self):
        self._client(fail=False)
        scanner.run_scan(force=True)
        self.assertTrue(scanner.LAST_SCAN.exists())


class ConfigTests(unittest.TestCase):
    """A bad config.json must come back as a sentence, never as a 500."""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.real_root = scanner.ROOT
        scanner.ROOT = self.tmp

    def tearDown(self):
        scanner.ROOT = self.real_root

    def _write(self, text):
        (self.tmp / "config.json").write_text(text, encoding="utf-8")

    def test_missing_file_explains_how_to_create_it(self):
        result = scanner.run_scan(force=True)
        self.assertFalse(result["ok"])
        self.assertIn("config.example.json", result["error"])

    def test_broken_json_points_at_the_line(self):
        self._write('{"sessionid": "x",, }')
        result = scanner.run_scan(force=True)
        self.assertFalse(result["ok"])
        self.assertIn("line 1", result["error"])

    def test_username_is_optional(self):
        self._write('{"sessionid": "1%3Ax", "targets": []}')
        result = scanner.run_scan(force=True)
        self.assertTrue(result["ok"])


class LookupTests(unittest.TestCase):
    """A misspelled target should say so, whichever way Instagram reports it."""

    def _client(self, response):
        client = igweb.IGWeb("1%3Ax", delay=0, jitter=0)
        client.session = _StubSession([response])
        return client

    def test_404_names_the_account(self):
        with self.assertRaises(LookupError) as ctx:
            self._client(_StubResponse(404)).resolve_uid("no.such.user")
        self.assertIn("@no.such.user", str(ctx.exception))

    def test_empty_user_names_the_account(self):
        with self.assertRaises(LookupError):
            self._client(_StubResponse(200, {"data": {"user": None}})).resolve_uid("no.such.user")

    def test_known_account_resolves(self):
        user = {"id": 42, "is_private": True, "followed_by_viewer": False,
                "edge_followed_by": {"count": 180}, "edge_follow": {"count": 90}}
        found = self._client(_StubResponse(200, {"data": {"user": user}})).resolve_uid("real")
        self.assertEqual(found, {"id": "42", "private": True, "followed": False,
                                 "followers": 180, "following": 90})


class SnapshotDurabilityTests(unittest.TestCase):
    """A half-written snapshot must never lock an account out of scanning."""

    def setUp(self):
        import tempfile
        self.real = storage.DATA_DIR
        storage.DATA_DIR = Path(tempfile.mkdtemp())

    def tearDown(self):
        storage.DATA_DIR = self.real

    def test_save_leaves_no_temp_file_behind(self):
        path = storage.save_snapshot("acct", "followers", {"1": "alice"})
        self.assertTrue(path.exists())
        self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_truncated_newest_snapshot_is_skipped(self):
        storage.save_snapshot("acct", "followers", {"1": "alice", "2": "bob"})
        broken = storage.DATA_DIR / "acct" / "followers_29991231_235959.json"
        broken.write_text('{"users": {"1": "al', encoding="utf-8")
        latest = storage.latest_snapshot("acct", "followers")
        self.assertEqual(latest["users"], {"1": "alice", "2": "bob"})

    def test_leftover_temp_file_is_not_mistaken_for_a_snapshot(self):
        storage.save_snapshot("acct", "followers", {"1": "alice"})
        (storage.DATA_DIR / "acct" / "followers_29991231_235959.json.tmp").write_text("{", encoding="utf-8")
        self.assertEqual(storage.latest_snapshot("acct", "followers")["users"], {"1": "alice"})


class SoftFailureTests(unittest.TestCase):
    """A 200 that is not a page of users must abort, never read as an empty page."""

    def _client(self, response):
        client = igweb.IGWeb("1%3Ax", delay=0, jitter=0)
        client.session = _StubSession([response] * 8)
        return client

    def test_status_fail_aborts(self):
        wait = _StubResponse(200, {"status": "fail", "message": "Please wait a few minutes before you try again."})
        with self.assertRaises(igweb.FetchError) as ctx:
            self._client(wait).followers("42")
        self.assertIn("Please wait a few minutes", str(ctx.exception))

    def test_body_without_users_aborts(self):
        with self.assertRaises(igweb.FetchError):
            self._client(_StubResponse(200, {"status": "ok"})).following("42")

    def test_html_instead_of_json_aborts(self):
        class Html(_StubResponse):
            def json(self):
                raise ValueError("Expecting value")
        with self.assertRaises(igweb.FetchError) as ctx:
            self._client(Html(200)).following("42")
        self.assertIn("login page", str(ctx.exception))

    def test_an_account_with_no_followers_is_still_fine(self):
        empty = _StubResponse(200, {"status": "ok", "users": [], "next_max_id": None})
        self.assertEqual(self._client(empty).followers("42"), {})


class NetworkErrorTests(unittest.TestCase):
    """Losing the connection should read as that, not as a urllib3 traceback."""

    def _client(self, exc):
        client = igweb.IGWeb("1%3Ax", delay=0, jitter=0)

        def boom(*args, **kwargs):
            raise exc
        client.session.get = boom
        return client

    def test_no_connection(self):
        import requests
        with self.assertRaises(igweb.NetworkError) as ctx:
            self._client(requests.ConnectionError("pool... getaddrinfo failed")).following("42")
        self.assertIn("Could not reach Instagram", str(ctx.exception))
        self.assertNotIn("getaddrinfo", str(ctx.exception))

    def test_timeout(self):
        import requests
        with self.assertRaises(igweb.NetworkError) as ctx:
            self._client(requests.ReadTimeout("Read timed out")).followers("42")
        self.assertIn("30 seconds", str(ctx.exception))


class AddTargetTests(unittest.TestCase):
    """Adding an account edits config.json safely and never touches the real one."""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.real_root, self.real_gen = scanner.ROOT, scanner.report_html.generate
        scanner.ROOT = self.tmp
        scanner.report_html.generate = lambda: None
        (self.tmp / "config.json").write_text(
            '{"sessionid": "1%3Asecret", "targets": ["alex.rivers"], "port": 5005}', encoding="utf-8")

    def tearDown(self):
        scanner.ROOT, scanner.report_html.generate = self.real_root, self.real_gen

    def _config(self):
        import json
        return json.loads((self.tmp / "config.json").read_text(encoding="utf-8"))

    def test_adds_and_keeps_everything_else(self):
        result = scanner.add_target("  @Vela.Studio ")
        self.assertEqual(result, {"ok": True, "target": "vela.studio", "added": True})
        cfg = self._config()
        self.assertEqual(cfg["targets"], ["alex.rivers", "vela.studio"])
        self.assertEqual(cfg["sessionid"], "1%3Asecret")
        self.assertEqual(cfg["port"], 5005)
        self.assertEqual(list(self.tmp.glob("*.tmp")), [])

    def test_existing_account_is_not_duplicated(self):
        result = scanner.add_target("ALEX.RIVERS")
        self.assertFalse(result["added"])
        self.assertEqual(self._config()["targets"], ["alex.rivers"])

    def test_rejects_names_instagram_cannot_have(self):
        for bad in ("", "@", "has space", "semi;colon", "x" * 31, "../config"):
            self.assertFalse(scanner.add_target(bad)["ok"], bad)
        self.assertEqual(self._config()["targets"], ["alex.rivers"])

    def test_single_target_scan_refuses_untracked_accounts(self):
        result = scanner.run_scan(force=True, only="someone.else")
        self.assertFalse(result["ok"])
        self.assertIn("not one of the tracked accounts", result["error"])


class AddEndpointTests(unittest.TestCase):
    """POST /targets follows the same origin rules as /scan."""

    def setUp(self):
        import server
        self.server, self.calls = server, []
        self.real = server.scanner.add_target
        server.scanner.add_target = lambda name: (self.calls.append(name),
                                                  {"ok": True, "target": name, "added": True})[1]
        self.client = server.app.test_client()

    def tearDown(self):
        self.server.scanner.add_target = self.real

    def test_dashboard_can_add(self):
        r = self.client.post("/targets", json={"username": "vela.studio"}, headers={"Origin": "http://localhost"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.calls, ["vela.studio"])

    def test_other_sites_cannot_add(self):
        r = self.client.post("/targets", json={"username": "x"}, headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.calls, [])


class PendingTargetTests(unittest.TestCase):
    """A tracked account with no snapshots yet still gets a tab."""

    def test_tracked_but_unscanned_account_is_listed(self):
        import tempfile

        import report_html
        tmp = Path(tempfile.mkdtemp())
        (tmp / "data").mkdir()
        (tmp / "config.json").write_text('{"targets": ["new.one"]}', encoding="utf-8")
        real = (report_html.ROOT, report_html.DATA_DIR)
        report_html.ROOT, report_html.DATA_DIR = tmp, tmp / "data"
        try:
            targets = report_html.collect_data()["targets"]
        finally:
            report_html.ROOT, report_html.DATA_DIR = real
        self.assertEqual(targets["new.one"], {"display": "new.one", "pending": True, "tracked": True})


class NewAccountScanTests(unittest.TestCase):
    """A newly added account must end up read, or explained, never silently empty."""

    def setUp(self):
        import json
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (scanner.ROOT, scanner.LAST_SCAN, storage.DATA_DIR, scanner.igweb.IGWeb,
                      scanner.report_html.generate)
        scanner.ROOT = self.tmp
        scanner.LAST_SCAN = self.tmp / "data" / ".last_scan"
        storage.DATA_DIR = self.tmp / "data"
        scanner.report_html.generate = lambda: None
        (self.tmp / "config.json").write_text(json.dumps(
            {"sessionid": "1%3Ax", "targets": ["new.one"], "min_scan_interval_seconds": 600}), encoding="utf-8")
        self.fetched = []

    def tearDown(self):
        (scanner.ROOT, scanner.LAST_SCAN, storage.DATA_DIR, scanner.igweb.IGWeb,
         scanner.report_html.generate) = self.saved

    def _ig(self, lists, **profile):
        test = self

        class Fake:
            self_id = "1"

            def __init__(self, *a, **k):
                pass

            def resolve_uid(self, name):
                return {"id": "99", **profile}

            def following(self, uid, max_passes=4):
                test.fetched.append(uid)
                return dict(lists)

            followers = following
        scanner.igweb.IGWeb = Fake

    def _recent_scan(self):
        import time
        scanner.LAST_SCAN.parent.mkdir(parents=True, exist_ok=True)
        scanner.LAST_SCAN.write_text(str(time.time() - 60))

    def test_first_read_of_a_new_account_skips_the_cooldown(self):
        self._recent_scan()
        self._ig({"10": "a"}, followers=1, following=1)
        result = scanner.run_scan(only="new.one")
        self.assertTrue(result["ok"], result)
        self.assertEqual(storage.latest_snapshot("new.one", "followers")["count"], 1)

    def test_second_read_still_waits_for_the_cooldown(self):
        self._ig({"10": "a"}, followers=1, following=1)
        scanner.run_scan(only="new.one", force=True)
        result = scanner.run_scan(only="new.one")
        self.assertFalse(result["ok"])
        self.assertIn("Cooldown", result["error"])

    def test_private_account_is_explained_and_not_fetched(self):
        self._ig({}, private=True, followed=False, followers=180, following=90)
        result = scanner.run_scan(only="new.one")
        self.assertIn("private", result["targets"][0]["error"])
        self.assertEqual(self.fetched, [])
        self.assertIsNone(storage.latest_snapshot("new.one", "followers"))

    def test_empty_list_for_a_populated_profile_is_not_saved(self):
        self._ig({}, private=False, followers=180, following=90)
        result = scanner.run_scan(only="new.one")
        self.assertIn("came back empty although the profile shows", result["targets"][0]["error"])
        self.assertIsNone(storage.latest_snapshot("new.one", "followers"))

    def test_empty_list_after_a_full_one_is_not_saved(self):
        storage.save_snapshot("new.one", "following", {"10": "a"})
        storage.save_snapshot("new.one", "followers", {"10": "a"})
        self._ig({})                                   # cached id: no profile counts
        result = scanner.run_scan(only="new.one", force=True)
        self.assertIn("the last scan had 1", result["targets"][0]["error"])
        self.assertEqual(storage.latest_snapshot("new.one", "followers")["count"], 1)

    def test_genuinely_empty_account_is_saved(self):
        self._ig({}, private=False, followers=0, following=0)
        result = scanner.run_scan(only="new.one")
        self.assertTrue(result["ok"])
        self.assertEqual(storage.latest_snapshot("new.one", "followers")["count"], 0)

    def test_looked_up_id_is_remembered(self):
        import json
        self._ig({"10": "a"}, followers=1, following=1)
        scanner.run_scan(only="new.one")
        cfg = json.loads((self.tmp / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["known_ids"], {"new.one": "99"})


class RemoveTargetTests(unittest.TestCase):
    """Removing stops scans but never deletes history or the rest of the config."""

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (scanner.ROOT, scanner.report_html.generate, storage.DATA_DIR)
        scanner.ROOT = self.tmp
        scanner.report_html.generate = lambda: None
        storage.DATA_DIR = self.tmp / "data"
        (self.tmp / "config.json").write_text(
            '{"sessionid": "1%3Asecret", "targets": ["alex.rivers", "vela.studio"]}', encoding="utf-8")

    def tearDown(self):
        scanner.ROOT, scanner.report_html.generate, storage.DATA_DIR = self.saved

    def _targets(self):
        import json
        return json.loads((self.tmp / "config.json").read_text(encoding="utf-8"))["targets"]

    def test_removes_only_that_account(self):
        result = scanner.remove_target("@Vela.Studio")
        self.assertEqual(result, {"ok": True, "target": "vela.studio", "removed": True})
        self.assertEqual(self._targets(), ["alex.rivers"])

    def test_history_is_kept(self):
        storage.save_snapshot("vela.studio", "followers", {"1": "a"})
        scanner.remove_target("vela.studio")
        self.assertIsNotNone(storage.latest_snapshot("vela.studio", "followers"))

    def test_untracked_name_is_a_no_op(self):
        self.assertFalse(scanner.remove_target("nobody.here")["removed"])
        self.assertEqual(self._targets(), ["alex.rivers", "vela.studio"])

    def test_bad_name_is_rejected(self):
        self.assertFalse(scanner.remove_target("../config")["ok"])

    def test_endpoint_refuses_other_sites(self):
        import server
        r = server.app.test_client().post("/targets/remove", json={"username": "vela.studio"},
                                          headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._targets(), ["alex.rivers", "vela.studio"])


class TrackedFlagTests(unittest.TestCase):
    """History of an account no longer tracked is still shown, marked and last."""

    def test_untracked_history_is_marked_and_sorted_last(self):
        import tempfile

        import report_html
        tmp = Path(tempfile.mkdtemp())
        data = tmp / "data"
        for name in ("aaa.old", "zzz.live"):
            (data / name).mkdir(parents=True)
            for kind in ("following", "followers"):
                (data / name / f"{kind}_20260101_000000.json").write_text(
                    '{"count": 1, "users": {"1": "x"}, "captured_at": "2026-01-01T00:00:00"}', encoding="utf-8")
        (tmp / "config.json").write_text('{"targets": ["zzz.live"]}', encoding="utf-8")
        real = (report_html.ROOT, report_html.DATA_DIR)
        report_html.ROOT, report_html.DATA_DIR = tmp, data
        try:
            targets = report_html.collect_data()["targets"]
        finally:
            report_html.ROOT, report_html.DATA_DIR = real
        self.assertEqual(list(targets), ["zzz.live", "aaa.old"])
        self.assertTrue(targets["zzz.live"]["tracked"])
        self.assertFalse(targets["aaa.old"]["tracked"])


class GenerateTests(unittest.TestCase):
    """The generated page is complete and cannot be broken by its own data."""

    def setUp(self):
        import tempfile

        import report_html
        self.rh = report_html
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "frontend").mkdir()
        self.saved = (report_html.ROOT, report_html.DATA_DIR, report_html.OUT)
        report_html.ROOT, report_html.DATA_DIR = self.tmp, self.tmp / "data"
        report_html.OUT = self.tmp / "frontend" / "viewer.html"

    def tearDown(self):
        self.rh.ROOT, self.rh.DATA_DIR, self.rh.OUT = self.saved

    def _snapshot(self, name, users):
        import json
        d = self.tmp / "data" / name
        d.mkdir(parents=True, exist_ok=True)
        for kind in ("following", "followers"):
            (d / f"{kind}_20260101_000000.json").write_text(json.dumps(
                {"count": len(users), "users": users, "captured_at": "2026-01-01T00:00:00"}), encoding="utf-8")

    def test_every_placeholder_is_filled(self):
        self._snapshot("alex.rivers", {"1": "studio.lumen"})
        html = self.rh.generate().read_text(encoding="utf-8")
        for placeholder in ("__DATA__", "__I18N__", "__LANGS__", "__GEN__"):
            self.assertNotIn(placeholder, html)
        self.assertIn("alex.rivers", html)
        self.assertEqual(list((self.tmp / "frontend").glob("*.tmp")), [])

    def test_data_cannot_close_the_script_element(self):
        self._snapshot("alex.rivers", {"1": "</script><script>alert(1)</script>"})
        html = self.rh.generate().read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert(1)", html)
        self.assertIn("<\\/script>", html)

    def test_generates_with_no_data_at_all(self):
        html = self.rh.generate().read_text(encoding="utf-8")
        self.assertIn('"targets": {}', html)

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
