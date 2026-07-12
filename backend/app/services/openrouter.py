"""
OpenRouter Chat Completions 클라이언트.

역할:
- 회의록 원문을 보내 JSON 문자열을 받는다
- 키/모델은 config에서만 읽는다
- 응답 본문에서 content를 꺼내 반환 (파싱·검증은 structure 서비스)
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """당신은 회의록 구조화 도우미입니다.
주어진 회의록 원문에 실제로 적힌 내용만 추출하세요.
없는 담당자·기한·결정·논의를 지어내지 마세요. 없으면 null 또는 빈 배열을 쓰세요.

반드시 아래 JSON 객체만 출력하세요. 설명 문장이나 코드펜스는 넣지 마세요.
{
  "decisions": ["결정사항 문자열"],
  "discussions": ["논의사항 문자열"],
  "action_items": [
    {"task": "할 일", "assignee": "담당자 또는 null", "due_date": "YYYY-MM-DD 또는 null"}
  ]
}
"""


class OpenRouterError(Exception):
    """OpenRouter 호출 또는 응답 형식 오류."""


def _require_api_key() -> str:
    if not OPENROUTER_API_KEY.strip():
        raise OpenRouterError("OPENROUTER_API_KEY is not set")
    return OPENROUTER_API_KEY.strip()


def _extract_message_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError(f"Unexpected OpenRouter response shape: {payload!r}") from exc

    if isinstance(content, list):
        # 일부 모델은 content를 파트 배열로 반환
        texts = [part.get("text", "") for part in content if isinstance(part, dict)]
        content = "".join(texts)

    if not isinstance(content, str) or not content.strip():
        raise OpenRouterError("OpenRouter returned empty content")
    return content.strip()


def strip_json_fences(text: str) -> str:
    """```json ... ``` 감싸기가 있으면 벗긴다."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


async def complete_meeting_structure(raw_text: str, *, title: str | None = None) -> str:
    """회의록 원문을 OpenRouter에 보내고, assistant content(JSON 문자열)를 반환."""
    api_key = _require_api_key()
    user_parts = []
    if title:
        user_parts.append(f"회의 제목: {title}")
    user_parts.append("회의록 원문:")
    user_parts.append(raw_text)
    user_content = "\n".join(user_parts)

    body: dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        # 가능하면 JSON만 오도록 유도. 미지원 모델은 서버가 무시할 수 있음.
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Meeting Action Tracker",
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        raise OpenRouterError("OpenRouter request timed out") from exc
    except httpx.HTTPError as exc:
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

    if response.status_code >= 400:
        raise OpenRouterError(
            f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter returned non-JSON body") from exc

    return strip_json_fences(_extract_message_content(payload))
