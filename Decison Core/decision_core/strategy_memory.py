from __future__ import annotations

import re
from typing import Any

from .schemas import as_list, text_join


class StrategyMemoryComposer:
    """Matches playbook items and maps memory tips onto concrete steps."""

    def compose(
        self,
        normalized_context: dict[str, Any],
        *,
        strategy_playbook: list[dict[str, Any]] | dict[str, Any] | None = None,
        experience_memory: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        playbook_items = self._normalize_items(strategy_playbook)
        memory_items = self._normalize_items(experience_memory)
        matched = self._match_playbook(normalized_context, playbook_items)

        mode = normalized_context["mode"]
        episode_goal = normalized_context["episode_goal"]
        is_instagram = "instagram" in episode_goal.lower() or "优惠券" in episode_goal

        if mode == "continue_current_episode":
            l1 = "恢复当前 Episode 的未完成部分，最大化续跑成功率"
            s1 = "从中断点继续，先确认当前页面状态；如果页面一致，直接完成中断步骤；如果页面不一致，只做最小路径恢复"
            why = "上一轮已经完成部分步骤，重复执行会浪费时间并可能破坏状态。"
            avoid = ["不要重复已完成步骤", "不要无根据返回首页", "不要探索无关页面"]
            fallback = [
                "如果当前页面不是中断步骤所需页面，先用最短路径恢复到该步骤。",
                "如果关键按钮不可见，优先滑动查找，而不是退出重进。",
                "如果发现前置状态丢失，再重新执行必要的最小前置步骤。",
            ]
        elif is_instagram:
            l1 = "找到真实且匹配的 Instagram 对象，并用低压方式完成联系与优惠券推送"
            s1 = "先验证真人和兴趣匹配，再选择私信或评论等最短可用联系入口；优惠券必须带个性化适配理由"
            why = "Episode 的核心不是随便发送优惠券，而是找到合适的人、建立最低限度信任，并避免骚扰式触达。"
            avoid = ["不要联系品牌号、机器人号或明显营销号", "不要群发模板话术", "不要把优惠券发给明显不匹配的人"]
            fallback = [
                "如果无法私信，尝试通过评论或关注后的可见入口建立联系。",
                "如果目标用户不匹配，立即换人，不要勉强发送。",
                "如果发送受限，记录目标、原因和下一步可恢复路径。",
            ]
        else:
            l1 = "快速建立新 Episode 的执行路径并完成主线目标"
            s1 = "按新 Run Plan 顺序执行；如果当前页面来自上一 Episode，先用最短路径进入新目标页面"
            why = "上一轮已完成，应避免把上一 Episode 的状态假设带入新 Episode。"
            avoid = ["不要继续上一 Episode 的残留任务", "不要基于上一页面假设执行新任务"]
            fallback = [
                "如果目标入口不可见，优先使用搜索、首页入口或返回主页面。",
                "如果环境状态不一致，先恢复到新 Episode 所需起点。",
            ]

        if matched:
            top = matched[0]
            l1 = str(top.get("L1") or top.get("l1") or l1)
            s1 = str(top.get("S1") or top.get("s1") or top.get("principle") or s1)
            why = text_join(why, f"匹配 Strategy Playbook：{top.get('title') or top.get('id') or '未命名策略'}。")

        tips_by_step: dict[str, list[str]] = {}
        for step in normalized_context.get("tasks_to_execute", []):
            tips_by_step[str(step["step"])] = self._tips_for_step(step, memory_items, normalized_context)

        global_tips = self._global_tips(normalized_context, memory_items)

        return {
            "L1": l1,
            "S1": s1,
            "why": why,
            "avoid": avoid,
            "fallback_policy": fallback,
            "matched_strategies": matched[:3],
            "tips_by_step": tips_by_step,
            "global_tips": global_tips,
        }

    def _normalize_items(self, value: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, dict):
            if isinstance(value.get("items"), list):
                return [item for item in value["items"] if isinstance(item, dict)]
            if isinstance(value.get("memories"), list):
                return [item for item in value["memories"] if isinstance(item, dict)]
            if isinstance(value.get("strategies"), list):
                return [item for item in value["strategies"] if isinstance(item, dict)]
            return [value]
        return [item for item in value if isinstance(item, dict)]

    def _match_playbook(self, context: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query = self._tokens(
            text_join(
                context.get("episode_goal"),
                context.get("mode"),
                " ".join(step.get("task", "") for step in context.get("tasks_to_execute", [])),
                context.get("current_state", {}).get("failure_reason"),
            )
        )
        scored = []
        for item in items:
            haystack = self._tokens(
                text_join(
                    item.get("id"),
                    item.get("title"),
                    item.get("stage"),
                    item.get("principle"),
                    item.get("L1"),
                    item.get("S1"),
                    " ".join(str(tag) for tag in as_list(item.get("tags") or item.get("keywords"))),
                )
            )
            score = len(query & haystack)
            if item.get("mode") == context.get("mode"):
                score += 3
            if score:
                scored.append((score, item))
        return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)]

    def _tips_for_step(
        self,
        step: dict[str, Any],
        memories: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[str]:
        query = self._tokens(text_join(step.get("task"), step.get("success_criteria")))
        scored = []
        for item in memories:
            text = str(item.get("tip") or item.get("text") or item.get("content") or "")
            haystack = self._tokens(text_join(text, " ".join(str(tag) for tag in as_list(item.get("tags")))))
            score = len(query & haystack)
            if item.get("step") == step.get("step") or item.get("source_step") == step.get("step"):
                score += 5
            if score and text:
                scored.append((score, text))
        tips = [text for _, text in sorted(scored, key=lambda pair: pair[0], reverse=True)[:2]]
        if tips:
            return tips

        task = step.get("task", "")
        if "真人" in task or "用户" in task:
            return ["优先选择有真人头像、自然简介、近期帖子和正常互动痕迹的用户；避开品牌号、抽奖号和明显机器人号。"]
        if "优惠券" in task:
            return ["发送优惠券时必须说明它为什么适合对方，避免只丢链接或兑换码。"]
        if "私信" in task or "联系" in task:
            return ["先用一句个性化低压开场，给对方选择权，不要像群发销售话术。"]
        if context["mode"] == "continue_current_episode":
            return ["先读取当前页面标题、按钮和已填写内容，再决定是否需要恢复路径。"]
        return ["优先完成主线动作；非必要弹窗只有在阻塞任务时才处理。"]

    def _global_tips(self, context: dict[str, Any], memories: list[dict[str, Any]]) -> list[str]:
        global_tips = [
            str(item.get("tip") or item.get("text") or item.get("content"))
            for item in memories
            if item.get("global") and (item.get("tip") or item.get("text") or item.get("content"))
        ][:3]
        if global_tips:
            return global_tips
        if context["mode"] == "continue_current_episode":
            return ["只在页面明确显示前置状态丢失时，才允许重复已完成步骤。"]
        return ["新 Episode 不继承上一 Episode 的页面假设；先确认当前页面，再执行主线。"]

    def _tokens(self, text: str) -> set[str]:
        lowered = text.lower()
        ascii_tokens = set(re.findall(r"[a-z0-9_]+", lowered))
        cjk_tokens: set[str] = set()
        for chunk in re.findall(r"[\u4e00-\u9fff]+", lowered):
            if len(chunk) >= 2:
                cjk_tokens.add(chunk)
            for size in (2, 3, 4):
                for start in range(0, max(len(chunk) - size + 1, 0)):
                    cjk_tokens.add(chunk[start : start + size])
        return ascii_tokens | cjk_tokens
