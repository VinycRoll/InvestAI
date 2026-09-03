import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app, get_gemini
from backend.services import gemini
from backend.services.analysis import (
    analyze_transactions,
    categorize_transaction,
    format_analysis_for_ai,
)

# =============================================================================
# 5. Categorização: prevenção de falsos positivos
# =============================================================================

def test_evento_not_casa():
    # "vento" era keyword de casa e casava "EVENTO"
    assert categorize_transaction("EVENTO FESTA JUNHO") == "outros"
    assert categorize_transaction("EVENTO CORPORATIVO") == "outros"


def test_ventilador_still_casa():
    assert categorize_transaction("VENTILADOR ELETRO") == "casa"


def test_nubank_purchase_not_investment():
    # "nubank" era keyword de investimentos e casava qualquer compra Nubank
    assert categorize_transaction("NUBANK *IFOOD") == "alimentacao"
    assert categorize_transaction("NUBANK PAGAMENTO") == "outros"


def test_terra_corretora_only_investment():
    assert categorize_transaction("COMPRA TERRA CORRETORA") == "investimentos"
    assert categorize_transaction("TERRA ARROZ") == "outros"
    assert categorize_transaction("FERTILIZANTE TERRA") == "outros"


def test_extra_requires_supermercado_keyword():
    assert categorize_transaction("DESPESA EXTRA") == "outros"
    assert categorize_transaction("EMPRESTIMO EXTRA") == "outros"


def test_ricardo_eletro_no_longer_investment():
    assert categorize_transaction("RICARDO ELETRO") == "outros"


def test_short_keywords_word_boundary():
    # "99" (transporte) e "oi" (moradia) não casam dentro de outras palavras
    assert categorize_transaction("99 TAXI") == "transporte"
    assert categorize_transaction("299 MUSICA") == "outros"
    assert categorize_transaction("99PEDIDO") == "outros"
    assert categorize_transaction("NOTA 109") == "outros"
    assert categorize_transaction("OI TELECOM") == "moradia"
    assert categorize_transaction("AVO BENEDITA") == "outros"


def test_accented_variants_categorized():
    assert categorize_transaction("AQUI AQUI") == "outros"
    assert categorize_transaction("CAFETERIA BOM SABOR") == "outros"
    assert categorize_transaction("IFOOD") == "alimentacao"


# =============================================================================
# 6/7. Matemática financeira e investimento sugerido (com disclaimer)
# =============================================================================

def _txns():
    return [
        {"amount": 5000.0, "date": "2026-01-15", "description": "SALARIO"},
        {"amount": -1200.0, "date": "2026-01-05", "description": "ALUGUEL"},
        {"amount": -300.0, "date": "2026-01-10", "description": "IFOOD"},
    ]


def test_balance_is_income_minus_expenses():
    a = analyze_transactions(_txns())
    assert a["total_income"] == 5000.0
    assert a["total_expenses"] == 1500.0
    assert a["balance"] == 3500.0
    assert a["balance"] == a["total_income"] - a["total_expenses"]


def test_savings_rate_math():
    a = analyze_transactions(_txns())
    assert a["savings_rate"] == 70.0  # 3500 / 5000 * 100


def test_savings_rate_zero_income_no_error():
    a = analyze_transactions([{"amount": -100.0, "date": "2026-01-01", "description": "IFOOD"}])
    assert a["savings_rate"] == 0
    assert a["balance"] == -100.0


def test_suggested_investment_is_estimate():
    a = analyze_transactions(_txns())
    assert a["suggested_investment"] == round(3500.0 * 0.8, 2)
    note = a["suggested_investment_note"]
    assert "Estimativa" in note
    assert "Não é uma recomendação" in note
    assert "Consulte um profissional" in note


def test_format_analysis_for_ai_includes_estimate_note():
    a = analyze_transactions(_txns())
    text = format_analysis_for_ai(a, _txns())
    assert "estimativa de capacidade" in text


# =============================================================================
# 8/9/10. GeminiService: URL, timeout, retries, truncation, prompt injection
# =============================================================================

class FakeResponse:
    def __init__(self, status_code, json_data=None, raises=None):
        self.status_code = status_code
        self._json = json_data
        self._raises = raises

    def json(self):
        if self._raises:
            raise self._raises
        if self._json is None:
            raise ValueError("no json body")
        return self._json


