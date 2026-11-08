# Security Policy

## 支持的版本

| 版本 | 支持 |
|---|---|
| 1.0.x | ✅ |
| < 1.0 | ❌ |

## 最重要的一条：不要把凭据提交上来

`config.json`、`workspace/`、`.env` 及所有 `cookie*.txt` 均已被 `.gitignore` 排除。
提交 PR 前请确认 `git status` 里没有这些东西。若不小心提交过 Cookie：

1. **立刻在对应平台退出登录 / 刷新会话**，使旧 Cookie 失效；
2. 从工作树删除文件；
3. 联系维护者清理历史（必要时重建仓库），不要只做一次普通删除提交。

本项目不需要、也不会收集任何账号、token 或个人数据。CI 只做静态检查与离线自检，
不会访问任何第三方平台。

## 报告漏洞

请**不要**用公开 Issue 报告安全问题。使用仓库的
**Security → Report a vulnerability**（GitHub Security Advisories）私下提交，
或在新 Issue 中仅说明「有安全问题，请私下联系」，不要贴出细节。

请在报告中包含：影响版本、复现步骤、影响范围、建议修复（如有）。
我们会在 7 天内确认收到，并在修复后同步发布说明。

## 依赖安全

- 依赖锁定见 `requirements.txt`；Dependabot 每周检查 pip 与 GitHub Actions 更新。
- 语音模型由 `faster-whisper` 从 Hugging Face 下载；需要完全离线时，
  请在 `config.json` 填写本地快照目录 `model_path`。
- 本项目不会执行从网络下载的脚本或模型权重以外的内容；`works.json` 中的
  `play_urls` 只作为下载目标，不参与任何命令拼接。
