from typing import TypeVar

from pydantic import BaseModel

from schemas.jd import (
    JDCategory,
    LLMJDRequirement,
    LLMJDResult,
)
from services.jd_service import parse_jd


T = TypeVar("T", bound=BaseModel)


class FakeLLMClient:
    """测试用假模型客户端，不会发起网络请求。"""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.1,
    ) -> T:
        fake_result = LLMJDResult(
            job_title="AI 应用开发工程师",
            requirements=[
                LLMJDRequirement(
                    name="Python 开发能力",
                    description="熟悉 Python 并能够完成后端开发。",
                    category=JDCategory.TECHNICAL,
                    weight=30,
                ),
                LLMJDRequirement(
                    name="FastAPI 开发能力",
                    description="能够使用 FastAPI 开发接口服务。",
                    category=JDCategory.TECHNICAL,
                    weight=20,
                ),
                LLMJDRequirement(
                    name="LLM 应用经验",
                    description="具有大语言模型应用开发经验。",
                    category=JDCategory.EXPERIENCE,
                    weight=40,
                ),
            ],
        )

        return response_model.model_validate(
            fake_result.model_dump()
        )


raw_text = """
招聘 AI 应用开发工程师。

要求熟悉 Python、FastAPI 和大语言模型应用开发。
"""


result = parse_jd(
    raw_text=raw_text,
    llm_client=FakeLLMClient(),
)

print(result.model_dump_json(indent=2))