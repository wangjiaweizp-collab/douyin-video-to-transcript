# -*- coding: utf-8 -*-
"""步骤 2：按发布时间命名，下载全部 mp4 与文案。

命名：YYYYMMDD_HHMMSS_<aweme_id>_video.mp4 / _desc.txt
直接用接口返回的 play_addr 直链下载（带 UA + Referer 即可，不需要 Cookie）。
无视频流的图文作品只写 _desc.txt，留给步骤 3 在时间线里如实标注。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import load_config, log, stamp, work_dirs

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Referer": "https://www.douyin.com/"}


def fetch(url: str, dst: Path) -> tuple[bool, str]:
    """优先 requests，失败回退系统 curl。返回 (ok, 错误摘要)。"""
    try:
        import requests
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        data = r.content
        if len(data) < 100_000:
            return False, f"响应过小 {len(data)} 字节"
        dst.write_bytes(data)
        return True, ""
    except Exception as e:
        first = str(e)[:120]
    curl = shutil.which("curl")
    if not curl:
        return False, f"requests 失败且无 curl: {first}"
    try:
        r = subprocess.run([curl, "-L", "-sS", "--max-time", "120",
                            "-A", UA, "-e", "https://www.douyin.com/",
                            "-o", str(dst), url], capture_output=True, text=True, timeout=150)
        if r.returncode != 0 or not dst.exists() or dst.stat().st_size < 100_000:
            return False, f"curl rc={r.returncode} {(r.stderr or '')[:100]}"
        return True, ""
    except Exception as e:
        return False, f"curl 失败: {str(e)[:120]}"


def main():
    cfg = load_config()
    d = work_dirs(cfg)
    src = d["works"]
    if not src.exists():
        raise RuntimeError("找不到 works.json，请先运行 01_fetch_works.py")
    meta = json.loads(src.read_text(encoding="utf-8"))
    works = meta["works"]

    ok = skip = fail = 0
    failures = []
    for w in works:
        aid = w["aweme_id"]
        ct = w.get("create_time")
        if not ct:
            failures.append((aid, "缺少 create_time"))
            fail += 1
            continue
        prefix = f"{stamp(ct)}_{aid}"
        desc_f = d["videos"] / f"{prefix}_desc.txt"
        if not desc_f.exists():
            desc_f.write_text(w.get("desc") or "", encoding="utf-8")

        if not w.get("is_video"):
            continue
        mp4 = d["videos"] / f"{prefix}_video.mp4"
        # 断点续跑：已存在且体积合理就跳过，避免重复请求同一 CDN 触发风控。
        if mp4.exists() and mp4.stat().st_size > 100_000:
            skip += 1
            continue
        done = False
        for url in (w.get("play_urls") or []):
            good, err = fetch(url, mp4)
            if good:
                done = True
                ok += 1
                log(f"下载 {mp4.name} ({mp4.stat().st_size // 1024} KB)", cfg, d, "STEP2")
                break
            last = err
        if not done:
            fail += 1
            failures.append((aid, locals().get("last", "无可用播放地址")))
            log(f"FAIL {aid} | {failures[-1][1]}", cfg, d, "ERROR")

    log(f"下载完成：新增 {ok}，跳过已有 {skip}，失败 {fail}；共 {meta['total']} 个作品", cfg, d, "STEP2")
    for aid, err in failures:
        log(f"失败清单 {aid} | {err}", cfg, d, "ERROR")
    print(f"\n视频文件数: {len(list(d['videos'].glob('*.mp4')))}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
