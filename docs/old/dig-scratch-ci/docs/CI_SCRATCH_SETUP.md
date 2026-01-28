# Scratch Org CI Setup (DIG)

This bundle adds a GitHub Actions workflow that:
1) JWT-auths to your Dev Hub
2) Creates a scratch org
3) Runs validation (via `make dig-validate` if present, otherwise a manifest dry-run)
4) Deletes the scratch org

## 1) GitHub Secrets to add

Set these in **GitHub → Settings → Secrets and variables → Actions**:

- `SF_DEVHUB_USERNAME` — Dev Hub username (e.g., you@dig.org)
- `SF_CLIENT_ID` — Connected App Consumer Key (in the Dev Hub)
- `SF_INSTANCE_URL` — `https://login.salesforce.com` (or `https://test.salesforce.com`)
- `SF_JWT_KEY_B64` — base64 of your private key file (`server.key`)

### Base64 the key
```bash
base64 -i server.key | pbcopy
```

## 2) Connected App checklist (Dev Hub)

- Enable OAuth
- Set callback URL to something valid (not used for JWT), e.g. `http://localhost:1717/OauthRedirect`
- Select OAuth scopes:
  - `Access and manage your data (api)`
  - `Perform requests on your behalf at any time (refresh_token, offline_access)`
- Upload the **certificate** that matches your `server.key` (private key stays local)

## 3) Scratch definition path

The workflow expects:
- `config/project-scratch-def.json`

If yours differs, edit `.github/workflows/ci-scratch.yml`.

## 4) Notes

- Keep your existing slice manifests (e.g., `manifest/dig.xml`) as the validation surface.
- Keep `layouts/profiles` out unless explicitly needed — your current repo guardrail is correct.

