import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from backend.services.analysis import (
    EXPENSE_CATEGORIES,
    analyze_transactions,
    categorize_transaction,
    format_analysis_for_ai,
)

# --- Testes de Categorização ---

def test_categorize_ifood():
    assert categorize_transaction("IFOOD PEDIDO 12345") == "alimentacao"

def test_categorize_netflix():
    assert categorize_transaction("NETFLIX.COM") == "lazer"

def test_categorize_aluguel():
    assert categorize_transaction("ALUGUEL APARTAMENTO") == "moradia"

def test_categorize_uber():
    assert categorize_transaction("UBER TRIP São Paulo") == "transporte"

def test_categorize_farmacia():
    assert categorize_transaction("COMPRA DROGARIA SAO PAULO") == "saude"

def test_categorize_escola():
    assert categorize_transaction("MENSALIDADE ESCOLA") == "educacao"

def test_categorize_spotify():
    assert categorize_transaction("SPOTIFY PREMIUM") == "lazer"

def test_categorize_pix():
    assert categorize_transaction("PIX ENVIADO João") == "transferencias"

def test_categorize_tesouro():
    assert categorize_transaction("TESOURO DIRETO") == "investimentos"

def test_categorize_pet():
    assert categorize_transaction("PET LOVE Ração") == "pets"

def test_categorize_unknown():
    assert categorize_transaction("XYZXYZ ABCDEF") == "outros"

def test_categorize_case_insensitive():
    assert categorize_transaction("ifood") == "alimentacao"
    assert categorize_transaction("iFood") == "alimentacao"
    assert categorize_transaction("IFOOD") == "alimentacao"

def test_categorize_empty():
    assert categorize_transaction("") == "outros"

def test_all_categories_have_keywords():
    for cat, keywords in EXPENSE_CATEGORIES.items():
        assert len(keywords) > 0, f"Categoria '{cat}' não tem keywords"


# --- Testes de Análise ---

def test_analyze_empty_transactions():
    result = analyze_transactions([])
    assert result["total_income"] == 0
    assert result["total_expenses"] == 0
    assert result["balance"] == 0
    assert result["categories"] == {}
    assert result["savings_rate"] == 0
    assert result["months_analyzed"] == 0

def test_analyze_income_only():
    transactions = [
        {"amount": 5000, "date": "2026-01-15", "description": "SALARIO"},
    ]
    result = analyze_transactions(transactions)
    assert result["total_income"] == 5000
    assert result["total_expenses"] == 0
    assert result["balance"] == 5000
    assert result["savings_rate"] == 100.0

def test_analyze_expenses_only():
    transactions = [
        {"amount": -100, "date": "2026-01-15", "description": "ALUGUEL"},
        {"amount": -50, "date": "2026-01-20", "description": "IFOOD"},
    ]
    result = analyze_transactions(transactions)
    assert result["total_income"] == 0
    assert result["total_expenses"] == 150
    assert result["balance"] == -150
    assert result["savings_rate"] == 0

def test_analyze_mixed_transactions():
    transactions = [
        {"amount": 5000, "date": "2026-01-15", "description": "SALARIO"},
        {"amount": -1200, "date": "2026-01-05", "description": "ALUGUEL"},
        {"amount": -200, "date": "2026-01-10", "description": "IFOOD"},
        {"amount": -100, "date": "2026-01-12", "description": "UBER"},
    ]
    result = analyze_transactions(transactions)
    assert result["total_income"] == 5000
    assert result["total_expenses"] == 1500
    assert result["balance"] == 3500
    assert result["savings_rate"] == 70.0
    assert result["suggested_investment"] == 2800.0  # 80% of (5000-1500)/1 month

def test_analyze_categories():
    transactions = [
        {"amount": -1200, "date": "2026-01-05", "description": "ALUGUEL"},
        {"amount": -200, "date": "2026-01-10", "description": "IFOOD"},
        {"amount": -100, "date": "2026-01-12", "description": "UBER"},
    ]
    result = analyze_transactions(transactions)
    assert "moradia" in result["categories"]
    assert "alimentacao" in result["categories"]
    assert "transporte" in result["categories"]
    assert result["categories"]["moradia"]["total"] == 1200
    assert result["categories"]["moradia"]["count"] == 1

