#!/usr/bin/env python3
"""Deterministically assess repository signals for AI-assisted development."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "venv",
    "vendor",
}

CONTEXT_FILES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}
EDITOR_RULES_FILES = {".clinerules", ".cursorrules", ".windsurfrules"}

LEVELS: Sequence[Tuple[int, str, str]] = (
    (0, "Starting point", "Few recognized agent-facing signals are discoverable."),
    (25, "Emerging", "Some useful signals exist, but important categories are absent or sparse."),
    (50, "Good foundation", "Several useful signals exist, with meaningful opportunities to improve coverage."),
    (75, "Strong foundation", "Most recognized signal types are present; review their quality and keep them maintained."),
)


def _contains_adjacent(parts: Sequence[str], parent: str, child: str) -> bool:
    return any(parts[index : index + 2] == (parent, child) for index in range(len(parts) - 1))


def _is_scoped_instruction(path: str, name: str) -> bool:
    parts = Path(path).parts
    return name.endswith(".instructions.md") or (
        _contains_adjacent(parts, ".cursor", "rules") and name.endswith(".mdc")
    )


def _is_editor_rule(path: str, name: str) -> bool:
    parts = Path(path).parts
    if name in EDITOR_RULES_FILES:
        return True
    if _contains_adjacent(parts, ".claude", "rules") or _contains_adjacent(
        parts, ".windsurf", "rules"
    ):
        return name.endswith(".md")
    return ".clinerules" in parts[:-1] and name.endswith(".md")


def _scan(root: Path) -> Tuple[List[str], List[str]]:
    files: List[str] = []
    errors: List[str] = []

    def on_error(error: OSError) -> None:
        errors.append("{}: {}".format(error.filename or root, error.strerror or str(error)))

    for directory, child_directories, filenames in os.walk(
        str(root), topdown=True, followlinks=False, onerror=on_error
    ):
        child_directories[:] = sorted(
            name
            for name in child_directories
            if name not in IGNORED_DIRECTORIES
            and not (Path(directory) / name).is_symlink()
        )
        base = Path(directory)
        for name in sorted(filenames):
            path = (base / name).relative_to(root).as_posix()
            files.append(path)

    return files, errors


def _check(
    key: str,
    label: str,
    category: str,
    points: int,
    matched_files: Sequence[str],
    recommendation: str,
) -> Dict[str, object]:
    awarded = points if matched_files else 0
    return {
        "key": key,
        "label": label,
        "category": category,
        "points": awarded,
        "max_points": points,
        "files": list(matched_files),
        "recommendation": recommendation if not matched_files else None,
    }


def assess_repository(root: Path) -> Dict[str, object]:
    root = root.resolve()
    if not root.exists():
        raise ValueError("Repository path does not exist: {}".format(root))
    if not root.is_dir():
        raise ValueError("Repository path is not a directory: {}".format(root))

    files, errors = _scan(root)
    basenames: Dict[str, List[str]] = {}
    for relative_path in files:
        basenames.setdefault(Path(relative_path).name, []).append(relative_path)

    root_context = [
        path
        for path in files
        if Path(path).parent == Path(".") and Path(path).name in CONTEXT_FILES
    ]
    nested_context = [
        path
        for path in files
        if Path(path).parent != Path(".") and Path(path).name in CONTEXT_FILES
    ]
    copilots = basenames.get("copilot-instructions.md", [])
    scoped_rules = [
        path
        for path in files
        if _is_scoped_instruction(path, Path(path).name)
    ]
    editor_rules = [
        path
        for path in files
        if _is_editor_rule(path, Path(path).name)
    ]
    skills = [path for path in files if Path(path).name == "SKILL.md"]
    prompts = [
        path
        for path in files
        if Path(path).name.endswith(".prompt.md")
        or (
            _contains_adjacent(Path(path).parts, ".claude", "commands")
            and Path(path).suffix == ".md"
        )
    ]

    nested_context_award = min(len(nested_context), 2)
    checks = [
        _check(
            "root_context",
            "Root-level agent context",
            "context",
            20,
            root_context,
            "Add a root AGENTS.md, CLAUDE.md, or GEMINI.md with concise repository orientation and essential development commands.",
        ),
        {
            "key": "nested_context",
            "label": "Additional directory-level context",
            "category": "context",
            "points": nested_context_award * 5,
            "max_points": 10,
            "files": nested_context,
            "recommendation": (
                "Add focused context files in important subdirectories whose local conventions differ."
                if nested_context_award < 2
                else None
            ),
        },
        _check(
            "copilot_instructions",
            "Copilot repository instructions",
            "rules",
            15,
            copilots,
            "Add .github/copilot-instructions.md to explain repository-wide coding conventions and validation commands for Copilot.",
        ),
        _check(
            "scoped_instructions",
            "Scoped instruction files",
            "rules",
            10,
            scoped_rules,
            "Add path-specific *.instructions.md or .cursor/rules/*.mdc guidance where different parts of the codebase need distinct rules.",
        ),
        _check(
            "editor_agent_rules",
            "Other editor or agent rules",
            "rules",
            10,
            editor_rules,
            "Add concise rules for the editor or agent your team uses, such as .claude/rules/, .windsurf/rules/, .clinerules/, or a root editor-rules file.",
        ),
        _check(
            "skills",
            "Reusable agent skills",
            "workflows",
            20,
            skills,
            "Add a focused SKILL.md workflow for a recurring repository task so agents can reuse reliable steps.",
        ),
        _check(
            "prompt_workflows",
            "Reusable prompt workflows",
            "workflows",
            15,
            prompts,
            "Add reusable *.prompt.md files or Claude command prompts for repeatable tasks the team runs with agents.",
        ),
    ]

    category_order = ("context", "rules", "workflows")
    categories = []
    for category in category_order:
        category_checks = [check for check in checks if check["category"] == category]
        categories.append(
            {
                "key": category,
                "label": {
                    "context": "Agent context",
                    "rules": "Agent rules and instructions",
                    "workflows": "Repeatable workflows",
                }[category],
                "points": sum(int(check["points"]) for check in category_checks),
                "max_points": sum(int(check["max_points"]) for check in category_checks),
                "files": sorted(
                    {
                        path
                        for check in category_checks
                        for path in check["files"]
                    }
                ),
            }
        )

    score = sum(int(check["points"]) for check in checks)
    level = max((entry for entry in LEVELS if score >= entry[0]), key=lambda entry: entry[0])
    recommendations = [
        {
            "priority": index,
            "check": check["key"],
            "category": check["category"],
            "points_available": int(check["max_points"]) - int(check["points"]),
            "action": check["recommendation"],
        }
        for index, check in enumerate(
            sorted(
                (check for check in checks if check["recommendation"]),
                key=lambda item: (
                    -(int(item["max_points"]) - int(item["points"])),
                    checks.index(item),
                ),
            ),
            start=1,
        )
    ]

    return {
        "repository": str(root),
        "score": score,
        "max_score": 100,
        "readiness": {
            "level": level[1],
            "meaning": level[2],
        },
        "categories": categories,
        "checks": checks,
        "recommendations": recommendations,
        "limitations": (
            "This score measures recognized file presence only. It does not assess artifact quality, "
            "accuracy, freshness, completeness, or whether an agent follows the guidance."
        ),
        "scan_errors": errors,
    }


def _format_text(report: Dict[str, object]) -> str:
    lines = [
        "Repository readiness: {}/100 — {}".format(
            report["score"], report["readiness"]["level"]
        ),
        str(report["readiness"]["meaning"]),
        "",
        "Category breakdown:",
    ]
    for category in report["categories"]:
        lines.append(
            "- {}: {}/{}".format(
                category["label"], category["points"], category["max_points"]
            )
        )
        for path in category["files"]:
            lines.append("  - {}".format(path))

    lines.extend(["", "Highest-impact recommendations:"])
    recommendations = report["recommendations"]
    if recommendations:
        for recommendation in recommendations:
            lines.append(
                "{}. {} (+{} points available)".format(
                    recommendation["priority"],
                    recommendation["action"],
                    recommendation["points_available"],
                )
            )
    else:
        lines.append("- No recognized file-presence gaps.")

    lines.extend(["", "Limitations: {}".format(report["limitations"])])
    if report["scan_errors"]:
        lines.extend(["", "Scan errors (assessment may be incomplete):"])
        lines.extend("- {}".format(error) for error in report["scan_errors"])
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score recognized agent context, rules, and repeatable workflows."
    )
    parser.add_argument(
        "repository",
        nargs="?",
        default=".",
        help="Repository directory to assess (defaults to the current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (defaults to text).",
    )
    args = parser.parse_args(argv)

    try:
        report = assess_repository(Path(args.repository))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(_format_text(report))
    return 2 if report["scan_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
