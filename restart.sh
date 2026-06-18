#!/bin/bash
# 重启训练（OOM/crash后用）
# curl -sL https://raw.githubusercontent.com/zwg2026pc/news-push/main/restart.sh | bash
kill $(pgrep -f train_v3.py) 2>/dev/null
cd /root
sed -i 's|models/qwen/Qwen2.5-7B-Instruct|models/qwen/Qwen2___5-7B-Instruct|g' train_v3.py
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nohup python3 train_v3.py > train.log 2>&1 &
echo "PID: $!"
sleep 5
tail -3 train.log
