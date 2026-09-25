import { strict as assert } from "node:assert";

// --- Geometric Hit Detection Patterns ---

function hitTestRect(mouseX, mouseY, nodes) {
  let best = null;
  let bestDepth = -1;
  for (const node of nodes) {
    const left = node.x - node.w / 2;
    const top = node.y - node.h / 2;
    if (mouseX >= left && mouseX <= left + node.w && mouseY >= top && mouseY <= top + node.h) {
      if (node.depth > bestDepth) {
        bestDepth = node.depth;
        best = node;
      }
    }
  }
  return best;
}

function hitTestArc(mouseX, mouseY, nodes) {
  const dist = Math.sqrt(mouseX * mouseX + mouseY * mouseY);
  let angle = Math.atan2(mouseY, mouseX) + Math.PI / 2;
  if (angle < 0) angle += Math.PI * 2;
  let best = null;
  let bestDepth = -1;
  for (const node of nodes) {
    if (dist >= node.innerR && dist <= node.outerR && angle >= node.startAngle && angle <= node.endAngle) {
      if (node.depth > bestDepth) {
        bestDepth = node.depth;
        best = node;
      }
    }
  }
  return best;
}

// --- Tests ---

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log(`  ✓ ${name}`); }
  catch (e) { failed++; console.log(`  ✗ ${name}\n    ${e.message}`); }
}

test("hitTestRect finds the node", () => {
  const nodes = [
    { id: 1, x: 50, y: 50, w: 20, h: 20, depth: 1 },
    { id: 2, x: 50, y: 50, w: 10, h: 10, depth: 2 } // overlapping child
  ];
  
  // Hit child
  assert.equal(hitTestRect(50, 50, nodes).id, 2);
  // Hit parent only
  assert.equal(hitTestRect(42, 42, nodes).id, 1);
  // Miss both
  assert.equal(hitTestRect(0, 0, nodes), null);
});

test("hitTestArc finds the node", () => {
  const nodes = [
    { id: 1, innerR: 0, outerR: 50, startAngle: 0, endAngle: Math.PI, depth: 1 }, // top half
    { id: 2, innerR: 0, outerR: 50, startAngle: Math.PI, endAngle: 2 * Math.PI, depth: 1 } // bottom half
  ];
  
  // Hit top half (angle ~ 0)
  assert.equal(hitTestArc(0, -25, nodes).id, 1);
  
  // Hit bottom half (angle ~ 3PI/2)
  // x=-25, y=0 -> atan2(0, -25) = PI -> angle = PI + PI/2 = 3PI/2
  assert.equal(hitTestArc(-25, 0, nodes).id, 2);
  
  // Miss radius
  assert.equal(hitTestArc(0, 60, nodes), null);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
