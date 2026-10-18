#!/usr/bin/env bash
# Rebuild ShieldLint-demo.mp4 from the captured beats, end to end.
#
#   ./demo/build_demo.sh
#
# Capture (only when the site or the stage pages changed) is separate, because
# it needs an X display and a kiosk Chromium:
#   Xvfb :99 -screen 0 1600x900x24 &
#   Chromium --kiosk --app=http://127.0.0.1:8010/ --remote-debugging-port=9222 ...
#   python3 demo/build_stages.py && DISPLAY=:99 python3 demo/record_screen.py
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/5  motion grade (sub-pixel push-in, ~5 min)"
python3 demo/motion.py --rate 0.0046

echo "== 2/5  compose (cross-dissolve concat)"
python3 demo/compose_screen.py

echo "== 3/5  mix the voice"
python3 demo/mix_voiceover.py --video demo/video/take.mp4 \
    --timeline demo/video/timeline.json --out ../ShieldLint-demo.mp4 --copy-video

echo "== 4/5  captions (burned in + .srt)"
python3 demo/captions.py --video ../ShieldLint-demo.mp4 --out ../ShieldLint-demo-cap.mp4

echo "== 5/5  web encode"
ffmpeg_web() {
  "$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" \
    -y -v error -i ../ShieldLint-demo-cap.mp4 \
    -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -r 30 -g 60 \
    -c:a aac -b:a 128k -movflags +faststart ShieldLint-demo.mp4
}
ffmpeg_web
cp ShieldLint-demo.mp4 ../ShieldLint-demo.mp4
rm -f ../ShieldLint-demo-cap.mp4

echo "done: $(du -h ShieldLint-demo.mp4 | cut -f1)"
