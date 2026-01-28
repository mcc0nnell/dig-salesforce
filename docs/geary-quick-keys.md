# Geary Golden Keys (JWT Auth Quick Guide)

This guide covers non-interactive JWT auth and manifest-scoped governance validate/deploy.

## Required environment variables

Local (shell) or CI:
- GEARY_SF_CLIENT_ID: Connected App Consumer Key
- GEARY_SF_USERNAME: integration user username
- GEARY_SF_INSTANCE_URL: defaults to https://login.salesforce.com
- GEARY_SF_JWT_KEY_B64: base64-encoded server.key content (CI-friendly)
- GEARY_SF_JWT_KEY_PATH: optional local path to server.key (overrides *_B64)
- GEARY_ORG_ALIAS: defaults to deafingov

Notes:
- Set either GEARY_SF_JWT_KEY_B64 or GEARY_SF_JWT_KEY_PATH (path wins if both are set).
- Do not store private keys or secrets in git.

## Generate server.key / server.crt

Run from a safe local folder (do not commit the key):

```bash
openssl genrsa -out server.key 2048
openssl req -new -x509 -key server.key -out server.crt -days 365
```

To produce a base64 string for CI secrets:

```bash
base64 < server.key
```

## Connected App configuration

Your Salesforce Connected App must be configured for JWT bearer:
- Enable OAuth settings
- Enable the JWT bearer flow
- Upload server.crt
- Use the Consumer Key as GEARY_SF_CLIENT_ID

## Commands

```bash
./scripts/geary auth
./scripts/geary governance:validate
./scripts/geary governance:deploy --confirm
```

## Key rotation

1) Generate a new server.key/server.crt pair.
2) Upload the new server.crt to the Connected App.
3) Update CI secrets and local GEARY_SF_JWT_KEY_* values.
4) Re-run `./scripts/geary auth` and validate.
