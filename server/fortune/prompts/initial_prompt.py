INITIAL_FORTUNE_INSTRUCTIONS = """오늘의 최초 운세 안내를 생성하세요.

요구사항:
- 인사말과 오늘의 전체 흐름을 짧고 자연스럽게 작성합니다.
- fortuneScore는 0부터 100 사이의 정수입니다.
- love, wealth, health, career, relationship 다섯 카테고리를 정확히 한 번씩 포함합니다.
- 각 카테고리 score는 1부터 5 사이의 정수입니다.
- 사용자가 이어서 물을 수 있는 추천 질문을 2개에서 4개 제공합니다.
- 운세가 재미와 참고 목적임을 알리는 문구를 포함합니다.

다음 JSON 구조로만 응답하세요:
{
  "greeting": "string",
  "summary": "string",
  "fortuneScore": 0,
  "keywords": ["string"],
  "categorySummaries": [
    {
      "category": "love | wealth | health | career | relationship",
      "label": "string",
      "score": 1,
      "summary": "string"
    }
  ],
  "suggestedQuestions": ["string"],
  "disclaimer": "string"
}"""
