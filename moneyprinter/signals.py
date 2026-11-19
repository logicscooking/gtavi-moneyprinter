"""Fetch a source and extract every per-second signal the scorer can use.

Each extractor returns None when its signal is unavailable. Nothing is faked.
"""
from __future__ import annotations

import array
import json
import math
import re
import sys
from pathlib import Path

from .util import is_url, load_json, need, run, save_json, short_hash, slug, tool, workspace

INFO_KEYS = ("id", "title", "uploader", "channel", "uploader_id", "channel_url", "webpage_url", "duration",
             "view_count", "timestamp", "upload_date", "heatmap", "is_live", "was_live", "extractor_key")


def log(msg: str) -> None:
    print(f"[moneyprinter] {msg}", file=sys.stderr, flush=True)


def resolve(query_or_url: str) -> str:
    """A URL or local file passes through; a text query becomes the top YouTube search result."""
    if is_url(query_or_url) or Path(query_or_url).exists():
        return query_or_url
    p = run([need("yt-dlp"), "--flat-playlist", "-J", f"ytsearch5:{query_or_url}"], timeout=120)
    entries = (json.loads(p.stdout or "{}").get("entries") or [])
    entries = [e for e in entries if e.get("id") and (e.get("duration") or 0) > 20]
    if not entries:
        sys.exit(f"[moneyprinter] no video found for '{query_or_url}'")
    url = entries[0].get("url") or f"https://www.youtube.com/watch?v={entries[0]['id']}"
    log(f"query '{query_or_url}' -> {entries[0].get('title')} ({url})")
    return url


def job_for(src: str) -> Path:
    d = workspace() / "jobs" / f"{slug(Path(src).stem if not is_url(src) else src.split('=')[-1].split('/')[-1], 24)}-{short_hash(src)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch(src: str, job: Path, max_minutes: float = 60) -> tuple[Path, dict]:
    """Download (or link) the source video and save trimmed metadata to info.json."""
    info = load_json(job / "info.json", {}) or {}
    vid = job / "source.mp4"
    if is_url(src):
        if not info:
            p = run([need("yt-dlp"), "-J", "--no-playlist", src], timeout=180)
            full = json.loads(p.stdout or "{}")
            info = {k: full.get(k) for k in INFO_KEYS}
            save_json(job / "info.json", info)
        if not vid.exists():
            args = [need("yt-dlp"), "--no-playlist", "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b",
                    "--merge-output-format", "mp4", "-o", str(vid)]
            ff = tool("ffmpeg")
            if ff:
                args += ["--ffmpeg-location", str(Path(ff).parent)]
            if (info.get("duration") or 0) > max_minutes * 60:
                args += ["--download-sections", f"*0-{int(max_minutes * 60)}"]
            log("downloading source ...")
            run(args + [src], timeout=1800)
    else:
        local = Path(src).resolve()
        if not vid.exists():
            try:
                vid.symlink_to(local)
            except OSError:
                import shutil
                shutil.copy2(local, vid)
        if not info:
            info = {"title": local.stem, "webpage_url": str(local), "uploader": None}
            save_json(job / "info.json", info)
    return vid, info