def test_analyze_recurring_expenses():
    transactions = [
        {"amount": -1200, "date": "2026-01-05", "description": "ALUGUEL"},
        {"amount": -1200, "date": "2026-02-05", "description": "ALUGUEL"},
        {"amount": -1200, "date": "2026-03-05", "description": "ALUGUEL"},
    ]
    result = analyze_transactions(transactions)
    assert len(result["recurring_expenses"]) >= 1
    aluguel = [r for r in result["recurring_expenses"] if "ALUGUEL" in r["description"]]
    assert len(aluguel) == 1
    assert aluguel[0]["count"] == 3
    assert aluguel[0]["avg_amount"] == 1200

def test_analyze_monthly_comparison():
    transactions = [
        {"amount": 5000, "date": "2026-01-15", "description": "SALARIO"},
        {"amount": -2000, "date": "2026-01-10", "description": "GASTOS"},
        {"amount": 5500, "date": "2026-02-15", "description": "SALARIO"},
        {"amount": -2200, "date": "2026-02-10", "description": "GASTOS"},
    ]
    result = analyze_transactions(transactions)
    assert len(result["monthly_comparison"]) == 1
    comp = result["monthly_comparison"][0]
    assert comp["month"] == "2026-02"
    assert comp["income"] == 5500
    assert comp["expenses"] == 2200
    assert comp["income_change_pct"] == 10.0

def test_analyze_savings_rate_clamped():
    transactions = [
        {"amount": 5000, "date": "2026-01-15", "description": "SALARIO"},
        {"amount": -1000, "date": "2026-01-10", "description": "GASTOS"},
        {"amount": 2000, "date": "2026-01-20", "description": "BONUS"},
    ]
    result = analyze_transactions(transactions)
    assert 0 <= result["savings_rate"] <= 100

def test_analyze_top_expenses():
    transactions = [
        {"amount": -100, "date": "2026-01-10", "description": "IFOOD"},
        {"amount": -5000, "date": "2026-01-15", "description": "COMPUTADOR"},
        {"amount": -200, "date": "2026-01-20", "description": "UBER"},
    ]
    result = analyze_transactions(transactions)
    assert len(result["top_expenses"]) == 3
    assert result["top_expenses"][0]["description"] == "COMPUTADOR"
    assert result["top_expenses"][0]["amount"] == -5000

def test_analyze_alerts():
    transactions = [
        {"amount": 5000, "date": "2026-01-15", "description": "SALARIO"},
        {"amount": -1000, "date": "2026-01-10", "description": "GASTOS"},
        {"amount": -5000, "date": "2026-02-10", "description": "GASTO ALTO"},
    ]
    result = analyze_transactions(transactions)
    assert len(result["alerts"]) > 0

def test_analyze_months_analyzed():
    transactions = [
        {"amount": 100, "date": "2026-01-15", "description": "SALARIO"},
        {"amount": 100, "date": "2026-02-15", "description": "SALARIO"},
        {"amount": 100, "date": "2026-03-15", "description": "SALARIO"},
    ]
    result = analyze_transactions(transactions)
    assert result["months_analyzed"] == 3


# --- Testes de Formatação para IA ---

def test_format_analysis_for_ai():
    analysis = {
        "total_income": 5000,
        "total_expenses": 2000,
        "balance": 3000,
        "savings_rate": 60.0,
        "months_analyzed": 1,
        "avg_monthly_income": 5000,
        "avg_monthly_expenses": 2000,
        "categories": {"alimentacao": {"count": 5, "total": 500}},
        "top_expenses": [{"description": "IFOOD", "amount": -100}],
        "recurring_expenses": [],
        "monthly_comparison": [],
        "alerts": [],
        "suggested_investment": 2400,
    }
    result = format_analysis_for_ai(analysis, {})
    assert "Receitas totais" in result
    assert "R$ 5,000.00" in result
    assert "alimentacao" in result

def test_format_analysis_empty():
    result = format_analysis_for_ai({
        "total_income": 0,
        "total_expenses": 0,
        "balance": 0,
        "savings_rate": 0,
        "months_analyzed": 0,
        "avg_monthly_income": 0,
        "avg_monthly_expenses": 0,
        "categories": {},
        "top_expenses": [],
        "recurring_expenses": [],
        "monthly_comparison": [],
        "alerts": [],
        "suggested_investment": 0,
    }, {})
    assert "Receitas totais" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
