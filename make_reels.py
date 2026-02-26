"""
Generate Instagram Reels from 6 promo images.
Output: 1080x1920 MP4, ~18 sec, Ken Burns zoom effect + crossfade transitions.
"""
import os
import subprocess
import requests

IMAGES = [
    ("https://files.catbox.moe/e023tl.png", "01_team.png"),
    ("https://files.catbox.moe/52b39m.png", "02_interview.png"),
    ("https://files.catbox.moe/qosoix.png", "03_handshake.png"),
    ("https://files.catbox.moe/9knt10.png", "04_laptop.png"),
    ("https://files.catbox.moe/jr8dpy.png", "05_success.png"),
    ("https://files.catbox.moe/utopgm.png", "06_collab.png"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "reels")
os.makedirs(OUT_DIR, exist_ok=True)

# Download images
for url, fname in IMAGES:
    path = os.path.join(OUT_DIR, fname)
    if not os.path.exists(path):
        print(f"Downloading {fname}...")
        r = requests.get(url)
        with open(path, "wb") as f:
            f.write(r.content)

# Each slide: 3 seconds, 0.5s crossfade between them
# Total: 6 * 3 - 5 * 0.5 = 15.5 seconds
SLIDE_DUR = 3
FADE_DUR = 0.5
FPS = 30
W, H = 1080, 1920

# Build ffmpeg filter: scale each image to 1080x1920 (cover), apply slow zoom, crossfade
inputs = []
filters = []

for i, (_, fname) in enumerate(IMAGES):
    inputs.extend(["-loop", "1", "-t", str(SLIDE_DUR), "-i", os.path.join(OUT_DIR, fname)])

# Scale + zoom effect for each input
for i in range(len(IMAGES)):
    # Scale to cover 1080x1920, then slow zoom from 1.0 to 1.1
    filters.append(
        f"[{i}:v]scale={W*2}:{H*2},zoompan=z='min(zoom+0.0005,1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={SLIDE_DUR*FPS}:s={W}x{H}:fps={FPS},setsar=1[v{i}]"
    )

# Chain crossfades
if len(IMAGES) == 1:
    filters.append(f"[v0]null[out]")
else:
    # First crossfade
    filters.append(
        f"[v0][v1]xfade=transition=fade:duration={FADE_DUR}:offset={SLIDE_DUR - FADE_DUR}[xf0]"
    )
    offset = SLIDE_DUR * 2 - FADE_DUR * 2
    for i in range(2, len(IMAGES)):
        prev = f"xf{i-2}"
        cur = f"xf{i-1}" if i < len(IMAGES) - 1 else "out"
        filters.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={FADE_DUR}:offset={offset:.1f}[{cur}]"
        )
        offset += SLIDE_DUR - FADE_DUR

filter_complex = ";\n".join(filters)

output_path = os.path.join(OUT_DIR, "jobs_ge_reels.mp4")

cmd = [
    "ffmpeg", "-y",
    *inputs,
    "-filter_complex", filter_complex,
    "-map", "[out]",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-preset", "medium",
    "-crf", "23",
    "-movflags", "+faststart",
    "-t", "18",
    output_path
]

print("Running ffmpeg...")
print(" ".join(cmd[:10]) + " ...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    size = os.path.getsize(output_path) / 1024 / 1024
    print(f"✅ Reels ready: {output_path} ({size:.1f} MB)")
else:
    print(f"❌ Error:\n{result.stderr[-1000:]}")
