"""Anlık görüntü (snapshot) saklama + karşılaştırma."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _dir(target: str) -> Path:
    d = DATA_DIR / target
    d.mkdir(parents=True, exist_ok=True)
    return d


def latest_snapshot(target: str, kind: str) -> dict | None:
    files = sorted(_dir(target).glob(f"{kind}_*.json"))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(target: str, kind: str, users: dict[str, str]) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _dir(target) / f"{kind}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "target": target, "kind": kind,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(users), "users": users,
        }, f, ensure_ascii=False, indent=2)
    return path


def diff(old: dict | None, new_users: dict[str, str]) -> dict:
    if old is None:
        return {"added": {}, "removed": {}, "is_baseline": True}
    ou = old.get("users", {})
    oi, ni = set(ou), set(new_users)
    return {
        "added": {i: new_users[i] for i in (ni - oi)},
        "removed": {i: ou[i] for i in (oi - ni)},
        "is_baseline": False,
        "old_captured_at": old.get("captured_at"),
    }
