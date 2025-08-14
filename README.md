# n8n + Ollama (GPT‑OSS) Minimal Stack

This repo provides a minimal Docker setup for running:

- n8n (automation workflows) on port 5678
- Ollama (LLM server) on port 11434
- Pre-pulls a GPT‑OSS model (20B by default) on container start

> Note: 20B models require substantial RAM. If you have limited memory, use a smaller model like `gpt-oss:8b` (see below).

## Quick start

```bash
docker compose up -d
```

Services:
- n8n: http://localhost:5678
- Ollama API: http://localhost:11434

## What’s in here

- `docker-compose.yml`: defines `ollama` and `n8n`
- `Dockerfile.ollama`: base image for the Ollama service
- `entrypoint.sh`: starts Ollama and pre-pulls the model defined by `OLLAMA_MODEL`

## Model selection (pre-pull)

By default, the compose uses:

```env
OLLAMA_MODEL=gpt-oss:20b
```

Override at runtime without editing files:

```powershell
$env:OLLAMA_MODEL="gpt-oss:8b"; docker compose up -d ollama
```

Or set it in your shell (Linux/macOS):

```bash
export OLLAMA_MODEL=gpt-oss:8b
docker compose up -d ollama
```

### Low-memory systems

If you see a message like:

```
Error: model requires more system memory (...) than is available (...)
```

switch to a smaller model, e.g. `gpt-oss:8b`.

## Verify it’s working

List models (should include your selected model):

```powershell
docker exec ollama_mongo ollama list
```

Show model details:

```powershell
docker exec ollama_mongo ollama show gpt-oss:20b
```

Test a tiny prompt (inside the container):

```powershell
docker exec ollama_mongo sh -lc "echo -n 'Reply with the single word: ok' | ollama run gpt-oss:20b"
```

HTTP API test from host (PowerShell):

```powershell
curl.exe -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss:20b\",\"prompt\":\"Say ok\",\"stream\":false}"
``;

Check n8n responds:

```powershell
curl.exe -I http://localhost:5678
```

## Enable n8n basic auth (optional)

Add these environment variables to the `n8n` service in `docker-compose.yml` and restart:

```yaml
environment:
  - N8N_BASIC_AUTH_ACTIVE=true
  - N8N_BASIC_AUTH_USER=admin
  - N8N_BASIC_AUTH_PASSWORD=change_me
```

## Optional: GPU (NVIDIA)

If you have NVIDIA GPU set up, you can add the following under the `ollama` service:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: ["gpu"]
```

Ensure the NVIDIA Container Toolkit is installed and Docker can access your GPU.

## Troubleshooting

- Model memory errors: use a smaller model (e.g., `gpt-oss:8b`).
- Check Ollama logs for pull status:
  ```powershell
  docker logs -f ollama_mongo
  ```
- Recreate only Ollama after changing `OLLAMA_MODEL`:
  ```powershell
  docker compose up -d ollama
  ```
- Windows quoting issues: prefer running `curl` inside the container or use double-escaped JSON as shown above.

## Data persistence

Docker volumes:
- `ollama_data`: stores Ollama models
- `n8n_data`: stores n8n configuration and workflows

Remove stack (keeps volumes):

```bash
docker compose down
```

Remove everything (including volumes):

```bash
docker compose down
docker volume rm n8n_gpt_ollama_data n8n_gpt_n8n_data 2> /dev/null
```


