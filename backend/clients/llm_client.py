import json
import os
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from pydantic import BaseModel, ValidationError


# 找到项目根目录：
# 当前文件位于 backend/clients/llm_client.py
# parents[0] = clients
# parents[1] = backend
# parents[2] = 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 明确读取项目根目录下的 .env
load_dotenv(PROJECT_ROOT / ".env")


# T 表示传入什么 Pydantic 模型，最终就返回什么模型
T = TypeVar("T", bound=BaseModel)


class LLMClientError(Exception):
    """模型调用过程中发生的统一业务异常。"""


class LLMConfigError(LLMClientError):
    """模型配置缺失或错误。"""


class LLMRequestError(LLMClientError):
    """请求模型接口失败。"""


class LLMResponseError(LLMClientError):
    """模型返回内容无法正常解析。"""


class LLMClient:
    """统一封装 OpenAI 兼容模型调用。"""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv(
            "OPENAI_BASE_URL",
            "https://api.openai.com/v1",
        ).strip()
        self.model = os.getenv("OPENAI_MODEL", "").strip()

        timeout_text = os.getenv("LLM_TIMEOUT", "60").strip()

        try:
            self.timeout = float(timeout_text)
        except ValueError as exc:
            raise LLMConfigError(
                "LLM_TIMEOUT 必须是有效数字。"
            ) from exc

        self._validate_config()

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _validate_config(self) -> None:
        """检查模型调用所需配置。"""

        if not self.api_key:
            raise LLMConfigError(
                "未配置 OPENAI_API_KEY，请检查项目根目录下的 .env 文件。"
            )

        if not self.base_url:
            raise LLMConfigError(
                "未配置 OPENAI_BASE_URL。"
            )

        if not self.model:
            raise LLMConfigError(
                "未配置 OPENAI_MODEL，请检查项目根目录下的 .env 文件。"
            )

        if self.timeout <= 0:
            raise LLMConfigError(
                "LLM_TIMEOUT 必须大于 0。"
            )

    #关键函数，大预言模型根据某个提供接口生成字符串，本地完成要求的格式校验
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.1,
    ) -> T:
        """
        调用模型并将返回结果解析为指定的 Pydantic 模型。

        参数：
        - system_prompt：系统提示词
        - user_prompt：当前任务提示词
        - response_model：期望得到的 Pydantic 数据类型
        - temperature：生成随机程度

        返回：
        - response_model 对应的 Pydantic 对象
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=temperature,
                response_format={
                    "type": "json_object",
                },
            )

        except APITimeoutError as exc:
            raise LLMRequestError(
                "模型请求超时，请稍后重试。"
            ) from exc

        except APIConnectionError as exc:
            raise LLMRequestError(
                "无法连接模型服务，请检查网络和 OPENAI_BASE_URL。"
            ) from exc

        except APIStatusError as exc:
            raise LLMRequestError(
                f"模型服务返回错误，状态码：{exc.status_code}。"
            ) from exc

        except Exception as exc:
            raise LLMRequestError(
                f"调用模型时发生未知错误：{exc}"
            ) from exc

        if not completion.choices:
            raise LLMResponseError(
                "模型没有返回任何候选结果。"
            )

        content = completion.choices[0].message.content

        if not content:
            raise LLMResponseError(
                "模型返回内容为空。"
            )

        cleaned_content = self._clean_json_content(content)

        try:
            json_data = json.loads(cleaned_content)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                "模型返回的内容不是有效 JSON。"
            ) from exc

        try:
            return response_model.model_validate(json_data)
        except ValidationError as exc:
            raise LLMResponseError(
                "模型返回的 JSON 不符合规定的数据结构。"
            ) from exc


    #一个清理json的静态方法，当然别的模块也能用
    @staticmethod
    def _clean_json_content(content: str) -> str:
        """
        清理模型偶尔附加的 Markdown JSON 代码块。

        例如将：

        ```json
        {"job_title": "..."}
        ```

        清理为纯 JSON 字符串。
        """

        cleaned = content.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```"):].strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-len("```")].strip()

        return cleaned