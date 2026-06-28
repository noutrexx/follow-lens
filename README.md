<div align="center">

<img src="assets/banner.png" alt="FollowLens — private Instagram follower analytics" width="100%">

### Track who **followed**, **unfollowed**, **stopped following back**, and **compare accounts** — all on your own machine. No hosted account, no password form.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![Self-hosted](https://img.shields.io/badge/self--hosted-100%25-1fc77d)
![No password](https://img.shields.io/badge/auth-session%20cookie-d6276f)
![Privacy](https://img.shields.io/badge/data-stays%20local-8e24aa)

</div>

---

<img src="assets/dashboard-preview.png" alt="FollowLens dashboard" width="100%">

## ✨ Features

- **📊 Bento dashboard** — followers, following, mutuals and one-way follows at a glance, with animated counters and sparkline trends.
- **🔁 Change history** — every scan is a timestamped snapshot; new and removed accounts are diffed and grouped by date.
- **⚖️ Reciprocity** — instantly see who you follow that doesn't follow back, and who follows you that you don't follow back.
- **🔀 Account comparison** — Venn-style overlap of **shared followers** and **shared following** between any two tracked accounts.
- **🔎 Global search & filters** — search any username across the active account; filter the change feed by *new* / *removed*.
- **⌨️ Keyboard shortcuts** — `/` to search, `R` to rescan, `Esc` to clear.
- **📦 One-click export** — download any account's data as JSON.
- **🔒 Private by design** — uses your existing browser session cookie (never a password), and all data stays in a local folder.

## 🖼 Screenshots

| Account comparison | Change history |
| --- | --- |
| ![Compare](assets/compare.png) | ![Changes](assets/changes.png) |

## 🧠 How it works

1. **Add a session** — paste your `instagram.com` session cookie into `config.json` (no password is ever entered).
2. **Run a scan** — FollowLens fetches the follower / following lists for your selected accounts using Instagram's web endpoints.
3. **Review the diff** — open the dashboard; every run is compared with the previous snapshot to reveal exactly what changed.

> Instagram does not expose *when* a follow happened, so "recent" always means **since your last scan**. The first scan is a baseline; later scans show the changes.

## 🚀 Quick start

```bash
git clone https://github.com/noutrexx/follow-lens.git
cd follow-lens

python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp config.example.json config.json
```

### Get your session cookie (not your password)

1. Open **instagram.com** in your browser while logged in.
2. Open DevTools (`F12`) → **Application** → **Cookies** → `https://www.instagram.com`.
3. Copy the **value** of the `sessionid` cookie.
4. Paste it into the `"sessionid"` field of `config.json`.

### Run

```bash
.venv\Scripts\python.exe run.py
```

Then open **http://localhost:5005** and click **Refresh**, or trigger a scan from the server directly:

```bash
curl -X POST http://localhost:5005/scan
curl -X POST "http://localhost:5005/scan?force=1"   # skip the cooldown
```

## ⚙️ Configuration

`config.json` (copied from `config.example.json`):

| Key | Description |
| --- | --- |
| `username` | Your own Instagram username (used for the `self` target). |
| `sessionid` | Your `sessionid` cookie value. Stays local; git-ignored. |
| `targets` | Accounts to track. `"self"` = your account; add any usernames you can access. |
| `known_ids` | Optional `username → id` map to skip the rate-limited profile lookup. |
| `delay_seconds` / `delay_jitter_seconds` | Randomized delay between requests. |
| `min_scan_interval_seconds` | Cooldown between full scans (default 10 min). |
| `followers_max_passes` | How many union passes to collect the followers list. |

## 🛡 Privacy & safety

- **Local only.** Snapshots and your session cookie live in `config.json` / `data/`, both git-ignored. Nothing is uploaded anywhere.
- **No password.** Authentication uses a session cookie you copy yourself; it never leaves your machine.
- **Conservative scanning.** Randomized delays and a scan cooldown keep request volume low.

> **Disclaimer:** This project is for personal and educational use. Automating access to Instagram may violate its Terms of Service and can lead to rate-limiting or account restrictions. You can only read accounts your own session can already access. Use responsibly and at your own risk.

## 🧱 Tech stack

`Python` · `Flask` · `requests` · vanilla HTML/CSS/JS (no framework, no build step).

## 📁 Project structure

```
follow-lens/
├─ run.py                 # entry point — python run.py
├─ backend/               # application code
│  ├─ server.py           #   Flask server (routes + /scan endpoint)
│  ├─ scanner.py          #   scan orchestration: cooldown, diff, snapshots
│  ├─ igweb.py            #   Instagram web client (session-based, rate-limit aware)
│  ├─ storage.py          #   snapshot storage + diff
│  └─ report_html.py      #   dashboard generator (bento UI)
├─ frontend/              # static pages served by the app
│  ├─ landing.html        #   marketing landing page
│  └─ og.svg              #   social preview image
├─ assets/                # screenshots used in this README
├─ config.example.json    # sample config (copy to config.json)
└─ requirements.txt
```

## 📄 License

[MIT](LICENSE) © noutrexx
