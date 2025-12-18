
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import csv
import io

from main import app
from api.routes import get_db
from models import Base, Call, Evaluation

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_csv_injection_sanitization(test_db):
    """
    Test that CSV injection payloads are sanitized in the export.
    """
    # Create a session to insert data
    db = TestingSessionLocal()

    # 1. Insert a call with malicious data
    malicious_manager = "=1+1" # Simple formula injection
    malicious_id = "@import_data"

    call = Call(
        filename="test.mp3",
        audio_url="/tmp/test.mp3",
        manager=malicious_manager,
        call_identifier=malicious_id,
        duration=60
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    # 2. Insert an evaluation so the call is included in export
    evaluation = Evaluation(
        call_id=call.id,
        scores={"1": {"score": 1}},
        итоговая_оценка=10,
        score_percent=100,
        нарушения=False,
        комментарии="Test"
    )
    db.add(evaluation)
    db.commit()

    db.close()

    # 3. Call the export endpoint
    response = client.get("/api/export")
    assert response.status_code == 200

    # 4. Check the content
    content = response.content.decode("utf-8-sig")

    # Parse CSV to find the row
    f = io.StringIO(content)
    reader = csv.reader(f)
    rows = list(reader)

    # Row 0: Header 1
    # Row 1: Header 2
    # Row 2: Data

    assert len(rows) >= 3
    data_row = rows[2]

    # Manager is index 5, ID is index 6
    manager_val = data_row[5]
    id_val = data_row[6]

    # Check for sanitization (must start with single quote)
    assert manager_val == "'=1+1"
    assert id_val == "'@import_data"
