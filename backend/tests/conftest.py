import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SQLITE_URL = "sqlite:///./test.db"
os.environ["DATABASE_URL"] = SQLITE_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.api.deps import DemoActor

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
def test_user():
    return DemoActor(id="test_user_01", full_name="Usuario de prueba")


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def unauthenticated_client(db_session):
    with TestClient(app) as c:
        yield c
