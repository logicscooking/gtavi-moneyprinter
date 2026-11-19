"""post.txt, posting calendar (CSV + .ics) and the static dashboard."""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timedelta
from pathlib import Path

from .hooks import ledger, style_rates
from .util import load_json

TAGS = {
    "tiktok": "#gta6 #gtavi #gta6clips #gaming #fyp",
    "reels": "#gta6 #gtavi #gamingreels #gta #gamer",
    "shorts": "#gta6 #gtavi #shorts #gaming",
    "x": "#GTA6 #GTAVI",
}


def post_text(hooks: list[dict], title: str, credit: str, source_url: str, extra_tags: list[str] | None = None) -> str:
    extra = " ".join(extra_tags or [])
    lines = ["HOOKS (A/B: post #1, keep #2 and #3 for re-posts or the cover)"]
    lines += [f"  {i}. [{h['style']}] {h['text']}" for i, h in enumerate(hooks, 1)]
    lines += ["", "CAPTION", f"  {hooks[0]['text']}. {title.strip()[:90]}".rstrip(),
              "", "CREDIT (keep it in every post)", f"  {credit} | original: {source_url}", "", "HASHTAGS"]
    lines += [f"  {p:<7} {t} {extra}".rstrip() for p, t in TAGS.items()]
    lines += ["", "COVERS: cover_1.jpg / cover_2.jpg / cover_3.jpg match hooks 1-3",
              "AFTER POSTING: python moneyprinter.py learn <this folder> --hook 1 --cover 1 --views N"]
    return "\n".join(lines) + "\n"


# ---------- calendar ----------

LAUNCH = datetime(2026, 11, 19)
PLATFORM_ORDER = ["x", "tiktok", "reels", "shorts"]


def cadence(day_index: int) -> list[int]:
    """Posting hours for a day. Launch day + day 2: every 2 h, 8:00-24:00. Rest of launch week: 4/day. Then 2/day."""
    if day_index <= 1:
        return list(range(8, 24, 2))
    if day_index <= 6:
        return [9, 13, 17, 21]
    return [15, 20]


def build_schedule(clips: list[Path], start: datetime, launch: datetime = LAUNCH) -> list[dict]:
    rows, i = [], 0
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while i < len(clips):
        di = (day - launch.replace(hour=0, minute=0)).days
        for h in cadence(max(0, di)):
            if i >= len(clips):
                break
            when = day + timedelta(hours=h)
            if when < start:
                continue
            c = clips[i]
            post = (c / "post.txt").read_text(encoding="utf-8") if (c / "post.txt").exists() else ""
            hook = next((ln.split("] ", 1)[-1] for ln in post.splitlines() if ln.strip().startswith("1. [")), c.name)
            # X first (fastest feed), then the vertical apps 30 min apart
            for k, plat in enumerate(PLATFORM_ORDER):
                rows.append({"when": (when + timedelta(minutes=30 * k)).isoformat(timespec="minutes"),
                             "platform": plat, "clip": str(c), "hook": hook, "status": "NEEDS APPROVAL"})
            i += 1
        day += timedelta(days=1)
    return rows


def write_calendar(rows: list[dict], out: Path) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    cpath, ipath = out / "calendar.csv", out / "calendar.ics"
    with cpath.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["when", "platform", "clip", "hook", "status"])
        w.writeheader()
        w.writerows(rows)
    ev = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//gtavi-moneyprinter//EN"]
    for n, r in enumerate(rows):
        t = datetime.fromisoformat(r["when"])
        stamp = t.strftime("%Y%m%dT%H%M%S")
        ev += ["BEGIN:VEVENT", f"UID:moneyprinter-{n}-{stamp}@local", f"DTSTAMP:{stamp}", f"DTSTART:{stamp}",
               f"DTEND:{(t + timedelta(minutes=15)).strftime('%Y%m%dT%H%M%S')}",
               f"SUMMARY:Post to {r['platform']}: {r['hook'][:60]}".replace(",", "\\,"),
               f"DESCRIPTION:Approve and post by hand. Clip: {r['clip']}".replace(",", "\\,"),
               "BEGIN:VALARM", "TRIGGER:-PT10M", "ACTION:DISPLAY", "DESCRIPTION:Post reminder", "END:VALARM",
               "END:VEVENT"]
    ev.append("END:VCALENDAR")
    ipath.write_text("\r\n".join(ev) + "\r\n", encoding="utf-8")
    return cpath, ipath


