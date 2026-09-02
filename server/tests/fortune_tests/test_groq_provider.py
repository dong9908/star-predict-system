import unittest

from fortune.schemas import InitialFortuneResponse


class GroqSchemaTests(unittest.TestCase):
    def test_strict_output_schema_forbids_extra_properties(self):
        schema = InitialFortuneResponse.model_json_schema(by_alias=True)

        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(
            schema["$defs"]["FortuneCategorySummary"]["additionalProperties"]
        )
        self.assertIn("fortuneScore", schema["required"])
        self.assertIn("categorySummaries", schema["required"])


if __name__ == "__main__":
    unittest.main()
