"""Builds viewer.html from data snapshots -- FollowLens bento dashboard."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUT = ROOT / "viewer.html"


def _load(td: Path, kind: str) -> list[dict]:
    snaps = []
    for fp in sorted(td.glob(f"{kind}_*.json")):
        try:
            snaps.append(json.load(open(fp, encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return snaps


def _build_kind(snaps: list[dict]) -> dict | None:
    if not snaps:
        return None
    history, series = [], []
    for s in snaps:
        series.append({"at": s.get("captured_at"), "count": s.get("count", len(s.get("users", {})))})
    for prev, cur in zip(snaps, snaps[1:]):
        pu, cu = prev.get("users", {}), cur.get("users", {})
        pi, ci = set(pu), set(cu)
        added = sorted(cu[i] for i in (ci - pi))
        removed = sorted(pu[i] for i in (pi - ci))
        if added or removed:
            history.append({"at": cur.get("captured_at"), "added": added, "removed": removed})
    cur = snaps[-1]
    return {"current": {"at": cur.get("captured_at"),
                        "count": cur.get("count", len(cur.get("users", {}))),
                        "usernames": sorted(cur.get("users", {}).values())},
            "history": list(reversed(history)), "series": series, "scans": len(snaps)}


def _latest_users(td: Path, kind: str) -> dict:
    snaps = _load(td, kind)
    return snaps[-1].get("users", {}) if snaps else {}


def collect_data() -> dict:
    try:
        cfg = json.load(open(ROOT / "config.json", encoding="utf-8"))
        self_username = cfg.get("username", "self")
    except Exception:  # noqa: BLE001
        self_username = "self"
    targets = {}
    if DATA_DIR.exists():
        for td in sorted(p for p in DATA_DIR.iterdir() if p.is_dir()):
            entry = {}
            for kind in ("following", "followers"):
                b = _build_kind(_load(td, kind))
                if b:
                    entry[kind] = b
            fwg, flw = _latest_users(td, "following"), _latest_users(td, "followers")
            if fwg and flw:
                fs, ls = set(fwg), set(flw)
                entry["compare"] = {"not_following_back": sorted(fwg[i] for i in (fs - ls)),
                                    "not_followed_back": sorted(flw[i] for i in (ls - fs))}
                entry["stats"] = {"following": len(fs), "followers": len(ls), "mutual": len(fs & ls)}
            if entry:
                entry["display"] = self_username if td.name == "self" else td.name
                targets[td.name] = entry
    return {"generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"), "targets": targets}


TPL = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FollowLens &mdash; Instagram follower analytics</title>
<meta name="description" content="FollowLens is a private, self-hosted Instagram analytics dashboard. Track followers, following, mutuals and one-way connections with a clean bento UI and change history.">
<meta name="keywords" content="instagram analytics, follower tracker, unfollowers, mutuals, social graph, FollowLens, ig analytics">
<meta name="author" content="FollowLens">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#070709">
<link rel="canonical" href="https://github.com/">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect width='24' height='24' rx='5' fill='%23d81b60'/%3E%3Cpath d='M2 12s4-6 10-6 10 6 10 6-4 6-10 6S2 12 2 12z' fill='none' stroke='white' stroke-width='1.6'/%3E%3Ccircle cx='12' cy='12' r='2.6' fill='white'/%3E%3C/svg%3E">
<meta property="og:type" content="website">
<meta property="og:site_name" content="FollowLens">
<meta property="og:title" content="FollowLens &mdash; Instagram follower analytics">
<meta property="og:description" content="Track followers, following, mutuals and unfollowers with a clean bento dashboard and full change history.">
<meta property="og:image" content="og.svg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="FollowLens &mdash; Instagram follower analytics">
<meta name="twitter:description" content="Private, self-hosted IG analytics: followers, mutuals, unfollowers and change history.">
<meta name="twitter:image" content="og.svg">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebApplication","name":"FollowLens","applicationCategory":"AnalyticsApplication","operatingSystem":"Any","description":"Private, self-hosted Instagram follower analytics dashboard.","offers":{"@type":"Offer","price":"0","priceCurrency":"USD"}}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
<style>
 :root{
  --bg:#070709;--text:#f4f4f6;--muted:#9090a0;--faint:#5d5d70;
  --glass:rgba(20,20,27,.5);--glass2:rgba(30,30,40,.42);--hover:rgba(255,255,255,.05);
  --line:rgba(255,255,255,.09);--line2:rgba(255,255,255,.17);
  --green:#28d17e;--green-bg:rgba(40,209,126,.1);--red:#ff4d6d;--red-bg:rgba(255,77,109,.1);
  --accent:#d6276f;--grad:linear-gradient(120deg,#f9a825,#f4511e 34%,#d81b60 64%,#8e24aa);
  --r:14px;--r-s:9px;--r-xs:6px;
 }
 *{box-sizing:border-box;} html,body{margin:0;} ::selection{background:rgba(214,39,111,.4);}
 body{background:var(--bg);color:var(--text);font-family:'Inter',-apple-system,'Segoe UI',Roboto,sans-serif;
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;}
 a{color:inherit;text-decoration:none;}
 .mono{font-family:'JetBrains Mono',monospace;}
 /* aurora bg */
 .bgfx{position:fixed;inset:0;z-index:-2;overflow:hidden;pointer-events:none;}
 .blob{position:absolute;border-radius:50%;filter:blur(95px);will-change:transform;}
 .b1{width:560px;height:560px;background:#d81b60;top:-200px;left:-140px;opacity:.16;animation:fl1 24s ease-in-out infinite;}
 .b2{width:480px;height:480px;background:#8e24aa;top:-80px;right:-150px;opacity:.13;animation:fl2 28s ease-in-out infinite;}
 .b3{width:600px;height:600px;background:#f4511e;bottom:-260px;left:32%;opacity:.08;animation:fl3 32s ease-in-out infinite;}
 @keyframes fl1{50%{transform:translate(60px,40px) scale(1.1);}} @keyframes fl2{50%{transform:translate(-50px,30px) scale(1.08);}} @keyframes fl3{50%{transform:translate(40px,-30px) scale(1.12);}}
 .wm{position:absolute;color:#fff;opacity:.03;stroke:#fff;} .wm-eye{width:640px;height:640px;right:-160px;bottom:-170px;} .wm-ring{width:500px;height:500px;left:-170px;top:42%;opacity:.025;}
 .grid-ov{position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:linear-gradient(rgba(255,255,255,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.02) 1px,transparent 1px);
  background-size:48px 48px;mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,#000 28%,transparent 72%);}
 .wrap{max-width:1000px;margin:0 auto;padding:0 22px;}
 /* top bar */
 .bar{position:sticky;top:0;z-index:40;background:rgba(9,9,12,.72);backdrop-filter:blur(18px) saturate(1.3);border-bottom:1px solid var(--line);}
 .bar::after{content:'';position:absolute;left:0;right:0;bottom:-1px;height:1px;background:var(--grad);opacity:.45;}
 .bar-in{display:flex;align-items:center;gap:14px;height:62px;}
 .brand{display:flex;align-items:center;gap:11px;cursor:default;}
 .mark{width:33px;height:33px;border-radius:9px;background:var(--grad);display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(216,27,96,.55),0 0 0 1px rgba(255,255,255,.18) inset;transition:.25s;}
 .brand:hover .mark{transform:rotate(-8deg) scale(1.05);} .mark svg{width:19px;height:19px;stroke:#fff;fill:none;stroke-width:1.9;}
 .mark .pupil{transition:.25s;transform-origin:center;} .brand:hover .mark .pupil{transform:scale(.5);}
 .wm-t{font-weight:800;font-size:19px;letter-spacing:-.4px;} .wm-t small{font-weight:700;color:var(--faint);font-size:10px;letter-spacing:1.6px;margin-left:8px;}
 .gsearch{flex:1;max-width:340px;margin:0 auto;position:relative;}
 .gsearch input{width:100%;padding:9px 12px 9px 36px;border-radius:10px;border:1px solid var(--line);background:var(--glass2);color:var(--text);font:inherit;font-size:13.5px;outline:none;transition:border-color .15s,box-shadow .15s;}
 .gsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(214,39,111,.16);}
 .gsearch input::placeholder{color:var(--faint);}
 .gsearch .si{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--faint);} .gsearch .si svg{width:15px;height:15px;}
 .gsearch kbd{position:absolute;right:9px;top:50%;transform:translateY(-50%);font:600 11px 'JetBrains Mono',monospace;color:var(--faint);background:var(--glass);border:1px solid var(--line);border-radius:5px;padding:1px 6px;}
 .right{display:flex;align-items:center;gap:12px;margin-left:auto;}
 .live{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);background:var(--glass2);border:1px solid var(--line);border-radius:999px;padding:6px 10px;}
 .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 0 rgba(40,209,126,.6);animation:pulse 2.4s infinite;}
 @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(40,209,126,.55);}70%{box-shadow:0 0 0 7px rgba(40,209,126,0);}100%{box-shadow:0 0 0 0 rgba(40,209,126,0);}}
 .ghub{display:flex;color:rgba(255,255,255,.68);transition:.15s;} .ghub:hover{color:var(--text);} .ghub svg{width:19px;height:19px;}
 .btn{display:inline-flex;align-items:center;gap:8px;border:none;cursor:pointer;color:#fff;font-family:inherit;font-size:13.5px;font-weight:600;
  padding:9px 15px;border-radius:9px;background:var(--grad);box-shadow:0 5px 16px rgba(216,27,96,.32);transition:.15s;}
 .btn:hover{filter:brightness(1.08);transform:translateY(-1px);} .btn:active{transform:translateY(0);} .btn:disabled{opacity:.5;cursor:default;box-shadow:none;transform:none;}
 .btn svg{width:15px;height:15px;stroke:#fff;fill:none;stroke-width:2;} .btn.spin svg{animation:spin .8s linear infinite;} @keyframes spin{to{transform:rotate(360deg);}}
 .ic{display:inline-flex;align-items:center;justify-content:center;} .ic svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;}
 @media(max-width:760px){
  .bar-in{height:auto;min-height:76px;flex-wrap:wrap;gap:8px 10px;padding-top:9px;padding-bottom:9px;}
  .brand{order:1;flex:1 1 auto;min-width:0;}
  .wm-t small{display:none;}
  .right{order:2;gap:8px;margin-left:0;}
  .live{display:none;}
  .ghub{display:none;}
  .btn{padding:8px 11px;font-size:0;gap:0;}
  .btn svg{width:16px;height:16px;}
  .gsearch{order:3;flex:1 0 100%;max-width:none;margin:0;}
 }
 /* account switcher */
 .accts{display:inline-flex;gap:4px;padding:4px;margin:22px 0 4px;background:var(--glass);border:1px solid var(--line);border-radius:12px;backdrop-filter:blur(10px);}
 .acct{display:flex;align-items:center;gap:9px;padding:7px 14px 7px 8px;border-radius:9px;cursor:pointer;transition:.14s;color:var(--muted);}
 .acct:hover{background:var(--hover);color:var(--text);} .acct.on{background:var(--grad);color:#fff;}
 .am{width:24px;height:24px;border-radius:50%;background:rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;text-transform:uppercase;}
 .acct.on .am{background:rgba(255,255,255,.22);} .acct .nm{font-size:13.5px;font-weight:600;}
 /* panel */
 .panel{display:none;padding:14px 0 80px;} .panel.on{display:block;animation:f .3s cubic-bezier(.2,.7,.3,1);}
 @keyframes f{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
 /* bento */
 .bento{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:minmax(98px,1fr);gap:12px;}
 @media(max-width:760px){.bento{grid-template-columns:repeat(2,1fr);}}
 .tile{position:relative;background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:16px 17px;backdrop-filter:blur(11px);overflow:hidden;transition:.18s;}
 .tile:hover{border-color:var(--line2);transform:translateY(-2px);}
 .tile::after{content:'';position:absolute;inset:0 0 auto 0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.14),transparent);}
 .b-prof{grid-column:span 2;grid-row:span 2;display:flex;flex-direction:column;}
 @media(max-width:760px){.b-prof{grid-column:span 2;grid-row:span 1;}}
 .pf-top{display:flex;align-items:center;gap:16px;}
 .pav{width:66px;height:66px;border-radius:50%;padding:2.5px;background:var(--grad);flex:none;}
 .pav>span{width:100%;height:100%;border-radius:50%;background:#0c0c10;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;text-transform:uppercase;}
 .pname{font-size:21px;font-weight:800;letter-spacing:-.4px;} .pname a:hover{opacity:.85;} .psub{color:var(--muted);font-size:13px;margin-top:3px;}
 .pf-mid{display:flex;align-items:center;gap:18px;margin-top:auto;padding-top:16px;}
 .donut-wrap{display:flex;align-items:center;gap:11px;}
 .donut{width:64px;height:64px;flex:none;} .donut .d-bg{fill:none;stroke:rgba(255,255,255,.08);stroke-width:7;} .donut .d-fg{fill:none;stroke:url(#grad);stroke-width:7;stroke-linecap:round;transform:rotate(-90deg);transform-origin:center;transition:stroke-dashoffset 1s cubic-bezier(.2,.7,.3,1);}
 .donut .d-t{fill:var(--text);font-size:15px;font-weight:800;text-anchor:middle;font-family:'JetBrains Mono',monospace;}
 .donut-lbl{font-size:12px;color:var(--muted);line-height:1.35;} .donut-lbl b{color:var(--text);font-weight:700;display:block;font-size:14px;}
 .net{margin-left:auto;text-align:right;} .net .nl{font-size:11px;color:var(--faint);} .net .nv{font-size:17px;font-weight:800;margin-top:2px;}
 /* stat tile */
 .st .top{display:flex;align-items:center;justify-content:space-between;color:var(--muted);}
 .st .lbl{font-size:11.5px;font-weight:600;letter-spacing:.02em;} .st .ic{color:var(--faint);}
 .st .num{font-size:25px;font-weight:800;letter-spacing:-.6px;margin-top:8px;line-height:1;font-feature-settings:'tnum';}
 .st .row{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin-top:7px;}
 .st .dl{font-size:11px;color:var(--faint);font-weight:600;display:flex;align-items:center;gap:4px;}
 .up{color:var(--green);} .down{color:var(--red);} .up svg,.down svg{width:11px;height:11px;stroke-width:2.6;}
 .spark{width:74px;height:26px;opacity:.95;} .spark .sp-line{fill:none;stroke:url(#grad);stroke-width:2;stroke-linecap:round;stroke-linejoin:round;} .spark .sp-area{fill:url(#sparkg);opacity:.4;stroke:none;}
 /* sections */
 .sec{margin-top:30px;} .sec-h{display:flex;align-items:center;gap:9px;margin-bottom:14px;}
 .sec-t{font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}
 .sec-h .ic{color:var(--accent);} .pill{background:var(--glass2);border:1px solid var(--line);border-radius:6px;padding:1px 8px;font-size:12px;font-weight:700;color:var(--muted);}
 .filters{display:inline-flex;gap:4px;margin-left:auto;background:var(--glass);border:1px solid var(--line);border-radius:8px;padding:3px;}
 .filters button{border:none;background:none;color:var(--muted);font:inherit;font-size:12px;font-weight:600;padding:4px 11px;border-radius:6px;cursor:pointer;transition:.13s;}
 .filters button.on{background:var(--grad);color:#fff;}
 .ml{font-size:12px;color:var(--faint);margin:16px 0 9px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;}
 .card{background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:15px 17px;margin-bottom:10px;backdrop-filter:blur(10px);}
 .tl{position:relative;padding-left:21px;}
 .tl::before{content:'';position:absolute;left:5px;top:8px;bottom:8px;width:1.5px;background:var(--line2);}
 .tl .tdot{position:absolute;left:0;top:17px;width:11px;height:11px;border-radius:50%;background:var(--grad);box-shadow:0 0 0 3px var(--bg);}
 .when{font-size:12px;color:var(--faint);font-weight:600;margin-bottom:9px;display:flex;align-items:center;gap:6px;}
 .lg{font-size:12px;font-weight:700;margin:10px 0 6px;display:flex;align-items:center;gap:6px;}
 .chips{display:flex;flex-wrap:wrap;gap:6px;}
 .chip{display:inline-flex;align-items:center;padding:5px 10px;border-radius:var(--r-xs);font-size:13px;font-weight:500;border:1px solid transparent;transition:.12s;}
 .chip.add{background:var(--green-bg);color:var(--green);border-color:rgba(40,209,126,.22);}
 .chip.rem{background:var(--red-bg);color:var(--red);border-color:rgba(255,77,109,.22);}
 .chip:hover{filter:brightness(1.18);transform:translateY(-1px);}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:11px;} @media(max-width:760px){.two{grid-template-columns:1fr;}}
 .cmp-t{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:13px;font-weight:700;margin-bottom:12px;}
 .grid{display:flex;flex-wrap:wrap;gap:7px;}
 .grid a{display:inline-flex;align-items:center;gap:7px;background:var(--glass2);border:1px solid var(--line);padding:5px 11px 5px 6px;border-radius:var(--r-s);font-size:13.5px;font-weight:500;transition:.12s;}
 .grid a:hover{border-color:var(--line2);background:var(--hover);transform:translateY(-1px);}
 .grid .gm{width:21px;height:21px;border-radius:50%;background:linear-gradient(135deg,#d6276f,#8e24aa);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;text-transform:uppercase;color:#fff;}
 .empty{color:var(--faint);font-style:italic;font-size:13.5px;}
 details{margin-top:6px;} summary{list-style:none;cursor:pointer;} summary::-webkit-details-marker{display:none;}
 .more{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--accent);font-weight:700;padding:6px 0;}
 details[open] .more .ic{transform:rotate(180deg);}
 .sec-act{display:inline-flex;align-items:center;gap:6px;margin-left:auto;font-size:12px;font-weight:600;color:var(--muted);cursor:pointer;border:1px solid var(--line);background:var(--glass);border-radius:7px;padding:5px 10px;transition:.13s;}
 .sec-act:hover{color:var(--text);border-color:var(--line2);} .sec-act svg{width:13px;height:13px;}
 .hidden{display:none!important;}
 footer{color:var(--faint);font-size:12px;text-align:center;padding:30px 0 14px;}
 footer b{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;font-weight:800;}
 /* compare */
 .cmp-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:16px 0 18px;}
 .cmp-bar .ic{color:var(--accent);} .cmp-bar select{background:var(--glass2);border:1px solid var(--line);color:var(--text);font:inherit;font-size:14px;font-weight:700;padding:9px 13px;border-radius:9px;outline:none;cursor:pointer;}
 .cmp-bar select:focus{border-color:var(--accent);} .cmp-bar .vs{color:var(--faint);font-weight:800;font-size:13px;text-transform:uppercase;letter-spacing:.08em;}
 .venns{display:grid;grid-template-columns:1fr 1fr;gap:12px;} @media(max-width:760px){.venns{grid-template-columns:1fr;}}
 .venn-card{background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:15px 17px;backdrop-filter:blur(11px);}
 .venn svg{width:100%;height:148px;display:block;margin-top:4px;} .venn .vn{fill:var(--text);font-weight:800;font-family:'JetBrains Mono',monospace;text-anchor:middle;} .venn .vl{fill:var(--muted);font-size:11px;text-anchor:middle;font-weight:600;}
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs>
 <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f9a825"/><stop offset=".5" stop-color="#d81b60"/><stop offset="1" stop-color="#8e24aa"/></linearGradient>
 <linearGradient id="sparkg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d6276f" stop-opacity=".55"/><stop offset="1" stop-color="#d6276f" stop-opacity="0"/></linearGradient>
</defs></svg>
<div class="bgfx"><div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>
 <svg class="wm wm-eye" viewBox="0 0 24 24" fill="none" stroke-width=".5"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>
 <svg class="wm wm-ring" viewBox="0 0 24 24" fill="none" stroke-width=".4"><circle cx="12" cy="12" r="11"/><circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="4"/></svg>
</div><div class="grid-ov"></div>
<div class="bar"><div class="wrap bar-in">
 <div class="brand"><div class="mark"><svg viewBox="0 0 24 24"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle class="pupil" cx="12" cy="12" r="3"/></svg></div><div class="wm-t">FollowLens<small>IG ANALYTICS</small></div></div>
 <div class="gsearch"><span class="si ic"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4-4"/></svg></span><input id="gs" placeholder="Search any username..." oninput="gsearch(this.value)"><kbd>/</kbd></div>
 <div class="right">
  <div class="live"><span class="dot"></span>Updated <b id="upd">__GEN__</b></div>
  <a class="ghub" href="https://github.com/" target="_blank" title="GitHub"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.49l-.01-1.9c-2.78.62-3.37-1.21-3.37-1.21-.46-1.18-1.11-1.49-1.11-1.49-.9-.64.07-.62.07-.62 1 .07 1.53 1.06 1.53 1.06.89 1.56 2.34 1.11 2.91.85.09-.66.35-1.11.63-1.36-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.72 0 0 .84-.27 2.75 1.05a9.4 9.4 0 0 1 5 0c1.91-1.32 2.75-1.05 2.75-1.05.55 1.42.2 2.46.1 2.72.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.81-4.57 5.06.36.32.68.94.68 1.9l-.01 2.81c0 .27.18.6.69.49A10.02 10.02 0 0 0 22 12.25C22 6.58 17.52 2 12 2z"/></svg></a>
  <button class="btn" id="rf" onclick="scan()"><svg viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><path d="M20.5 15a9 9 0 1 1-2.1-9.4L23 10"/></svg><span class="t">Refresh</span></button>
 </div>
</div></div>
<div class="wrap"><div class="accts" id="accts"></div><div id="main"></div>
 <footer>built with <b>FollowLens</b> &middot; private &middot; self-hosted &middot; data stays on your machine</footer>
</div>
<script>
const DATA=__DATA__;
const I={
 clock:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></svg>',
 up:'<svg viewBox="0 0 24 24"><line x1="12" y1="19" x2="12" y2="6"/><polyline points="6 12 12 6 18 12"/></svg>',
 down:'<svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="18"/><polyline points="6 12 12 18 18 12"/></svg>',
 trend:'<svg viewBox="0 0 24 24"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
 scale:'<svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M5 7h14M7 7l-3.5 6a3 3 0 0 0 7 0z M17 7l-3.5 6a3 3 0 0 0 7 0z"/><path d="M8 21h8"/></svg>',
 userplus:'<svg viewBox="0 0 24 24"><path d="M15 20v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1"/><circle cx="8.5" cy="8" r="3.5"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>',
 users:'<svg viewBox="0 0 24 24"><path d="M16 20v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1"/><circle cx="9" cy="8" r="3.5"/><path d="M22 20v-1a4 4 0 0 0-3-3.8"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/></svg>',
 dl:'<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
 compare:'<svg viewBox="0 0 24 24"><polyline points="17 2 21 6 17 10"/><path d="M3 12V9a3 3 0 0 1 3-3h15"/><polyline points="7 22 3 18 7 14"/><path d="M21 12v3a3 3 0 0 1-3 3H3"/></svg>',
 chev:'<svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>'
};
const ic=(n,c)=>'<span class="ic'+(c?' '+c:'')+'">'+I[n]+'</span>';
const igl=u=>'https://instagram.com/'+u, ini=n=>(n||'?').slice(0,1), nf=n=>(n||0).toLocaleString('en-US');
// ---- sparkline ----
function spark(series){if(!series||series.length<2)return '<svg class="spark"></svg>';
 const v=series.map(s=>s.count),mn=Math.min(...v),mx=Math.max(...v),rg=(mx-mn)||1,w=74,h=26,n=v.length;
 const pt=v.map((x,i)=>[(i/(n-1))*w,h-3-((x-mn)/rg)*(h-7)]);
 const d=pt.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
 return '<svg class="spark" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none"><path class="sp-area" d="'+d+' L '+w+' '+h+' L 0 '+h+' Z"/><path class="sp-line" d="'+d+'"/></svg>';}
// ---- donut ----
function donut(pct){const r=24,c=2*Math.PI*r,off=c*(1-pct/100);
 return '<svg class="donut" viewBox="0 0 64 64"><circle class="d-bg" cx="32" cy="32" r="'+r+'"/><circle class="d-fg" cx="32" cy="32" r="'+r+'" stroke-dasharray="'+c.toFixed(1)+'" stroke-dashoffset="'+c.toFixed(1)+'" data-off="'+off.toFixed(1)+'"/><text class="d-t" x="32" y="37">'+pct+'%</text></svg>';}
function lastDelta(d){if(!d||!d.history.length)return null;const h=d.history[0];return{a:h.added.length,r:h.removed.length};}
function netChange(d){if(!d||d.series.length<2)return null;return d.series[d.series.length-1].count-d.series[0].count;}
function delHtml(x){if(!x||(!x.a&&!x.r))return '<span class="dl">no change</span>';const p=[];if(x.a)p.push('<span class="up">'+ic('up')+'+'+x.a+'</span>');if(x.r)p.push('<span class="down">'+ic('down')+x.r+'</span>');return '<span class="dl">'+p.join('&nbsp;')+'</span>';}
function statTile(lbl,num,icn,d){
 return '<div class="tile st"><div class="top"><span class="lbl">'+lbl+'</span>'+ic(icn)+'</div>'
  +'<div class="num" data-v="'+(typeof num==='number'?num:0)+'">'+(typeof num==='number'?'0':num)+'</div>'
  +'<div class="row">'+delHtml(lastDelta(d))+spark(d?d.series:null)+'</div></div>';}
function timeline(d,host){const items=d.history.slice(0,12);
 if(!items.length)return '<div class="card"><span class="empty">No changes yet &mdash; at least 2 scans are needed to compare.</span></div>';
 return items.map(h=>{let s='<div class="card tl" data-has="'+((h.added.length?'new ':'')+(h.removed.length?'rem':'')).trim()+'"><div class="tdot"></div><div class="when">'+ic('clock')+(h.at||'').replace('T',' ')+'</div>';
  if(h.added.length)s+='<div class="lg up">'+ic('up')+'New &middot; '+h.added.length+'</div><div class="chips">'+h.added.map(u=>chip(u,'add')).join('')+'</div>';
  if(h.removed.length)s+='<div class="lg down">'+ic('down')+'Removed &middot; '+h.removed.length+'</div><div class="chips">'+h.removed.map(u=>chip(u,'rem')).join('')+'</div>';
  return s+'</div>';}).join('');}
const chip=(u,c)=>'<a class="chip '+c+'" data-u="'+u+'" href="'+igl(u)+'" target="_blank">@'+u+'</a>';
function grid(list,id){return '<div class="grid"'+(id?' id="'+id+'"':'')+'>'+list.map(u=>'<a data-u="'+u+'" href="'+igl(u)+'" target="_blank"><span class="gm">'+ini(u)+'</span>@'+u+'</a>').join('')+'</div>';}
function cmp(title,list){return '<div class="tile" style="padding:15px 17px"><div class="cmp-t"><span>'+title+'</span><span class="pill">'+list.length+'</span></div>'+(list.length?grid(list):'<span class="empty">None</span>')+'</div>';}
function listSection(name,kind,d,label,icn){const lid='l_'+name+'_'+kind;
 return '<div class="sec"><div class="sec-h">'+ic(icn)+'<div class="sec-t">'+label+'</div><span class="pill">'+d.current.count+'</span></div>'
  +'<details><summary><div class="more">Show '+d.current.count+' &middot; '+label+' '+ic('chev')+'</div></summary>'+grid(d.current.usernames,lid)+'</details></div>';}
function panel(name){const t=DATA.targets[name],s=t.stats||{},disp=t.display||name;
 const fwBack=t.compare?t.compare.not_following_back.length:0;
 const pct=s.following?Math.round(s.mutual/s.following*100):0;
 const net=netChange(t.followers);
 let netH='<div class="net"><div class="nl">net followers</div><div class="nv '+(net>0?'up':net<0?'down':'')+'">'+(net==null?'&ndash;':(net>0?'+':'')+net)+'</div></div>';
 // bento
 let h='<div class="bento">';
 h+='<div class="tile b-prof"><div class="pf-top"><div class="pav"><span>'+ini(disp)+'</span></div>'
   +'<div><div class="pname"><a href="'+igl(disp)+'" target="_blank">@'+disp+'</a></div>'
   +'<div class="psub">'+nf(s.following)+' following &middot; '+nf(s.followers)+' followers</div></div></div>'
   +'<div class="pf-mid"><div class="donut-wrap">'+donut(pct)+'<div class="donut-lbl"><b>'+nf(s.mutual)+'</b>mutual<br>follow-back</div></div>'+netH+'</div></div>';
 h+=statTile('Following',s.following,'userplus',t.following);
 h+=statTile('Followers',s.followers,'users',t.followers);
 h+=statTile('Mutual',s.mutual,'scale',null);
 h+=statTile('One-way',fwBack,'trend',null);
 h+='</div>';
 // recent changes with filters
 h+='<div class="sec"><div class="sec-h">'+ic('trend')+'<div class="sec-t">Recent changes</div>'
   +'<div class="filters" data-host="'+name+'"><button class="on" onclick="filt(this,\''+name+'\',\'all\')">All</button><button onclick="filt(this,\''+name+'\',\'new\')">New</button><button onclick="filt(this,\''+name+'\',\'rem\')">Removed</button></div></div>';
 h+='<div id="tl_'+name+'">';
 if(t.following){h+='<div class="ml">In following</div>'+timeline(t.following);}
 if(t.followers){h+='<div class="ml">In followers</div>'+timeline(t.followers);}
 h+='</div></div>';
 // reciprocity
 if(t.compare){const self=name==='self';h+='<div class="sec"><div class="sec-h">'+ic('scale')+'<div class="sec-t">Reciprocity</div></div><div class="two">'
  +cmp(self?'You follow, they don&rsquo;t follow back':'@'+disp+' follows, they don&rsquo;t follow back',t.compare.not_following_back)
  +cmp(self?'They follow you, you don&rsquo;t follow back':'They follow @'+disp+', no follow back',t.compare.not_followed_back)+'</div></div>';}
 // lists + export
 h+='<div class="sec"><div class="sec-h">'+ic('dl')+'<div class="sec-t">Lists &amp; export</div><div class="sec-act" onclick="expt(\''+name+'\')">'+ic('dl')+'Export JSON</div></div>';
 if(t.following)h+=listSection(name,'following',t.following,'Following','userplus');
 if(t.followers)h+=listSection(name,'followers',t.followers,'Followers','users');
 h+='</div>';
 return h;}
// ---- interactions ----
function countUp(panel){panel.querySelectorAll('.num[data-v]').forEach(el=>{const tgt=+el.dataset.v;if(!tgt)return;const t0=performance.now();
 (function step(t){const p=Math.min(1,(t-t0)/750),e=1-Math.pow(1-p,3);el.textContent=nf(Math.round(tgt*e));if(p<1)requestAnimationFrame(step);})(performance.now());});}
function animDonut(panel){panel.querySelectorAll('.d-fg').forEach(c=>{requestAnimationFrame(()=>{c.style.strokeDashoffset=c.dataset.off;});});}
function filt(btn,name,mode){btn.parentNode.querySelectorAll('button').forEach(b=>b.classList.remove('on'));btn.classList.add('on');
 document.querySelectorAll('#tl_'+name+' .tl').forEach(c=>{const h=c.dataset.has||'';c.classList.toggle('hidden',mode!=='all'&&!h.includes(mode));});}
function gsearch(q){q=q.trim().toLowerCase();const p=document.querySelector('.panel.on');if(!p)return;
 if(q)p.querySelectorAll('details').forEach(d=>d.open=true);
 p.querySelectorAll('[data-u]').forEach(a=>{a.style.display=(!q||a.dataset.u.toLowerCase().includes(q))?'':'none';});}
function expt(name){const t=DATA.targets[name],disp=t.display||name;
 const out={account:disp,exported_at:new Date().toISOString(),stats:t.stats,
  following:t.following?t.following.current.usernames:[],followers:t.followers?t.followers.current.usernames:[],
  reciprocity:t.compare,history:{following:t.following?t.following.history:[],followers:t.followers?t.followers.history:[]}};
 const b=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});const a=document.createElement('a');
 a.href=URL.createObjectURL(b);a.download='followlens_'+disp+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500);toast('Exported @'+disp+'.json');}
function scan(){const b=document.getElementById('rf'),t=b.querySelector('.t');b.disabled=true;b.classList.add('spin');t.textContent='Scanning...';
 fetch('/scan',{method:'POST'}).then(r=>r.json()).then(j=>{if(j.ok){t.textContent='Updated';setTimeout(()=>location.reload(),450);}else{toast(j.error||'error');b.disabled=false;b.classList.remove('spin');t.textContent='Refresh';}})
 .catch(()=>{toast('Cannot reach server (is server.py running?)');b.disabled=false;b.classList.remove('spin');t.textContent='Refresh';});}
function toast(x){let e=document.getElementById('tt');if(!e){e=document.createElement('div');e.id='tt';
 e.style.cssText='position:fixed;left:50%;bottom:26px;transform:translateX(-50%);background:rgba(20,20,27,.94);backdrop-filter:blur(10px);border:1px solid var(--line2);color:#fff;padding:11px 18px;border-radius:10px;font-size:14px;z-index:60;box-shadow:0 12px 40px rgba(0,0,0,.55);transition:.3s';document.body.appendChild(e);}
 e.textContent=x;e.style.opacity='1';clearTimeout(e._t);e._t=setTimeout(()=>e.style.opacity='0',4200);}
function show(name){document.querySelectorAll('.acct').forEach(x=>x.classList.toggle('on',x.dataset.n===name));
 document.querySelectorAll('.panel').forEach(x=>x.classList.remove('on'));const p=document.getElementById('pn_'+name);p.classList.add('on');
 countUp(p);animDonut(p);window.scrollTo({top:0,behavior:'smooth'});}
// keyboard
document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement.id!=='gs'){e.preventDefault();document.getElementById('gs').focus();}
 else if(e.key==='Escape'){const g=document.getElementById('gs');g.value='';gsearch('');g.blur();}
 else if((e.key==='r'||e.key==='R')&&!/input/i.test(document.activeElement.tagName)){scan();}});
// ---- compare ----
const interU=(a,b)=>{const s=new Set(b.map(x=>x.toLowerCase()));return a.filter(x=>s.has(x.toLowerCase()));};
function venn(dispA,dispB,A,B){const both=interU(A,B),oa=A.length-both.length,ob=B.length-both.length;
 const svg='<svg viewBox="0 0 300 150"><circle cx="112" cy="74" r="60" fill="rgba(216,27,96,.16)" stroke="#d6276f" stroke-width="1.5"/><circle cx="188" cy="74" r="60" fill="rgba(142,36,170,.16)" stroke="#8e24aa" stroke-width="1.5"/>'
  +'<text class="vn" x="72" y="72" font-size="17">'+oa+'</text><text class="vl" x="72" y="90">@'+dispA.slice(0,9)+'</text>'
  +'<text class="vn" x="150" y="72" font-size="21">'+both.length+'</text><text class="vl" x="150" y="90">shared</text>'
  +'<text class="vn" x="228" y="72" font-size="17">'+ob+'</text><text class="vl" x="228" y="90">@'+dispB.slice(0,9)+'</text></svg>';
 return {svg,both};}
function comparePanel(){const opts=names.map(n=>'<option value="'+n+'">@'+(DATA.targets[n].display||n)+'</option>').join('');
 return '<div class="cmp-bar">'+ic('compare')+'<select id="cmpA" onchange="runCompare()">'+opts+'</select><span class="vs">vs</span><select id="cmpB" onchange="runCompare()">'+opts+'</select></div><div id="cmpOut"></div>';}
function runCompare(){const a=document.getElementById('cmpA').value,b=document.getElementById('cmpB').value,out=document.getElementById('cmpOut');
 const ta=DATA.targets[a],tb=DATA.targets[b],da=ta.display||a,db=tb.display||b;
 if(a===b){out.innerHTML='<div class="card"><span class="empty">Pick two different accounts to compare.</span></div>';return;}
 const aF=ta.followers?ta.followers.current.usernames:[],bF=tb.followers?tb.followers.current.usernames:[];
 const aG=ta.following?ta.following.current.usernames:[],bG=tb.following?tb.following.current.usernames:[];
 const vF=venn(da,db,aF,bF),vG=venn(da,db,aG,bG);
 let h='<div class="venns"><div class="venn-card"><div class="cmp-t"><span>Shared followers</span><span class="pill">'+vF.both.length+'</span></div><div class="venn">'+vF.svg+'</div></div>'
  +'<div class="venn-card"><div class="cmp-t"><span>Shared following</span><span class="pill">'+vG.both.length+'</span></div><div class="venn">'+vG.svg+'</div></div></div>';
 h+='<div class="sec"><div class="sec-h">'+ic('users')+'<div class="sec-t">People who follow both</div><span class="pill">'+vF.both.length+'</span></div>'+(vF.both.length?grid(vF.both):'<div class="card"><span class="empty">No shared followers.</span></div>')+'</div>';
 h+='<div class="sec"><div class="sec-h">'+ic('userplus')+'<div class="sec-t">Accounts both follow</div><span class="pill">'+vG.both.length+'</span></div>'+(vG.both.length?grid(vG.both):'<div class="card"><span class="empty">No shared following.</span></div>')+'</div>';
 out.innerHTML=h;}
// build
const names=Object.keys(DATA.targets),accts=document.getElementById('accts'),main=document.getElementById('main');
if(!names.length)main.innerHTML='<div class="card" style="margin-top:24px"><span class="empty">No data yet. Click Refresh at the top right.</span></div>';
else{names.forEach((n,i)=>{const disp=DATA.targets[n].display||n;const a=document.createElement('div');a.className='acct'+(i?'':' on');a.dataset.n=n;
 a.innerHTML='<span class="am">'+ini(disp)+'</span><span class="nm">@'+disp+'</span>';a.onclick=()=>show(n);accts.appendChild(a);
 const p=document.createElement('div');p.className='panel'+(i?'':' on');p.id='pn_'+n;p.innerHTML=panel(n);main.appendChild(p);});
 if(names.length>=2){const ca=document.createElement('div');ca.className='acct';ca.dataset.n='__cmp__';
  ca.innerHTML='<span class="am">'+ic('compare')+'</span><span class="nm">Compare</span>';ca.onclick=()=>show('__cmp__');accts.appendChild(ca);
  const cp=document.createElement('div');cp.className='panel';cp.id='pn___cmp__';cp.innerHTML=comparePanel();main.appendChild(cp);
  document.getElementById('cmpB').selectedIndex=1;runCompare();}
 const first=document.querySelector('.panel.on');if(first){countUp(first);animDonut(first);}}
</script></body></html>
"""


def generate() -> Path:
    data = collect_data()
    html = TPL.replace("__GEN__", data["generated_at"]).replace("__DATA__", json.dumps(data, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    print(generate())
