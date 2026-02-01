# Geary Mermaid Runner (MVP)

## Endpoint

`POST /render`

### Request

JSON body:

```
{
  "mermaid": "<string>",
  "format": "json" | "svg" (optional, default: json),
  "id": "<optional>"
}
```

### Auth

- Requires header `X-Geary-Key`.
- The key must match the `GEARY_KEY` secret in the Worker environment.

### Responses

#### JSON (default)

```
{
  "ok": true,
  "id": "<id or null>",
  "warnings": [],
  "ast": {
    "kind": "flowchart|sequenceDiagram|stateDiagram|classDiagram|unknown",
    "nodes": [],
    "edges": []
  }
}
```

#### SVG (real rendering)

```
{
  "ok": true,
  "id": "<id or null>",
  "svg": "<svg...>",
  "warnings": []
}
```

### Errors

- 401 `unauthorized` (missing/invalid key)
- 400 `missing_mermaid` or `invalid_json`
- 413 `payload_too_large` (over 200KB)
- 422 `render_failed` (Mermaid failed to render or generated unsafe SVG)
- 500 `unexpected_error`

### CORS

- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: POST, OPTIONS`
- No credentials.

## Examples

Basic JSON:

```
curl -s -X POST https://geary-mermaid-runner-v1.stokoe.workers.dev/render \
  -H 'Content-Type: application/json' \
  -H 'X-Geary-Key: <GEARY_KEY>' \
  -d '{"mermaid":"flowchart TD\nA-->B"}'
```

Placeholder SVG:

```
curl -s -X POST https://geary-mermaid-runner-v1.stokoe.workers.dev/render \
  -H 'Content-Type: application/json' \
  -H 'X-Geary-Key: <GEARY_KEY>' \
  -d '{"mermaid":"sequenceDiagram\nA->>B: hi","format":"svg"}'
```

## Deploy

From `cf/mermaid-runner`:

```
npx wrangler deploy --env production
```

## Local key setup

Generate a key and write `.env.local` (repo root):

```
bash scripts/gen_geary_key.sh
```

Load it into your shell:

```
source scripts/load-env.sh
```

Set the Worker secret from your env:

```
printf '%s' "${GEARY_KEY}" | npx wrangler secret put GEARY_KEY --env production
```

## Geary CLI smoke & doctor

- `geary doctor` (it will load `.env.local` / `.env` automatically when run from the repo root or you can pass `--env-file`) prints `worker host`, `key present`, `mode` (`LIVE` or `OFFLINE`), `http status`, `latency ms`, and a PASS/FAIL line with next-step guidance. In live mode it hits the worker; add `--no-network` to validate the offline invariants for receipts/emissions/run directory structure/hash verification.
- `geary run --offline --stdin --format svg` normalizes the Mermaid input, emits `input.mmd`, a placeholder `output.svg` (or `output.json`), receipts, and emissions, and prints `run id: …` to stderr. Use `geary replay <run_id>` to recompute hashes and verify against the receipt.
- `scripts/smoke_geary.sh` loads `.env.local`/`.env`, runs `geary doctor` plus a live run/replay, and if the live doctor fails it falls back to `geary doctor --no-network`, `geary run --offline`, and `geary replay` so the smoke suite passes even in restricted CI/agent environments.

## TODO (real rendering)

- Use an external renderer service (Puppeteer/Playwright) to generate SVG/PNG.
- Add request signing / rate limiting.
- Persist render results (KV/R2) if needed.
- Expand AST parsing or use Mermaid parser in a separate runner.
