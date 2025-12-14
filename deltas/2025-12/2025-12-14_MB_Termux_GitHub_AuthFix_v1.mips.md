MIPS_HEADER:
  artifact_id: MB__TERMUX_GIT_AUTH_FIX__2025-12-14_v1
  parent_bundle: MB__LOOP_MVP_LTM_PIPELINE__2025-12-14_v1
  version: v1
  councils: [Auditor, Recorder]
  sha256: 6f01fbb81778a4e8dfdb096b7ff3586a9ba6a00cb8bc810dd0a566c7e4624795
  timestamp_utc: 2025-12-14T19:29:53Z
  content_type: text/markdown
BODY:

# Termux GitHub HTTPS Auth — Fix “Authentication failed” (PAT)

## What most often caused it
1) Token was not pasted correctly (hidden input makes this common)  
2) Token lacks permission: **Contents: Read & write**  
3) Token not scoped to **this repo** (fine-grained token repo access)  
4) Using GitHub account password (won’t work) instead of PAT

---

## Fastest clean fix: re-issue PAT and use AskPass so you don’t type blind

### A) Re-issue the PAT (recommended)
Create a **Fine-grained PAT** with:
- Repository access: **Only** `metablooms-ltm`
- Permissions: **Contents = Read and write**
- Expiration: pick something reasonable (30–90d) and you can rotate later

Copy it to your Android clipboard.

---

### B) Termux: ensure Termux:API is installed (clipboard access)
```bash
pkg install -y termux-api
```

---

### C) One-shot “no-blind-typing” clone (AskPass)
This pulls the token from your clipboard and feeds it to git without requiring visible typing.

```bash
cd ~
rm -rf ~/metablooms-ltm

# create a temporary askpass helper
cat > /data/data/com.termux/files/home/.git_askpass_mb.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-clipboard-get
EOF
chmod 700 /data/data/com.termux/files/home/.git_askpass_mb.sh

# force git to use askpass
export GIT_ASKPASS=/data/data/com.termux/files/home/.git_askpass_mb.sh
export GIT_TERMINAL_PROMPT=1

git clone https://github.com/blobertplunk-hue/metablooms-ltm.git

# cleanup
unset GIT_ASKPASS
rm -f /data/data/com.termux/files/home/.git_askpass_mb.sh
```

When prompted for **Username**, type: `blobertplunk-hue`  
When prompted for **Password**, just press Enter (AskPass supplies clipboard).

---

## If clone works but push fails later
Run inside the repo:
```bash
cd ~/metablooms-ltm
git remote -v
git status
```

Then try a quick network/auth probe:
```bash
GIT_TRACE=1 GIT_CURL_VERBOSE=1 git ls-remote https://github.com/blobertplunk-hue/metablooms-ltm.git
```

---

## Canonical debug log entry template
```text
UTC:
CONTEXT:
ERROR:
CAUSE:
FIX:
VERIFIED:
STATUS: [OK]/[FAIL]
SHA256(artifact):
```

## Burndown
Replace blind password entry with a clipboard-based AskPass flow and validate token scopes so Termux can clone/push reliably.
