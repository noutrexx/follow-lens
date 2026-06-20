"""Yerel sunucu. Tarayıcıda http://localhost:PORT açılır.
'🔄 Yenile' butonu /scan'i tetikler -> tarama çalışır, sayfa güncellenir.
Komutu sunucuya da gönderebilirsin:  curl -X POST http://localhost:5005/scan
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

import report_html
import scanner

ROOT = Path(__file__).parent
app = Flask(__name__)
_lock = threading.Lock()


@app.route("/")
def landing():
    resp = send_file(ROOT / "landing.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/dashboard")
@app.route("/viewer.html")
def dashboard():
    out = ROOT / "viewer.html"
    if not out.exists():
        report_html.generate()
    resp = send_file(out)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/assets/<path:name>")
def assets(name: str):
    return send_from_directory(ROOT / "assets", name)


@app.route("/scan", methods=["POST", "GET"])
def scan():
    if not _lock.acquire(blocking=False):
        return jsonify({"ok": False, "error": "A scan is already running."}), 409
    force = request.args.get("force") in ("1", "true", "yes")
    try:
        return jsonify(scanner.run_scan(force=force))
    finally:
        _lock.release()


@app.route("/og.svg")
def og():
    return send_file(ROOT / "og.svg")


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    cfg = json.load(open(ROOT / "config.json", encoding="utf-8"))
    port = int(cfg.get("port", 5005))
    if not (ROOT / "viewer.html").exists():
        report_html.generate()
    print(f"\n  FollowLens landing: http://localhost:{port}\n  dashboard: http://localhost:{port}/dashboard\n")
    app.run(host="127.0.0.1", port=port, debug=False)
