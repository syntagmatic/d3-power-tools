"""Staging directory helpers for block generation.

Creates per-block staging dirs with copied skills so Claude/Gemini
discover them via native mechanisms (.claude/CLAUDE.md and .gemini/skills/).
"""
import json
import re
import shutil
from pathlib import Path

CLAUDE_SKILLS_DIR = "skills"
GEMINI_SKILLS_DIR = ".gemini/skills"


def _parse_description(skill_path: Path) -> str:
    """Extract description from SKILL.md YAML frontmatter."""
    text = skill_path.read_text()
    m = re.search(r'^description:\s*"(.+?)"', text, re.MULTILINE)
    return m.group(1) if m else ""


def _all_skill_names(proj: Path) -> list[str]:
    """List all skill directory names under skills/."""
    skills_dir = proj / CLAUDE_SKILLS_DIR
    return sorted(
        d.name for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def create_staging_dir(
    bid: str,
    skills: list[str],
    proj: Path,
    *,
    all_skills: bool = False,
) -> Path:
    """Create a staging directory with copied skills.

    Args:
        bid: Block ID (used as directory name).
        skills: Skills listed in the manifest for this block.
        proj: Project root path.
        all_skills: If True, include all skills (for trigger testing).
                    If False, include only the manifest-listed skills.

    Returns:
        Path to the staging directory.
    """
    staging = proj / "temp" / "staging" / bid
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    skill_names = _all_skill_names(proj) if all_skills else skills

    # Copy skills for Claude (skills/{name}/SKILL.md)
    for name in skill_names:
        src = proj / CLAUDE_SKILLS_DIR / name / "SKILL.md"
        if not src.exists():
            continue
        dest_dir = staging / CLAUDE_SKILLS_DIR / name
        dest_dir.mkdir(parents=True)
        shutil.copy2(src, dest_dir / "SKILL.md")

    # Copy skills for Gemini (.gemini/skills/{name}/SKILL.md)
    for name in skill_names:
        src = proj / GEMINI_SKILLS_DIR / name / "SKILL.md"
        if not src.exists():
            continue
        dest_dir = staging / GEMINI_SKILLS_DIR / name
        dest_dir.mkdir(parents=True)
        shutil.copy2(src, dest_dir / "SKILL.md")

    # Write .claude/CLAUDE.md
    _write_claude_md(staging, skill_names, proj)

    return staging


def _write_claude_md(staging: Path, skill_names: list[str], proj: Path):
    """Write a minimal CLAUDE.md listing available skills."""
    rows = []
    for name in sorted(skill_names):
        src = proj / CLAUDE_SKILLS_DIR / name / "SKILL.md"
        if not src.exists():
            continue
        desc = _parse_description(src)
        # Truncate long descriptions for the table
        short = desc[:120] + "..." if len(desc) > 120 else desc
        rows.append(f"| {name} | skills/{name}/SKILL.md | {short} |")

    table = "\n".join(rows)

    claude_dir = staging / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "CLAUDE.md").write_text(f"""# D3 Power Tools

Build a standalone D3.js visualization. Use modern D3 v7+, vanilla JS, no frameworks.
Canvas for data (>500 elements), SVG for interaction.
Generate ALL synthetic data inline.

## Code Style

- ES modules or inline `<script type="module">`
- No frameworks — vanilla JS + D3
- Prefer `const` and arrow functions
- Use D3 conventions: selections, joins, scales, axes

## Available Skills

Read any skill file for detailed patterns and recipes.

| Skill | Path | Description |
|-------|------|-------------|
{table}
""")


def cleanup_staging_dir(staging: Path):
    """Remove a staging directory. Safe to call if it doesn't exist."""
    shutil.rmtree(staging, ignore_errors=True)


def parse_skill_reads(stream_output: str) -> list[str]:
    """Extract skill names from Claude stream-json tool_use Read events.

    Looks for Read tool calls targeting skills/*/SKILL.md paths.
    """
    skills_read = []
    for line in stream_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        if event.get("type") != "assistant":
            continue

        message = event.get("message", {})
        for block in message.get("content", []):
            if block.get("type") != "tool_use" or block.get("name") != "Read":
                continue
            file_path = block.get("input", {}).get("file_path", "")
            m = re.search(r"skills/([^/]+)/SKILL\.md", file_path)
            if m:
                skill_name = m.group(1)
                if skill_name not in skills_read:
                    skills_read.append(skill_name)

    return skills_read
