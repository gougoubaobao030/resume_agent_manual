import unittest

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.main import app
from database import SessionLocal
from models import UserModel
from services.auth_service import create_user


class AuthPersistenceTest(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as db:
            db.execute(delete(UserModel).where(UserModel.username == "auth_flow_test"))
            db.commit()
            create_user(db, username="auth_flow_test", password="old-pass-123")

    def tearDown(self):
        with SessionLocal() as db:
            db.execute(delete(UserModel).where(UserModel.username == "auth_flow_test"))
            db.commit()

    def test_password_change_rotates_current_and_revokes_other_sessions(self):
        current = TestClient(app)
        other = TestClient(app)
        credentials = {"username": "auth_flow_test", "password": "old-pass-123"}
        self.assertEqual(current.post("/api/auth/login", json=credentials).status_code, 200)
        self.assertEqual(other.post("/api/auth/login", json=credentials).status_code, 200)

        changed = current.put("/api/users/me/password", json={
            "current_password": "old-pass-123",
            "new_password": "new-pass-456",
        })
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(current.get("/api/auth/me").status_code, 200)
        self.assertEqual(other.get("/api/auth/me").status_code, 401)
        self.assertEqual(current.post("/api/auth/logout").status_code, 204)
        self.assertEqual(current.post("/api/auth/login", json=credentials).status_code, 401)
        self.assertEqual(current.post("/api/auth/login", json={
            "username": "auth_flow_test", "password": "new-pass-456"
        }).status_code, 200)


if __name__ == "__main__":
    unittest.main()
