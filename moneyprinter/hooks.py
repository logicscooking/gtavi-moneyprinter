"""Hook A/B lab: 3 hooks per clip from different styles, biased by what actually won before.

The ledger (workspace/ledger.json) stores every clip, which hook/cover variant was posted,
and the real numbers the user reports. Style win rates come only from those numbers.
"""
from __future__ import annotations

import random
import re
from datetime import datetime

from .util import load_json, save_json, workspace

STYLES = {
    "curiosity": ["Nobody noticed this in GTA 6", "Wait for the last second", "This is not supposed to happen in GTA 6",
                  "GTA 6 hid this in plain sight"],
    "stakes": ["One mistake and it's over", "He had exactly one shot", "This went wrong so fast"],
    "question": ["Would you have survived this?", "How did he pull this off?", "Is this the best GTA 6 moment yet?"],
    "reaction": ["Chat lost it at this", "His reaction says everything", "Nobody in chat was ready"],
    "number": ["3 seconds that broke chat", "The {n}-second GTA 6 moment everyone's clipping", "{n} seconds of pure Vice City"],
    "tip": ["Do this before your first mission", "The GTA 6 trick nobody told you", "Save first, then try this"],
    "pov": ["POV: your first hour in Leonida", "POV: you trusted the GPS", "POV: the cops were 1 block away"],
}

# Signals suggest a style: chat spikes -> reaction, replayed -> curiosity, etc.
SIGNAL_STYLE = {"chat": "reaction", "replayed": "curiosity", "loudness": "stakes", "hype": "reaction", "scenes": "pov"}


def ledger() -> dict:
    return load_json(workspace() / "ledger.json", {"clips": {}, "styles": {}}) or {"clips": {}, "styles": {}}


def save_ledger(d: dict) -> None:
    save_json(workspace() / "ledger.json", d)


def style_rates(led: dict | None = None) -> dict[str, float]:
    """Posterior mean win rate per style, Beta(1,1) prior: (wins+1)/(tests+2)."""
    led = led or ledger()
    st = led.get("styles", {})
    return {s: (st.get(s, {}).get("wins", 0) + 1) / (st.get(s, {}).get("tests", 0) + 2) for s in STYLES}


def pick_styles(breakdown: dict, led: dict | None = None, k: int = 3, seed: int | None = None) -> list[str]:
    """Slot 1: best learned style. Slot 2: style the signals suggest. Slot 3: explore (least-tested)."""
    led = led or ledger()
    rates = style_rates(led)
    tests = {s: led.get("styles", {}).get(s, {}).get("tests", 0) for s in STYLES}
    rng = random.Random(seed)
    order = sorted(STYLES, key=lambda s: (rates[s], -tests[s], rng.random()), reverse=True)
    chosen: list[str] = [order[0]]
    if breakdown:
        top_sig = max(breakdown, key=breakdown.get)
        sug = SIGNAL_STYLE.get(top_sig)
        if sug and sug not in chosen:
            chosen.append(sug)
    for s in sorted(STYLES, key=lambda s: (tests[s], rng.random())):
        if len(chosen) >= k:
            break
        if s not in chosen:
            chosen.append(s)
    for s in order:
        if len(chosen) >= k:
            break
        if s not in chosen:
            chosen.append(s)
    return chosen[:k]


def quote_hook(text: str) -> str | None:
    """A short shouted line from the transcript makes a strong hook: '"NO WAY he made that"'."""
    text = re.sub(r"\s+", " ", text or "").strip()
    m = re.search(r"(no way|oh my god|bro|wait|what|holy|let'?s go)[^.?!]{0,30}", text, re.I)
    if not m:
        return None
    q = m.group(0).strip(" ,")
    return f'"{q[0].upper() + q[1:]}"' if len(q) >= 6 else None


def make_hooks(breakdown: dict, length: int, transcript_text: str = "", seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    styles = pick_styles(breakdown, seed=seed)
    out = []
    for s in styles:
        txt = rng.choice(STYLES[s]).replace("{n}", str(length))
        if s == "reaction":
            q = quote_hook(transcript_text)
            if q:
                txt = q
        out.append({"style": s, "text": txt})
    return out


def record_result(clip_id: str, hook: int | None = None, cover: int | None = None, views: int | None = None,
                  earned: float | None = None, platform: str | None = None, url: str | None = None,
                  posted: bool = True) -> dict:
    """Store real numbers for a clip. The hook variant marked as posted gets a test; a win
    is counted when its views beat the user's median views so far."""
    led = ledger()
    c = led["clips"].setdefault(clip_id, {"id": clip_id})
    if hook is not None:
        c["posted_hook"] = hook
    if cover is not None:
        c["posted_cover"] = cover
    if platform:
        c["platform"] = platform
    if url:
        c["url"] = url
    if views is not None:
        c["views"] = int(views)
    if earned is not None:
        c["earned"] = float(earned)
    c["posted"] = posted
    c["updated"] = datetime.now().isoformat(timespec="seconds")
    # Re-derive style stats from scratch so repeated reports never double-count.
    viewed = [x for x in led["clips"].values() if x.get("views") is not None and x.get("posted_hook")]
    vs = sorted(x["views"] for x in viewed)
    med = (vs[(len(vs) - 1) // 2] + vs[len(vs) // 2]) / 2 if vs else 0
    styles: dict[str, dict] = {}
    for x in viewed:
        hooks = x.get("hooks") or []
        i = x["posted_hook"] - 1
        if 0 <= i < len(hooks):
            s = hooks[i]["style"]
            st = styles.setdefault(s, {"tests": 0, "wins": 0})
            st["tests"] += 1
            if len(viewed) >= 2 and x["views"] > med:
                st["wins"] += 1
    led["styles"] = styles
    save_ledger(led)
    return c


def register_clip(clip_id: str, meta: dict) -> None:
    led = ledger()
    c = led["clips"].setdefault(clip_id, {"id": clip_id})
    c.update(meta)
    c.setdefault("posted", False)
    save_ledger(led)
