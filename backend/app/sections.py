"""Section-level parsing, diffing, and merging for the fork system."""

import datetime
import re
from typing import Dict, List, Optional


def parse_sections(content: str) -> Dict[str, str]:
    """Parse markdown body (after frontmatter) into {section_name: content}.

    Splits on '## ' headers. Content before the first ## header is stored
    under the key '_preamble' (usually the '# Title' line).
    """
    sections = {}
    current_key = "_preamble"
    current_lines = []

    for line in content.split("\n"):
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            sections[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_key] = "\n".join(current_lines).strip()
    return {k: v for k, v in sections.items() if v}


def sections_from_recipe_data(
    ingredients: List[str],
    instructions: List[str],
    notes: List[str],
) -> Dict[str, str]:
    """Convert structured recipe data to section content strings."""
    sections = {}
    if ingredients:
        sections["Ingredients"] = "\n".join(f"- {item}" for item in ingredients)
    if instructions:
        sections["Instructions"] = "\n".join(
            f"{i}. {step}" for i, step in enumerate(instructions, 1)
        )
    if notes:
        sections["Notes"] = "\n".join(f"- {note}" for note in notes)
    return sections


def diff_sections(
    base_content: str,
    fork_ingredients: List[str],
    fork_instructions: List[str],
    fork_notes: List[str],
) -> Dict[str, str]:
    """Compare fork data against base recipe content.
    Returns only the sections that differ from the base.
    """
    base_sections = parse_sections(base_content)
    fork_sections = sections_from_recipe_data(
        fork_ingredients, fork_instructions, fork_notes
    )

    changed = {}
    for key in ("Ingredients", "Instructions", "Notes"):
        base_text = _normalize(base_sections.get(key, ""))
        fork_text = _normalize(fork_sections.get(key, ""))
        if fork_text != base_text:
            if fork_text:
                changed[key] = fork_sections[key]
            elif base_text:
                changed[key] = ""
    return changed


def generate_fork_markdown(
    forked_from: str,
    fork_name: str,
    changed_sections: Dict[str, str],
    author: Optional[str] = None,
    forked_at_commit: Optional[str] = None,
) -> str:
    """Generate a fork markdown file with frontmatter and changed sections."""
    lines = []
    lines.append("---")
    lines.append(f"forked_from: {forked_from}")
    lines.append(f"fork_name: {fork_name}")
    if author:
        lines.append(f"author: {author}")
    lines.append(f"date_added: {datetime.date.today().isoformat()}")
    if forked_at_commit:
        lines.append(f"forked_at_commit: {forked_at_commit}")
    lines.append("---")

    for section_name, content in changed_sections.items():
        if content:
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    lines.append("")
    return "\n".join(lines)


def merge_content(base_content: str, fork_content: str) -> str:
    """Merge base recipe content with fork modifications.
    For each section: use fork version if present, otherwise use base.
    """
    base_sections = parse_sections(base_content)
    fork_sections = parse_sections(fork_content)

    lines = []
    preamble = base_sections.get("_preamble", "")
    if preamble:
        lines.append(preamble)

    seen_sections = set()
    for section_name in base_sections:
        if section_name == "_preamble":
            continue
        seen_sections.add(section_name)
        content = fork_sections.get(section_name, base_sections[section_name])
        if content:
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    for section_name in fork_sections:
        if section_name == "_preamble" or section_name in seen_sections:
            continue
        content = fork_sections[section_name]
        if content:
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    lines.append("")
    return "\n".join(lines)


def merge_fork_into_base(base_content: str, fork_content: str) -> str:
    """Merge a fork's changes back into the base recipe content.

    This is an explicit alias for merge_content, used at the merge endpoint
    call site to clarify intent.
    """
    return merge_content(base_content, fork_content)


def _normalize(text: str) -> str:
    """Normalize section text for comparison."""
    return re.sub(r"\s+", " ", text.strip())
