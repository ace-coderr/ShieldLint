#!/usr/bin/env bash
# Rebuild ShieldLint-demo.mp4 from the captured beats, end to end.
#
#   ./docs/demo/build_demo.sh
#
# Capture (only when the site or the stage pages changed) is separate, because
# it needs an X display and a kiosk Chromium:
#   Xvfb :99 -screen 0 1600x900x24 &
#   Chromium --kiosk --app=http://127.0.0.1:8010/ --remote-debugging-port=9222 ...
#   python3 docs/demo/build_stages.py && DISPLAY=:99 python3 docs/demo/record_screen.py
set -euo pipefail
cd "$(dirname "$0")/../.."          # repo root

DEMO=docs/demo
OUT=ShieldLint-demo.mp4

echo "== 1/5  motion grade (sub-pixel push-in, ~5 min)"
python3 "$DEMO/motion.py" --rate 0.0046

echo "== 2/5  compose (cross-dissolve concat)"
python3 "$DEMO/compose_screen.py"

echo "== 3/5  mix the voice"
python3 "$DEMO/mix_voiceover.py" --video "$DEMO/video/take.mp4" \
    --timeline "$DEMO/video/timeline.json" --out "$OUT" --copy-video

echo "== 4/5  captions (burned in + .srt)"
python3 "$DEMO/captions.py" --video "$OUT" --out /tmp/shieldlint-captioned.mp4

echo "== 5/5  web encode"
"$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" \
    -y -v error -i /tmp/shieldlint-captioned.mp4 \
    -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -r 30 -g 60 \
    -c:a aac -b:a 128k -movflags +faststart "$OUT"

rm -f /tmp/shieldlint-captioned.mp4
echo "done: $OUT  $(du -h "$OUT" | cut -f1)"
