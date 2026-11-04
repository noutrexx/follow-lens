"""Snapshot storage and diffing."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _dir(target: str) -> Path:
    d = DATA_DIR / target
    d.mkdir(parents=True, exist_ok=True)
    return d


def latest_snapshot(target: str, kind: str) -> dict | None:
    """Return the most recent readable snapshot for ``target``/``kind``, or ``None``.

    An unreadable file is skipped rather than raised: if it were the newest one,
    every later scan of the account would fail on it until someone deleted it.
    """
    for path in sorted(_dir(target).glob(f"{kind}_*.json"), reverse=True):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return None


def save_snapshot(target: str, kind: str, users: dict[str, str]) -> Path:
    """Write a timestamped snapshot and return its path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _dir(target) / f"{kind}_{ts}.json"
    # Write beside the target and swap it in, so a process killed mid-write leaves
    # a stray .tmp (which nothing reads) instead of a truncated snapshot.
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "target": target, "kind": kind,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(users), "users": users,
        }, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def diff(old: dict | None, new_users: dict[str, str]) -> dict:
    """Compare a previous snapshot with the current users and return the delta."""
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
