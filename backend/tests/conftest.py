import os
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-only-secret-key-with-more-than-32-characters"
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_ADMIN_BOOTSTRAP"] = "false"

import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine, SessionLocal
from app.main import app
from app.models import User, UserRole
from app.core.security import hash_password

@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    db.add(User(email="admin@example.com",full_name="Test Admin",password_hash=hash_password("AdminPass123!"),role=UserRole.ADMIN))
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
