"""
hallucination.py — AI가 "원문에 없는 담당자/기한"을 지어냈는지 걸러 내는 파일

왜 필요한가?
  프롬프트에 "지어내지 마세요"라고 써도, 무료 모델은 가끔 없는 이름을 넣는다.
  그래서 DB에 넣기 직전에 우리 코드가 한 번 더 검사한다.

언제 호출되나?
  structure.py 에서 JSON 스키마 검증이 끝난 직후,
  sanitize_structure_result(회의원문, AI결과) 를 부른다.

이 파일이 하는 일 (짧게):
  1. 담당자 글자가 원문에 있나? 없으면 null
  2. 기한 날짜가 원문에 근거가 있나? 없으면 null
  3. 할 일 문구 / 결정 / 논의 문장은 여기서 지우지 않음
"""

from __future__ import annotations

from datetime import date

from app.schemas.ai import AiActionItem, AiStructureResult


def _normalize(text: str) -> str:
    """
    비교하기 쉽게 글자를 정리한다.

    하는 일:
    - casefold() : 대소문자 차이를 없앰 (영문 이름 대비)
    - split() + join : 공백이 여러 칸이어도 한 칸으로 맞춤

    예:
      "  Kim  Min  " → "kim min"
    """
    return " ".join(text.casefold().split())


def assignee_in_raw_text(assignee: str | None, raw_text: str) -> bool:
    """
    담당자 이름이 회의록 원문에 "들어 있는지" 확인한다.

    True  = 원문에 그 이름이 보인다 → 믿어도 됨
    False = 원문에 없다 → AI가 지어낸 가능성이 큼

    검사 방식 = 부분 문자열 포함 여부
      assignee = "민수"
      raw_text 에 "김민수는 ..." 가 있으면 → True
        ( "민수" 가 "김민수" 안에 들어 있으니까 )

      assignee = "홍길동"
      raw_text 어디에도 없으면 → False
    """
    # None 이거나 빈 글자면 "원문에 있다"고 볼 수 없음
    if assignee is None:
        return False
    name = assignee.strip()
    if not name:
        return False

    # 정리한 이름이 정리한 원문 안에 있는지
    return _normalize(name) in _normalize(raw_text)


def due_date_in_raw_text(due: date | None, raw_text: str) -> bool:
    """
    기한(date)이 원문에 근거가 있는지 확인한다.

    어려운 점:
      AI는 보통 due_date 를 "2026-07-15" 처럼 ISO 형식으로 준다.
      그런데 사람이 쓴 원문에는 "7월 15일" 처럼 다르게 적혀 있을 수 있다.
      그래서 ISO 하나만 찾지 않고, 같은 날을 가리킬 수 있는 여러 표기를 만든다.

    candidates 예 (due = 2026-07-15 일 때):
      "2026-07-15", "2026.07.15", "7월 15일", "7/15" ...

    이 표기 중 하나라도 원문에 있으면 True.
    하나도 없으면 False → 나중에 null 로 바꾼다.
    """
    if due is None:
        return False

    # 같은 날짜를 원문에서 찾을 때 쓸 후보 문자열들
    candidates = [
        due.isoformat(),  # 2026-07-15
        f"{due.year}.{due.month:02d}.{due.day:02d}",
        f"{due.year}.{due.month}.{due.day}",
        f"{due.year}/{due.month:02d}/{due.day:02d}",
        f"{due.year}/{due.month}/{due.day}",
        f"{due.month}월 {due.day}일",  # 7월 15일
        f"{due.month}월{due.day}일",  # 7월15일
        f"{due.month:02d}월 {due.day:02d}일",
        f"{due.month}/{due.day}",
        f"{due.month}/{due.day:02d}",
    ]

    # 원문도 같은 방식으로 정리해 두고, 후보를 하나씩 찾아 본다
    normalized_raw = _normalize(raw_text)
    for token in candidates:
        if _normalize(token) in normalized_raw:
            return True  # 근거 발견 → 이 기한은 통과

    # 후보가 전부 원문에 없음 → 근거 없음
    return False


def sanitize_structure_result(
    raw_text: str,
    result: AiStructureResult,
) -> AiStructureResult:
    """
    AI 구조화 결과 전체를 "원문 근거" 기준으로 한 번 청소한다.

    입력:
      raw_text = 사용자가 붙여넣은 회의록
      result   = 이미 Pydantic 형식 검사를 통과한 AI 결과

    출력:
      담당자/기한이 수상하면 null 로 바꾼 새 AiStructureResult
      (원본 result 를 직접 수정하지 않고 새로 만들어 반환)

    액션아이템 하나씩 보면서:
      - assignee 가 원문에 없으면 → None
      - due_date 가 원문에 근거 없으면 → None
      - task(할 일 문구)는 그대로 둠

    왜 결정/논의 문장은 안 지우나?
      문장 전체를 자동 삭제하면, 맞는 내용까지 날아갈 위험이 크다.
      그 부분은 상세 화면에서 사람이 고치게 둔다.
    """
    cleaned_items: list[AiActionItem] = []

    # AI가 준 액션을 하나씩 검사
    for item in result.action_items:
        assignee = item.assignee
        due = item.due_date

        # 담당자가 있는데, 원문에 없으면 지움(null)
        if assignee is not None and not assignee_in_raw_text(assignee, raw_text):
            assignee = None

        # 기한이 있는데, 원문에 근거가 없으면 지움(null)
        if due is not None and not due_date_in_raw_text(due, raw_text):
            due = None

        # 검사 통과한 값으로 새 액션 객체 만들기
        cleaned_items.append(
            AiActionItem(
                task=item.task,
                assignee=assignee,
                due_date=due,
            )
        )

    # 결정/논의는 그대로 두고, 액션만 청소한 결과를 반환
    return AiStructureResult(
        decisions=result.decisions,
        discussions=result.discussions,
        action_items=cleaned_items,
    )
