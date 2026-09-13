import json
from pathlib import Path

from pydantic import ValidationError

from clients.llm_client import LLMClient
from prompts.scoring_prompt import (
    JOB_MATCH_SYSTEM_PROMPT,
    build_job_match_user_prompt,
)
from schemas.jd import JDParseResponse
from schemas.resume import Candidate
from schemas.scoring import (
    LLMJobMatchResult,
    LLMRequirementMatch,
)


TEST_DATA_PATH = (
    Path(__file__).parent
    / "test_data"
    / "scoring_integration_case.json"
)


def _print_exception_chain(exc: BaseException) -> None:
    """Print validation details without changing or concealing the failure."""

    print(f"Exception type: {type(exc)!r}")
    print(f"Exception: {exc}")

    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, ValidationError):
            print("ValidationError details:")
            print(
                json.dumps(
                    current.errors(include_url=False),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        current = current.__cause__


def test_real_deepseek_job_match_structured_output() -> None:
    """Exercise the real scoring prompt/client/DeepSeek/Pydantic chain."""

    test_data = json.loads(TEST_DATA_PATH.read_text(encoding="utf-8"))
    jd_response = JDParseResponse.model_validate(test_data["jd_response"])
    candidate = Candidate.model_validate(test_data["candidate"])
    jd = jd_response.job

    user_prompt = build_job_match_user_prompt(
        jd_data=jd.model_dump(mode="json"),
        candidate_data=candidate.model_dump(mode="json"),
    )

    client = LLMClient()
    print("DeepSeek integration configuration:")
    print("Base URL:", client.base_url)
    print("Model:", client.model)
    print("Timeout:", client.timeout)

    try:
        result = client.generate_structured(
            system_prompt=JOB_MATCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=LLMJobMatchResult,
            temperature=0.1,
        )
    except Exception as exc:
        _print_exception_chain(exc)
        raise

    print("type(result):", type(result))
    print(
        "type(result.requirement_matches):",
        type(result.requirement_matches),
    )
    if result.requirement_matches:
        print(
            "type(result.requirement_matches[0]):",
            type(result.requirement_matches[0]),
        )

    print("Complete structured result:")
    print(
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("Requirement-by-requirement result:")
    for item in result.requirement_matches:
        print(
            json.dumps(
                {
                    "requirement_id": item.requirement_id,
                    "status": item.status.value,
                    "score": item.score,
                    "confidence": item.confidence.value,
                    "reason": item.reason,
                    "evidence": [
                        evidence.model_dump(mode="json")
                        for evidence in item.evidence
                    ],
                    "missing_information": item.missing_information,
                    "needs_raw_review": item.needs_raw_review,
                    "raw_review_reason": item.raw_review_reason,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    expected_ids = [item.id for item in jd.requirements]
    actual_ids = [item.requirement_id for item in result.requirement_matches]

    assert isinstance(result, LLMJobMatchResult)
    assert isinstance(result.requirement_matches, list)
    assert len(result.requirement_matches) == len(jd.requirements)
    assert all(
        isinstance(item, LLMRequirementMatch)
        for item in result.requirement_matches
    )
    assert all(requirement_id in expected_ids for requirement_id in actual_ids)
    assert set(actual_ids) == set(expected_ids)
    assert len(actual_ids) == len(set(actual_ids))
    assert all(0 <= item.score <= 100 for item in result.requirement_matches)
    assert all(isinstance(item.evidence, list) for item in result.requirement_matches)
    assert all(
        isinstance(item.missing_information, list)
        for item in result.requirement_matches
    )
    assert all(
        isinstance(item.needs_raw_review, bool)
        for item in result.requirement_matches
    )
    assert isinstance(result.missing_information, list)
    assert isinstance(result.raw_review_requirement_ids, list)
    assert isinstance(result.needs_raw_review, bool)
