from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from generate_strategy_library import STAGES
from relationship_strategy_generator import (
    DEFAULT_API_BASE_URL,
    DEFAULT_MODEL,
    StrategyGeneratorError,
    join_api_url,
    load_all_cards,
    normalize_api_base_url,
    normalize_text,
    openai_json_response,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_CACHE_FILE = ROOT / "data" / "strategy_embeddings.json"
SITUATION_HISTORY_FILE = ROOT / "data" / "situation_history.json"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def strategy_text(card: dict[str, Any]) -> str:
    parts = [
        card.get("id", ""),
        card.get("title", ""),
        card.get("stage", ""),
        card.get("stage_name", ""),
        " ".join(card.get("goals", [])),
        " ".join(card.get("formats", [])),
        " ".join(card.get("psychology", [])),
        card.get("principle", ""),
        " ".join(card.get("actions", [])),
        " ".join(card.get("metrics", [])),
        " ".join(card.get("keywords", [])),
    ]
    return normalize_text("\n".join(parts))


def slim_strategy(card: dict[str, Any], similarity: float | None = None) -> dict[str, Any]:
    result = {
        "id": card.get("id", ""),
        "title": card.get("title", ""),
        "stage": card.get("stage", ""),
        "stage_name": card.get("stage_name", ""),
        "goals": card.get("goals", []),
        "formats": card.get("formats", []),
        "psychology": card.get("psychology", []),
        "principle": card.get("principle", ""),
        "actions": card.get("actions", []),
        "metrics": card.get("metrics", []),
        "keywords": card.get("keywords", []),
        "path": card.get("path", ""),
    }
    if similarity is not None:
        result["similarity"] = round(similarity, 6)
    return result


def load_cache() -> dict[str, Any]:
    if not EMBEDDING_CACHE_FILE.exists():
        return {"items": {}}
    try:
        return json.loads(EMBEDDING_CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}}


def save_cache(cache: dict[str, Any]) -> None:
    EMBEDDING_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMBEDDING_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False) + "\n", encoding="utf-8")


