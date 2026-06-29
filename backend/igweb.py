"""Minimal Instagram web client backed by a session cookie (no password, no 2FA).

The client talks to the same private web endpoints the browser uses. To keep the
request volume conservative it skips ``web_profile_info`` for accounts whose id is
already known, spaces requests with a randomized delay, caps the number of
follower union passes, and backs off and retries on HTTP 429.
"""
from __future__ import annotations

import random
import time
from urllib.parse import unquote

import requests

APP_ID = "936619743392459"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class RateLimited(Exception):
    """Raised when Instagram keeps returning HTTP 429 after retries."""


def _sleep(base: float, jitter: float) -> None:
    time.sleep(max(0.0, base + random.uniform(0, jitter)))


class IGWeb:
    """Authenticated client for the Instagram web API.

    Args:
        sessionid: The ``sessionid`` cookie value from a logged-in browser.
        known_ids: Optional ``username -> id`` map to avoid profile lookups.
        delay: Base delay between paginated requests, in seconds.
        jitter: Extra random delay added on top of ``delay``.
    """

    def __init__(self, sessionid: str, known_ids: dict | None = None,
                 delay: float = 3.0, jitter: float = 2.5):
        if not sessionid:
            raise ValueError("sessionid is empty -- add your session key to config.json.")
        self.known_ids = {k.lower(): str(v) for k, v in (known_ids or {}).items()}
        self.self_id = unquote(sessionid).split(":")[0]
        self.delay, self.jitter = delay, jitter
        self.session = requests.Session()
        self.session.headers.update({
            "x-ig-app-id": APP_ID,
            "x-asbd-id": "129477",
            "x-ig-www-claim": "0",
            "user-agent": USER_AGENT,
            "x-requested-with": "XMLHttpRequest",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://www.instagram.com/",
        })
        self.session.cookies.set("sessionid", sessionid, domain=".instagram.com")
        self.session.cookies.set("ds_user_id", self.self_id, domain=".instagram.com")

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        """GET with up to two backoff retries on HTTP 429."""
        last = None
        for attempt in range(3):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                last = resp
                if attempt < 2:
                    time.sleep(15 * (attempt + 1) + random.uniform(0, 8))
                    continue
                raise RateLimited("Instagram returned 429 (too many requests). Wait a bit and retry.")
            if resp.status_code == 401:
                raise PermissionError("Session invalid or expired (401). Refresh your sessionid.")
            return resp
        return last  # type: ignore[return-value]

    def resolve_uid(self, username: str) -> dict:
        """Return ``{"id": ...}`` for a username, using the cache when possible."""
        key = username.lower()
        if key in self.known_ids:
            return {"id": self.known_ids[key]}
        resp = self._get(
            "https://www.instagram.com/api/v1/users/web_profile_info/",
            {"username": username},
        )
        resp.raise_for_status()
        user = resp.json()["data"]["user"]
        return {"id": str(user["id"])}

    def _page(self, uid: str, kind: str, max_id, count: int):
        """Fetch one page of a friendship list. Returns ``(items, next_max_id)``."""
        url = f"https://www.instagram.com/api/v1/friendships/{uid}/{kind}/"
        params = {"count": str(count)}
        if max_id:
            params["max_id"] = max_id
        resp = self._get(url, params)
        if resp.status_code != 200:
            return [], None
        body = resp.json()
        items = [(str(u["pk"]), u["username"]) for u in body.get("users", [])]
        return items, body.get("next_max_id")

    def following(self, uid: str) -> dict[str, str]:
        """Return the full following list as ``{user_id: username}``."""
        out: dict[str, str] = {}
        next_max_id = None
        for _ in range(40):
            users, next_max_id = self._page(uid, "following", next_max_id, 200)
            for pk, username in users:
                out[pk] = username
            if not next_max_id:
                break
            _sleep(self.delay, self.jitter)
        return out

    def followers(self, uid: str, max_passes: int = 3) -> dict[str, str]:
        """Return the full followers list as ``{user_id: username}``.

        The followers endpoint paginates inconsistently, so we run repeated full
        passes (up to ``max_passes``) and union the results, stopping early once a
        pass adds no new accounts.
        """
        out: dict[str, str] = {}
        prev = -1
        for _ in range(max_passes):
            next_max_id = None
            for _ in range(40):
                users, next_max_id = self._page(uid, "followers", next_max_id, 100)
                for pk, username in users:
                    out[pk] = username
                if not next_max_id:
                    break
                _sleep(self.delay, self.jitter)
            if len(out) == prev:
                break
            prev = len(out)
            _sleep(self.delay, self.jitter)
        return out
