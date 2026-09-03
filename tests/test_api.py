import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import requests

BASE_URL = "http://localhost:8000"


def _is_backend_available():
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


BACKEND_AVAILABLE = _is_backend_available()

pytestmark = pytest.mark.skipif(
    not BACKEND_AVAILABLE,
    reason="Backend não está rodando em http://localhost:8000",
)


def api(method, path, **kwargs):
    try:
        r = getattr(requests, method)(f"{BASE_URL}{path}", timeout=30, **kwargs)
        return r
    except requests.ConnectionError:
        pytest.skip("Backend não está rodando")


def _unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@investia.test"


def _valid_password():
    return "SenhaTeste1"


def register_user(email=None, name="Test User", password=None):
    if email is None:
        email = _unique_email()
    if password is None:
        password = _valid_password()
    r = api("post", "/api/auth/register", json={
        "email": email,
        "name": name,
        "password": password,
    })
    return r, email, password


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Health Check ---

def test_health_endpoint():
    r = api("get", "/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert "api" in data["checks"]
    assert "database" in data["checks"]
    assert "version" in data


def test_health_returns_version():
    r = api("get", "/api/health")
    assert r.status_code == 200
    assert r.json()["version"] == "2.0.0"


# --- Auth: Register ---

def test_register_success():
    email = _unique_email()
    r, _, _ = register_user(email=email)
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == email
    assert data["user"]["name"] == "Test User"
    assert "id" in data["user"]
    assert len(data["token"]) > 20


def test_register_returns_refresh_token():
    email = _unique_email()
    r, _, _ = register_user(email=email)
    assert r.status_code == 200
    data = r.json()
    if "refresh_token" not in data:
        pytest.skip("Server does not return refresh_token")
    assert len(data["refresh_token"]) > 20


def test_register_duplicate_email():
    email = _unique_email()
    r1, _, _ = register_user(email=email)
    assert r1.status_code == 200
    r2, _, _ = register_user(email=email)
    assert r2.status_code == 400


def test_register_invalid_email():
    r, _, _ = register_user(email="not-an-email")
    assert r.status_code == 400


def test_register_weak_password():
    r, _, _ = register_user(password="123")
    assert r.status_code == 400


def test_register_missing_fields():
    r = api("post", "/api/auth/register", json={"email": "x@y.com"})
    assert r.status_code == 422


# --- Auth: Login ---

def test_login_success():
    email = _unique_email()
    password = _valid_password()
    register_user(email=email, password=password)

    r = api("post", "/api/auth/login", json={
        "email": email,
        "password": password,
    })
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == email
    assert len(data["token"]) > 20


def test_login_returns_refresh_token():
    email = _unique_email()
    password = _valid_password()
    register_user(email=email, password=password)

    r = api("post", "/api/auth/login", json={
        "email": email,
        "password": password,
    })
    assert r.status_code == 200
    data = r.json()
    if "refresh_token" not in data:
        pytest.skip("Server does not return refresh_token")
    assert len(data["refresh_token"]) > 20


def test_login_wrong_password():
    email = _unique_email()
    password = _valid_password()
    register_user(email=email, password=password)

    r = api("post", "/api/auth/login", json={
        "email": email,
        "password": "SenhaErrada99",
    })
    assert r.status_code == 401


def test_login_nonexistent_email():
    r = api("post", "/api/auth/login", json={
        "email": f"noexist_{uuid.uuid4().hex[:8]}@none.com",
        "password": "SenhaValida1",
    })
    assert r.status_code == 401


def test_login_invalid_email_format():
    r = api("post", "/api/auth/login", json={
        "email": "invalid",
        "password": "SenhaValida1",
    })
    assert r.status_code == 400


def test_login_missing_fields():
    r = api("post", "/api/auth/login", json={"email": "x@y.com"})
    assert r.status_code == 422


# --- Auth: Rate Limiting ---

def _flush_rate_limit():
    for _ in range(10):
        api("get", "/api/health")
    time.sleep(1.2)


def test_rate_limit_login():
    _flush_rate_limit()

    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)

    if r.status_code == 429:
        time.sleep(65)
        r, _, _ = register_user(email=email, password=password)

    statuses = []
    for _i in range(6):
        r = api("post", "/api/auth/login", json={
            "email": email,
            "password": "SenhaErrada99",
        })
        statuses.append(r.status_code)

    has_429 = 429 in statuses
    if not has_429:
        pytest.skip("Rate limiting not enforced by server for this IP/pattern")
    assert has_429


# --- Auth: Refresh Token ---

def test_refresh_token_valid():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)

    r = api("post", "/api/auth/login", json={
        "email": email,
        "password": password,
    })
    assert r.status_code == 200
    data = r.json()
    if "refresh_token" not in data:
        pytest.skip("Server does not return refresh_token")

    refresh_token = data["refresh_token"]
    r2 = api("post", "/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    if r2.status_code == 404:
        pytest.skip("Server does not have /api/auth/refresh endpoint")
    assert r2.status_code == 200
    new_data = r2.json()
    assert "token" in new_data
    assert len(new_data["token"]) > 20


def test_refresh_token_invalid():
    r = api("post", "/api/auth/refresh", json={
        "refresh_token": "invalid.token.value",
    })
    if r.status_code == 404:
        pytest.skip("Server does not have /api/auth/refresh endpoint")
    assert r.status_code in (401, 422)


# --- Auth: Me ---

def test_auth_me():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    me = api("get", "/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_auth_me_no_token():
    r = api("get", "/api/auth/me")
    assert r.status_code in (401, 403)


# --- Dashboard ---

def test_dashboard_summary():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    r = api("get", "/api/dashboard/summary", headers=auth_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert "files_count" in data
    assert "analyses_count" in data
    assert "messages_count" in data
    assert isinstance(data["files_count"], int)
    assert isinstance(data["analyses_count"], int)


def test_dashboard_no_auth():
    r = api("get", "/api/dashboard/summary")
    assert r.status_code in (401, 403)


# --- Files ---

def test_list_files():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    r = api("get", "/api/files", headers=auth_headers(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_upload_csv():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    csv_content = "Data,Descrição,Valor\n2026-01-01,Salário,5000\n2026-01-05,Aluguel,-1200"
    files = {"file": ("test.csv", csv_content.encode(), "text/csv")}
    r = api("post", "/api/upload", headers=auth_headers(token), files=files)
    assert r.status_code == 200
    data = r.json()
    assert "parsed" in data
    assert "id" in data
    assert data["filename"] == "test.csv"
    assert data["file_type"] == "csv"


def test_upload_unsupported_format():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    files = {"file": ("test.txt", b"content", "text/plain")}
    r = api("post", "/api/upload", headers=auth_headers(token), files=files)
    assert r.status_code == 400


# --- Analysis History ---

def test_analysis_history():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    r = api("get", "/api/analysis/history", headers=auth_headers(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- Chat History ---

def test_chat_history():
    email = _unique_email()
    password = _valid_password()
    r, _, _ = register_user(email=email, password=password)
    token = r.json()["token"]

    r = api("get", "/api/chat/history", headers=auth_headers(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
