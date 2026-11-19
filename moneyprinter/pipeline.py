"""find -> score -> cut -> check -> package, one folder per clip."""
from __future__ import annotations

from pathlib import Path

from . import check, hooks, package, render, scoring, signals
from .util import fmt_ts, save_json, slug, workspace

SIGNALS = ["loudness", "hype", "replayed", "chat", "scenes"]


def score_source(src: str, top: int = 3, min_len: int = 12, max_len: int = 35, chat: str | None = None,
                 max_minutes: float = 60, whisper_model: str = "small") -> dict:
    src = signals.resolve(src)
    job = signals.job_for(src)
    vid, info = signals.fetch(src, job, max_minutes)
    dur = int(signals.duration_of(vid))
    signals.log(f"job {job.name}: {dur}s, extracting signals ...")
    words, engine = signals.transcript(vid, job, src, whisper_model)
    sig = {
        "loudness": signals.loudness(vid, job),
        "hype": scoring.hype_per_second(words, dur) if words else None,
        "replayed": scoring.heatmap_per_second(info.get("heatmap"), dur),
        "chat": scoring.rate_per_second(signals.chat_times(job, src, info, chat), dur),
        "scenes": scoring.rate_per_second(signals.scene_cuts(vid, job), dur),
    }
    sig = {k: (v[:dur] if v else None) for k, v in sig.items()}
    available = {k: bool(v and any(v)) for k, v in sig.items()}
    moments = scoring.pick_moments(sig, top=top, min_len=min_len, max_len=min(max_len, max(min_len, dur)))
    table = scoring.breakdown_table(moments, SIGNALS)
    lines = [f"# Moments: {info.get('title')}", "", f"source: {info.get('webpage_url') or src}",
             f"transcript: {engine}", "signals: " + ", ".join(f"{k}={'yes' if v else 'missing'}" for k, v in available.items()),
             "", "Each column is that signal's weighted contribution (missing signals are skipped, not faked).", "", table, ""]
    for i, m in enumerate(moments, 1):
        said = " ".join(w["word"] for w in (words or []) if m.start <= w["start"] < m.end)
        lines.append(f"{i}. {fmt_ts(m.start)}-{fmt_ts(m.end)} peak {fmt_ts(m.peak)}: {said[:160] or '(no transcript)'}")
    (job / "moments.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    save_json(job / "moments.json", {"signals_available": available, "moments": [m.to_dict() for m in moments]})
    return {"src": src, "job": job, "video": vid, "info": info, "words": words, "moments": moments, "table": table,
            "loud": sig["loudness"] or [],
            "available": available, "engine": engine}


def creator_handle(info: dict, override: str | None = None) -> str:
    h = override or info.get("uploader_id") or info.get("channel") or info.get("uploader") or "creator"
    h = str(h).lstrip("@").replace(" ", "")
    return f"via @{h}"


def make_clip(sc: dict, idx: int, layout: str = "blur", face=None, commentary: str | None = None,
              credit: str | None = None, campaign_text: str | None = None, seed: int | None = None) -> dict:
    m = sc["moments"][idx]
    info, words = sc["info"], sc["words"]
    said = " ".join(w["word"] for w in (words or []) if m.start <= w["start"] < m.end)
    hk = hooks.make_hooks(m.breakdown, m.length, said, seed=seed)
    cred = creator_handle(info, credit)
    clip_id = f"{sc['job'].name}-{idx + 1}"
    out = workspace() / "clips" / f"{slug(info.get('title') or 'clip', 28)}-{idx + 1}-{sc['job'].name[-8:]}"
    # punch-ins: the fused peak plus the loudest other second inside the window
    peaks = [m.peak]
    loud = sc.get("loud") or []
    inside = [s for s in range(m.start + 1, m.end - 1) if abs(s - m.peak) > 3 and s < len(loud)]
    if inside:
        peaks.append(max(inside, key=lambda s: loud[s]))
    man = render.render_clip(sc["video"], out, m.start, m.end, hk[0]["text"], words, cred, layout, face,
                             punch_at=peaks, commentary=commentary)
    frames = [m.peak, min(m.end - 1, m.peak + 1.5), m.start + m.length / 3]
    for i, (h, t) in enumerate(zip(hk, frames), 1):
        render.render_cover(sc["video"], out, t, h["text"], cred, layout, face, f"cover_{i}.jpg")
    (out / "cover.jpg").write_bytes((out / "cover_1.jpg").read_bytes())
    man.update({"id": clip_id, "source": sc["info"].get("webpage_url") or sc["src"], "source_file": str(sc["video"]),
                "title": info.get("title"), "hooks": hk, "score": round(m.score, 4), "breakdown": m.to_dict()["breakdown"],
                "covers": ["cover_1.jpg", "cover_2.jpg", "cover_3.jpg"], "face": face})
    save_json(out / "manifest.json", man)
    (out / "post.txt").write_text(package.post_text(hk, info.get("title") or "", cred, man["source"]), encoding="utf-8")
    ok, res = check.check_clip(out, campaign_text)
    man["check"] = {"pass": ok, "results": [{"rule": r, "pass": p, "detail": d} for r, p, d in res]}
    save_json(out / "manifest.json", man)
    hooks.register_clip(clip_id, {"folder": str(out), "hooks": hk, "score": man["score"], "check_pass": ok,
                                  "title": info.get("title")})
    return {"dir": out, "ok": ok, "results": res, "manifest": man}


def run(src: str, top: int = 3, layout: str = "blur", face=None, commentary: str | None = None,
        campaign: str | None = None, chat: str | None = None, min_len: int = 12, max_len: int = 35,
        credit: str | None = None, max_minutes: float = 60) -> list[dict]:
    sc = score_source(src, top=top, min_len=min_len, max_len=max_len, chat=chat, max_minutes=max_minutes)
    print(f"\nWHY these moments ({sc['engine']} transcript):\n{sc['table']}\n")
    camp = Path(campaign).read_text(encoding="utf-8", errors="replace") if campaign else None
    out = []
    for i in range(len(sc["moments"])):
        r = make_clip(sc, i, layout, face, commentary, credit, camp)
        print(f"clip {i + 1}: {'PASS' if r['ok'] else 'FAIL'} -> {r['dir']}")
        print(check.report(r["results"]))
        out.append(r)
    return out
