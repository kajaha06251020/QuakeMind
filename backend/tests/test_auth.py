import pytest
from app.services.auth import create_access_token, verify_token, hash_password, verify_password
from fastapi import HTTPException

def test_create_and_verify_token():
    token = create_access_token({"sub": "user1"})
    payload = verify_token(token)
    assert payload["sub"] == "user1"

def test_invalid_token():
    with pytest.raises(HTTPException):
        verify_token("invalid.token.here")

def test_password_hash():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)
