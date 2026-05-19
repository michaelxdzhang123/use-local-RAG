"""Pretty-print RAGFlow MCP retrieval output as Markdown.

Usage:
    export RAGFLOW_MCP_URL="http://172.28.21.22:9382/mcp/"
    export RAGFLOW_TOOL_NAME="ragflow_retrieval"
    export RAGFLOW_DATASET_IDS="c01c944642d611f1847e7fab85a8d86d"
    python pretty_streamMCP.py "介绍天洑工业AI底座?"

Optional:
    export RAGFLOW_API_KEY="ragflow-..."       # only when MCP is in host mode
    export RAGFLOW_AUTH_MODE="bearer"          # bearer | api_key | none
    export RAGFLOW_DOCUMENT_IDS="docid1,docid2"
    export RAGFLOW_TOP_N="8"
"""

from __future__ import annotations

import ast
import json
import os
import sys
import textwrap
from typing import Any

from anyio import run
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def env_list(name: str) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_payload_from_response_dump(response_dump: dict[str, Any]) -> dict[str, Any]:
    """Extract the JSON payload from an MCP response.model_dump()."""
    if response_dump.get("isError"):
        raise RuntimeError(f"MCP tool returned isError=True: {response_dump}")

    content_items = response_dump.get("content") or []
    text_blobs: list[str] = []
    for item in content_items:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                text_blobs.append(text.strip())

    if not text_blobs:
        raise ValueError(f"No text payload found in MCP response: {response_dump}")

    last_error: Exception | None = None
    for text in text_blobs:
        for parser in (json.loads, ast.literal_eval):
            try:
                payload = parser(text)
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if isinstance(payload, dict):
                    return payload
            except Exception as exc:  # noqa: BLE001 - keep trying parsers
                last_error = exc

    raise ValueError(f"Could not parse MCP text payload. Last error: {last_error}")


def get_chunks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("chunks"), list):
        return payload["chunks"]
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("chunks"), list):
        return data["chunks"]
    return []


