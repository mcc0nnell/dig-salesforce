import {Flags, SfCommand} from '@salesforce/sf-plugins-core';
import path from 'node:path';
import {resolveRepoRoot} from '../../shared/root';
import {runPython} from '../../shared/runPython';

export default class GearyUpdate extends SfCommand<void> {
  public static summary = 'Rebuild Geary slice registry.';

  public static flags = {
    root: Flags.string({description: 'Repo root', required: false}),
  };

  public async run(): Promise<void> {
    const {flags} = await this.parse(GearyUpdate);
    const root = resolveRepoRoot(flags.root);
    const script = path.join(root, 'tools', 'geary', 'geary.py');
    const code = await runPython([script, 'update', '--root', root]);
    if (code !== 0) this.exit(code);
  }
}
