"""Scan logic: cooldown check -> fetch targets -> diff -> save snapshots."""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import igweb
import report_html
import storage

ROOT = Path(__file__).resolve().parents[1]
LAST_SCAN = ROOT / "data" / ".last_scan"


class ConfigError(Exception):
    """config.json is missing or unreadable; the message says how to fix it."""


def load_config() -> dict:
    path = ROOT / "config.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigError("config.json not found. Copy config.example.json to config.json "
                          "and paste your sessionid into it.") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"config.json is not valid JSON: {e.msg} at line {e.lineno}, "
                          f"column {e.colno}.") from None


def _read_last() -> float:
    try:
        return float(LAST_SCAN.read_text())
    except Exception:  # noqa: BLE001
        return 0.0


# Instagram names: 1-30 letters, digits, dots and underscores, case-insensitive.
USERNAME = re.compile(r"[a-z0-9._]{1,30}")


def normalize_username(raw: str) -> str | None:
    """Return the canonical form of a typed username, or None if it cannot be one."""
    name = (raw or "").strip().lstrip("@").lower()
    return name if USERNAME.fullmatch(name) else None


def save_config(cfg: dict) -> None:
    """Write config.json atomically. It holds the session cookie, so a half-written
    file would cost the user their login on top of their target list."""
    path = ROOT / "config.json"
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def add_target(raw: str) -> dict:
    """Start tracking an account. Nothing is fetched here; the next scan reads it."""
    name = normalize_username(raw)
    if not name:
        return {"ok": False, "error": "That is not a valid Instagram username."}
    try:
        cfg = load_config()
    except ConfigError as e:
        return {"ok": False, "error": str(e)}
    targets = list(cfg.get("targets", ["self"]))
    if name in (str(t).lower() for t in targets):
        return {"ok": True, "target": name, "added": False}
    cfg["targets"] = [*targets, name]
    save_config(cfg)
    report_html.generate()            # so the new tab is there on the next page load
    return {"ok": True, "target": name, "added": True}


def session_error(exc: Exception, scanned: list[str]) -> str:
    """Explain a 401 using what the rest of this run already managed to read."""
    if scanned:
        return (f"{exc} The session itself works -- {scanned[0]} was read in this same run -- "
                "so Instagram is refusing this account for now. Wait a while before retrying.")
    return f"{exc} No account could be read, so the sessionid has most likely expired. Refresh it."


def never_scanned(target: str) -> bool:
    return (storage.latest_snapshot(target, "following") is None
            and storage.latest_snapshot(target, "followers") is None)


def empty_problem(target: str, uname: str, profile: dict, lists) -> str | None:
    """Explain a list that came back empty when it clearly should not have.

    Instagram serves an empty list, not an error, for an account it will not show
    this session. Stored, that reads as everyone leaving, and when the account
    becomes visible again everyone reads as new.
    """
    for kind, users in lists:
        if users:
            continue
        expected = profile.get(kind)
        old = storage.latest_snapshot(target, kind)
        before = old.get("count", len(old.get("users", {}))) if old else 0
        if expected or before:
            seen = f"the profile shows {expected}" if expected else f"the last scan had {before}"
            return (f"@{uname}'s {kind} came back empty although {seen}. The account is "
                    "private or hidden from this session; nothing was saved.")
    return None


