# Geary Mermaid Runner (Worker-only MVP)

## Deploy

```bash
cd cf/mermaid-runner
npx wrangler secret put GEARY_KEY
npx wrangler deploy
```

## Notes

- This is the canonical Worker-only implementation for `geary-mermaid-runner-v1`.
- It does not use Containers or Durable Objects.
- `format=svg` runs the Mermaid core via Linkedom and returns safe `<svg>` output.
