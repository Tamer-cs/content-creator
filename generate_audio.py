import os
import asyncio
import edge_tts

SCRIPTS_DIR = "scripts"
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

VOICE = "en-GB-RyanNeural"   # Deep, mature, very human
RATE = "-8%"                # Slower = more natural
PITCH = "-15Hz"              # Lower pitch = deeper voice


async def main():
    for filename in os.listdir(SCRIPTS_DIR):
        if not filename.endswith(".txt"):
            continue

        base = filename.replace(".txt", "")
        out_path = os.path.join(AUDIO_DIR, base + ".mp3")

        if os.path.exists(out_path):
            continue

        with open(os.path.join(SCRIPTS_DIR, filename), "r", encoding="utf-8") as f:
            text = f.read().strip()

        communicate = edge_tts.Communicate(
            text=text,
            voice=VOICE,
            rate=RATE,
            pitch=PITCH
        )

        await communicate.save(out_path)
        print("Audio created:", out_path)

asyncio.run(main())
