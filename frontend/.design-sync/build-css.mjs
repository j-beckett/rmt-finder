// Compiles the Tailwind stylesheet for design-sync; @font-face rules are
// stripped because their relative urls break once inlined (fonts ship via cfg.extraFonts).
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const out = '.design-sync/.cache/ds.css';
execFileSync(process.execPath, ['.ds-sync/node_modules/@tailwindcss/cli/dist/index.mjs', '-i', '.design-sync/tailwind.css', '-o', out], { stdio: 'inherit' });
const css = readFileSync(out, 'utf8').replace(/@font-face\s*\{[^}]*\}\s*/g, '');
writeFileSync(out, css);
console.error(`css: ${out} (${(css.length / 1024).toFixed(0)} KB)`);
