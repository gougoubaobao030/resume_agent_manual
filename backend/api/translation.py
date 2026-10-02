from fastapi import APIRouter, HTTPException

from clients.llm_client import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseError,
)
from schemas.translation import BatchTranslationRequest, BatchTranslationResponse
from services.translation_service import translate_batch


router = APIRouter(
    prefix="/api/translations",
    tags=["translation"],
)


@router.post("/batch", response_model=BatchTranslationResponse)
def translate_batch_api(
    request: BatchTranslationRequest,
) -> BatchTranslationResponse:
    try:
        return translate_batch(request)
    except LLMConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMRequestError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