def duration_of(vid: Path) -> float:
    p = run([need("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(vid)])
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def loudness(vid: Path, job: Path) -> list[float] | None:
    """Per-second RMS level in dB from an 8 kHz mono decode."""
    cache = job / "sig_loudness.json"
    if cache.exists():
        return load_json(cache)
    sr = 8000
    p = __import__("subprocess").run([need("ffmpeg"), "-v", "error", "-i", str(vid), "-vn", "-ac", "1", "-ar", str(sr),
                                      "-f", "s16le", "-"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    a = array.array("h")
    a.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    out = []
    for i in range(0, len(a) - sr + 1, sr):
        chunk = a[i:i + sr]
        ms = sum(x * x for x in chunk) / sr
        out.append(20 * math.log10(math.sqrt(ms) / 32768 + 1e-6))
    save_json(cache, out)
    return out or None


def scene_cuts(vid: Path, job: Path, threshold: float = 10.0) -> list[float] | None:
    """Timestamps of scene changes via ffmpeg scdet (on a small downscale, so it's fast)."""
    cache = job / "sig_scenes.json"
    if cache.exists():
        return load_json(cache)
    p = run([need("ffmpeg"), "-hide_banner", "-i", str(vid), "-an", "-vf",
             f"fps=10,scale=240:-2,scdet=threshold={threshold}", "-f", "null", "-"], check=False, timeout=1800)
    times = [float(t) for t in re.findall(r"lavfi\.scd\.time:\s*([0-9.]+)", p.stderr or "")]
    save_json(cache, times)
    return times


def _parse_vtt(text: str) -> list[dict]:
    """YouTube auto-captions VTT -> word list with approximate timings (dedupes rolling lines)."""
    words, seen = [], set()
    ts = re.compile(r"(\d+):(\d+):(\d+)\.(\d+) --> (\d+):(\d+):(\d+)\.(\d+)")
    blocks = re.split(r"\n\s*\n", text)
    for b in blocks:
        m = ts.search(b)
        if not m:
            continue
        g = list(map(int, m.groups()))
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        e = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = b[m.end():].strip().splitlines()
        for line in body:
            clean = re.sub(r"<[^>]+>", "", line).strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            toks = clean.split()
            step = max(0.05, (e - a) / max(1, len(toks)))
            for i, t in enumerate(toks):
                words.append({"start": round(a + i * step, 2), "end": round(a + (i + 1) * step, 2), "word": t})
    return words


def transcript(vid: Path, job: Path, src: str, model: str = "small") -> tuple[list[dict] | None, str]:
    """Word timestamps: faster-whisper first, then YouTube captions, else None (graceful)."""
    cache = job / "transcript.json"
    if cache.exists():
        d = load_json(cache, {})
        return d.get("words"), d.get("engine", "cache")
    try:
        from faster_whisper import WhisperModel  # type: ignore
        try:
            import ctranslate2  # type: ignore
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
        log(f"transcribing with faster-whisper ({model}, {device}) ...")
        wm = WhisperModel(model, device=device, compute_type="float16" if device == "cuda" else "int8")
        segs, _ = wm.transcribe(str(vid), word_timestamps=True, vad_filter=True)
        words = [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word.strip()}
                 for s in segs for w in (s.words or [])]
        save_json(cache, {"engine": "faster-whisper", "words": words})
        return words, "faster-whisper"
    except ImportError:
        log("faster-whisper not installed: trying YouTube captions instead")
    except Exception as ex:  # model download failure, etc.
        log(f"faster-whisper failed ({ex}): trying YouTube captions instead")
    if is_url(src):
        run([need("yt-dlp"), "--skip-download", "--no-playlist", "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,en",
             "--sub-format", "vtt", "-o", str(job / "subs"), src], check=False, timeout=180)
        vtts = sorted(job.glob("subs*.vtt"))
        if vtts:
            words = _parse_vtt(vtts[0].read_text(encoding="utf-8", errors="replace"))
            if words:
                save_json(cache, {"engine": "youtube-captions", "words": words})
                return words, "youtube-captions"
    log("no transcript available: hype-word signal and captions skipped")
    return None, "none"


def chat_times(job: Path, src: str, info: dict, chat_file: str | None = None) -> list[float] | None:
    """Chat message timestamps (seconds from video start).

    Sources: an explicit file (TwitchDownloader JSON, moneyprinter live JSONL, or plain 'seconds' lines),
    or YouTube live-chat replay for past streams.
    """
    path = Path(chat_file) if chat_file else None
    if not path and is_url(src) and info.get("was_live"):
        run([need("yt-dlp"), "--skip-download", "--no-playlist", "--write-subs", "--sub-langs", "live_chat",
             "-o", str(job / "chat"), src], check=False, timeout=600)
        found = list(job.glob("chat*.live_chat.json"))
        path = found[0] if found else None
    if not path or not path.exists():
        return None
    return parse_chat(path.read_text(encoding="utf-8", errors="replace"))


def parse_chat(text: str) -> list[float] | None:
    text = text.strip()
    times: list[float] = []
    if text.startswith("{") and '"comments"' in text[:2000]:  # TwitchDownloader
        d = json.loads(text)
        times = [float(c.get("content_offset_seconds", 0)) for c in d.get("comments", [])]
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if "t" in o:  # moneyprinter live recorder
                    times.append(float(o["t"]))
                    continue
                # YouTube live_chat replay line
                off = (o.get("replayChatItemAction") or {}).get("videoOffsetTimeMsec")
                if off is not None:
                    times.append(int(off) / 1000)
            else:
                try:
                    times.append(float(line.split()[0]))
                except ValueError:
                    pass
    return times or None
