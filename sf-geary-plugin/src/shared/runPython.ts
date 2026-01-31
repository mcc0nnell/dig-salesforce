import {spawn} from 'node:child_process';

function trySpawn(command: string, args: string[]): Promise<number> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {stdio: 'inherit'});
    child.on('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'ENOENT') {
        return reject(err);
      }
      return reject(err);
    });
    child.on('close', (code) => {
      resolve(code ?? 1);
    });
  });
}

export async function runPython(args: string[]): Promise<number> {
  try {
    return await trySpawn('python3', args);
  } catch (err: unknown) {
    const e = err as NodeJS.ErrnoException;
    if (e.code !== 'ENOENT') throw err;
    return await trySpawn('python', args);
  }
}
