#!/bin/bash
set -e

OUTPUT="sayitvid.ankiaddon"
echo "Packaging ${OUTPUT}..."

rm -f "${OUTPUT}"
zip -9 -r "${OUTPUT}" \
  LICENSE \
  README.md \
  __init__.py \
  api_client.py \
  card_filter.py \
  config.json \
  config.md \
  enricher.py \
  icon.png \
  icon.svg \
  manifest.json \
  meta.json \
  ui_dialog.py \
  -x "*.pyc" "*__pycache__*" "*.DS_Store*"

echo "Successfully built ${OUTPUT} ($(du -h "${OUTPUT}" | cut -f1))"
