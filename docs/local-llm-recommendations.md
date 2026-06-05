# Local LLM Recommendations (for this machine)

_Generated 2026-06-05 based on detected hardware._

## Hardware snapshot
| Component | Spec | Verdict for LLMs |
|---|---|---|
| **GPU** | NVIDIA Quadro P2000, **5 GB VRAM** (Pascal) | Binding constraint. WMI reports ~4 GB but the P2000 physically has 5 GB GDDR5. CUDA-capable, so Ollama GPU-accelerates. |
| **RAM** | 32 GB | Plenty — allows bigger models to run partly on CPU. |
| **CPU** | Intel i7-2600K (Sandy Bridge, 2011), 4c/8t | Weak link. **No AVX2/FMA** → anything spilling to CPU runs slowly. |

**Rule:** stay within ~5 GB VRAM so the model runs fully on the GPU. Use **Q4_K_M** quantization (Ollama default). Avoid models ≥13B — they lean on the AVX2-less CPU and crawl.

## Recommended — full GPU fit (fast)
| Model | Ollama pull | ~VRAM (Q4) | Good for |
|---|---|---|---|
| Llama 3.2 3B | `ollama pull llama3.2:3b` | ~2.0 GB | Best all-round small model; Wiki-Forge ingest/compile |
| Qwen2.5 3B | `ollama pull qwen2.5:3b` | ~2.0 GB | Strong reasoning + summarization for its size |
| Phi-3.5-mini (3.8B) | `ollama pull phi3.5` | ~2.3 GB | Structured / instruction tasks |
| Gemma 2 2B | `ollama pull gemma2:2b` | ~1.6 GB | Fastest, lightest; quick drafting |

## Tight fit (works, slightly slower)
| Model | Ollama pull | ~VRAM (Q4) | Note |
|---|---|---|---|
| Mistral 7B | `ollama pull mistral` | ~4.4 GB | Fits tightly |
| Qwen2.5 7B | `ollama pull qwen2.5:7b` | ~4.7 GB | Best quality that still mostly fits |
| Llama 3.1 8B | `ollama pull llama3.1:8b` | ~4.9 GB | Borderline — may offload a couple layers to CPU |

## Pick for Wiki-Forge
Start with **Llama 3.2 3B** (fast, fully on GPU). Step up to **Qwen2.5 7B** for higher quality when a bit less speed is acceptable.
