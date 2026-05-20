from __future__ import annotations

from typing import Any

from .schemas import (
    DEFAULT_INSTAGRAM_EPISODE_GOAL,
    DEFAULT_INSTAGRAM_STEPS,
    as_dict,
    as_list,
    extract_steps,
    int_or_none,
    normalize_step,
    text_join,
    unique_ints,
)


class ContextBuilder:
    """Builds the shared NormalizedContext shape for both branches."""

    def build(
        self,
        control_decision: dict[str, Any],
        *,
        judge_result: dict[str, Any] | None = None,
        execution_result: dict[str, Any] | None = None,
        act_log: list[dict[str, Any]] | None = None,
        history_context: dict[str, Any] | None = None,
        run_plan: dict[str, Any] | None = None,
        environment_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mode = control_decision["mode"]
        if mode == "next_episode":
            return self._build_next_context(
                control_decision,
                judge_result=judge_result or {},
                history_context=history_context or {},
                run_plan=run_plan or {},
                environment_settings=environment_settings or {},
            )
        return self._build_continue_context(
            control_decision,
            judge_result=judge_result or {},
            execution_result=execution_result or {},
            act_log=act_log or [],
            history_context=history_context or {},
            run_plan=run_plan or {},
            environment_settings=environment_settings or {},
        )

    def _build_continue_context(
        self,
        control_decision: dict[str, Any],
        *,
        judge_result: dict[str, Any],
        execution_result: dict[str, Any],
        act_log: list[dict[str, Any]],
        history_context: dict[str, Any],
        run_plan: dict[str, Any],
        environment_settings: dict[str, Any],
    ) -> dict[str, Any]:
        episode = self._current_episode(history_context, run_plan)
        episode_id = str(episode.get("episode_id") or episode.get("id") or history_context.get("episode_id") or "current_episode")
        episode_goal = str(episode.get("episode_goal") or episode.get("goal") or history_context.get("episode_goal") or DEFAULT_INSTAGRAM_EPISODE_GOAL)

        interrupted_at = int_or_none(
            control_decision.get("resume_from_step")
            or judge_result.get("interrupted_at")
            or execution_result.get("interrupted_at")
            or history_context.get("interrupted_at")
        )

        completed_steps = unique_ints(
            execution_result.get("completed_steps")
            or judge_result.get("completed_steps")
            or history_context.get("completed_steps")
        )
        if not completed_steps and interrupted_at and interrupted_at > 1:
            completed_steps = list(range(1, interrupted_at))

        all_steps = extract_steps(episode) or [normalize_step(step, idx) for idx, step in enumerate(DEFAULT_INSTAGRAM_STEPS, 1)]
        start_step = interrupted_at or (max(completed_steps) + 1 if completed_steps else 1)
        tasks_to_execute = [
            step for step in all_steps if step["step"] not in completed_steps and step["step"] >= start_step
        ]
        if not tasks_to_execute:
            tasks_to_execute = [
                normalize_step(
                    {
                        "step": start_step,
                        "task": f"确认并完成当前 Episode 的步骤{start_step}",
                        "success_criteria": f"页面或结果明确显示步骤{start_step}已经完成。",
                        "time_limit": "60秒",
                        "dependency": "已完成前置步骤",
                    },
                    start_step,
                )
            ]

        last_successful_action, last_failed_action = self._last_actions(act_log)
        current_screen = (
            history_context.get("current_screen_or_state")
            or execution_result.get("current_screen_or_state")
            or environment_settings.get("current_screen_or_state")
            or "未知，需要执行器基于当前手机状态判断"
        )
        failure_reason = (
            judge_result.get("failed_reason")
            or control_decision.get("reason")
            or execution_result.get("failed_reason")
            or "上一轮未完成当前 Episode"
        )

        constraints = [
            f"不要重复步骤{self._range_label(completed_steps)}，除非当前页面明确显示这些步骤没有生效。",
            "优先从当前页面继续，不要无根据返回首页。",
            "只做与当前 Episode 相关的操作。",
            "遵守 autoGLM.md 的手机操作规范。",
        ]
        constraints.extend(str(item) for item in as_list(history_context.get("constraints")))

        return {
            "mode": "continue_current_episode",
            "episode_id": episode_id,
            "episode_goal": episode_goal,
            "interrupted_at": interrupted_at,
            "completed_steps": completed_steps,
            "skip_steps": completed_steps[:],
            "tasks_to_execute": tasks_to_execute,
            "current_state": {
                "summary": text_join(
                    f"上一轮已完成步骤{self._range_label(completed_steps)}。" if completed_steps else "",
                    f"中断在步骤{interrupted_at}。" if interrupted_at else "当前中断步骤不明确。",
                ),
                "current_screen_or_state": str(current_screen),
                "failure_reason": str(failure_reason),
                "last_successful_action": last_successful_action,
                "last_failed_action": last_failed_action,
            },
            "opponent_state": self._opponent_state(
                history_context=history_context,
                execution_result=execution_result,
                run_plan=run_plan,
                episode=episode,
                fallback_summary="目标用户已经被选择并完成前置触达动作，当前需要确认优惠券发送结果和记录触达方式。",
            ),
            "constraints": self._dedupe(constraints),
            "risks": self._dedupe(
                [
                    "重复前置步骤可能导致状态重置或浪费时间。",
                    "如果当前页面状态不一致，需要先做最小恢复。",
                ]
                + [str(item) for item in as_list(history_context.get("risks"))]
            ),
            "unknowns": self._dedupe(
                [
                    f"当前手机页面是否仍停留在步骤{interrupted_at}所需页面。" if interrupted_at else "当前准确中断步骤未知。",
                ]
                + [str(item) for item in as_list(history_context.get("unknowns"))]
            ),
        }

    def _build_next_context(
        self,
        control_decision: dict[str, Any],
        *,
        judge_result: dict[str, Any],
        history_context: dict[str, Any],
        run_plan: dict[str, Any],
        environment_settings: dict[str, Any],
    ) -> dict[str, Any]:
        episode = self._next_episode(run_plan)
        episode_id = str(episode.get("episode_id") or episode.get("id") or run_plan.get("episode_id") or "next_episode")
        episode_goal = str(episode.get("episode_goal") or episode.get("goal") or run_plan.get("episode_goal") or DEFAULT_INSTAGRAM_EPISODE_GOAL)
        tasks_to_execute = extract_steps(episode) or [normalize_step(step, idx) for idx, step in enumerate(DEFAULT_INSTAGRAM_STEPS, 1)]

        constraints = [
            "不要继承上一 Episode 的页面假设。",
            "如果当前手机停留在上一 Episode 的残留页面，先用最短路径进入新目标页面。",
            "遵守 autoGLM.md 的手机操作规范。",
            "只处理与新 Episode 目标相关的页面、弹窗和通知。",
        ]
        constraints.extend(str(item) for item in as_list(run_plan.get("constraints")))

        return {
            "mode": "next_episode",
            "episode_id": episode_id,
            "episode_goal": episode_goal,
            "interrupted_at": None,
            "completed_steps": [],
            "skip_steps": [],
            "tasks_to_execute": tasks_to_execute,
            "current_state": {
                "summary": "上一 Episode 已完成，现在开始新 Episode。",
                "current_screen_or_state": str(
                    environment_settings.get("current_screen_or_state")
                    or "未知，需要执行器基于当前手机状态判断"
                ),
                "failure_reason": "",
                "last_successful_action": str(history_context.get("last_successful_action") or judge_result.get("last_successful_action") or ""),
                "last_failed_action": "",
            },
            "opponent_state": self._opponent_state(
                history_context=history_context,
                execution_result={},
                run_plan=run_plan,
                episode=episode,
                fallback_summary="目标用户尚未锁定，需要先找到真人候选人，再判断是否适合收到当前优惠券。",
            ),
            "constraints": self._dedupe(constraints),
            "risks": self._dedupe(
                [
                    "当前手机可能停留在上一 Episode 的页面。",
                    "目标用户可能不是真人、不可联系，或优惠券与其需求不匹配。",
                    "Instagram 可能限制陌生私信，需要使用评论、关注或记录失败原因作为替代。",
                ]
                + [str(item) for item in as_list(run_plan.get("risks"))]
            ),
            "unknowns": self._dedupe(
                [
                    "当前手机初始页面状态。",
                    "当前 Instagram 账号是否已登录且具备私信权限。",
                ]
                + [str(item) for item in as_list(run_plan.get("unknowns"))]
            ),
        }

    def _current_episode(self, history_context: dict[str, Any], run_plan: dict[str, Any]) -> dict[str, Any]:
        return (
            as_dict(history_context.get("current_episode"))
            or as_dict(run_plan.get("current_episode"))
            or self._next_episode(run_plan)
            or {}
        )

    def _next_episode(self, run_plan: dict[str, Any]) -> dict[str, Any]:
        if isinstance(run_plan.get("next_episode"), dict):
            return run_plan["next_episode"]
        episodes = [as_dict(item) for item in as_list(run_plan.get("episodes")) if isinstance(item, dict)]
        for episode in episodes:
            if str(episode.get("status", "")).lower() in {"pending", "next", ""}:
                return episode
        return episodes[0] if episodes else as_dict(run_plan)

    def _last_actions(self, act_log: list[dict[str, Any]]) -> tuple[str, str]:
        last_success = ""
        last_failed = ""
        for item in act_log:
            status = str(item.get("status", "")).lower()
            action = str(item.get("action") or item.get("summary") or "")
            if status in {"success", "completed", "done"} and action:
                last_success = action
            if status in {"failed", "error", "interrupted"} and action:
                last_failed = action
        return last_success, last_failed

    def _opponent_state(
        self,
        *,
        history_context: dict[str, Any],
        execution_result: dict[str, Any],
        run_plan: dict[str, Any],
        episode: dict[str, Any],
        fallback_summary: str,
    ) -> dict[str, Any]:
        raw = (
            as_dict(history_context.get("opponent_state"))
            or as_dict(history_context.get("target_user_state"))
            or as_dict(execution_result.get("opponent_state"))
            or as_dict(execution_result.get("target_user_state"))
            or as_dict(episode.get("opponent_state"))
            or as_dict(episode.get("target_user_state"))
            or as_dict(run_plan.get("opponent_state"))
            or as_dict(run_plan.get("target_user_state"))
        )
        summary = str(raw.get("summary") or fallback_summary)
        return {
            "summary": summary,
            "target_user_identifier": str(raw.get("target_user_identifier") or raw.get("username") or raw.get("handle") or "未知"),
            "evidence": [str(item) for item in as_list(raw.get("evidence"))],
            "contact_status": str(raw.get("contact_status") or "未知"),
            "coupon_status": str(raw.get("coupon_status") or "未知"),
            "unknowns": [str(item) for item in as_list(raw.get("unknowns"))],
        }

    def _range_label(self, steps: list[int]) -> str:
        if not steps:
            return "无"
        if steps == list(range(min(steps), max(steps) + 1)):
            return f"{min(steps)}-{max(steps)}" if len(steps) > 1 else str(steps[0])
        return "、".join(str(step) for step in steps)

    def _dedupe(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            clean = str(item).strip()
            if clean and clean not in result:
                result.append(clean)
        return result
