"""Comprehensive parser tests for CSV, PDF, and shared utilities.

Covers: encodings, delimiters, column detection, dual credit/debit,
multi-line PDF extraction, edge cases, and regression tests for the
"Nenhuma transação encontrada" failure mode.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.parsers.utils import (
    is_amount_column,
    is_credit_column,
    is_date_column,
    is_debit_column,
    is_desc_column,
    normalize_text,
    parse_date,
    parse_money,
)
from backend.parsers.excel_parser import (
    _extract_transactions_from_rows,
    parse_csv,
    parse_excel,
)
from backend.parsers.pdf_parser import (
    extract_transactions_from_text,
    parse_amount,
    parse_pdf,
)

# ===========================================================================
# parse_money
# ===========================================================================

class TestParseMoney:
    def test_brazilian_basic(self):
        assert parse_money("1.234,56") == 1234.56

    def test_brazilian_negative(self):
        assert parse_money("-1.234,56") == -1234.56

    def test_brazilian_negative_no_sign_space(self):
        assert parse_money("- 1.234,56") == -1234.56

    def test_parentheses(self):
        assert parse_money("(1.234,56)") == -1234.56

    def test_parentheses_small(self):
        assert parse_money("(50,00)") == -50.0

    def test_international(self):
        assert parse_money("1,234.56") == 1234.56

    def test_international_negative(self):
        assert parse_money("-1,234.56") == -1234.56

    def test_plain_decimal(self):
        assert parse_money("1234.56") == 1234.56

    def test_plain_comma_decimal(self):
        assert parse_money("1234,56") == 1234.56

    def test_r_prefix(self):
        assert parse_money("R$ 1.234,56") == 1234.56

    def test_r_prefix_negative(self):
        assert parse_money("-R$ 1.234,56") == -1234.56

    def test_r_negative_space(self):
        assert parse_money("R$ -1.234,56") == -1234.56

    def test_r_with_spaces(self):
        assert parse_money("R$   1.234,56") == 1234.56

    def test_zero_value(self):
        assert parse_money("0,00") == 0.0

    def test_zero_international(self):
        assert parse_money("0.00") == 0.0

    def test_small_value(self):
        assert parse_money("0,50") == 0.5

    def test_integer_value(self):
        # "1.234" with no decimals — ambiguous, but parse_money should handle
        result = parse_money("1.234")
        assert result is not None

    def test_empty_string(self):
        assert parse_money("") is None

    def test_none(self):
        assert parse_money(None) is None

    def test_non_numeric(self):
        assert parse_money("abc") is None

    def test_integer_input(self):
        assert parse_money(100) == 100.0

    def test_float_input(self):
        assert parse_money(1234.56) == 1234.56

    def test_large_value(self):
        assert parse_money("1.234.567,89") == 1234567.89

    def test_spaces_in_number(self):
        assert parse_money("1 234,56") == 1234.56


# ===========================================================================
# parse_date
# ===========================================================================

class TestParseDate:
    def test_dd_mm_yyyy(self):
        assert parse_date("01/09/2026") == "2026-09-01"

    def test_dd_mm_yyyy_dash(self):
        assert parse_date("01-09-2026") == "2026-09-01"

    def test_yyyy_mm_dd(self):
        assert parse_date("2026-09-01") == "2026-09-01"

    def test_dd_mm_yy(self):
        assert parse_date("01/09/26") == "2026-09-01"

    def test_dot_format(self):
        assert parse_date("01.09.2026") == "2026-09-01"

    def test_dot_format_short(self):
        assert parse_date("01.09.26") == "2026-09-01"

    def test_empty(self):
        assert parse_date("") is None

    def test_none(self):
        assert parse_date(None) is None

    def test_embedded_date(self):
        assert parse_date("Lançamento em 01/09/2026 da conta") == "2026-09-01"

    def test_invalid(self):
        assert parse_date("abc") is None

    def test_pt_month_jul(self):
        assert parse_date("31 JUL 2026") == "2026-07-31"

    def test_pt_month_ago(self):
        assert parse_date("01 AGO 2026") == "2026-08-01"

    def test_pt_month_all(self):
        expected = [
            ("01 JAN 2026", "2026-01-01"),
            ("15 FEV 2026", "2026-02-15"),
            ("10 MAR 2026", "2026-03-10"),
            ("05 ABR 2026", "2026-04-05"),
            ("20 MAI 2026", "2026-05-20"),
            ("12 JUN 2026", "2026-06-12"),
            ("31 JUL 2026", "2026-07-31"),
            ("01 AGO 2026", "2026-08-01"),
            ("15 SET 2026", "2026-09-15"),
            ("31 OUT 2026", "2026-10-31"),
            ("10 NOV 2026", "2026-11-10"),
            ("25 DEZ 2026", "2026-12-25"),
        ]
        for date_str, expected_iso in expected:
            assert parse_date(date_str) == expected_iso, f"Failed for {date_str}"

    def test_pt_month_case_insensitive(self):
        assert parse_date("31 jul 2026") == "2026-07-31"
        assert parse_date("01 Ago 2026") == "2026-08-01"

    def test_pt_month_embedded(self):
        assert parse_date("Movimentações 01 AGO 2026 Total") == "2026-08-01"


# ===========================================================================
# normalize_text
# ===========================================================================

class TestNormalizeText:
    def test_basic(self):
        assert normalize_text("  hello  world  ") == "hello world"

    def test_unicode(self):
        assert normalize_text("café") == "café"

    def test_empty(self):
        assert normalize_text("") == ""

    def test_none(self):
        assert normalize_text(None) == ""


# ===========================================================================
# Column detection helpers
# ===========================================================================

class TestColumnDetection:
    def test_is_date_column_keyword(self):
        assert is_date_column("Data", []) is True

    def test_is_date_column_samples(self):
        vals = ["01/09/2026", "02/09/2026", "03/09/2026"]
        assert is_date_column("col", vals) is True

    def test_is_amount_column_keyword(self):
        assert is_amount_column("Valor", []) is True

    def test_is_amount_column_samples(self):
        vals = ["1.234,56", "500,00", "25,90"]
        assert is_amount_column("col", vals) is True

    def test_is_amount_column_non_amount(self):
        assert is_amount_column("Codigo", ["123", "456"]) is False

    def test_is_credit_column(self):
        assert is_credit_column("Crédito") is True
        assert is_credit_column("credito") is True
        assert is_credit_column("Credit") is True

    def test_is_debit_column(self):
        assert is_debit_column("Débito") is True
        assert is_debit_column("debito") is True
        assert is_debit_column("Debit") is True

    def test_is_desc_column_keyword(self):
        assert is_desc_column("Descrição", []) is True

    def test_is_desc_column_samples(self):
        vals = ["PIX ENVIADO", "ALUGUEL", "SALARIO"]
        assert is_desc_column("col", vals) is True


# ===========================================================================
# CSV parser
# ===========================================================================

class TestCSVParsing:
    def test_semicolon_delimiter(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;ALUGUEL;-1.234,56\n05/01/2026;SALARIO;5.000,00\n"
        result = parse_csv(csv_data.encode("utf-8"), "test.csv")
        assert len(result["transactions"]) == 2
        txn = {t["description"]: t for t in result["transactions"]}
        assert txn["ALUGUEL"]["amount"] == -1234.56
        assert txn["SALARIO"]["amount"] == 5000.0
        assert result["total_income"] == 5000.0
        assert result["total_expenses"] == 1234.56

    def test_comma_delimiter(self):
        csv_data = "Data,Descricao,Valor\n01/01/2026,ALUGUEL,-1234.56\n05/01/2026,SALARIO,5000.00\n"
        result = parse_csv(csv_data.encode("utf-8"), "test.csv")
        assert len(result["transactions"]) == 2

    def test_tab_delimiter(self):
        csv_data = "Data\tDescricao\tValor\n01/01/2026\tALUGUEL\t-1234.56\n"
        result = parse_csv(csv_data.encode("utf-8"), "test.csv")
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["amount"] == -1234.56

    def test_latin1_encoding(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Maçã Mercado;-10,50\n"
        result = parse_csv(csv_data.encode("latin-1"), "latin.csv")
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["amount"] == -10.5

    def test_cp1252_encoding(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Loja Allçã;-25,00\n"
        result = parse_csv(csv_data.encode("cp1252"), "cp.csv")
        assert len(result["transactions"]) == 1

    def test_utf8_bom(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Teste;-10,00\n"
        content = b"\xef\xbb\xbf" + csv_data.encode("utf-8")
        result = parse_csv(content, "bom.csv")
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["amount"] == -10.0

    def test_empty_file(self):
        result = parse_csv(b"", "empty.csv")
        assert result.get("error") is None
        assert result["transactions"] == []
        assert "vazio" in result["summary"].lower()

    def test_only_header(self):
        result = parse_csv(b"Data,Descricao,Valor\n", "header.csv")
        assert result["transactions"] == []

    def test_no_financial_columns(self):
        result = parse_csv(b"nome;idade\njoao;30\nmaria;25\n", "people.csv")
        assert result["transactions"] == []

    def test_numeric_id_column_ignored(self):
        csv_data = (
            "Data;Codigo;Descricao;Produto;Valor\n"
            "2026-01-01;12345;PIX ENVIADO;AAA;50,00\n"
            "2026-01-02;12346;PIX ENVIADO;BBB;70,00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "id.csv")
        assert len(result["transactions"]) == 2
        for t in result["transactions"]:
            assert t["amount"] in (50.0, 70.0)
            assert t["amount"] not in (12345, 12346)

    def test_dual_credit_debit_columns(self):
        csv_data = (
            "Data;Descrição;Crédito;Débito\n"
            "01/09/2026;Salário;5000,00;\n"
            "02/09/2026;Aluguel;;1500,00\n"
            "03/09/2026;Freelance;800,00;\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "dual.csv")
        assert len(result["transactions"]) == 3
        amounts = {t["description"]: t["amount"] for t in result["transactions"]}
        assert amounts["Salário"] == 5000.0
        assert amounts["Aluguel"] == -1500.0
        assert amounts["Freelance"] == 800.0

    def test_dual_credit_debit_both_populated(self):
        csv_data = (
            "Data;Descrição;Crédito;Débito\n"
            "01/09/2026;Transferência;1000,00;500,00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "dual2.csv")
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["amount"] == 500.0

    def test_negative_parentheses(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Teste;(1.234,56)\n"
        result = parse_csv(csv_data.encode("utf-8"), "paren.csv")
        assert result["transactions"][0]["amount"] == -1234.56

    def test_zero_amount_row_skipped(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Teste;0,00\n02/01/2026;Teste2;10,00\n"
        result = parse_csv(csv_data.encode("utf-8"), "zero.csv")
        # Zero amounts are valid transactions, not silently skipped
        assert len(result["transactions"]) == 2
        amounts = {t["amount"] for t in result["transactions"]}
        assert 0.0 in amounts
        assert 10.0 in amounts

    def test_diagnostics_present(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Teste;10,00\n"
        result = parse_csv(csv_data.encode("utf-8"), "diag.csv")
        assert "_diagnostics" in result
        assert "rows_processed" in result["_diagnostics"]
        assert "transactions_found" in result["_diagnostics"]
        assert "columns_detected" in result["_diagnostics"]

    def test_saldo_not_treated_as_amount(self):
        csv_data = (
            "Data;Descrição;Valor;Saldo\n"
            "01/09/2026;Salário;5000,00;15000,00\n"
            "02/09/2026;Aluguel;-1500,00;13500,00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "saldo.csv")
        assert len(result["transactions"]) == 2
        amounts = {t["amount"] for t in result["transactions"]}
        # Saldo values (15000, 13500) should NOT appear as transaction amounts
        assert 15000.0 not in amounts
        assert 13500.0 not in amounts

    def test_quoted_descriptions(self):
        csv_data = 'Data;Descricao;Valor\n01/01/2026;"PIX,/envio";-10,00\n'
        result = parse_csv(csv_data.encode("utf-8"), "quoted.csv")
        assert len(result["transactions"]) == 1

    def test_malformed_rows(self):
        csv_data = "Data;Descricao;Valor\n01/01/2026;Teste;10,00\nbad_data\n02/01/2026;Ok;20,00\n"
        result = parse_csv(csv_data.encode("utf-8"), "malformed.csv")
        # Malformed rows should be skipped gracefully
        assert len(result["transactions"]) >= 1


# ===========================================================================
# XLSX parser (basic — preserve existing behavior)
# ===========================================================================

class TestXLSXParsing:
    def test_xlsx_basic(self):
        """XLSX test requires openpyxl — create a minimal file."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Data", "Descricao", "Valor"])
        ws.append(["01/01/2026", "ALUGUEL", -1234.56])
        ws.append(["05/01/2026", "SALARIO", 5000.00])

        from io import BytesIO

        buf = BytesIO()
        wb.save(buf)
        wb.close()
        content = buf.getvalue()

        result = parse_excel(content, "test.xlsx")
        assert result["type"] == "XLSX"
        assert len(result["transactions"]) == 2

    def test_xlsx_diagnostics(self):
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Data", "Descricao", "Valor"])
        ws.append(["01/01/2026", "Teste", 100.0])

        from io import BytesIO

        buf = BytesIO()
        wb.save(buf)
        wb.close()

        result = parse_excel(buf.getvalue(), "diag.xlsx")
        assert "_diagnostics" in result


