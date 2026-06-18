#!/usr/bin/env python3
"""状态检查：GPU、训练进度、checkpoint、磁盘"""
import subprocess
def run(cmd): return subprocess.getoutput(cmd)
print("GPU:", run("nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader"))
print("TRAIN:", run("tail -3 /root/train.log"))
print("CKPTS:", run("ls -d /root/output/lora_v3/checkpoint-* 2>/dev/null | wc -l"))
print("DISK:", run("df -h / | tail -1"))
