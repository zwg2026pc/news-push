#!/usr/bin/env python3
"""cmd_relay.py — 轮询 GitHub cmd.txt，执行命令，写回 output.txt"""
import subprocess, time, os, json, base64, sys

REPO = "zwg2026pc/news-push"
CMD_PATH = "relay/cmd.txt"
OUT_PATH = "relay/output.txt"
POLL = 3

last_cmd = None

def gh_api(endpoint, method="GET", body=None):
    cmd = ["gh", "api", f"repos/{REPO}/{endpoint}"]
    if method != "GET":
        cmd.extend(["-X", method])
    if body:
        cmd.extend(["--input", "-"])
    r = subprocess.run(cmd, input=body, capture_output=True, text=True, timeout=15)
    return r

def fetch_cmd():
    r = gh_api(f"contents/{CMD_PATH}", "--jq", ".content")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return base64.b64decode(r.stdout.strip()).decode("utf-8")
    except:
        return None

def push_output(text):
    content_b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    # get sha if exists
    r = gh_api(f"contents/{OUT_PATH}", "--jq", ".sha")
    sha = r.stdout.strip() if r.returncode == 0 else None
    payload = json.dumps({"message":"relay output","content":content_b64, **({"sha":sha} if sha else {})})
    gh_api(f"contents/{OUT_PATH}", "PUT", payload)

print(f"RELAY STARTED: polling {CMD_PATH} every {POLL}s", flush=True)

while True:
    try:
        cmd = fetch_cmd()
        if cmd and cmd != last_cmd:
            print(f"[EXEC] {cmd[:120]}", flush=True)
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd="/root")
            out = f"EXIT={r.returncode}\n--- STDOUT ---\n{r.stdout}\n--- STDERR ---\n{r.stderr}"
            push_output(out)
            last_cmd = cmd
            print(f"[DONE] exit={r.returncode}", flush=True)
        time.sleep(POLL)
    except Exception as e:
        print(f"[ERR] {e}", flush=True)
        time.sleep(POLL)
