from __future__ import annotations

from copy import deepcopy
from typing import Any


BRIEF_TYPES = {"continue_current_episode", "next_episode"}


DEFAULT_INSTAGRAM_EPISODE_GOAL = "找到一个 Instagram 上的真人，和他取得联系，并给他推送一个适合他的优惠券。"


DEFAULT_INSTAGRAM_STEPS = [
    {
        "step": 1,
        "task": "打开或切换到 Instagram，并确认当前处于可搜索或可浏览用户的入口。",
        "success_criteria": "看到 Instagram 主界面、搜索入口、Explore 页面或可进入用户主页的页面。",
        "time_limit": "30秒",
        "dependency": "无",
    },
    {
        "step": 2,
        "task": "找到一个看起来是真人的 Instagram 用户，而不是品牌号、机器人号或明显营销号。",
        "success_criteria": "目标用户主页有真人头像、自然个人简介、近期真实动态或正常互动痕迹。",
        "time_limit": "90秒",
        "dependency": "步骤1完成",
    },
    {
        "step": 3,
        "task": "判断该用户是否适合收到当前优惠券。",
        "success_criteria": "能从主页内容、简介、帖子或互动痕迹判断优惠券与他的兴趣或需求相关。",
        "time_limit": "60秒",
        "dependency": "步骤2完成",
    },
    {
        "step": 4,
        "task": "用低压、个性化的方式和该用户取得联系。",
        "success_criteria": "成功进入私信、评论或其他可联系入口，并发出自然、非骚扰式的第一句话。",
        "time_limit": "90秒",
        "dependency": "步骤3完成",
    },
    {
        "step": 5,
        "task": "向该用户推送适合他的优惠券，并说明为什么这张优惠券和他相关。",
        "success_criteria": "优惠券信息已发送，且包含简短适配理由、使用方式或下一步行动。",
        "time_limit": "60秒",
        "dependency": "步骤4完成",
    },
    {
        "step": 6,
        "task": "确认发送结果并记录目标用户和触达方式。",
        "success_criteria": "能明确判断消息/评论已发出，或记录因权限限制无法发送的原因。",
        "time_limit": "30秒",
        "dependency": "步骤5完成",
    },
]


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def unique_ints(values: Any) -> list[int]:
    result: list[int] = []
    for value in as_list(values):
        parsed = int_or_none(value)
        if parsed is not None and parsed not in result:
            result.append(parsed)
    return sorted(result)


def text_join(*parts: Any) -> str:
    clean = [str(part).strip() for part in parts if str(part or "").strip()]
    return " ".join(clean)


def copy_json(value: Any) -> Any:
    return deepcopy(value)


def normalize_step(raw: dict[str, Any], fallback_step: int) -> dict[str, Any]:
    step_number = int_or_none(raw.get("step") or raw.get("source_step") or raw.get("index")) or fallback_step
    task = str(raw.get("task") or raw.get("title") or raw.get("description") or f"完成步骤{step_number}").strip()
    return {
        "step": step_number,
        "task": task,
        "success_criteria": str(
            raw.get("success_criteria")
            or raw.get("check")
            or raw.get("done_when")
            or "该步骤的页面状态、任务结果或外部反馈明确显示已经完成。"
        ).strip(),
        "time_limit": str(raw.get("time_limit") or raw.get("timeout") or "60秒").strip(),
        "dependency": str(raw.get("dependency") or raw.get("depends_on") or "前一步完成").strip(),
    }


def extract_steps(container: dict[str, Any]) -> list[dict[str, Any]]:
    raw_steps = (
        container.get("steps")
        or container.get("tasks_to_execute")
        or container.get("tasks")
        or container.get("plan")
        or []
    )
    return [normalize_step(as_dict(raw), index) for index, raw in enumerate(as_list(raw_steps), 1)]
