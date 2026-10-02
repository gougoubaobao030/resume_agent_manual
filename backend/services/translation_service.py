import os

from clients.llm_client import LLMClient, LLMResponseError
from prompts.translation_prompt import (
    TRANSLATION_SYSTEM_PROMPT,
    build_translation_user_prompt,
)
from schemas.translation import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    LLMBatchTranslationResult,
    TranslationItemResponse,
    TranslationStatus,
)


def _is_translation_mock_enabled() -> bool:
    return os.getenv("TRANSLATION_USE_MOCK", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_mock_result(request: BatchTranslationRequest) -> LLMBatchTranslationResult:
    """测试映射和调用链；Mock 文本不冒充真实机器翻译质量。"""

    return LLMBatchTranslationResult(
        items=[
            {
                "item_id": item.item_id,
                "translated_text": f"[Mock {request.target_language.value}] {item.text}",
            }
            for item in request.items
        ]
    )


def _map_translation_result(
    request: BatchTranslationRequest,
    llm_result: LLMBatchTranslationResult,
) -> BatchTranslationResponse:
    expected_ids = [item.item_id for item in request.items]
    actual_ids = [item.item_id for item in llm_result.items]

    if len(actual_ids) != len(set(actual_ids)):
        raise LLMResponseError("模型翻译结果包含重复item_id")

    unknown_ids = set(actual_ids) - set(expected_ids)
    if unknown_ids:
        raise LLMResponseError(
            f"模型翻译结果包含未知item_id: {sorted(unknown_ids)}"
        )

    translated_by_id = {
        item.item_id: item.translated_text
        for item in llm_result.items
    }
    response_items: list[TranslationItemResponse] = []
    missing_ids: list[str] = []
    for item_id in expected_ids:
        translated_text = translated_by_id.get(item_id)
        if translated_text:
            response_items.append(TranslationItemResponse(
                item_id=item_id,
                status=TranslationStatus.SUCCESS,
                translated_text=translated_text,
            ))
        else:
            missing_ids.append(item_id)
            response_items.append(TranslationItemResponse(
                item_id=item_id,
                status=TranslationStatus.FAILED,
                error="模型未返回该翻译项",
            ))

    warnings = []
    if missing_ids:
        warnings.append(
            f"{len(missing_ids)}个翻译项未返回，原文应继续保留显示。"
        )

    return BatchTranslationResponse(
        target_language=request.target_language,
        items=response_items,
        warnings=warnings,
    )


def translate_batch(
    request: BatchTranslationRequest,
    llm_client: LLMClient | None = None,
) -> BatchTranslationResponse:
    """独立完成批量翻译，不修改任何评分、人才发现或原文对象。"""

    if llm_client is not None:
        result = llm_client.generate_structured(
            system_prompt=TRANSLATION_SYSTEM_PROMPT,
            user_prompt=build_translation_user_prompt(
                target_language=request.target_language,
                items=request.items,
            ),
            response_model=LLMBatchTranslationResult,
            temperature=0.1,
        )
    elif _is_translation_mock_enabled():
        result = _build_mock_result(request)
    else:
        client = LLMClient()
        result = client.generate_structured(
            system_prompt=TRANSLATION_SYSTEM_PROMPT,
            user_prompt=build_translation_user_prompt(
                target_language=request.target_language,
                items=request.items,
            ),
            response_model=LLMBatchTranslationResult,
            temperature=0.1,
        )

    return _map_translation_result(request, result)