# ---------- dashboard ----------

def dashboard(out: Path) -> Path:
    led = ledger()
    clips = list(led.get("clips", {}).values())
    posted = [c for c in clips if c.get("posted")]
    views = sum(c.get("views", 0) for c in posted if c.get("views") is not None)
    earned_known = [c["earned"] for c in posted if c.get("earned") is not None]
    rates = style_rates(led)
    st = led.get("styles", {})
    best = sorted(((s, r, st.get(s, {}).get("tests", 0)) for s, r in rates.items()), key=lambda x: (x[2] > 0, x[1]),
                  reverse=True)
    top_hooks = sorted([c for c in posted if c.get("views") is not None], key=lambda c: c["views"], reverse=True)[:8]

    def hook_of(c):
        hs, i = c.get("hooks") or [], (c.get("posted_hook") or 1) - 1
        return hs[i]["text"] if 0 <= i < len(hs) else "?"

    e = html.escape
    kpi = [("Clips made", len(clips)), ("Posted", len(posted)), ("Views (reported)", f"{views:,}"),
           ("Earned (reported)", f"${sum(earned_known):,.2f}" if earned_known else "n/a")]
    rows_h = "".join(f"<tr><td>{e(hook_of(c))}</td><td>{e(str(c.get('platform') or '-'))}</td><td>{c['views']:,}</td>"
                     f"<td>{'$%.2f' % c['earned'] if c.get('earned') is not None else 'n/a'}</td></tr>" for c in top_hooks)
    rows_s = "".join(f"<tr><td>{e(s)}</td><td>{n}</td><td>{r * 100:.0f}%</td></tr>" for s, r, n in best)
    rows_c = "".join(f"<tr><td>{e(c['id'])}</td><td>{'yes' if c.get('posted') else 'no'}</td>"
                     f"<td>{c.get('views', 'n/a') if c.get('views') is not None else 'n/a'}</td>"
                     f"<td>{e(str(c.get('score', '')))}</td></tr>" for c in sorted(clips, key=lambda c: c['id']))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moneyprinter Dashboard</title><style>
:root{{--bg:#0d0718;--card:#1a0f2e;--ink:#f6eefe;--mut:#b9a6d6;--acc:#ff3e8a;--acc2:#ffb347}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;padding:24px 16px}}
main{{max-width:980px;margin:auto}}h1{{margin:0 0 4px;font-size:28px}}p.s{{color:var(--mut);margin:0 0 20px}}
.k{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}}
.k div{{background:var(--card);border-radius:14px;padding:16px;border:1px solid #2c1d48}}.k b{{display:block;font-size:30px;color:var(--acc2)}}
table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden;margin-bottom:24px}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid #2c1d48}}th{{color:var(--acc);font-weight:600}}
h2{{font-size:18px;margin:8px 0}}</style></head><body><main>
<h1>gtavi-moneyprinter</h1><p class="s">Built {datetime.now():%Y-%m-%d %H:%M} from ledger.json. Real reported numbers only; missing = n/a.</p>
<div class="k">{''.join(f'<div>{e(k)}<b>{v}</b></div>' for k, v in kpi)}</div>
<h2>Best hooks (by views)</h2><table><tr><th>Hook</th><th>Platform</th><th>Views</th><th>Earned</th></tr>{rows_h or '<tr><td colspan=4>No posted clips with views yet.</td></tr>'}</table>
<h2>Hook styles (learning loop)</h2><table><tr><th>Style</th><th>Tests</th><th>Win rate (Beta prior)</th></tr>{rows_s}</table>
<h2>All clips</h2><table><tr><th>Clip</th><th>Posted</th><th>Views</th><th>Score</th></tr>{rows_c or '<tr><td colspan=4>No clips yet.</td></tr>'}</table>
</main></body></html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
