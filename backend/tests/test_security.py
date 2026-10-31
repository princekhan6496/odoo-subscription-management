from app.core.security import hash_password, verify_password, create_access_token
import jwt
from app.core.config import settings

def test_password_hash_round_trip():
    hashed = hash_password("SecurePass123!")
    assert hashed != "SecurePass123!"
    assert verify_password("SecurePass123!", hashed)
    assert not verify_password("wrong", hashed)

def test_token_contains_subject():
    token = create_access_token("42")
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == "42"
