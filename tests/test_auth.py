import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from backend.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    validate_email,
    validate_password,
    verify_password,
    verify_token,
)


def test_create_access_token():
    token = create_access_token({"sub": "1"})
    assert isinstance(token, str)
    assert len(token) > 20

def test_verify_valid_token():
    token = create_access_token({"sub": "42", "email": "test@test.com"})
    payload = verify_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "test@test.com"

def test_verify_invalid_token():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        verify_token("invalid.token.here")
    assert exc_info.value.status_code == 401

def test_token_expiration():
    from datetime import timedelta
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        verify_token(token)
    assert exc_info.value.status_code == 401

def test_validate_email_valid():
    assert validate_email("user@example.com") is True
    assert validate_email("name.last@domain.co.uk") is True
    assert validate_email("user+tag@email.com") is True

def test_validate_email_invalid():
    assert validate_email("invalid") is False
    assert validate_email("@domain.com") is False
    assert validate_email("user@") is False
    assert validate_email("user@domain") is False
    assert validate_email("") is False

def test_secret_key_from_env():
    assert SECRET_KEY is not None
    assert len(SECRET_KEY) > 0

def test_algorithm_is_hs256():
    assert ALGORITHM == "HS256"

def test_token_contains_exp():
    token = create_access_token({"sub": "1"})
    import base64
    import json
    parts = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    assert "exp" in payload

def test_multiple_tokens_different():
    t1 = create_access_token({"sub": "1"})
    t2 = create_access_token({"sub": "2"})
    assert t1 != t2


# --- Password Hashing Tests ---

def test_hash_password():
    hashed = hash_password("Minha Senha 123")
    assert hashed != "Minha Senha 123"
    assert len(hashed) > 20

def test_verify_password_correct():
    hashed = hash_password("Minha Senha 123")
    assert verify_password("Minha Senha 123", hashed) is True

def test_verify_password_wrong():
    hashed = hash_password("Minha Senha 123")
    assert verify_password("Senha Errada 456", hashed) is False

def test_hash_different_each_time():
    h1 = hash_password("Same Password 123")
    h2 = hash_password("Same Password 123")
    assert h1 != h2
    assert verify_password("Same Password 123", h1) is True
    assert verify_password("Same Password 123", h2) is True


# --- Password Validation Tests ---

def test_validate_password_valid():
    errors = validate_password("Minha Senha 1")
    assert errors == []

def test_validate_password_too_short():
    errors = validate_password("Ab1")
    assert len(errors) > 0
    assert any("mínimo" in e for e in errors)

def test_validate_password_no_uppercase():
    errors = validate_password("minha senha 123")
    assert len(errors) > 0
    assert any("maiúscula" in e for e in errors)

def test_validate_password_no_lowercase():
    errors = validate_password("MINHA SENHA 123")
    assert len(errors) > 0
    assert any("minúscula" in e for e in errors)

def test_validate_password_no_digit():
    errors = validate_password("Minha Senha")
    assert len(errors) > 0
    assert any("número" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
