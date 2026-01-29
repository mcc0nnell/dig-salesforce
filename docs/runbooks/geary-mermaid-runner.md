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

#### SVG (placeholder)

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
npx wrangler deploy
```

## Local key setup

Generate a key and write `.env.local` (repo root):

```
bash scripts/gen_geary_key.sh
```

Load it into your shell:

```
set -a; source .env.local; set +a
```

Set the Worker secret from your env:

```
npx wrangler secret put GEARY_KEY
```

## TODO (real rendering)

- Use an external renderer service (Puppeteer/Playwright) to generate SVG/PNG.
- Add request signing / rate limiting.
- Persist render results (KV/R2) if needed.
- Expand AST parsing or use Mermaid parser in a separate runner.
