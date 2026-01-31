import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {findRepoRoot, looksLikeRepoRoot, resolveRepoRoot} from '../src/shared/root';

describe('repo root discovery', () => {
  it('finds root by markers', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'geary-root-'));
    const repo = path.join(tmp, 'repo');
    const nested = path.join(repo, 'a', 'b');
    fs.mkdirSync(path.join(repo, 'tools', 'geary'), {recursive: true});
    fs.mkdirSync(nested, {recursive: true});
    fs.writeFileSync(path.join(repo, 'sfdx-project.json'), '{}');
    fs.writeFileSync(path.join(repo, 'tools', 'geary', 'geary.py'), '#!/usr/bin/env python3');

    expect(looksLikeRepoRoot(repo)).toBe(true);
    expect(findRepoRoot(nested)).toBe(repo);
    expect(resolveRepoRoot(repo)).toBe(repo);
  });
});
