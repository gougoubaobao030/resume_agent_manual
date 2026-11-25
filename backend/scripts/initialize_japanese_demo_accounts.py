"""Create the four Japanese demo users and clone one user's business dataset.

This is an explicit, idempotent initialization command. It never runs during
login or application startup, and it never stores plaintext passwords.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, uuid5


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

SEED_KEY = "japanese-demo-v1"
SOURCE_USERNAME = "admin_cn"
TARGET_USERNAMES = ("ra333", "ra555", "ra777", "ra888")
TARGET_LANGUAGE = "ja-JP"
BUSINESS_TABLES = (
    "jobs",
    "candidates",
    "job_candidates",
    "scoring_results",
    "talent_discovery_results",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(kind: str, target_user_id: str, source_id: str) -> str:
    value = uuid5(
        NAMESPACE_URL,
        f"resume-agent:{SEED_KEY}:{target_user_id}:{kind}:{source_id}",
    )
    return f"{kind}_{value.hex}"


def _json_value(value):
    return json.loads(value) if isinstance(value, str) else value


def _resolve_resume(data_root: Path, resume_path: str) -> Path:
    key = PurePosixPath(resume_path)
    if key.is_absolute() or ".." in key.parts or key.parts[:1] != ("resumes",):
        raise RuntimeError(f"Invalid resume path in source data: {resume_path}")
    root = data_root.resolve()
    resolved = root.joinpath(*key.parts).resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"Resume path escapes data root: {resume_path}")
    return resolved


def _source_snapshot(connection: sqlite3.Connection, source_user_id: str) -> dict:
    snapshot = {}
    for table in BUSINESS_TABLES:
        rows = connection.execute(
            f"SELECT * FROM {table} WHERE user_id = ? ORDER BY rowid",
            (source_user_id,),
        ).fetchall()
        snapshot[table] = [dict(row) for row in rows]
    return snapshot


def _source_fingerprint(snapshot: dict, data_root: Path) -> str:
    payload = {"tables": snapshot, "resume_files": []}
    for candidate in snapshot["candidates"]:
        resume_path = candidate.get("resume_path")
        if not resume_path:
            continue
        physical_path = _resolve_resume(data_root, resume_path)
        if not physical_path.is_file():
            raise RuntimeError(f"Source resume is missing: {resume_path}")
        payload["resume_files"].append({
            "candidate_id": candidate["id"],
            "resume_path": resume_path,
            "sha256": _sha256(physical_path),
        })
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _create_or_load_users() -> dict[str, str]:
    from sqlalchemy import select

    from database import SessionLocal
    from models import UserModel
    from services.auth_service import create_user

    with SessionLocal() as db:
        existing = {
            row.username: row
            for row in db.scalars(
                select(UserModel).where(UserModel.username.in_(TARGET_USERNAMES))
            ).all()
        }

    missing = [username for username in TARGET_USERNAMES if username not in existing]
    password = None
    if missing:
        password = getpass("Demo account password: ")
        confirmation = getpass("Confirm demo account password: ")
        if password != confirmation:
            raise SystemExit("Password confirmation does not match")
        if len(password) < 8:
            raise SystemExit("Password must contain at least 8 characters")

    for username in missing:
        with SessionLocal() as db:
            user = create_user(
                db,
                username=username,
                password=password,
                display_name=username,
                preferred_language=TARGET_LANGUAGE,
            )
            existing[username] = user

    with SessionLocal() as db:
        users = {
            row.username: row
            for row in db.scalars(
                select(UserModel).where(UserModel.username.in_(TARGET_USERNAMES))
            ).all()
        }
        for username in TARGET_USERNAMES:
            user = users.get(username)
            if user is None or not user.is_active:
                raise RuntimeError(f"Demo user is missing or inactive: {username}")
            if user.preferred_language != TARGET_LANGUAGE:
                user.preferred_language = TARGET_LANGUAGE
        db.commit()
        return {username: users[username].id for username in TARGET_USERNAMES}


def _mapped_rows(snapshot: dict, target_user_id: str) -> tuple[dict, dict, dict]:
    job_map = {
        row["id"]: _stable_id("job", target_user_id, row["id"])
        for row in snapshot["jobs"]
    }
    candidate_map = {
        row["id"]: _stable_id("candidate", target_user_id, row["id"])
        for row in snapshot["candidates"]
    }
    mapped = {table: [] for table in BUSINESS_TABLES}

    for source in snapshot["jobs"]:
        row = dict(source)
        row.update(id=job_map[source["id"]], user_id=target_user_id,
                   created_by=target_user_id)
        mapped["jobs"].append(row)

    for source in snapshot["candidates"]:
        row = dict(source)
        new_id = candidate_map[source["id"]]
        row.update(id=new_id, user_id=target_user_id, created_by=target_user_id)
        if source.get("resume_path"):
            row["resume_path"] = PurePosixPath(
                "resumes", new_id, "original.pdf"
            ).as_posix()
        mapped["candidates"].append(row)

    for source in snapshot["job_candidates"]:
        row = dict(source)
        row.update(
            user_id=target_user_id,
            job_id=job_map[source["job_id"]],
            candidate_id=candidate_map[source["candidate_id"]],
            added_by=target_user_id,
        )
        mapped["job_candidates"].append(row)

    for source in snapshot["scoring_results"]:
        row = dict(source)
        result = _json_value(source["result_json"])
        result["job_id"] = job_map[source["job_id"]]
        result["candidate_id"] = candidate_map[source["candidate_id"]]
        row.update(
            id=_stable_id("score", target_user_id, source["id"]),
            user_id=target_user_id,
            job_id=job_map[source["job_id"]],
            candidate_id=candidate_map[source["candidate_id"]],
            result_json=json.dumps(result, ensure_ascii=False),
            created_by=target_user_id,
        )
        mapped["scoring_results"].append(row)

    for source in snapshot["talent_discovery_results"]:
        row = dict(source)
        result = _json_value(source["result_json"])
        result["candidate_id"] = candidate_map[source["candidate_id"]]
        row.update(
            id=_stable_id("talent", target_user_id, source["id"]),
            user_id=target_user_id,
            candidate_id=candidate_map[source["candidate_id"]],
            result_json=json.dumps(result, ensure_ascii=False),
            created_by=target_user_id,
        )
        mapped["talent_discovery_results"].append(row)

    return mapped, job_map, candidate_map


def _insert_rows(connection: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    placeholders = ", ".join(f":{column}" for column in columns)
    column_sql = ", ".join(columns)
    connection.executemany(
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
        rows,
    )


def _copy_resumes(
    snapshot: dict,
    mapped_candidates: list[dict],
    data_root: Path,
) -> None:
    mapped_by_source = dict(zip(
        (row["id"] for row in snapshot["candidates"]),
        mapped_candidates,
        strict=True,
    ))
    for source in snapshot["candidates"]:
        source_resume = source.get("resume_path")
        if not source_resume:
            continue
        source_path = _resolve_resume(data_root, source_resume)
        target_path = _resolve_resume(
            data_root, mapped_by_source[source["id"]]["resume_path"]
        )
        source_hash = _sha256(source_path)
        if target_path.exists():
            if _sha256(target_path) != source_hash:
                raise RuntimeError(f"Existing cloned resume differs: {target_path}")
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path = target_path.with_suffix(".pdf.tmp")
        shutil.copyfile(source_path, staged_path)
        if _sha256(staged_path) != source_hash:
            staged_path.unlink(missing_ok=True)
            raise RuntimeError(f"Resume verification failed: {target_path}")
        os.replace(staged_path, target_path)


def _validate_target(
    connection: sqlite3.Connection,
    target_user_id: str,
    expected: dict,
) -> None:
    for table, rows in expected.items():
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()[0]
        if count != len(rows):
            raise RuntimeError(
                f"Target validation failed for {table}: expected {len(rows)}, got {count}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Japanese demo accounts and clone the CN business dataset"
    )
    parser.add_argument(
        "--database-url",
        help="Override DATABASE_URL before loading the application database module",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=PROJECT_ROOT / "data",
        help="Data root containing the resumes directory",
    )
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from sqlalchemy.engine import make_url

    from database import DATABASE_URL

    database_url = make_url(DATABASE_URL)
    if not database_url.drivername.startswith("sqlite") or not database_url.database:
        raise SystemExit("This initializer currently supports the project's SQLite database")
    database_path = Path(database_url.database).resolve()
    data_root = args.data_root.resolve()

    target_users = _create_or_load_users()
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        source = connection.execute(
            "SELECT id FROM users WHERE username = ?", (SOURCE_USERNAME,)
        ).fetchone()
        if source is None:
            raise RuntimeError(f"Source user does not exist: {SOURCE_USERNAME}")
        source_user_id = source["id"]
        snapshot = _source_snapshot(connection, source_user_id)
        if not snapshot["jobs"] or not snapshot["candidates"]:
            raise RuntimeError("Source user has no business dataset to clone")
        fingerprint = _source_fingerprint(snapshot, data_root)

        plans = {}
        for username, target_user_id in target_users.items():
            mapped, _, _ = _mapped_rows(snapshot, target_user_id)
            marker = connection.execute(
                "SELECT source_fingerprint FROM data_initialization_runs "
                "WHERE seed_key = ? AND target_user_id = ?",
                (SEED_KEY, target_user_id),
            ).fetchone()
            if marker is not None:
                if marker["source_fingerprint"] != fingerprint:
                    raise RuntimeError(
                        f"Seed source changed after {username} was initialized"
                    )
                _validate_target(connection, target_user_id, mapped)
                continue
            existing_count = sum(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
                    (target_user_id,),
                ).fetchone()[0]
                for table in BUSINESS_TABLES
            )
            if existing_count:
                raise RuntimeError(
                    f"Target user already has untracked business data: {username}"
                )
            plans[username] = (target_user_id, mapped)

        for _, mapped in plans.values():
            _copy_resumes(snapshot, mapped["candidates"], data_root)

        connection.execute("BEGIN IMMEDIATE")
        try:
            for username, (target_user_id, mapped) in plans.items():
                for table in BUSINESS_TABLES:
                    _insert_rows(connection, table, mapped[table])
                _validate_target(connection, target_user_id, mapped)
                details = {
                    "source_username": SOURCE_USERNAME,
                    "target_username": username,
                    "counts": {table: len(rows) for table, rows in mapped.items()},
                }
                connection.execute(
                    "INSERT INTO data_initialization_runs "
                    "(seed_key, target_user_id, source_user_id, source_fingerprint, "
                    "details_json, completed_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        SEED_KEY,
                        target_user_id,
                        source_user_id,
                        fingerprint,
                        json.dumps(details, ensure_ascii=False),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RuntimeError(f"Foreign key validation failed: {foreign_key_errors[:10]}")
        print(
            f"Initialization verified for {len(target_users)} demo users; "
            f"newly seeded: {len(plans)}"
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
