import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Iterator
from uuid import uuid4

from database import PROJECT_ROOT


DATA_ROOT = PROJECT_ROOT / "data"
_resume_write_lock = Lock()


def candidate_resume_key(candidate_id: str) -> str:
    if not candidate_id:
        raise ValueError("Candidate缺少id，无法保存原始简历")
    key = PurePosixPath("resumes", candidate_id, "original.pdf").as_posix()
    resolve_resume_path(key)
    return key


def resolve_resume_path(resume_path: str) -> Path:
    key = PurePosixPath(resume_path)
    if key.is_absolute() or ".." in key.parts or key.parts[:1] != ("resumes",):
        raise ValueError("原始简历存储路径无效")

    data_root = DATA_ROOT.resolve()
    resolved = data_root.joinpath(*key.parts).resolve()
    if data_root not in resolved.parents:
        raise ValueError("原始简历存储路径超出data目录")
    return resolved


@contextmanager
def store_candidate_resume(source_path: str, candidate_id: str) -> Iterator[str]:
    """原子替换 Candidate 的原始 PDF；调用方失败时恢复原文件。"""

    resume_path = candidate_resume_key(candidate_id)
    target_path = resolve_resume_path(resume_path)

    with _resume_write_lock:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path: Path | None = None
        backup_path: Path | None = None
        promoted = False

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                dir=target_path.parent,
                suffix=".tmp",
            ) as staged_file:
                staged_path = Path(staged_file.name)
                with open(source_path, "rb") as source_file:
                    shutil.copyfileobj(source_file, staged_file)

            if target_path.exists():
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    dir=target_path.parent,
                    suffix=".bak",
                ) as backup_file:
                    backup_path = Path(backup_file.name)
                os.replace(target_path, backup_path)

            os.replace(staged_path, target_path)
            staged_path = None
            promoted = True

            yield resume_path
        except Exception:
            if promoted:
                target_path.unlink(missing_ok=True)
            if backup_path is not None:
                os.replace(backup_path, target_path)
                backup_path = None
            raise
        else:
            if backup_path is not None:
                backup_path.unlink(missing_ok=True)
                backup_path = None
        finally:
            if staged_path is not None:
                staged_path.unlink(missing_ok=True)
            if backup_path is not None:
                backup_path.unlink(missing_ok=True)


@contextmanager
def stage_candidate_resume_deletion(resume_path: str | None) -> Iterator[None]:
    """Stage one Candidate PDF for deletion and restore it if the caller fails."""

    if not resume_path:
        yield
        return

    target_path = resolve_resume_path(resume_path)

    with _resume_write_lock:
        if not target_path.is_file():
            yield
            return

        staged_path = target_path.with_name(
            f".{target_path.name}.{uuid4().hex}.delete"
        )
        os.replace(target_path, staged_path)

        try:
            yield
        except Exception:
            os.replace(staged_path, target_path)
            raise
        else:
            staged_path.unlink(missing_ok=True)
            try:
                target_path.parent.rmdir()
            except OSError:
                pass
