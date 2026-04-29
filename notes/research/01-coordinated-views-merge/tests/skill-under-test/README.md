# Skill Under Test

The synthesizer drops the merged SKILL.md here as `SKILL.md`. Frontmatter required:

```
---
role: skill-under-test
model: <synthesizer's model id>
harness: <synthesizer's harness>
date: <YYYY-MM-DD>
parent-skills: [brushing, linked-views, coordination]
proposed-name: coordinated-views
---
```

This file IS the merge proposal made executable. Critics review it. Alt-generators produce blocks against it. The blind judge does NOT see it. If the merge graduates, this file becomes `skills/coordinated-views/SKILL.md` (or whatever name synthesis chose).

## Anti-cheat for the synthesizer

- Don't write this file by copy-pasting all three source SKILL.md files. The whole point is compression and disambiguation. If the merged file exceeds ~350 lines, the merge is probably wrong.
- Don't reach for content from outside the three source skills (e.g., don't paste in scale advice from `scales/SKILL.md`). The merge is constrained to the union of brushing + linked-views + coordination minus the brush mechanics that stay in `brushing`.
- If you can't decide whether something belongs in the merge or stays in `brushing`, list it in `synthesis.md` under "Open questions deferred to critique / test" rather than guessing.
