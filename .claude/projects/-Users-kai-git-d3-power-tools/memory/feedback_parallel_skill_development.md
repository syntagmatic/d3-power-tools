---
name: parallel-skill-development
description: Lessons learned from using parallel subagents to build multiple D3 skills simultaneously
type: feedback
---

Parallel subagent workflow for building skills works well. Validated pattern: parent reads conventions, launches N agents with detailed prompts, agents build+test+screenshot autonomously, parent copies results and updates shared files.

**Why:** Skills are independent directories with no shared code, making them ideal for parallel work. Worktree isolation adds overhead (manual cp -r to merge) without benefit when files don't overlap.

**How to apply:**
- Skip worktree isolation for new skills — just use parallel agents writing to different directories
- Always update shared files (CLAUDE.md, index.html, test.config.json) in the parent after agents finish
- Include convention references and exact frontmatter format in agent prompts for consistency
- Consider a follow-up audit pass to check cross-skill consistency in tone and depth
