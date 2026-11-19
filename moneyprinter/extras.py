"""Trends, live streams, live chat-explosion recording, questions-to-posts, secrets map, cheat carousel."""
from __future__ import annotations

import csv
import json
import re
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .util import DATA, md_table, need, run, workspace

UA = {"User-Agent": "gtavi-moneyprinter/1.0 (+https://github.com/logicscooking/gtavi-moneyprinter)"}
TWITCH_GQL = "https://gql.twitch.tv/gql"
TWITCH_PUBLIC_CLIENT = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # Twitch's public web client id (also used by yt-dlp)


def _get_json(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 20):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------- trends ----------

def views_per_hour(view_count: int | None, timestamp: float | None, now: float | None = None) -> float | None:
    if not view_count or not timestamp:
        return None
    hours = max(0.5, ((now or time.time()) - timestamp) / 3600)
    return view_count / hours


def trends(query: str = "gta 6", hours: int = 24, limit: int = 15) -> list[dict]:
    p = run([need("yt-dlp"), "-j", "--skip-download", "--ignore-errors", "--no-warnings",
             f"ytsearchdate{limit}:{query}"], check=False, timeout=600)
    rows, now = [], time.time()
    for ln in (p.stdout or "").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        ts = d.get("timestamp") or (datetime.strptime(d["upload_date"], "%Y%m%d").replace(tzinfo=timezone.utc).timestamp()
                                    if d.get("upload_date") else None)
        if ts and now - ts > hours * 3600:
            continue
        rows.append({"title": d.get("title"), "channel": d.get("channel"), "views": d.get("view_count"),
                     "vph": views_per_hour(d.get("view_count"), ts, now), "duration": d.get("duration"),
                     "url": d.get("webpage_url"), "live": d.get("is_live")})
    return sorted(rows, key=lambda r: r["vph"] or 0, reverse=True)


# ---------- live streams ----------

def youtube_live(query: str = "gta 6", limit: int = 15) -> list[dict]:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=EgJAAQ%253D%253D"
    p = run([need("yt-dlp"), "--flat-playlist", "-J", "--playlist-end", str(limit), url], check=False, timeout=120)
    try:
        ents = json.loads(p.stdout or "{}").get("entries") or []
    except ValueError:
        ents = []
    return [{"platform": "youtube", "channel": e.get("channel") or e.get("uploader"), "title": e.get("title"),
             "viewers": e.get("concurrent_view_count") or e.get("view_count"),
             "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"} for e in ents]


def twitch_live(game: str = "Grand Theft Auto VI", limit: int = 15) -> list[dict]:
    q = ('query($name:String!,$n:Int!){game(name:$name){streams(first:$n){edges{node{title viewersCount '
         'broadcaster{login displayName}}}}}}')
    body = json.dumps({"query": q, "variables": {"name": game, "n": limit}}).encode()
    try:
        d = _get_json(TWITCH_GQL, body, {"Client-Id": TWITCH_PUBLIC_CLIENT, "Content-Type": "application/json"})
    except Exception as ex:
        print(f"[moneyprinter] twitch lookup failed: {ex}")
        return []
    edges = (((d.get("data") or {}).get("game") or {}).get("streams") or {}).get("edges") or []
    return [{"platform": "twitch", "channel": e["node"]["broadcaster"]["login"], "title": e["node"]["title"],
             "viewers": e["node"]["viewersCount"], "url": f"https://www.twitch.tv/{e['node']['broadcaster']['login']}"}
            for e in edges]


# ---------- live mode: record + chat explosion ----------

def twitch_irc(channel: str, out: Path, stop: threading.Event, t0: float) -> None:
    """Anonymous read-only Twitch chat (justinfan login). Writes {"t": seconds, "msg": text} lines."""
    ctx = ssl.create_default_context()
    with socket.create_connection(("irc.chat.twitch.tv", 6697), timeout=15) as raw, \
            ctx.wrap_socket(raw, server_hostname="irc.chat.twitch.tv") as s, out.open("a", encoding="utf-8") as f:
        s.sendall(f"NICK justinfan{int(time.time()) % 100000}\r\nJOIN #{channel.lower()}\r\n".encode())
        s.settimeout(2)
        buf = ""
        while not stop.is_set():
            try:
                buf += s.recv(4096).decode("utf-8", "replace")
            except socket.timeout:
                continue
            *lines, buf = buf.split("\r\n")
            for ln in lines:
                if ln.startswith("PING"):
                    s.sendall(b"PONG :tmi.twitch.tv\r\n")
                elif "PRIVMSG" in ln:
                    f.write(json.dumps({"t": round(time.time() - t0, 2), "msg": ln.split(" :", 2)[-1]}) + "\n")
                    f.flush()


def record_live(url: str, minutes: float) -> tuple[Path, Path | None]:
    d = workspace() / "live" / datetime.now().strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    vid, chat = d / "source.mp4", d / "chat.jsonl"
    stop, th = threading.Event(), None
    m = re.search(r"twitch\.tv/([A-Za-z0-9_]+)", url)
    t0 = time.time()
    if m:
        th = threading.Thread(target=twitch_irc, args=(m.group(1), chat, stop, t0), daemon=True)
        th.start()
    stream = run([need("yt-dlp"), "-g", "-f", "best[height<=1080]/best", url], timeout=120).stdout.strip().splitlines()[0]
    t0 = time.time()  # chat offsets are relative to recording start
    run([need("ffmpeg"), "-y", "-v", "error", "-i", stream, "-t", str(int(minutes * 60)), "-c", "copy", str(vid)],
        check=False, timeout=minutes * 60 + 300)
    stop.set()
    if th:
        th.join(timeout=5)
    return vid, (chat if chat.exists() and chat.stat().st_size else None)


