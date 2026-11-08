# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与
[语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-11-08

首个公开版本。从一次真实任务中提炼：某创作者主页 29 个作品被完整抓取、
23 段语音本地转写、按发布时间合并为 29 节 Markdown 时间线。

### Added

- `scripts/01_fetch_works.py`：基于 Chrome DevTools Protocol 的全量作品列表抓取。
  让浏览器自己滚动分页，监听 `aweme/v1/web/aweme/post/` 响应并汇总，
  解决第三方下载器只返回第一页（带 `max_cursor` 的第二页被风控返回空壳）的问题。
- `scripts/02_download.py`：按 `create_time` 生成 `YYYYMMDD_HHMMSS_<aweme_id>` 文件名，
  从 `play_addr` 直链下载 mp4，并落盘每个作品的文案。
- `scripts/03_transcribe.py`：ffmpeg → 16 kHz 单声道 wav → float32 数组 →
  faster-whisper → 分段 JSON/TXT → 按时间线合并 Markdown。
- `scripts/run_all.py`：三步串行编排，失败即停、不自动重试。
- `scripts/lib.py`：配置加载、路径推导、UTC+8 时间换算、Cookie 解析、Chrome/ffmpeg 定位。
- `scripts/selftest.py`：离线自检（不联网、不启动浏览器），供 CI 与本地快速验证。
- `scripts/publish_github.py`：可选的 GitHub 一键发布脚本。
- 完整文档：README（中/英）、架构说明、故障排查、贡献指南、行为准则、安全政策、免责声明。
- GitHub 工程要素：MIT LICENSE、`.gitignore`、`.gitattributes`、`pyproject.toml`、
  CI 工作流、Issue/PR 模板、Dependabot 配置。

### Design decisions

- 所有路径从 `__file__` 与 `config.json` 推导，不含任何机器专用绝对路径。
- 时间统一用接口原始 `create_time` 显式按 UTC+8 转换，不依赖系统时区，
  不用 `aweme_id >> 32` 反推，也不采信第三方库格式化后的结果。
- 不让 Whisper 自行解码媒体：用 `wave` 读 PCM 转 float32 数组，
  绕开 `av` 新版本移除 `av.open(metadata_errors=...)` 导致的兼容故障。
- `beam_size=1` + `condition_on_previous_text=False`，在 CPU 上把 medium 模型
  转写从约 1.5× 实时压到约 0.6× 实时。
- 图文/配乐作品（`duration=0`、`images` 非空、播放地址指向音频）在时间线里
  如实标注「无口播音频」，不伪造转写内容。
- 断点续跑：已存在的 mp4 / txt 自动跳过；失败项只写入 `progress.log`。

### Known limitations

- 仅覆盖网页端公开作品接口能返回的内容。
- 转写未做人工校对，存在同音错字与繁简混排；个股/专有名词可能失真。
- 平台风控变化可能导致任一环节失效。
- 不含涨停/连板等行情字段，本项目只负责「视频 → 文字稿」。
