import json
import unittest

from prompts.jd_prompt import (
    build_jd_parse_user_prompt,
    get_jd_parse_response_schema,
)
from prompts.resume_prompt import (
    build_resume_user_prompt,
    get_resume_response_schema,
)
from schemas.jd import LLMJDResult
from schemas.resume import ResumeLLMResult


class PromptSchemaInjectionTest(unittest.TestCase):
    def test_resume_prompt_injects_response_model_schema(self) -> None:
        schema_text = get_resume_response_schema()
        prompt = build_resume_user_prompt("测试简历原文")

        self.assertEqual(
            json.loads(schema_text),
            ResumeLLMResult.model_json_schema(),
        )
        self.assertIn("测试简历原文", prompt)
        self.assertIn(schema_text, prompt)
        self.assertIn("【必须严格遵守的JSON Schema】", prompt)

    def test_jd_prompt_injects_response_model_schema(self) -> None:
        schema_text = get_jd_parse_response_schema()
        prompt = build_jd_parse_user_prompt("测试岗位说明")

        self.assertEqual(
            json.loads(schema_text),
            LLMJDResult.model_json_schema(),
        )
        self.assertIn("测试岗位说明", prompt)
        self.assertIn(schema_text, prompt)
        self.assertIn("【必须严格遵守的JSON Schema】", prompt)

if __name__ == "__main__":
    unittest.main()
