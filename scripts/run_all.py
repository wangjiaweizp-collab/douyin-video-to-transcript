# -*- coding: utf-8 -*-
"""一键跑完整流程：抓全量 → 下载 → 转音频/转写/合并。失败即停，不重试。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["01_fetch_works.py", "02_download.py", "03_transcribe.py"]


def main():
    for s in STEPS:
        print(f"\n{'=' * 60}\n>>> {s}\n{'=' * 60}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / s)], check=False)
        if r.returncode != 0:
            print(f"\n[ABORT] {s} 失败（退出码 {r.returncode}），流程停止，不自动重试。", flush=True)
            return r.returncode
    print("\n[DONE] 全部完成。查看 workspace/ 下的文字稿与 progress.log。", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
