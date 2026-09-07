from pathlib import Path
from uuid import uuid4

from clients.llm_client import LLMClient

from prompts.resume_prompt import (
    RESUME_SYSTEM_PROMPT,
    RESUME_USER_PROMPT_TEMPLATE,
)
from schemas.resume import (
    BasicInfo,
    Candidate,
    CandidateEvidence,
    Education,
    ExtractionMetadata,
    Project,
    ResumeLLMResult,
    WorkExperience,
    ResumeBatchParseResponse,
    ResumeParseItemResult,
)
from services.pdf_service import extract_pdf_text

llm_client = LLMClient()

def _generate_candidate_id() -> str:
    return f"candidate_{uuid4().hex[:8]}"


def _build_candidate(
    llm_result: ResumeLLMResult,
    raw_text: str,
    source_file: str | None = None,
) -> Candidate:

    basic_info = None

    if llm_result.basic_info is not None:
        basic_info = BasicInfo.model_validate(
            llm_result.basic_info.model_dump()
        )

    education = [
        Education.model_validate(item.model_dump())
        for item in llm_result.education
    ]

    work_experience = [
        WorkExperience.model_validate(item.model_dump())
        for item in llm_result.work_experience
    ]

    projects = [
        Project.model_validate(item.model_dump())
        for item in llm_result.projects
    ]

    candidate_evidence = [
        CandidateEvidence.model_validate(item.model_dump())
        for item in llm_result.candidate_evidence
    ]

    return Candidate(
        id=_generate_candidate_id(),
        basic_info=basic_info,
        education=education,
        work_experience=work_experience,
        projects=projects,
        skills=llm_result.skills,
        languages=llm_result.languages,
        achievements=llm_result.achievements,
        certifications=llm_result.certifications,
        candidate_evidence=candidate_evidence,
        custom_attributes={},
        raw_text=raw_text,
        extraction_metadata=ExtractionMetadata(
            source_file=source_file,
            parser="unstructured",
        ),
    )


def parse_resume_text(
    raw_text: str,
    source_file: str | None = None,
) -> Candidate:

    cleaned_text = raw_text.strip()

    if not cleaned_text:
        raise ValueError(
            "简历文本为空，无法解析"
        )

    user_prompt = RESUME_USER_PROMPT_TEMPLATE.format(
        resume_text=cleaned_text
    )

    #以后要批量的
    #llm_client = LLMClient()

    llm_result = llm_client.generate_structured(
        system_prompt=RESUME_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=ResumeLLMResult,
    )

    return _build_candidate(
        llm_result=llm_result,
        raw_text=cleaned_text,
        source_file=source_file,
    )


def parse_resume_pdf(
    pdf_path: str,
    source_file: str | None = None,
) -> Candidate:

    path = Path(pdf_path)

    raw_text = extract_pdf_text(
        str(path)
    )

    if not raw_text.strip():
        raise ValueError(
            "无法解析简历，请上传文本型PDF"
        )

    return parse_resume_text(
        raw_text=raw_text,
        source_file=source_file or path.name,
    )

def parse_resume_batch(
    files: list[tuple[str, str]],
) -> ResumeBatchParseResponse:

    results = []

    for filename, pdf_path in files:

        try:
            candidate = parse_resume_pdf(
                pdf_path=pdf_path,
                source_file=filename,
            )

            results.append(
                ResumeParseItemResult(
                    filename=filename,
                    success=True,
                    candidate=candidate,
                )
            )

        except Exception as exc:
            results.append(
                ResumeParseItemResult(
                    filename=filename,
                    success=False,
                    error=str(exc),
                )
            )

    success_count = sum(
        1
        for result in results
        if result.success
    )

    failed_count = len(results) - success_count

    return ResumeBatchParseResponse(
        total=len(results),
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )