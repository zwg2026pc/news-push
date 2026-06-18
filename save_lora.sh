#!/bin/bash
# 训练完成后运行此脚本：下载 LoRA 权重到本地
# 在云端运行: curl -sL https://raw.githubusercontent.com/zwg2026pc/news-push/main/save_lora.sh | bash
cd /root/output/lora_v3
tar czf /root/lora_weights.tar.gz adapter_model.safetensors tokenizer* *.json 2>/dev/null
ls -lh /root/lora_weights.tar.gz
echo "LoRA weights saved to /root/lora_weights.tar.gz"
echo "Download via JupyterLab file manager or: scp root@IP:/root/lora_weights.tar.gz ."
