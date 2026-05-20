from __future__ import annotations

from typing import Any

from .schemas import int_or_none


class ControlFlowDecider:
    """Rule-based decision for continue vs next episode."""

    SUCCESS_STATUSES = {"success", "completed", "done"}
    CONTINUE_STATUSES = {"partial", "failed_recoverable", "interrupted", "incomplete", "failed"}

    def decide(self, judge_result: dict[str, Any] | None) -> dict[str, Any]:
        judge_result = judge_result or {}
        status = str(judge_result.get("status", "")).strip().lower()

        if status in self.SUCCESS_STATUSES:
            return {
                "mode": "next_episode",
                "reason": "previous episode completed",
                "resume_from_step": None,
            }

        resume_from_step = int_or_none(
            judge_result.get("resume_from_step")
            or judge_result.get("interrupted_at")
            or judge_result.get("failed_step")
        )

        if status in self.CONTINUE_STATUSES:
            return {
                "mode": "continue_current_episode",
                "reason": judge_result.get("failed_reason") or judge_result.get("reason") or "",
                "resume_from_step": resume_from_step,
            }

        return {
            "mode": "continue_current_episode",
            "reason": "default to continuing current episode when uncertain",
            "resume_from_step": resume_from_step,
        }
