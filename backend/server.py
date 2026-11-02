"""Local Flask server.

Open http://localhost:PORT in the browser. The dashboard "Refresh" button calls
/scan, which runs a scan and regenerates the dashboard. You can also trigger a
scan directly:  curl -X POST http://localhost:5005/scan
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import i18n
import report_html
import scanner
from flask import Flask, jsonify, request, send_file, send_from_directory

ROOT = Path(__file__).resolve().parents[1]      # repo root
FRONTEND = ROOT / "frontend"
ASSETS = ROOT / "assets"

app = Flask(__name__)
_lock = threading.Lock()


def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/")
def landing():
    return _no_cache(send_file(FRONTEND / "landing.html"))


@app.route("/dashboard")
@app.route("/viewer.html")
def dashboard():
    out = FRONTEND / "viewer.html"
    if not out.exists():
        report_html.generate()
    return _no_cache(send_file(out))


@app.route("/assets/<path:name>")
def assets(name: str):
    return send_from_directory(ASSETS, name)


@app.route("/i18n/landing.json")
def landing_strings():
    """Landing-page copy in every supported language; the page fetches it once."""
    return jsonify({"langs": i18n.LANGS, "strings": i18n.landing_table()})


@app.route("/og.svg")
def og():
    return send_file(FRONTEND / "og.svg")


def _same_origin() -> bool:
    """Refuse scans started by some other site the browser happens to have open.

    A cross-site request always carries Origin (or at least Sec-Fetch-Site), so
    a page elsewhere cannot fire one through an <img> or a hidden form. curl and
    other local tools send neither header and stay allowed.
    """
    origin = request.headers.get("Origin")
    if origin is not None:
        return origin.rstrip("/") == request.host_url.rstrip("/")
    return request.headers.get("Sec-Fetch-Site") in (None, "same-origin", "none")


@app.route("/scan", methods=["POST"])
def scan():
    if not _same_origin():
        return jsonify({"ok": False, "error": "Scans can only be started from this dashboard."}), 403
    if not _lock.acquire(blocking=False):
        return jsonify({"ok": False, "error": "A scan is already running."}), 409
    force = request.args.get("force") in ("1", "true", "yes")
    try:
        return jsonify(scanner.run_scan(force=force))
    finally:
        _lock.release()


@app.route("/health")
def health():
    return jsonify({"ok": True})


def main() -> None:
    with open(ROOT / "config.json", encoding="utf-8") as f:
        port = int(json.load(f).get("port", 5005))
    # Rebuild on every start, not only when the file is missing: the dashboard is
    # generated code, and after an update the old copy would otherwise linger
    # until the next successful scan. It only reads local snapshots, so it is cheap.
    report_html.generate()
    print(f"\n  FollowLens running:\n    landing   http://localhost:{port}\n    dashboard http://localhost:{port}/dashboard\n")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
