from schemas.jd import (
    JDCategory,
    LLMJDRequirement,
    LLMJDResult,
)
from services.jd_service import build_jd_info


raw_text = """
招聘 AI 应用开发工程师。

必须熟悉 Python 和大语言模型应用开发，了解 FastAPI。
有 RAG 项目经验者优先。
"""


llm_result = LLMJDResult(
    job_title="AI 应用开发工程师",
    requirements=[
        LLMJDRequirement(
            name="Python 开发能力",
            description="必须熟悉 Python，能够进行后端开发。",
            category=JDCategory.TECHNICAL,
            weight=30,
            must_have=True,
        ),
        LLMJDRequirement(
            name="FastAPI 开发能力",
            description="能够使用 FastAPI 开发后端接口。",
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
        LLMJDRequirement(
            name="RAG 项目经验",
            description="具有 RAG 项目经验者优先。",
            category=JDCategory.EXPERIENCE,
            weight=10,
            must_have=False,
        ),
    ],
)


jd_info = build_jd_info(
    raw_text=raw_text,
    llm_result=llm_result,
)

assert [item.must_have for item in jd_info.requirements] == [
    True,
    False,
    True,
    False,
]


print("模型返回的数据：")
print(llm_result.model_dump_json(indent=2))

print("\n后端补充后的完整 JD：")
print(jd_info.model_dump_json(indent=2))
