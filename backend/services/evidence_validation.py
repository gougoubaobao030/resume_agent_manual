import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from schemas.evidence import (
    EvidenceIssueReason,
    EvidenceValidationIssue,
    EvidenceVerificationStatus,
)
from schemas.resume import Candidate


_SOURCE_ALIASES = {
    "project": "projects",
    "work": "work_experience",
    "experience": "work_experience",
}

_INDEXED_OBJECT_SOURCES = {
    "education",
    "work_experience",
    "projects",
    "candidate_evidence",
}

_INDEXED_TEXT_SOURCES = {
    "skills",
    "languages",
    "achievements",
    "certifications",
}

_ALL_INDEXED_SOURCES = (
    "education",
    "work_experience",
    "projects",
    "candidate_evidence",
    "skills",
    "languages",
    "achievements",
    "certifications",
)


@dataclass(frozen=True)
class EvidenceCheck:
    verification_status: EvidenceVerificationStatus | None
    source_type: str | None
    source_index: int | None
    source_path: str | None
    locator_verified: bool
    issue: EvidenceValidationIssue | None

    @property
    def is_verified(self) -> bool:
        return self.verification_status is not None


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_text(container: str, evidence_text: str) -> bool:
    normalized_evidence = _normalize_text(evidence_text)
    if not normalized_evidence:
        return False
    return normalized_evidence in _normalize_text(container)


def _iter_scalar_texts(value: Any, path: str):
    if isinstance(value, str):
        if value.strip():
            yield path, value
        return

    if isinstance(value, BaseModel):
        value = value.model_dump()

    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_scalar_texts(item, f"{path}.{key}" if path else str(key))
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_scalar_texts(item, f"{path}[{index}]")


def _resolve_claimed_source(
    candidate: Candidate,
    source_type: str | None,
    source_index: int | None,
) -> tuple[bool, str | None, int | None, list[tuple[str, str]]]:
    normalized_type = _SOURCE_ALIASES.get(source_type or "", source_type)

    if normalized_type == "raw_text":
        if source_index is not None or not candidate.raw_text:
            return False, normalized_type, None, []
        return True, normalized_type, None, [("raw_text", candidate.raw_text)]

    if normalized_type == "basic_info":
        if source_index is not None or candidate.basic_info is None:
            return False, normalized_type, None, []
        return True, normalized_type, None, list(
            _iter_scalar_texts(candidate.basic_info, "basic_info")
        )

    if normalized_type == "custom_attributes":
        if source_index is not None:
            return False, normalized_type, None, []
        return True, normalized_type, None, list(
            _iter_scalar_texts(candidate.custom_attributes, "custom_attributes")
        )

    if normalized_type in _ALL_INDEXED_SOURCES:
        items = getattr(candidate, normalized_type)
        if source_index is None or source_index >= len(items):
            return False, normalized_type, source_index, []
        return True, normalized_type, source_index, list(
            _iter_scalar_texts(items[source_index], f"{normalized_type}[{source_index}]")
        )

    return False, normalized_type, source_index, []


def _find_in_candidate(
    candidate: Candidate,
    evidence_text: str,
) -> tuple[str, str, int | None] | None:
    for source_type in ("basic_info", "custom_attributes"):
        value = getattr(candidate, source_type)
        for path, text in _iter_scalar_texts(value, source_type):
            if _contains_text(text, evidence_text):
                return path, source_type, None

    for source_type in _ALL_INDEXED_SOURCES:
        items = getattr(candidate, source_type)
        for index, item in enumerate(items):
            for path, text in _iter_scalar_texts(item, f"{source_type}[{index}]"):
                if _contains_text(text, evidence_text):
                    return path, source_type, index

    return None


def verify_candidate_evidence(
    *,
    candidate: Candidate,
    text: str,
    source_type: str | None,
    source_index: int | None,
    location: str,
) -> EvidenceCheck:
    """验证证据文本来源；不使用模糊匹配或语义相似度。"""

    (
        locator_is_valid,
        normalized_source_type,
        normalized_source_index,
        claimed_texts,
    ) = _resolve_claimed_source(candidate, source_type, source_index)

    locator_match = next(
        (
            path
            for path, candidate_text in claimed_texts
            if _contains_text(candidate_text, text)
        ),
        None,
    )
    raw_text_match = bool(
        candidate.raw_text and _contains_text(candidate.raw_text, text)
    )

    if locator_match:
        return EvidenceCheck(
            verification_status=(
                EvidenceVerificationStatus.RAW_TEXT_EXACT
                if raw_text_match
                else EvidenceVerificationStatus.CANDIDATE_EXACT
            ),
            source_type=normalized_source_type,
            source_index=normalized_source_index,
            source_path=locator_match,
            locator_verified=True,
            issue=None,
        )

    if raw_text_match:
        return EvidenceCheck(
            verification_status=EvidenceVerificationStatus.RAW_TEXT_EXACT,
            source_type="raw_text",
            source_index=None,
            source_path="raw_text",
            locator_verified=False,
            issue=EvidenceValidationIssue(
                location=location,
                reason=(
                    EvidenceIssueReason.LOCATOR_MISMATCH
                    if locator_is_valid
                    else EvidenceIssueReason.INVALID_SOURCE_LOCATOR
                ),
                claimed_source_type=source_type,
                claimed_source_index=source_index,
            ),
        )

    candidate_match = _find_in_candidate(candidate, text)
    if candidate_match:
        source_path, actual_source_type, actual_source_index = candidate_match
        return EvidenceCheck(
            verification_status=EvidenceVerificationStatus.CANDIDATE_EXACT,
            source_type=actual_source_type,
            source_index=actual_source_index,
            source_path=source_path,
            locator_verified=False,
            issue=EvidenceValidationIssue(
                location=location,
                reason=(
                    EvidenceIssueReason.LOCATOR_MISMATCH
                    if locator_is_valid
                    else EvidenceIssueReason.INVALID_SOURCE_LOCATOR
                ),
                claimed_source_type=source_type,
                claimed_source_index=source_index,
            ),
        )

    return EvidenceCheck(
        verification_status=None,
        source_type=None,
        source_index=None,
        source_path=None,
        locator_verified=False,
        issue=EvidenceValidationIssue(
            location=location,
            reason=(
                EvidenceIssueReason.TEXT_NOT_FOUND
                if locator_is_valid
                else EvidenceIssueReason.INVALID_SOURCE_LOCATOR
            ),
            claimed_source_type=source_type,
            claimed_source_index=source_index,
        ),
    )
