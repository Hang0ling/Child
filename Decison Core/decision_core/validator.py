from __future__ import annotations

from typing import Any


class BriefValidator:
    """Validates BriefPlan before rendering."""

    REQUIRED_OPENING = ["episode_status_sentence", "problem_sentence", "instruction_sentence"]
    REQUIRED_STEP_FIELDS = ["task", "reason", "success_criteria", "time_limit", "tips"]

    def validate(self, brief_plan: dict[str, Any], normalized_context: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []

        if brief_plan.get("brief_type") != normalized_context.get("mode"):
            errors.append("brief_type does not match normalized_context.mode")

        opening = brief_plan.get("opening") or {}
        for key in self.REQUIRED_OPENING:
            if not opening.get(key):
                errors.append(f"missing opening.{key}")

        strategy = brief_plan.get("strategy") or {}
        if not strategy.get("L1"):
            errors.append("missing strategy.L1")
        if not strategy.get("S1"):
            errors.append("missing strategy.S1")

        if not brief_plan.get("global_constraints"):
            errors.append("missing global_constraints")

        steps = brief_plan.get("steps") or []
        if not steps:
            errors.append("missing steps")

        for expected_index, step in enumerate(steps, start=1):
            if step.get("index") != expected_index:
                errors.append(f"step index not continuous at {expected_index}")
            for field in self.REQUIRED_STEP_FIELDS:
                if field not in step or step.get(field) in (None, "", []):
                    errors.append(f"step {expected_index} missing {field}")
            if not isinstance(step.get("tips"), list):
                errors.append(f"step {expected_index} tips must be a list")

        mode = normalized_context.get("mode")
        rendered_opening = " ".join(str(opening.get(key, "")) for key in self.REQUIRED_OPENING)

        if mode == "continue_current_episode":
            skip_steps = set(normalized_context.get("skip_steps", []))
            source_steps = {step.get("source_step") for step in steps}
            repeated = sorted(step for step in skip_steps.intersection(source_steps) if step is not None)
            if repeated:
                errors.append(f"brief includes skipped completed steps: {repeated}")
            if not normalized_context.get("interrupted_at"):
                errors.append("continue mode missing interrupted_at")
            if "中断" not in rendered_opening:
                errors.append("continue opening must mention interruption")
            if "问题" not in rendered_opening:
                errors.append("continue opening must mention problem")
            if "不要重复" not in rendered_opening:
                errors.append("continue opening must mention not repeating completed steps")

        if mode == "next_episode":
            if "上一 Episode 已完成" not in rendered_opening:
                errors.append("next opening must mention previous episode completed")
            if "下一 Episode" not in rendered_opening:
                errors.append("next opening must mention next episode")
            if "不继承" not in rendered_opening:
                errors.append("next opening must mention not inheriting previous page assumptions")

        return {"valid": not errors, "errors": errors}
