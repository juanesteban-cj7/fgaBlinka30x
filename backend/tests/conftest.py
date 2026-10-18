import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SQLITE_URL = "sqlite:///./test.db"
os.environ["DATABASE_URL"] = SQLITE_URL
os.environ["JWT_SECRET"] = "test-secret-for-auth-tests-at-least-32-chars"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.app_user import AppUser
from app.services.auth import create_access_token, hash_password

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def test_user(db_session):
    user = AppUser(
        id="test_user_01",
        username="test.user",
        full_name="Usuario de prueba",
        password_hash=hash_password("test-password"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def client(test_user):
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {create_access_token(test_user.id)}"
        yield c


@pytest.fixture()
def unauthenticated_client(db_session):
    with TestClient(app) as c:
        yield c
