from typing import Literal

from pydantic import BaseModel, Field, model_validator

from schemas.resume import Candidate


TalentMode = Literal[
    "auto",
    "specified",
]

TalentLevel = Literal[
    "high",
    "medium_high",
    "medium",
    "medium_low",
    "low",
]


class TalentEvidence(BaseModel):
    """支持人才能力判断的候选人事实证据。"""

    text: str = Field(
        ...,
        min_length=1,
    )

    source_type: str | None = None

    source_index: int | None = Field(
        default=None,
        ge=0,
    )


class TalentAbility(BaseModel):
    """AI从候选人资料中发现的一项值得关注的能力。"""

    ability_name: str = Field(
        ...,
        min_length=1,
    )

    level: TalentLevel

    reason: str = Field(
        ...,
        min_length=1,
    )

    evidence: list[TalentEvidence] = Field(
        default_factory=list,
    )


class SpecifiedTraitResult(BaseModel):
    """候选人资料对某一个HR指定人才特征的支持结果。"""

    trait: str = Field(
        ...,
        min_length=1,
    )

    fit_level: TalentLevel

    reason: str = Field(
        ...,
        min_length=1,
    )

    evidence: list[TalentEvidence] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )


class TalentDiscoveryRequest(BaseModel):
    """人才能力发现请求。"""

    candidate: Candidate

    mode: TalentMode = "auto"

    desired_traits: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_mode_and_traits(self):
        if self.mode == "specified" and not self.desired_traits:
            raise ValueError(
                "specified模式必须提供desired_traits"
            )

        if self.mode == "auto" and self.desired_traits:
            raise ValueError(
                "auto模式不应提供desired_traits"
            )

        return self


class TalentDiscoveryResult(BaseModel):
    """人才能力发现模块最终业务结果。"""

    candidate_id: str

    mode: TalentMode

    attention_level: TalentLevel | None = None

    specified_fit_level: TalentLevel | None = None

    summary: str = Field(
        ...,
        min_length=1,
    )

    abilities: list[TalentAbility] = Field(
        default_factory=list,
    )

    specified_traits: list[SpecifiedTraitResult] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_result_by_mode(self):
        if self.mode == "auto":
            if self.attention_level is None:
                raise ValueError(
                    "auto模式必须包含attention_level"
                )

            if self.specified_fit_level is not None:
                raise ValueError(
                    "auto模式不应包含specified_fit_level"
                )

            if self.specified_traits:
                raise ValueError(
                    "auto模式不应包含specified_traits"
                )

        if self.mode == "specified":
            if self.specified_fit_level is None:
                raise ValueError(
                    "specified模式必须包含specified_fit_level"
                )

        return self
    
## LLM响应schema
class LLMTalentEvidence(BaseModel):
    """LLM返回的人才能力证据。"""

    text: str = Field(
        ...,
        min_length=1,
    )

    source_type: str | None = None

    source_index: int | None = Field(
        default=None,
        ge=0,
    )


class LLMTalentAbility(BaseModel):
    """LLM主动发现的一项候选人能力。"""

    ability_name: str = Field(
        ...,
        min_length=1,
    )

    level: TalentLevel

    reason: str = Field(
        ...,
        min_length=1,
    )

    evidence: list[LLMTalentEvidence] = Field(
        default_factory=list,
    )


class LLMSpecifiedTraitResult(BaseModel):
    """LLM对某一个HR指定人才特征的分析结果。"""

    trait: str = Field(
        ...,
        min_length=1,
    )

    fit_level: TalentLevel

    reason: str = Field(
        ...,
        min_length=1,
    )

    evidence: list[LLMTalentEvidence] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )


class LLMTalentDiscoveryResult(BaseModel):
    """LLM返回的人才能力发现结果。"""

    mode: TalentMode

    attention_level: TalentLevel | None = None

    specified_fit_level: TalentLevel | None = None

    summary: str = Field(
        ...,
        min_length=1,
    )

    abilities: list[LLMTalentAbility] = Field(
        default_factory=list,
    )

    specified_traits: list[LLMSpecifiedTraitResult] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_result_by_mode(self):
        if self.mode == "auto":
            if self.attention_level is None:
                raise ValueError(
                    "auto模式必须包含attention_level"
                )

            if self.specified_fit_level is not None:
                raise ValueError(
                    "auto模式不应包含specified_fit_level"
                )

            if self.specified_traits:
                raise ValueError(
                    "auto模式不应包含specified_traits"
                )

        if self.mode == "specified":
            if self.specified_fit_level is None:
                raise ValueError(
                    "specified模式必须包含specified_fit_level"
                )

        return self