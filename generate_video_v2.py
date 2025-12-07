import os
import random
import re
import srt
import textwrap

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
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
    text_clips = []

    for sub in subs:
        start = sub.start.total_seconds()
        end = sub.end. total_seconds()
        duration = end - start

        clean_text = clean_subtitle_text(sub.content)
        wrapped = "\n".join(textwrap. wrap(clean_text, width=26))

        txt = TextClip(
            text=wrapped,
            font_size=42,
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(900, None),
        ).with_start(start).with_duration(duration)

        # Position based on text height so bottom stays in frame
        bottom_margin = 200  # pixels from bottom edge (safe zone)
        y_pos = bg.h - txt.h - bottom_margin  # place TOP of clip here

        # Clamp so it never goes above a reasonable point
        y_pos = max(int(bg.h * 0.5), y_pos)

        txt = txt.with_position(("center", y_pos))
        text_clips.append(txt)

    # =========================
    # FINAL COMPOSITION
    # =========================
    final = CompositeVideoClip([bg] + text_clips)
    final = final.with_audio(audio_clip)

    # =========================
    # EXPORT
    # =========================
    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4
    )

    print("Saved:", out_path)