def get_pagination(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("pagination")
    return value if isinstance(value, dict) else {}


def get_query_info(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("query_info")
    return value if isinstance(value, dict) else {}


def clip(text: Any, limit: int = 420) -> str:
    s = " ".join(str(text or "").split())
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def fmt_score(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:  # noqa: BLE001
        return ""


def doc_name(chunk: dict[str, Any]) -> str:
    meta = chunk.get("document_metadata") if isinstance(chunk.get("document_metadata"), dict) else {}
    return str(
        chunk.get("document_name")
        or chunk.get("document_keyword")
        or meta.get("name")
        or chunk.get("document_id")
        or "unknown"
    )


def chunk_type(chunk: dict[str, Any]) -> str:
    meta = chunk.get("document_metadata") if isinstance(chunk.get("document_metadata"), dict) else {}
    return str(chunk.get("doc_type_kwd") or meta.get("type") or "unknown")


def keyword_text(chunk: dict[str, Any], max_items: int = 4) -> str:
    keywords = chunk.get("important_keywords")
    if isinstance(keywords, list):
        return ", ".join(str(k).strip() for k in keywords[:max_items] if str(k).strip())
    return ""


def markdown_from_payload(payload: dict[str, Any], top_n: int = 8) -> str:
    chunks = get_chunks(payload)
    pagination = get_pagination(payload)
    query = get_query_info(payload)

    chunks_sorted = sorted(
        chunks,
        key=lambda c: float(c.get("similarity") or 0.0) if isinstance(c, dict) else 0.0,
        reverse=True,
    )[:top_n]

    lines: list[str] = []
    lines.append("# RAGFlow MCP 检索结果")
    lines.append("")
    lines.append("## 检索摘要")
    lines.append("")
    lines.append(f"- 问题：{query.get('question', '')}")
    lines.append(f"- 数据集数量：{query.get('dataset_count', '')}")
    lines.append(f"- 命中片段：{pagination.get('total_chunks', len(chunks))}")
    lines.append(f"- 当前页：{pagination.get('page', '')} / {pagination.get('total_pages', '')}")
    lines.append(f"- 相似度阈值：{query.get('similarity_threshold', '')}")
    lines.append(f"- 向量权重：{query.get('vector_weight', '')}")
    lines.append(f"- 关键词检索：{query.get('keyword_search', '')}")
    lines.append("")

    lines.append("## Top 检索片段")
    lines.append("")
    lines.append("| # | similarity | dataset | document | type | chunk_id | keywords |")
    lines.append("|---:|---:|---|---|---|---|---|")
    for i, c in enumerate(chunks_sorted, 1):
        lines.append(
            "| {i} | {sim} | {dataset} | {doc} | {typ} | `{cid}` | {kw} |".format(
                i=i,
                sim=fmt_score(c.get("similarity")),
                dataset=clip(c.get("dataset_name"), 40),
                doc=clip(doc_name(c), 48),
                typ=chunk_type(c),
                cid=clip(c.get("id"), 20),
                kw=clip(keyword_text(c), 50),
            )
        )
    lines.append("")

    weak_scores = [float(c.get("similarity") or 0) for c in chunks_sorted if isinstance(c, dict)]
    if weak_scores and max(weak_scores) < 0.35:
        lines.append("> 注意：最高 similarity 低于 0.35，相关性偏弱；建议继续优化 query 或扩大检索关键词。")
        lines.append("")

    lines.append("## 证据片段")
    lines.append("")
    for i, c in enumerate(chunks_sorted, 1):
        meta = c.get("document_metadata") if isinstance(c.get("document_metadata"), dict) else {}
        lines.append(f"### [{i}] {doc_name(c)}")
        lines.append("")
        lines.append(f"- dataset: {c.get('dataset_name', '')}")
        lines.append(f"- chunk: `{c.get('id', '')}`")
        lines.append(f"- document_id: `{c.get('document_id', '')}`")
        lines.append(f"- type: {chunk_type(c)}")
        lines.append(f"- similarity: {fmt_score(c.get('similarity'))}")
        if c.get("term_similarity") is not None or c.get("vector_similarity") is not None:
            lines.append(
                f"- term/vector: {fmt_score(c.get('term_similarity'))} / {fmt_score(c.get('vector_similarity'))}"
            )
        if c.get("image_id"):
            lines.append(f"- image_id: `{c.get('image_id')}`")
        if meta.get("update_date"):
            lines.append(f"- document_update_date: {meta.get('update_date')}")
        lines.append("")
        lines.append("> " + clip(c.get("content"), 500))
        lines.append("")

    return "\n".join(lines)


def auth_headers() -> dict[str, str] | None:
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip()
    mode = os.getenv("RAGFLOW_AUTH_MODE", "none").strip().lower()
    if not api_key or mode == "none":
        return None
    if mode == "bearer":
        return {"Authorization": f"Bearer {api_key}"}
    if mode == "api_key":
        return {"api_key": api_key}
    raise ValueError("RAGFLOW_AUTH_MODE must be one of: none, bearer, api_key")


async def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = input("RAGFlow question> ").strip()
    if not question:
        raise SystemExit("question is required")

    mcp_url = os.getenv("RAGFLOW_MCP_URL", "http://172.28.21.22:9382/mcp/")
    tool_name = os.getenv("RAGFLOW_TOOL_NAME", "ragflow_retrieval")
    dataset_ids = env_list("RAGFLOW_DATASET_IDS")
    document_ids = env_list("RAGFLOW_DOCUMENT_IDS")
    top_n = int(os.getenv("RAGFLOW_TOP_N", "8"))

    if not dataset_ids:
        raise SystemExit("Please set RAGFLOW_DATASET_IDS, e.g. export RAGFLOW_DATASET_IDS='dataset_id_1,dataset_id_2'")

    client_kwargs: dict[str, Any] = {}
    headers = auth_headers()
    if headers:
        client_kwargs["headers"] = headers

    async with streamable_http_client(mcp_url, **client_kwargs) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            available = [tool.name for tool in tools.tools]
            if tool_name not in available:
                print(f"Available tools: {available}", file=sys.stderr)
                raise SystemExit(f"Tool '{tool_name}' not found")

            response = await session.call_tool(
                name=tool_name,
                arguments={
                    "dataset_ids": dataset_ids,
                    "document_ids": document_ids,
                    "question": question,
                },
            )

    payload = parse_payload_from_response_dump(response.model_dump())
    print(markdown_from_payload(payload, top_n=top_n))


if __name__ == "__main__":
    run(main)
