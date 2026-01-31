import fs from 'node:fs';
import path from 'node:path';

export const ROOT_MARKERS = [
  'sfdx-project.json',
  path.join('tools', 'geary', 'geary.py'),
];

export function looksLikeRepoRoot(dir: string): boolean {
  return ROOT_MARKERS.every((p) => fs.existsSync(path.join(dir, p)));
}

export function findRepoRoot(startDir: string): string {
  let current = path.resolve(startDir);
  while (true) {
    if (looksLikeRepoRoot(current)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  throw new Error('Unable to locate repo root (missing sfdx-project.json and tools/geary/geary.py).');
}

export function resolveRepoRoot(rootFlag?: string): string {
  const candidate = rootFlag ? path.resolve(rootFlag) : process.cwd();
  const root = rootFlag ? candidate : findRepoRoot(candidate);
  if (!looksLikeRepoRoot(root)) {
    throw new Error(`Provided --root is not a repo root: ${root}`);
  }
  return root;
}
