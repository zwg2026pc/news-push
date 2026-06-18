#!/bin/bash
# 备份最新 checkpoint 到 GitHub Release
# export GH_TOKEN="ghp_xxx"  # 你的 GitHub Token
# curl -sL https://raw.githubusercontent.com/zwg2026pc/news-push/main/backup_ckpt.sh | bash

if [ -z "$GH_TOKEN" ]; then
  echo "Set GH_TOKEN first: export GH_TOKEN=ghp_xxx"
  exit 1
fi

CKPT_DIR="/root/output/lora_v3"
LATEST=$(ls -d $CKPT_DIR/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
if [ -z "$LATEST" ]; then echo "No checkpoint"; exit 0; fi
CKPT_NAME=$(basename $LATEST)
echo "Backing up $CKPT_NAME..."

# 打包 adapter + tokenizer
TAR="/root/${CKPT_NAME}.tar.gz"
tar czf "$TAR" -C "$CKPT_DIR" "$CKPT_NAME/adapter_model.safetensors" "$CKPT_NAME/tokenizer_config.json" "$CKPT_NAME/training_args.bin" 2>/dev/null
echo "Packed: $(ls -lh $TAR | awk '{print $5}')"

# 创建 release
TAG="ckpt-$(date +%m%d-%H%M)"
curl -s -X POST "https://api.github.com/repos/zwg2026pc/news-push/releases" \
  -H "Authorization: token $GH_TOKEN" \
  -d "{\"tag_name\":\"$TAG\",\"name\":\"$CKPT_NAME\"}" > /tmp/rel.json

URL=$(python3 -c "import json;d=json.load(open('/tmp/rel.json'));print(d.get('upload_url','').split('{')[0])")
if [ -n "$URL" ]; then
  curl -s -X POST "$URL?name=${CKPT_NAME}.tar.gz" \
    -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/gzip" \
    --data-binary "@$TAR"
  echo "Done: $CKPT_NAME"
else
  echo "Failed: $(cat /tmp/rel.json)"
fi
rm -f "$TAR" /tmp/rel.json
