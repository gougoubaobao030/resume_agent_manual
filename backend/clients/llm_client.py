import json
import asyncio
import logging
import os
import re
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)
from pydantic import BaseModel, ValidationError


logger = logging.getLogger("uvicorn.error")


# 找到项目根目录：
# 当前文件位于 backend/clients/llm_client.py
# parents[0] = clients
# parents[1] = backend
# parents[2] = 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 明确读取项目根目录下的 .env
load_dotenv(
    PROJECT_ROOT / ".env",
    override=True,
)


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
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.base_url = os.getenv(
            "LLM_BASE_URL",
            "https://api.openai.com/v1",
        ).strip()
        self.model = os.getenv("LLM_MODEL", "").strip()

        timeout_text = os.getenv("LLM_TIMEOUT", "60").strip()
        max_concurrency_text = os.getenv("LLM_MAX_CONCURRENCY", "5").strip()

        try:
            self.timeout = float(timeout_text)
        except ValueError as exc:
            raise LLMConfigError(
                "LLM_TIMEOUT 必须是有效数字。"
            ) from exc

        try:
            self.max_concurrency = int(max_concurrency_text)
        except ValueError as exc:
            raise LLMConfigError(
                "LLM_MAX_CONCURRENCY 必须是有效整数。"
            ) from exc

        self._validate_config()

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        self._provider_semaphore = _get_provider_semaphore(self.max_concurrency)

    def _validate_config(self) -> None:
        """检查模型调用所需配置。"""

        if not self.api_key:
            raise LLMConfigError(
                "未配置 LLM_API_KEY，请检查项目根目录下的 .env 文件。"
            )

        if not self.base_url:
            raise LLMConfigError(
                "未配置 LLM_BASE_URL。"
            )

        if not self.model:
            raise LLMConfigError(
                "未配置 LLM_MODEL，请检查项目根目录下的 .env 文件。"
            )

        if self.timeout <= 0:
            raise LLMConfigError(
                "LLM_TIMEOUT 必须大于 0。"
            )

        if self.max_concurrency <= 0:
            raise LLMConfigError(
                "LLM_MAX_CONCURRENCY 必须大于 0。"
            )

    #关键函数，大预言模型根据某个提供接口生成字符串，本地完成要求的格式校验
    async def generate_structured(
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
            async with self._provider_semaphore:
                completion = await self.client.chat.completions.create(
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

        except asyncio.CancelledError:
            raise

        except APITimeoutError as exc:
            raise LLMRequestError(
                "模型请求超时，请稍后重试。"
            ) from exc

        except APIConnectionError as exc:
            raise LLMRequestError(
                "无法连接模型服务，请检查网络和 LLM_BASE_URL。"
            ) from exc

        #似乎key的原因，遇到了这个问题得到来自deepseek的401错误
        except APIStatusError as exc:
            request_id = getattr(exc, "request_id", None)
            error_message = " ".join(str(exc).split())[:500]
            logger.error(
                "[LLM Request Error] status_code=%s error_type=%s "
                "request_id=%s message=%s",
                exc.status_code,
                type(exc).__name__,
                request_id,
                error_message,
            )
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

        choice = completion.choices[0]
        content = choice.message.content
        usage = completion.usage

        logger.info(
            "[LLM Response] finish_reason=%s completion_tokens=%s "
            "prompt_tokens=%s total_tokens=%s content_chars=%s",
            choice.finish_reason,
            getattr(usage, "completion_tokens", None),
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "total_tokens", None),
            len(content or ""),
        )

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

    async def close(self) -> None:
        """关闭底层异步 HTTP Client 及其连接池。"""

        await self.client.close()

    @staticmethod
    def _get_schema_name(response_model: type[BaseModel]) -> str:
        """生成符合 Structured Outputs 命名限制的稳定 schema 名称。"""

        schema_name = re.sub(r"[^a-zA-Z0-9_-]", "_", response_model.__name__)
        return schema_name[:64] or "structured_response"

    @classmethod
    def _build_strict_json_schema(
        cls,
        response_model: type[BaseModel],
    ) -> dict:
        """从 Pydantic 模型生成 Chat Completions strict JSON Schema。"""

        schema = response_model.model_json_schema()
        cls._normalize_strict_json_schema(schema)
        return schema

    @classmethod
    def _normalize_strict_json_schema(cls, node: object) -> None:
        """递归补齐 Structured Outputs strict 模式要求。"""

        if isinstance(node, dict):
            node.pop("default", None)

            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
                node["additionalProperties"] = False

            for value in node.values():
                cls._normalize_strict_json_schema(value)
        elif isinstance(node, list):
            for value in node:
                cls._normalize_strict_json_schema(value)


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


_shared_llm_client: LLMClient | None = None
_provider_semaphore: asyncio.Semaphore | None = None
_provider_semaphore_limit: int | None = None


def _get_provider_semaphore(max_concurrency: int) -> asyncio.Semaphore:
    """返回进程内所有真实 provider 请求共享的并发限制器。"""

    global _provider_semaphore, _provider_semaphore_limit

    if _provider_semaphore is None:
        _provider_semaphore = asyncio.Semaphore(max_concurrency)
        _provider_semaphore_limit = max_concurrency
    elif _provider_semaphore_limit != max_concurrency:
        logger.warning(
            "LLM_MAX_CONCURRENCY 已在进程内初始化为 %s，忽略运行期新值 %s。",
            _provider_semaphore_limit,
            max_concurrency,
        )
    return _provider_semaphore


def get_llm_client() -> LLMClient:
    """首次真实调用时创建并复用进程级异步 LLM Client。"""

    global _shared_llm_client

    if _shared_llm_client is None:
        _shared_llm_client = LLMClient()
    return _shared_llm_client


async def close_llm_client() -> None:
    """在应用关闭时释放共享 LLM Client 和连接池。"""

    global _shared_llm_client, _provider_semaphore, _provider_semaphore_limit

    client = _shared_llm_client
    _shared_llm_client = None
    if client is not None:
        await client.close()
    _provider_semaphore = None
    _provider_semaphore_limit = None
