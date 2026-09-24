#!/usr/bin/env node
// PostToolUse hook: after Write/Edit of an .html file that uses D3, run the load+nan probe.
// Silent on success or when Playwright isn't installed. On errors, exit 2 so Claude sees the findings.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

let input = {};
try { input = JSON.parse(readFileSync(0, "utf8")); } catch { process.exit(0); }
const file = input.tool_input?.file_path;
if (!file || !/\.html?$/i.test(file)) process.exit(0);
try { if (!/\bd3\b/.test(readFileSync(file, "utf8"))) process.exit(0); } catch { process.exit(0); }

const probe = fileURLToPath(new URL("./probe.mjs", import.meta.url));
const r = spawnSync(process.execPath, [probe, file, "--checks", "load,nan"], { encoding: "utf8", timeout: 50000 });
if (r.status === 0) process.exit(0);
if (/Cannot find (package|module) 'playwright'|Executable doesn't exist/.test(r.stderr)) process.exit(0);

let findings = [];
try { findings = JSON.parse(r.stdout).findings.filter(f => f.severity === "error"); } catch {}
if (!findings.length) process.exit(0);
console.error(`Render check failed for ${file}:\n${findings.map(f => `- [${f.check}] ${f.detail}`).join("\n")}`);
process.exit(2);
