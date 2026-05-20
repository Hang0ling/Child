from __future__ import annotations

import json
import unittest
from pathlib import Path

from decision_core import DecisionCoreOrchestrator
from decision_core.repairer import BriefRepairer
from decision_core.validator import BriefValidator


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class DecisionCoreTests(unittest.TestCase):
    def test_next_episode_generates_valid_brief(self) -> None:
        result = DecisionCoreOrchestrator().run(load_example("next_episode_input.json"))

        self.assertTrue(result["ok"], result.get("validation"))
        self.assertEqual(result["control_decision"]["mode"], "next_episode")
        self.assertEqual(result["brief_plan"]["brief_type"], "next_episode")
        self.assertIn("上一 Episode 已完成", result["execution_brief"])
        self.assertIn("下一 Episode", result["execution_brief"])
        self.assertIn("不继承", result["execution_brief"])
        self.assertIn("Opponent State：目标用户尚未锁定", result["execution_brief"])
        self.assertNotIn("Opponent State：上一 Episode 已完成", result["execution_brief"])
        self.assertIn("L1：", result["execution_brief"])
        self.assertIn("Tips：", result["execution_brief"])

    def test_continue_generates_valid_brief_and_skips_completed_steps(self) -> None:
        result = DecisionCoreOrchestrator().run(load_example("continue_input.json"))

        self.assertTrue(result["ok"], result.get("validation"))
        self.assertEqual(result["control_decision"]["mode"], "continue_current_episode")
        self.assertEqual(result["normalized_context"]["skip_steps"], [1, 2, 3, 4, 5])
        source_steps = [step["source_step"] for step in result["brief_plan"]["steps"]]
        self.assertNotIn(1, source_steps)
        self.assertEqual(source_steps[0], 6)
        self.assertIn("中断在了步骤6", result["execution_brief"])
        self.assertIn("不要重复", result["execution_brief"])
        self.assertIn("Opponent State：目标用户：@example_real_user", result["execution_brief"])

    def test_repairer_removes_repeated_completed_steps(self) -> None:
        result = DecisionCoreOrchestrator().run(load_example("continue_input.json"))
        context = result["normalized_context"]
        strategy = result["strategy_result"]
        bad_plan = {
            "brief_type": "continue_current_episode",
            "opening": {},
            "strategy": {},
            "global_constraints": [],
            "steps": [
                {
                    "index": 1,
                    "source_step": 1,
                    "task": "错误地重复步骤1",
                    "reason": "bad",
                    "success_criteria": "bad",
                    "time_limit": "10秒",
                    "tips": ["bad"],
                }
            ],
        }

        validator = BriefValidator()
        invalid = validator.validate(bad_plan, context)
        self.assertFalse(invalid["valid"])

        repaired = BriefRepairer().repair(bad_plan, context, strategy, invalid["errors"])
        valid = validator.validate(repaired, context)
        self.assertTrue(valid["valid"], valid["errors"])
        self.assertNotIn(1, [step["source_step"] for step in repaired["steps"]])


if __name__ == "__main__":
    unittest.main()
