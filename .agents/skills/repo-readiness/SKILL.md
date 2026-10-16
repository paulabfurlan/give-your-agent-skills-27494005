---
name: repo-readiness
description: Evaluate how ready a software repository is for AI-assisted development by running the bundled deterministic assessment script. Use this skill whenever a user asks whether a repository is ready for AI coding agents, how well it supports agent workflows, or what context, instructions, skills, or prompts it is missing; explain the score and prioritize improvements, and create missing artifacts only when asked.
compatibility: Requires Python 3.8+ to run the bundled assessment script.
---

# Repository readiness for AI-assisted development

Assess whether an agent can discover useful repository context, follow project-specific rules, and reuse repeatable workflows. The score is a deterministic inventory of recognized file signals, not a judgment about the quality of their contents.

## Assess the repository

1. Identify the repository root. If the user named a path, use it; otherwise use the current workspace root. If the workspace is a subdirectory, locate and assess the containing repository root rather than scoring only the current subdirectory.
2. Run the bundled script from this skill's directory, passing the repository root:

   ```bash
   python scripts/assess_repo.py /path/to/repository
   ```

   Add `--format json` when you need the structured report. Do not calculate, round, adjust, or substitute a score yourself. If the script reports an error or cannot inspect part of the repository, surface that limitation and do not present an incomplete result as a complete assessment.
3. Use the report's score, readiness band, category totals, detected files, and ordered recommendations as the source of truth. Explain that the score reflects the presence of recognized artifacts only: it does not validate whether instructions are accurate, current, well scoped, or followed by an agent.
4. Highlight the highest-point recommendations first. Connect each suggestion to the gap it addresses and the way it helps an agent work reliably. Mention already-detected files as evidence; do not imply that a missing signal proves the repository has no useful guidance.
5. Offer to help draft or add the highest-impact missing artifacts. Do not create or modify repository files unless the user asks.

## Explain the score

The script assigns points from fixed file-presence checks. The output includes the earned points, maximum points, evidence, and recommendations so users can see exactly what contributed.

Use the readiness band supplied by the script:

- **Starting point (0-24):** few recognized agent-facing signals are discoverable.
- **Emerging (25-49):** some useful signals exist, but important categories are absent or sparse.
- **Good foundation (50-74):** the repository has several useful signals, with meaningful opportunities to improve coverage.
- **Strong foundation (75-100):** most recognized signal types are present; review their quality and keep them maintained.

These bands describe artifact coverage, not guaranteed development speed, correctness, or safety. Do not describe a score as a quality certification.

## Report format

Present a concise report with:

1. **Readiness:** score out of 100 and the script's band.
2. **Category breakdown:** points earned and the files detected for context, rules/instructions, and repeatable workflows.
3. **What it means:** explain the scope and limits of a presence-based score.
4. **Recommended next steps:** list the highest-impact missing signals first, retaining the script's priority order.
5. **Offer:** ask whether the user wants help creating any missing artifact.

For machine-readable use, preserve the script's JSON output rather than rewriting or recalculating its values.

## Creating missing artifacts

Only proceed after the user explicitly asks for creation. Check existing files and project conventions first, ask for the intended audience or scope if it is unclear, and make the smallest useful addition. Prefer concise, repository-specific guidance over generic boilerplate. Re-run the assessment after changes and report the new deterministic score and detected evidence.
