import { validateHierarchy, cleanHierarchy } from "./validate-hierarchy.js";
import { strict as assert } from "node:assert";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log(`  ✓ ${name}`); }
  catch (e) { failed++; console.log(`  ✗ ${name}\n    ${e.message}`); }
}

// --- validateHierarchy ---

test("valid tree passes", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "root" },
    { id: "B", parent: "root" },
  ];
  const result = validateHierarchy(rows);
  assert.equal(result.valid, true);
  assert.equal(result.errors.length, 0);
});

test("detects duplicate IDs", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "root" },
    { id: "A", parent: "root" },
  ];
  const result = validateHierarchy(rows);
  assert.equal(result.valid, false);
  assert.equal(result.errors[0].type, "duplicate");
});

test("detects orphaned nodes", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "missing" },
  ];
  const result = validateHierarchy(rows);
  assert.equal(result.valid, false);
  assert.equal(result.errors[0].type, "orphan");
  assert.equal(result.errors[0].node, "A");
});

test("detects multiple roots", () => {
  const rows = [
    { id: "root1", parent: "" },
    { id: "root2", parent: "" },
  ];
  const result = validateHierarchy(rows);
  assert.equal(result.valid, false);
  assert.equal(result.errors[0].type, "multiple-roots");
});

test("detects no root", () => {
  const rows = [
    { id: "A", parent: "B" },
    { id: "B", parent: "A" },
  ];
  const result = validateHierarchy(rows);
  assert.equal(result.valid, false);
  const types = result.errors.map(e => e.type);
  assert.ok(types.includes("no-root"));
});

test("detects cycles", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "B" },
    { id: "B", parent: "A" },
  ];
  const result = validateHierarchy(rows);
  assert.equal(result.valid, false);
  const types = result.errors.map(e => e.type);
  assert.ok(types.includes("cycle"));
});

// --- cleanHierarchy ---

test("clean returns original rows when valid", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "root" },
  ];
  assert.equal(cleanHierarchy(rows), rows);
});

test("clean deduplicates IDs", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "root", v: 1 },
    { id: "A", parent: "root", v: 2 },
  ];
  const cleaned = cleanHierarchy(rows);
  assert.equal(cleaned.filter(r => r.id === "A").length, 1);
  assert.equal(cleaned.find(r => r.id === "A").v, 1); // keeps first
});

test("clean grafts orphans onto root", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "missing" },
  ];
  const cleaned = cleanHierarchy(rows);
  const a = cleaned.find(r => r.id === "A");
  assert.equal(a.parent, "root");
});

test("clean merges multiple roots under synthetic root", () => {
  const rows = [
    { id: "R1", parent: "" },
    { id: "R2", parent: "" },
    { id: "A", parent: "R1" },
  ];
  const cleaned = cleanHierarchy(rows);
  assert.ok(cleaned.find(r => r.id === "__root__"));
  const roots = cleaned.filter(r => !r.parent || r.parent === "");
  assert.equal(roots.length, 1);
  assert.equal(roots[0].id, "__root__");
});

test("clean breaks cycles", () => {
  const rows = [
    { id: "root", parent: "" },
    { id: "A", parent: "B" },
    { id: "B", parent: "A" },
  ];
  const cleaned = cleanHierarchy(rows);
  // After breaking, should be valid
  const result = validateHierarchy(cleaned);
  assert.equal(result.valid, true, `Still has errors: ${JSON.stringify(result.errors)}`);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
