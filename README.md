# 抖音博主视频 → 全量时间线文字稿

[English](README.en.md) · [架构说明](docs/ARCHITECTURE.md) · [故障排查](docs/TROUBLESHOOTING.md) · [免责声明](DISCLAIMER.md)

[![CI](https://github.com/wangjiaweizp-collab/douyin-video-to-transcript/actions/workflows/ci.yml/badge.svg)](https://github.com/wangjiaweizp-collab/douyin-video-to-transcript/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

把某个抖音博主主页的**全部公开作品**按发布时间抓下来，视频语音用本地
`faster-whisper` 转文字，合并成一份按时间排序的 Markdown 文字稿。
全程本机运行，不依赖第三方转写服务，不内置任何账号或凭据。

> ⚠️ **使用前请先读 [DISCLAIMER.md](DISCLAIMER.md)**：只处理公开内容、只使用你自己的登录态、
> 不绕过技术保护措施、不用于商业转售或公开再分发。项目于 **2026-11-07** 在
> Chrome 156 / Python 3.13 / Windows 实测通过，平台接口变化后不保证继续可用。
> 转写结果**未做人工校对**，存在同音错字与繁简混排；图文/配乐作品没有口播音频，
> 只会如实标注，**不会伪造转写内容**。

---

## 目录

- [为什么需要这个工具](#为什么需要这个工具)
- [特性](#特性)
- [快速开始](#快速开始)
- [两个必填输入](#两个必填输入)
- [配置参考](#配置参考)
- [三步流程与输出](#三步流程与输出)
- [关键设计决策](#关键设计决策)
- [开发与自检](#开发与自检)
- [从其他电脑发布](#从其他电脑发布)
- [常见问题](#常见问题)
- [已知局限](#已知局限)
- [贡献与许可证](#贡献与许可证)

---

## 为什么需要这个工具

第三方下载器 CLI 通常只返回**第一页**作品：带 `max_cursor` 的第二页
`aweme/v1/web/aweme/post/` 请求会被风控返回空壳 `{"status_code":0}`，
于是 `has_more=1` 却拿不到后续数据。一次真实任务里，CLI 只看到 20 条，
而博主主页实际有 29 个作品（还漏掉了最新的 4 条）。

本项目不自己复刻签名，而是启动一个带调试端口的独立 Chrome，**让页面自己滚动分页**
（签名由页面生成），我们只监听浏览器已经收到的响应。实测两页 18 + 11 = 29 条，
与主页数量一致。详见 [架构说明](docs/ARCHITECTURE.md)。

## 特性

| | |
|---|---|
| 🔍 全量抓取 | 浏览器自分页 + 按 `aweme_id` 去重，不受单页 20 条限制 |
| 🕒 时间准确 | 用接口原始 `create_time` 显式按 UTC+8 命名，不依赖系统时区 |
| 🗣 本地转写 | faster-whisper medium / CPU int8，不上传任何音频 |
| 🖼 诚实标注 | 图文/配乐作品保留文案并标注「无口播音频」，不制造假转写 |
| ♻️ 断点续跑 | 已有 mp4 / txt 自动跳过，失败只记录、不自动重试 |
| 🧳 可移植 | 所有路径从 `__file__` 与配置推导，无机器专用绝对路径 |
| 🔒 凭据安全 | `config.json` / `workspace/` 已进 `.gitignore`，CI 不访问任何平台 |

## 快速开始

```bash
git clone https://github.com/wangjiaweizp-collab/douyin-video-to-transcript.git
cd douyin-video-to-transcript

python -m venv .venv
.venv\Scripts\activate                 # Windows；macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp config.example.json config.json     # 填写 user_url 与 cookie
python scripts/selftest.py             # 离线自检，应先全部 PASS
python scripts/run_all.py              # 一键跑完三步
```

分步执行便于排查：

```bash
python scripts/01_fetch_works.py       # 抓全量作品元数据
python scripts/02_download.py          # 下载 mp4 + 文案
python scripts/03_transcribe.py        # 转写 + 合并 Markdown
```

| 环境要求 | 说明 |
|---|---|
| Python 3.10+ | 建议 venv 隔离 |
| Chrome 任意较新版本 | 自动探测路径；找不到就填 `chrome_path` |
| `faster-whisper` 等 | `pip install -r requirements.txt` |
| ffmpeg | 不必系统安装，`imageio-ffmpeg` 自带；已装则优先用系统的 |
| Whisper 模型 | 默认 `medium`，首次自动下载约 1.5GB；可填 `model_path` 走本地快照离线运行 |

## 两个必填输入

**`user_url`** — 在抖音网页版点博主头像进主页，复制地址栏
`https://www.douyin.com/user/MS4wLjABAAAA...`（`?from_tab_name=main` 可去掉）。

**`cookie`** — Chrome 保持登录 → `F12` → **Network** → 刷新 → 任取一个 `douyin.com` 请求
→ Request Headers → 复制 **`Cookie:` 整行**（不是 `Set-Cookie`）粘进 `config.json`。

也可用环境变量，完全不落盘：`DY_USER_URL=... DY_COOKIE=... python scripts/run_all.py`

> ⚠️ 不要用 `document.cookie`：登录态是 HttpOnly，JS 读不到。
> ⚠️ Cookie 有时效，失效时典型表现是页面验证码、接口空壳、`works.json` 数量偏小。
> ⚠️ **永远不要**把 Cookie 提交到仓库、贴进 Issue 或写进 CI。

## 配置参考

| 键 | 默认 | 说明 |
|---|---|---|
| `user_url` | 空（必填） | 博主主页 `/user/` 链接 |
| `cookie` | 空（必填） | 本人登录态 Cookie 整行 |
| `chrome_path` | 自动探测 | Chrome 可执行文件完整路径 |
| `cdp_port` | `9224` | 调试端口，被占用时改这里 |
| `work_dir` | `./workspace` | 运行时产物目录 |
| `model` | `medium` | Whisper 模型名，可改 `small` / `base` 提速 |
| `model_path` | 空 | 本地模型快照目录（含 `model.bin`），填了就离线 |
| `output_name` | `全部作品时间线文字稿.md` | 最终 Markdown 文件名 |
| `scroll_rounds` | `12` | 滚动加载轮数，作品多就调大 |
| `scroll_interval_sec` | `3` | 每轮间隔，避免过快触发风控 |
| `headless` | `false` | 无头模式更容易被风控，建议保持 `false` |

## 三步流程与输出

| 步骤 | 脚本 | 主要产物 |
|---|---|---|
| 1 | `01_fetch_works.py` | `workspace/works.json`（`create_time` / `desc` / `play_urls` / `is_video`） |
| 2 | `02_download.py` | `workspace/videos/YYYYMMDD_HHMMSS_<aweme_id>_video.mp4` 与 `_desc.txt` |
| 3 | `03_transcribe.py` | `.wav` → `03_transcripts/*.txt` + `*.json` → 最终 Markdown |

`run_all.py` 串行调用，失败即停。文件命名前缀 `YYYYMMDD_HHMMSS` 就是权威发布时间，
也是合并时的排序键；同一 stem 贯穿四个阶段，因此断点续跑只需判断目标文件是否存在。
`workspace/progress.log` 记录每阶段状态、下载数量、每 5 个文件的转写进度与失败清单。

文字稿每节带发布时间、原文案与类型标注，按时间从早到晚排列。

## 关键设计决策

完整版见 [架构说明](docs/ARCHITECTURE.md) 与 [故障排查](docs/TROUBLESHOOTING.md)。

| 坑 | 本项目的做法 |
|---|---|
| 下载器只翻一页 | CDP 让浏览器自己分页，只监听响应，不复刻签名 |
| Chrome App-Bound 加密 | 不读本地 Cookie 库，用 `Network.setCookies` 注入你提供的 Cookie |
| DevTools 键盘焦点 / self-XSS | 全程 CDP 协议，不模拟键盘、不点 UI |
| 时间换算错乱 | 只用原始 `create_time` 显式 UTC+8；不用 `aweme_id >> 32`，不采信第三方 `createTime` |
| `av` 与 faster-whisper 冲突 | ffmpeg → wav → `wave` 读成 float32 数组喂模型，不走 PyAV |
| `WhisperModel` 参数错位 | `language` / `vad_filter` 等只放 `transcribe()`，不进构造函数 |
| CPU 转写慢 | `beam_size=1` + `condition_on_previous_text=False`，实测约提速 2 倍 |
| 误杀用户浏览器 | 独立 `--user-data-dir`，只 `terminate()` 自己启动的进程 |

## 开发与自检

```bash
python scripts/selftest.py     # 离线：语法、配置、路径、时区、命名、敏感文件
python -m compileall -q scripts
ruff check scripts             # 可选，配置见 pyproject.toml
```

CI（[`.github/workflows/ci.yml`](.github/workflows/ci.yml)）在 Python 3.10–3.13 上跑同样的自检，
另有一个任务检查**没有敏感文件被提交**、以及文档相对链接没有断链。
CI 不安装 `faster-whisper`、不启动浏览器、不访问任何第三方平台。

工程要素齐备：[LICENSE](LICENSE) · [DISCLAIMER](DISCLAIMER.md) · [SECURITY](SECURITY.md) ·
[CONTRIBUTING](CONTRIBUTING.md) · [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) ·
[CHANGELOG](CHANGELOG.md) · [Issue / PR 模板](.github/ISSUE_TEMPLATE) ·
[Dependabot](.github/dependabot.yml)。

## 从其他电脑发布

本仓库首次发布用的是 GitHub 连接器；若你在别的环境想复现发布流程，可用内置脚本：

```bash
export GITHUB_TOKEN=ghp_xxx    # Windows: set GITHUB_TOKEN=ghp_xxx
python scripts/publish_github.py
```

脚本会读取 token → `GET /user` → 创建仓库（已存在则沿用）→ 本地提交 →
一次性推送 → 把 `origin` 设为**不含凭据**的干净地址。
token 不写文件、不打印、不进 remote；最小权限为 `repo`。发布完请撤销该 PAT。
详见 [scripts/publish_github.py](scripts/publish_github.py) 顶部注释。

## 常见问题

- **只抓到 20 条 / 1 页？** Cookie 失效或滚动没触发分页；重新登录并调大 `scroll_rounds`。
- **下载全失败？** 播放直链有时效；重跑 `01` 刷新 `works.json` 再跑 `02`。
- **换电脑要改代码吗？** 不用，只需装依赖 + 填两项配置。
- **能抓喜欢列表 / 私密作品吗？** 不能，只处理公开主页作品。

更多症状 → 原因 → 解法见 [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

## 已知局限

- 只覆盖网页端 `aweme/post` 能返回的公开作品；仅 App 可见内容抓不到。
- 转写质量受音质、方言、背景音乐影响；繁体输出与专有名词失真属正常现象。
- 本项目只做「视频 → 文字稿」，不含行情字段、内容总结或投资信号。
- 平台风控变化可能导致任一环节失效，需按架构文档重新定位接口。

## 贡献与许可证

欢迎改进，请先读 [CONTRIBUTING.md](CONTRIBUTING.md)——尤其**不要提交 Cookie 或运行时产物**，
以及明确不接受的贡献类型（绕过风控、并发暴拉、非公开内容等）。

代码采用 [MIT](LICENSE) 许可，并受 [DISCLAIMER.md](DISCLAIMER.md) 中的使用边界约束。
