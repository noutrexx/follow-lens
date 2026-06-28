"""Local Flask server.

Open http://localhost:PORT in the browser. The dashboard "Refresh" button calls
/scan, which runs a scan and regenerates the dashboard. You can also trigger a
scan directly:  curl -X POST http://localhost:5005/scan
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

import report_html
import scanner

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


@app.route("/og.svg")
def og():
    return send_file(FRONTEND / "og.svg")


@app.route("/scan", methods=["POST", "GET"])
def scan():
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
    cfg = json.load(open(ROOT / "config.json", encoding="utf-8"))
    port = int(cfg.get("port", 5005))
    if not (FRONTEND / "viewer.html").exists():
        report_html.generate()
    print(f"\n  FollowLens running:\n    landing   http://localhost:{port}\n    dashboard http://localhost:{port}/dashboard\n")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
