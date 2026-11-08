# 故障排查

> 先看 `workspace/progress.log`，脚本把每一步状态和失败摘要都写在那里。
> 全部按「失败不自动重试」设计：定位原因后手动重跑对应步骤即可。

## 快速定位

| 现象 | 最可能的原因 | 处理 |
|---|---|---|
| `未找到 Chrome` | 自动探测路径没覆盖 | `config.json` 填 `chrome_path` 完整路径 |
| `Chrome 调试端口未就绪` | 端口被占用 / 上次实例残留 | 换 `cdp_port`，或结束占用该端口的进程 |
| `未抓到任何作品` | Cookie 失效、页面出验证码 | 重新登录抖音，复制新的 Cookie 整行 |
| 只抓到 1 页 / 20 条 | 滚动没触发分页，或接口返回空壳 | 调大 `scroll_rounds` / `scroll_interval_sec`；确认 Cookie 有效 |
| 下载全部失败 | 播放直链过期 | 重跑 `01` 刷新 `works.json`，再跑 `02` |
| `ModuleNotFoundError: faster_whisper` | 依赖未装 | `pip install -r requirements.txt` |
| `av.open(metadata_errors=...)` 报错 | 用了 whisper 自带解码路径 | 确认走的是本仓库 `03_transcribe.py`（wave → float32） |
| `WhisperModel(...) TypeError` | 把 `language` / `vad_filter` 传进构造函数 | 这两个参数必须放 `transcribe()` |
| 转写极慢 | `beam_size=5` 或模型太大 | 保持 `beam_size=1`；或 `model` 改 `small` / `base` |
| 首次运行卡在模型下载 | faster-whisper 从 Hugging Face 拉 ~1.5GB | 预下载快照并填 `model_path` 走离线 |
| 文字稿里出现「无口播音频」 | 图文/配乐作品 | 预期行为，不是错误 |
| 文件名时间看着差 8 小时 | 拿第三方 `createTime` 对比了 | 以原始 `create_time` 按 UTC+8 为准 |

## 分步诊断

### 1. 先跑离线自检

```bash
python scripts/selftest.py
```

它不联网、不启动浏览器，验证配置加载、时区换算、`sec_uid` 解析、
Cookie 解析、文件名正则与排序键。CI 也跑同一份自检。

### 2. 确认 Cookie 是否有效

在 Chrome 里打开目标主页，能正常看到作品列表说明会话有效。
复制 Cookie 时注意：

- 取 **Request Headers → `Cookie:` 整行**，不是 `Set-Cookie`；
- 不要用控制台 `document.cookie`，登录态是 HttpOnly，JS 读不到；
- 不要带换行；粘贴到 JSON 里时引号需正确转义（建议用编辑器而非记事本）。

失效的典型信号：页面验证码、接口 `{"status_code":0}` 空壳、
`works.json` 里 `total` 远小于主页显示数。

### 3. 判断是「翻页问题」还是「下载问题」

```bash
python scripts/01_fetch_works.py
python -c "import json;d=json.load(open('workspace/works.json',encoding='utf-8'));print(d['pages'],d['total'],d['videos'],d['image_only'])"
```

- `pages=1` 且 `total` 偏小 → 翻页没触发，回到上一步检查 Cookie 与滚动参数；
- `total` 正确但 mp4 数量为 0 → 是下载问题，检查 `play_urls` 是否过期、网络能否访问 CDN。

### 4. 单步重跑

```bash
python scripts/01_fetch_works.py   # 只刷新元数据
python scripts/02_download.py      # 只补下载（跳过已有）
python scripts/03_transcribe.py    # 只补转写 + 重新合并
```

合并阶段每次都会重新生成 Markdown，所以补完任意一步后只需重跑 `03` 即可得到完整文稿。

## 平台无关问题

### Windows

- `pdl` 之类 npm 全局命令是 `.cmd` shim，Python `subprocess` 直接调用会报 `WinError 2`。
  本仓库不依赖它；若自行接入，请显式用 `node node_modules/polydl/dist/cli/index.js`。
- `Av` / `faster-whisper` 在部分 Python 3.13 环境需要较新的 wheel；
  若安装失败，改用 Python 3.11 建 venv 通常最省事。
- 路径含中文和空格是支持的（所有路径都用 `Path` 与参数列表传递，未拼 shell 字符串）。

### macOS / Linux

- Chrome 路径自动探测覆盖 `/Applications/Google Chrome.app/...` 与常见 `/usr/bin/*`。
- 无头模式可在 `config.json` 设 `headless: true`，但无头更容易触发页面风控，
  建议先在有头环境跑通。
- `imageio-ffmpeg` 提供内置 ffmpeg；若系统已有 ffmpeg 则优先使用系统版本。

## 仍然失败时

请带着以下信息新建 Issue（**不要贴 Cookie、真实主页链接或转写正文**）：

1. 操作系统、Python 版本、Chrome 版本；
2. `python scripts/selftest.py` 的完整输出；
3. `workspace/progress.log` 最后 20 行（可脱敏）；
4. `works.json` 里的 `pages / total / videos / image_only` 四个数字；
5. 你期望的结果与实际结果的差别。
