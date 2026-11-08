# -*- coding: utf-8 -*-
"""公共工具：配置、路径、时间、日志、Chrome 定位。

设计原则：所有路径从 __file__ 或配置推导，绝不写死任何机器的绝对路径。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 工作流包根目录
TZ_CN = timezone(timedelta(hours=8))                  # 抖音 create_time 是 UTC 秒，展示用中国时间

DEFAULTS = {
    "user_url": "",
    "cookie": "",
    "chrome_path": "",
    "cdp_port": 9224,
    "work_dir": "",
    "model": "medium",
    "model_path": "",
    "output_name": "全部作品时间线文字稿.md",
    "scroll_rounds": 12,
    "scroll_interval_sec": 3,
    "headless": False,
}


def load_config(path: str | None = None) -> dict:
    """config.json > 环境变量 > 默认值。"""
    p = Path(path or os.environ.get("DY_CONFIG") or ROOT / "config.json")
    cfg = dict(DEFAULTS)
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    cfg["user_url"] = os.environ.get("DY_USER_URL") or cfg["user_url"]
    cfg["cookie"] = os.environ.get("DY_COOKIE") or cfg["cookie"]
    cfg["chrome_path"] = os.environ.get("DY_CHROME") or cfg["chrome_path"]
    cfg["_config_path"] = str(p)
    return cfg


def work_dirs(cfg: dict) -> dict:
    # 所有路径从包根目录推导：换机器、换用户名、换盘符都不需要改代码。
    base = Path(cfg["work_dir"] or (ROOT / "workspace")).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    d = {
        "base": base,
        "videos": base / "videos",
        "transcripts": base / "03_transcripts",
        "cdp_profile": base / "_cdp_profile",
        "works": base / "works.json",
        "progress": base / "progress.log",
        "output": base / cfg["output_name"],
    }
    for k in ("videos", "transcripts", "cdp_profile"):
        d[k].mkdir(parents=True, exist_ok=True)
    return d


def log(msg: str, cfg: dict | None = None, d: dict | None = None, tag: str = "INFO") -> None:
    line = f"[{datetime.now(TZ_CN):%Y-%m-%d %H:%M:%S}] [{tag}] {msg}"
    print(line, flush=True)
    if d:
        with d["progress"].open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def stamp(create_time: int | float) -> str:
    """UTC 秒 -> YYYYMMDD_HHMMSS（中国时间）。"""
    return datetime.fromtimestamp(int(create_time), TZ_CN).strftime("%Y%m%d_%H%M%S")


def display_time(create_time: int | float) -> str:
    return datetime.fromtimestamp(int(create_time), TZ_CN).strftime("%Y-%m-%d %H:%M")


def sec_uid_from_url(url: str) -> str:
    m = re.search(r"/user/([A-Za-z0-9_\-]{20,})", url)
    if not m:
        raise ValueError(f"user_url 不是合法的抖音用户主页链接: {url}")
    return m.group(1)


def parse_cookie(raw: str) -> list[dict]:
    out = []
    for part in raw.split(";"):
        if "=" not in part:
            continue
        n, v = part.strip().split("=", 1)
        if n:
            out.append({"name": n, "value": v, "domain": ".douyin.com", "path": "/"})
    return out


def find_chrome(cfg: dict) -> str:
    explicit = cfg.get("chrome_path")
    if explicit and Path(explicit).exists():
        return explicit
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser"):
        w = shutil.which(name)
        if w:
            return w
    raise RuntimeError("未找到 Chrome，请在 config.json 的 chrome_path 里填写可执行文件完整路径")


def find_ffmpeg() -> str:
    w = shutil.which("ffmpeg")
    if w:
        return w
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise RuntimeError("未找到 ffmpeg，请安装 ffmpeg 或 pip install imageio-ffmpeg") from e


def cdp_base(cfg: dict) -> str:
    return f"http://127.0.0.1:{int(cfg['cdp_port'])}"


def require(cfg: dict, *keys: str) -> None:
    missing = [k for k in keys if not cfg.get(k)]
    if missing:
        raise ValueError(f"config.json 缺少必填项: {', '.join(missing)}；可参考 config.example.json")
