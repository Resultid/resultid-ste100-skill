"""Tests for the hooks. Run: python3 -m unittest discover -s tests -v"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"


def run_hook(script, level=None, data_dir=None):
    env = {k: v for k, v in os.environ.items() if k != "STE100_LEVEL"}
    if level is not None:
        env["STE100_LEVEL"] = level
    env["CLAUDE_PLUGIN_DATA"] = data_dir or tempfile.mkdtemp()
    return subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input="{}", capture_output=True, text=True, env=env, timeout=10,
    )


class HooksConfig(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((HOOKS / "hooks.json").read_text())["hooks"]

    def test_events_registered(self):
        self.assertIn("SessionStart", self.config)
        self.assertIn("UserPromptSubmit", self.config)

    def test_session_start_matcher_covers_resume_events(self):
        matcher = self.config["SessionStart"][0]["matcher"]
        for source in ("startup", "resume", "clear", "compact"):
            self.assertIn(source, matcher.split("|"))

    def test_hook_scripts_exist(self):
        for entries in self.config.values():
            for entry in entries:
                for hook in entry["hooks"]:
                    script = hook["args"][0].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
                    self.assertTrue(Path(script).is_file(), script)


class SessionStartHook(unittest.TestCase):
    def test_injects_full_prompt(self):
        for level in ("strict", "standard", "terse"):
            out = json.loads(run_hook("session_start.py", level).stdout)
            hook = out["hookSpecificOutput"]
            self.assertEqual(hook["hookEventName"], "SessionStart")
            self.assertIn(f"LEVEL: {level}", hook["additionalContext"])

    def test_off_prints_nothing(self):
        self.assertEqual(run_hook("session_start.py", "off").stdout, "")


class PromptReminderHook(unittest.TestCase):
    def test_reminder_is_short_and_names_the_level(self):
        for level in ("strict", "standard", "terse"):
            result = run_hook("prompt_reminder.py", level)
            self.assertEqual(result.returncode, 0)
            hook = json.loads(result.stdout)["hookSpecificOutput"]
            self.assertEqual(hook["hookEventName"], "UserPromptSubmit")
            text = hook["additionalContext"]
            self.assertIn(level, text)
            self.assertLess(len(text.split()), 40)

    def test_off_prints_nothing(self):
        self.assertEqual(run_hook("prompt_reminder.py", "off").stdout, "")

    def test_default_level_is_standard(self):
        text = json.loads(run_hook("prompt_reminder.py").stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("standard", text)

    def test_saved_level_is_used(self):
        data_dir = tempfile.mkdtemp()
        (Path(data_dir) / "level").write_text("terse\n")
        text = json.loads(run_hook("prompt_reminder.py", None, data_dir).stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("terse", text)


if __name__ == "__main__":
    unittest.main()
