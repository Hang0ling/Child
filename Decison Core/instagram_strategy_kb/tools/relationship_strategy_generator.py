from __future__ import annotations

import argparse
import html
import random
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from generate_strategy_library import (
    FORMATS,
    GOALS,
    PSYCHOLOGY,
    RELATIONSHIP_MISSION,
    SAFETY_BOUNDARY,
    STAGES,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "strategies.json"
USER_DATA_FILE = ROOT / "data" / "user_strategies.json"
POOL_FILE = ROOT / "data" / "active_strategy_pool.json"
REJECTED_DATA_FILE = ROOT / "data" / "rejected_strategies.json"
RESEARCH_MATERIALS_FILE = ROOT / "data" / "research_materials.jsonl"
RESEARCH_SEEN_FILE = ROOT / "data" / "research_seen_urls.json"
USER_CARD_DIR = ROOT / "cards" / "generated"
REJECTED_CARD_DIR = ROOT / "cards" / "rejected"
DEFAULT_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
TARGET_POOL_SIZE = 300
DEFAULT_RESEARCH_QUERIES = [
    "social media trust building strangers friendship online communities",
    "active listening online conversation trust social platforms",
    "parasocial interaction trust creator audience social media",
    "community management building trust social media relationships",
    "nonviolent communication online conflict comments direct messages",
    "social media relationship marketing authentic engagement",
    "online friendship formation trust self disclosure boundaries",
    "creator community trust retention Instagram stories comments DM",
]


class StrategyGeneratorError(RuntimeError):
    pass


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = {key: value or "" for key, value in attrs}
        href = attrs_dict.get("href", "")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            text = normalize_text(" ".join(self._text))
            if text:
                self.links.append({"url": self._href, "title": text})
            self._href = ""
            self._text = []


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_text(html.unescape(" ".join(self.parts)))


def compact_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？!?；;])\s+|\n+", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def split_long_text(text: str, chunk_size: int) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        sentence_len = compact_length(sentence)
        if sentence_len > chunk_size:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            for start in range(0, len(sentence), chunk_size):
                chunks.append(sentence[start : start + chunk_size])
            continue
        if current and current_len + sentence_len > chunk_size:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = sentence_len
        else:
            current.append(sentence)
            current_len += sentence_len
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_text(text: str, chunk_size: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    chunks: list[str] = []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = compact_length(paragraph)
        if paragraph_len > chunk_size:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            chunks.extend(split_long_text(paragraph, chunk_size))
            continue
        if current and current_len + paragraph_len > chunk_size:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = paragraph_len
        else:
            current.append(paragraph)
            current_len += paragraph_len

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def decode_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        if text.strip():
            return text
    except Exception:
        pass

    try:
        import fitz

        doc = fitz.open(stream=data, filetype="pdf")
        pages = [page.get_text("text") for page in doc]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        if text.strip():
            return text
    except Exception as exc:
        raise StrategyGeneratorError(f"PDF 文本提取失败：{exc}") from exc

    raise StrategyGeneratorError("PDF 没有提取到可用文本，可能是扫描版图片 PDF。")


def read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    file_path = Path(path)
    data = file_path.read_bytes()
    if file_path.suffix.lower() == ".pdf":
        return extract_pdf_text(data)
    return decode_text_bytes(data)


def http_get(url: str, timeout: int = 20) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RelationshipStrategyResearchAgent/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")


def strip_html(data: bytes) -> str:
    text = decode_text_bytes(data)
    extractor = TextExtractor()
    extractor.feed(text)
    return extractor.text()


def clean_research_text(text: str, max_chars: int = 9000) -> str:
    text = normalize_text(text)
    text = re.sub(r"(cookie|subscribe|newsletter|advertisement|privacy policy)", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def normalize_result_url(url: str) -> str:
    url = html.unescape(url)
    if url.startswith("//"):
        url = "https:" + url
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        query = urllib.parse.parse_qs(parsed.query)
        if query.get("uddg"):
            return query["uddg"][0]
    if parsed.scheme not in {"http", "https"}:
        return ""
    return urllib.parse.urlunparse(parsed._replace(fragment=""))


def search_duckduckgo(query: str, limit: int = 8) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    data, _ = http_get(url)
    parser = LinkExtractor()
    parser.feed(decode_text_bytes(data))
    results = []
    seen = set()
    for link in parser.links:
        result_url = normalize_result_url(link["url"])
        title = link["title"]
        if not result_url or result_url in seen:
            continue
        if any(blocked in result_url for blocked in ["duckduckgo.com", "javascript:", "mailto:"]):
            continue
        seen.add(result_url)
        results.append({"title": title, "url": result_url, "snippet": ""})
        if len(results) >= limit:
            break
    return results


def search_bing_news(query: str, limit: int = 8) -> list[dict[str, str]]:
    url = "https://www.bing.com/news/search?" + urllib.parse.urlencode({"q": query, "format": "RSS"})
    data, _ = http_get(url)
    root = ElementTree.fromstring(data)
    results = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        description = item.findtext("description") or ""
        link = normalize_result_url(link)
        if title and link:
            results.append({"title": normalize_text(title), "url": link, "snippet": normalize_text(description)})
        if len(results) >= limit:
            break
    return results


def search_web(query: str, limit: int = 8) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for searcher in (search_bing_news, search_duckduckgo):
        try:
            results.extend(searcher(query, limit=limit))
        except Exception:
            continue
        if len(results) >= limit:
            break
    seen = set()
    clean = []
    for result in results:
        if result["url"] in seen:
            continue
        seen.add(result["url"])
        clean.append(result)
        if len(clean) >= limit:
            break
    return clean


def load_seen_urls() -> set[str]:
    if not RESEARCH_SEEN_FILE.exists():
        return set()
    try:
        return set(json.loads(RESEARCH_SEEN_FILE.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return set()


def save_seen_urls(urls: set[str]) -> None:
    RESEARCH_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESEARCH_SEEN_FILE.write_text(json.dumps(sorted(urls), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_research_material(material: dict[str, Any]) -> None:
    RESEARCH_MATERIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESEARCH_MATERIALS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(material, ensure_ascii=False) + "\n")


def fetch_research_material(result: dict[str, str]) -> dict[str, Any] | None:
    try:
        data, content_type = http_get(result["url"], timeout=25)
        if "pdf" in content_type.lower() or result["url"].lower().endswith(".pdf"):
            text = extract_pdf_text(data)
        else:
            text = strip_html(data)
    except Exception:
        text = result.get("snippet", "")

    text = clean_research_text(text or result.get("snippet", ""))
    if compact_length(text) < 300:
        return None

    return {
        "title": result.get("title", ""),
        "url": result.get("url", ""),
        "snippet": result.get("snippet", ""),
        "text": text,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }


def collect_research_material(queries: list[str]) -> dict[str, Any]:
    queries = [query.strip() for query in queries if query.strip()] or DEFAULT_RESEARCH_QUERIES
    seen = load_seen_urls()
    random.shuffle(queries)
    errors: list[str] = []

    for query in queries:
        try:
            results = search_web(query, limit=8)
        except Exception as exc:
            errors.append(f"{query}: {exc}")
            continue
        for result in results:
            url = result.get("url", "")
            if not url or url in seen:
                continue
            material = fetch_research_material(result)
            seen.add(url)
            save_seen_urls(seen)
            if material:
                material["query"] = query
                append_research_material(material)
                return material
    raise StrategyGeneratorError("没有搜集到可用新资料。" + (" / " + "；".join(errors[:3]) if errors else ""))


def strategy_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "stage": {"type": "string", "enum": list(STAGES)},
            "goals": {
                "type": "array",
                "items": {"type": "string", "enum": GOALS},
                "minItems": 2,
                "maxItems": 3,
            },
            "formats": {
                "type": "array",
                "items": {"type": "string", "enum": FORMATS},
                "minItems": 1,
                "maxItems": 3,
            },
            "psychology": {
                "type": "array",
                "items": {"type": "string", "enum": PSYCHOLOGY},
                "minItems": 2,
                "maxItems": 3,
            },
            "principle": {"type": "string"},
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5,
            },
            "metrics": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5,
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 8,
            },
            "evidence_summary": {"type": "string"},
            "novelty_angle": {"type": "string"},
            "safety_boundary": {"type": "string"},
        },
        "required": [
            "title",
            "stage",
            "goals",
            "formats",
            "psychology",
            "principle",
            "actions",
            "metrics",
            "keywords",
            "evidence_summary",
            "novelty_angle",
            "safety_boundary",
        ],
    }


def generation_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"strategy": strategy_schema()},
        "required": ["strategy"],
    }


def audit_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "can_add": {"type": "boolean"},
            "status": {"type": "string", "enum": ["add", "revise", "reject"]},
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "reasons": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 5,
            },
            "required_changes": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 6,
            },
            "closest_existing": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "overlap": {"type": "string"},
                    },
                    "required": ["id", "title", "overlap"],
                },
                "minItems": 0,
                "maxItems": 3,
            },
            "library_note": {"type": "string"},
        },
        "required": [
            "can_add",
            "status",
            "score",
            "reasons",
            "required_changes",
            "closest_existing",
            "library_note",
        ],
    }


