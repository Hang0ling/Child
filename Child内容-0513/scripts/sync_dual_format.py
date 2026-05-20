#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def render_block(lines: list[str], block: dict[str, Any], level: int) -> None:
    title = block.get("title")
    if title:
        lines.append(f'{"#" * level} {title}')
        lines.append("")

    for paragraph in block.get("paragraphs", []):
        lines.append(paragraph)
        lines.append("")

    for bullet in block.get("bullets", []):
        lines.append(f"- {bullet}")
    if block.get("bullets"):
        lines.append("")

    for idx, item in enumerate(block.get("numbered", []), start=1):
        lines.append(f"{idx}. {item}")
    if block.get("numbered"):
        lines.append("")

    for child in block.get("items", []):
        render_block(lines, child, level + 1)


def render_markdown(spec: dict[str, Any]) -> str:
    meta = spec.get("meta", {})
    lines: list[str] = []
    lines.append(f'# {meta.get("title", "Untitled")}')
    lines.append("")

    subtitle = meta.get("subtitle")
    if subtitle:
        lines.append(subtitle)
        lines.append("")

    for paragraph in spec.get("summary", []):
        lines.append(paragraph)
        lines.append("")

    for section in spec.get("sections", []):
        render_block(lines, section, 2)

    lines.append("")
    return "\n".join(lines)


def extract_json_from_markdown(markdown_text: str) -> dict[str, Any]:
    """Build a lightweight, generic structure from a human Markdown document.

    This intentionally does not try to recover every runtime field from prose.
    Strict runtime contracts should keep a companion JSON file as the canonical
    contract. Human documents can still be converted to a review/search structure
    without carrying a hidden machine-only block.
    """
    title = "Untitled"
    summary: list[str] = []
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            current = {"title": line[3:].strip(), "paragraphs": [], "bullets": []}
            sections.append(current)
            continue
        if line.startswith("- "):
            if current is None:
                current = {"title": "Notes", "paragraphs": [], "bullets": []}
                sections.append(current)
            current["bullets"].append(line[2:].strip())
            continue
        if line.startswith("|"):
            continue
        if current is None:
            summary.append(line)
        else:
            current["paragraphs"].append(line)

    return {
        "meta": {
            "title": title,
            "kind": "markdown_extract",
            "version": 1,
        },
        "summary": summary,
        "sections": sections,
    }


def parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def extract_tables_by_heading(markdown_text: str) -> dict[str, list[dict[str, str]]]:
    tables: dict[str, list[dict[str, str]]] = {}
    current_heading = "Document"
    lines = markdown_text.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("## "):
            current_heading = line[3:].strip()
            idx += 1
            continue
        if line.startswith("|") and idx + 1 < len(lines) and set(lines[idx + 1].strip().replace("|", "").replace(" ", "")) <= {"-", ":"}:
            headers = parse_table_row(line)
            idx += 2
            rows: list[dict[str, str]] = []
            while idx < len(lines) and lines[idx].strip().startswith("|"):
                values = parse_table_row(lines[idx])
                rows.append({headers[col]: values[col] if col < len(values) else "" for col in range(len(headers))})
                idx += 1
            tables[current_heading] = rows
            continue
        idx += 1
    return tables


