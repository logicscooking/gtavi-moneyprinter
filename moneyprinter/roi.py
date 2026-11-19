"""Campaign ROI ranker.

Reads campaign pages the user pasted or saved (txt/md/html/json in a folder) and ranks them by
expected $ per hour of work. Rates are only ever read from the page. Unknown = "n/a".

expected $/hour = rate_per_1k * (expected_views / 1000) * clips_per_hour, capped by budget left
and by any max payout per clip. expected_views comes from the user's own ledger median or --views;
without either, $/hour is "n/a" and campaigns rank by rate and budget instead.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MONEY = r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kKmM])?"


def _money(num: str, suffix: str | None) -> float:
    v = float(num.replace(",", ""))
    if suffix and suffix.lower() == "k":
        v *= 1_000
    elif suffix and suffix.lower() == "m":
        v *= 1_000_000
    return v


@dataclass
class Campaign:
    name: str
    source: str
    rate_per_1k: float | None = None
    budget_left: float | None = None
    budget_total: float | None = None
    max_payout: float | None = None
    min_views: int | None = None
    platforms: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    url: str | None = None

    def expected_per_hour(self, views: float | None, clips_per_hour: float) -> float | None:
        if self.rate_per_1k is None or views is None:
            return None
        if self.min_views and views < self.min_views:
            return 0.0
        per_clip = self.rate_per_1k * views / 1000
        if self.max_payout is not None:
            per_clip = min(per_clip, self.max_payout)
        hourly = per_clip * clips_per_hour
        if self.budget_left is not None:
            hourly = min(hourly, self.budget_left)
        return round(hourly, 2)


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"[ \t]+", " ", s))


def parse_campaign(text: str, name: str = "campaign", source: str = "") -> Campaign:
    if "<html" in text[:500].lower() or "</div>" in text:
        text = _strip_html(text)
    c = Campaign(name=name, source=source)
    m = re.search(r"^\s*(?:#+\s*|title:\s*|campaign:\s*)(.+)$", text, re.M | re.I)
    if m:
        c.name = m.group(1).strip()[:80]
    m = re.search(MONEY + r"\s*(?:/|per)\s*(?:1,?000|1k|thousand)\s*(?:views)?", text, re.I)
    if m:
        c.rate_per_1k = _money(m.group(1), m.group(2))
    else:
        m = re.search(MONEY + r"\s*(?:cpm|rpm)\b", text, re.I)
        if m:
            c.rate_per_1k = _money(m.group(1), m.group(2))
        else:
            m = re.search(MONEY + r"\s*(?:/|per)\s*(?:1m|1,000,000|million)\s*(?:views)?", text, re.I)
            if m:
                c.rate_per_1k = _money(m.group(1), m.group(2)) / 1000
    m = re.search(MONEY + r"\s*(?:of\s*)?" + MONEY + r"\s*(?:paid|used|spent)", text, re.I)
    if m:  # "$1,200 of $5,000 paid out"
        paid, total = _money(m.group(1), m.group(2)), _money(m.group(3), m.group(4))
        c.budget_total, c.budget_left = total, max(0.0, total - paid)
    else:
        m = re.search(MONEY + r"\s*(?:budget\s*)?(?:left|remaining)", text, re.I) or \
            re.search(r"(?:budget\s*)?(?:left|remaining)\s*[:\-]?\s*" + MONEY, text, re.I)
        if m:
            c.budget_left = _money(m.group(1), m.group(2))
        m = re.search(r"(?:total\s*)?budget\s*[:\-]?\s*" + MONEY, text, re.I)
        if m:
            c.budget_total = _money(m.group(1), m.group(2))
    m = re.search(r"max(?:imum)?\s*(?:payout)?\s*(?:per\s*(?:clip|post|video))\s*[:\-]?\s*" + MONEY, text, re.I) or \
        re.search(MONEY + r"\s*max(?:imum)?\s*per\s*(?:clip|post|video)", text, re.I)
    if m:
        c.max_payout = _money(m.group(1), m.group(2))
    m = re.search(r"(?:min(?:imum)?|at least)\s*([0-9][0-9,]*)\s*([kK])?\s*views", text, re.I)
    if m:
        c.min_views = int(_money(m.group(1), m.group(2)))
    for p in ("tiktok", "instagram", "youtube", "x.com", "twitter"):
        if re.search(rf"\b{re.escape(p)}\b", text, re.I):
            c.platforms.append({"x.com": "x", "twitter": "x"}.get(p, p))
    c.platforms = sorted(set(c.platforms))
    c.rules = [ln.strip(" -*\t") for ln in text.splitlines()
               if re.match(r"^\s*[-*•]\s+", ln) and len(ln.strip()) < 200][:12]
    m = re.search(r"https?://(?:www\.)?whop\.com/\S+", text)
    if m:
        c.url = m.group(0).rstrip(").,")
    return c


def load_campaigns(folder: Path) -> list[Campaign]:
    out = []
    for p in sorted(Path(folder).glob("*")):
        if p.suffix.lower() not in (".txt", ".md", ".html", ".htm", ".json"):
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        if p.suffix.lower() == ".json":
            try:
                d = json.loads(raw)
                raw = "\n".join(f"{k}: {v}" for k, v in d.items()) if isinstance(d, dict) else raw
            except ValueError:
                pass
        out.append(parse_campaign(raw, name=p.stem, source=str(p)))
    return out


def rank(campaigns: list[Campaign], views: float | None, clips_per_hour: float = 3.0) -> list[dict]:
    rows = []
    for c in campaigns:
        eph = c.expected_per_hour(views, clips_per_hour)
        rows.append({"name": c.name, "rate_per_1k": c.rate_per_1k, "budget_left": c.budget_left,
                     "max_payout": c.max_payout, "min_views": c.min_views, "platforms": c.platforms,
                     "expected_per_hour": eph, "url": c.url, "source": c.source, "rules": c.rules,
                     "exhausted": c.budget_left is not None and c.budget_left <= 0})

    def key(r):
        return (not r["exhausted"], r["expected_per_hour"] if r["expected_per_hour"] is not None else -1,
                r["rate_per_1k"] if r["rate_per_1k"] is not None else -1,
                r["budget_left"] if r["budget_left"] is not None else -1)
    return sorted(rows, key=key, reverse=True)


def na(v, money: bool = True) -> str:
    if v is None:
        return "n/a"
    return f"${v:,.2f}" if money else str(v)