class FakeClient:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []
        self.is_closed = False

    async def post(self, url, params=None, json=None, headers=None):
        self.calls.append({"url": url, "params": params, "json": json, "headers": headers})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self):
        self.is_closed = True


def _success_response(text="resposta do modelo"):
    return FakeResponse(200, json_data={
        "candidates": [{"content": {"parts": [{"text": text}]}}]
    })


def _capture_body(fake_service, captured):
    async def fake_post(body):
        captured.append(body)
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
    fake_service._post_with_retry = fake_post


def test_gemini_custom_url_and_header(monkeypatch):
    fake = FakeClient([_success_response()])
    monkeypatch.setattr(gemini, "_get_client", lambda: fake)
    service = gemini.GeminiService("segredo123", url="https://gemini.custom.example/v1/render")
    import asyncio
    asyncio.run(service.chat([{"role": "user", "content": "oi"}]))
    call = fake.calls[0]
    assert call["url"] == "https://gemini.custom.example/v1/render"
    assert call["headers"]["x-goog-api-key"] == "segredo123"
    assert call["json"]["systemInstruction"]["parts"][0]["text"]


def test_gemini_retries_on_500_then_succeeds(monkeypatch):
    monkeypatch.setattr(gemini, "GEMINI_RETRIES", 2)
    monkeypatch.setattr(gemini, "GEMINI_RETRY_DELAY", 0.0)
    fake = FakeClient([
        FakeResponse(500, json_data={"error": {"message": "internal"}}),
        FakeResponse(500, json_data={"error": {"message": "internal"}}),
        _success_response(),
    ])
    monkeypatch.setattr(gemini, "_get_client", lambda: fake)
    service = gemini.GeminiService("k")
    import asyncio
    text = asyncio.run(service.chat([{"role": "user", "content": "oi"}]))
    assert text == "resposta do modelo"
    assert len(fake.calls) == 3


def test_gemini_raises_after_retries_exhausted(monkeypatch):
    monkeypatch.setattr(gemini, "GEMINI_RETRIES", 1)
    monkeypatch.setattr(gemini, "GEMINI_RETRY_DELAY", 0.0)
    fake = FakeClient([
        FakeResponse(500, json_data={"error": {"message": "boom"}}),
        FakeResponse(500, json_data={"error": {"message": "boom"}}),
        FakeResponse(500, json_data={"error": {"message": "boom"}}),
    ])
    monkeypatch.setattr(gemini, "_get_client", lambda: fake)
    service = gemini.GeminiService("k")
    import asyncio
    with pytest.raises(gemini.GeminiAPIError):
        asyncio.run(service.chat([{"role": "user", "content": "oi"}]))


def test_gemini_retries_on_timeout(monkeypatch):
    monkeypatch.setattr(gemini, "GEMINI_RETRIES", 1)
    monkeypatch.setattr(gemini, "GEMINI_RETRY_DELAY", 0.0)
    import httpx
    fake = FakeClient([
        httpx.TimeoutException("timeout"),
        _success_response(),
    ])
    monkeypatch.setattr(gemini, "_get_client", lambda: fake)
    service = gemini.GeminiService("k")
    import asyncio
    asyncio.run(service.chat([{"role": "user", "content": "oi"}]))
    assert len(fake.calls) == 2


def test_gemini_truncates_large_context(monkeypatch):
    monkeypatch.setattr(gemini, "GEMINI_RETRIES", 0)
    captured = []
    fake = FakeClient([_success_response()])
    monkeypatch.setattr(gemini, "_get_client", lambda: fake)
    service = gemini.GeminiService("k")
    _capture_body(service, captured)
    import asyncio
    asyncio.run(service.chat([{"role": "user", "content": "x" * (gemini.GEMINI_MAX_CONTEXT_LENGTH + 500)}]))
    sent = captured[0]["contents"][0]["parts"][0]["text"]
    assert sent.endswith("[contexto truncado por limite de tamanho]")
    assert len(sent) < gemini.GEMINI_MAX_CONTEXT_LENGTH


