# Douyin Video → Chronological Transcript

[中文文档（完整版）](README.md) · [Disclaimer](DISCLAIMER.md) · [Architecture](docs/ARCHITECTURE.md)

A **local, portable workflow** that fetches every public post from a Douyin (抖音) creator,
transcribes the speech with `faster-whisper` on your own machine, and merges everything
into one Markdown file ordered by publish time. No third-party transcription API, no
hosted service, no credentials shipped with the code.

> **Please read [DISCLAIMER.md](DISCLAIMER.md) first.** This tool only handles publicly
> available content using your own logged-in session. It does not bypass technical
> protection measures, does not ship accounts or cookies, and is intended for personal
> study only. You are responsible for complying with the platform's terms and local law.

## Why this exists

Third-party downloader CLIs typically return only the **first page** of a creator's
posts: the second `aweme/post` request with `max_cursor` gets an empty shell
`{"status_code":0}` from risk control. This project instead launches an isolated
Chrome with a debugging port, lets the page scroll and paginate **itself** (so the
platform's own signing logic is used), and only listens to the responses the browser
already received. In a real run this recovered all 29 posts (18 + 11) where the CLI
saw 20.

## Quick start

Requirements: Python 3.10+, Chrome, and a valid Cookie from your own logged-in session.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp config.example.json config.json
#   fill in user_url and cookie (see README.md §4)

python scripts/selftest.py        # offline sanity check
python scripts/run_all.py         # fetch → download → transcribe → merge
```

Output lands in `workspace/全部作品时间线文字稿.md` (configurable via `output_name`).
Re-running is safe: existing mp4 / txt files are skipped. Failures are logged to
`workspace/progress.log` and never retried automatically.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1 | `01_fetch_works.py` | `workspace/works.json` — all posts with `create_time`, `desc`, `play_urls` |
| 2 | `02_download.py` | `YYYYMMDD_HHMMSS_<aweme_id>_video.mp4` + `_desc.txt` |
| 3 | `03_transcribe.py` | 16 kHz mono wav → float32 → Whisper → `.txt`/`.json` → merged Markdown |

`run_all.py` chains the three and stops on first failure.

## Key design decisions

- **All paths derived from `__file__` / `config.json`** — no machine-specific absolute paths.
- **UTC+8 explicitly** from the raw `create_time` Unix seconds; never trust a third-party
  formatted `createTime`, and never infer time from `aweme_id >> 32`.
- **No PyAV decoding**: feed a float32 numpy array built from a wav, which avoids the
  `av.open(metadata_errors=...)` incompatibility with newer `av` releases.
- `beam_size=1` + `condition_on_previous_text=False` roughly halves CPU transcription time.
- Image/music posts have no spoken audio; they are labelled as such in the timeline
  instead of being given fabricated transcripts.
- The isolated Chrome uses its own `--user-data-dir`; only the process we started is
  terminated, so your normal browser stays untouched.

## Limitations

- Only public posts returned by the web `aweme/post` endpoint.
- Whisper output is unproofread: homophone errors and mixed Simplified/Traditional
  Chinese are normal; proper nouns may be unrecognisable.
- Platform changes may break any step. Last verified: 2026-11-07 (Chrome 156 / Python 3.13 / Windows).
- No buy/sell signals, market data, or content summarisation — text ordering is done by scripts.

## Contributing & license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Licensed under [MIT](LICENSE), subject to the additional notices in [DISCLAIMER.md](DISCLAIMER.md).
