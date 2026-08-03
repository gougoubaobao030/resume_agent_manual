from prompts.jd_prompt import (
    JD_PARSE_SYSTEM_PROMPT,
    build_jd_parse_user_prompt,
)


raw_text = """
招聘 AI 应用开发工程师。

岗位职责：
1. 负责大语言模型相关应用开发。
2. 参与 RAG 问答系统设计与实现。
3. 使用 FastAPI 开发后端接口。

岗位要求：
1. 熟悉 Python。
2. 有大语言模型应用开发经验。
3. 有 RAG 项目经验者优先。
4. 本科及以上学历。
5. 具备良好的沟通和团队合作能力。
"""


print("系统提示词：")
print(JD_PARSE_SYSTEM_PROMPT)

print("\n用户提示词：")
print(build_jd_parse_user_prompt(raw_text))