def prune_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "remove_id": {"type": "string"},
            "reason": {"type": "string"},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        },
        "required": ["remove_id", "reason", "confidence"],
    }


def extract_output_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"])

    texts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                texts.append(str(content["text"]))
    if texts:
        return "\n".join(texts)
    raise StrategyGeneratorError("AI 返回里没有可解析的文本。")


def normalize_api_base_url(base_url: str) -> str:
    base_url = (base_url or DEFAULT_API_BASE_URL).strip().rstrip("/")
    for suffix in ("/chat/completions", "/responses", "/embeddings"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)].rstrip("/")
    return base_url or DEFAULT_API_BASE_URL


def join_api_url(base_url: str, path: str) -> str:
    return normalize_api_base_url(base_url).rstrip("/") + "/" + path.lstrip("/")


def extract_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        return text[start : end + 1]
    return text


def use_responses_api(base_url: str) -> bool:
    style = os.getenv("OPENAI_API_STYLE", "").strip().lower()
    if style in {"responses", "chat"}:
        return style == "responses"
    return "api.openai.com" in urllib.parse.urlparse(normalize_api_base_url(base_url)).netloc


def openai_json_response(
    *,
    instructions: str,
    user_text: str,
    schema_name: str,
    schema: dict[str, Any],
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
    max_output_tokens: int = 2500,
) -> dict[str, Any]:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise StrategyGeneratorError("缺少 OPENAI_API_KEY，无法进行 AI 生成或审核。")
    api_base_url = normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL)

    if use_responses_api(api_base_url):
        endpoint = join_api_url(api_base_url, "responses")
        payload = {
            "model": model or DEFAULT_MODEL,
            "instructions": instructions,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": max_output_tokens,
        }
    else:
        endpoint = join_api_url(api_base_url, "chat/completions")
        schema_prompt = json.dumps(schema, ensure_ascii=False, indent=2)
        payload = {
            "model": model or DEFAULT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        instructions
                        + "\n\n你必须只输出一个 JSON 对象，不要 Markdown，不要解释。"
                        + f"\nJSON Schema 名称：{schema_name}\nJSON Schema：\n{schema_prompt}"
                    ),
                },
                {"role": "user", "content": user_text},
            ],
            "max_tokens": max_output_tokens,
            "temperature": 0.2,
        }
    request = urllib.request.Request(
        endpoint,
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
        hint = ""
        if exc.code == 401 and "api.openai.com" in urllib.parse.urlparse(api_base_url).netloc:
            hint = " 当前请求发到了官方 OpenAI 端点；如果你使用第三方兼容 key，请把 API Base URL 改成对应服务的 /v1 地址。"
        raise StrategyGeneratorError(f"OpenAI API 请求失败：HTTP {exc.code}，端点：{endpoint}。{hint} {body}") from exc
    except urllib.error.URLError as exc:
        raise StrategyGeneratorError(f"OpenAI API 网络请求失败：{exc}") from exc

    parsed = json.loads(raw)
    if use_responses_api(api_base_url):
        output_text = extract_output_text(parsed)
    else:
        choices = parsed.get("choices", [])
        if not choices:
            raise StrategyGeneratorError("Chat Completions 返回里没有 choices。")
        output_text = choices[0].get("message", {}).get("content", "")
    try:
        return json.loads(extract_json_text(output_text))
    except json.JSONDecodeError as exc:
        raise StrategyGeneratorError(f"AI 输出不是合法 JSON：{output_text[:600]}") from exc


def test_chat_connection(
    *,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any]:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise StrategyGeneratorError("缺少 OPENAI_API_KEY 或临时 API Key，无法测试连接。")
    api_base_url = normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL)
    endpoint = join_api_url(api_base_url, "chat/completions")
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": "你好，请用一句话说明连接测试成功。"},
        ],
        "max_tokens": 120,
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        hint = ""
        if exc.code == 401:
            hint = " 请确认 API Key 属于这个 API Base URL 对应的服务，不要把第三方 key 发到官方 OpenAI 端点。"
        raise StrategyGeneratorError(f"连接测试失败：HTTP {exc.code}，端点：{endpoint}。{hint} {body}") from exc
    except urllib.error.URLError as exc:
        raise StrategyGeneratorError(f"连接测试网络失败：{exc}") from exc

    parsed = json.loads(raw)
    choices = parsed.get("choices", [])
    if not choices:
        raise StrategyGeneratorError(f"连接测试返回里没有 choices：{raw[:600]}")
    content = choices[0].get("message", {}).get("content", "")
    return {
        "ok": True,
        "endpoint": endpoint,
        "model": model or DEFAULT_MODEL,
        "content": content,
    }


def generation_instructions() -> str:
    return f"""你是一个社交平台关系策略生成器，不是关键词抽取器。

目标：从输入资料中综合推理，生成 1 条可执行策略，用于在社交平台上认识陌生人、自然成为朋友、逐步赢得信任。

要求：
- 必须提炼资料背后的关系机制，不能只摘抄关键词或改写原句。
- 策略要能直接落到 Instagram/TikTok/X/小红书等社交平台的公开互动、主页、内容、评论、私信、资源互助或长期维护中。
- actions 必须是具体动作，不要写空泛原则。
- 分类只能从给定枚举中选择。

关系应用：{RELATIONSHIP_MISSION}
底线：{SAFETY_BOUNDARY}
"""


def audit_instructions() -> str:
    return f"""你是策略库 AI 审核员，判断候选策略是否能加入“社交平台认识陌生人并建立信任”的策略库。

审核标准：
- 相关性：必须服务认识陌生人、成为朋友、赢得信任。
- 安全性：不能鼓励伪装身份、套取隐私、情绪操控、骚扰、虚假亲密或高压推进。
- 可执行性：动作足够具体，能被运营者照着做。
- 新颖性：不能只是已有策略的换皮。
- 分类质量：阶段、目标、形式、心理分类要合理。

只有明显相关、安全、可执行且不重复时，can_add 才能为 true。
底线：{SAFETY_BOUNDARY}
"""


def build_generation_prompt(chunk: str, index: int, total: int, source_name: str) -> str:
    return json.dumps(
        {
            "source_name": source_name,
            "chunk_index": index,
            "chunk_total": total,
            "chunk_char_count": compact_length(chunk),
            "allowed_categories": {
                "stages": STAGES,
                "goals": GOALS,
                "formats": FORMATS,
                "psychology": PSYCHOLOGY,
            },
            "source_chunk": chunk,
        },
        ensure_ascii=False,
        indent=2,
    )


