# Geary CLI Mermaid helper

Use `python tools/geary/geary.py mermaid` when you just need to hit the
`geary-mermaid-runner-v1` Worker and get back the JSON AST or rendered
SVG without dealing with the full slice workflow.

## Environment

- `GEARY_KEY` must be exported or defined via `.env.local`/`.env` before every
  invocation (the CLI also supports `--env-file`).
- `WORKER_URL` is optional; the default is
  `https://geary-mermaid-runner-v1.stokoe.workers.dev` (the CLI appends
  `/render`).
- Keep your Worker secret synchronized with the production env:

```bash
npx wrangler secret put GEARY_KEY --env production
```

## Examples

Read from stdin and emit SVG:

```bash
printf 'flowchart TD\nA-->B' | python tools/geary/geary.py mermaid --format svg --out tmp/a.svg
```

Read a file and print the JSON AST:

```bash
python tools/geary/geary.py mermaid --in docs/diagrams/example.mmd --format json
```

## Smoke check

`./scripts/geary-mermaid-smoke.sh` exercises both JSON and SVG output. It will
fail fast if `GEARY_KEY` is not exported or if the worker returns unexpected
content.
