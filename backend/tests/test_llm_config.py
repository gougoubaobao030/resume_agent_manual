from clients.llm_client import LLMClient


llm_client = LLMClient()

print("模型客户端初始化成功")
print("Base URL:", llm_client.base_url)
print("Model:", llm_client.model)
print("Timeout:", llm_client.timeout)