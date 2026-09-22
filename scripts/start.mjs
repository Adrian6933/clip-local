import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { readFileSync } from 'node:fs';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const py = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const mode = process.argv[2];
const astroPackage = JSON.parse(readFileSync(path.join(root,'node_modules/astro/package.json'),'utf8'));
const astroBin = typeof astroPackage.bin === 'string' ? astroPackage.bin : astroPackage.bin.astro;
const tasks = mode === 'api' ? [[py, ['-m','uvicorn','engine.api:app','--host','127.0.0.1','--port','4323']]] : mode === 'worker' ? [[py, ['-m','engine.worker']]] : [[process.execPath, [path.join(root,'node_modules/astro',astroBin), ...process.argv.slice(2)]]];
const children = tasks.map(([file,args]) => spawn(file,args,{cwd:root,stdio:'inherit',windowsHide:true,env:{...process.env,ASTRO_TELEMETRY_DISABLED:'1',ASTRO_DEV_BACKGROUND:'0'}}));
for (const child of children) { child.on('error', e => { console.error(e.message); process.exitCode=1; }); child.on('exit',code => {process.exitCode=code??1;}); }
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>children.forEach(child=>child.kill()));