# ===========================================================================
# PDF parser
# ===========================================================================

class TestPDFParsing:
    def test_pdf_amount_parentheses(self):
        assert parse_amount("(1.234,56)") == -1234.56
        assert parse_amount("(50,00)") == -50.0
        assert parse_amount("-1.234,56") == -1234.56
        assert parse_amount("1.234,56") == 1234.56
        assert parse_amount("1234.56") == 1234.56

    def test_pdf_text_single_line(self):
        text = (
            "01.08.2026 (1.234,56) ALUGUEL\n"
            "15.08.2026 500,00 SALARIO\n"
            "20/08/2026 -25,90 MERCADO\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) == 3
        amounts = {t["amount"] for t in txns}
        assert -1234.56 in amounts
        assert 500.0 in amounts
        assert -25.9 in amounts

    def test_pdf_text_multiline(self):
        """Date, description, and amount on separate lines."""
        text = (
            "01/09/2026\n"
            "PIX PAGAMENTO\n"
            "-150,00\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) == 1
        assert txns[0]["amount"] == -150.0
        assert txns[0]["date"] == "2026-09-01"

    def test_pdf_text_multiline_with_description(self):
        text = (
            "02/09/2026\n"
            "TRANSFERENCIA INTERBANCARIA PARA JOAO\n"
            "1500,00\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) == 1
        assert txns[0]["amount"] == 1500.0
        assert "TRANSFERENCIA" in txns[0]["description"]

    def test_pdf_empty(self):
        result = parse_pdf(b"")
        assert isinstance(result["transactions"], list)
        assert result["transactions"] == []

    def test_pdf_diagnostics_present(self):
        result = parse_pdf(b"")
        assert "_diagnostics" in result

    def test_pdf_text_with_header_lines(self):
        """Lines that look like headers should be filtered."""
        text = (
            "Extrato Bancário\n"
            "Data Descrição Valor\n"
            "01/09/2026 ALUGUEL -1500,00\n"
            "02/09/2026 SALARIO 5000,00\n"
            "Saldo Disponível: 3500,00\n"
        )
        txns = extract_transactions_from_text(text)
        amounts = {t["amount"] for t in txns}
        assert -1500.0 in amounts
        assert 5000.0 in amounts

    def test_pdf_deduplication(self):
        """Same transaction appearing twice should be deduplicated."""
        text = (
            "01/09/2026 ALUGUEL -1500,00\n"
            "01/09/2026 ALUGUEL -1500,00\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) == 1


# ===========================================================================
# Regression: "Nenhuma transação encontrada" failure modes
# ===========================================================================

class TestRegressionNoTransactions:
    """Reproduce and verify fixes for the 'Nenhuma transação encontrada' error."""

    def test_csv_with_description_containing_delimiter(self):
        """Quoted CSV with commas inside descriptions."""
        csv_data = 'Data;Descricao;Valor\n01/01/2026;"PIX, envio";-10,00\n'
        result = parse_csv(csv_data.encode("utf-8"), "test.csv")
        assert result["total_transactions"] >= 1

    def test_csv_brazilian_bank_format(self):
        """Typical Brazilian bank CSV export."""
        csv_data = (
            "Data Lançamento;Descrição;Valor\n"
            "01/09/2026;SALARIO EMPRESA;5000,00\n"
            "02/09/2026;ALUGUEL APARTAMENTO;-1800,00\n"
            "03/09/2026;SUPERMERCADO;-250,50\n"
            "04/09/2026;PIX RECEBIDO MARIA;300,00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "bank.csv")
        assert result["total_transactions"] == 4
        assert result["total_income"] == 5300.0

    def test_csv_international_format(self):
        """US-style CSV with commas as thousands and dots as decimal."""
        csv_data = (
            "Date,Description,Amount\n"
            "09/01/2026,SALARY,5000.00\n"
            "09/02/2026,RENT,-1800.00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "us.csv")
        assert result["total_transactions"] == 2

    def test_csv_credit_debit_not_skipped(self):
        """Rows with credit=0 and debit>0 should not be skipped."""
        csv_data = (
            "Data;Descrição;Crédito;Débito\n"
            "01/09/2026;Aluguel;;1500,00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "test.csv")
        assert result["total_transactions"] == 1
        assert result["transactions"][0]["amount"] == -1500.0

    def test_csv_saldo_column_not_used(self):
        """Saldo (balance) column should not be used as transaction amount."""
        csv_data = (
            "Data;Descrição;Valor;Saldo\n"
            "01/09/2026;Salário;5000,00;5000,00\n"
            "02/09/2026;Aluguel;-1500,00;3500,00\n"
        )
        result = parse_csv(csv_data.encode("utf-8"), "test.csv")
        assert result["total_transactions"] == 2
        for t in result["transactions"]:
            assert abs(t["amount"]) < 10000

    def test_pdf_multiline_statement(self):
        """PDF with transactions spanning multiple lines."""
        text = (
            "Extrato Mensal\n"
            "\n"
            "01/09/2026\n"
            "Pagamento de Aluguel\n"
            "-1.800,00\n"
            "\n"
            "02/09/2026\n"
            "Recebimento de Salário\n"
            "5.000,00\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) == 2
        amounts = {t["amount"] for t in txns}
        assert -1800.0 in amounts
        assert 5000.0 in amounts

    def test_pdf_portuguese_month_dates(self):
        """Real PDF structure: DD MMM YYYY dates with Brazilian amounts."""
        text = (
            "31 JUL 2026 Total de entradas + 436,51\n"
            "Transferência recebida pelo Pix 145,00\n"
            "01 AGO 2026 Total de saídas - 84,61\n"
            "Compra no débito CONSORCIO 19,80\n"
            "Compra no débito CASA DOS DOCES 26,94\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) >= 2
        dates = {t["date"] for t in txns}
        assert "2026-07-31" in dates
        assert "2026-08-01" in dates

    def test_pdf_portuguese_month_multiline(self):
        """DD MMM YYYY date on one line, amount on a following line."""
        text = (
            "06 AGO 2026 Total de saídas - 226,94\n"
            "Compra no débito DOM MARIO ALIMENTOS LT 10,00\n"
        )
        txns = extract_transactions_from_text(text)
        assert len(txns) >= 1
        dates = {t["date"] for t in txns}
        assert "2026-08-06" in dates
