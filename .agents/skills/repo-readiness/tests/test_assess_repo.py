import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "assess_repo.py"


class AssessRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_file(self, relative_path):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test fixture\n", encoding="utf-8")

    def run_script(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_empty_repository_has_zero_score_and_all_recommendations(self):
        result = self.run_script("--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["score"], 0)
        self.assertEqual(report["readiness"]["level"], "Starting point")
        self.assertEqual(len(report["recommendations"]), 7)

    def test_recognized_signals_are_scored_deterministically(self):
        for path in (
            "AGENTS.md",
            "packages/api/CLAUDE.md",
            "packages/web/GEMINI.md",
            ".github/copilot-instructions.md",
            ".github/instructions/python.instructions.md",
            ".claude/rules/review.md",
            ".cursor/rules/python/testing.mdc",
            "skills/release/SKILL.md",
            ".github/prompts/review.prompt.md",
            ".claude/commands/code/review.md",
        ):
            self.add_file(path)

        first = self.run_script("--format", "json")
        second = self.run_script("--format", "json")

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertEqual(report["score"], 100)
        self.assertEqual(
            [category["points"] for category in report["categories"]],
            [30, 35, 35],
        )
        self.assertEqual(report["readiness"]["level"], "Strong foundation")
        self.assertIn(
            ".claude/commands/code/review.md",
            next(check for check in report["checks"] if check["key"] == "prompt_workflows")[
                "files"
            ],
        )

    def test_ignored_dependency_directory_does_not_inflate_score(self):
        self.add_file("node_modules/example/AGENTS.md")
        self.add_file("vendor/tool/SKILL.md")

        report = json.loads(self.run_script("--format", "json").stdout)

        self.assertEqual(report["score"], 0)

    def test_invalid_path_fails_explicitly(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root / "missing")],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
