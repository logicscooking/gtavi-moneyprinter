"""Cut a 1080x1920 clip with real transformations and write cover variants.

Transformations applied (recorded in manifest.json so `check` can verify them):
  hook_overlay, captions, zoom_punch_ins, facecam_layout / reaction_layout, commentary_slot
plus the mandatory credit overlay "via @creator".
"""
from __future__ import annotations

from pathlib import Path

from .util import need, run, save_json

W, H = 1080, 1920
FACE_PRESETS = {  # x, y, w, h as fractions of the source frame
    "tl": (0.0, 0.0, 0.28, 0.32), "tr": (0.72, 0.0, 0.28, 0.32),
    "bl": (0.0, 0.68, 0.28, 0.32), "br": (0.72, 0.68, 0.28, 0.32),
}


def parse_face(face: str | None):
    if not face:
        return None
    if face in FACE_PRESETS:
        return FACE_PRESETS[face]
    parts = [float(x) for x in face.split(",")]
    if len(parts) != 4:
        raise ValueError("--face must be tl/tr/bl/br or x,y,w,h fractions")
    return tuple(parts)


def layout_filter(layout: str, face=None) -> tuple[str, int]:
    """Return (filtergraph from [0:v] to [v0], y of the 'seam' where the hook sits)."""
    if layout == "fill":
        return f"[0:v]scale=-2:{H},crop={W}:{H},setsar=1[v0]", 300
    if layout in ("facecam", "reaction"):
        fx, fy, fw, fh = face or FACE_PRESETS["br"]
        top = 640
        g = (f"[0:v]split[a][b];[a]crop=iw*{fw}:ih*{fh}:iw*{fx}:ih*{fy},scale={W}:{top}:force_original_aspect_ratio=increase,"
             f"crop={W}:{top}[face];[b]scale=-2:{H - top},crop={W}:{H - top}[game];[face][game]vstack,setsar=1[v0]")
        return g, top
    # default: blurred background, full frame centred
    g = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2[bg];"
         f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]")
    return g, 360


def zoom_filter(punch: list[tuple[float, float]], fps: int = 30) -> str:
    if not punch:
        return "[v0]null[v1]"
    z = "+".join(f"0.12*between(in_time,{a:.2f},{b:.2f})" for a, b in punch)
    return (f"[v0]zoompan=z='1+{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={fps}[v1]")


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def caption_chunks(words: list[dict], start: float, end: float, per: int = 3) -> list[tuple[float, float, str]]:
    """Words inside [start, end) grouped into short chunks, times relative to the clip."""
    ws = [w for w in words or [] if start <= w["start"] < end and str(w.get("word", "")).strip()]
    out = []
    for i in range(0, len(ws), per):
        grp = ws[i:i + per]
        a = grp[0]["start"] - start
        b = min(end - start, max(grp[-1]["end"] - start, a + 0.4))
        out.append((a, b, " ".join(str(w["word"]).strip() for w in grp)))
    # no overlaps
    for i in range(len(out) - 1):
        if out[i][1] > out[i + 1][0]:
            out[i] = (out[i][0], out[i + 1][0], out[i][2])
    return out


def build_ass(hook: str, chunks, length: float, credit: str, seam_y: int, commentary: str | None = None,
              hook_secs: float | None = None) -> str:
    hook_end = length if hook_secs is None else min(length, hook_secs)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Arial,78,&H00FFFFFF,&H00FFFFFF,&H00B0167A,&H00B0167A,1,0,0,0,100,100,0,0,3,18,0,8,70,70,{max(40, seam_y - 70)},1
