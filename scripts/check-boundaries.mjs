import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const roots = ['app', 'packages'];
const allowedCoreBoundary = path.normalize('packages/noel-bridge');
const forbiddenPatterns = [
  /core\.manuscript_registry/g,
  /core\.text_witness_registry/g,
  /core\.manuscript_reading_attestations/g,
  /from\s+['"][^'"]*core\//g,
];

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true }).catch(() => []);
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...await walk(full));
    else if (/\.(?:ts|tsx|js|jsx|mjs|cjs)$/.test(entry.name)) files.push(full);
  }
  return files;
}

const violations = [];
for (const root of roots) {
  for (const file of await walk(root)) {
    if (path.normalize(file).startsWith(allowedCoreBoundary)) continue;
    const text = await readFile(file, 'utf8');
    for (const pattern of forbiddenPatterns) {
      pattern.lastIndex = 0;
      if (pattern.test(text)) violations.push(`${file}: direct Noel/Core dependency (${pattern})`);
    }
  }
}

if (violations.length) {
  console.error('Write Now custody boundary violations:\n' + violations.join('\n'));
  process.exit(1);
}

console.log('Write Now custody boundaries passed.');
