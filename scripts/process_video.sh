#!/bin/bash
# Process a green screen video into WebM with alpha channel
# Usage: ./process_video.sh input.mp4 output.webm

set -e

INPUT="${1:?Usage: process_video.sh input.mp4 output.webm}"
OUTPUT="${2:?Usage: process_video.sh input.mp4 output.webm}"

echo "Processing: $INPUT -> $OUTPUT"

ffmpeg -i "$INPUT" \
  -vf 'colorkey=0x00FF00:similarity=0.25:blend=0.15' \
  -c:v libvpx-vp9 \
  -auto-alt-ref 0 \
  -pix_fmt yuva420p \
  -b:v 1M \
  -f webm \
  "$OUTPUT"

echo "Done: $OUTPUT"
