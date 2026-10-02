from enum import Enum

from pydantic import BaseModel


class EvidenceVerificationStatus(str, Enum):
    """证据文本能够被哪一层输入事实精确确认。"""

    CANDIDATE_EXACT = "candidate_exact"
    RAW_TEXT_EXACT = "raw_text_exact"


class EvidenceIssueReason(str, Enum):
    """证据没有完全通过来源定位校验的原因。"""

    LOCATOR_MISMATCH = "locator_mismatch"
    INVALID_SOURCE_LOCATOR = "invalid_source_locator"
    TEXT_NOT_FOUND = "text_not_found"


class EvidenceValidationIssue(BaseModel):
    """供 API 消费方识别证据校验异常，不把异常文本当作正式证据。"""

    location: str
    reason: EvidenceIssueReason
    claimed_source_type: str | None = None
    claimed_source_index: int | None = None
