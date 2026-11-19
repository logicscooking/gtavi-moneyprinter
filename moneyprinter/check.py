"""Rule check + originality guard. A clip folder passes only when every hard rule passes.

Campaigns and platforms reject plain re-uploads, so a clip needs at least 2 transformations
and a visible credit overlay. Missing proof (no manifest.json) counts as a re-upload.
"""
from __future__ import annotations

import re
from pathlib import Path

from .util import ffprobe, load_json

TRANSFORMATIONS = {"hook_overlay", "captions", "zoom_punch_ins", "facecam_layout", "reaction_layout", "commentary_slot"}
BANNED = [r"\bleak(ed|s)?\b", r"free download", r"play (it )?early", r"\bmod menu\b", r"money glitch", r"\bcrack(ed)?\b",
          r"\btorrent\b", r"official rockstar", r"\bafk bot\b", r"\bbeta access\b", r"\bgiveaway\b.*\bpassword\b"]


def parse_campaign_rules(text: str) -> dict:
    """Pull machine-checkable rules out of a pasted campaign page. Unknown stays unknown."""
    r: dict = {}
    t = text.lower()
    m = re.search(r"(\d{1,3})\s*(?:-|to|–)\s*(\d{1,3})\s*(?:s|sec|seconds)\b", t)
    if m:
        r["min_len"], r["max_len"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"(?:max(?:imum)?|under|up to|no longer than)\s*(\d{1,3})\s*(?:s|sec|seconds)\b", t)
        if m:
            r["max_len"] = int(m.group(1))
        m = re.search(r"(?:min(?:imum)?|at least|longer than)\s*(\d{1,3})\s*(?:s|sec|seconds)\b", t)
        if m:
            r["min_len"] = int(m.group(1))
    tags = re.findall(r"(?:must|required?|include|use)[^\n]{0,60}?(#\w+)", text, re.I)
    if tags:
        r["required_hashtags"] = sorted(set(x.lower() for x in tags))
    mentions = re.findall(r"(?:tag|mention|credit)[^\n]{0,40}?(@\w[\w.]*\w)", text, re.I)
    if mentions:
        r["required_mentions"] = sorted(set(x.lower() for x in mentions))
    if re.search(r"no (?:ai[- ]?voice|tts|text[- ]to[- ]speech)", t):
        r["no_tts"] = True
    if re.search(r"(?:must|only) (?:be )?(?:original|edited|transformed)|no (?:re-?uploads?|reposts?)", t):
        r["no_reupload"] = True
    return r


def check_originality(manifest: dict | None) -> list[tuple[str, bool, str]]:
    if not manifest:
        return [("originality", False, "no manifest.json: treated as a plain re-upload")]
    tr = [t for t in manifest.get("transformations", []) if t in TRANSFORMATIONS]
    res = [("transformations >= 2", len(tr) >= 2, ", ".join(tr) or "none")]
    credit = manifest.get("credit") or ""
    res.append(("credit overlay", bool(manifest.get("credit_overlay")) and credit.startswith("via @"),
                credit or "missing"))
    return res


def check_post_text(text: str, rules: dict, credit: str | None) -> list[tuple[str, bool, str]]:
    res = []
    low = text.lower()
    hits = [p for p in BANNED if re.search(p, low)]
    res.append(("no banned claims", not hits, ", ".join(hits) or "clean"))
    if credit:
        res.append(("credit line in post", credit.lower() in low, credit))
    for tag in rules.get("required_hashtags", []):
        res.append((f"hashtag {tag}", tag in low, "required by campaign"))
    for m in rules.get("required_mentions", []):
        res.append((f"mention {m}", m in low, "required by campaign"))
    return res


def check_video(path: Path, rules: dict) -> list[tuple[str, bool, str]]:
    if not path.exists():
        return [("clip exists", False, str(path))]
    info = ffprobe(path)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    lo, hi = rules.get("min_len", 7), rules.get("max_len", 60)
    return [
        ("1080x1920", (v.get("width"), v.get("height")) == (1080, 1920), f"{v.get('width')}x{v.get('height')}"),
        (f"length {lo}-{hi}s", lo <= dur <= hi, f"{dur:.1f}s"),
        ("has audio", a is not None, a.get("codec_name") if a else "none"),
        ("h264", v.get("codec_name") == "h264", v.get("codec_name")),
    ]


def check_clip(clip_dir: Path, campaign_text: str | None = None) -> tuple[bool, list[tuple[str, bool, str]]]:
    rules = parse_campaign_rules(campaign_text) if campaign_text else {}
    manifest = load_json(clip_dir / "manifest.json")
    results = check_video(clip_dir / "clip.mp4", rules)
    results += check_originality(manifest)
    post = clip_dir / "post.txt"
    if post.exists():
        results += check_post_text(post.read_text(encoding="utf-8"), rules, (manifest or {}).get("credit"))
    else:
        results.append(("post.txt", False, "missing"))
    if rules.get("no_tts") and manifest and manifest.get("tts"):
        results.append(("no TTS voice", False, "campaign forbids TTS"))
    return all(ok for _, ok, _ in results), results


def report(results) -> str:
    return "\n".join(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}" for name, ok, detail in results)
