from clients.llm_client import LLMClient


import asyncio
import os
import pytest


if os.getenv("RUN_LLM_INTEGRATION", "false").lower() != "true":
    pytest.skip("设置 RUN_LLM_INTEGRATION=true 才检查真实 LLM 配置", allow_module_level=True)


llm_client = LLMClient()

print("模型客户端初始化成功")
print("Base URL:", llm_client.base_url)
print("Model:", llm_client.model)
print("Timeout:", llm_client.timeout)
print("Max concurrency:", llm_client.max_concurrency)
asyncio.run(llm_client.close())