Style: Cap,Arial,92,&H00FFFFFF,&H0000E6FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,7,3,2,60,60,520,1
Style: Credit,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,1,0,0,0,100,100,0,0,1,3,1,9,40,40,60,1
Style: Comment,Arial,54,&H00101010,&H00101010,&H0040D8FF,&H0040D8FF,1,0,0,0,100,100,0,0,3,14,0,2,80,80,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 2,{_ass_time(0)},{_ass_time(hook_end)},Hook,,0,0,0,,{{\\fad(120,0)}}{_esc(hook).upper()}"]
    for a, b, txt in chunks:
        ev.append(f"Dialogue: 1,{_ass_time(a)},{_ass_time(b)},Cap,,0,0,0,,{{\\fscx80\\fscy80\\t(0,90,\\fscx100\\fscy100)}}{_esc(txt).upper()}")
    ev.append(f"Dialogue: 3,{_ass_time(0)},{_ass_time(length)},Credit,,0,0,0,,{_esc(credit)}")
    if commentary:
        ev.append(f"Dialogue: 2,{_ass_time(min(1.0, length / 3))},{_ass_time(length)},Comment,,0,0,0,,{_esc(commentary)}")
    return head + "\n".join(ev) + "\n"


def srt(chunks) -> str:
    def t(x):
        ms = int(round(x * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return "\n".join(f"{i}\n{t(a)} --> {t(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(chunks, 1))


def render_clip(source: Path, out_dir: Path, start: float, end: float, hook: str, words: list[dict] | None,
                credit: str, layout: str = "blur", face=None, punch_at: list[float] | None = None,
                commentary: str | None = None, name: str = "clip.mp4", captions: bool = True,
                srt_override: Path | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    length = round(end - start, 2)
    graph, seam = layout_filter(layout, face)
    if srt_override and srt_override.exists():
        chunks = parse_srt(srt_override.read_text(encoding="utf-8"))
    else:
        chunks = caption_chunks(words or [], start, end) if captions else []
    punch = []
    for p in punch_at or []:
        rel = p - start
        if 0.3 <= rel < length - 0.6:
            punch.append((rel, min(length, rel + 0.9)))
    ass_name = name.rsplit(".", 1)[0] + ".ass"
    (out_dir / ass_name).write_text(build_ass(hook, chunks, length, credit, seam, commentary), encoding="utf-8")
    if not srt_override:
        (out_dir / "captions.srt").write_text(srt(chunks), encoding="utf-8")
    fg = f"{graph};{zoom_filter(punch)};[v1]ass={ass_name},format=yuv420p[v]"
    run([need("ffmpeg"), "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", str(source.resolve()),
         "-filter_complex", fg, "-map", "[v]", "-map", "0:a?", "-r", "30",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-movflags", "+faststart", name], cwd=out_dir, timeout=1800)
    tr = ["hook_overlay"]
    if chunks:
        tr.append("captions")
    if punch:
        tr.append("zoom_punch_ins")
    if layout in ("facecam", "reaction"):
        tr.append(f"{layout}_layout")
    if commentary:
        tr.append("commentary_slot")
    return {"file": name, "start": start, "end": end, "length": length, "layout": layout, "hook": hook,
            "credit": credit, "transformations": tr, "credit_overlay": bool(credit), "punch_ins": punch,
            "caption_chunks": len(chunks)}


def parse_srt(text: str):
    import re
    out = []
    for blk in re.split(r"\n\s*\n", text.strip()):
        m = re.search(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)\s*\n(.+)", blk, re.S)
        if m:
            g = [int(x) for x in m.groups()[:8]]
            a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
            b = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
            out.append((a, b, " ".join(m.group(9).split())))
    return out


def render_cover(source: Path, out_dir: Path, at: float, hook: str, credit: str, layout: str, face, name: str) -> Path:
    graph, seam = layout_filter(layout, face)
    ass_name = name.rsplit(".", 1)[0] + ".ass"
    # No fade-in on a still frame (frame 0 would be transparent), and a bigger hook.
    ass = build_ass(hook, [], 5, credit, seam).replace(",78,", ",104,", 1).replace("{\\fad(120,0)}", "")
    (out_dir / ass_name).write_text(ass, encoding="utf-8")
    run([need("ffmpeg"), "-y", "-v", "error", "-ss", f"{max(0, at):.2f}", "-i", str(source.resolve()),
         "-filter_complex", f"{graph};[v0]ass={ass_name}[v]", "-map", "[v]", "-frames:v", "1", "-q:v", "3", name],
        cwd=out_dir, timeout=300)
    (out_dir / ass_name).unlink(missing_ok=True)
    return out_dir / name
