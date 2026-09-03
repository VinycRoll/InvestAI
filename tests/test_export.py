import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

from backend.services.export import ExportService

SAMPLE_ANALYSIS = {
    "total_income": 10000,
    "total_expenses": 4500,
    "balance": 5500,
    "savings_rate": 55.0,
    "months_analyzed": 2,
    "avg_monthly_income": 5000,
    "avg_monthly_expenses": 2250,
    "categories": {
        "alimentacao": {"count": 10, "total": 800},
        "moradia": {"count": 1, "total": 1500},
        "transporte": {"count": 5, "total": 300},
    },
    "top_expenses": [
        {"description": "ALUGUEL", "date": "2026-01-05", "amount": -1500},
        {"description": "COMPUTADOR", "date": "2026-01-15", "amount": -800},
    ],
    "recurring_expenses": [
        {"description": "ALUGUEL", "count": 2, "avg_amount": 1500, "total": 3000},
        {"description": "NETFLIX", "count": 2, "avg_amount": 40, "total": 80},
    ],
    "suggested_investment": 2200,
}


# --- HTML ---

def test_generate_html_report():
    html = ExportService.generate_html_report(SAMPLE_ANALYSIS, "Análise completa do mês")
    assert "<html>" in html
    assert "InvestIA" in html
    assert "10,000.00" in html
    assert "4,500.00" in html
    assert "5,500.00" in html

def test_html_with_ai_analysis():
    html = ExportService.generate_html_report(
        SAMPLE_ANALYSIS,
        "## Recomendações\n\n1. Investir em **CDB**\n2. Reduzir aluguel"
    )
    assert "Recomendações" in html
    assert "CDB" in html

def test_html_with_empty_analysis():
    html = ExportService.generate_html_report({})
    assert "<html>" in html
    assert "InvestIA" in html

def test_html_categories():
    html = ExportService.generate_html_report(SAMPLE_ANALYSIS)
    assert "alimentacao" in html.lower() or "Alimentacao" in html
    assert "moradia" in html.lower() or "Moradia" in html

def test_html_top_expenses():
    html = ExportService.generate_html_report(SAMPLE_ANALYSIS)
    assert "ALUGUEL" in html
    assert "COMPUTADOR" in html

def test_html_recurring():
    html = ExportService.generate_html_report(SAMPLE_ANALYSIS)
    assert "ALUGUEL" in html
    assert "NETFLIX" in html

def test_html_investment_suggestion():
    html = ExportService.generate_html_report(SAMPLE_ANALYSIS)
    assert "2,200.00" in html


# --- CSV ---

def test_generate_csv_report():
    csv = ExportService.generate_csv_data(SAMPLE_ANALYSIS)
    assert "Receitas" in csv
    assert "Despesas" in csv
    assert "Saldo" in csv
    assert "10,000.00" in csv

def test_csv_categories():
    csv = ExportService.generate_csv_data(SAMPLE_ANALYSIS)
    assert "alimentacao" in csv.lower() or "alimentacao" in csv
    assert "moradia" in csv.lower() or "moradia" in csv

def test_csv_top_expenses():
    csv = ExportService.generate_csv_data(SAMPLE_ANALYSIS)
    assert "ALUGUEL" in csv
    assert "COMPUTADOR" in csv

def test_csv_recurring():
    csv = ExportService.generate_csv_data(SAMPLE_ANALYSIS)
    assert "ALUGUEL" in csv
    assert "NETFLIX" in csv

def test_csv_with_ai():
    csv = ExportService.generate_csv_data(SAMPLE_ANALYSIS, "Investir em renda fixa")
    assert "Investir em renda fixa" in csv

def test_csv_empty():
    csv = ExportService.generate_csv_data({})
    assert "InvestIA" in csv


# --- JSON ---

def test_generate_json_report():
    result = ExportService.generate_json_report(SAMPLE_ANALYSIS)
    parsed = json.loads(result)
    assert parsed["total_income"] == 10000
    assert parsed["total_expenses"] == 4500
    assert parsed["balance"] == 5500

def test_json_categories():
    result = ExportService.generate_json_report(SAMPLE_ANALYSIS)
    parsed = json.loads(result)
    assert "alimentacao" in parsed["categories"]
    assert parsed["categories"]["alimentacao"]["total"] == 800

def test_json_empty():
    result = ExportService.generate_json_report({})
    parsed = json.loads(result)
    assert parsed == {}

def test_json_with_datetime():
    from datetime import datetime
    result = ExportService.generate_json_report({"date": datetime.now()})
    parsed = json.loads(result)
    assert "date" in parsed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
