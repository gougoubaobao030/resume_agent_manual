from enum import Enum

from pydantic import BaseModel, Field, model_validator

from schemas.language import AnalysisLanguage


class TranslationTextType(str, Enum):
    ANALYSIS = "analysis"
    EVIDENCE = "evidence"


class TranslationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class TranslationItemRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=240)
    text_type: TranslationTextType
    text: str = Field(min_length=1, max_length=6000)


class BatchTranslationRequest(BaseModel):
    target_language: AnalysisLanguage
    items: list[TranslationItemRequest] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_items(self):
        item_ids = [item.item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("翻译请求中的item_id不能重复")
        if sum(len(item.text) for item in self.items) > 30000:
            raise ValueError("单次翻译请求文本总长度不能超过30000字符")
        return self


class TranslationItemResponse(BaseModel):
    item_id: str
    status: TranslationStatus
    translated_text: str | None = None
    error: str | None = None


class BatchTranslationResponse(BaseModel):
    target_language: AnalysisLanguage
    items: list[TranslationItemResponse]
    warnings: list[str] = Field(default_factory=list)


class LLMTranslationItem(BaseModel):
    item_id: str
    translated_text: str = Field(min_length=1)


class LLMBatchTranslationResult(BaseModel):
    items: list[LLMTranslationItem] = Field(default_factory=list)
