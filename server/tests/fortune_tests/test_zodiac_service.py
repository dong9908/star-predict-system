import unittest
from datetime import date

from fortune.services.zodiac_service import calculate_zodiac


class ZodiacServiceTests(unittest.TestCase):
    def test_all_boundaries(self):
        cases = (
            ((1, 19), "capricorn"), ((1, 20), "aquarius"),
            ((2, 18), "aquarius"), ((2, 19), "pisces"),
            ((3, 20), "pisces"), ((3, 21), "aries"),
            ((4, 19), "aries"), ((4, 20), "taurus"),
            ((5, 20), "taurus"), ((5, 21), "gemini"),
            ((6, 21), "gemini"), ((6, 22), "cancer"),
            ((7, 22), "cancer"), ((7, 23), "leo"),
            ((8, 22), "leo"), ((8, 23), "virgo"),
            ((9, 22), "virgo"), ((9, 23), "libra"),
            ((10, 22), "libra"), ((10, 23), "scorpio"),
            ((11, 22), "scorpio"), ((11, 23), "sagittarius"),
            ((12, 21), "sagittarius"), ((12, 22), "capricorn"),
        )

        for (month, day), expected in cases:
            with self.subTest(month=month, day=day):
                self.assertEqual(
                    calculate_zodiac(date(2000, month, day)).code,
                    expected,
                )

    def test_leap_day_is_pisces(self):
        self.assertEqual(calculate_zodiac(date(2000, 2, 29)).code, "pisces")

    def test_zodiac_contains_display_metadata(self):
        zodiac = calculate_zodiac(date(2000, 4, 12))
        self.assertEqual(zodiac.name_ko, "양자리")
        self.assertEqual(zodiac.name_en, "Aries")
        self.assertEqual(zodiac.symbol, "♈")


if __name__ == "__main__":
    unittest.main()
