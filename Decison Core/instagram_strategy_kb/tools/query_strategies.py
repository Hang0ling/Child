from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "strategies.json"
USER_DATA_FILE = ROOT / "data" / "user_strategies.json"
POOL_FILE = ROOT / "data" / "active_strategy_pool.json"


def load_cards() -> list[dict]:
    if not DATA_FILE.exists():
        raise SystemExit(
            f"Missing {DATA_FILE}. Run: python {ROOT / 'tools' / 'generate_strategy_library.py'}"
        )
    if POOL_FILE.exists():
        return json.loads(POOL_FILE.read_text(encoding="utf-8"))
    cards = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if USER_DATA_FILE.exists():
        cards.extend(json.loads(USER_DATA_FILE.read_text(encoding="utf-8")))
    return cards


def contains_all_terms(card: dict, query: str) -> bool:
    if not query:
        return True
    haystack = json.dumps(card, ensure_ascii=False).lower()
    return all(term.lower() in haystack for term in query.split())


def matches(args: argparse.Namespace, card: dict) -> bool:
    if args.stage and card["stage"] != args.stage:
        return False
    if args.goal and args.goal not in card["goals"]:
        return False
    if args.format and args.format not in card["formats"]:
        return False
    if args.psychology and args.psychology not in card["psychology"]:
        return False
    if args.source and args.source not in card["sources"]:
        return False
    if args.q and not contains_all_terms(card, args.q):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Query local Instagram strategy cards.")
    parser.add_argument("--stage", help="Example: S3")
    parser.add_argument("--goal", help='Example: "开启私信对话"')
    parser.add_argument("--format", help='Example: "Reels 策略"')
    parser.add_argument("--psychology", help='Example: "提升真实感"')
    parser.add_argument("--source", help="Example: CIALDINI_INFLUENCE")
    parser.add_argument("--q", help='Keyword query. Example: "福利 私信"')
    parser.add_argument("--show-related", action="store_true", help="Print strategy graph relations.")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    cards = [card for card in load_cards() if matches(args, card)]
    print(f"Matched {len(cards)} strategies")
    for card in cards[: args.limit]:
        print()
        print(f"{card['id']} {card['title']}")
        print(f"  stage: {card['stage']} {card['stage_name']}")
        print(f"  goals: {'、'.join(card['goals'])}")
        print(f"  formats: {'、'.join(card['formats'])}")
        print(f"  psychology: {'、'.join(card['psychology'])}")
        print(f"  sources: {'、'.join(card['sources'])}")
        print(f"  path: {ROOT / card['path']}")
        print(f"  principle: {card['principle']}")
        if args.show_related and card.get("related_strategies"):
            related = "；".join(
                f"{item['relation']}->{item['id']}" for item in card["related_strategies"]
            )
            print(f"  related: {related}")


if __name__ == "__main__":
    main()
