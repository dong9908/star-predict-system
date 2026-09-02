from datetime import date

from fortune.schemas import ZodiacInfo


_ZODIAC_RANGES = (
    ((1, 20), (2, 18), ZodiacInfo(code="aquarius", name_ko="물병자리", name_en="Aquarius", symbol="♒")),
    ((2, 19), (3, 20), ZodiacInfo(code="pisces", name_ko="물고기자리", name_en="Pisces", symbol="♓")),
    ((3, 21), (4, 19), ZodiacInfo(code="aries", name_ko="양자리", name_en="Aries", symbol="♈")),
    ((4, 20), (5, 20), ZodiacInfo(code="taurus", name_ko="황소자리", name_en="Taurus", symbol="♉")),
    ((5, 21), (6, 21), ZodiacInfo(code="gemini", name_ko="쌍둥이자리", name_en="Gemini", symbol="♊")),
    ((6, 22), (7, 22), ZodiacInfo(code="cancer", name_ko="게자리", name_en="Cancer", symbol="♋")),
    ((7, 23), (8, 22), ZodiacInfo(code="leo", name_ko="사자자리", name_en="Leo", symbol="♌")),
    ((8, 23), (9, 22), ZodiacInfo(code="virgo", name_ko="처녀자리", name_en="Virgo", symbol="♍")),
    ((9, 23), (10, 22), ZodiacInfo(code="libra", name_ko="천칭자리", name_en="Libra", symbol="♎")),
    ((10, 23), (11, 22), ZodiacInfo(code="scorpio", name_ko="전갈자리", name_en="Scorpio", symbol="♏")),
    ((11, 23), (12, 21), ZodiacInfo(code="sagittarius", name_ko="사수자리", name_en="Sagittarius", symbol="♐")),
)

_CAPRICORN = ZodiacInfo(
    code="capricorn",
    name_ko="염소자리",
    name_en="Capricorn",
    symbol="♑",
)


def calculate_zodiac(birth_date: date) -> ZodiacInfo:
    """Calculate the western zodiac from the month and day of a birth date."""
    month_day = (birth_date.month, birth_date.day)

    for start, end, zodiac in _ZODIAC_RANGES:
        if start <= month_day <= end:
            return zodiac.model_copy()

    # Capricorn spans the end and beginning of a calendar year.
    return _CAPRICORN.model_copy()