def normalize_strategy(
    raw_strategy: dict[str, Any],
    *,
    index: int,
    chunk: str,
    source_name: str,
    id_prefix: str,
) -> dict[str, Any]:
    stage = raw_strategy.get("stage") if raw_strategy.get("stage") in STAGES else "S5"
    strategy = {
        "id": f"{id_prefix}-{index:03d}",
        "title": str(raw_strategy.get("title", "")).strip() or f"AI 关系策略 {index}",
        "stage": stage,
        "stage_name": STAGES[stage],
        "goals": [goal for goal in raw_strategy.get("goals", []) if goal in GOALS][:3],
        "formats": [fmt for fmt in raw_strategy.get("formats", []) if fmt in FORMATS][:3],
        "psychology": [item for item in raw_strategy.get("psychology", []) if item in PSYCHOLOGY][:3],
        "source_name": source_name,
        "chunk_index": index,
        "chunk_char_count": compact_length(chunk),
        "evidence_summary": str(raw_strategy.get("evidence_summary", "")).strip(),
        "novelty_angle": str(raw_strategy.get("novelty_angle", "")).strip(),
        "principle": str(raw_strategy.get("principle", "")).strip(),
        "actions": [str(action).strip() for action in raw_strategy.get("actions", []) if str(action).strip()][:5],
        "metrics": [str(metric).strip() for metric in raw_strategy.get("metrics", []) if str(metric).strip()][:5],
        "relationship_focus": RELATIONSHIP_MISSION,
        "safety_boundary": str(raw_strategy.get("safety_boundary", "")).strip() or SAFETY_BOUNDARY,
        "keywords": [str(keyword).strip() for keyword in raw_strategy.get("keywords", []) if str(keyword).strip()][:8],
        "origin": "ai_generated",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    if len(strategy["goals"]) < 2:
        strategy["goals"] = ["开启私信对话", "提高后续对话率"]
    if not strategy["formats"]:
        strategy["formats"] = ["私信策略"]
    if len(strategy["psychology"]) < 2:
        strategy["psychology"] = ["提升安全感", "提升被理解感"]
    if len(strategy["actions"]) < 3:
        strategy["actions"].append(f"边界要求：{SAFETY_BOUNDARY}")
    if SAFETY_BOUNDARY not in " ".join(strategy["actions"]):
        strategy["actions"].append(f"边界要求：{SAFETY_BOUNDARY}")
    if not strategy["metrics"]:
        strategy["metrics"] = ["第一轮回应率", "重复互动率", "信任类反馈"]
    if not strategy["keywords"]:
        strategy["keywords"] = ["认识陌生人", "成为朋友", "建立信任", "社交平台"]
    return strategy


def load_builtin_cards() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def load_user_cards() -> list[dict[str, Any]]:
    if not USER_DATA_FILE.exists():
        return []
    return json.loads(USER_DATA_FILE.read_text(encoding="utf-8"))


def load_active_pool() -> list[dict[str, Any]]:
    if POOL_FILE.exists():
        return json.loads(POOL_FILE.read_text(encoding="utf-8"))
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in load_user_cards() + load_builtin_cards():
        card_id = card.get("id")
        if not card_id or card_id in seen:
            continue
        cards.append(card)
        seen.add(card_id)
        if len(cards) >= TARGET_POOL_SIZE:
            break
    return cards


def save_active_pool(cards: list[dict[str, Any]]) -> None:
    POOL_FILE.parent.mkdir(parents=True, exist_ok=True)
    POOL_FILE.write_text(json.dumps(cards[:TARGET_POOL_SIZE], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_all_cards() -> list[dict[str, Any]]:
    return load_active_pool()


def append_rejected_strategy(strategy: dict[str, Any], reason: str) -> None:
    rejected = []
    if REJECTED_DATA_FILE.exists():
        rejected = json.loads(REJECTED_DATA_FILE.read_text(encoding="utf-8"))
    item = dict(strategy)
    item["rejected_on"] = datetime.now().isoformat(timespec="seconds")
    item["rejection_reason"] = reason
    rejected.append(item)
    REJECTED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    REJECTED_DATA_FILE.write_text(json.dumps(rejected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if item.get("id"):
        REJECTED_CARD_DIR.mkdir(parents=True, exist_ok=True)
        (REJECTED_CARD_DIR / f"{item['id']}.md").write_text(render_strategy(item).rstrip() + "\n", encoding="utf-8")


def strategy_quality_score(card: dict[str, Any]) -> int:
    text = json.dumps(card, ensure_ascii=False)
    score = 0
    score += min(len(card.get("actions", [])), 5) * 8
    score += min(len(card.get("metrics", [])), 5) * 4
    score += min(len(card.get("keywords", [])), 8) * 2
    for word in ["边界", "真实", "选择", "安全", "信任", "具体", "复述", "倾听"]:
        if word in text:
            score += 4
    for word in ["操控", "伪装", "套取", "骚扰", "施压", "虚假亲密"]:
        if word in text and "不" not in text[max(0, text.find(word) - 4) : text.find(word)]:
            score -= 20
    if card.get("origin") == "ai_generated":
        score += 6
    return score


def choose_heuristic_removal(cards: list[dict[str, Any]], protected_id: str | None = None) -> dict[str, Any]:
    candidates = [card for card in cards if card.get("id") != protected_id] or cards
    return sorted(candidates, key=strategy_quality_score)[0]


def choose_ai_removal(
    cards: list[dict[str, Any]],
    *,
    new_strategy: dict[str, Any] | None = None,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> tuple[dict[str, Any], str]:
    protected_id = new_strategy.get("id") if new_strategy else None
    heuristic_candidates = sorted(
        [card for card in cards if card.get("id") != protected_id],
        key=strategy_quality_score,
    )[:8]
    if not heuristic_candidates:
        candidate = choose_heuristic_removal(cards, protected_id=protected_id)
        return candidate, "策略池超过 300 条，启发式移出低分策略。"
    if not (api_key or os.getenv("OPENAI_API_KEY")):
        return heuristic_candidates[0], "策略池超过 300 条，未提供 API Key，启发式移出低分策略。"

    prompt = json.dumps(
        {
            "pool_target_size": TARGET_POOL_SIZE,
            "new_strategy": new_strategy,
            "delete_candidates": [
                {
                    "id": card.get("id"),
                    "title": card.get("title"),
                    "stage": card.get("stage"),
                    "principle": card.get("principle", ""),
                    "actions": card.get("actions", []),
                    "metrics": card.get("metrics", []),
                    "keywords": card.get("keywords", []),
                    "origin": card.get("origin", "built_in"),
                }
                for card in heuristic_candidates
            ],
            "instruction": "从 delete_candidates 中选择最应该移出有效策略池的一条，优先移出重复、空泛、不可执行、风险边界不足或与主题偏离的策略。",
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        result = openai_json_response(
            instructions="你是策略池清理审核员。必须只返回 delete_candidates 里的 remove_id，不允许选择 new_strategy，除非它也在候选列表里。",
            user_text=prompt,
            schema_name="strategy_pool_prune",
            schema=prune_response_schema(),
            model=model,
            api_key=api_key,
            api_base_url=api_base_url,
            max_output_tokens=800,
        )
        remove_id = result["remove_id"]
        for card in heuristic_candidates:
            if card.get("id") == remove_id:
                return card, result.get("reason", "AI 审核移出低质量策略。")
    except Exception:
        pass
    return heuristic_candidates[0], "AI 清理失败，启发式移出低分策略。"


def maintain_strategy_pool(
    *,
    new_strategy: dict[str, Any] | None = None,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any] | None:
    cards = load_active_pool()
    if new_strategy:
        cards = [card for card in cards if card.get("id") != new_strategy.get("id")]
        cards.append(new_strategy)

    removed: dict[str, Any] | None = None
    while len(cards) > TARGET_POOL_SIZE:
        remove_card, reason = choose_ai_removal(
            cards,
            new_strategy=new_strategy,
            model=model,
            api_key=api_key,
            api_base_url=api_base_url,
        )
        cards = [card for card in cards if card.get("id") != remove_card.get("id")]
        append_rejected_strategy(remove_card, reason)
        removed = {"strategy": remove_card, "reason": reason}

    save_active_pool(cards)
    return removed


def delete_strategy(strategy_id: str, reason: str = "AI 审核删除") -> dict[str, Any]:
    cards = load_active_pool()
    for card in cards:
        if card.get("id") == strategy_id:
            cards = [item for item in cards if item.get("id") != strategy_id]
            append_rejected_strategy(card, reason)
            replacements = [item for item in load_builtin_cards() + load_user_cards() if item.get("id") != strategy_id]
            existing_ids = {item.get("id") for item in cards}
            for candidate in sorted(replacements, key=strategy_quality_score, reverse=True):
                if candidate.get("id") not in existing_ids:
                    cards.append(candidate)
                    break
            save_active_pool(cards[:TARGET_POOL_SIZE])
            return card
    raise StrategyGeneratorError(f"没有找到策略：{strategy_id}")


def token_set(value: Any) -> set[str]:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return set(re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]{2,}", text.lower()))


def similar_existing(strategy: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    base = token_set(
        " ".join(
            [
                strategy.get("title", ""),
                strategy.get("principle", ""),
                " ".join(strategy.get("keywords", [])),
            ]
        )
    )
    scored = []
    for card in load_all_cards():
        other = token_set(
            " ".join(
                [
                    card.get("title", ""),
                    card.get("principle", ""),
                    " ".join(card.get("keywords", [])),
                ]
            )
        )
        if not base or not other:
            continue
        overlap = len(base & other)
        if overlap:
            scored.append((overlap, card))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "id": card.get("id", ""),
            "title": card.get("title", ""),
            "stage": card.get("stage", ""),
            "principle": card.get("principle", "")[:220],
            "overlap_score": score,
        }
        for score, card in scored[:limit]
    ]


def audit_strategy(
    strategy: dict[str, Any],
    *,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any]:
    prompt = json.dumps(
        {
            "candidate_strategy": strategy,
            "closest_existing_candidates": similar_existing(strategy),
            "allowed_categories": {
                "stages": STAGES,
                "goals": GOALS,
                "formats": FORMATS,
                "psychology": PSYCHOLOGY,
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    result = openai_json_response(
        instructions=audit_instructions(),
        user_text=prompt,
        schema_name="strategy_audit",
        schema=audit_response_schema(),
        model=model,
        api_key=api_key,
        api_base_url=api_base_url,
        max_output_tokens=1800,
    )
    return result


def generate_strategy_for_chunk(
    chunk: str,
    *,
    index: int,
    total: int,
    source_name: str,
    id_prefix: str,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any]:
    result = openai_json_response(
        instructions=generation_instructions(),
        user_text=build_generation_prompt(chunk, index, total, source_name),
        schema_name="relationship_strategy_generation",
        schema=generation_response_schema(),
        model=model,
        api_key=api_key,
        api_base_url=api_base_url,
        max_output_tokens=2600,
    )
    return normalize_strategy(
        result["strategy"],
        index=index,
        chunk=chunk,
        source_name=source_name,
        id_prefix=id_prefix,
    )


def generate_strategies(
    text: str,
    *,
    source_name: str,
    chunk_size: int = 2000,
    id_prefix: str = "RSG",
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
    review: bool = False,
    max_chunks: int | None = None,
) -> list[dict[str, Any]]:
    chunks = chunk_text(text, chunk_size)
    if max_chunks:
        chunks = chunks[:max_chunks]
    if not chunks:
        raise StrategyGeneratorError("没有可生成策略的输入文本。")

    strategies = []
    total = len(chunks)
    for index, chunk in enumerate(chunks, 1):
        strategy = generate_strategy_for_chunk(
            chunk,
            index=index,
            total=total,
            source_name=source_name,
            id_prefix=id_prefix,
            model=model,
            api_key=api_key,
            api_base_url=api_base_url,
        )
        if review:
            strategy["review"] = audit_strategy(strategy, model=model, api_key=api_key, api_base_url=api_base_url)
        strategies.append(strategy)
    return strategies


def strategy_source_label(strategy: dict[str, Any]) -> str:
    if strategy.get("source_name"):
        return str(strategy["source_name"])
    source_names = strategy.get("source_names") or []
    if source_names:
        return "、".join(str(item) for item in source_names)
    sources = strategy.get("sources") or []
    if sources:
        return "、".join(str(item) for item in sources)
    research_source = strategy.get("research_source") or {}
    if research_source.get("title"):
        return str(research_source["title"])
    return "内置策略库"


def strategy_source_line(strategy: dict[str, Any]) -> str:
    label = strategy_source_label(strategy)
    if strategy.get("chunk_index") or strategy.get("chunk_char_count"):
        return f"- 来源：{label} / 第 {strategy.get('chunk_index', '-')} 段 / {strategy.get('chunk_char_count', '-')} 字"
    return f"- 来源：{label}"


def render_strategy(strategy: dict[str, Any]) -> str:
    actions = "\n".join(f"{idx}. {action}" for idx, action in enumerate(strategy.get("actions", []), 1))
    metrics = "\n".join(f"- {metric}" for metric in strategy.get("metrics", []))
    review = strategy.get("review")
    review_section = ""
    if review:
        reasons = "\n".join(f"- {item}" for item in review.get("reasons", []))
        changes = "\n".join(f"- {item}" for item in review.get("required_changes", [])) or "- 无"
        review_section = f"""
### AI 审核

- 结论：{review.get('status')} / {'可加入' if review.get('can_add') else '暂不加入'}
- 分数：{review.get('score')}
- 入库备注：{review.get('library_note', '')}

原因：

{reasons}

需要修改：

{changes}
"""
    stage = strategy.get("stage", "")
    return f"""## {strategy.get('id', '')} {strategy.get('title', '')}

- 阶段：{stage} {strategy.get('stage_name') or STAGES.get(stage, '')}
- 目标：{'、'.join(strategy.get('goals', []))}
- 内容形式：{'、'.join(strategy.get('formats', []))}
- 用户心理：{'、'.join(strategy.get('psychology', []))}
{strategy_source_line(strategy)}

### 核心判断

{strategy.get('principle', '')}

### 资料依据

{strategy.get('evidence_summary', '')}

### 新增价值

{strategy.get('novelty_angle', '')}

### 关系应用

{strategy.get('relationship_focus', RELATIONSHIP_MISSION)}

底线：{strategy.get('safety_boundary', SAFETY_BOUNDARY)}

### 执行动作

{actions}

### 观察指标

{metrics}
{review_section}

### 检索关键词

{'、'.join(strategy.get('keywords', []))}
"""


def render_markdown(strategies: list[dict[str, Any]], source_name: str) -> str:
    body = "\n".join(render_strategy(strategy) for strategy in strategies)
    return f"""# AI 关系策略生成结果

来源：{source_name}

生成规则：每约 2000 字由 AI 综合生成 1 条与“在社交平台上认识陌生人、成为朋友并赢得信任”相关的策略；不足 2000 字的最后一段也会生成 1 条。

{body}
"""


def write_cards(cards_dir: Path, strategies: list[dict[str, Any]]) -> None:
    cards_dir.mkdir(parents=True, exist_ok=True)
    for strategy in strategies:
        (cards_dir / f"{strategy['id']}.md").write_text(render_strategy(strategy).rstrip() + "\n", encoding="utf-8")


def save_user_strategy(
    strategy: dict[str, Any],
    *,
    model: str | None = None,
    api_key: str | None = None,
    api_base_url: str | None = None,
) -> dict[str, Any]:
    review = strategy.get("review")
    if not review or not review.get("can_add"):
        raise StrategyGeneratorError("AI 审核未通过，不能加入策略库。")

    existing = load_user_cards()
    now = datetime.now()
    accepted_id = strategy.get("id")
    if not accepted_id or any(card.get("id") == accepted_id for card in existing):
        accepted_id = f"RSG-{now.strftime('%Y%m%d-%H%M%S')}"

    card = dict(strategy)
    card["id"] = accepted_id
    card["stage_name"] = STAGES[card["stage"]]
    card["path"] = f"cards/generated/{accepted_id}.md"
    card["sources"] = ["AI_GENERATED"]
    card["source_names"] = [card.get("source_name", "AI 生成")]
    card["added_on"] = now.isoformat(timespec="seconds")
    card["all_tags"] = (
        [card["stage"], card["stage_name"]]
        + card.get("goals", [])
        + card.get("formats", [])
        + card.get("psychology", [])
        + card.get("keywords", [])
        + ["AI_GENERATED"]
    )

    USER_CARD_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / card["path"]).write_text(render_strategy(card).rstrip() + "\n", encoding="utf-8")
    USER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = [item for item in existing if item.get("id") != card["id"]]
    existing.append(card)
    USER_DATA_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    removed = maintain_strategy_pool(new_strategy=card, model=model, api_key=api_key, api_base_url=api_base_url)
    if removed:
        card["pool_removed"] = removed
    return card


def strategy_matches(card: dict[str, Any], category_type: str, category_value: str) -> bool:
    if not category_type or not category_value:
        return True
    if category_type == "stage":
        return card.get("stage") == category_value
    if category_type == "goal":
        return category_value in card.get("goals", [])
    if category_type == "format":
        return category_value in card.get("formats", [])
    if category_type == "psychology":
        return category_value in card.get("psychology", [])
    if category_type == "source":
        return category_value in card.get("sources", []) or category_value in card.get("source_names", [])
    return True


def query_cards(category_type: str = "", category_value: str = "", q: str = "", limit: int = 80) -> list[dict[str, Any]]:
    cards = []
    terms = [term.lower() for term in q.split() if term.strip()]
    for card in load_all_cards():
        if not strategy_matches(card, category_type, category_value):
            continue
        haystack = json.dumps(card, ensure_ascii=False).lower()
        if terms and not all(term in haystack for term in terms):
            continue
        cards.append(card)
    return cards[:limit]


def category_counts(cards: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts = {
        "stage": {key: 0 for key in STAGES},
        "goal": {key: 0 for key in GOALS},
        "format": {key: 0 for key in FORMATS},
        "psychology": {key: 0 for key in PSYCHOLOGY},
    }
    for card in cards:
        if card.get("stage") in counts["stage"]:
            counts["stage"][card["stage"]] += 1
        for goal in card.get("goals", []):
            if goal in counts["goal"]:
                counts["goal"][goal] += 1
        for fmt in card.get("formats", []):
            if fmt in counts["format"]:
                counts["format"][fmt] += 1
        for item in card.get("psychology", []):
            if item in counts["psychology"]:
                counts["psychology"][item] += 1
    return counts


class ResearchAgent:
    def __init__(self) -> None:
        self.running = False
        self.busy = False
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.logs: list[dict[str, Any]] = []
        self.interval_seconds = 60
        self.model: str | None = None
        self.api_key: str | None = None
        self.api_base_url: str | None = None
        self.queries = list(DEFAULT_RESEARCH_QUERIES)
        self.last_run = ""
        self.next_run = ""
        self.generated_count = 0
        self.accepted_count = 0
        self.rejected_count = 0
        self.deleted_count = 0
        self.last_material: dict[str, Any] | None = None
        self.recent_strategies: list[dict[str, Any]] = load_user_cards()[-20:]
        self.last_strategy: dict[str, Any] | None = self.recent_strategies[-1] if self.recent_strategies else None

    def log(self, message: str, level: str = "info", **data: Any) -> None:
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "level": level,
            "message": message,
            **data,
        }
        with self.lock:
            self.logs.append(entry)
            self.logs = self.logs[-80:]

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {
                "running": self.running,
                "busy": self.busy,
                "interval_seconds": self.interval_seconds,
                "model": self.model or DEFAULT_MODEL,
                "api_base_url": self.api_base_url or DEFAULT_API_BASE_URL,
                "queries": self.queries,
                "last_run": self.last_run,
                "next_run": self.next_run,
                "generated_count": self.generated_count,
                "accepted_count": self.accepted_count,
                "rejected_count": self.rejected_count,
                "deleted_count": self.deleted_count,
                "pool_size": len(load_active_pool()),
                "last_material": self.last_material,
                "last_strategy": self.last_strategy,
                "recent_strategies": list(reversed(self.recent_strategies[-20:])),
                "logs": list(reversed(self.logs[-30:])),
            }

    def start(
        self,
        *,
        interval_seconds: int,
        model: str | None,
        api_key: str | None,
        api_base_url: str | None,
        queries: list[str],
    ) -> None:
        if not api_key and not os.getenv("OPENAI_API_KEY"):
            raise StrategyGeneratorError("缺少 OPENAI_API_KEY 或临时 API Key，Agent 无法自动生成策略。")
        with self.lock:
            self.interval_seconds = max(30, interval_seconds)
            self.model = model or DEFAULT_MODEL
            self.api_key = api_key or None
            self.api_base_url = normalize_api_base_url(api_base_url or DEFAULT_API_BASE_URL)
            self.queries = [query.strip() for query in queries if query.strip()] or list(DEFAULT_RESEARCH_QUERIES)
            if self.running:
                self.log("Agent 配置已更新。")
                return
            self.running = True
            self.stop_event.clear()
            self.next_run = datetime.now().isoformat(timespec="seconds")
        self.thread = threading.Thread(target=self.loop, name="research-strategy-agent", daemon=True)
        self.thread.start()
        self.log("Agent 已启动。")

    def stop(self) -> None:
        with self.lock:
            self.running = False
            self.next_run = ""
        self.stop_event.set()
        self.log("Agent 已停止。")

    def loop(self) -> None:
        while not self.stop_event.is_set():
            self.run_once()
            next_time = time.time() + self.interval_seconds
            with self.lock:
                self.next_run = datetime.fromtimestamp(next_time).isoformat(timespec="seconds")
            remaining = self.interval_seconds
            while remaining > 0 and not self.stop_event.is_set():
                time.sleep(min(1, remaining))
                remaining -= 1

    def run_once(self) -> None:
        with self.lock:
            self.busy = True
            self.last_run = datetime.now().isoformat(timespec="seconds")
        try:
            self.log("开始搜集资料。")
            material = collect_research_material(self.queries)
            with self.lock:
                self.last_material = {
                    "title": material.get("title", ""),
                    "url": material.get("url", ""),
                    "query": material.get("query", ""),
                }
            self.log("资料已清洗。", title=material.get("title", ""), url=material.get("url", ""))

            source_name = f"Research Agent: {material.get('title') or material.get('query')}"
            strategies = generate_strategies(
                material["text"],
                source_name=source_name,
                chunk_size=2000,
                id_prefix=f"RAG-{int(time.time())}",
                model=self.model,
                api_key=self.api_key,
                api_base_url=self.api_base_url,
                review=True,
                max_chunks=1,
            )
            strategy = strategies[0]
            strategy["research_source"] = {
                "title": material.get("title", ""),
                "url": material.get("url", ""),
                "query": material.get("query", ""),
            }
            with self.lock:
                self.generated_count += 1
                self.last_strategy = strategy
                self.recent_strategies.append(strategy)
                self.recent_strategies = self.recent_strategies[-20:]
            self.log("已生成并审核策略。", strategy_id=strategy.get("id"), status=strategy.get("review", {}).get("status"))

            if strategy.get("review", {}).get("can_add"):
                saved = save_user_strategy(
                    strategy,
                    model=self.model,
                    api_key=self.api_key,
                    api_base_url=self.api_base_url,
                )
                removed = saved.get("pool_removed")
                with self.lock:
                    self.accepted_count += 1
                    if removed:
                        self.deleted_count += 1
                self.log("策略已加入有效池。", strategy_id=saved.get("id"))
                if removed:
                    self.log(
                        "策略池已保持 300 条，AI 审核移出低质量策略。",
                        removed_id=removed["strategy"].get("id"),
                        reason=removed.get("reason", ""),
                    )
            else:
                append_rejected_strategy(strategy, strategy.get("review", {}).get("library_note", "AI 审核未通过"))
                with self.lock:
                    self.rejected_count += 1
                self.log("策略未通过审核，已归档。", strategy_id=strategy.get("id"), level="warn")
        except Exception as exc:
            self.log(str(exc), level="error")
        finally:
            with self.lock:
                self.busy = False


RESEARCH_AGENT = ResearchAgent()


def parse_query(path: str) -> dict[str, str]:
    if "?" not in path:
        return {}
    query = path.split("?", 1)[1]
    values: dict[str, str] = {}
    for pair in query.split("&"):
        if not pair:
            continue
        key, _, value = pair.partition("=")
        values[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
    return values


def parse_multipart(body: bytes, content_type: str) -> dict[str, Any]:
    match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
    if not match:
        raise StrategyGeneratorError("缺少 multipart boundary。")
    boundary = match.group("boundary").strip('"').encode("utf-8")
    fields: dict[str, Any] = {}
    for raw_part in body.split(b"--" + boundary):
        raw_part = raw_part.strip()
        if not raw_part or raw_part == b"--":
            continue
        if raw_part.endswith(b"--"):
            raw_part = raw_part[:-2].strip()
        header_blob, sep, data = raw_part.partition(b"\r\n\r\n")
        if not sep:
            continue
        data = data.rstrip(b"\r\n")
        headers = decode_text_bytes(header_blob).split("\r\n")
        disposition = next((line for line in headers if line.lower().startswith("content-disposition:")), "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match and filename_match.group(1):
            fields[name] = {"filename": filename_match.group(1), "data": data}
        else:
            fields[name] = decode_text_bytes(data)
    return fields


APP_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI 关系策略生成器</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f8;
      --panel: #ffffff;
      --line: #d9dee5;
      --text: #17202a;
      --muted: #65727f;
      --blue: #1f6feb;
      --green: #1f8a5b;
      --red: #b42318;
      --amber: #9a6700;
      --shadow: 0 1px 3px rgba(20, 28, 36, .08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--text); background: var(--bg); }
    header { height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 18px; border-bottom: 1px solid var(--line); background: var(--panel); }
    h1 { font-size: 17px; margin: 0; font-weight: 700; letter-spacing: 0; }
    main { display: grid; grid-template-columns: minmax(260px, 330px) minmax(280px, 360px) minmax(360px, 1fr) minmax(320px, 420px); gap: 12px; padding: 12px; height: calc(100vh - 56px); }
    section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); min-height: 0; display: flex; flex-direction: column; }
    .section-head { padding: 12px; border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .section-head h2 { font-size: 14px; margin: 0; }
    .body { padding: 12px; overflow: auto; min-height: 0; }
    label { display: block; font-size: 12px; color: var(--muted); margin: 12px 0 6px; }
    input, textarea, select, button { font: inherit; }
    input, textarea, select { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; background: #fff; color: var(--text); }
    textarea { min-height: 260px; resize: vertical; line-height: 1.45; }
    button { border: 1px solid var(--line); border-radius: 6px; background: #fff; color: var(--text); padding: 8px 11px; cursor: pointer; }
    button.primary { background: var(--blue); color: #fff; border-color: var(--blue); }
    button.good { background: var(--green); color: #fff; border-color: var(--green); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .muted { color: var(--muted); font-size: 12px; }
    .status { color: var(--muted); font-size: 12px; min-height: 18px; }
    .card { border: 1px solid var(--line); border-radius: 8px; padding: 12px; margin-bottom: 10px; background: #fff; }
    .card h3 { margin: 0 0 8px; font-size: 15px; line-height: 1.3; }
    .meta { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
    .pill { font-size: 12px; border: 1px solid var(--line); border-radius: 999px; padding: 3px 7px; color: var(--muted); background: #fafafa; }
    .pill.ok { color: var(--green); border-color: rgba(31, 138, 91, .35); background: #f0fbf5; }
    .pill.warn { color: var(--amber); border-color: rgba(154, 103, 0, .35); background: #fff8df; }
    .pill.bad { color: var(--red); border-color: rgba(180, 35, 24, .35); background: #fff1f0; }
    .card p { margin: 8px 0; line-height: 1.48; }
    .card ul, .card ol { padding-left: 20px; margin: 8px 0; }
    .tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; padding: 12px 12px 0; }
    .tabs button.active { border-color: var(--blue); color: var(--blue); background: #edf4ff; }
    .library-list { display: grid; gap: 8px; }
    .small-card { border: 1px solid var(--line); border-radius: 7px; padding: 10px; background: #fff; }
    .small-card strong { display: block; font-size: 13px; margin-bottom: 6px; }
    .small-card p { margin: 0; font-size: 12px; color: var(--muted); line-height: 1.45; }
    .empty { border: 1px dashed var(--line); border-radius: 8px; padding: 20px; color: var(--muted); text-align: center; }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; height: auto; }
      section { min-height: 420px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>AI 关系策略生成器</h1>
    <div class="toolbar"><span id="apiState" class="muted"></span></div>
  </header>
  <main>
    <section>
      <div class="section-head"><h2>搜集 Agent</h2><span id="agentState" class="muted">未启动</span></div>
      <div class="body">
        <label>搜索主题</label>
        <textarea id="agentQueries" style="min-height:180px"></textarea>
        <div class="row">
          <div>
            <label>间隔秒数</label>
            <input id="agentInterval" type="number" min="30" step="10" value="60">
          </div>
          <div>
            <label>目标池</label>
            <input id="poolSize" value="300" disabled>
          </div>
        </div>
        <div class="toolbar" style="margin-top:12px">
          <button id="agentStart" class="primary">启动</button>
          <button id="agentStop">停止</button>
        </div>
        <p class="muted">Agent 会主动搜索公开资料，清洗后每分钟尝试生成 1 条策略；审核通过才入池，策略池始终维持 300 条。</p>
        <div class="card">
          <p><strong>运行：</strong><span id="agentRunInfo">-</span></p>
          <p><strong>统计：</strong><span id="agentStats">-</span></p>
          <p><strong>最近资料：</strong><span id="agentMaterial">-</span></p>
          <p><strong>最近策略：</strong><span id="agentStrategy">-</span></p>
        </div>
        <div id="agentLogs"></div>
      </div>
    </section>
    <section>
      <div class="section-head"><h2>输入</h2><span class="muted">PDF / TXT / Markdown</span></div>
      <div class="body">
        <label>资料名称</label>
        <input id="sourceName" value="输入资料">
        <label>上传文件</label>
        <input id="fileInput" type="file" accept=".pdf,.txt,.md,.markdown,text/plain,application/pdf">
        <label>文本</label>
        <textarea id="sourceText"></textarea>
        <div class="row">
          <div>
            <label>每条字数</label>
            <input id="chunkSize" type="number" min="500" step="100" value="2000">
          </div>
          <div>
            <label>模型</label>
            <input id="modelName" value="">
          </div>
        </div>
        <label>API Key</label>
        <input id="apiKey" type="password" autocomplete="off" placeholder="可留空使用环境变量 OPENAI_API_KEY">
        <label>API Base URL</label>
        <input id="apiBaseUrl" placeholder="https://api.openai.com/v1">
        <label><input id="reviewOnGenerate" type="checkbox" style="width:auto"> 生成时立即 AI 审核（关闭后每条倒计时 10 秒自动审核）</label>
        <div class="toolbar" style="margin-top:12px">
          <button id="testConnectionBtn">测试连接</button>
          <button id="generateBtn" class="primary">生成策略</button>
          <button id="clearBtn">清空</button>
        </div>
        <p id="inputStatus" class="status"></p>
        <div class="card">
          <h3>策略选择</h3>
          <label>当前状况</label>
          <textarea id="situationText" style="min-height:150px" placeholder="例如：对方刚回复了 Story，但语气很短，我不确定该继续问还是先给资源。"></textarea>
          <div class="row">
            <div>
              <label>会话 ID</label>
              <input id="sessionId" value="default">
            </div>
            <div>
              <label>Embedding</label>
              <input id="embeddingModel" value="">
            </div>
          </div>
          <div class="toolbar" style="margin-top:12px">
            <button id="selectStrategyBtn" class="primary">选择一个策略</button>
          </div>
          <div id="selectionResult" style="margin-top:10px"><div class="empty">等待当前状况</div></div>
        </div>
      </div>
    </section>
    <section>
      <div class="section-head"><h2>生成策略</h2><span id="generatedCount" class="muted">0 条</span></div>
      <div id="generatedList" class="body"><div class="empty">等待生成</div></div>
    </section>
    <section>
      <div class="section-head"><h2>策略库</h2><span id="libraryCount" class="muted"></span></div>
      <div class="tabs">
        <button data-type="stage" class="active">阶段</button>
        <button data-type="goal">目标</button>
        <button data-type="format">形式</button>
        <button data-type="psychology">心理</button>
      </div>
      <div class="body">
        <label>分类</label>
        <select id="categorySelect"></select>
        <label>搜索</label>
        <input id="librarySearch" placeholder="私信 信任 边界">
        <div id="libraryList" class="library-list" style="margin-top:12px"></div>
      </div>
    </section>
  </main>
  <script>
    const state = {
      meta: null,
      generated: [],
      activeType: 'stage',
      reviewTimers: {},
      reviewDeadlines: {},
      reviewing: {},
      autoReviewErrors: {}
    };
    const $ = (id) => document.getElementById(id);

    function esc(value) {
      return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    async function request(path, options = {}) {
      const res = await fetch(path, options);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
      return data;
    }

    function syncAgentStrategies(status) {
      const incoming = status.recent_strategies || (status.last_strategy ? [status.last_strategy] : []);
      if (!incoming.length) return;
      const existing = new Set(state.generated.map(item => item.id));
      const additions = incoming.filter(item => item && item.id && !existing.has(item.id));
      if (!additions.length) return;
      state.generated = [...additions, ...state.generated].slice(0, 30);
      renderGenerated();
    }

    function renderAgentStatus(status) {
      $('agentState').textContent = status.running ? (status.busy ? '运行中' : '等待中') : '未启动';
      $('agentRunInfo').textContent = status.running ? `上次 ${status.last_run || '-'} / 下次 ${status.next_run || '-'}` : '已停止';
      $('agentStats').textContent = `生成 ${status.generated_count} / 入池 ${status.accepted_count} / 拒绝 ${status.rejected_count} / 删除 ${status.deleted_count} / 当前 ${status.pool_size}`;
      const material = status.last_material;
      $('agentMaterial').textContent = material ? `${material.title || material.query || '-'} ${material.url || ''}` : '-';
      const lastStrategy = status.last_strategy;
      $('agentStrategy').textContent = lastStrategy ? `${lastStrategy.id || ''} ${lastStrategy.title || ''}` : '-';
      syncAgentStrategies(status);
      $('agentLogs').innerHTML = (status.logs || []).map(log => `
        <div class="small-card">
          <strong>${esc(log.time)} ${esc(log.level)}</strong>
          <p>${esc(log.message)}</p>
          ${log.strategy_id ? `<p>${esc(log.strategy_id)}</p>` : ''}
          ${log.removed_id ? `<p>移出：${esc(log.removed_id)} ${esc(log.reason || '')}</p>` : ''}
        </div>
      `).join('') || '<div class="empty">暂无日志</div>';
    }

    async function loadAgentStatus() {
      const data = await request('/api/agent/status');
      renderAgentStatus(data.status);
    }

    async function startAgent() {
      $('inputStatus').textContent = '启动 Agent...';
      try {
        const data = await request('/api/agent/start', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            api_key: $('apiKey').value.trim(),
            api_base_url: $('apiBaseUrl').value.trim(),
            model: $('modelName').value.trim(),
            interval_seconds: Number($('agentInterval').value || 60),
            queries: $('agentQueries').value.split('\n').map(x => x.trim()).filter(Boolean)
          })
        });
        renderAgentStatus(data.status);
        $('inputStatus').textContent = 'Agent 已启动';
      } catch (err) {
        $('inputStatus').textContent = err.message;
      }
    }

    async function stopAgent() {
      const data = await request('/api/agent/stop', {method: 'POST'});
      renderAgentStatus(data.status);
      $('inputStatus').textContent = 'Agent 已停止';
    }

    function pill(text, cls = '') {
      return `<span class="pill ${cls}">${esc(text)}</span>`;
    }

    function strategyKey(strategy, index) {
      return strategy && strategy.id ? strategy.id : `strategy-${index}`;
    }

    function clearReviewTimer(key) {
      if (state.reviewTimers[key]) {
        clearInterval(state.reviewTimers[key]);
        delete state.reviewTimers[key];
      }
      delete state.reviewDeadlines[key];
    }

    function reviewCountdownText(key) {
      if (state.reviewing[key]) return 'AI 审核中';
      if (state.autoReviewErrors[key]) return '自动审核失败';
      const deadline = state.reviewDeadlines[key];
      if (!deadline) return '10秒后自动审核';
      const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      return seconds > 0 ? `${seconds}秒后自动AI审核` : '自动AI审核中';
    }

    function updateReviewCountdowns() {
      document.querySelectorAll('[data-countdown-key]').forEach(node => {
        node.textContent = reviewCountdownText(node.dataset.countdownKey);
      });
    }

    function reviewPill(strategy, index) {
      const review = strategy.review;
      const key = strategyKey(strategy, index);
      if (!review) return `<span class="pill warn" data-countdown-key="${esc(key)}">${esc(reviewCountdownText(key))}</span>`;
      if (review.can_add) return pill(`可加入 ${review.score}`, 'ok');
      if (review.status === 'reject') return pill(`拒绝 ${review.score}`, 'bad');
      return pill(`需修改 ${review.score}`, 'warn');
    }

    function scheduleAutoReview(index) {
      const strategy = state.generated[index];
      if (!strategy || strategy.review) return;
      const key = strategyKey(strategy, index);
      if (state.reviewTimers[key] || state.reviewing[key] || state.autoReviewErrors[key]) return;
      state.reviewDeadlines[key] = Date.now() + 10000;
      state.reviewTimers[key] = setInterval(() => {
        updateReviewCountdowns();
        if (Date.now() >= state.reviewDeadlines[key]) {
          clearReviewTimer(key);
          autoReviewOne(key);
        }
      }, 500);
      updateReviewCountdowns();
    }

    function scheduleAutoReviews() {
      state.generated.forEach((strategy, index) => {
        if (strategy && strategy.review) clearReviewTimer(strategyKey(strategy, index));
        else scheduleAutoReview(index);
      });
    }

    async function autoReviewOne(key) {
      const index = state.generated.findIndex((strategy, idx) => strategyKey(strategy, idx) === key && !strategy.review);
      if (index < 0) return;
      await reviewOne(index, {auto: true});
    }

    function renderGenerated() {
      $('generatedCount').textContent = `${state.generated.length} 条`;
      if (!state.generated.length) {
        $('generatedList').innerHTML = '<div class="empty">等待生成</div>';
        return;
      }
      $('generatedList').innerHTML = state.generated.map((s, i) => `
        <article class="card">
          <h3>${esc(s.id)} ${esc(s.title)}</h3>
          <div class="meta">
            ${pill(`${s.stage} ${s.stage_name}`)}
            ${(s.goals || []).map(x => pill(x)).join('')}
            ${(s.formats || []).map(x => pill(x)).join('')}
            ${reviewPill(s, i)}
          </div>
          <p><strong>核心判断：</strong>${esc(s.principle)}</p>
          <p><strong>资料依据：</strong>${esc(s.evidence_summary || '')}</p>
          <p><strong>新增价值：</strong>${esc(s.novelty_angle || '')}</p>
          <ol>${(s.actions || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>
          ${s.review ? `
            <p><strong>AI 审核：</strong>${esc(s.review.library_note || '')}</p>
            <ul>${(s.review.reasons || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
          ` : ''}
          <div class="toolbar">
            <button data-review="${i}">AI 审核</button>
            <button class="good" data-add="${i}" ${s.review && s.review.can_add ? '' : 'disabled'}>加入策略库</button>
          </div>
        </article>
      `).join('');
      document.querySelectorAll('[data-review]').forEach(btn => btn.onclick = () => reviewOne(Number(btn.dataset.review)));
      document.querySelectorAll('[data-add]').forEach(btn => btn.onclick = () => addOne(Number(btn.dataset.add)));
      scheduleAutoReviews();
    }

    async function reviewOne(index, options = {}) {
      const strategy = state.generated[index];
      if (!strategy || strategy.review) return;
      const key = strategyKey(strategy, index);
      clearReviewTimer(key);
      state.reviewing[key] = true;
      delete state.autoReviewErrors[key];
      renderGenerated();
      $('inputStatus').textContent = options.auto ? '倒计时结束，自动 AI 审核中...' : 'AI 审核中...';
      try {
        const model = $('modelName').value.trim();
        const apiKey = $('apiKey').value.trim();
        const apiBaseUrl = $('apiBaseUrl').value.trim();
        const data = await request('/api/review', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({strategy, model, api_key: apiKey, api_base_url: apiBaseUrl})
        });
        const currentIndex = state.generated.findIndex((item, idx) => strategyKey(item, idx) === key);
        if (currentIndex >= 0) state.generated[currentIndex].review = data.review;
        renderGenerated();
        $('inputStatus').textContent = options.auto ? '自动审核完成' : '审核完成';
      } catch (err) {
        state.autoReviewErrors[key] = err.message;
        renderGenerated();
        $('inputStatus').textContent = err.message;
      } finally {
        delete state.reviewing[key];
        updateReviewCountdowns();
      }
    }

    async function addOne(index) {
      $('inputStatus').textContent = '写入策略库...';
      try {
        const data = await request('/api/add', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            strategy: state.generated[index],
            api_key: $('apiKey').value.trim(),
            api_base_url: $('apiBaseUrl').value.trim(),
            model: $('modelName').value.trim()
          })
        });
        state.generated[index] = data.strategy;
        renderGenerated();
        await loadMeta();
        await loadLibrary();
        $('inputStatus').textContent = `已加入：${data.strategy.id}`;
      } catch (err) {
        $('inputStatus').textContent = err.message;
      }
    }

    async function generate() {
      const form = new FormData();
      form.append('source_name', $('sourceName').value.trim() || '输入资料');
      form.append('text', $('sourceText').value);
      form.append('chunk_size', $('chunkSize').value || '2000');
      form.append('model', $('modelName').value.trim());
      form.append('api_key', $('apiKey').value.trim());
      form.append('api_base_url', $('apiBaseUrl').value.trim());
      form.append('review', $('reviewOnGenerate').checked ? '1' : '0');
      if ($('fileInput').files[0]) form.append('file', $('fileInput').files[0]);
      $('generateBtn').disabled = true;
      $('inputStatus').textContent = 'AI 生成中...';
      try {
        const data = await request('/api/generate', {method: 'POST', body: form});
        Object.keys(state.reviewTimers).forEach(clearReviewTimer);
        state.reviewing = {};
        state.autoReviewErrors = {};
        state.generated = data.strategies;
        renderGenerated();
        $('inputStatus').textContent = `完成：${data.strategies.length} 条`;
      } catch (err) {
        $('inputStatus').textContent = err.message;
      } finally {
        $('generateBtn').disabled = false;
      }
    }

    async function testConnection() {
      $('inputStatus').textContent = '正在测试 chat/completions...';
      $('testConnectionBtn').disabled = true;
      try {
        const data = await request('/api/test-connection', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            api_key: $('apiKey').value.trim(),
            api_base_url: $('apiBaseUrl').value.trim(),
            model: $('modelName').value.trim()
          })
        });
        $('inputStatus').textContent = `连接成功：${data.result.model} @ ${data.result.endpoint}`;
      } catch (err) {
        $('inputStatus').textContent = err.message;
      } finally {
        $('testConnectionBtn').disabled = false;
      }
    }

    function renderSelection(result) {
      const strategy = result.selected_strategy || {};
      const selection = result.selection || {};
      const stage = result.stage_analysis || {};
      $('selectionResult').innerHTML = `
        <article class="small-card">
          <strong>${esc(strategy.id)} ${esc(strategy.title)}</strong>
          <div class="meta">
            ${pill(`${stage.stage || strategy.stage} ${strategy.stage_name || ''}`)}
            ${pill(`置信度 ${selection.selection_confidence ?? '-'}`)}
          </div>
          <p><strong>阶段判断：</strong>${esc(stage.matched_condition || '')}</p>
          <p><strong>当前分析：</strong>${esc(selection.situation_analysis || '')}</p>
          <p><strong>上次影响：</strong>${esc(selection.previous_context_effect || '')}</p>
          <p><strong>为什么选：</strong>${esc(selection.why_this_strategy || '')}</p>
          <p><strong>召回方式：</strong>${esc(result.retrieval_mode || 'embedding')}${result.embedding_error ? `（${esc(result.embedding_error)}）` : ''}</p>
          <p><strong>第一步：</strong>${esc(selection.first_action || '')}</p>
          <ol>${(selection.execution_plan || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>
          <p><strong>边界：</strong>${esc(selection.risk_boundary || '')}</p>
          <p><strong>观察：</strong>${esc(selection.next_observation || '')}</p>
        </article>
      `;
    }

    async function selectStrategy() {
      $('inputStatus').textContent = '正在用 embedding + LLM 选择策略...';
      $('selectStrategyBtn').disabled = true;
      try {
        const data = await request('/api/select-strategy', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            situation: $('situationText').value,
            session_id: $('sessionId').value.trim() || 'default',
            model: $('modelName').value.trim(),
            embedding_model: $('embeddingModel').value.trim(),
            api_base_url: $('apiBaseUrl').value.trim(),
            api_key: $('apiKey').value.trim()
          })
        });
        renderSelection(data.result);
        $('inputStatus').textContent = `已选择：${data.result.selected_strategy.id}`;
      } catch (err) {
        $('selectionResult').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
        $('inputStatus').textContent = err.message;
      } finally {
        $('selectStrategyBtn').disabled = false;
      }
    }

    function fillCategories() {
      const select = $('categorySelect');
      const type = state.activeType;
      const labels = state.meta.labels[type];
      const counts = state.meta.counts[type];
      select.innerHTML = '<option value="">全部</option>' + Object.entries(labels).map(([key, label]) => {
        const count = counts[key] || 0;
        return `<option value="${esc(key)}">${esc(label)} (${count})</option>`;
      }).join('');
    }

    async function loadMeta() {
      state.meta = await request('/api/meta');
      $('apiState').textContent = state.meta.api_key_present ? `模型：${state.meta.default_model}` : '未设置 OPENAI_API_KEY';
      if (!$('modelName').value) $('modelName').value = state.meta.default_model;
      if (!$('apiBaseUrl').value) $('apiBaseUrl').value = state.meta.default_api_base_url || 'https://api.openai.com/v1';
      if (!$('embeddingModel').value) $('embeddingModel').value = state.meta.default_embedding_model || 'text-embedding-3-small';
      if (!$('agentQueries').value) $('agentQueries').value = (state.meta.default_research_queries || []).join('\n');
      fillCategories();
    }

    async function loadLibrary() {
      const params = new URLSearchParams({
        type: state.activeType,
        value: $('categorySelect').value,
        q: $('librarySearch').value.trim(),
        limit: '80'
      });
      const data = await request(`/api/strategies?${params.toString()}`);
      $('libraryCount').textContent = `${data.total} 条`;
      $('libraryList').innerHTML = data.strategies.length ? data.strategies.map(s => `
        <article class="small-card">
          <strong>${esc(s.id)} ${esc(s.title)}</strong>
          <div class="meta">${pill(`${s.stage} ${s.stage_name}`)} ${(s.formats || []).slice(0,2).map(x => pill(x)).join('')}</div>
          <p>${esc(s.principle || '')}</p>
        </article>
      `).join('') : '<div class="empty">没有匹配策略</div>';
    }

    document.querySelectorAll('.tabs button').forEach(btn => {
      btn.onclick = async () => {
        document.querySelectorAll('.tabs button').forEach(x => x.classList.remove('active'));
        btn.classList.add('active');
        state.activeType = btn.dataset.type;
        fillCategories();
        await loadLibrary();
      };
    });
    $('categorySelect').onchange = loadLibrary;
    $('librarySearch').oninput = () => {
      clearTimeout(window.__libraryTimer);
      window.__libraryTimer = setTimeout(loadLibrary, 250);
    };
    $('generateBtn').onclick = generate;
    $('testConnectionBtn').onclick = testConnection;
    $('selectStrategyBtn').onclick = selectStrategy;
    $('agentStart').onclick = startAgent;
    $('agentStop').onclick = stopAgent;
    $('clearBtn').onclick = () => {
      $('sourceText').value = '';
      $('fileInput').value = '';
      state.generated = [];
      Object.keys(state.reviewTimers).forEach(clearReviewTimer);
      renderGenerated();
      $('inputStatus').textContent = '';
    };

    (async () => {
      await loadMeta();
      await loadLibrary();
      await loadAgentStatus();
      setInterval(() => loadAgentStatus().catch(() => {}), 5000);
    })().catch(err => $('apiState').textContent = err.message);
  </script>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    server_version = "RelationshipStrategyGenerator/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or 0)
        return self.rfile.read(length)

    def send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_html(self, html: str) -> None:
        payload = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def handle_error(self, exc: Exception) -> None:
        self.send_json({"error": str(exc)}, status=400)

    def do_GET(self) -> None:
        try:
            path = self.path.split("?", 1)[0]
            if path == "/":
                self.send_html(APP_HTML)
                return
            if path == "/api/meta":
                cards = load_all_cards()
                self.send_json(
                    {
                        "default_model": DEFAULT_MODEL,
                        "default_api_base_url": DEFAULT_API_BASE_URL,
                        "default_api_style": "responses" if use_responses_api(DEFAULT_API_BASE_URL) else "chat",
                        "default_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                        "api_key_present": bool(os.getenv("OPENAI_API_KEY")),
                        "counts": category_counts(cards),
                        "labels": {
                            "stage": {key: f"{key} {value}" for key, value in STAGES.items()},
                            "goal": {key: key for key in GOALS},
                            "format": {key: key for key in FORMATS},
                            "psychology": {key: key for key in PSYCHOLOGY},
                        },
                        "default_research_queries": DEFAULT_RESEARCH_QUERIES,
                    }
                )
                return
            if path == "/api/agent/status":
                self.send_json({"status": RESEARCH_AGENT.status()})
                return
            if path == "/api/strategies":
                query = parse_query(self.path)
                cards = query_cards(
                    query.get("type", ""),
                    query.get("value", ""),
                    query.get("q", ""),
                    int(query.get("limit", "80") or 80),
                )
                self.send_json({"total": len(cards), "strategies": cards})
                return
            self.send_json({"error": "Not found"}, status=404)
        except Exception as exc:
            self.handle_error(exc)

    def do_POST(self) -> None:
        try:
            path = self.path.split("?", 1)[0]
            if path == "/api/generate":
                fields = parse_multipart(self.read_body(), self.headers.get("Content-Type", ""))
                text = str(fields.get("text", "") or "")
                upload = fields.get("file")
                if isinstance(upload, dict) and upload.get("data"):
                    filename = upload.get("filename", "")
                    if str(filename).lower().endswith(".pdf"):
                        text = extract_pdf_text(upload["data"])
                    else:
                        text = decode_text_bytes(upload["data"])
                source_name = str(fields.get("source_name", "输入资料") or "输入资料")
                chunk_size = int(fields.get("chunk_size", "2000") or 2000)
                model = str(fields.get("model", "") or "").strip() or None
                api_key = str(fields.get("api_key", "") or "").strip() or None
                api_base_url = str(fields.get("api_base_url", "") or "").strip() or None
                review = str(fields.get("review", "0")) == "1"
                strategies = generate_strategies(
                    text,
                    source_name=source_name,
                    chunk_size=chunk_size,
                    id_prefix=f"RSG-{int(time.time())}",
                    model=model,
                    api_key=api_key,
                    api_base_url=api_base_url,
                    review=review,
                )
                self.send_json({"strategies": strategies})
                return
            body = json.loads(self.read_body().decode("utf-8"))
            if path == "/api/test-connection":
                result = test_chat_connection(
                    model=body.get("model") or None,
                    api_key=body.get("api_key") or None,
                    api_base_url=body.get("api_base_url") or None,
                )
                self.send_json({"result": result})
                return
            if path == "/api/review":
                model = body.get("model") or None
                api_key = body.get("api_key") or None
                api_base_url = body.get("api_base_url") or None
                review = audit_strategy(body["strategy"], model=model, api_key=api_key, api_base_url=api_base_url)
                self.send_json({"review": review})
                return
            if path == "/api/add":
                card = save_user_strategy(
                    body["strategy"],
                    model=body.get("model") or None,
                    api_key=body.get("api_key") or None,
                    api_base_url=body.get("api_base_url") or None,
                )
                self.send_json({"strategy": card})
                return
            if path == "/api/select-strategy":
                from strategy_selector import select_strategy

                result = select_strategy(
                    body.get("situation", ""),
                    session_id=body.get("session_id") or "default",
                    model=body.get("model") or None,
                    embedding_model=body.get("embedding_model") or None,
                    api_base_url=body.get("api_base_url") or None,
                    api_key=body.get("api_key") or None,
                    save=True,
                )
                self.send_json({"result": result})
                return
            if path == "/api/delete":
                card = delete_strategy(body["id"], body.get("reason", "AI 审核删除"))
                self.send_json({"deleted": card, "pool_size": len(load_active_pool())})
                return
            if path == "/api/agent/start":
                queries = body.get("queries") or DEFAULT_RESEARCH_QUERIES
                if isinstance(queries, str):
                    queries = queries.splitlines()
                RESEARCH_AGENT.start(
                    interval_seconds=int(body.get("interval_seconds", 60) or 60),
                    model=body.get("model") or None,
                    api_key=body.get("api_key") or None,
                    api_base_url=body.get("api_base_url") or None,
                    queries=queries,
                )
                self.send_json({"status": RESEARCH_AGENT.status()})
                return
            if path == "/api/agent/stop":
                RESEARCH_AGENT.stop()
                self.send_json({"status": RESEARCH_AGENT.status()})
                return
            self.send_json({"error": "Not found"}, status=404)
        except Exception as exc:
            self.handle_error(exc)


def serve(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"AI relationship strategy generator: http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI strategy generator for social-platform relationship building.")
    parser.add_argument("--input", "-i", default="-", help="Input text/Markdown/PDF file. Use '-' for stdin.")
    parser.add_argument("--output", "-o", help="Write combined Markdown output.")
    parser.add_argument("--json-output", help="Write machine-readable JSON output.")
    parser.add_argument("--cards-dir", help="Optional directory for individual Markdown strategy cards.")
    parser.add_argument("--source-name", default="输入资料", help="Source name shown in generated strategies.")
    parser.add_argument("--chunk-size", type=int, default=2000, help="Approximate non-space characters per strategy.")
    parser.add_argument("--id-prefix", default="RSG", help="Generated strategy id prefix.")
    parser.add_argument("--model", default="", help=f"OpenAI model. Defaults to OPENAI_MODEL or {DEFAULT_MODEL}.")
    parser.add_argument("--api-key", default="", help="OpenAI API key. Defaults to OPENAI_API_KEY.")
    parser.add_argument("--api-base-url", default="", help=f"OpenAI-compatible API base URL. Defaults to {DEFAULT_API_BASE_URL}.")
    parser.add_argument("--review", action="store_true", help="Run AI review for each generated strategy.")
    parser.add_argument("--max-chunks", type=int, help="Limit chunks for testing.")
    parser.add_argument("--serve", action="store_true", help="Start the local visual interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.serve:
        serve(args.host, args.port)
        return

    if args.chunk_size < 500:
        raise SystemExit("--chunk-size should be at least 500 to avoid over-fragmented strategies.")

    text = read_input(args.input)
    strategies = generate_strategies(
        text,
        source_name=args.source_name,
        chunk_size=args.chunk_size,
        id_prefix=args.id_prefix,
        model=args.model or None,
        api_key=args.api_key or None,
        api_base_url=args.api_base_url or None,
        review=args.review,
        max_chunks=args.max_chunks,
    )
    markdown = render_markdown(strategies, args.source_name)

    if args.output:
        Path(args.output).write_text(markdown.rstrip() + "\n", encoding="utf-8")
    else:
        print(markdown)

    if args.json_output:
        Path(args.json_output).write_text(json.dumps(strategies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.cards_dir:
        write_cards(Path(args.cards_dir), strategies)


if __name__ == "__main__":
    main()
