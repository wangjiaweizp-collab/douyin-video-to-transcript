# -*- coding: utf-8 -*-
"""离线自检：不联网、不启动浏览器、不需要 faster-whisper / ffmpeg。

CI 与本地都跑这一份，用于挡住「换个环境就坏」的低级回归：
语法、配置模板、路径推导、时区换算、命名与排序、必需文件、敏感文件。
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PASS, FAIL = [], []


def check(name: str, fn):
    """执行单个断言，收集结果而不是一出错就退出，便于一次看到全部问题。"""
    try:
        fn()
        PASS.append(name)
    except Exception as e:
        FAIL.append(f"{name}: {type(e).__name__}: {e}")


def t_syntax():
    for p in sorted(SCRIPTS.glob("*.py")):
        compile(p.read_text(encoding="utf-8"), str(p), "exec")


def t_config_template():
    d = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
    assert isinstance(d["cdp_port"], int) and d["cdp_port"] > 0
    assert d["user_url"].startswith("https://www.douyin.com/user/")
    assert "cookie" in d and "model" in d
    # 模板里绝不能出现真实凭据
    assert "sessionid=" not in json.dumps(d, ensure_ascii=False)


def t_required_files():
    required = [
        "README.md", "README.en.md", "LICENSE", "DISCLAIMER.md", "CHANGELOG.md",
        "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
        "requirements.txt", "config.example.json", "pyproject.toml", ".gitignore",
        ".github/workflows/ci.yml", "docs/ARCHITECTURE.md", "docs/TROUBLESHOOTING.md",
        "scripts/lib.py", "scripts/01_fetch_works.py", "scripts/02_download.py",
        "scripts/03_transcribe.py", "scripts/run_all.py",
    ]
    missing = [f for f in required if not (ROOT / f).exists()]
    assert not missing, f"缺少文件: {missing}"


def t_lib_paths():
    import lib
    cfg = lib.load_config(str(ROOT / "config.example.json"))
    assert cfg["cdp_port"] == 9224
    assert cfg["_config_path"].endswith("config.example.json")
    # 路径必须从 __file__ 推导，不能含有本机用户名或盘符
    d = lib.work_dirs(cfg)
    assert d["base"].name == "workspace"
    assert "acer" not in str(d["base"])


def t_time():
    import lib
    # create_time 是 Unix 秒；固定按 UTC+8 换算，与系统时区无关
    assert lib.stamp(1793334026) == "20261030_122026"
    assert lib.display_time(1793334026) == "2026-10-30 12:20"


def t_sec_uid():
    import lib
    fake = "M" * 30
    assert lib.sec_uid_from_url(f"https://www.douyin.com/user/{fake}?from_tab_name=main") == fake
    try:
        lib.sec_uid_from_url("https://www.douyin.com/jingxuan")
        raise AssertionError("非法链接应当抛错")
    except ValueError:
        pass


def t_cookie_parse():
    import lib
    cks = lib.parse_cookie("a=1; b=two=three; ; c=3")
    assert len(cks) == 3
    assert cks[1]["value"] == "two=three"          # 值里的等号必须保留
    assert all(c["domain"] == ".douyin.com" for c in cks)


def t_naming_and_sort():
    m = importlib.import_module("03_transcribe")  # 模块名以数字开头，用 importlib
    p = Path("20261106_183307_7705004629935548584_desc.txt")
    assert m.sort_key(p) == (0, "20261106183307")
    # 文件名前缀即权威发布时间，正则必须能取到「日期_时分」
    mm = re.match(r"^(\d{8})_(\d{6})_", p.stem)
    assert mm and mm.group(1) == "20261106" and mm.group(2) == "183307"
    earlier = Path("20260828_145010_7678971209938495336_desc.txt")
    assert m.sort_key(earlier) < m.sort_key(p)


def t_no_secrets_tracked():
    # 本地有 git 时，检查暂存区/索引里是否误入敏感文件
    import subprocess
    if not (ROOT / ".git").exists():
        return
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    bad = [l for l in out.splitlines() if re.search(
        r"(^|/)(config\.json|workspace/|\.env|cookie[^/]*\.txt|.*\.(mp4|wav|zip)$)", l)]
    assert not bad, f"索引中含敏感文件: {bad}"


def main() -> int:
    for name, fn in [
        ("脚本语法编译", t_syntax),
        ("配置模板合法且无真实凭据", t_config_template),
        ("必需文件齐全", t_required_files),
        ("路径从 __file__ 推导", t_lib_paths),
        ("UTC+8 时间换算", t_time),
        ("sec_uid 解析", t_sec_uid),
        ("Cookie 解析", t_cookie_parse),
        ("命名与排序", t_naming_and_sort),
        ("无敏感文件入索引", t_no_secrets_tracked),
    ]:
        check(name, fn)
    # 只清理自检自己创建的空目录，绝不删除使用者已有的产物
    ws = ROOT / "workspace"
    if ws.exists():
        for sub in ("videos", "03_transcripts", "_cdp_profile"):
            p = ws / sub
            if p.exists() and not any(p.iterdir()):
                p.rmdir()
        if not any(ws.iterdir()):
            ws.rmdir()

    for name in PASS:
        print(f"  PASS  {name}")
    for name in FAIL:
        print(f"  FAIL  {name}")
    print(f"\n自检结果: {len(PASS)} 通过 / {len(FAIL)} 失败")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
