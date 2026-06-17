#!/usr/bin/env python
"""train_v3_cloud.py — cloud GPU training"""
import torch, json, os, sys

def log(msg): print(msg, flush=True)

log("="*60)
log("  train_v3_cloud — Instruct + Loss Mask + Full Checklist")
log("="*60)

HOME = os.path.expanduser("~")
MODEL_PATH = os.path.join(HOME, "models", "Qwen2.5-7B-Instruct")
DATA_PATH  = os.path.join(HOME, "data", "all_train_data.jsonl")
OUTPUT_DIR = os.path.join(HOME, "output", "lora_v3")
LOG_DIR    = os.path.join(HOME, "output", "logs")
for d in [OUTPUT_DIR, LOG_DIR, os.path.join(HOME,"data"), os.path.join(HOME,"models")]:
    os.makedirs(d, exist_ok=True)

log("\n[1] Loading data...")
with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = [json.loads(l) for l in f if l.strip()]
log(f"  Loaded {len(data)} samples")

log("\n[2] Loading tokenizer...")
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
tokenizer.padding_side = "right"
if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token

log("\n[3] Tokenizing with Loss Mask...")
SYSTEM_PROMPT = "You are a Chinese novel writer. Short sentences, plain style, no translation-ese."
def tokenize_fn(examples):
    all_input_ids, all_labels = [], []
    for inst, inp, out in zip(examples["instruction"], examples["input"], examples["output"]):
        messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"{inst}\n{inp}"}]
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        full_text = prompt_text + out + tokenizer.eos_token
        prompt_ids = tokenizer(prompt_text, truncation=True, max_length=1536, padding=False)["input_ids"]
        full_ids = tokenizer(full_text, truncation=True, max_length=1536, padding=False)["input_ids"]
        all_input_ids.append(full_ids)
        all_labels.append([-100]*len(prompt_ids) + full_ids[len(prompt_ids):])
    return {"input_ids":all_input_ids, "labels":all_labels}

from datasets import Dataset
dataset = Dataset.from_list(data).map(tokenize_fn, batched=True, remove_columns=["instruction","input","output"])

log("\n[4] Loading 4-bit Instruct model...")
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training

model = AutoModelForCausalLM.from_pretrained(MODEL_PATH,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4"),
    device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16, use_cache=False)
model = prepare_model_for_kbit_training(model)

log("\n[5] LoRA config...")
model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, task_type=TaskType.CAUSAL_LM,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]))
model.print_trainable_parameters()

log("\n[6] DataCollator...")
from transformers import DataCollatorForSeq2Seq
data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding="longest", label_pad_token_id=-100)

split = dataset.train_test_split(test_size=0.1, seed=42)
log(f"  Train: {len(split['train'])}, Val: {len(split['test'])}")

log(f"\n[7] Training... GPU: {torch.cuda.get_device_name(0)}")
from transformers import TrainingArguments, Trainer

trainer = Trainer(model=model, args=TrainingArguments(
    output_dir=OUTPUT_DIR, per_device_train_batch_size=1, gradient_accumulation_steps=8,
    num_train_epochs=2, learning_rate=1e-4, lr_scheduler_type="cosine", warmup_ratio=0.1,
    bf16=True, fp16=False, optim="paged_adamw_8bit", max_grad_norm=1.0, weight_decay=0.01,
    save_steps=50, save_strategy="steps", save_total_limit=None,
    eval_strategy="steps", eval_steps=50, load_best_model_at_end=True, metric_for_best_model="eval_loss", greater_is_better=False,
    logging_steps=10, report_to="tensorboard", logging_dir=LOG_DIR,
    group_by_length=True, dataloader_num_workers=0,
    gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
    seed=42, overwrite_output_dir=True),
    train_dataset=split["train"], eval_dataset=split["test"], data_collator=data_collator)
trainer.train()

log("\n[8] Saving LoRA...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
log(f"Done: {OUTPUT_DIR}")