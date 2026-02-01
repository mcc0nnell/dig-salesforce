# Geary Mermaid Runner workflow

## 1. Generate a strong GEARY_KEY
Use a deterministic one-liner so the key is hard to guess:

```bash
openssl rand -hex 32
```

You can store the output temporarily in your shell (see step 2) but **do not commit it**.

## 2. Set the key for the current shell
Before you start working, export the generated key so other helpers can read it immediately:

```bash
export GEARY_KEY="$(openssl rand -hex 32)"
```

If you already generated the key elsewhere (password manager, secret store, etc.), substitute that value.

## 3. Store secrets locally (deterministic overrides)
The repo ships `cf/mermaid-runner/.env.example` with the fields you can override:

```ini
GEARY_KEY=REDACTED
WORKER_URL=https://geary-mermaid-runner-v1.stokoe.workers.dev
```

Copy it into `.env.local` (which is gitignored) and replace the placeholders:

```bash
cp .env.example .env.local
# edit .env.local and paste GEARY_KEY plus an optional WORKER_URL override
```

If you prefer to load a default worker URL for every shell regardless of `.env.local`, edit `.env`.

## 4. Persist the key in zsh shells
Run `scripts/install-shell-env.sh` from the repo root. It:

1. Ensures `~/.config/geary/.env` exists with `GEARY_KEY` and optional `WORKER_URL`.
2. Appends an idempotent snippet to `~/.zshrc` that sources that file without printing secrets.

After the script runs, open `~/.config/geary/.env`, paste your `GEARY_KEY` (and optional `WORKER_URL`), save, and restart your shell to get the export automatically.

## 5. Load the environment before running commands
Always run:

```bash
source scripts/load-env.sh
```

This helper loads `.env` first, then `.env.local`, so overrides win. It prints `GEARY_KEY length=<n>` and `WORKER_URL=<value>` and fails fast if `GEARY_KEY` is missing.

## 6. Push the secret to the production worker
Wrangler secrets are scoped per environment, so run:

```bash
printf '%s' "${GEARY_KEY}" | npx wrangler secret put GEARY_KEY --env production
```

Make sure `GEARY_KEY` is exported (compare to `source scripts/load-env.sh`) before invoking the command so it picks up the right value.

## 7. Deploy and validate
Deploy the worker:

```bash
npx wrangler deploy --env production
```

Then verify local behavior:

```bash
./scripts/smoke.sh
```

`smoke.sh` expects `GEARY_KEY` (and optionally `WORKER_URL`) to be set via `source scripts/load-env.sh`. It fails fast on missing secrets and exercises authenticated/unauthenticated/oversized payloads.

## Browser Rendering requirements
This worker uses Cloudflare Browser Rendering with a `MYBROWSER` binding (see `wrangler.toml`). Make sure Browser Rendering is enabled for your Cloudflare account and the binding exists before you deploy, otherwise SVG renders will fail with `svg_render_failed`.

Mermaid is currently loaded from a pinned CDN URL inside the Browser Rendering page. Bundling Mermaid into the worker would avoid a network fetch, but increases the worker bundle size significantly; if that becomes necessary, swap the CDN script for an injected bundle and keep the `securityLevel: "strict"` setting.

## Troubleshooting

### Confirm secrets exist in production
List the secrets so Wrangler confirms the value you set with `wrangler secret put`:

```bash
npx wrangler secret list --env production
```

Look for `GEARY_KEY` in the output so you know Wrangler has a copy to inject into `env.GEARY_KEY` at deploy time.

### Ensure the deployed worker name matches the manifest
Your `cf/mermaid-runner/wrangler.toml` uses `name = "geary-mermaid-runner-v1"` both globally and under `[env.production]`. If the worker you deploy to Cloudflare has a different script name, edit the `name` field to match before running `npx wrangler deploy --env production`.

### Verify the local key is correct
After you `source scripts/load-env.sh`, run:

```bash
printf '%s\n' "${GEARY_KEY:-}" | wc -c
```

It should print `64`. Use `curl --silent` (see the next section) to confirm the key sent in `X-Geary-Key` matches the exported value.

### Manual curl with explicit header
You can add `-H "X-Geary-Key: $GEARY_KEY"` to a `curl` request to prove the worker accepts the key outside of `smoke.sh`:

```bash
curl -s -w " %{http_code}\\n" \
  -X POST "${WORKER_URL:-https://geary-mermaid-runner-v1.stokoe.workers.dev}/render" \
  -H 'Content-Type: application/json' \
  -H "X-Geary-Key: ${GEARY_KEY}" \
  -d '{"mermaid":"graph TD\\nA-->B","format":"json"}'
```

If the key is valid, you should see `200` and a JSON body containing `"ok":true`.

### Latency test
Use the latency helper to exercise the same SVG path as the smoke test, with small curl retries for transient network hiccups:

```bash
./scripts/latency.sh
```

It prints `HTTP:<code> total:<seconds>` plus `requestId` and failure diagnostics (stage/attempt/elapsedMs) when a render fails.

### Command sequence recap
1. `source scripts/load-env.sh` (makes sure `.env`/`.env.local` are loaded and `GEARY_KEY` is exported)
2. `printf '%s' "${GEARY_KEY}" | npx wrangler secret put GEARY_KEY --env production`
3. `npx wrangler deploy --env production`
4. `./scripts/smoke.sh` (or the manual `curl` above)
