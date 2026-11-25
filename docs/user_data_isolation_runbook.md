# User data isolation operations runbook

This runbook covers the permanent single-database, per-user isolation introduced
by Alembic revision `0005`. Plaintext passwords must never be added to this file,
the repository, or command history.

## Deployment order

1. Stop the backend so no new writes or in-memory resume tasks can start.
2. Create an SQLite online backup with Python's `sqlite3.Connection.backup()`.
   Do not copy only the `.db` file while WAL mode is active.
3. Copy `data/resumes` and verify the file count and SHA-256 hashes.
4. Run `python -m alembic upgrade head` from `backend`.
5. Verify `PRAGMA quick_check`, `PRAGMA foreign_key_check`, table counts, and
   that all legacy business rows belong to the confirmed `admin_cn` user ID.
6. Run `python scripts/initialize_japanese_demo_accounts.py`. Enter the demo
   password only at the hidden prompt.
7. Run the initializer a second time. It must report `newly seeded: 0`.
8. Validate each account through the login API, then restart the application.

The initializer is explicit and is never called by login or application
startup. It records a source-data fingerprint in `data_initialization_runs`,
uses deterministic cloned record IDs, rejects untracked target data, and
verifies copied resume hashes.

## Current production migration snapshot

The pre-migration recovery snapshot created on 2026-10-31 is:

`data/backups/pre_user_isolation_20261031_01`

It contains an SQLite online backup at revision `0004` and a byte-for-byte
verified copy of the 26 source resume files. Keep this directory unchanged
until the migrated environment has been accepted.

## Recovery

Revision `0005` deliberately refuses to downgrade after tenant data exists,
because collapsing account-scoped unique constraints would destroy data.
Recovery therefore means restoring the complete snapshot, not running
`alembic downgrade`:

1. Stop backend and frontend processes.
2. Preserve the failed database and `data/resumes` separately for diagnosis.
3. Restore both `resume_agent.db` and the complete `resumes` directory from the
   same pre-migration snapshot.
4. Remove stale `resume_agent.db-wal` and `resume_agent.db-shm` files only while
   the backend is stopped and only after confirming the restored paths.
5. Check Alembic revision `0004`, `PRAGMA quick_check`, foreign keys, table
   counts, and resume hashes before starting the old application code.

Never restore only the database or only the resume directory; they form one
consistent recovery unit.
