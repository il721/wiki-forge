# Ollama Setup Guide (this machine)

_Step-by-step to install Ollama and run the two recommended models. See `local-llm-recommendations.md` for the hardware rationale._

Two recommended models:
- **`llama3.2:3b`** — fast daily driver (fully on GPU, ~2 GB)
- **`qwen2.5:7b`** — higher-quality step-up (tight 5 GB GPU fit, ~4.7 GB)

## Step 1 — Install Ollama
- GUI: download `OllamaSetup.exe` from https://ollama.com/download/windows and run it. Installs to the user profile, runs as a tray background service, auto-starts with Windows.
- CLI alternative:
  ```powershell
  winget install --id Ollama.Ollama -e
  ```

## Step 2 — Verify install (open a NEW PowerShell so PATH refreshes)
```powershell
ollama --version
```

## Step 3 — Pull the two models (downloaded once, cached in C:\Users\il720506\.ollama\models)
```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
```

## Step 4 — Chat
```powershell
ollama run llama3.2:3b      # type a prompt; leave chat with /bye
ollama run qwen2.5:7b
```

## Step 5 — Confirm GPU offload
With a model loaded, in another PowerShell:
```powershell
ollama ps
```
PROCESSOR column: `100% GPU` = ideal (3B does this). A GPU/CPU split is expected on the 7B (tight fit on 5 GB) — works, just slower.

## Using with Wiki-Forge / scripts
Ollama serves a local API at `http://localhost:11434`.
```powershell
(Invoke-WebRequest http://localhost:11434/api/tags).Content   # list installed models (JSON)
ollama run llama3.2:3b "Summarize the Wiki-Forge project in two sentences."   # one-shot
```

## ⚠️ Performance tuning (IMPORTANT — already applied 2026-06-05)
Ollama 0.30.5 defaults to a **131072-token context**, which inflates the KV-cache to ~18 GB and shoves
83% of even the 3B model onto the (no-AVX2) CPU → very slow. Fix: cap the default context.

A persistent user env var was set:
```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH","8192","User")
# then restart Ollama (quit tray app, relaunch) so the server picks it up
```
Per-call override (API): add `"options": { "num_ctx": 8192 }`.

### GPU/driver note
NVIDIA driver **553** is too old for Ollama's CUDA backend (needs **570+**). Ollama falls back to **Vulkan**,
which still uses the P2000 (detects 5.1 GiB, ~4.3 GiB usable). Updating the driver to 570+ would re-enable
CUDA (typically faster than Vulkan) — optional.

### Measured results on this machine (ctx=8192, Vulkan)
| Model | Footprint | Processor | Speed |
|---|---|---|---|
| llama3.2:3b | 3.0 GB | **100% GPU** | ~57 tok/s |
| qwen2.5:7b | 6.0 GB | 42% CPU / 58% GPU | ~17 tok/s |

For comparison, llama3.2:3b at the **default 131072** context: 18 GB, 83% CPU/17% GPU — avoid.

## Quick reference
| Action | Command |
|---|---|
| List installed models | `ollama list` |
| Loaded models + GPU/CPU split | `ollama ps` |
| Chat | `ollama run llama3.2:3b` |
| Leave chat | `/bye` |
| Remove a model | `ollama rm qwen2.5:7b` |
| Update a model | `ollama pull llama3.2:3b` |
