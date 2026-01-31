# sf-geary (plugin)

Wrapper around the existing Geary Python CLI.

## Install (local dev)
```bash
cd sf-geary-plugin
npm i
npm run build
```

## Usage
```bash
node bin/run.js geary update --root ..
node bin/run.js geary list --root ..
node bin/run.js geary doctor --root ..
node bin/run.js geary install comms-web --target-org deafingov --root ..
```

## Notes
- The plugin discovers the repo root by searching for `sfdx-project.json` and `tools/geary/geary.py`.
- If `geary/out/slices.json` is missing, list/doctor/install will auto-run update unless `--no-auto-update` is set.
- Output and exit codes are streamed from the underlying Python CLI.
