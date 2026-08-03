from clients.llm_client import LLMClientError
from services.jd_service import parse_jd


raw_text = """
招聘 AI 应用开发工程师。

岗位职责：
1. 负责大语言模型相关应用的设计和开发。
2. 参与 RAG 问答系统设计与实现。
3. 使用 FastAPI 开发后端接口。

岗位要求：
1. 熟悉 Python 编程。
2. 有大语言模型应用开发经验。
3. 有 RAG 项目经验者优先。
4. 本科及以上学历。
5. 具备良好的沟通和团队合作能力。
"""


try:
    result = parse_jd(raw_text)

    print("JD解析成功：")
    print(result.model_dump_json(indent=2))

except LLMClientError as exc:
    print(f"JD解析失败：{exc}")

except Exception as exc:
    print(f"发生未处理错误：{exc}")