# -*- coding: utf-8 -*-
"""步骤 3：ffmpeg 转 16kHz 单声道 wav → faster-whisper 转写 → 按时间合并 Markdown。

两个已验证的坑（勿改回去）：
1. WhisperModel 构造函数不接受 language / vad_filter，这两个参数只能放 transcribe()。
2. 某些 av 版本与 faster-whisper 冲突（av.open(metadata_errors=...) 已移除）。
   这里不走 PyAV 解码，而是用 wave 读 PCM 转 float32 数组直接喂模型。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import find_ffmpeg, load_config, log, work_dirs


def wav_to_float32(path: Path):
    import numpy as np
    with wave.open(str(path), "rb") as w:
        pcm = w.readframes(w.getnframes())
    arr = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    return arr


def sort_key(p: Path):
    """文件名前缀 YYYYMMDD_HHMMSS 优先，其余退回 mtime。"""
    m = re.match(r"^(\d{8})_(\d{6})_", p.stem)
    if m:
        return (0, m.group(1) + m.group(2))
    return (1, str(int(p.stat().st_mtime)).zfill(20))


def main():
    cfg = load_config()
    d = work_dirs(cfg)
    ffmpeg = find_ffmpeg()
    mp4s = sorted(d["videos"].glob("*.mp4"))
    if not mp4s:
        raise RuntimeError("videos/ 下没有 mp4，请先运行 02_download.py")

    # --- 3a 音频提取 ---
    wavs = []
    for mp4 in mp4s:
        wav = mp4.with_suffix(".wav")
        if not (wav.exists() and wav.stat().st_size > 1000):
            r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(mp4),
                                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
                               capture_output=True, text=True, timeout=900)
            if r.returncode != 0 or not wav.exists():
                log(f"FAIL {mp4.name} | ffmpeg: {(r.stderr or '')[:150]}", cfg, d, "ERROR")
                continue
        wavs.append(wav)
    log(f"音频提取完成（成功 {len(wavs)}/{len(mp4s)}）", cfg, d, "STEP3")

    # --- 3b 转写 ---
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        raise RuntimeError("未安装 faster-whisper：pip install -r requirements.txt") from e
    model_ref = cfg.get("model_path") or cfg.get("model") or "medium"
    log(f"加载 Whisper 模型: {model_ref} (CPU / int8)", cfg, d, "STEP3")
    model = WhisperModel(model_ref, device="cpu", compute_type="int8")

    done = 0
    for idx, wav in enumerate(sorted(wavs, key=sort_key), 1):
        txt = d["transcripts"] / (wav.stem + ".txt")
        js = d["transcripts"] / (wav.stem + ".json")
        if txt.exists() and txt.stat().st_size > 0:
            done += 1
        else:
            try:
                # 不把媒体路径交给 whisper：新版 av 移除了 av.open(metadata_errors=...)，
                # faster-whisper 自行解码媒体会直接抛错。改用 numpy float32 数组输入。
                audio = wav_to_float32(wav)
                segs, _info = model.transcribe(
                    audio, beam_size=1, language="zh", vad_filter=True,
                    condition_on_previous_text=False,
                )
                items = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text} for s in segs]
                js.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
                txt.write_text("\n".join(x["text"].strip() for x in items), encoding="utf-8")
                done += 1
            except Exception as e:
                log(f"FAIL {wav.name} | 转写异常: {str(e)[:180]}", cfg, d, "ERROR")
        if idx % 5 == 0 or idx == len(wavs):
            log(f"转写进度: {idx}/{len(wavs)}（成功 {done}）", cfg, d, "STEP3")
    log(f"转写完成 {done}/{len(wavs)}", cfg, d, "STEP3")

    # --- 3c 合并（含无音频图文作品）---
    entries = []
    for desc in sorted(d["videos"].glob("*_desc.txt"), key=sort_key):
        stem = desc.stem.replace("_desc", "_video")
        txt = d["transcripts"] / (stem + ".txt")
        mp4 = d["videos"] / (stem + ".mp4")
        m = re.match(r"^(\d{8})_(\d{6})_", desc.stem)
        date_str = (f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]} "
                    f"{m.group(2)[:2]}:{m.group(2)[2:4]}") if m else ""
        desc_text = desc.read_text(encoding="utf-8").strip()
        if txt.exists():
            body = txt.read_text(encoding="utf-8").strip()
            kind = "视频语音转写"
        elif mp4.exists():
            body = "（转写未完成或失败，详见 progress.log）"
            kind = "视频（转写缺失）"
        else:
            body = desc_text or "（无文案）"
            kind = "图文/配乐作品，无口播音频，未做转写"
        entries.append((sort_key(desc), desc.stem, date_str, kind, body, desc_text[:100]))
    entries.sort(key=lambda x: x[0])
    n_voice = sum(1 for e in entries if e[3] == "视频语音转写")
    n_missing = sum(1 for e in entries if e[3] == "视频（转写缺失）")
    n_image = len(entries) - n_voice - n_missing

    lines = [
        "# 抖音博主 · 全部作品时间线文字稿", "",
        f"- 作品数：{len(entries)}（语音转写 {n_voice} 个，图文无音频 {n_image} 个，转写缺失 {n_missing} 个）",
        "- 排序规则：按作品发布时间（文件名 YYYYMMDD_HHMMSS 前缀，UTC+8）升序",
        "- 说明：语音部分由 faster-whisper 自动转写，未做人工校对或内容总结；图文作品仅保留原文案。",
        "", "---", "",
    ]
    for i, (_k, stem, date_str, kind, body, desc) in enumerate(entries, 1):
        meta = []
        if date_str:
            meta.append(f"发布时间：{date_str}")
        if desc:
            meta.append(f"作品文案：{desc}")
        meta.append(f"类型：{kind}")
        lines += [f"## {i:03d}. {stem}", "", *meta, "", body, "", "---", ""]
    d["output"].write_text("\n".join(lines), encoding="utf-8")
    log(f"最终文字稿: {d['output']}（{len(entries)} 个作品, {d['output'].stat().st_size} 字节）", cfg, d, "STEP3")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
