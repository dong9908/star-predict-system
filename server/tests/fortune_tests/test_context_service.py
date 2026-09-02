import unittest
from datetime import date
from types import SimpleNamespace

from fortune.services.context_service import build_fortune_context


class FortuneContextServiceTests(unittest.TestCase):
    def test_context_uses_user_and_injected_date(self):
        user = SimpleNamespace(user_id=7, birth_date=date(2000, 4, 12))
        context = build_fortune_context(user, current_date=date(2026, 9, 2))

        self.assertEqual(context.user_id, 7)
        self.assertEqual(context.birth_date, date(2000, 4, 12))
        self.assertEqual(context.today, date(2026, 9, 2))
        self.assertEqual(context.zodiac.code, "aries")

    def test_serialized_context_uses_api_aliases(self):
        user = SimpleNamespace(user_id=7, birth_date=date(2000, 4, 12))
        payload = build_fortune_context(
            user,
            current_date=date(2026, 9, 2),
        ).model_dump(mode="json", by_alias=True)

        self.assertEqual(payload["userId"], 7)
        self.assertEqual(payload["birthDate"], "2000-04-12")
        self.assertEqual(payload["zodiac"]["nameKo"], "양자리")
        self.assertNotIn("email", payload)
        self.assertNotIn("phone", payload)
        self.assertNotIn("password_hash", payload)

    def test_missing_birth_date_is_rejected(self):
        user = SimpleNamespace(user_id=7, birth_date=None)

        with self.assertRaisesRegex(ValueError, "생년월일"):
            build_fortune_context(user, current_date=date(2026, 9, 2))


if __name__ == "__main__":
    unittest.main()
