# -*- coding: utf-8 -*-
"""步骤 1：用浏览器自己翻页，抓全博主作品列表（解决下载器只给第一页的问题）。

原理：polydl / 各类 CLI 调 `aweme/v1/web/aweme/post/` 带 max_cursor 的第二页常被风控
返回空壳 {"status_code":0}，导致只拿到 20 条。改成启动一个带调试端口的独立 Chrome，
让抖音页面自己滚动加载（签名由页面生成），我们只监听它发出的接口响应。

输出：workspace/works.json
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (cdp_base, display_time, find_chrome, load_config, log,
                 parse_cookie, require, sec_uid_from_url, work_dirs)


class CDP:
    def __init__(self, ws_url: str, timeout: int = 40):
        import websocket
        self.ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self.n = 0

    def send(self, method: str, params: dict | None = None) -> int:
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        return self.n

    def wait(self, mid: int, timeout: float = 12) -> dict:
        end = time.time() + timeout
        while time.time() < end:
            self.ws.settimeout(max(0.5, end - time.time()))
            try:
                msg = json.loads(self.ws.recv())
            except Exception:
                continue
            if msg.get("id") == mid:
                return msg
        return {}

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def wait_cdp(base: str, seconds: int = 20):
    end = time.time() + seconds
    while time.time() < end:
        try:
            return json.load(urllib.request.urlopen(base + "/json/version", timeout=3))
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Chrome 调试端口未就绪，检查是否被占用或 Chrome 路径错误")


def main():
    cfg = load_config()
    require(cfg, "user_url", "cookie")
    d = work_dirs(cfg)
    sec = sec_uid_from_url(cfg["user_url"])
    base = cdp_base(cfg)
    chrome = find_chrome(cfg)

    args = [
        chrome,
        f"--remote-debugging-port={int(cfg['cdp_port'])}",
        f"--user-data-dir={d['cdp_profile']}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900",
    ]
    if cfg.get("headless"):
        args.append("--headless=new")
    args.append("https://www.douyin.com/user/" + sec)

    log(f"启动独立 Chrome（不影响你正在用的浏览器）: {chrome}", cfg, d, "STEP1")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ver = wait_cdp(base)
        log(f"CDP 就绪: {ver.get('Browser', '')}", cfg, d, "STEP1")

        targets = json.load(urllib.request.urlopen(base + "/json", timeout=10))
        page = next((t for t in targets if t.get("type") == "page" and "douyin.com" in (t.get("url") or "")), None)
        if not page:
            req = urllib.request.Request(base + "/json/new?https://www.douyin.com/user/" + sec, method="PUT")
            page = json.load(urllib.request.urlopen(req, timeout=10))

        c = CDP(page["webSocketDebuggerUrl"])
        cks = parse_cookie(cfg["cookie"])
        r = c.wait(c.send("Network.setCookies", {"cookies": cks}), 10)
        if (r.get("error") or {}).get("message"):
            log(f"注入 Cookie 失败: {r['error']['message']}", cfg, d, "WARN")
        c.send("Network.enable")
        c.send("Page.enable")
        c.send("Page.reload", {"ignoreCache": True})

        rids, pages = [], []
        last_scroll = time.time()
        scrolls = 0
        rounds = int(cfg["scroll_rounds"])
        interval = float(cfg["scroll_interval_sec"])
        end = time.time() + max(30, rounds * interval + 15)
        log(f"开始监听作品接口并滚动加载（最多 {rounds} 轮）…", cfg, d, "STEP1")
        while time.time() < end:
            c.ws.settimeout(0.6)
            try:
                msg = json.loads(c.ws.recv())
            except Exception:
                if time.time() - last_scroll > interval and scrolls < rounds:
                    c.send("Runtime.evaluate", {"expression": "window.scrollTo(0,document.body.scrollHeight)"})
                    scrolls += 1
                    last_scroll = time.time()
                continue
            # 滚动阶段只收集 requestId，响应体稍后统一取。
            # 原因：在事件循环里同步调用 getResponseBody 会阻塞收包，容易漏掉后续分页响应。
            if msg.get("method") == "Network.responseReceived":
                u = (msg["params"].get("response") or {}).get("url", "")
                if "/aweme/v1/web/aweme/post/" in u:
                    rids.append(msg["params"]["requestId"])

        log(f"捕获作品接口响应 {len(rids)} 个，滚动 {scrolls} 轮", cfg, d, "STEP1")
        for rid in rids:
            r = c.wait(c.send("Network.getResponseBody", {"requestId": rid}), 8)
            body = ((r.get("result") or {}).get("body") or "")
            if not body:
                continue
            try:
                data = json.loads(body)
            except Exception:
                continue
            pages.append(data)
            log(f"  分页: {len(data.get('aweme_list') or [])} 条, has_more={data.get('has_more')}", cfg, d, "STEP1")
        c.close()

        works = {}
        for data in pages:
            for a in (data.get("aweme_list") or []):
                aid = str(a.get("aweme_id") or "")
                if not aid:
                    continue
                video = a.get("video") or {}
                play = (video.get("play_addr") or {}).get("url_list") or []
                duration = video.get("duration") or 0
                is_video = bool(duration) and not a.get("images") and not any(".mp3" in u for u in play[:1])
                works[aid] = {
                    "aweme_id": aid,
                    "create_time": a.get("create_time"),
                    "time_str": display_time(a["create_time"]) if a.get("create_time") else "",
                    "desc": a.get("desc") or "",
                    "play_urls": play,
                    "is_video": bool(is_video),
                    "aweme_type": a.get("aweme_type"),
                }
        if not works:
            raise RuntimeError("未抓到任何作品：多半是 Cookie 失效或触发验证码，请重新登录抖音后更新 config.json 的 cookie")

        out = {
            "sec_uid": sec,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pages": len(pages),
            "total": len(works),
            "videos": sum(1 for w in works.values() if w["is_video"]),
            "image_only": sum(1 for w in works.values() if not w["is_video"]),
            "works": sorted(works.values(), key=lambda w: w["create_time"] or 0),
        }
        d["works"].write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"完成：共 {out['total']} 个作品（视频 {out['videos']} / 图文 {out['image_only']}）-> {d['works']}", cfg, d, "STEP1")
        if out["pages"] < 2:
            log("只抓到 1 页：若主页作品数明显更多，请调大 scroll_rounds 或检查是否出现验证码", cfg, d, "WARN")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
