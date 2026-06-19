"""Tarama mantığı: cooldown kontrolü → hedefleri çek → diff → snapshot kaydet."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import igweb
import report_html
import storage

ROOT = Path(__file__).parent
LAST_SCAN = ROOT / "data" / ".last_scan"


def load_config() -> dict:
    return json.load(open(ROOT / "config.json", encoding="utf-8"))


def _read_last() -> float:
    try:
        return float(LAST_SCAN.read_text())
    except Exception:  # noqa: BLE001
        return 0.0


def run_scan(force: bool = False) -> dict:
    cfg = load_config()
    sessionid = cfg.get("sessionid", "").strip()
    if not sessionid:
        return {"ok": False, "error": "No sessionid. Add your session key to config.json (see README)."}

    # --- Cooldown: minimum time between scans to lower ban risk ---
    cooldown = float(cfg.get("min_scan_interval_seconds", 600))
    elapsed = time.time() - _read_last()
    if not force and elapsed < cooldown:
        remain = int(cooldown - elapsed)
        return {"ok": False, "cooldown": remain,
                "error": f"Cooldown active: try again in {remain}s "
                         f"(min {int(cooldown)}s between scans, to lower ban risk)."}

    delay = float(cfg.get("delay_seconds", 3.0))
    jitter = float(cfg.get("delay_jitter_seconds", 2.5))
    max_passes = int(cfg.get("followers_max_passes", 3))
    me_username = cfg["username"]
    targets = cfg.get("targets", ["self"])
    known = dict(cfg.get("known_ids", {}))

    try:
        ig = igweb.IGWeb(sessionid, known_ids=known, delay=delay, jitter=jitter)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    known.setdefault(me_username.lower(), ig.self_id)

    summary = {"ok": True, "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "targets": []}

    for t in targets:
        uname = me_username if t == "self" else t
        try:
            uid = ig.self_id if t == "self" else ig.resolve_uid(uname)["id"]
            fwg = ig.following(uid)
            flw = ig.followers(uid, max_passes=max_passes)
        except igweb.RateLimited as e:
            return {"ok": False, "error": f"429: {e} (too many scans today, try again in ~30 min)"}
        except Exception as e:  # noqa: BLE001
            summary["targets"].append({"target": t, "error": f"{type(e).__name__}: {e}"})
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
        summary["targets"].append({"target": t, "changes": changes})

    LAST_SCAN.parent.mkdir(parents=True, exist_ok=True)
    LAST_SCAN.write_text(str(time.time()))
    report_html.generate()
    return summary


if __name__ == "__main__":
    print(json.dumps(run_scan(), ensure_ascii=False, indent=2))