def key_value_table(rows: list[dict[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        keys = list(row.keys())
        if len(keys) >= 2:
            result[row[keys[0]]] = row[keys[1]]
    return result


def extract_specialized_markdown(markdown_text: str) -> dict[str, Any]:
    generic = extract_json_from_markdown(markdown_text)
    title = generic["meta"]["title"]
    tables = extract_tables_by_heading(markdown_text)
    if title == "Execution Brief":
        brief_match = re.search(r"本轮编号\s*(?P<brief_id>EB-[^，。]+).*?目标是\s*(?P<episode_id>EP\d+)/(?P<active_target_id>M\d+).*?第\s*(?P<round>\d+)\s*轮", markdown_text, re.S)
        command_match = re.search(r"消息编号\s*(?P<command_id>EC-[^，。]+).*?发送到\s*(?P<channel>[^，。]+).*?动作是\s*(?P<action>[a-z_]+).*?正文是[：:]\s*「(?P<message>.*?)」", markdown_text, re.S)
        timer_match = re.search(r"等待\s*(?P<wait_seconds>\d+)\s*秒.*?最长(?:等待|等)\s*(?P<max_wait_seconds>\d+)\s*秒", markdown_text, re.S)
        enum_match = re.search(r"Judge Result\s*只(?:能|允许)(?:给出|是)?\s*(?P<enum>Continuing Episode、Next Episode、Run Plan Close)", markdown_text)
        if brief_match or command_match or timer_match:
            fixed = brief_match.groupdict() if brief_match else {}
            command = command_match.groupdict() if command_match else {}
            timer = timer_match.groupdict() if timer_match else {}
            if timer:
                early_match = re.search(r"只要(?P<early_resume_conditions>[^。]+?)，就提前恢复", markdown_text)
                timeout_match = re.search(r"超时后(?P<timeout_action>[^。]+)", markdown_text)
                if early_match:
                    timer["early_resume_conditions"] = early_match.group("early_resume_conditions").strip()
                if timeout_match:
                    timer["timeout_action"] = timeout_match.group("timeout_action").strip()
            if enum_match:
                fixed["judge_result_enum"] = enum_match.group("enum")
            return {
                "meta": {"title": title, "kind": "execution_brief_extract", "version": 3},
                "readable_sections": generic["sections"],
                "runtime_fields": fixed,
                "opponent_state": key_value_table(tables.get("对手状态字段", [])),
                "strategy_fields": key_value_table(tables.get("策略字段", [])),
                "execution_command": command or key_value_table(tables.get("Execution Command", [])),
                "execution_timer": timer or key_value_table(tables.get("Execution Timer", [])),
                "result_contract": key_value_table(tables.get("结果回收字段", [])),
            }
        return {
            "meta": {"title": title, "kind": "execution_brief_extract", "version": 2},
            "natural_language": {
                "summary": generic["summary"],
                "sections": generic["sections"],
            },
            "fixed_runtime_fields": key_value_table(tables.get("Runtime Fields", [])),
            "opponent_state": key_value_table(tables.get("对手状态字段", [])),
            "strategy_fields": key_value_table(tables.get("策略字段", [])),
            "execution_command": key_value_table(tables.get("Execution Command", [])),
            "execution_timer": key_value_table(tables.get("Execution Timer", [])),
            "result_contract": key_value_table(tables.get("结果回收字段", [])),
        }
    if title == "Closure Policy":
        enum_match = re.search(r"Judge Result\s*只(?:能|允许)(?:给出|是)?\s*(?P<enum>Continuing Episode、Next Episode、Run Plan Close)", markdown_text)
        rule_matches = re.findall(r"如果([^，。]+)，Judge Result\s*是\s*(Continuing Episode|Next Episode|Run Plan Close)", markdown_text)
        outcome_matches = re.findall(r"(success_close|partial_success_close|fail_close|blocked_close|risk_aborted)\s*表示([^。]+)", markdown_text)
        table_rules = tables.get("判定表", [])
        table_outcomes = tables.get("目标级 outcome", [])
        if enum_match or rule_matches or outcome_matches or table_rules or table_outcomes:
            judge_result_rules = [{"condition": condition.strip(), "judge_result": result} for condition, result in rule_matches]
            if not judge_result_rules:
                judge_result_rules = [
                    {"condition": row.get("条件", "").strip(), "judge_result": row.get("Judge Result", "").strip()}
                    for row in table_rules
                    if row.get("条件") and row.get("Judge Result")
                ]
            target_outcome_rules = [{"outcome": outcome, "condition": condition.strip()} for outcome, condition in outcome_matches]
            if not target_outcome_rules:
                target_outcome_rules = [
                    {"outcome": row.get("outcome", "").strip(), "condition": (row.get("含义") or row.get("条件") or "").strip()}
                    for row in table_outcomes
                    if row.get("outcome") and (row.get("含义") or row.get("条件"))
                ]
            return {
                "meta": {"title": title, "kind": "closure_policy_extract", "version": 3},
                "readable_sections": generic["sections"],
                "fixed_judgement_fields": {
                    "judge_result_enum": enum_match.group("enum") if enum_match else "",
                    "target_outcome_enum": "success_close；partial_success_close；fail_close；blocked_close；risk_aborted",
                },
                "judge_result_rules": judge_result_rules,
                "target_outcome_rules": target_outcome_rules,
            }
        return {
            "meta": {"title": title, "kind": "closure_policy_extract", "version": 2},
            "natural_language": {
                "summary": generic["summary"],
                "sections": generic["sections"],
            },
            "fixed_judgement_fields": key_value_table(tables.get("Judgement Fields", [])),
            "judge_result_rules": tables.get("三态判定表", []),
            "target_outcome_rules": tables.get("目标级 outcome 表", []),
        }
    return generic


def spec_path_to_doc_path(spec_path: Path) -> Path:
    return spec_path.with_suffix(".md")


def doc_path_to_spec_path(doc_path: Path) -> Path:
    return doc_path.with_suffix(".index.json")


def sync_spec_to_doc(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    doc_path = spec_path_to_doc_path(spec_path)
    doc_path.write_text(render_markdown(spec), encoding="utf-8")


def sync_doc_to_spec(doc_path: Path) -> None:
    spec = extract_specialized_markdown(doc_path.read_text(encoding="utf-8"))
    spec_path = doc_path_to_spec_path(doc_path)
    spec_path.write_text(json_dumps(spec), encoding="utf-8")
    if spec.get("meta", {}).get("kind") == "execution_brief_extract":
        if spec.get("execution_command"):
            (doc_path.parent / "ExecutionCommand.extracted.json").write_text(json_dumps(spec["execution_command"]), encoding="utf-8")
        if spec.get("execution_timer"):
            (doc_path.parent / "ExecutionTimer.extracted.json").write_text(json_dumps(spec["execution_timer"]), encoding="utf-8")


def discover_spec_paths() -> list[Path]:
    candidates: list[Path] = []
    for path in ROOT.rglob("*.json"):
        if ".vscode" in path.parts or "node_modules" in path.parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("meta"), dict) and isinstance(data.get("sections"), list):
            candidates.append(path)
    return sorted(candidates)


def discover_doc_paths() -> list[Path]:
    candidates: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if ".vscode" in path.parts or "node_modules" in path.parts:
            continue
        candidates.append(path)
    return sorted(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync human-readable Markdown docs and machine-readable JSON specs.")
    parser.add_argument(
        "direction",
        choices=["spec-to-doc", "doc-to-spec", "sync"],
        help="Choose sync direction.",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Optional list of paths to limit the sync scope.",
    )
    args = parser.parse_args()

    if args.direction == "spec-to-doc":
        paths = [ROOT / p for p in args.paths] if args.paths else discover_spec_paths()
        for path in paths:
            sync_spec_to_doc(path)
    elif args.direction == "doc-to-spec":
        if not args.paths:
            raise SystemExit("doc-to-spec now requires --paths and writes *.index.json to avoid overwriting strict runtime JSON contracts.")
        paths = [ROOT / p for p in args.paths] if args.paths else discover_doc_paths()
        for path in paths:
            sync_doc_to_spec(path)
    else:
        spec_paths = [ROOT / p for p in args.paths] if args.paths else discover_spec_paths()
        for path in spec_paths:
            sync_spec_to_doc(path)


if __name__ == "__main__":
    main()
