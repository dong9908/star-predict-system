from datetime import date
import unittest

from services.title_service import UserDiscoveryStats, get_qualified_title_ids


_BIRTH_DATE = date(2000, 4, 12)


def _stats(**overrides) -> UserDiscoveryStats:
    values = {
        "user_id": 1,
        "total_constellations": 89,
        "discovered_count": 0,
        "discovered_ids": frozenset(),
        "discovered_names": frozenset(),
        "discovered_abbreviations": frozenset(),
        "total_by_difficulty": {"1": 15, "2": 11, "3": 24, "4": 23},
        "discovered_by_difficulty": {},
        "mythology_count": 0,
        "discoveries_by_date": {},
        "longest_consecutive_days": 0,
    }
    values.update(overrides)
    return UserDiscoveryStats(**values)


_BOUNDARY_CASES = [
        (1, {"discovered_count": 9}, {"discovered_count": 10}),
        (2, {"discovered_count": 24}, {"discovered_count": 25}),
        (3, {"discovered_count": 49}, {"discovered_count": 50}),
        (4, {"discovered_count": 74}, {"discovered_count": 75}),
        (5, {"discovered_count": 88}, {"discovered_count": 89}),
        (6, {"discovered_abbreviations": frozenset({"SerH"})}, {"discovered_abbreviations": frozenset({"SerH", "SerT"})}),
        (7, {"discovered_abbreviations": frozenset()}, {"discovered_abbreviations": frozenset({"Oph"})}),
        (8, {"discovered_names": frozenset()}, {"discovered_names": frozenset({"양자리"})}),
        (9, {"discovered_by_difficulty": {"1": 14}}, {"discovered_by_difficulty": {"1": 15}}),
        (10, {"discovered_by_difficulty": {"2": 10}}, {"discovered_by_difficulty": {"2": 11}}),
        (11, {"discovered_by_difficulty": {"3": 23}}, {"discovered_by_difficulty": {"3": 24}}),
        (12, {"discovered_by_difficulty": {"4": 9}}, {"discovered_by_difficulty": {"4": 10}}),
        (13, {"discovered_by_difficulty": {"4": 22}}, {"discovered_by_difficulty": {"4": 23}}),
        (14, {"discovered_by_difficulty": {"1": 1, "2": 1, "3": 1}}, {"discovered_by_difficulty": {"1": 1, "2": 1, "3": 1, "4": 1}}),
        (15, {"mythology_count": 19}, {"mythology_count": 20}),
        (16, {"longest_consecutive_days": 6}, {"longest_consecutive_days": 7}),
        (17, {"discoveries_by_date": {date(2026, 9, 1): 2}}, {"discoveries_by_date": {date(2026, 9, 1): 3}}),
]


class TitleConditionBoundaryTest(unittest.TestCase):
    def test_each_title_condition_boundary(self):
        for title_id, before, at_boundary in _BOUNDARY_CASES:
            with self.subTest(title_id=title_id):
                self.assertNotIn(
                    title_id,
                    get_qualified_title_ids(_stats(**before), _BIRTH_DATE),
                )
                self.assertIn(
                    title_id,
                    get_qualified_title_ids(_stats(**at_boundary), _BIRTH_DATE),
                )


if __name__ == "__main__":
    unittest.main()
