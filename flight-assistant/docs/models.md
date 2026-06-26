# Switching the model

The agent depends on an `LLMBackend` interface, not a specific vendor, so most
switches are pure configuration. There are three tiers.

## 1. Different OpenAI model — config only

```bash
export OPENAI_MODEL=gpt-4o-mini          # or via .env / --model
flight-assistant --model gpt-4o "from Tokyo to Reykjavik"
```

`--model` overrides `OPENAI_MODEL` for a single run, which is handy for A/B
comparisons (the CLI prints end-to-end latency per query).

## 2. Different OpenAI-compatible provider — config only

Any endpoint that speaks the OpenAI API (Azure OpenAI, Groq, Together, local
Ollama / LM Studio, vLLM, …) works by pointing `OPENAI_BASE_URL` at it:

```bash
# Local Ollama (free, no real token needed — great for token-free demos)
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_MODEL=llama3.1
export OPENAI_API_KEY=ollama            # dummy, just must be non-empty

# Groq
export OPENAI_BASE_URL=https://api.groq.com/openai/v1
export OPENAI_MODEL=llama-3.1-8b-instant
```

No code changes — the OpenAI backend already reads `OPENAI_BASE_URL`.

## 3. A different SDK (e.g. Anthropic Claude, Google Gemini) — one new file

Providers with their own SDKs/message formats are isolated behind the
`LLMBackend` interface in [`assistant/backends/`](../src/flight_assistant/assistant/backends).
To add one:

1. Implement `LLMBackend` in `assistant/backends/<provider>_backend.py`.
2. Register it in `assistant/backends/__init__.py` (`_BACKENDS`).
3. Select it with `LLM_PROVIDER=<provider>` or `--provider <provider>`.

The agent loop, MCP server, tools, registry, domain, and data layers are
**unchanged** — only the new backend file is added.

## Run with a free local model (Ollama)

Want to run the assistant with **no API key and no cost** — for a fully
offline, token-free demo? [Ollama](https://ollama.com) serves an
OpenAI-compatible endpoint locally, so it works through the existing OpenAI
backend with **zero code changes** (this is the Tier 2 switch above).

```bash
# 1. Install + start the local server
brew install ollama
ollama serve                          # leave running; listens on :11434

# 2. Pull a tool-capable model (function calling is required by the agent)
ollama pull llama3.2:3b               # ~2 GB, fastest/lightest
# or: ollama pull qwen2.5:7b          # ~4.7 GB, strongest tool calling
# or: ollama pull llama3.1:8b         # ~4.9 GB, popular all-rounder

# 3. Point the assistant at Ollama (e.g. in .env)
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_MODEL=llama3.2:3b       # match what you pulled
export OPENAI_API_KEY=ollama          # dummy — just must be non-empty

# 4. Run it, now fully token-free
flight-assistant "Can I fly from Berlin to Lisbon directly?"
```

To switch back to OpenAI, unset `OPENAI_BASE_URL` (or restore the EU endpoint)
and use your real key.

> **Caveat:** small local models — especially 3B — are weaker at multi-step
> tool calling than hosted models. If a local model fails to call a tool
> correctly, move up to `qwen2.5:7b`, the most reliable of the three for
> function calling.

## Self-hosting the model in the cloud (vLLM)

Ollama-on-a-laptop and a self-hosted model in the cloud are the **same
integration** — only the URL and a network boundary change. For production
serving, [vLLM](https://github.com/vllm-project/vllm) is the usual choice: it
exposes an **OpenAI-compatible `/v1` server** with high-throughput batching, so
the app still needs **no code change**.

```bash
# On a GPU host/container (e.g. the vllm/vllm-openai image):
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000   # OpenAI-compatible :8000/v1

# Point the assistant at it (front it with HTTPS + auth in real deployments):
export OPENAI_BASE_URL=https://llm.internal.example.com/v1
export OPENAI_MODEL=meta-llama/Llama-3.1-8B-Instruct
export OPENAI_API_KEY=<gateway token>     # from a secret manager, not the image
```

Deployment shape: containerize the vLLM server (weights baked in or pulled from
object storage), run it on a **GPU node pool** (managed Kubernetes, or a
model-serving product like SageMaker / Vertex / Azure ML, or serverless-GPU
hosts), add a health probe + autoscaling, and front it with **TLS + an API
gateway** — never expose the raw inference port. In the deployment topology the
LLM endpoint is its own GPU-bound, independently-scaled box behind
`OPENAI_BASE_URL`; the agent and MCP tool servers stay CPU-only and stateless.

> **When to self-host:** per-token hosted APIs (OpenAI, Groq, Together, …) are
> simpler and cheaper until utilization is high and steady. Self-hosting wins on
> data residency/privacy, vendor independence, or model customization — at the
> cost of owning GPU capacity, scaling, and model updates. Pick a model with
> strong function calling (Llama 3.1 8B+, Qwen2.5 7B+), which the agent requires.
