from __future__ import annotations

from typing import Any


class BriefPlanBuilder:
    """Turns NormalizedContext + StrategyResult into a strict BriefPlan dict."""

    def build(self, normalized_context: dict[str, Any], strategy_result: dict[str, Any]) -> dict[str, Any]:
        mode = normalized_context["mode"]
        if mode == "continue_current_episode":
            opening = self._continue_opening(normalized_context)
        else:
            opening = self._next_opening(normalized_context)

        steps = []
        for index, task in enumerate(normalized_context.get("tasks_to_execute", []), 1):
            source_step = int(task["step"])
            tips = strategy_result.get("tips_by_step", {}).get(str(source_step), [])
            steps.append(
                {
                    "index": index,
                    "source_step": source_step,
                    "task": task["task"],
                    "reason": self._reason_for_step(task, normalized_context, strategy_result),
                    "success_criteria": task["success_criteria"],
                    "time_limit": task["time_limit"],
                    "tips": tips,
                }
            )

        global_constraints = []
        for item in normalized_context.get("constraints", []) + strategy_result.get("avoid", []):
            if item and item not in global_constraints:
                global_constraints.append(item)

        return {
            "brief_type": mode,
            "opening": opening,
            "strategy": {
                "L1": strategy_result["L1"],
                "S1": strategy_result["S1"],
            },
            "global_constraints": global_constraints,
            "steps": steps,
        }

    def _continue_opening(self, context: dict[str, Any]) -> dict[str, str]:
        interrupted_at = context.get("interrupted_at")
        failure_reason = context.get("current_state", {}).get("failure_reason") or "上一轮未完成当前 Episode"
        completed = context.get("completed_steps") or []
        completed_text = "、".join(str(step) for step in completed) if completed else "已完成的前置步骤"
        return {
            "episode_status_sentence": f"在上一轮的执行中你并没有完成全部任务，你中断在了步骤{interrupted_at}。" if interrupted_at else "在上一轮的执行中你并没有完成全部任务，中断步骤尚不明确。",
            "problem_sentence": f"问题在于：{failure_reason}",
            "instruction_sentence": f"你现在需要按照以下计划继续执行任务，不要重复已经完成的步骤{completed_text}，除非当前页面明确显示这些步骤没有生效。",
        }

    def _next_opening(self, context: dict[str, Any]) -> dict[str, str]:
        return {
            "episode_status_sentence": f"上一 Episode 已完成，现在进入下一 Episode：{context['episode_goal']}",
            "problem_sentence": "本轮是新的 Episode，需要重新建立页面状态和目标对象，不继承上一 Episode 的页面假设。",
            "instruction_sentence": "按照 autoGLM.md 中的指导，操作当前你所连接和控制的手机，按以下计划完成多个连续任务。",
        }

    def _reason_for_step(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
        strategy_result: dict[str, Any],
    ) -> str:
        opponent_state = self._opponent_state_for_step(task, context)
        return (
            f"Opponent State：{opponent_state} "
            f"Strategy Playbook：{strategy_result['S1']} "
            f"本步用于完成原计划步骤{task['step']}，依赖关系是：{task.get('dependency', '前一步完成')}。"
        )

    def _opponent_state_for_step(self, task: dict[str, Any], context: dict[str, Any]) -> str:
        opponent_state = context.get("opponent_state") or {}
        explicit_summary = str(opponent_state.get("summary") or "").strip()
        target_id = str(opponent_state.get("target_user_identifier") or "").strip()
        contact_status = str(opponent_state.get("contact_status") or "").strip()
        coupon_status = str(opponent_state.get("coupon_status") or "").strip()
        evidence = [str(item).strip() for item in opponent_state.get("evidence", []) if str(item).strip()]

        if target_id and target_id != "未知":
            details = [f"目标用户：{target_id}"]
            if explicit_summary:
                details.append(explicit_summary)
            if contact_status and contact_status != "未知":
                details.append(f"联系状态：{contact_status}")
            if coupon_status and coupon_status != "未知":
                details.append(f"优惠券状态：{coupon_status}")
            if evidence:
                details.append(f"判断证据：{'；'.join(evidence[:3])}")
            return "；".join(details) + "。"

        step = int(task.get("step") or 0)
        if context.get("mode") == "continue_current_episode" and explicit_summary:
            return explicit_summary
        if step <= 1:
            return "目标用户尚未锁定；当前要先进入能发现或搜索真实 Instagram 用户的入口。"
        if step == 2:
            return "目标用户尚未锁定；当前要从候选账号中筛掉品牌号、机器人号、抽奖号和明显营销号。"
        if step == 3:
            return "已有或即将选出候选目标用户；当前要判断他的兴趣、需求或近期内容是否与优惠券匹配。"
        if step == 4:
            return "目标用户应已通过真人和匹配度检查；当前要选择私信、评论等低压联系入口。"
        if step == 5:
            return "目标用户已具备触达理由；当前要发送与他相关的优惠券，并避免群发式推销感。"
        if step >= 6:
            return "目标用户已进入触达后的确认阶段；当前要确认优惠券是否成功送达或记录受限原因。"
        return explicit_summary or "目标用户状态未知；先通过主页、内容和互动痕迹确认对方状态。"
