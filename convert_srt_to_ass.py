import pysubs2
import os

SRC = "subtitles"
DST = "subtitles_ass"

os.makedirs(DST, exist_ok=True)

for f in os.listdir(SRC):
    if f.endswith(".srt"):
        subs = pysubs2.load(os.path.join(SRC, f))

        style = subs.styles["Default"]
        style.fontname = "Arial"
        style.fontsize = 38      # ✅ smaller, non-cropped
        style.outline = 2
        style.shadow = 1
        style.alignment = 2     # Bottom-center
        style.marginv = 140     # ✅ pushes subtitles DOWN correctly

        out = f.replace(".srt", ".ass")
        subs.save(os.path.join(DST, out))

print("✅ SRT → ASS conversion completed with safe styling.")
