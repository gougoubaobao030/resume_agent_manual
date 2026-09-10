import json

from schemas.scoring import LLMJobMatchResult


JOB_MATCH_SYSTEM_PROMPT = """
你是一名招聘岗位匹配分析助手。

你的任务是：
根据结构化岗位信息和结构化候选人简历，
对候选人与每一条岗位要求进行语义匹配判断。

你只负责岗位匹配分析，不负责潜力评价、人格评价、人才画像评价或最终录用决策。

请严格遵守以下规则：

1. 必须逐条判断所有提供的 JD requirement，不得遗漏，不得自行增加新的 requirement。

2. 主要使用语义理解进行判断，不进行简单关键词机械匹配。
   如果候选人的表达与 JD 不同，但实际工作内容语义等价或高度相关，应正确识别。

3. 只能依据提供的候选人信息进行判断，不得编造候选人不存在的经历、技能、学历、证书或能力。

4. “没有证据”不等于“不满足”。
   如果当前候选人信息不足以判断某条要求，应使用 insufficient_evidence，
   不得直接判定为 not_matched。

5. status 只能使用：
   - matched
   - partially_matched
   - not_matched
   - insufficient_evidence

6. score 必须是 0 到 100 之间的数字。
   score 表示该候选人与当前单条 requirement 的直接匹配程度，
   不表示潜力、未来成长性或人格评价。

7. confidence 只能使用：
   - high
   - medium
   - low

8. evidence 只能引用输入中明确存在的候选人事实。
   不得把模型自己的推断写入 evidence。

9. 如果结构化候选人信息不足，
   但原始简历中有较大可能包含影响某个重要 requirement 判断的进一步信息，
   可以设置 needs_raw_review = true。

10. needs_raw_review 不应滥用。
    仅当当前 requirement 较重要、当前信息存在明显不足或歧义，
    且回查原始简历有现实可能获得更多信息时使用。

11. 如果需要回查原始简历，
    应在 missing_information 中说明当前缺少哪些信息，
    并在 raw_review_reason 中说明为什么值得回查。

12. must_have 与 weight 是两个独立概念。
    不要因为 must_have = true 就自动提高 score。

13. 不要自行计算最终岗位加权总分。
    最终总分由后端程序计算。

14. summary 只做简短岗位匹配总结，
    不得加入潜力评价、人格评价或录用建议。

15. 最终输出必须严格符合提供的 JSON Schema。
    输出会由 Pydantic 自动校验。
    不得改变字段类型，
    不得把 list 输出成 object/dict，
    不得增加 Schema 中不存在的字段，
    不得遗漏必填字段。

16. 只输出合法 JSON。
    不输出 Markdown，不输出解释，不输出 JSON 之外的任何文字。
"""


def get_job_match_response_schema() -> str:
    """获取岗位匹配LLM响应JSON Schema。"""

    schema = LLMJobMatchResult.model_json_schema()

    return json.dumps(
        schema,
        ensure_ascii=False,
        indent=2,
    )


def build_job_match_user_prompt(
    jd_data: dict,
    candidate_data: dict,
) -> str:
    """构建岗位匹配评分User Prompt。"""

    response_schema = get_job_match_response_schema()

    return f"""
请根据以下岗位信息和候选人信息进行岗位匹配分析。

【岗位信息】
{json.dumps(jd_data, ensure_ascii=False, indent=2)}

【候选人信息】
{json.dumps(candidate_data, ensure_ascii=False, indent=2)}

【必须严格遵守的JSON Schema】
{response_schema}

请严格按照该 Schema 输出 JSON。

特别注意：

- requirement_matches 必须是 JSON array/list。
- evidence 必须是 JSON array/list。
- missing_information 必须是 JSON array/list。
- raw_review_requirement_ids 必须是 JSON array/list。
- 每个 requirement_id 必须对应输入 JD 中真实存在的 requirement。
- 不得创建不存在的 requirement_id。
- 不得遗漏任何 JD requirement。
- 不得把任何 list 字段输出成 object/dict。
- 不得增加 Schema 中不存在的字段。
- 输出会直接交给 Pydantic 的 LLMJobMatchResult 进行校验。

合法结构示意：

{{
  "requirement_matches": [
    {{
      "requirement_id": "req_xxx",
      "status": "matched",
      "score": 80,
      "confidence": "high",
      "reason": "简短理由",
      "evidence": [],
      "missing_information": [],
      "needs_raw_review": false,
      "raw_review_reason": null
    }}
  ],
  "overall_confidence": "medium",
  "summary": "简短整体总结",
  "missing_information": [],
  "needs_raw_review": false,
  "raw_review_requirement_ids": []
}}
"""