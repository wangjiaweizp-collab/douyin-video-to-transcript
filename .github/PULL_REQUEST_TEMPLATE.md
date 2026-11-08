## 改动说明

<!-- 一句话说明这个 PR 解决了什么，以及为什么需要它 -->

## 关联 Issue

<!-- Closes #123 -->

## 改动类型

- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档 / 注释
- [ ] 重构（不改变行为）
- [ ] CI / 工程配置
- [ ] 依赖更新

## 验证方式

<!-- 请贴出 `python scripts/selftest.py` 的输出；如涉及平台接口，注明测试日期与 Chrome / Python 版本 -->

```text

```

## 检查清单

- [ ] 没有提交 `config.json`、`workspace/`、Cookie、视频/音频/文字稿产物
- [ ] 所有路径仍从 `__file__` / `config.json` 推导，没有写死绝对路径
- [ ] 新增配置项已同步 `config.example.json`、`lib.DEFAULTS` 与 README 配置表
- [ ] 保持「失败只记录、不自动重试」的行为
- [ ] 行为变化已写入 `CHANGELOG.md`，相关文档已更新
- [ ] 改动没有绕过平台风控、没有获取非公开内容（见 DISCLAIMER.md）

> 请勿在 PR 描述、截图或日志里粘贴真实 Cookie、主页链接或转写正文。
