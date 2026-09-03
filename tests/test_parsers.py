import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from backend.parsers.excel_parser import _parse_amount, _parse_date, parse_csv
from backend.parsers.ofx_parser import parse_ofx
from backend.parsers.pdf_parser import extract_transactions_from_text, parse_amount, parse_date

# --- CSV: semicolon / encoding / empty / column detection ---

def test_csv_semicolon_delimiter():
    csv_data = "Data;Descricao;Valor\n01/01/2026;ALUGUEL;-1.234,56\n05/01/2026;SALARIO;5.000,00\n"
    result = parse_csv(csv_data.encode("utf-8"), "test.csv")
    assert len(result["transactions"]) == 2
    txn = {t["description"]: t for t in result["transactions"]}
    assert txn["ALUGUEL"]["amount"] == -1234.56
    assert txn["SALARIO"]["amount"] == 5000.0
    assert result["total_income"] == 5000.0
    assert result["total_expenses"] == 1234.56


def test_csv_latin1_encoding():
    csv_data = "Data;Descricao;Valor\n01/01/2026;Maçã Mercado;-10,50\n"
    result = parse_csv(csv_data.encode("latin-1"), "latin.csv")
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["amount"] == -10.5


def test_csv_empty_file():
    result = parse_csv(b"", "empty.csv")
    assert result.get("error") is None
    assert result["transactions"] == []
    assert "vazio" in result["summary"].lower()


def test_csv_only_header_no_data():
    result = parse_csv(b"Data,Descricao,Valor\n", "header.csv")
    assert result["transactions"] == []


def test_csv_malformed_no_columns():
    # Dados sem coluna financeira/descritiva nao devem virar transacoes
    result = parse_csv(b"nome;idade\njoao;30\nmaria;25\n", "people.csv")
    assert result["transactions"] == []


def test_csv_numeric_id_column_ignored():
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


def test_csv_invalid_column_prioritized_by_name():
    csv_data = (
        "Data;Código;Valor\n"
        "2026-01-01;999;10,00\n"
        "2026-01-02;888;20,00\n"
    )
    result = parse_csv(csv_data.encode("utf-8"), "codigo.csv")
    # "Código" must not be treated as the value column
    for t in result["transactions"]:
        assert t["amount"] != 999.0
        assert t["amount"] == 10.0 or t["amount"] == 20.0


def test_csv_amount_column_keyword_priority():
    csv_data = (
        "Data;Numero da Conta;Valor\n"
        "2026-01-01;1234;15,00\n"
        "2026-01-02;5678;25,00\n"
    )
    result = parse_csv(csv_data.encode("utf-8"), "conta.csv")
    for t in result["transactions"]:
        assert t["amount"] == 15.0 or t["amount"] == 25.0


# --- CSV number parsing helpers ---

def test_parse_amount_negative():
    assert _parse_amount("(1.234,56)") == -1234.56
    assert _parse_amount("(50,00)") == -50.0
    assert _parse_amount("-1234,56") == -1234.56
    assert _parse_amount("-1234.56") == -1234.56


def test_parse_amount_positive():
    assert _parse_amount("1.234,56") == 1234.56
    assert _parse_amount("R$ 1.234,56") == 1234.56
    assert _parse_amount("1234.56") == 1234.56


def test_parse_date_formats():
    assert _parse_date("01/08/2026") == "2026-08-01"
    assert _parse_date("2026-08-01") == "2026-08-01"
    assert _parse_date("01-08-2026") == "2026-08-01"


# --- PDF parser ---

def test_pdf_amount_parentheses():
    assert parse_amount("(1.234,56)") == -1234.56
    assert parse_amount("(50,00)") == -50.0
    assert parse_amount("-1.234,56") == -1234.56
    assert parse_amount("1.234,56") == 1234.56
    assert parse_amount("1234.56") == 1234.56


def test_pdf_date_formats():
    assert parse_date("01.08.2026") == "2026-08-01"
    assert parse_date("01/08/2026") == "2026-08-01"
    assert parse_date("01-08-2026") == "2026-08-01"
    assert parse_date("2026-08-01") == "2026-08-01"
    assert parse_date("") is None


def test_pdf_text_extraction_multiple_formats():
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


def test_pdf_empty_content():
    from backend.parsers.pdf_parser import parse_pdf
    result = parse_pdf(b"")
    assert isinstance(result["transactions"], list)


# --- OFX parser ---

MINIMAL_OFX = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>001</BANKID>
<ACCTID>123456</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101</DTSTART>
<DTEND>20260131</DTEND>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260105</DTPOSTED>
<TRNAMT>-1234.56</TRNAMT>
<FITID>1001</FITID>
<MEMO>ALUGUEL</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260115</DTPOSTED>
<TRNAMT>5000.00</TRNAMT>
<FITID>1002</FITID>
<MEMO>SALARIO</MEMO>
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL><BALAMT>3765.44</BALAMT><DTASOF>20260131</DTASOF></LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


def test_ofx_parses_transactions():
    result = parse_ofx(MINIMAL_OFX.encode("utf-8"))
    assert result.get("error") is None
    assert len(result["transactions"]) == 2
    amounts = sorted(t["amount"] for t in result["transactions"])
    assert amounts == [-1234.56, 5000.0]
    assert result["total_income"] == 5000.0
    assert result["total_expenses"] == 1234.56


def test_ofx_invalid_content():
    result = parse_ofx(b"isto nao e ofx")
    assert result["transactions"] == []
    assert result.get("error") is not None


def test_ofx_not_enough_columns_handled():
    # OFX without balances should not crash
    no_balance = MINIMAL_OFX.replace(
        "<LEDGERBAL><BALAMT>3765.44</BALAMT><DTASOF>20260131</DTASOF></LEDGERBAL>",
        "",
    )
    result = parse_ofx(no_balance.encode("utf-8"))
    assert len(result["transactions"]) == 2
