import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

if not PLAYWRIGHT_AVAILABLE:
    pytest.skip("playwright não está instalado", allow_module_level=True)

BASE_URL = "http://localhost:8501"
API_URL = "http://localhost:8000"
E2E_MARK = pytest.mark.e2e


def _is_backend_available():
    import requests
    try:
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _is_frontend_available():
    import requests
    try:
        r = requests.get(BASE_URL, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


BACKEND_AVAILABLE = _is_backend_available()
FRONTEND_AVAILABLE = _is_frontend_available()

pytestmark = [
    E2E_MARK,
    pytest.mark.skipif(
        not BACKEND_AVAILABLE,
        reason="Backend não está rodando em http://localhost:8000",
    ),
    pytest.mark.skipif(
        not FRONTEND_AVAILABLE,
        reason="Frontend (Streamlit) não está rodando em http://localhost:8501",
    ),
]


def _unique_email():
    return f"e2e_{uuid.uuid4().hex[:8]}@investia.test"


def _valid_password():
    return "E2eSenhaTeste1"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    pg = context.new_page()
    yield pg
    pg.close()
    context.close()


@E2E_MARK
def test_app_loads_login_page(page):
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    content = page.content()
    assert "Entrar" in content or "InvestIA" in content


@E2E_MARK
def test_register_flow(page):
    email = _unique_email()
    password = _valid_password()

    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    create_btn = page.locator("text=Criar conta").first
    if create_btn.is_visible():
        create_btn.click()
        page.wait_for_timeout(2000)

    page.wait_for_selector('input[aria-label="Nome"]', timeout=10000)
    page.fill('input[aria-label="Nome"]', "E2E Test User")
    page.fill('input[aria-label="Email"]', email)

    password_inputs = page.locator('input[type="password"]')
    if password_inputs.count() >= 2:
        password_inputs.nth(0).fill(password)
        password_inputs.nth(1).fill(password)

    page.locator('button:has-text("Criar conta")').last.click()
    page.wait_for_timeout(5000)

    content = page.content()
    logged_in = (
        "Dashboard" in content
        or "Upload" in content
        or "Navegação" in content
    )
    assert logged_in, "Expected to be redirected to dashboard after register"


@E2E_MARK
def test_login_flow(page):
    email = _unique_email()
    password = _valid_password()

    import requests
    requests.post(f"{API_URL}/api/auth/register", json={
        "email": email,
        "name": "Login E2E",
        "password": password,
    })

    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    page.wait_for_selector('input[aria-label="Email"]', timeout=10000)
    page.fill('input[aria-label="Email"]', email)
    page.locator('input[type="password"]').first.fill(password)

    page.locator('button:has-text("Entrar")').first.click()
    page.wait_for_timeout(5000)

    content = page.content()
    logged_in = (
        "Dashboard" in content
        or "Upload" in content
        or "Navegação" in content
    )
    assert logged_in, "Expected to be redirected to dashboard after login"


@E2E_MARK
def test_login_wrong_password_shows_error(page):
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    page.wait_for_selector('input[aria-label="Email"]', timeout=10000)
    page.fill('input[aria-label="Email"]', "anyone@email.com")
    page.locator('input[type="password"]').first.fill("WrongPass1")

    page.locator('button:has-text("Entrar")').first.click()
    page.wait_for_timeout(3000)

    content = page.content()
    has_error = "incorretos" in content or "erro" in content.lower() or "inválido" in content
    assert has_error, "Expected error message for wrong password"


@E2E_MARK
def test_sidebar_navigation(page):
    email = _unique_email()
    password = _valid_password()

    import requests
    requests.post(f"{API_URL}/api/auth/register", json={
        "email": email,
        "name": "Nav E2E",
        "password": password,
    })

    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    page.fill('input[aria-label="Email"]', email)
    page.locator('input[type="password"]').first.fill(password)
    page.locator('button:has-text("Entrar")').first.click()
    page.wait_for_timeout(5000)

    content = page.content()
    has_sidebar = "Dashboard" in content
    assert has_sidebar, "Expected sidebar navigation after login"

    nav_items = ["Upload", "Análise", "Chat", "Relatórios"]
    for item in nav_items:
        assert item in content, f"Expected nav item '{item}' in sidebar"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
