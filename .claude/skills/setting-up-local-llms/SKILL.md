---
name: setting-up-local-llms
description: Use when the user wants to run LLMs locally or offline, asks which local model their computer can handle, or wants to install and test Ollama models matched to their hardware (GPU VRAM, system RAM, CPU). Covers hardware detection, model recommendations, Ollama install, and GPU-offload verification.
---

# Setting Up Local LLMs

## Overview
Match models to the machine, install a runtime, and verify they actually run on the GPU.

**Core principle: VRAM is the binding constraint.** The model weights *plus* the KV-cache must fit
in GPU VRAM, or layers spill onto the CPU and inference crawls — catastrophically so on CPUs without
AVX2. Default to **Q4_K_M** quantization (Ollama's default). Optimize for *fully on GPU*, not just "fits".

## Run as permission-gated steps
Do these in order. **After each step, STOP and ask the user's permission before starting the next**
(use AskUserQuestion). Do not chain steps. This skill ends at "install + test" — wiring a model into
a specific application is intentionally out of scope.

1. Detect hardware
2. Recommend models + save to a file
3. Install the runtime (Ollama)
4. Pull + test the recommended models

## Step 1 — Detect hardware
The three numbers that decide everything: **GPU VRAM**, **system RAM**, **CPU AVX2 support**.

**`nvidia-smi` is the source of truth for VRAM and driver version — on every OS, Windows included.**
It ships with the NVIDIA driver. Run it first; only fall back to WMI if it's missing:
```powershell
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
# if "not recognized", it's just off PATH — try: & "$env:SystemRoot\System32\nvidia-smi.exe" ...
```
Then RAM + CPU (and WMI as a GPU fallback only):
```powershell
Get-CimInstance Win32_ComputerSystem | ForEach-Object { [math]::Round($_.TotalPhysicalMemory/1GB,1) }  # RAM GB
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM   # AdapterRAM is unreliable — see gotcha
```
Linux/macOS: same `nvidia-smi` line · `free -h` / `sysctl hw.memsize` · `lscpu | grep -o avx2` (empty = no AVX2).

**Gotchas — verify, do not trust raw output:**
- **WMI under-reports VRAM.** `Win32_VideoController.AdapterRAM` is a 32-bit field that saturates at
  ~4 GB (`4293918720`), so it lies about any bigger card. **Get the true number from `nvidia-smi`**, not
  from a spec lookup — the model name alone is often ambiguous (an "RTX 3060" is 12 GB, 8 GB, *or* a 6 GB
  laptop part; a "4 GB" Quadro P2000 is really 5 GB). `nvidia-smi`'s `memory.total` is authoritative.
- **AVX2.** Pre-2013 Intel (Sandy/Ivy Bridge — e.g. i5-3470, i7-2600K) have AVX1 but **no AVX2/FMA**;
  CPU-offloaded layers are very slow, so full-GPU fit is critical there. Rule of thumb: **all AMD
  Ryzen/Zen, and Intel from Haswell (2013) onward, have AVX2** — don't flag those. When unsure, check
  (`lscpu | grep -o avx2`, or `Get-CimInstance Win32_Processor` + the model's spec).
- **GPU driver age.** Ollama's CUDA backend needs a recent NVIDIA driver (570+ as of 2026). On an older
  driver it falls back to **Vulkan** — still GPU-accelerated but typically ~10–30% slower than CUDA.
  **Recommend updating to 570+ to unlock CUDA**; otherwise accept Vulkan. Confirm which backend actually
  engaged via the Ollama server log or `ollama ps` after loading a model.
- **Laptop GPUs.** A "Laptop GPU" name (and often less VRAM than the desktop part) means thermal/power
  limits apply: expect lower, more variable tok/s, and worse on battery than plugged in. Test on AC power.

## Step 2 — Recommend + save
Pick by *usable* VRAM (leave ~0.5–1 GB headroom), Q4_K_M:

| Usable VRAM | Fully-on-GPU picks |
|---|---|
| 2–3 GB | gemma2:2b, llama3.2:3b, qwen2.5:3b |
| 4–6 GB | llama3.2:3b (fast) + mistral / qwen2.5:7b (tight, may partially offload) |
| 8 GB | qwen2.5:7b, llama3.1:8b comfortably |
| 12–16 GB | 13–14B (qwen2.5:14b), or 8B at long context |
| 24 GB+ | 32B-class at Q4 |

A 7–8B model's ~4.7 GB of weights alone nearly fills a 5–6 GB card → expect partial CPU offload there.
A model sized right at the tier boundary (e.g. a 14B on exactly 12 GB) is "verify, may be tight" — pick
it only after `ollama ps` confirms 100% GPU at a capped context, not on the table alone.
Save the picks + the hardware snapshot + exact `ollama pull` commands to a markdown file (e.g.
`local-llm-recommendations.md`) so it survives the session.

## Step 3 — Install Ollama
```powershell
winget install --id Ollama.Ollama -e          # if winget is present
# else download + silent install:
Invoke-WebRequest https://ollama.com/download/OllamaSetup.exe -OutFile $env:TEMP\OllamaSetup.exe
Start-Process $env:TEMP\OllamaSetup.exe -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" -Wait
```
(macOS: `brew install ollama`; Linux: `curl -fsSL https://ollama.com/install.sh | sh`.)
Verify in a **new** shell: `ollama --version`. The server listens at `http://localhost:11434`.

## Step 4 — Pull + test (the part that matters)
```powershell
ollama pull <model>
ollama run <model> "Say: ready"
ollama ps        # PROCESSOR column — you want 100% GPU
```

**Critical fix — context length.** Recent Ollama defaults to a very large context (e.g. 131072), which
inflates the KV-cache to many GB and shoves most of even a 3B model onto the CPU (`ollama ps` shows e.g.
`83% CPU / 17% GPU`, SIZE many GB). Cap it:
```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH","8192","User")   # then restart Ollama
```
Per request, add `"options": { "num_ctx": 8192 }` to the API call. Re-check `ollama ps`: a model that was
`83% CPU` at 131072 ctx becomes `100% GPU` at 8192. Measure speed from the `/api/generate` response:
`tok/s = eval_count / (eval_duration / 1e9)`.

## Common mistakes
| Symptom | Cause / fix |
|---|---|
| Model crawls; `ollama ps` shows high % CPU | KV-cache too large — cap `OLLAMA_CONTEXT_LENGTH` (8192) and restart |
| "VRAM is only 4 GB" on a bigger card | WMI 32-bit cap — check the card's real spec |
| GPU not used at all | NVIDIA driver too old for CUDA → update driver, or accept Vulkan fallback |
| 7–8B won't fully fit on 5–6 GB | Expected; prefer a 3B for speed or accept partial offload |
| `ollama` not found right after install | PATH not refreshed — open a new shell, or call the full exe path |

## Red flags — STOP
- About to recommend a model without knowing the GPU's **usable** VRAM → detect hardware first.
- About to run all four steps without pausing → STOP, ask permission between each.
- About to declare a model "running on GPU" without reading `ollama ps` → verify the PROCESSOR split.
