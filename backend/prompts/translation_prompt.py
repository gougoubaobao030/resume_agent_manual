import json

from schemas.language import AnalysisLanguage, get_analysis_language_name
from schemas.translation import LLMBatchTranslationResult, TranslationItemRequest


TRANSLATION_SYSTEM_PROMPT = """
你是招聘分析系统中的忠实翻译助手。

你的任务仅是翻译输入文本，不进行评分、人才发现、事实补充或内容改写。

规则：
1. 每个 item_id 必须原样返回，不能修改、翻译或重新生成。
2. 不得遗漏、重复或增加 item。
3. analysis 类型应自然、准确地翻译，保留原始含义和不确定程度。
4. evidence 类型是候选人原文的参考译文，必须尽量逐句忠实，不得概括、润色、弱化或补充事实。
5. 技术名称、公司名、产品名、证书名、数字、日期和 ID 应保持准确。
6. 输入可能是中文、日文、英文或混合语言；已经是目标语言的内容保持原意，不要无意义改写。
7. 只输出符合指定 JSON Schema 的 JSON。
"""


def build_translation_user_prompt(
    *,
    target_language: AnalysisLanguage,
    items: list[TranslationItemRequest],
) -> str:
    response_schema = json.dumps(
        LLMBatchTranslationResult.model_json_schema(),
        ensure_ascii=False,
        indent=2,
    )
    item_data = [item.model_dump(mode="json") for item in items]
    return f"""
请将下面所有 item 翻译为 {get_analysis_language_name(target_language)}（{target_language.value}）。

【待翻译 items】
{json.dumps(item_data, ensure_ascii=False, indent=2)}

【必须严格遵守的 JSON Schema】
{response_schema}

只返回 JSON。item_id 必须与输入完全一致。
""".strip()
