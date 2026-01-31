import {Flags, SfCommand} from '@salesforce/sf-plugins-core';
import fs from 'node:fs';
import path from 'node:path';
import {resolveRepoRoot} from '../../shared/root';
import {runPython} from '../../shared/runPython';

export default class GearyInstall extends SfCommand<void> {
  public static summary = 'Install a Geary slice or alias.';

  public static args = [{name: 'name', required: true}];

  public static flags = {
    root: Flags.string({description: 'Repo root', required: false}),
    'target-org': Flags.string({char: 'o', required: true, description: 'Target org alias'}),
    'with-deps': Flags.boolean({description: 'Install dependencies'}),
    'allow-empty': Flags.boolean({description: 'Allow installing empty slices'}),
    'test-level': Flags.string({
      description: 'Test level',
      options: ['NoTestRun', 'RunLocalTests', 'RunAllTestsInOrg', 'RunSpecifiedTests'],
    }),
    tests: Flags.string({description: 'Comma-separated tests (RunSpecifiedTests only)'}),
    debug: Flags.boolean({description: 'Show full traceback on errors'}),
    'no-auto-update': Flags.boolean({description: 'Disable auto update when slices.json is missing'}),
  };

  public async run(): Promise<void> {
    const {args, flags} = await this.parse(GearyInstall);
    if (flags.tests && flags['test-level'] !== 'RunSpecifiedTests') {
      this.error('--tests requires --test-level RunSpecifiedTests');
    }
    if (flags['test-level'] === 'RunSpecifiedTests' && !flags.tests) {
      this.error('--test-level RunSpecifiedTests requires --tests');
    }

    const root = resolveRepoRoot(flags.root);
    const script = path.join(root, 'tools', 'geary', 'geary.py');
    const slices = path.join(root, 'geary', 'out', 'slices.json');

    if (!fs.existsSync(slices) && !flags['no-auto-update']) {
      this.log('geary/out/slices.json missing; running sf geary update first...');
      const updateCode = await runPython([script, 'update', '--root', root]);
      if (updateCode !== 0) this.exit(updateCode);
    }

    const pyArgs = buildInstallArgs({
      script,
      name: args.name,
      root,
      targetOrg: flags['target-org'],
      withDeps: flags['with-deps'],
      allowEmpty: flags['allow-empty'],
      testLevel: flags['test-level'],
      tests: flags.tests,
      debug: flags.debug,
    });

    const code = await runPython(pyArgs);
    if (code !== 0) this.exit(code);
  }
}

export type InstallArgInput = {
  script: string;
  name: string;
  root: string;
  targetOrg: string;
  withDeps?: boolean;
  allowEmpty?: boolean;
  testLevel?: string;
  tests?: string;
  debug?: boolean;
};

export function buildInstallArgs(input: InstallArgInput): string[] {
  const args: string[] = [
    input.script,
    'install',
    input.name,
    '--root',
    input.root,
    '--target-org',
    input.targetOrg,
  ];
  if (input.withDeps) args.push('--with-deps');
  if (input.allowEmpty) args.push('--allow-empty');
  if (input.testLevel) args.push('--test-level', input.testLevel);
  if (input.tests) args.push('--tests', input.tests);
  if (input.debug) args.push('--debug');
  return args;
}
