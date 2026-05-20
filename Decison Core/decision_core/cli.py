from __future__ import annotations

import argparse
import json
from pathlib import Path

from .orchestrator import DecisionCoreOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a validated Execution Brief from Decision Core input JSON.")
    parser.add_argument("--input", required=True, help="Path to input JSON payload.")
    parser.add_argument("--output", help="Optional path to write full JSON result.")
    parser.add_argument("--brief-output", help="Optional path to write only the final Execution Brief.")
    parser.add_argument("--print-brief", action="store_true", help="Print final Execution Brief to stdout.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = DecisionCoreOrchestrator().run(payload)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.brief_output:
        if not result.get("execution_brief"):
            raise SystemExit(f"Cannot write brief; validation failed: {result.get('validation')}")
        Path(args.brief_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.brief_output).write_text(result["execution_brief"], encoding="utf-8")

    if args.print_brief:
        if result.get("execution_brief"):
            print(result["execution_brief"])
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
