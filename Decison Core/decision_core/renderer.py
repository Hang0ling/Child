from __future__ import annotations

from typing import Any


class BriefRenderer:
    """Template-only renderer for final Execution Brief."""

    def render(self, brief_plan: dict[str, Any]) -> str:
        opening = brief_plan["opening"]
        strategy = brief_plan["strategy"]
        lines = [
            "【Execution Brief】",
            "",
            opening["episode_status_sentence"],
            opening["problem_sentence"],
            opening["instruction_sentence"],
            "",
            "当前策略：",
            f"L1：{strategy['L1']}",
            f"S1：{strategy['S1']}",
            "",
            "全局约束：",
        ]
        for constraint in brief_plan.get("global_constraints", []):
            lines.append(f"- {constraint}")
        lines.append("")

        for step in brief_plan.get("steps", []):
            tips = "；".join(step.get("tips") or ["无"])
            lines.extend(
                [
                    f"{step['index']}. {step['task']}",
                    f"这么做的原因：{step['reason']}",
                    f"检验标准：{step['success_criteria']}",
                    f"时间限制：{step['time_limit']}",
                    f"Tips：{tips}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"