# ---------- questions to posts ----------

QWORDS = re.compile(r"^(how|where|what|can|is|does|do|why|when|which)\b", re.I)
STOP = set("the a an to in of and is it do does how where what can i you my on for gta 6 vi gta6 gtavi get be with".split())


def questions(subs: list[str], comments_file: str | None = None, limit: int = 100) -> list[dict]:
    texts = []
    for sub in subs:
        try:
            d = _get_json(f"https://www.reddit.com/r/{sub}/new.json?limit={limit}")
            texts += [c["data"]["title"] for c in d["data"]["children"]]
        except Exception as ex:
            print(f"[moneyprinter] r/{sub} failed: {ex}")
    if comments_file:
        texts += Path(comments_file).read_text(encoding="utf-8", errors="replace").splitlines()
    qs = [t.strip() for t in texts if t.strip().endswith("?") or QWORDS.match(t.strip())]
    groups: dict[str, list[str]] = {}
    for q in qs:
        key = " ".join(sorted({w for w in re.findall(r"[a-z0-9']+", q.lower()) if w not in STOP})[:4])
        if key:
            groups.setdefault(key, []).append(q)
    out = [{"topic": k, "count": len(v), "example": v[0]} for k, v in groups.items()]
    return sorted(out, key=lambda r: r["count"], reverse=True)


# ---------- secrets map ----------

SECRETS_FIELDS = ["id", "name", "category", "area", "how_to_find", "clip", "timestamp", "credit", "status", "added"]


def secrets_path() -> Path:
    return workspace() / "secrets.csv"


def secrets_add(**kw) -> dict:
    p = secrets_path()
    rows = secrets_list()
    row = {k: kw.get(k, "") for k in SECRETS_FIELDS}
    row["id"] = str(len(rows) + 1)
    row["status"] = kw.get("status") or "unverified"
    row["added"] = datetime.now().strftime("%Y-%m-%d")
    new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SECRETS_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def secrets_list() -> list[dict]:
    p = secrets_path()
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def secrets_map_md() -> str:
    rows = secrets_list()
    by_area: dict[str, list[dict]] = {}
    for r in rows:
        by_area.setdefault(r["area"] or "Unknown", []).append(r)
    out = ["# GTA 6 secrets map", "", "Only `verified` entries become tip posts. Credit every finder."]
    for area, items in sorted(by_area.items()):
        out += ["", f"## {area}", md_table(["#", "name", "category", "how to find", "credit", "status"],
                                           [[r["id"], r["name"], r["category"], r["how_to_find"], r["credit"], r["status"]]
                                            for r in items])]
    return "\n".join(out) + "\n"


# ---------- cheat codes ----------

def cheats(status: tuple[str, ...] = ("reported", "verified")) -> list[dict]:
    with (DATA / "cheats.csv").open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["status"] in status]


def _ass_card(lines: list[tuple[str, int, str]], w: int = 1080, h: int = 1350) -> str:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    y = 90
    for text, size, color in lines:
        ev.append(f"Dialogue: 0,0:00:00.00,0:00:05.00,T,,0,0,0,,{{\\pos(70,{y})\\fs{size}\\c&H{color}&}}{text}")
        y += int(size * 1.45)
    return head + "\n".join(ev) + "\n"


def cheat_carousel(out: Path, handle: str = "@yourpage") -> list[Path]:
    rows = cheats()
    pink, gold, white, grey = "8A3EFF", "47B3FF", "FFFFFF", "D6A6B9"
    player = [r for r in rows if r["group"] == "player"]
    world = [r for r in rows if r["group"] != "player"]
    slides = [
        [("GTA 6 CHEAT CODES", 92, pink), ("PS5 + Xbox Series X|S", 48, white), ("", 30, white),
         ("The $250,000 cheat is reported", 52, gold), ("Status: REPORTED by public guides,", 38, grey),
         ("not yet verified in game", 38, grey), ("", 300, white), (handle, 40, white)],
        [("HOW TO ENTER", 80, pink), ("1. Finish the main story", 46, white), ("2. Press UP to open the phone", 46, white),
         ("3. Hold L1+R1 (PS5) or LB+RB (Xbox)", 46, white), ("4. Enter the D-pad sequence", 46, white), ("", 30, white),
         ("SAVE FIRST: cheats block saving,", 44, gold), ("trophies and achievements", 44, gold), ("", 200, white), (handle, 40, white)],
    ]
    for title, group in (("PLAYER + COMBAT", player), ("VEHICLES + FILTERS", world)):
        s = [(title, 72, pink)]
        for r in group[:8]:
            s += [(r["cheat"], 40, white), (r["sequence"].replace(" ", "  "), 46, gold)]
        s += [("Status: reported. Source column in data/cheats.csv", 30, grey), (handle, 36, white)]
        slides.append(s)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, s in enumerate(slides, 1):
        ass = out / f"slide_{i}.ass"
        ass.write_text(_ass_card(s), encoding="utf-8")
        run([need("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x120a22:s=1080x1350:d=1",
             "-vf", f"ass={ass.name}", "-frames:v", "1", f"slide_{i}.png"], cwd=out)
        ass.unlink()
        paths.append(out / f"slide_{i}.png")
    srcs = sorted({r["source"] for r in rows})
    (out / "caption.txt").write_text(
        "GTA 6 cheat codes (reported, not yet verified in game). Save first!\n"
        f"Codes via: {', '.join(srcs)}\n#gta6 #gtavi #gta6cheats\n", encoding="utf-8")
    return paths