def test_gemini_system_prompt_guards_against_injection():
    assert "NÃO CONFIÁVEIS" in gemini.SYSTEM_PROMPT
    assert "interpretados como instruções" in gemini.SYSTEM_PROMPT
    assert "instrução embutida" in gemini.SYSTEM_PROMPT


def test_investment_recommendation_stays_educational():
    captured = []
    service = gemini.GeminiService("k")
    _capture_body(service, captured)
    import asyncio
    asyncio.run(service.generate_investment_recommendation("conservador", 1000.0, ["alimentacao", "moradia"]))
    prompt = captured[0]["contents"][0]["parts"][0]["text"]
    assert "ESTIMATIVA" in prompt
    assert "não uma recomendação financeira personalizada" in prompt
    assert "Não invente produtos financeiros" in prompt
    assert "disclaimer" in prompt


def test_aclose_client_closes_global(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(gemini, "_client", fake)
    import asyncio
    asyncio.run(gemini.aclose_client())
    assert fake.is_closed is True


# =============================================================================
# API: paginação, upload vazio, formato de export, learn_categories
# (TestClient offline com banco temporário e Gemini simulado)
# =============================================================================

_TMP_DB = os.path.join(tempfile.gettempdir(), f"investia_fase2_{uuid.uuid4().hex}.db")
_engine = create_engine(f"sqlite:///{_TMP_DB}", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=_engine)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _test_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


class _FakeGemini:
    async def chat(self, messages, system_prompt=None):
        return "resposta simulada do modelo"

    async def generate_investment_recommendation(self, profile, amount, categories):
        return "recomendação educacional simulada"


app.dependency_overrides[get_db] = _test_db
app.dependency_overrides[get_gemini] = lambda: _FakeGemini()

_client_ctx = TestClient(app)


def _registered_headers():
    email = f"fase2_{uuid.uuid4().hex[:8]}@investia.test"
    resp = _client_ctx.post("/api/auth/register", json={
        "email": email, "name": "Fase2", "password": "SenhaTeste1",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_csv(headers, name="extrato.csv", body=b"data,descricao,valor\n2026-01-01,pix,-10,50\n"):
    return _client_ctx.post(
        "/api/upload",
        headers=headers,
        files={"file": (name, body, "text/csv")},
    )


def test_empty_file_upload_rejected():
    headers = _registered_headers()
    r = _client_ctx.post("/api/upload", headers=headers,
                         files={"file": ("vazio.csv", b"", "text/csv")})
    assert r.status_code == 400
    assert "vazio" in r.json()["detail"].lower()


def test_export_invalid_format_rejected():
    headers = _registered_headers()
    r = _client_ctx.post("/api/reports/export", headers=headers,
                         json={"analysis_id": 1, "format": "xml"})
    assert r.status_code == 400
    assert "não suportado" in r.json()["detail"].lower()


def test_learn_categories_short_words_ignored():
    headers = _registered_headers()
    r = _client_ctx.post("/api/categories/learn", headers=headers,
                         json={"assignments": [{"description": "ab", "category": "teste"}]})
    assert r.status_code == 200


def test_files_default_returns_plain_list_backward_compat():
    headers = _registered_headers()
    assert _upload_csv(headers).status_code == 200
    r = _client_ctx.get("/api/files", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert all("id" in f and "filename" in f for f in body)
    assert len(body) == 1


def test_files_pagination_shape_and_behavior():
    headers = _registered_headers()
    csv_body = "data,descricao,valor\n2026-01-01,pix,-10,50\n"
    for i in range(3):
        r = _upload_csv(headers, name=f"f{i}.csv", body=csv_body.encode("latin-1"))
        assert r.status_code == 200, r.text
    r = _client_ctx.get("/api/files?page=1&page_size=2", headers=headers)
    body = r.json()
    assert set(body) == {"items", "total", "page", "page_size"}
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    r2 = _client_ctx.get("/api/files?page=2&page_size=2", headers=headers)
    assert len(r2.json()["items"]) == 1
    assert r2.json()["total"] == 3


def test_files_pagination_clamps_page_size():
    headers = _registered_headers()
    r = _client_ctx.get("/api/files?page=1&page_size=500", headers=headers)
    assert r.json()["page_size"] == 200


def test_chat_history_default_returns_plain_list():
    headers = _registered_headers()
    r = _client_ctx.get("/api/chat/history", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
