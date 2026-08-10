"""Builds viewer.html from data snapshots -- FollowLens bento dashboard."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT = ROOT / "frontend" / "viewer.html"


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
                        # kept in API order (most recent follow first) so the UI can sort by recency
                        "usernames": list(cur.get("users", {}).values())},
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
<script>/* Apply the saved theme before first paint so the page never flashes. */
(function(){try{var t=localStorage.getItem('fl-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>
<link rel="canonical" href="https://github.com/">
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2032%2032%27%3E%3Cdefs%3E%3ClinearGradient%20id%3D%27g%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%2732%27%20y2%3D%2732%27%20gradientUnits%3D%27userSpaceOnUse%27%3E%3Cstop%20stop-color%3D%27%23f9a825%27%2F%3E%3Cstop%20offset%3D%27.38%27%20stop-color%3D%27%23f4511e%27%2F%3E%3Cstop%20offset%3D%27.72%27%20stop-color%3D%27%23d81b60%27%2F%3E%3Cstop%20offset%3D%271%27%20stop-color%3D%27%238e24aa%27%2F%3E%3C%2FlinearGradient%3E%3C%2Fdefs%3E%3Crect%20width%3D%2732%27%20height%3D%2732%27%20rx%3D%278%27%20fill%3D%27url%28%23g%29%27%2F%3E%3Cpath%20d%3D%27M4.5%2016C7.5%2011%2011.4%208.5%2016%208.5S24.5%2011%2027.5%2016c-3%205-6.9%207.5-11.5%207.5S7.5%2021%204.5%2016Z%27%20fill%3D%27none%27%20stroke%3D%27%23fff%27%20stroke-width%3D%272.3%27%20stroke-linejoin%3D%27round%27%2F%3E%3Ccircle%20cx%3D%2716%27%20cy%3D%2716%27%20r%3D%273.7%27%20fill%3D%27%23fff%27%2F%3E%3C%2Fsvg%3E">
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
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      /* bound to the CSS variables below, so every utility is theme-aware */
      colors: {
        page: 'var(--bg)', surface: 'var(--glass)', surface2: 'var(--glass2)',
        body: 'var(--text)', muted: 'var(--muted)', faint: 'var(--faint)',
        line: 'var(--line)', line2: 'var(--line2)',
        add: 'var(--green)', del: 'var(--red)', accent: 'var(--accent)',
        brand: { amber: '#f9a825', orange: '#f4511e', pink: '#d81b60', violet: '#8e24aa' },
      },
      maxWidth: { shell: '58rem' },
      keyframes: {
        drift1: { '50%': { transform: 'translate(60px,40px) scale(1.1)' } },
        drift2: { '50%': { transform: 'translate(-50px,30px) scale(1.08)' } },
        drift3: { '50%': { transform: 'translate(40px,-30px) scale(1.12)' } },
        rise:   { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'none' } },
        pulseRing: { '0%': { boxShadow: '0 0 0 0 rgba(40,209,126,.55)' }, '70%': { boxShadow: '0 0 0 7px rgba(40,209,126,0)' }, '100%': { boxShadow: '0 0 0 0 rgba(40,209,126,0)' } },
      },
      animation: {
        drift1: 'drift1 24s ease-in-out infinite', drift2: 'drift2 28s ease-in-out infinite',
        drift3: 'drift3 32s ease-in-out infinite', rise: 'rise .3s cubic-bezier(.2,.7,.3,1)',
        pulseRing: 'pulseRing 2.4s infinite',
      },
    },
  },
};
</script>
<style type="text/tailwindcss">
 :root{
  color-scheme:dark;
  --bg:#08080c;--text:#f4f4f6;--muted:#9090a0;--faint:#5d5d70;
  --glass:rgba(255,255,255,.035);--glass2:rgba(255,255,255,.055);--hover:rgba(255,255,255,.06);
  --line:rgba(255,255,255,.10);--line2:rgba(255,255,255,.19);
  --green:#28d17e;--green-bg:rgba(40,209,126,.09);--red:#ff4d6d;--red-bg:rgba(255,77,109,.09);
  --accent:#ff6b9c;--grad:linear-gradient(120deg,#f9a825,#f4511e 34%,#d81b60 64%,#8e24aa);
  --r:14px;--r-s:9px;--r-xs:6px;
  --bar-bg:rgba(8,8,12,.8);--grid-line:rgba(255,255,255,.022);
  --track:rgba(255,255,255,.08);--av-bg:#0d0d13;--av-chip:rgba(255,255,255,.14);
  --wm-c:#fff;--wm-o:.03;--blob-o1:.13;--blob-o2:.10;--blob-o3:.07;
  --on-grad:#fff;--ring:rgba(255,107,156,.18);
 }
 /* Light theme: follow the system unless the toggle pinned a choice, and let an
    explicit data-theme win in both directions. */
 @media(prefers-color-scheme:light){
  :root:not([data-theme="dark"]){
   color-scheme:light;
   --bg:#f7f7fa;--text:#15151c;--muted:#5c5c6e;--faint:#82829a;
   --glass:rgba(255,255,255,.7);--glass2:rgba(255,255,255,.55);--hover:rgba(16,16,28,.045);
   --line:rgba(16,16,28,.11);--line2:rgba(16,16,28,.2);
   --green:#0a8f52;--green-bg:rgba(10,143,82,.1);--red:#d31f43;--red-bg:rgba(211,31,67,.08);
   --accent:#c2185b;
   --bar-bg:rgba(247,247,250,.82);--grid-line:rgba(16,16,28,.035);
   --track:rgba(16,16,28,.09);--av-bg:#fff;--av-chip:rgba(16,16,28,.08);
   --wm-c:#15151c;--wm-o:.035;--blob-o1:.11;--blob-o2:.09;--blob-o3:.06;
   --ring:rgba(194,24,91,.18);
  }
 }
 :root[data-theme="light"]{
  color-scheme:light;
  --bg:#f7f7fa;--text:#15151c;--muted:#5c5c6e;--faint:#82829a;
  --glass:rgba(255,255,255,.7);--glass2:rgba(255,255,255,.55);--hover:rgba(16,16,28,.045);
  --line:rgba(16,16,28,.11);--line2:rgba(16,16,28,.2);
  --green:#0a8f52;--green-bg:rgba(10,143,82,.1);--red:#d31f43;--red-bg:rgba(211,31,67,.08);
  --accent:#c2185b;
  --bar-bg:rgba(247,247,250,.82);--grid-line:rgba(16,16,28,.035);
  --track:rgba(16,16,28,.09);--av-bg:#fff;--av-chip:rgba(16,16,28,.08);
  --wm-c:#15151c;--wm-o:.035;--blob-o1:.11;--blob-o2:.09;--blob-o3:.06;
  --ring:rgba(194,24,91,.18);
 }
 html,body{@apply m-0;}
 body{@apply bg-page font-sans text-[15px] leading-normal text-body antialiased selection:bg-brand-pink/40;}
 a{@apply text-inherit no-underline;}
 .mono{@apply font-mono;}
 /* ambient background */
 .bgfx{@apply pointer-events-none fixed inset-0 -z-20 overflow-hidden;}
 .blob{@apply absolute rounded-full blur-[95px] will-change-transform;}
 .b1{@apply h-[560px] w-[560px] -left-36 -top-52 animate-drift1;background:#d81b60;opacity:var(--blob-o1);}
 .b2{@apply h-[480px] w-[480px] -right-40 -top-20 animate-drift2;background:#8e24aa;opacity:var(--blob-o2);}
 .b3{@apply h-[600px] w-[600px] -bottom-64 left-1/3 animate-drift3;background:#f4511e;opacity:var(--blob-o3);}
 .wm{@apply absolute;color:var(--wm-c);stroke:var(--wm-c);opacity:var(--wm-o);}
 .wm-eye{@apply h-[640px] w-[640px] -right-40 -bottom-44;}
 .wm-ring{@apply h-[500px] w-[500px] -left-44 top-[42%];opacity:calc(var(--wm-o) * .83);}
 .grid-ov{@apply pointer-events-none fixed inset-0 -z-10 bg-[size:44px_44px] [mask-image:radial-gradient(ellipse_75%_55%_at_50%_0%,#000_30%,transparent_75%)];
  background-image:linear-gradient(var(--grid-line) 1px,transparent 1px),linear-gradient(90deg,var(--grid-line) 1px,transparent 1px);}
 .wrap{@apply mx-auto max-w-shell px-5;}
 /* top bar */
 .bar{@apply sticky top-0 z-40 border-b border-line backdrop-blur-xl;background:var(--bar-bg);}
 .bar-in{@apply flex h-14 items-center gap-3.5;}
 .brand{@apply flex cursor-default items-center gap-2.5;}
 .mark{@apply grid h-8 w-8 flex-none place-items-center rounded-[10px] shadow-lg shadow-brand-pink/25 transition;background:var(--grad);}
 .brand:hover .mark{@apply -rotate-6 scale-105;}
 .mark svg{@apply h-4 w-4 fill-none stroke-white stroke-[1.9];}
 .mark .pupil{@apply origin-center transition;} .brand:hover .mark .pupil{@apply scale-50;}
 .wm-t{@apply text-[17px] font-black tracking-tight;}
 .wm-t small{@apply ml-2 font-mono text-[10px] font-semibold uppercase tracking-[.16em] text-faint;}
 .gsearch{@apply relative mx-auto max-w-[320px] flex-1;}
 .gsearch input{@apply w-full rounded-lg border border-line bg-surface2 py-2 pl-9 pr-3 font-sans text-[13px] text-body outline-none transition;}
 .gsearch input:focus{@apply border-accent;box-shadow:0 0 0 3px var(--ring);}
 .gsearch input::placeholder{@apply text-faint;}
 .gsearch .si{@apply absolute left-3 top-1/2 -translate-y-1/2 text-faint;} .gsearch .si svg{@apply h-[15px] w-[15px];}
 .gsearch kbd{@apply absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-line bg-surface px-1.5 font-mono text-[11px] font-semibold text-faint;}
 .right{@apply ml-auto flex items-center gap-2.5;}
 .live{@apply flex items-center gap-2 rounded-full border border-line bg-surface2 px-2.5 py-1.5 font-mono text-[11px] text-muted;}
 .dot{@apply h-[7px] w-[7px] animate-pulseRing rounded-full;background:var(--green);}
 .ghub{@apply flex text-muted transition-colors hover:text-body;} .ghub svg{@apply h-[18px] w-[18px];}
 .btn{@apply inline-flex cursor-pointer items-center gap-2 rounded-lg border-0 px-4 py-2 font-sans text-[13px] font-bold text-white shadow-lg shadow-brand-pink/25 transition;background:linear-gradient(90deg,#f4511e,#d81b60);}
 .btn:hover{@apply brightness-110;} .btn:disabled{@apply cursor-default opacity-50 shadow-none;}
 .btn svg{@apply h-[15px] w-[15px] fill-none stroke-white stroke-2;} .btn.spin svg{@apply animate-spin;}
 .ic{@apply inline-flex items-center justify-center;}
 .ic svg{@apply h-[15px] w-[15px] fill-none stroke-current stroke-[1.8] [stroke-linecap:round] [stroke-linejoin:round];}
 @media(max-width:760px){
  .bar-in{@apply h-auto min-h-[76px] flex-wrap gap-x-2.5 gap-y-2 py-2.5;}
  .brand{@apply order-1 min-w-0 flex-auto;}
  .wm-t small,.live,.ghub{display:none;}
  .right{@apply order-2 ml-0 gap-2;}
  .btn{@apply gap-0 px-3 py-2 text-[0px];} .btn svg{@apply h-4 w-4;}
  .gsearch{@apply order-3 mx-0 max-w-none flex-[1_0_100%];}
 }
 /* account switcher */
 .accts{@apply my-5 mb-1 inline-flex max-w-full gap-1 overflow-x-auto rounded-xl border border-line bg-surface p-1;scrollbar-width:none;}
 .accts::-webkit-scrollbar{display:none;}
 .acct{@apply flex-none;}
 .acct{@apply flex cursor-pointer items-center gap-2.5 rounded-lg py-1.5 pl-2 pr-3.5 text-muted transition;}
 .acct:hover{@apply text-body;background:var(--hover);}
 .acct.on{@apply text-white;background:var(--grad);}
 .am{@apply flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold uppercase;background:var(--av-chip);}
 .acct.on .am{@apply bg-white/25;} .acct .nm{@apply text-[13px] font-semibold;}
 /* panel */
 .panel{@apply pb-20 pt-3.5;display:none;} .panel.on{@apply animate-rise;display:block;}
 /* bento */
 .bento{@apply grid grid-cols-4 gap-3;grid-auto-rows:minmax(96px,1fr);}
 @media(max-width:760px){.bento{@apply grid-cols-2;}}
 .tile{@apply relative overflow-hidden rounded-xl border border-line bg-surface px-4 py-4 transition-colors;}
 .tile:hover{@apply border-line2;}
 .b-prof{@apply col-span-2 row-span-2 flex flex-col;}
 @media(max-width:760px){.b-prof{@apply col-span-2 row-span-1;}}
 .pf-top{@apply flex items-center gap-4;}
 .pav{@apply h-16 w-16 flex-none rounded-full p-[2.5px];background:var(--grad);}
 .pav>span{@apply flex h-full w-full items-center justify-center rounded-full text-[26px] font-bold uppercase;background:var(--av-bg);}
 .pname{@apply text-xl font-extrabold tracking-tight;} .pname a:hover{@apply opacity-85;}
 .psub{@apply mt-0.5 font-mono text-[12px] text-muted;}
 .pf-mid{@apply mt-auto flex items-center gap-4 pt-4;}
 .donut-wrap{@apply flex items-center gap-3;}
 .donut{@apply h-16 w-16 flex-none;}
 .donut .d-bg{fill:none;stroke:var(--track);stroke-width:7;}
 .donut .d-fg{fill:none;stroke:url(#grad);stroke-width:7;stroke-linecap:round;transform:rotate(-90deg);transform-origin:center;transition:stroke-dashoffset 1s cubic-bezier(.2,.7,.3,1);}
 .donut .d-t{@apply font-mono text-[15px] font-extrabold [text-anchor:middle];fill:var(--text);}
 .donut-lbl{@apply text-xs leading-snug text-muted;} .donut-lbl b{@apply block text-sm font-bold text-body;}
 .net{@apply ml-auto text-right;}
 .net .nl{@apply font-mono text-[10px] uppercase tracking-widest text-faint;} .net .nv{@apply mt-0.5 text-[17px] font-extrabold;}
 /* stat tile */
 .st .top{@apply flex items-center justify-between text-muted;}
 .st .lbl{@apply font-mono text-[10px] font-semibold uppercase tracking-[.12em];} .st .ic{@apply text-faint;}
 .st .num{@apply mt-2 text-[25px] font-extrabold leading-none tracking-tight [font-feature-settings:'tnum'];}
 .st .row{@apply mt-1.5 flex items-end justify-between gap-2;}
 .st .dl{@apply flex items-center gap-1 font-mono text-[10px] font-semibold text-faint;}
 .up{@apply text-add;} .down{@apply text-del;} .up svg,.down svg{@apply h-[11px] w-[11px] stroke-[2.6];}
 .spark{@apply h-[26px] w-[74px];}
 .spark .sp-line{fill:none;stroke:url(#grad);stroke-width:2;stroke-linecap:round;stroke-linejoin:round;}
 .spark .sp-area{fill:url(#sparkg);opacity:.4;stroke:none;}
 /* sections */
 .sec{@apply mt-8;} .sec-h{@apply mb-3.5 flex items-center gap-2.5;}
 .sec-t{@apply font-mono text-[11px] font-bold uppercase tracking-[.18em] text-accent;}
 .sec-h .ic{@apply text-accent;}
 .pill{@apply rounded border border-line bg-surface2 px-2 font-mono text-[11px] font-semibold text-muted;}
 .filters{@apply ml-auto inline-flex gap-1 rounded-lg border border-line bg-surface p-[3px];}
 .filters button{@apply cursor-pointer rounded-md border-0 bg-transparent px-2.5 py-1 font-sans text-xs font-semibold text-muted transition;}
 .filters button.on{@apply text-white;background:var(--grad);}
 .ml{@apply mb-2 mt-4 font-mono text-[10px] font-semibold uppercase tracking-[.14em] text-faint;}
 .card{@apply mb-2.5 rounded-xl border border-line bg-surface px-4 py-4;}
 .tl{@apply relative pl-5;}
 .tl::before{content:'';@apply absolute bottom-2 left-[5px] top-2 w-px;background:var(--line2);}
 .tl .tdot{@apply absolute left-0 top-4 h-2.5 w-2.5 rounded-full;background:var(--grad);box-shadow:0 0 0 3px var(--bg);}
 .when{@apply mb-2 flex items-center gap-1.5 font-mono text-[11px] font-semibold text-faint;}
 .lg{@apply mb-1.5 mt-2.5 flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase tracking-wider;}
 .chips{@apply flex flex-wrap gap-1.5;}
 .chip{@apply inline-flex items-center rounded-md border border-transparent px-2.5 py-1 font-mono text-[12.5px] transition;}
 .chip.add{@apply text-add;background:var(--green-bg);border-color:var(--green-bg);}
 .chip.rem{@apply text-del;background:var(--red-bg);border-color:var(--red-bg);}
 .chip:hover{@apply brightness-125;}
 .two{@apply grid grid-cols-2 gap-2.5;} @media(max-width:760px){.two{@apply grid-cols-1;}}
 .cmp-t{@apply mb-3 flex items-center justify-between gap-2.5 text-[13px] font-bold;}
 .grid{@apply flex flex-wrap gap-1.5;}
 .grid a{@apply inline-flex items-center gap-2 rounded-lg border border-line bg-surface2 py-1 pl-1.5 pr-3 text-[13px] transition;}
 .grid a:hover{@apply border-line2;background:var(--hover);}
 .grid .gm{@apply flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold uppercase text-white;background:linear-gradient(135deg,#d81b60,#8e24aa);}
 .empty{@apply text-[13px] italic text-faint;}
 details{@apply mt-1.5;} summary{@apply cursor-pointer list-none;} summary::-webkit-details-marker{display:none;}
 .more{@apply inline-flex items-center gap-1.5 py-1.5 text-[13px] font-bold text-accent;}
 details[open] .more .ic{transform:rotate(180deg);}
 .sortbar{@apply mb-3 mt-0.5 inline-flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-faint;}
 .sortbar button{@apply cursor-pointer rounded-md border border-line bg-surface px-3 py-1 font-sans text-xs font-semibold normal-case tracking-normal text-muted transition;}
 .sortbar button:hover{@apply border-line2 text-body;}
 .sortbar button.on{@apply border-transparent text-white;background:var(--grad);}
 .sec-act{@apply ml-auto inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1 text-xs font-semibold text-muted transition;}
 .sec-act:hover{@apply border-line2 text-body;} .sec-act svg{@apply h-3 w-3;}
 .hidden{@apply !hidden;}
 footer{@apply py-8 text-center font-mono text-[11px] text-faint;}
 footer b{@apply bg-clip-text font-bold text-transparent;background:var(--grad);}
 /* compare */
 .cmp-bar{@apply my-4 flex flex-wrap items-center gap-2.5;}
 .cmp-bar .ic{@apply text-accent;}
 .cmp-bar select{@apply cursor-pointer rounded-lg border border-line bg-surface2 px-3 py-2 font-sans text-sm font-bold text-body outline-none;}
 .cmp-bar select:focus{@apply border-accent;}
 .cmp-bar .vs{@apply font-mono text-[11px] font-bold uppercase tracking-[.18em] text-faint;}
 .venns{@apply grid grid-cols-2 gap-3;} @media(max-width:760px){.venns{@apply grid-cols-1;}}
 .venn-card{@apply rounded-xl border border-line bg-surface px-4 py-4;}
 .venn svg{@apply mt-1 block h-[148px] w-full;}
 .venn .vn{@apply font-mono font-extrabold [text-anchor:middle];fill:var(--text);}
 .venn .vl{@apply text-[11px] font-semibold [text-anchor:middle];fill:var(--muted);}
 /* theme toggle */
 .tgl{@apply inline-flex h-[34px] w-[34px] flex-none cursor-pointer items-center justify-center rounded-lg border border-line bg-surface2 p-0 text-muted transition;}
 .tgl:hover{@apply border-line2 text-body;}
 .tgl svg{@apply h-4 w-4 fill-none stroke-current stroke-[1.9] [stroke-linecap:round] [stroke-linejoin:round];}
 .tgl .moon{display:none;}
 :root[data-theme="light"] .tgl .moon{display:block;} :root[data-theme="light"] .tgl .sun{display:none;}
 @media(prefers-color-scheme:light){
  :root:not([data-theme="dark"]) .tgl .moon{display:block;}
  :root:not([data-theme="dark"]) .tgl .sun{display:none;}
 }
 /* keyboard users get a visible focus ring; mouse users do not */
 :focus-visible{@apply rounded outline outline-2 outline-offset-2 outline-accent;}
 /* Respect the OS "reduce motion" preference: keep the layout, drop the movement. */
 @media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;
   transition-duration:.01ms!important;scroll-behavior:auto!important;}
  .blob,.dot{animation:none;}
 }
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
  <button class="tgl" id="tg" onclick="toggleTheme()" title="Switch theme (T)" aria-label="Switch colour theme"><svg class="sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.4M12 19.6V22M4.2 4.2l1.7 1.7M18.1 18.1l1.7 1.7M2 12h2.4M19.6 12H22M4.2 19.8l1.7-1.7M18.1 5.9l1.7-1.7"/></svg><svg class="moon" viewBox="0 0 24 24"><path d="M20.5 14.3A8.6 8.6 0 0 1 9.7 3.5a8.6 8.6 0 1 0 10.8 10.8z"/></svg></button>
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
function grid(list,id){return '<div class="grid"'+(id?' id="'+id+'"':'')+'>'+list.map((u,i)=>'<a data-u="'+u+'" data-i="'+i+'" href="'+igl(u)+'" target="_blank"><span class="gm">'+ini(u)+'</span>@'+u+'</a>').join('')+'</div>';}
function sortList(btn,id,mode){btn.parentNode.querySelectorAll('button').forEach(b=>b.classList.remove('on'));btn.classList.add('on');
 const box=document.getElementById(id);if(!box)return;const items=[...box.children];
 if(mode==='az')items.sort((a,b)=>a.dataset.u.localeCompare(b.dataset.u));else items.sort((a,b)=>(+a.dataset.i)-(+b.dataset.i));
 items.forEach(el=>box.appendChild(el));}
function cmp(title,list){return '<div class="tile" style="padding:15px 17px"><div class="cmp-t"><span>'+title+'</span><span class="pill">'+list.length+'</span></div>'+(list.length?grid(list):'<span class="empty">None</span>')+'</div>';}
function listSection(name,kind,d,label,icn){const lid='l_'+name+'_'+kind;
 return '<div class="sec"><div class="sec-h">'+ic(icn)+'<div class="sec-t">'+label+'</div><span class="pill">'+d.current.count+'</span></div>'
  +'<details><summary><div class="more">Show '+d.current.count+' &middot; '+label+' '+ic('chev')+'</div></summary>'
  +'<div class="sortbar">Sort<button class="on" onclick="sortList(this,\''+lid+'\',\'recent\')">Newest</button><button onclick="sortList(this,\''+lid+'\',\'az\')">A&ndash;Z</button></div>'
  +grid(d.current.usernames,lid)+'</details></div>';}
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
// ---- theme ----
const LIGHT_Q=window.matchMedia('(prefers-color-scheme: light)');
const STILL_Q=window.matchMedia('(prefers-reduced-motion: reduce)');
function isLight(){const p=document.documentElement.getAttribute('data-theme');return p?p==='light':LIGHT_Q.matches;}
function paintTheme(){const m=document.querySelector('meta[name=theme-color]');if(m)m.content=isLight()?'#f7f7fa':'#08080c';}
function toggleTheme(){const next=isLight()?'dark':'light';
 try{localStorage.setItem('fl-theme',next);}catch(e){}
 document.documentElement.setAttribute('data-theme',next);paintTheme();}
// With no pinned choice, keep following the system if it changes mid-session.
LIGHT_Q.addEventListener('change',()=>{if(!document.documentElement.getAttribute('data-theme'))paintTheme();});
paintTheme();
// ---- interactions ----
function countUp(panel){panel.querySelectorAll('.num[data-v]').forEach(el=>{const tgt=+el.dataset.v;if(!tgt)return;
 if(STILL_Q.matches){el.textContent=nf(tgt);return;}
 const t0=performance.now();
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
 else if((e.key==='r'||e.key==='R')&&!/input/i.test(document.activeElement.tagName)){scan();}
 else if((e.key==='t'||e.key==='T')&&!/input/i.test(document.activeElement.tagName)){toggleTheme();}});
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
