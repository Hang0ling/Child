from __future__ import annotations

from typing import Any

from .brief_plan_builder import BriefPlanBuilder
from .context_builder import ContextBuilder
from .decider import ControlFlowDecider
from .renderer import BriefRenderer
from .repairer import BriefRepairer
from .strategy_memory import StrategyMemoryComposer
from .validator import BriefValidator


class DecisionCoreOrchestrator:
    """End-to-end MVP orchestrator."""

    def __init__(self, max_repair_attempts: int = 2) -> None:
        self.max_repair_attempts = max_repair_attempts
        self.decider = ControlFlowDecider()
        self.context_builder = ContextBuilder()
        self.strategy_memory_composer = StrategyMemoryComposer()
        self.brief_plan_builder = BriefPlanBuilder()
        self.validator = BriefValidator()
        self.repairer = BriefRepairer()
        self.renderer = BriefRenderer()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        judge_result = payload.get("judge_result") or {}
        control_decision = self.decider.decide(judge_result)

        normalized_context = self.context_builder.build(
            control_decision,
            judge_result=judge_result,
            execution_result=payload.get("execution_result") or {},
            act_log=payload.get("act_log") or [],
            history_context=payload.get("history_context") or {},
            run_plan=payload.get("run_plan") or {},
            environment_settings=payload.get("environment_settings") or {},
        )

        strategy_result = self.strategy_memory_composer.compose(
            normalized_context,
            strategy_playbook=payload.get("strategy_playbook") or [],
            experience_memory=payload.get("experience_memory") or [],
        )

        brief_plan = self.brief_plan_builder.build(normalized_context, strategy_result)
        repair_history = []
        validation = self.validator.validate(brief_plan, normalized_context)
        attempts = 0
        while not validation["valid"] and attempts < self.max_repair_attempts:
            attempts += 1
            repair_history.append({"attempt": attempts, "errors": validation["errors"]})
            brief_plan = self.repairer.repair(
                brief_plan,
                normalized_context,
                strategy_result,
                validation["errors"],
            )
            validation = self.validator.validate(brief_plan, normalized_context)

        if not validation["valid"]:
            return {
                "ok": False,
                "control_decision": control_decision,
                "normalized_context": normalized_context,
                "strategy_result": strategy_result,
                "brief_plan": brief_plan,
                "validation": validation,
                "repair_history": repair_history,
                "execution_brief": None,
            }

        return {
            "ok": True,
            "control_decision": control_decision,
            "normalized_context": normalized_context,
            "strategy_result": strategy_result,
            "brief_plan": brief_plan,
            "validation": validation,
            "repair_history": repair_history,
            "execution_brief": self.renderer.render(brief_plan),
        }
