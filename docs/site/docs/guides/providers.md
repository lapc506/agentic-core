# Configuring LLM Providers

Agent Studio connects to LLMs through a unified model configuration layer. You can set a runtime default and override it at the persona or sub-agent level.

---

## Model Cascading

Models inherit top-down: **Runtime → Persona → Sub-agent**. Each level overrides the one above it.

```
AgenticSettings.default_model     ← global fallback
  └── Persona model_config        ← persona-level override
        └── Sub-agent model_config ← sub-agent override
```

---

## Supported Providers

### OpenRouter

OpenRouter gives access to 200+ models from Anthropic, Google, Meta, Mistral, and others through a single API key.

**Environment variable:**
```bash
AGENTIC_OPENROUTER_API_KEY=sk-or-...
```

**Persona config:**
```yaml
model_config:
  provider: openrouter
  model: anthropic/claude-sonnet-4-6
  temperature: 0.3
  max_tokens: 4096
```

**Available models (examples):**

| Model | Use case |
|-------|----------|
| `anthropic/claude-sonnet-4-6` | Best for most agents |
| `anthropic/claude-opus-4-6` | Complex reasoning, orchestrators |
| `anthropic/claude-haiku-4-5` | Fast, cheap sub-tasks |
| `google/gemini-2.5-pro` | Long context, multimodal |
| `meta-llama/llama-3.3-70b-instruct` | Open-weight, cost-effective |

Browse all models at [openrouter.ai/models](https://openrouter.ai/models).

---

### Ollama (Local Models)

Run models locally without API keys.

**Environment variable:**
```bash
AGENTIC_OLLAMA_URL=http://localhost:11434   # default
```

**Persona config:**
```yaml
model_config:
  provider: ollama
  model: llama3.2:latest
  temperature: 0.7
```

**Pull a model:**
```bash
ollama pull llama3.2
ollama pull qwen2.5-coder:7b
```

Ollama must be running before starting Agent Studio.

---

### LM Studio

LM Studio exposes an OpenAI-compatible API on `localhost:1234`.

**Environment variable:**
```bash
AGENTIC_LMSTUDIO_URL=http://localhost:1234
```

**Persona config:**
```yaml
model_config:
  provider: lmstudio
  model: lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF
```

Load the model in LM Studio before starting Agent Studio. The model name must match exactly what LM Studio reports in its `/v1/models` endpoint.

---

### Fireworks AI

Fireworks offers fast, cost-efficient inference for open-weight models.

**Environment variable:**
```bash
AGENTIC_FIREWORKS_API_KEY=fw_...
```

**Persona config:**
```yaml
model_config:
  provider: fireworks
  model: accounts/fireworks/models/llama-v3p1-70b-instruct
  temperature: 0.5
```

---

### Anthropic (Direct)

Bypass OpenRouter and call Anthropic directly.

**Environment variable:**
```bash
AGENTIC_ANTHROPIC_API_KEY=sk-ant-...
```

**Persona config:**
```yaml
model_config:
  provider: anthropic
  model: claude-sonnet-4-6
```

---

### Google Gemini

**Environment variable:**
```bash
AGENTIC_GOOGLE_API_KEY=AIza...
```

**Persona config:**
```yaml
model_config:
  provider: google
  model: gemini-2.5-pro
```

Gemini is also the default embedding provider (`gemini-embedding-exp-03-07`) for multimodal RAG.

---

## Runtime Default

Set the global default in `AgenticSettings` or via environment variable:

```python
settings = AgenticSettings(
    default_model="anthropic/claude-sonnet-4-6",
    default_provider="openrouter",
)
```

```bash
AGENTIC_DEFAULT_MODEL=anthropic/claude-sonnet-4-6
AGENTIC_DEFAULT_PROVIDER=openrouter
```

Any persona without an explicit `model_config` inherits this default.

---

## Cost Tracking

All token usage is tracked via Langfuse when configured:

```bash
AGENTIC_LANGFUSE_PUBLIC_KEY=pk-lf-...
AGENTIC_LANGFUSE_SECRET_KEY=sk-lf-...
AGENTIC_LANGFUSE_HOST=https://cloud.langfuse.com
```

View per-agent, per-model cost breakdowns in the Langfuse dashboard or via `GET /api/metrics/cost`.
