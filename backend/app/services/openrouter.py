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

from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_TIMEOUT_SECONDS

# OpenRouter Chat Completions API의 고정 URL
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# 모델에게 주는 시스템 지시문.
# 원문에 있는 내용만 뽑고, 없는 정보는 만들지 말라고 명시한다.
# 출력은 지정한 JSON 객체만 하도록 한다.
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
    # 키가 비어 있으면 바로 오류를 낸다. 빈 문자열로 요청을 보내지 않기 위함이다.
    if not OPENROUTER_API_KEY.strip():
        raise OpenRouterError("OPENROUTER_API_KEY is not set")
    # 앞뒤 공백을 제거한 키를 반환한다.
    return OPENROUTER_API_KEY.strip()


def _extract_message_content(payload: dict[str, Any]) -> str:
    # OpenRouter 응답에서 assistant 메시지 본문을 꺼낸다.
    # 정상 형식: choices[0].message.content
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        # 키가 없거나 배열이 비어 있거나 타입이 다르면 형식 오류로 처리한다.
        raise OpenRouterError(f"Unexpected OpenRouter response shape: {payload!r}") from exc

    if isinstance(content, list):
        # 일부 모델은 content를 문자열 대신 파트 배열로 반환한다.
        # dict 파트에서 text 필드만 모아 하나의 문자열로 합친다.
        texts = [part.get("text", "") for part in content if isinstance(part, dict)]
        content = "".join(texts)

    # 최종 content가 문자열이 아니거나 내용이 비어 있으면 오류다.
    if not isinstance(content, str) or not content.strip():
        raise OpenRouterError("OpenRouter returned empty content")
    return content.strip()


def strip_json_fences(text: str) -> str:
    """```json ... ``` 감싸기가 있으면 벗긴다."""
    cleaned = text.strip()
    # 모델이 가끔 ```json 코드 블록으로 감싸서 보낼 수 있다.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # 첫 줄의 ``` 또는 ```json 을 제거한다.
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # 마지막 줄의 닫는 ``` 도 제거한다.
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


async def complete_meeting_structure(raw_text: str, *, title: str | None = None) -> str:
    """회의록 원문을 OpenRouter에 보내고, assistant content(JSON 문자열)를 반환."""
    api_key = _require_api_key()

    # 사용자 메시지 본문을 만든다. 제목이 있으면 앞에 붙인다.
    user_parts = []
    if title:
        user_parts.append(f"회의 제목: {title}")
    user_parts.append("회의록 원문:")
    user_parts.append(raw_text)
    user_content = "\n".join(user_parts)

    # Chat Completions 요청 본문.
    # temperature를 낮춰 출력이 덜 흔들리게 한다.
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

    # Authorization에 Bearer 키를 넣고, OpenRouter가 권장하는 식별 헤더도 함께 보낸다.
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Meeting Action Tracker",
    }

    try:
        # 비동기 HTTP 클라이언트로 POST.
        # timeout 은 .env 의 OPENROUTER_TIMEOUT_SECONDS (기본 90초).
        # 이 시간을 넘기면 httpx.TimeoutException → 아래 except 에서 OpenRouterError.
        async with httpx.AsyncClient(timeout=OPENROUTER_TIMEOUT_SECONDS) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        # 제한 시간 안에 응답이 없으면 타임아웃 오류로 바꾼다.
        raise OpenRouterError(
            f"OpenRouter request timed out after {OPENROUTER_TIMEOUT_SECONDS}s"
        ) from exc
    except httpx.HTTPError as exc:
        # 그 밖의 HTTP 전송 오류를 OpenRouterError로 통일한다.
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

    # 4xx·5xx 상태면 응답 본문 앞부분과 함께 오류를 낸다.
    if response.status_code >= 400:
        raise OpenRouterError(
            f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        # 응답 본문을 JSON 객체로 파싱한다.
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter returned non-JSON body") from exc

    # 메시지 content를 꺼내고, 코드 블록 감싸기가 있으면 제거한 뒤 반환한다.
    return strip_json_fences(_extract_message_content(payload))