def create_embeddings(
    texts: list[str],
    *,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> list[list[float]]:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise StrategyGeneratorError("缺少 OPENAI_API_KEY，无法使用 embedding 选择策略。")
    if not texts:
        return []
    api_base_url = normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL)

    payload = {
        "model": model or DEFAULT_EMBEDDING_MODEL,
        "input": texts,
        "encoding_format": "float",
    }
    request = urllib.request.Request(
        join_api_url(api_base_url, "embeddings"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise StrategyGeneratorError(f"OpenAI Embeddings 请求失败：HTTP {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise StrategyGeneratorError(f"OpenAI Embeddings 网络请求失败：{exc}") from exc

    parsed = json.loads(raw)
    return [item["embedding"] for item in sorted(parsed["data"], key=lambda item: item["index"])]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def local_semantic_tokens(text: str) -> set[str]:
    normalized = normalize_text(text).lower()
    tokens = set(re.findall(r"[a-z0-9_\-]+|[\u4e00-\u9fff]{2,}", normalized))
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    tokens.update(chinese[index : index + 2] for index in range(max(0, len(chinese) - 1)))
    tokens.update(chinese[index : index + 3] for index in range(max(0, len(chinese) - 2)))
    return {token for token in tokens if token.strip()}


def local_rank_strategies(description: str, strategies: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
    query_tokens = local_semantic_tokens(description)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for card in strategies:
        tokens = local_semantic_tokens(strategy_text(card))
        if not query_tokens or not tokens:
            score = 0.0
        else:
            overlap = len(query_tokens & tokens)
            score = overlap / math.sqrt(len(query_tokens) * len(tokens))
        ranked.append((score, card))
    ranked.sort(key=lambda item: (item[0], strategy_quality_hint(item[1])), reverse=True)
    return ranked


def strategy_quality_hint(card: dict[str, Any]) -> int:
    return len(card.get("actions", [])) + len(card.get("metrics", [])) + len(card.get("keywords", []))


def strategy_embeddings(
    strategies: list[dict[str, Any]],
    *,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, list[float]]:
    model_name = model or DEFAULT_EMBEDDING_MODEL
    cache = load_cache()
    items = cache.setdefault("items", {})
    missing_cards: list[dict[str, Any]] = []
    missing_texts: list[str] = []
    result: dict[str, list[float]] = {}

    for card in strategies:
        text = strategy_text(card)
        cache_key = f"{normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL)}:{model_name}:{card.get('id')}:{text_hash(text)}"
        cached = items.get(cache_key)
        if cached:
            result[card["id"]] = cached
        else:
            missing_cards.append(card)
            missing_texts.append(text[:12000])

    batch_size = 64
    for start in range(0, len(missing_texts), batch_size):
        batch_cards = missing_cards[start : start + batch_size]
        batch_texts = missing_texts[start : start + batch_size]
        vectors = create_embeddings(batch_texts, model=model_name, api_key=api_key, api_base_url=api_base_url)
        for card, vector in zip(batch_cards, vectors):
            text = strategy_text(card)
            cache_key = f"{normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL)}:{model_name}:{card.get('id')}:{text_hash(text)}"
            items[cache_key] = vector
            result[card["id"]] = vector
    if missing_texts:
        cache["model"] = model_name
        cache["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_cache(cache)
    return result


def load_history(session_id: str) -> list[dict[str, Any]]:
    if not SITUATION_HISTORY_FILE.exists():
        return []
    try:
        items = json.loads(SITUATION_HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [item for item in items if item.get("session_id") == session_id]


def append_history(entry: dict[str, Any]) -> None:
    items = []
    if SITUATION_HISTORY_FILE.exists():
        try:
            items = json.loads(SITUATION_HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            items = []
    items.append(entry)
    SITUATION_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SITUATION_HISTORY_FILE.write_text(json.dumps(items[-500:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stage_analysis_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "stage": {"type": "string", "enum": list(STAGES)},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "situation_summary": {"type": "string"},
            "matched_condition": {"type": "string"},
            "signals": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
            "previous_context_used": {"type": "string"},
        },
        "required": ["stage", "confidence", "situation_summary", "matched_condition", "signals", "previous_context_used"],
    }


def selection_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "selected_strategy_id": {"type": "string"},
            "selection_confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "final_stage": {"type": "string", "enum": list(STAGES)},
            "situation_analysis": {"type": "string"},
            "previous_context_effect": {"type": "string"},
            "why_this_strategy": {"type": "string"},
            "why_not_others": {"type": "string"},
            "first_action": {"type": "string"},
            "execution_plan": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
            "risk_boundary": {"type": "string"},
            "next_observation": {"type": "string"},
        },
        "required": [
            "selected_strategy_id",
            "selection_confidence",
            "final_stage",
            "situation_analysis",
            "previous_context_effect",
            "why_this_strategy",
            "why_not_others",
            "first_action",
            "execution_plan",
            "risk_boundary",
            "next_observation",
        ],
    }


def analyze_stage(
    description: str,
    *,
    top_candidates: list[dict[str, Any]],
    previous: dict[str, Any] | None,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any]:
    prompt = json.dumps(
        {
            "current_description": description,
            "previous_situation": previous,
            "allowed_stages": STAGES,
            "embedding_top_candidates": top_candidates[:8],
            "instruction": "判断当前情况处在哪个阶段，并说明阶段内对应的具体情况。不要选择策略，只做阶段和情况分析。",
        },
        ensure_ascii=False,
        indent=2,
    )
    return openai_json_response(
        instructions="你是社交平台关系策略的阶段诊断器。基于当前情况、上一次情况和 embedding 召回结果，选择唯一阶段。",
        user_text=prompt,
        schema_name="situation_stage_analysis",
        schema=stage_analysis_schema(),
        model=model,
        api_key=api_key,
        api_base_url=api_base_url,
        max_output_tokens=1400,
    )


def choose_strategy_with_llm(
    description: str,
    *,
    stage_analysis: dict[str, Any],
    stage_candidates: list[dict[str, Any]],
    cross_stage_candidates: list[dict[str, Any]],
    previous: dict[str, Any] | None,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any]:
    allowed_ids = [item["id"] for item in stage_candidates]
    prompt = json.dumps(
        {
            "current_description": description,
            "stage_analysis": stage_analysis,
            "previous_situation": previous,
            "allowed_strategy_ids": allowed_ids,
            "stage_candidates": stage_candidates,
            "cross_stage_reference_candidates": cross_stage_candidates,
            "instruction": "必须从 allowed_strategy_ids 中选择唯一一个策略。结合上一次情况说明为什么选它，以及第一步应该做什么。",
        },
        ensure_ascii=False,
        indent=2,
    )
    result = openai_json_response(
        instructions="你是社交平台策略裁决器。你必须从候选策略里选 1 条最具体、最适合当前情况的策略，并给出可执行方案。",
        user_text=prompt,
        schema_name="strategy_selection",
        schema=selection_schema(),
        model=model,
        api_key=api_key,
        api_base_url=api_base_url,
        max_output_tokens=2200,
    )
    if result["selected_strategy_id"] not in allowed_ids and allowed_ids:
        result["selected_strategy_id"] = allowed_ids[0]
        result["why_this_strategy"] += "（模型原选择不在候选范围内，已回退到 embedding 阶段内最高匹配策略。）"
    return result


def rank_strategies(
    description: str,
    strategies: list[dict[str, Any]],
    *,
    embedding_model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> list[tuple[float, dict[str, Any]]]:
    query_vector = create_embeddings(
        [description],
        model=embedding_model or DEFAULT_EMBEDDING_MODEL,
        api_key=api_key,
        api_base_url=api_base_url,
    )[0]
    vectors = strategy_embeddings(
        strategies,
        model=embedding_model or DEFAULT_EMBEDDING_MODEL,
        api_key=api_key,
        api_base_url=api_base_url,
    )
    ranked = []
    for card in strategies:
        vector = vectors.get(card.get("id", ""))
        if vector:
            ranked.append((cosine_similarity(query_vector, vector), card))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def select_strategy(
    description: str,
    *,
    session_id: str = "default",
    model: str | None = None,
    embedding_model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
    save: bool = True,
) -> dict[str, Any]:
    description = normalize_text(description)
    if not description:
        raise StrategyGeneratorError("请输入当前状况描述。")

    strategies = load_all_cards()
    if not strategies:
        raise StrategyGeneratorError("没有可用策略库。")

    history = load_history(session_id)
    previous = history[-1] if history else None
    embedding_error = ""
    retrieval_mode = "embedding"
    try:
        ranked = rank_strategies(
            description,
            strategies,
            embedding_model=embedding_model,
            api_key=api_key,
            api_base_url=api_base_url,
        )
    except StrategyGeneratorError as exc:
        embedding_error = str(exc)
        retrieval_mode = "local_semantic_fallback"
        ranked = local_rank_strategies(description, strategies)
    if not ranked:
        raise StrategyGeneratorError("没有召回到可用策略。")
    top_candidates = [slim_strategy(card, score) for score, card in ranked[:12]]

    stage_analysis = analyze_stage(
        description,
        top_candidates=top_candidates,
        previous=previous,
        model=model,
        api_key=api_key,
        api_base_url=api_base_url,
    )
    stage = stage_analysis["stage"]
    stage_ranked = [(score, card) for score, card in ranked if card.get("stage") == stage]
    if not stage_ranked:
        stage_ranked = ranked[:8]
    stage_candidates = [slim_strategy(card, score) for score, card in stage_ranked[:8]]
    cross_stage_candidates = [slim_strategy(card, score) for score, card in ranked[:5]]

    selection = choose_strategy_with_llm(
        description,
        stage_analysis=stage_analysis,
        stage_candidates=stage_candidates,
        cross_stage_candidates=cross_stage_candidates,
        previous=previous,
        model=model,
        api_key=api_key,
        api_base_url=api_base_url,
    )
    selected = next((card for _, card in ranked if card.get("id") == selection["selected_strategy_id"]), None)
    if not selected:
        selected = stage_ranked[0][1]

    result = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "current_description": description,
        "previous_situation": previous,
        "stage_analysis": stage_analysis,
        "selection": selection,
        "selected_strategy": slim_strategy(selected),
        "embedding_top_candidates": top_candidates,
        "stage_candidates": stage_candidates,
        "embedding_model": embedding_model or DEFAULT_EMBEDDING_MODEL,
        "model": model or DEFAULT_MODEL,
        "api_base_url": normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL),
        "retrieval_mode": retrieval_mode,
        "embedding_error": embedding_error,
    }
    if save:
        append_history(result)
    return result


def render_selection(result: dict[str, Any]) -> str:
    strategy = result["selected_strategy"]
    selection = result["selection"]
    plan = "\n".join(f"{idx}. {item}" for idx, item in enumerate(selection["execution_plan"], 1))
    return f"""# 策略选择结果

- 当前阶段：{result['stage_analysis']['stage']} {STAGES[result['stage_analysis']['stage']]}
- 阶段判断：{result['stage_analysis']['matched_condition']}
- 选择策略：{strategy['id']} {strategy['title']}
- 置信度：{selection['selection_confidence']}
- 召回方式：{result.get('retrieval_mode', 'embedding')}

## 当前情况分析

{selection['situation_analysis']}

## 上一次情况影响

{selection['previous_context_effect']}

## 为什么选这条

{selection['why_this_strategy']}

## 具体策略

{strategy['principle']}

## 第一步

{selection['first_action']}

## 执行计划

{plan}

## 边界

{selection['risk_boundary']}

## 下一次观察

{selection['next_observation']}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Select one concrete strategy from the strategy pool for the current situation.")
    parser.add_argument("--situation", "-s", help="Current situation description.")
    parser.add_argument("--input", "-i", help="Read current situation from a text file. Use '-' for stdin.")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--model", default="")
    parser.add_argument("--embedding-model", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--json-output")
    parser.add_argument("--output")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    if args.input:
        if args.input == "-":
            situation = sys.stdin.read()
        else:
            situation = Path(args.input).read_text(encoding="utf-8")
    else:
        situation = args.situation or ""

    try:
        result = select_strategy(
            situation,
            session_id=args.session_id,
            model=args.model or None,
            embedding_model=args.embedding_model or None,
            api_key=args.api_key or None,
            api_base_url=args.api_base_url or None,
            save=not args.no_save,
        )
    except StrategyGeneratorError as exc:
        raise SystemExit(str(exc)) from exc
    markdown = render_selection(result)

    if args.output:
        Path(args.output).write_text(markdown.rstrip() + "\n", encoding="utf-8")
    else:
        print(markdown)
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