def run_scan(force: bool = False, only: str | None = None) -> dict:
    try:
        cfg = load_config()
    except ConfigError as e:
        return {"ok": False, "error": str(e)}
    sessionid = cfg.get("sessionid", "").strip()
    if not sessionid:
        return {"ok": False, "error": "No sessionid. Add your session key to config.json (see README)."}

    targets = cfg.get("targets", ["self"])
    if only is not None:
        # One account at a time, e.g. the one just added, so adding an account
        # does not re-read every other list as well.
        name = normalize_username(only)
        if name not in (str(t).lower() for t in targets):
            return {"ok": False, "error": f"@{only} is not one of the tracked accounts."}
        targets = [name]
    # The first read of a single account nobody has scanned yet is allowed through
    # the cooldown: without it, an account added minutes after a scan just sits
    # there empty. Every later scan, of it or of anything else, still waits.
    first_read = only is not None and never_scanned(targets[0])

    # --- Cooldown: minimum time between scans to lower ban risk ---
    cooldown = float(cfg.get("min_scan_interval_seconds", 600))
    elapsed = time.time() - _read_last()
    if not force and not first_read and elapsed < cooldown:
        remain = int(cooldown - elapsed)
        return {"ok": False, "cooldown": remain,
                "error": f"Cooldown active: try again in {remain}s "
                         f"(min {int(cooldown)}s between scans, to lower ban risk)."}

    delay = float(cfg.get("delay_seconds", 3.0))
    jitter = float(cfg.get("delay_jitter_seconds", 2.5))
    max_passes = int(cfg.get("followers_max_passes", 4))
    me_username = cfg.get("username") or "self"
    known = dict(cfg.get("known_ids", {}))
    new_ids: dict[str, str] = {}

    try:
        ig = igweb.IGWeb(sessionid, known_ids=known, delay=delay, jitter=jitter)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    known.setdefault(me_username.lower(), ig.self_id)

    summary = {"ok": True, "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "targets": []}
    scanned: list[str] = []

    for t in targets:
        uname = me_username if t == "self" else t
        try:
            profile = {"id": ig.self_id} if t == "self" else ig.resolve_uid(uname)
            if uname.lower() not in known:
                new_ids[uname.lower()] = profile["id"]
            if profile.get("private") and not profile.get("followed") and profile["id"] != ig.self_id:
                summary["targets"].append({"target": t, "error": (
                    f"@{uname} is private and this session does not follow it, so its lists "
                    "cannot be read. Nothing was saved.")})
                continue
            fwg = ig.following(profile["id"], max_passes=max_passes)
            flw = ig.followers(profile["id"], max_passes=max_passes)
        except igweb.RateLimited as e:
            return {"ok": False, "error": f"429: {e} (too many scans today, try again in ~30 min)"}
        except igweb.SessionRejected as e:
            summary["targets"].append({"target": t, "error": session_error(e, scanned)})
            continue
        except Exception as e:  # noqa: BLE001
            summary["targets"].append({"target": t, "error": f"{type(e).__name__}: {e}"})
            continue

        problem = empty_problem(t, uname, profile, (("following", fwg), ("followers", flw)))
        if problem:
            summary["targets"].append({"target": t, "error": problem})
            continue

        changes = {}
        for kind, users in (("following", fwg), ("followers", flw)):
            old = storage.latest_snapshot(t, kind)
            d = storage.diff(old, users)
            storage.save_snapshot(t, kind, users)
            changes[kind] = {
                "count": len(users), "baseline": d["is_baseline"],
                "added": sorted(d["added"].values()), "removed": sorted(d["removed"].values()),
            }
        scanned.append(t)
        summary["targets"].append({"target": t, "changes": changes})

    # A run that read nothing spent no real budget and changed no data, so it
    # must not start the cooldown: the usual cause is an expired session, and
    # the user should be able to retry the moment they paste a new one.
    # Remember ids looked up this run, so the rate-limited profile endpoint is
    # hit once per account rather than on every scan.
    if new_ids:
        try:
            fresh = load_config()
            fresh.setdefault("known_ids", {}).update(new_ids)
            save_config(fresh)
        except ConfigError:
            pass
    if scanned:
        LAST_SCAN.parent.mkdir(parents=True, exist_ok=True)
        LAST_SCAN.write_text(str(time.time()))
        report_html.generate()
    return summary


if __name__ == "__main__":
    print(json.dumps(run_scan(), ensure_ascii=False, indent=2))
