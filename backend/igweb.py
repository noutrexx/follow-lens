"""Instagram web API istemcisi — sessionid çerezi ile (şifre/2FA yok).

Ban riskini düşürmek için: bilinen hesaplarda web_profile_info atlanır,
istekler arası RASTGELE (insansı) gecikme verilir, takipçi union geçişleri
sınırlıdır, 429'da bekle-tekrar-dene yapılır.
"""
from __future__ import annotations

import random
import time
from urllib.parse import unquote

import requests

APP_ID = "936619743392459"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


class RateLimited(Exception):
    pass


def _sleep(base: float, jitter: float) -> None:
    time.sleep(max(0.0, base + random.uniform(0, jitter)))


class IGWeb:
    def __init__(self, sessionid: str, known_ids: dict | None = None,
                 delay: float = 3.0, jitter: float = 2.5):
        if not sessionid:
            raise ValueError("sessionid is empty -- add your session key to config.json.")
        self.known_ids = {k.lower(): str(v) for k, v in (known_ids or {}).items()}
        self.self_id = unquote(sessionid).split(":")[0]
        self.delay, self.jitter = delay, jitter
        self.s = requests.Session()
        self.s.headers.update({
            "x-ig-app-id": APP_ID,
            "x-asbd-id": "129477",
            "x-ig-www-claim": "0",
            "user-agent": UA,
            "x-requested-with": "XMLHttpRequest",
            "accept": "*/*",
            "accept-language": "tr-TR,tr;q=0.9,en;q=0.8",
            "referer": "https://www.instagram.com/",
        })
        self.s.cookies.set("sessionid", sessionid, domain=".instagram.com")
        self.s.cookies.set("ds_user_id", self.self_id, domain=".instagram.com")

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        last = None
        for attempt in range(3):
            r = self.s.get(url, params=params, timeout=30)
            if r.status_code == 429:
                last = r
                if attempt < 2:
                    time.sleep(15 * (attempt + 1) + random.uniform(0, 8))  # ~15s, ~30s
                    continue
                raise RateLimited("Instagram 429 (too many requests). Wait a bit and retry.")
            if r.status_code == 401:
                raise PermissionError("Session invalid/expired (401). Refresh your sessionid.")
            return r
        return last  # type: ignore

    def resolve_uid(self, username: str) -> dict:
        key = username.lower()
        if key in self.known_ids:
            return {"id": self.known_ids[key]}
        r = self._get("https://www.instagram.com/api/v1/users/web_profile_info/",
                      {"username": username})
        r.raise_for_status()
        u = r.json()["data"]["user"]
        return {"id": str(u["id"])}

    def _page(self, uid: str, kind: str, max_id, count: int):
        url = f"https://www.instagram.com/api/v1/friendships/{uid}/{kind}/"
        params = {"count": str(count)}
        if max_id:
            params["max_id"] = max_id
        r = self._get(url, params)
        if r.status_code != 200:
            return [], None
        j = r.json()
        return [(str(x["pk"]), x["username"]) for x in j.get("users", [])], j.get("next_max_id")

    def following(self, uid: str) -> dict[str, str]:
        out: dict[str, str] = {}
        nxt = None
        for _ in range(40):
            users, nxt = self._page(uid, "following", nxt, 200)
            for pk, un in users:
                out[pk] = un
            if not nxt:
                break
            _sleep(self.delay, self.jitter)
        return out

    def followers(self, uid: str, max_passes: int = 3) -> dict[str, str]:
        """Boyut büyümeyi durdurana kadar (en fazla max_passes) tam geçiş."""
        out: dict[str, str] = {}
        prev = -1
        for _ in range(max_passes):
            nxt = None
            for _ in range(40):
                users, nxt = self._page(uid, "followers", nxt, 100)
                for pk, un in users:
                    out[pk] = un
                if not nxt:
                    break
                _sleep(self.delay, self.jitter)
            if len(out) == prev:
                break
            prev = len(out)
            _sleep(self.delay, self.jitter)
        return out
