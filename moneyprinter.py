#!/usr/bin/env python3
"""gtavi-moneyprinter: turn GTA 6 streams, videos and trends into ready-to-post vertical clips.

Nothing is uploaded automatically. You approve every post.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if sys.version_info < (3, 10):
    sys.exit("gtavi-moneyprinter needs Python 3.10+")

from moneyprinter import util  # noqa: E402


def cmd_doctor(a):
    ok = True
    print("gtavi-moneyprinter doctor\n")
    print(f"  [ OK ] python {sys.version.split()[0]}")
    for name, why in (("ffmpeg", "cutting, captions, covers"), ("ffprobe", "clip checks"), ("yt-dlp", "downloads, trends, heatmap")):
        t = util.tool(name)
        print(f"  [{' OK ' if t else 'MISS'}] {name:<8} {t or 'install it: see README'}  ({why})")
        ok &= bool(t)
    if util.tool("ffmpeg"):
        flt = util.run([util.tool("ffmpeg"), "-hide_banner", "-filters"], check=False).stdout
        for f in ("ass", "scdet", "zoompan", "loudnorm"):
            have = f" {f} " in flt
            print(f"  [{' OK ' if have else 'MISS'}] ffmpeg filter '{f}'")
            ok &= have
    fw = importlib.util.find_spec("faster_whisper") is not None
    print(f"  [{' OK ' if fw else 'WARN'}] faster-whisper {'installed' if fw else 'missing: falls back to YouTube captions (pip install faster-whisper)'}")
    print(f"\n  workspace: {util.workspace()}")
    print("\nReady." if ok else "\nFix the MISS lines, then run doctor again.")
    return 0 if ok else 1


def cmd_run(a):
    from moneyprinter import pipeline, render
    res = pipeline.run(a.source, top=a.top, layout=a.layout, face=render.parse_face(a.face), commentary=a.commentary,
                       campaign=a.campaign, chat=a.chat, min_len=a.min, max_len=a.max, credit=a.credit,
                       max_minutes=a.max_minutes)
    good = sum(r["ok"] for r in res)
    print(f"\n{good}/{len(res)} clips passed. Open each folder, pick a hook, post by hand, then run `learn`.")
    return 0 if good else 2


def cmd_moments(a):
    from moneyprinter import pipeline
    sc = pipeline.score_source(a.source, top=a.top, min_len=a.min, max_len=a.max, chat=a.chat, max_minutes=a.max_minutes)
    print(sc["table"])
    print(f"\nwritten: {sc['job'] / 'moments.md'}")
    return 0


def cmd_cut(a):
    from moneyprinter import pipeline, render
    sc = pipeline.score_source(a.source, top=max(a.pick, 3), min_len=a.min, max_len=a.max, chat=a.chat)
    if a.pick > len(sc["moments"]):
        sys.exit("not enough moments")
    camp = Path(a.campaign).read_text(encoding="utf-8") if a.campaign else None
    r = pipeline.make_clip(sc, a.pick - 1, a.layout, render.parse_face(a.face), a.commentary, a.credit, camp)
    if a.hook:
        m = r["manifest"]
        man = render.render_clip(Path(m["source_file"]), r["dir"], m["start"], m["end"], a.hook, sc["words"], m["credit"],
                                 a.layout, render.parse_face(a.face), [p[0] + m["start"] for p in m["punch_ins"]], a.commentary)
        m.update(man)
        util.save_json(r["dir"] / "manifest.json", m)
    print(f"{'PASS' if r['ok'] else 'FAIL'} -> {r['dir']}")
    return 0


def cmd_check(a):
    from moneyprinter import check
    camp = Path(a.campaign).read_text(encoding="utf-8", errors="replace") if a.campaign else None
    worst = 0
    for d in a.clips:
        ok, res = check.check_clip(Path(d), camp)
        print(f"{'PASS' if ok else 'FAIL'} {d}\n{check.report(res)}")
        worst |= 0 if ok else 1
    return worst


def cmd_campaigns(a):
    from moneyprinter import hooks, roi
    if a.action == "save":
        folder = Path(a.folder)
        folder.mkdir(parents=True, exist_ok=True)
        text = sys.stdin.read()
        p = folder / f"{util.slug(a.name or text.splitlines()[0] if text.strip() else 'campaign')}.md"
        p.write_text(text, encoding="utf-8")
        print(f"saved {p}")
        return 0
    camps = roi.load_campaigns(Path(a.folder))
    if not camps:
        print(f"No campaign pages in {a.folder}. Paste a page: python moneyprinter.py campaigns save < page.txt")
        return 1
    views = a.views
    if views is None:
        vs = sorted(c["views"] for c in hooks.ledger()["clips"].values() if c.get("views") is not None)
        views = vs[len(vs) // 2] if vs else None
    rows = roi.rank(camps, views, a.clips_per_hour)
    basis = f"{views:,} views/clip ({'--views' if a.views else 'your ledger median'})" if views else "n/a (no views yet: pass --views or report results)"
    print(f"Expected $/hour basis: {basis}, {a.clips_per_hour} clips/hour\n")
    print(util.md_table(["#", "campaign", "$/1K", "budget left", "max/clip", "$/hour", "platforms"],
                        [[i, r["name"][:38], roi.na(r["rate_per_1k"]), roi.na(r["budget_left"]), roi.na(r["max_payout"]),
                          roi.na(r["expected_per_hour"]) + (" (exhausted)" if r["exhausted"] else ""),
                          ",".join(r["platforms"]) or "n/a"] for i, r in enumerate(rows, 1)]))
    if a.json:
        util.save_json(Path(a.json), rows)
    return 0


def cmd_trends(a):
    from moneyprinter import extras
    rows = extras.trends(a.query, a.hours, a.limit)
    print(util.md_table(["#", "views/h", "views", "channel", "title", "url"],
                        [[i, f"{r['vph']:,.0f}" if r["vph"] else "n/a", f"{r['views']:,}" if r["views"] else "n/a",
                          r["channel"], (r["title"] or "")[:50], r["url"]] for i, r in enumerate(rows, 1)]))
    return 0


def cmd_streams(a):
    from moneyprinter import extras
    rows = extras.twitch_live(a.game, a.limit) + extras.youtube_live(a.query, a.limit)
    rows.sort(key=lambda r: r.get("viewers") or 0, reverse=True)
    print(util.md_table(["#", "platform", "viewers", "channel", "title", "url"],
                        [[i, r["platform"], r["viewers"] or "n/a", r["channel"], (r["title"] or "")[:50], r["url"]]
                         for i, r in enumerate(rows, 1)]))
    return 0


def cmd_live(a):
    from moneyprinter import extras, pipeline, render
    vid, chat = extras.record_live(a.url, a.minutes)
    print(f"recorded {vid} (chat: {chat or 'none'})")
    pipeline.run(str(vid), top=a.top, layout=a.layout, face=render.parse_face(a.face), chat=str(chat) if chat else None,
                 credit=a.credit)
    return 0


def cmd_learn(a):
    from moneyprinter import hooks
    man = util.load_json(Path(a.clip) / "manifest.json") if Path(a.clip).exists() else None
    cid = man["id"] if man else a.clip
    c = hooks.record_result(cid, a.hook, a.cover, a.views, a.earned, a.platform, a.url)
    print(json.dumps(c, indent=2))
    rates = hooks.style_rates()
    print("hook style win rates:", ", ".join(f"{k} {v:.0%}" for k, v in sorted(rates.items(), key=lambda kv: -kv[1])))
    return 0


def cmd_calendar(a):
    from moneyprinter import package
    clips = [Path(c) for c in a.clips] or sorted(p for p in (util.workspace() / "clips").glob("*") if p.is_dir())
    start = datetime.fromisoformat(a.start) if a.start else datetime.now()
    rows = package.build_schedule(clips, start)
    c, i = package.write_calendar(rows, Path(a.out))
    print(f"{len(rows)} slots for {len(clips)} clips -> {c} and {i}. Every slot is NEEDS APPROVAL.")
    return 0


def cmd_dashboard(a):
    from moneyprinter import package
    print(f"dashboard -> {package.dashboard(Path(a.out))}")
    return 0


def cmd_multilang(a):
    from moneyprinter import render
    d = Path(a.clip)
    m = util.load_json(d / "manifest.json")
    if not m:
        sys.exit("not a clip folder")
    for lang in a.langs.split(","):
        srt = d / f"captions.{lang}.srt"
        hook_file = d / f"hook.{lang}.txt"
        if not srt.exists() or not hook_file.exists():
            print(f"[{lang}] missing {srt.name} / {hook_file.name}: translate captions.srt and hook 1 first (see skill multilang)")
            continue
        man = render.render_clip(Path(m["source_file"]), d, m["start"], m["end"], hook_file.read_text(encoding="utf-8").strip(),
                                 None, m["credit"], m["layout"], m.get("face"), [p[0] + m["start"] for p in m["punch_ins"]],
                                 name=f"clip.{lang}.mp4", srt_override=srt)
        print(f"[{lang}] {d / man['file']} ({', '.join(man['transformations'])})")
    return 0


def cmd_questions(a):
    from moneyprinter import extras
    rows = extras.questions(a.subs.split(","), a.comments)
    print(util.md_table(["#", "asked", "example question"], [[i, r["count"], r["example"][:90]] for i, r in enumerate(rows[:a.top], 1)]))
    return 0


def cmd_secrets(a):
    from moneyprinter import extras
    if a.action == "add":
        print(extras.secrets_add(name=a.name, category=a.category, area=a.area, how_to_find=a.how, clip=a.clip,
                                 timestamp=a.ts, credit=a.credit, status=a.status))
    elif a.action == "map":
        out = util.workspace() / "secrets_map.md"
        out.write_text(extras.secrets_map_md(), encoding="utf-8")
        print(f"map -> {out}")
    else:
        for r in extras.secrets_list():
            print(r)
    return 0


def cmd_cheats(a):
    from moneyprinter import extras
    if a.action == "carousel":
        for p in extras.cheat_carousel(Path(a.out), a.handle):
            print(p)
    else:
        print(util.md_table(["cheat", "sequence", "unlock", "status", "source"],
                            [[r["cheat"], r["sequence"], r["unlock"], r["status"], r["source"]] for r in extras.cheats()]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="moneyprinter.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    def clip_opts(s):
        s.add_argument("--layout", choices=["blur", "fill", "facecam", "reaction"], default="blur")
        s.add_argument("--face", help="webcam box: tl/tr/bl/br or x,y,w,h fractions (facecam/reaction layout)")
        s.add_argument("--commentary", help="your one-line take, shown in the commentary slot")
        s.add_argument("--credit", help="creator handle for the 'via @creator' overlay (default: from the video)")
        s.add_argument("--campaign", help="saved campaign page to check rules against")
        s.add_argument("--chat", help="chat log (TwitchDownloader JSON, live JSONL, or seconds per line)")
        s.add_argument("--min", type=int, default=12)
        s.add_argument("--max", type=int, default=35)
        s.add_argument("--max-minutes", type=float, default=60, help="only download the first N minutes")

    s = sp.add_parser("doctor", help="check ffmpeg, yt-dlp, faster-whisper")
    s.set_defaults(f=cmd_doctor)
    s = sp.add_parser("run", help="find -> score -> cut -> check -> package, one folder per clip")
    s.add_argument("source", help="URL, local file, or a search query like 'gta 6 funny'")
    s.add_argument("--top", type=int, default=3)
    clip_opts(s)
    s.set_defaults(f=cmd_run)
    s = sp.add_parser("moments", help="score moments only and show the WHY table")
    s.add_argument("source")
    s.add_argument("--top", type=int, default=8)
    clip_opts(s)
    s.set_defaults(f=cmd_moments)
    s = sp.add_parser("cut", help="cut one picked moment")
    s.add_argument("source")
    s.add_argument("--pick", type=int, default=1)
    s.add_argument("--hook", help="override hook 1")
    clip_opts(s)
    s.set_defaults(f=cmd_cut)
    s = sp.add_parser("check", help="rule check + originality guard")
    s.add_argument("clips", nargs="+")
    s.add_argument("--campaign")
    s.set_defaults(f=cmd_check)
    s = sp.add_parser("campaigns", help="save pasted campaign pages and rank them by $/hour")
    s.add_argument("action", choices=["rank", "save"], nargs="?", default="rank")
    s.add_argument("--folder", default=str(util.workspace() / "campaigns"))
    s.add_argument("--name")
    s.add_argument("--views", type=int, help="expected views per clip (default: your ledger median)")
    s.add_argument("--clips-per-hour", type=float, default=3.0)
    s.add_argument("--json")
    s.set_defaults(f=cmd_campaigns)
    s = sp.add_parser("trends", help="GTA 6 videos ranked by views per hour")
    s.add_argument("--query", default="gta 6")
    s.add_argument("--hours", type=int, default=24)
    s.add_argument("--limit", type=int, default=15)
    s.set_defaults(f=cmd_trends)
    s = sp.add_parser("streams", help="who is live with GTA 6 now (Twitch + YouTube)")
    s.add_argument("--query", default="gta 6")
    s.add_argument("--game", default="Grand Theft Auto VI")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(f=cmd_streams)
    s = sp.add_parser("live", help="record a live stream, then clip where chat explodes")
    s.add_argument("url")
    s.add_argument("--minutes", type=float, default=30)
    s.add_argument("--top", type=int, default=3)
    s.add_argument("--layout", default="reaction", choices=["blur", "fill", "facecam", "reaction"])
    s.add_argument("--face")
    s.add_argument("--credit")
    s.set_defaults(f=cmd_live)
    s = sp.add_parser("learn", help="record real results; biases future hooks")
    s.add_argument("clip", help="clip folder or clip id")
    s.add_argument("--hook", type=int)
    s.add_argument("--cover", type=int)
    s.add_argument("--views", type=int)
    s.add_argument("--earned", type=float)
    s.add_argument("--platform")
    s.add_argument("--url")
    s.set_defaults(f=cmd_learn)
    s = sp.add_parser("calendar", help="posting calendar (CSV + .ics), launch-week cadence")
    s.add_argument("clips", nargs="*")
    s.add_argument("--start", help="ISO datetime, default now")
    s.add_argument("--out", default=str(util.workspace()))
    s.set_defaults(f=cmd_calendar)
    s = sp.add_parser("dashboard", help="static HTML dashboard from real numbers")
    s.add_argument("--out", default=str(util.workspace() / "dashboard.html"))
    s.set_defaults(f=cmd_dashboard)
    s = sp.add_parser("multilang", help="re-render a clip with translated captions + hook")
    s.add_argument("clip")
    s.add_argument("--langs", default="es,pt,de,ru,fr,ja")
    s.set_defaults(f=cmd_multilang)
    s = sp.add_parser("questions", help="repeated questions from subreddits/comments -> HOW TO posts")
    s.add_argument("--subs", default="GTA6,GTA")
    s.add_argument("--comments", help="text file with your comments, one per line")
    s.add_argument("--top", type=int, default=15)
    s.set_defaults(f=cmd_questions)
    s = sp.add_parser("secrets", help="secrets map database")
    s.add_argument("action", choices=["add", "list", "map"])
    for k in ("name", "category", "area", "how", "clip", "ts", "credit"):
        s.add_argument(f"--{k}", default="")
    s.add_argument("--status", default="unverified", choices=["unverified", "verified", "wrong"])
    s.set_defaults(f=cmd_secrets)
    s = sp.add_parser("cheats", help="reported cheat codes table or a 4-slide carousel")
    s.add_argument("action", choices=["list", "carousel"], nargs="?", default="list")
    s.add_argument("--out", default=str(util.workspace() / "carousel"))
    s.add_argument("--handle", default="@yourpage")
    s.set_defaults(f=cmd_cheats)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.f(a) or 0


if __name__ == "__main__":
    sys.exit(main())
