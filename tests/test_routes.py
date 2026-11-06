import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.main import app

# SQLite en mémoire par défaut (local), PostgreSQL si TEST_DATABASE_URL est définie (CI)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

if TEST_DATABASE_URL.startswith("sqlite"):
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

URL = "https://example.com"


@pytest.fixture(autouse=True)
def test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


class TestShorten:
    def test_creates_link(self):
        r = client.post("/shorten", json={"original_url": URL})
        assert r.status_code == 200
        assert "short_url" in r.json()

    def test_same_url_returns_same_code(self):
        a = client.post("/shorten", json={"original_url": URL}).json()
        b = client.post("/shorten", json={"original_url": URL}).json()
        assert a["short_url"] == b["short_url"]


class TestRedirect:
    def test_redirects_to_original(self):
        code = client.post("/shorten", json={"original_url": URL}).json()["short_url"]
        r = client.get(f"/{code}", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert r.headers["location"] == URL

    def test_unknown_code_returns_404(self):
        assert client.get("/zzzzzz", follow_redirects=False).status_code == 404


class TestValidation:
    def test_missing_field_returns_422(self):
        assert client.post("/shorten", json={}).status_code == 422

    @pytest.mark.xfail(reason="Pas de validation d'URL : limite connue")
    def test_dangerous_url_is_rejected(self):
        r = client.post("/shorten", json={"original_url": "javascript:alert(1)"})
        assert r.status_code == 422