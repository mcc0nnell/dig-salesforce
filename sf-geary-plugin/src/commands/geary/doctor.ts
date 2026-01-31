import {Flags, SfCommand} from '@salesforce/sf-plugins-core';
import fs from 'node:fs';
import path from 'node:path';
import {resolveRepoRoot} from '../../shared/root';
import {runPython} from '../../shared/runPython';

export default class GearyDoctor extends SfCommand<void> {
  public static summary = 'Check for Geary issues.';

  public static flags = {
    root: Flags.string({description: 'Repo root', required: false}),
    'no-auto-update': Flags.boolean({description: 'Disable auto update when slices.json is missing'}),
  };

  public async run(): Promise<void> {
    const {flags} = await this.parse(GearyDoctor);
    const root = resolveRepoRoot(flags.root);
    const script = path.join(root, 'tools', 'geary', 'geary.py');
    const slices = path.join(root, 'geary', 'out', 'slices.json');

    if (!fs.existsSync(slices) && !flags['no-auto-update']) {
      this.log('geary/out/slices.json missing; running sf geary update first...');
      const updateCode = await runPython([script, 'update', '--root', root]);
      if (updateCode !== 0) this.exit(updateCode);
    }

    const code = await runPython([script, 'doctor', '--root', root]);
    if (code !== 0) this.exit(code);
  }
}
