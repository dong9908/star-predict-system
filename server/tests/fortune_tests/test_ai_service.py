import json
import unittest
from datetime import date

from fortune.exceptions import (
    FortuneAIAuthenticationError,
    FortuneAIResponseError,
)
from fortune.schemas import (
    FortuneChatInput,
    FortuneContextResponse,
    ZodiacInfo,
)
from fortune.services.ai_service import (
    generate_chat_response,
    generate_initial_fortune,
)


def _context() -> FortuneContextResponse:
    return FortuneContextResponse(
        user_id=7,
        birth_date=date(2000, 4, 12),
        today=date(2026, 9, 2),
        zodiac=ZodiacInfo(
            code="aries",
            name_ko="양자리",
            name_en="Aries",
            symbol="♈",
        ),
    )


def _initial_payload() -> dict:
    categories = (
        ("love", "사랑운"),
        ("wealth", "재물운"),
        ("health", "건강운"),
        ("career", "직업운"),
        ("relationship", "인간관계운"),
    )
    return {
        "greeting": "안녕하세요. 오늘의 양자리 운세입니다.",
        "summary": "차분한 소통이 도움이 될 수 있는 날입니다.",
        "fortuneScore": 82,
        "keywords": ["소통", "집중"],
        "categorySummaries": [
            {
                "category": category,
                "label": label,
                "score": 4,
                "summary": f"오늘의 {label} 흐름입니다.",
            }
            for category, label in categories
        ],
        "suggestedQuestions": [
            "오늘 직업운을 자세히 알려줘.",
            "오늘 조심할 점은 무엇이야?",
        ],
        "disclaimer": "운세는 재미와 참고 목적으로 활용해 주세요.",
    }


class FakeProvider:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def generate(self, prompt, response_model):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


class FortuneAIServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_fortune_is_validated(self):
        provider = FakeProvider([json.dumps(_initial_payload(), ensure_ascii=False)])

        result = await generate_initial_fortune(
            _context(),
            provider=provider,
            max_retries=0,
        )

        self.assertEqual(result.fortune_score, 82)
        self.assertEqual(len(result.category_summaries), 5)
        self.assertEqual(provider.calls, 1)

    async def test_chat_response_is_validated(self):
        payload = {
            "answer": "발표 전에 핵심 내용을 다시 확인해 보세요.",
            "category": "career",
            "suggestedQuestions": ["발표 전에 무엇을 점검할까?"],
            "disclaimer": "운세는 참고용으로 활용해 주세요.",
        }
        provider = FakeProvider([json.dumps(payload, ensure_ascii=False)])

        result = await generate_chat_response(
            _context(),
            FortuneChatInput(message="오늘 발표 운은 어때?", category="career"),
            provider=provider,
            max_retries=0,
        )

        self.assertEqual(result.category.value, "career")
        self.assertIn("발표", result.answer)

    async def test_invalid_json_is_retried_once(self):
        provider = FakeProvider([
            "not-json",
            json.dumps(_initial_payload(), ensure_ascii=False),
        ])

        result = await generate_initial_fortune(
            _context(),
            provider=provider,
            max_retries=1,
        )

        self.assertEqual(result.fortune_score, 82)
        self.assertEqual(provider.calls, 2)

    async def test_duplicate_categories_are_rejected(self):
        payload = _initial_payload()
        payload["categorySummaries"][4]["category"] = "love"
        provider = FakeProvider([json.dumps(payload, ensure_ascii=False)])

        with self.assertRaises(FortuneAIResponseError):
            await generate_initial_fortune(
                _context(),
                provider=provider,
                max_retries=0,
            )

    async def test_authentication_failure_is_not_retried(self):
        provider = FakeProvider([FortuneAIAuthenticationError("invalid key")])

        with self.assertRaises(FortuneAIAuthenticationError):
            await generate_initial_fortune(
                _context(),
                provider=provider,
                max_retries=2,
            )

        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
