#!/usr/bin/env python3
"""cmd_relay.py — 轮询 GitHub cmd.txt，执行命令，写回 output.txt"""
import subprocess, time, os, json, base64

REPO = "zwg2026pc/news-push"
POLL = 3
last_cmd = None

def gh_get(path):
    r = subprocess.run(["gh", "api", f"repos/{REPO}/contents/{path}"],
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)

def gh_put(path, content_b64, sha=None):
    payload = {"message": "relay", "content": content_b64}
    if sha:
        payload["sha"] = sha
    body = json.dumps(payload)
    subprocess.run(["gh", "api", f"repos/{REPO}/contents/{path}", "-X", "PUT", "--input", "-"],
                   input=body, capture_output=True, text=True, timeout=15)

def fetch_cmd():
    data = gh_get("relay/cmd.txt")
    if not data:
        return None
    return base64.b64decode(data["content"]).decode("utf-8").strip()

def push_output(text):
    content_b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    existing = gh_get("relay/output.txt")
    sha = existing["sha"] if existing else None
    gh_put("relay/output.txt", content_b64, sha)

print("RELAY STARTED", flush=True)

while True:
    try:
        cmd = fetch_cmd()
        if cmd and cmd != last_cmd:
            print(f"[EXEC] {cmd[:100]}", flush=True)
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd="/root")
            out = f"EXIT={r.returncode}\n--- STDOUT ---\n{r.stdout}\n--- STDERR ---\n{r.stderr}"
            push_output(out)
            last_cmd = cmd
        time.sleep(POLL)
    except Exception as e:
        print(f"[ERR] {e}", flush=True)
        time.sleep(POLL)
