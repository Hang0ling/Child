from __future__ import annotations

from copy import deepcopy
from typing import Any

from .brief_plan_builder import BriefPlanBuilder


class BriefRepairer:
    """Repairs BriefPlan deterministically where possible."""

    def __init__(self) -> None:
        self.builder = BriefPlanBuilder()

    def repair(
        self,
        brief_plan: dict[str, Any],
        normalized_context: dict[str, Any],
        strategy_result: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        repaired = deepcopy(brief_plan) if brief_plan else {}
        baseline = self.builder.build(normalized_context, strategy_result)

        repaired["brief_type"] = normalized_context["mode"]
        repaired.setdefault("opening", {})
        for key, value in baseline["opening"].items():
            if not repaired["opening"].get(key) or self._opening_needs_mode_fix(errors):
                repaired["opening"][key] = value

        repaired.setdefault("strategy", {})
        repaired["strategy"]["L1"] = repaired["strategy"].get("L1") or strategy_result["L1"]
        repaired["strategy"]["S1"] = repaired["strategy"].get("S1") or strategy_result["S1"]

        if not repaired.get("global_constraints"):
            repaired["global_constraints"] = baseline["global_constraints"]
        else:
            for item in baseline["global_constraints"]:
                if item not in repaired["global_constraints"]:
                    repaired["global_constraints"].append(item)

        skip_steps = set(normalized_context.get("skip_steps", []))
        steps = repaired.get("steps") or baseline["steps"]
        clean_steps = []
        for step in steps:
            if normalized_context["mode"] == "continue_current_episode" and step.get("source_step") in skip_steps:
                continue
            clean_steps.append(step)
        if not clean_steps:
            clean_steps = baseline["steps"]

        baseline_by_source = {step["source_step"]: step for step in baseline["steps"]}
        for index, step in enumerate(clean_steps, 1):
            source_step = step.get("source_step") or step.get("index") or index
            base = baseline_by_source.get(source_step, baseline["steps"][min(index - 1, len(baseline["steps"]) - 1)])
            step["index"] = index
            step["source_step"] = source_step
            for field in ["task", "reason", "success_criteria", "time_limit"]:
                if not step.get(field):
                    step[field] = base[field]
            if not step.get("tips") or not isinstance(step.get("tips"), list):
                step["tips"] = base.get("tips") or ["按当前页面状态执行最短可行路径。"]
        repaired["steps"] = clean_steps

        return repaired

    def _opening_needs_mode_fix(self, errors: list[str]) -> bool:
        return any("opening must mention" in error for error in errors)
