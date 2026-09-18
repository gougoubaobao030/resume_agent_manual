from typing import TypeVar

from pydantic import BaseModel

from schemas.jd import (
    JDCategory,
    JDRequirement,
    JDSaveRequest,
    JDUpdateRequest,
    LLMJDRequirement,
    LLMJDResult,
)
from api.jd import save_jd_api, update_jd_api
from services import jd_service
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
                    description="必须熟悉 Python 并能够完成后端开发。",
                    category=JDCategory.TECHNICAL,
                    weight=30,
                    must_have=True,
                ),
                LLMJDRequirement(
                    name="FastAPI 开发能力",
                    description="能够使用 FastAPI 开发接口服务。",
                    category=JDCategory.TECHNICAL,
                    weight=20,
                    must_have=False,
                ),
                LLMJDRequirement(
                    name="LLM 应用经验",
                    description="必须具有大语言模型应用开发经验。",
                    category=JDCategory.EXPERIENCE,
                    weight=40,
                    must_have=True,
                ),
            ],
        )

        return response_model.model_validate(
            fake_result.model_dump()
        )


raw_text = """
招聘 AI 应用开发工程师。

必须熟悉 Python 和大语言模型应用开发，了解 FastAPI。
"""


result = parse_jd(
    raw_text=raw_text,
    llm_client=FakeLLMClient(),
)

print(result.model_dump_json(indent=2))


class UnexpectedLLMClient:
    """启用 JD mock 时不应实例化真实模型客户端。"""

    def __init__(self) -> None:
        raise AssertionError("JD mock 模式不应调用真实 LLM")


jd_service.LLMClient = UnexpectedLLMClient

mock_result = jd_service.parse_jd(
    raw_text=raw_text,
)

assert mock_result.job.job_title == "AI应用开发工程师"
mock_requirements = mock_result.job.requirements
assert len(mock_requirements) == 10
assert all(item.weight == 10 for item in mock_requirements)
assert {item.name for item in mock_requirements if item.must_have} == {
    "Python 后端开发",
    "本科及以上学历",
}
assert next(item for item in mock_requirements if item.name == "本科及以上学历").category == JDCategory.EDUCATION
assert all(
    term in " ".join(item.name + item.description for item in mock_requirements)
    for term in (
        "FastAPI", "Flask", "Embedding", "向量数据库", "RAG",
        "LangChain", "LangGraph", "Agent", "企业知识库", "智能问答",
        "简历筛选", "JLPT N1", "需求分析", "学习能力", "问题分析能力",
        "沟通能力", "AI 产品落地", "业务价值",
    )
)

print("JD mock 模式测试通过")


save_response = save_jd_api(
    JDSaveRequest(
        job_title="AI 应用开发工程师",
        raw_text=raw_text,
        requirements=[
            JDRequirement(
                name="Python 开发能力",
                description="必须熟悉 Python。",
                category=JDCategory.TECHNICAL,
                weight=10,
                must_have=True,
            ),
        ],
    )
)

assert save_response.job.requirements[0].must_have is True

updated_job = update_jd_api(
    save_response.job.id,
    JDUpdateRequest(
        job_title=save_response.job.job_title,
        requirements=[
            JDRequirement(
                name="Python 开发能力",
                description="熟悉 Python 者优先。",
                category=JDCategory.TECHNICAL,
                weight=10,
                must_have=False,
            ),
        ],
    ),
)

assert updated_job.requirements[0].must_have is False
assert JDRequirement(
    name="兼容旧请求",
).must_have is False

print("JD 保存和 PUT 修改 must_have 测试通过")
