import {buildInstallArgs} from '../src/commands/geary/install';

describe('argument mapping', () => {
  it('forwards flags to python', () => {
    const args = buildInstallArgs({
      script: '/repo/tools/geary/geary.py',
      name: 'comms-web',
      root: '/repo',
      targetOrg: 'deafingov',
      withDeps: true,
      allowEmpty: true,
      testLevel: 'RunLocalTests',
      tests: 'TestA,TestB',
      debug: true,
    });

    expect(args).toEqual([
      '/repo/tools/geary/geary.py',
      'install',
      'comms-web',
      '--root',
      '/repo',
      '--target-org',
      'deafingov',
      '--with-deps',
      '--allow-empty',
      '--test-level',
      'RunLocalTests',
      '--tests',
      'TestA,TestB',
      '--debug',
    ]);
  });
});
