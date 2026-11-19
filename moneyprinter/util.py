"""Small helpers shared by every module: tool lookup, subprocess, JSON, workspace paths."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def workspace() -> Path:
    """Where jobs, clips and the ledger live. Override with MONEYPRINTER_HOME."""
    p = Path(os.environ.get("MONEYPRINTER_HOME", Path.cwd() / "moneyprinter-work"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def tool(name: str) -> str | None:
    """Find a binary on PATH or in ~/.local/bin (common for user installs)."""
    env = os.environ.get(f"MONEYPRINTER_{name.upper().replace('-', '_')}")
    if env and Path(env).exists():
        return env
    found = shutil.which(name)
    if found:
        return found
    for extra in (Path.home() / ".local" / "bin" / name, Path("/opt/homebrew/bin") / name, Path("/usr/local/bin") / name):
        for cand in (extra, extra.with_suffix(".exe")):
            if cand.exists():
                return str(cand)
    return None


def need(name: str) -> str:
    t = tool(name)
    if not t:
        sys.exit(f"[moneyprinter] '{name}' not found. Run: python moneyprinter.py doctor")
    return t


def run(cmd: list, check: bool = True, capture: bool = True, timeout: float | None = None,
        cwd: Path | None = None) -> subprocess.CompletedProcess:
    p = subprocess.run([str(c) for c in cmd], capture_output=capture, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace", cwd=cwd)
    if check and p.returncode != 0:
        tail = (p.stderr or "")[-1500:]
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd[:4]))} ...\n{tail}")
    return p


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s or ""))


def slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s or "").strip("-").lower()
    return (s[:n] or "clip").strip("-")


def short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def load_json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(p: Path, obj) -> Path:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def fmt_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def ffprobe(path: Path) -> dict:
    p = run([need("ffprobe"), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    return json.loads(p.stdout or "{}")
