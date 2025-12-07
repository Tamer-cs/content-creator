import os
import random
import re
import srt
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

# =========================
# FOLDER CONFIG
# =========================
BG_DIR = "video-clips"
AUDIO_DIR = "audio"
SUB_DIR = "subtitles"
OUT_DIR = "output"

os.makedirs(OUT_DIR, exist_ok=True)

# =========================
# LOAD BACKGROUNDS
# =========================
bgs = [
    os.path.join(BG_DIR, f)
    for f in os.listdir(BG_DIR)
    if f.lower().endswith((".mp4", ".mov"))
]

if not bgs:
    raise RuntimeError("No background videos found.")

# =========================
# SANITIZER
# =========================


def clean_subtitle_text(txt):
    txt = re.sub(r"<.*?>", "", txt)
    return txt.strip()

# =========================
# LOAD SRT
# =========================


def load_subtitles(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(srt.parse(f.read()))

# =========================
# FONT HELPERS
# =========================


def load_font(font_size: int):
    candidates = [
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_subtitle_image(
    text: str,
    wrap_width: int = 26,
    font_size: int = 42,
    stroke_width: int = 2,
    padding: int = 28,
    extra_bottom: int = 12,
    box_opacity: float = 0.55,
):
    font = load_font(font_size)
    wrapped = "\n".join(textwrap.wrap(text, width=wrap_width)) or " "

    # Measure text
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(dummy)
    bbox = d.multiline_textbbox(
        (0, 0), wrapped, font=font, stroke_width=stroke_width, spacing=4)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    box_w = text_w + 2 * padding
    box_h = text_h + 2 * padding + extra_bottom  # extra room for descenders

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Background box with opacity
    alpha = int(255 * box_opacity)
    d.rectangle([0, 0, box_w, box_h], fill=(0, 0, 0, alpha))

    # Draw text, lifted upward a bit to avoid bottom clipping
    text_x = (box_w - text_w) // 2
    text_y = padding - 4  # small upward bias
    d.multiline_text(
        (text_x, text_y),
        wrapped,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, 255),
        spacing=4,
        align="center",
    )
    return np.array(img)


# =========================
# MAIN LOOP
# =========================
for f in os.listdir(AUDIO_DIR):
    if not f.endswith(".mp3"):
        continue

    base = f.replace(".mp3", "")
    audio_path = os.path.join(AUDIO_DIR, f)
    srt_path = os.path.join(SUB_DIR, base + ".srt")
    out_path = os.path.join(OUT_DIR, base + ".mp4")

    if not os.path.exists(srt_path):
        print("Skipping (no subtitles):", base)
        continue

    print("Rendering:", base)

    # =========================
    # LOAD AUDIO
    # =========================
    audio_clip = AudioFileClip(audio_path)
    target_duration = audio_clip.duration

    # =========================
    # LOAD + LOOP BACKGROUND
    # =========================
    bg_raw = VideoFileClip(random.choice(bgs))

    if bg_raw.duration < target_duration:
        loops = int(target_duration // bg_raw.duration) + 1
        bg_looped = concatenate_videoclips([bg_raw] * loops)
        bg = bg_looped.subclipped(0, target_duration)
    else:
        bg = bg_raw.subclipped(0, target_duration)

    # =========================
    # FORCE 9:16
    # =========================
    bg = bg.resized(height=1920)

    if bg.w > 1080:
        bg = bg.cropped(x_center=bg.w / 2, width=1080)
    else:
        bg = bg.resized(width=1080)

    bg = bg.with_duration(target_duration)

    # =========================
    # SUBTITLES — SAFE, UNCROPPED
    # =========================
    subs = load_subtitles(srt_path)
    subtitle_layers = []

    bottom_safe_margin = 320   # generous bottom clearance
    min_top_anchor = int(bg.h * 0.56)
    box_opacity = 0.55
    wrap_width = 26
    font_size = 42
    stroke_width = 2
    padding = 28
    extra_bottom = 14  # extra baseline room

    for sub in subs:
        start = sub.start.total_seconds()
        end = sub.end.total_seconds()
        duration = end - start

        clean_text = clean_subtitle_text(sub.content)
        img_arr = render_subtitle_image(
            clean_text,
            wrap_width=wrap_width,
            font_size=font_size,
            stroke_width=stroke_width,
            padding=padding,
            extra_bottom=extra_bottom,
            box_opacity=box_opacity,
        )

        subtitle = ImageClip(img_arr)
        subtitle = subtitle.with_duration(duration).with_start(start)

        # Position calculation
        box_h = subtitle.h
        y_pos = bg.h - box_h - bottom_safe_margin
        y_pos = max(min_top_anchor, y_pos)

        subtitle = subtitle.with_position(("center", y_pos))
        subtitle_layers.append(subtitle)

    # =========================
    # FINAL COMPOSITION
    # =========================
    final = CompositeVideoClip([bg] + subtitle_layers)
    final = final.with_audio(audio_clip)

    # =========================
    # EXPORT
    # =========================
    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
    )

    print("Saved:", out_path)
