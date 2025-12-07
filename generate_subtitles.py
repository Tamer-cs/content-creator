import os
import stable_whisper
import subprocess

AUDIO_DIR = "audio"
SUB_DIR = "subtitles"

os.makedirs(SUB_DIR, exist_ok=True)

# ✅ Inject local ffmpeg + ffprobe into runtime PATH
PROJECT_ROOT = os.path.abspath(".")
os.environ["PATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PATH", "")

# ✅ Test that ffprobe is now visible to Python
test = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True)
if test.returncode != 0:
    raise RuntimeError("ffprobe still not detectable by Python runtime")

# ✅ Load Whisper normally (no unsupported args)
model = stable_whisper.load_model("small")

for f in os.listdir(AUDIO_DIR):
    if not f.endswith(".mp3"):
        continue

    print("Transcribing:", f)

    audio_path = os.path.join(AUDIO_DIR, f)
    result = model.transcribe(audio_path)

    srt_path = os.path.join(SUB_DIR, f.replace(".mp3", ".srt"))
    result.to_srt_vtt(srt_path)

    print("Subtitle created:", srt_path)
