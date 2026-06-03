#!/usr/bin/env python3
"""Generate DataMagic slide assets via the project image API using gpt-image-2.

This intentionally follows the project API configuration in settings/api_config.py
instead of Codex's built-in image tool or Codex's imagegen CLI.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any
import argparse

import requests
from PIL import Image, ImageOps

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from settings import api_config


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "slides" / "datamagic-system-deck" / "assets"
RAW_DIR = OUT_DIR / "gpt2_raw"

MODEL = "gpt-image-2"
API_SIZE = "1536x1024"
API_QUALITY = "medium"
DEFAULT_FINAL_SIZE = (1280, 800)

PROMPTS = {
    "motivation-panel-1-gpt2.png": (
        DEFAULT_FINAL_SIZE,
        "motivation-panel-1-gpt2.png",
        "Dark navy technology illustration for a DataMagic presentation card. "
        "Concept: static dashboard charts are useful, but they do not automatically become a narrative. "
        "Show disconnected analytical panels, tables, chart surfaces, and data widgets floating above a subtle grid floor. "
        "Polished glassmorphism, luminous blue and cyan accents, subtle violet depth lighting. "
        "Clean cinematic slide asset. Abstract UI and chart-like marks are allowed, but no readable words, no logos, no watermark.",
    ),
    "motivation-panel-2-gpt2.png": (
        DEFAULT_FINAL_SIZE,
        "motivation-panel-2-gpt2.png",
        "Dark navy technology illustration for a DataMagic presentation card. "
        "Concept: traditional data video authoring requires prepared charts, scripts, narration, animation, and timeline work. "
        "Show a glowing video editing timeline with chart thumbnails, audio waveform shapes, animation keyframe dots, "
        "and curved orchestration paths. Polished glassmorphism, luminous blue and cyan accents, subtle violet depth lighting. "
        "Clean cinematic slide asset. Abstract UI and chart-like marks are allowed, but no readable words, no logos, no watermark.",
    ),
    "motivation-panel-3-gpt2.png": (
        DEFAULT_FINAL_SIZE,
        "motivation-panel-3-gpt2.png",
        "Dark navy technology illustration for a DataMagic presentation card. "
        "Concept: generated data videos need clear data lineage back to source tables. "
        "Show video frames and chart cards emerging from a central computational module, with abstract source-data paths "
        "and structured connection lines. Polished glassmorphism, luminous blue and cyan accents, subtle violet depth lighting. "
        "Clean cinematic slide asset. Abstract UI and chart-like marks are allowed, but no readable words, no logos, no watermark.",
    ),
    "positioning-structure-blueprint-gpt2.png": (
        (1600, 900),
        "positioning-structure-blueprint-gpt2.png",
        "Dark navy cinematic concept illustration for a DataMagic presentation section. "
        "Concept: a system transforms raw tabular data into candidate analytical insights, then organizes them into a structured storyboard blueprint before rendering a narrated insight video. "
        "Composition: left side glowing spreadsheet/data-source panels; middle floating chart candidates and insight cards; right side a video storyboard timeline with chart frames and audio waveform; a luminous structured document/blueprint layer subtly connects everything. "
        "Use polished glassmorphism, deep navy background, blue/cyan light paths, subtle violet highlights, grid depth, premium data visualization interface aesthetics. "
        "Important: no readable words, no numbers, no logos, no watermark, no UI text. Leave comfortable empty margins for HTML labels to be overlaid.",
    ),
}


def center_crop_to_aspect(img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    target_w, target_h = target_size
    width, height = img.size
    target_ratio = target_w / target_h
    current_ratio = width / height

    if current_ratio > target_ratio:
        crop_w = int(height * target_ratio)
        left = max(0, (width - crop_w) // 2)
        img = img.crop((left, 0, left + crop_w, height))
    elif current_ratio < target_ratio:
        crop_h = int(width / target_ratio)
        top = max(0, (height - crop_h) // 2)
        img = img.crop((0, top, width, top + crop_h))

    return img.resize(target_size, Image.Resampling.LANCZOS)


def decode_image(item: dict[str, Any]) -> bytes:
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        response = requests.get(item["url"], timeout=90)
        response.raise_for_status()
        return response.content
    raise RuntimeError("Image API response did not include b64_json or url")


def generate_one(filename: str, prompt: str, final_size: tuple[int, int]) -> None:
    response = requests.post(
        f"{api_config.API_BASE}/v1/images/generations",
        headers={
            "Authorization": f"Bearer {api_config.API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "prompt": prompt,
            "n": 1,
            "size": API_SIZE,
            "quality": API_QUALITY,
        },
        timeout=180,
    )

    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")

    data = response.json().get("data") or []
    if not data:
        raise RuntimeError("Image API returned empty data")

    image_bytes = decode_image(data[0])
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / filename
    raw_path.write_bytes(image_bytes)

    with Image.open(BytesIO(image_bytes)) as img:
        img.load()
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = center_crop_to_aspect(img, final_size)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / filename
        img.save(out_path, optimize=True)

    print(f"saved {out_path.relative_to(ROOT)} ({final_size[0]}x{final_size[1]})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=sorted(PROMPTS), help="Generate only the named output file. Can be passed multiple times.")
    args = parser.parse_args()
    selected = args.only or list(PROMPTS)

    print(f"API_BASE={api_config.API_BASE}")
    print(f"MODEL={MODEL} API_SIZE={API_SIZE}")
    for key in selected:
        final_size, filename, prompt = PROMPTS[key]
        generate_one(filename, prompt, final_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
