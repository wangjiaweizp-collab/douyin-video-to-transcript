# 贡献指南

感谢你愿意改进这个项目。请先读 [DISCLAIMER.md](DISCLAIMER.md)——
本项目对使用边界有明确要求，贡献的代码也不应突破这些边界。

## 开发准备

```bash
git clone https://github.com/<OWNER>/douyin-video-to-transcript.git
cd douyin-video-to-transcript
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/selftest.py
```

`selftest.py` 完全离线：不联网、不启动浏览器、不读取真实 Cookie。
CI 跑的也是它 + `compileall` + JSON 校验，所以请先确保它在你机器上通过。

## 代码约定

- Python 3.10+，类型注解尽量完整；函数与模块都要有中文或英文 docstring，
  **注释写「为什么」而不是「这行在做什么」**。
- 所有路径必须通过 `lib.work_dirs()` / `Path(__file__)` 推导，
  **禁止写死任何绝对路径、用户名或盘符**。
- 新增配置项必须同步更新 `config.example.json`、`README.md` 的配置表与
  `lib.DEFAULTS`，并给出合理默认值。
- 保持「失败只记录、不自动重试」的行为；任何重试逻辑都要显式可配置。
- 不要引入新的重型依赖；若必须，请说明理由并更新 `requirements.txt` 与 CHANGELOG。
- 不要提交 `config.json`、`workspace/`、任何视频/音频/文字稿产物或 Cookie。

## 提交与 PR

- 提交信息用简短祈使句，例如 `fix: 修正 CDP 响应体解析的空值分支`。
- 一个 PR 只解决一个问题；涉及行为变化时同步更新 `CHANGELOG.md` 与相关文档。
- PR 描述里请写：改了什么、为什么改、怎么验证（贴 `selftest.py` 输出即可）。
- 若改动涉及平台接口，请说明测试日期与环境（Chrome / Python 版本），
  **不要贴任何真实 Cookie、主页链接或转写正文**。

## 明确不接受的贡献

- 绕过验证码、伪造签名、代理池 / IP 轮换、并发暴拉等规避平台风控的能力。
- 抓取非公开内容、评论用户个人信息、自动关注/点赞/评论等写操作。
- 内置账号、共享 Cookie、成品数据集或任何可能侵犯内容权利人利益的内容。
- 把项目改造成托管服务或公开转写内容分发平台。

## 行为准则

参与本项目即表示同意 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
