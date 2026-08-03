from clients.llm_client import LLMClient
from prompts.jd_prompt import (
    JD_PARSE_SYSTEM_PROMPT,
    build_jd_parse_user_prompt,
)

from schemas.jd import (
    JDInfo,
    JDRequirement,
    LLMJDResult,
    JDParseResponse,
)

#把模型结果转为系统正式用的数据结构
#转这个过程不是由大模型实现而是由后端实现
def build_jd_info(
    raw_text: str,
    llm_result: LLMJDResult,
) -> JDInfo:
    """
    将模型解析结果转换为系统正式使用的 JDInfo。

    模型只负责提供岗位名称和要求内容；
    岗位 ID、条目 ID 和原始文本由后端补充。
    """

    requirements = [
        JDRequirement(
            name=item.name,
            description=item.description,
            category=item.category,
            weight=item.weight,
        )
        #这里是把每个岗位里的n个岗位要求逐一给弄出来，是个省略写法
        for item in llm_result.requirements
    ]

    return JDInfo(
        job_title=llm_result.job_title,
        raw_text=raw_text,
        requirements=requirements,
    )

#调用大语言模型，生成回应，并解析成JDInfo加上warnning
#成为响应前端需要的JDParseResponse
def parse_jd(
    raw_text: str,
    llm_client: LLMClient | None = None,
) -> JDParseResponse:
    """
    调用大模型解析原始 JD，并返回系统正式使用的数据。

    参数：
    - raw_text：HR 输入的原始 JD
    - llm_client：可选模型客户端，方便测试时替换

    返回：
    - JDParseResponse
    """

    cleaned_raw_text = raw_text.strip()

    if not cleaned_raw_text:
        raise ValueError("JD 文本不能为空。")

    client = llm_client or LLMClient()

    llm_result = client.generate_structured(
        system_prompt=JD_PARSE_SYSTEM_PROMPT,
        user_prompt=build_jd_parse_user_prompt(cleaned_raw_text),
        response_model=LLMJDResult,
        temperature=0.1,
    )

    job = build_jd_info(
        raw_text=cleaned_raw_text,
        llm_result=llm_result,
    )

    #注意这里的warning是解析JDInfo格式自生带来的warning
    #不是大语言模型生成时带来的warning
    warnings = build_parse_warnings(job)

    return JDParseResponse(
        job=job,
        warnings=warnings,
    )


def build_parse_warnings(job: JDInfo) -> list[str]:
    """根据解析结果生成需要 HR 注意的非致命提示。"""

    warnings: list[str] = []

    if not job.requirements:
        warnings.append(
            "未解析出明确的岗位要求，请HR检查原文并手动补充。"
        )

    if not any(
        item.category.value == "education"
        for item in job.requirements
    ):
        warnings.append(
            "JD中未解析出明确的学历要求，如有需要请HR手动补充。"
        )

    if job.requirements and all(
        item.weight == 0
        for item in job.requirements
    ):
        warnings.append(
            "所有要求的建议权重均为0，后续评分时将按等权处理。"
        )

    return warnings