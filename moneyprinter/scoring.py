"""Fuse per-second signals into ranked clip windows, with a breakdown of WHY each one won.

Pure Python on purpose: easy to unit-test offline and no numpy needed.

A signal is a list of floats, one value per second of source video. Signals can be missing
(None or empty); their weight is then redistributed so a missing signal is skipped, never faked.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

DEFAULT_WEIGHTS = {
    "loudness": 0.25,   # audio energy spikes (shouting, explosions)
    "hype": 0.25,       # hype words in the transcript
    "replayed": 0.25,   # YouTube "most replayed" heatmap
    "chat": 0.15,       # chat messages per second
    "scenes": 0.10,     # scene-change density (action, fast cuts)
}

HYPE_RE = re.compile(
    r"\b(no way|oh my god|omg|what+|wait|bro+|let'?s go+|holy|insane|crazy|yo+|wtf|dude|look at (this|that)|"
    r"nah+|run+|go go|are you kidding|how did|did you see|clip (it|that)|bruh|oh no|why|huge|secret|hidden)\b",
    re.I,
)


def robust_norm(xs: list[float] | None) -> list[float] | None:
    """Map a signal to 0..1 by how far each second sits above the median (median/MAD z-score).

    Flat signals return all zeros, so a constant signal never invents a peak.
    """
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    dev = sorted(abs(x - med) for x in xs)
    mad = dev[n // 2] if n % 2 else (dev[n // 2 - 1] + dev[n // 2]) / 2
    scale = 1.4826 * mad
    if scale < 1e-9:
        # Fall back to range scaling (sparse signals like chat bursts or hype words).
        lo, hi = min(xs), max(xs)
        if hi - lo < 1e-9:
            return [0.0] * n
        return [(x - lo) / (hi - lo) for x in xs]
    # z of +3 or more counts as a full-strength spike.
    return [min(1.0, max(0.0, (x - med) / scale / 3.0)) for x in xs]


def hype_per_second(words: list[dict], duration: int) -> list[float]:
    """words: [{start, end, word}] -> hype-word hits per second (plus '!' and ALL CAPS as small boosts)."""
    out = [0.0] * max(1, duration)
    text_by_sec: dict[int, list[str]] = {}
    for w in words or []:
        sec = int(w.get("start", 0))
        if 0 <= sec < len(out):
            text_by_sec.setdefault(sec, []).append(str(w.get("word", "")))
    for sec, toks in text_by_sec.items():
        line = " ".join(toks)
        hits = len(HYPE_RE.findall(line))
        hits += 0.3 * line.count("!")
        hits += 0.3 * sum(1 for t in toks if len(t) > 2 and t.isupper())
        out[sec] += hits
    return out


def heatmap_per_second(heatmap: list[dict] | None, duration: int) -> list[float] | None:
    """yt-dlp 'heatmap' entries [{start_time, end_time, value}] -> per-second values."""
    if not heatmap:
        return None
    out = [0.0] * max(1, duration)
    for h in heatmap:
        a, b = int(h.get("start_time", 0)), int(math.ceil(h.get("end_time", 0)))
        for s in range(max(0, a), min(len(out), max(a + 1, b))):
            out[s] = max(out[s], float(h.get("value", 0)))
    return out


def rate_per_second(timestamps: list[float] | None, duration: int) -> list[float] | None:
    """Event timestamps (chat messages, scene cuts) -> counts per second."""
    if not timestamps:
        return None
    out = [0.0] * max(1, duration)
    for t in timestamps:
        i = int(t)
        if 0 <= i < len(out):
            out[i] += 1
    return out


def smooth(xs: list[float], radius: int = 2) -> list[float]:
    n = len(xs)
    pref = [0.0]
    for x in xs:
        pref.append(pref[-1] + x)
    return [(pref[min(n, i + radius + 1)] - pref[max(0, i - radius)]) / (min(n, i + radius + 1) - max(0, i - radius))
            for i in range(n)]


@dataclass
class Moment:
    start: int
    end: int
    score: float
    peak: int
    breakdown: dict = field(default_factory=dict)  # signal -> weighted contribution

    @property
    def length(self) -> int:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "length": self.length, "score": round(self.score, 4),
                "peak": self.peak, "breakdown": {k: round(v, 4) for k, v in self.breakdown.items()}}


def fuse(signals: dict[str, list[float] | None], weights: dict[str, float] | None = None) -> tuple[list[float], dict]:
    """Return (combined per-second curve, per-signal normalised curves with effective weights)."""
    weights = dict(weights or DEFAULT_WEIGHTS)
    norm = {k: robust_norm(v) for k, v in signals.items() if v}
    norm = {k: smooth(v, 1) for k, v in norm.items() if v and any(v)}
    live = {k: weights.get(k, 0.1) for k in norm}
    total = sum(live.values()) or 1.0
    eff = {k: w / total for k, w in live.items()}
    n = max((len(v) for v in norm.values()), default=0)
    combined = [0.0] * n
    for k, curve in norm.items():
        for i, x in enumerate(curve):
            combined[i] += eff[k] * x
    return combined, {"curves": norm, "weights": eff}


def pick_moments(signals: dict[str, list[float] | None], top: int = 5, min_len: int = 12, max_len: int = 35,
                 weights: dict[str, float] | None = None, lead_in: int = 3) -> list[Moment]:
    """Pick the best non-overlapping windows.

    For each candidate peak second, try lengths from min_len to max_len (step 3) with the peak
    placed `lead_in` seconds after the start (so the clip opens just before the action), and
    keep the window with the best mean score, lightly favouring shorter clips.
    """
    combined, meta = fuse(signals, weights)
    n = len(combined)
    if n == 0:
        return []
    min_len = max(3, min(min_len, n))
    max_len = max(min_len, min(max_len, n))
    pref = [0.0]
    for x in combined:
        pref.append(pref[-1] + x)

    def mean(a, b):
        return (pref[b] - pref[a]) / max(1, b - a)

    peaks = sorted(range(n), key=lambda i: combined[i], reverse=True)
    taken: list[tuple[int, int]] = []
    out: list[Moment] = []
    for p in peaks:
        if len(out) >= top or combined[p] <= 0:
            break
        if any(a - 2 <= p < b + 2 for a, b in taken):
            continue
        best = None
        for L in range(min_len, max_len + 1, 3):
            a = max(0, min(p - lead_in, n - L))
            b = a + L
            if any(not (b <= ta or a >= tb) for ta, tb in taken):
                continue
            # Mean score, with a 0.5%/s penalty on length so tight clips win ties.
            sc = mean(a, b) * (1 - 0.005 * (L - min_len)) + 0.25 * combined[p]
            if best is None or sc > best[0]:
                best = (sc, a, b)
        if not best:
            continue
        sc, a, b = best
        breakdown = {}
        for k, curve in meta["curves"].items():
            seg = curve[a:b]
            breakdown[k] = meta["weights"][k] * (sum(seg) / max(1, len(seg)))
        out.append(Moment(a, b, sc, p, breakdown))
        taken.append((a, b))
    out.sort(key=lambda m: m.score, reverse=True)
    return out


def why(m: Moment) -> str:
    """Plain-language reason for a pick: the top two contributing signals."""
    names = {"loudness": "loud spike", "hype": "hype words", "replayed": "most replayed",
             "chat": "chat explosion", "scenes": "fast action"}
    top = sorted(m.breakdown.items(), key=lambda kv: kv[1], reverse=True)[:2]
    return " + ".join(names.get(k, k) for k, v in top if v > 0) or "steady"


def breakdown_table(moments: list[Moment], signal_names: list[str]) -> str:
    head = ["#", "start", "len", "score"] + signal_names + ["why"]
    rows = []
    for i, m in enumerate(moments, 1):
        mm, ss = divmod(m.start, 60)
        cells = [i, f"{mm}:{ss:02d}", f"{m.length}s", f"{m.score:.3f}"]
        cells += [f"{m.breakdown.get(k, 0):.3f}" if k in m.breakdown else "n/a" for k in signal_names]
        cells.append(why(m))
        rows.append(cells)
    lines = ["| " + " | ".join(map(str, head)) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    return "\n".join(lines)
