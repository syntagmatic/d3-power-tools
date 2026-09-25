#!/usr/bin/env node
// Parse every ```js / ```javascript fenced block in skills/**/*.md as an ES module.
// Blocks fenced as js-fragment are skipped. Exit 1 on any syntax error.
//   node plugin/scripts/check-snippets.mjs [dir-or-file ...]   (default: skills)
import { readFileSync, readdirSync, statSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { join, relative } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";

const root = new URL("..", import.meta.url).pathname;
const targets = process.argv.slice(2).length ? process.argv.slice(2) : [join(root, "skills")];

const walk = p => statSync(p).isDirectory()
  ? readdirSync(p).flatMap(f => walk(join(p, f)))
  : p.endsWith(".md") ? [p] : [];

const blocks = [];
for (const file of targets.flatMap(walk)) {
  const lines = readFileSync(file, "utf8").split("\n");
  let open = null;
  lines.forEach((line, i) => {
    const m = line.match(/^\s*```(\S*)/);
    if (!m) return;
    if (open) { if (open.lang) blocks.push({ ...open, code: lines.slice(open.start + 1, i).join("\n") }); open = null; }
    else open = { file, start: i, lang: /^(js|javascript)$/.test(m[1]) ? m[1] : null };
  });
}

const dir = mkdtempSync(join(tmpdir(), "snippets-"));
let failed = 0;
for (const [n, b] of blocks.entries()) {
  const f = join(dir, `b${n}.mjs`);
  writeFileSync(f, b.code);
  const r = spawnSync(process.execPath, ["--check", f], { encoding: "utf8" });
  if (r.status !== 0) {
    failed++;
    const msg = (r.stderr.match(/SyntaxError: .*/) || [r.stderr.trim()])[0];
    console.log(`FAIL ${relative(root, b.file)}:${b.start + 1}  ${msg}`);
  }
}
rmSync(dir, { recursive: true, force: true });
console.log(`${blocks.length - failed}/${blocks.length} js blocks parse`);
process.exit(failed ? 1 : 0);
