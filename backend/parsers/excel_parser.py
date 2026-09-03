import re
from datetime import datetime
from io import BytesIO, StringIO

import openpyxl
import pandas as pd

DATE_PATTERNS = [
    r"\d{2}/\d{2}/\d{4}",
    r"\d{2}-\d{2}-\d{4}",
    r"\d{4}-\d{2}-\d{2}",
    r"\d{2}/\d{2}/\d{2}",
]

AMOUNT_PATTERNS = [
    r"[+-]?\d+[\.,]\d{2}",
]

DATE_KEYWORDS = {"data", "date", "dt", "dt.", "dat", "datap", "lancamento", "lançamento", "movement", "post_date"}
DESC_KEYWORDS = {
    "descricao", "descrição", "description", "historico", "histórico", "memo", "detail",
    "detalhe", "descricao_da_transacao", "estabelecimento", "merchant", "payee",
    "beneficiario", "beneficiário", "favorecido", "nota", "complemento",
}
AMOUNT_KEYWORDS = {
    "valor", "amount", "value", "total", "quantia", "montante", "vlr", "vlr.",
    "credit", "debit", "credito", "debito", "saque", "deposito", "depósito",
}
NON_AMOUNT_KEYWORDS = {
    "codigo", "código", "code", "id", "numero", "número", "conta", "account",
    "agency", "agencia", "Sequence", "sequencia",
}


def _is_date_column(col_name: str, sample_values: list) -> bool:
    col_lower = col_name.lower().strip()
    if any(kw in col_lower for kw in DATE_KEYWORDS):
        return True
    if not sample_values:
        return False
    match_count = 0
    for v in sample_values[:10]:
        s = str(v).strip()
        for pat in DATE_PATTERNS:
            if re.search(pat, s):
                match_count += 1
                break
    return match_count >= len(sample_values) * 0.5


def _is_amount_column(col_name: str, sample_values: list) -> bool:
    col_lower = col_name.lower().strip()
    if any(kw in col_lower for kw in NON_AMOUNT_KEYWORDS):
        return False
    if any(kw in col_lower for kw in AMOUNT_KEYWORDS):
        return True
    if not sample_values:
        return False
    numeric_count = 0
    has_decimal = 0
    for v in sample_values[:10]:
        if v is None:
            continue
        s = str(v).strip()
        s_clean = s.replace(".", "").replace(",", ".")
        try:
            float(s_clean)
            numeric_count += 1
            if "," in s or ("." in s and s.count(".") == 1 and len(s.split(".")[-1]) == 2):
                has_decimal += 1
        except ValueError:
            pass
    if numeric_count < len(sample_values) * 0.5:
        return False
    if has_decimal >= numeric_count * 0.5:
        return True
    return False


def _is_desc_column(col_name: str, sample_values: list) -> bool:
    col_lower = col_name.lower().strip()
    if any(kw in col_lower for kw in DESC_KEYWORDS):
        return True
    if not sample_values:
        return False
    text_count = sum(1 for v in sample_values[:10] if v and isinstance(v, str) and len(v) > 3)
    return text_count >= len(sample_values) * 0.5


def _parse_date(val) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def _parse_amount(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = s.replace("R$", "").replace("$", "").strip()
    negative = False
    if s.startswith("-") or s.startswith("("):
        negative = True
    s = s.lstrip("-").lstrip("(").rstrip(")")
    if "," in s:
        # Formato brasileiro: ponto é milhar, vírgula é decimal (1.234,56 ou 1234,56)
        s = s.replace(".", "").replace(",", ".")
    elif "." in s and (s.count(".") != 1 or len(s.rsplit(".", 1)[-1]) > 2):
        # Sem vírgula: um único ponto com ≤2 casas decimais é formato internacional (1234.56);
        # múltiplos pontos ou 3+ casas são milhares brasileiros sem vírgula (1.234 / 1.234.567).
        s = s.replace(".", "")
    try:
        amount = float(s)
        return -amount if negative else amount
    except ValueError:
        return 0.0


def _extract_transactions_from_rows(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    all_cols = list(rows[0].keys())
    date_col = None
    desc_col = None
    amount_col = None

    for col in all_cols:
        sample = [r.get(col) for r in rows[:20] if r.get(col) is not None]
        if date_col is None and _is_date_column(col, sample):
            date_col = col
        elif amount_col is None and _is_amount_column(col, sample):
            amount_col = col
        elif desc_col is None and _is_desc_column(col, sample):
            desc_col = col

    if amount_col is None:
        numeric_cols = []
        for col in all_cols:
            col_lower = col.lower().strip()
            if any(kw in col_lower for kw in NON_AMOUNT_KEYWORDS):
                continue
            sample = [r.get(col) for r in rows[:20]]
            numeric_count = 0
            has_decimal = 0
            for v in sample:
                if v is None:
                    continue
                s = str(v).strip()
                s_clean = s.replace(".", "").replace(",", ".")
                try:
                    float(s_clean)
                    numeric_count += 1
                    if "," in s or ("." in s and s.count(".") == 1 and len(s.split(".")[-1]) == 2):
                        has_decimal += 1
                except ValueError:
                    pass
            if numeric_count >= len(sample) * 0.5:
                numeric_cols.append((col, has_decimal))
        if numeric_cols:
            numeric_cols.sort(key=lambda x: x[1], reverse=True)
            amount_col = numeric_cols[0][0]

    if desc_col is None:
        for col in all_cols:
            if col != date_col and col != amount_col:
                desc_col = col
                break

    transactions = []
    for row in rows:
        amount = _parse_amount(row.get(amount_col)) if amount_col else 0.0
        if amount == 0:
            continue
        transactions.append({
            "date": _parse_date(row.get(date_col)) if date_col else "",
            "description": str(row.get(desc_col, "")) if desc_col else "",
            "amount": round(amount, 2),
        })

    return transactions


def parse_excel(file_content: bytes, filename: str = "") -> dict:
    try:
        wb = openpyxl.load_workbook(BytesIO(file_content), read_only=True, data_only=True)
        sheets_data = {}
        total_rows = 0
        sheet_names = list(wb.sheetnames)

        for sheet_name in sheet_names:
            ws = wb[sheet_name]
            rows = []
            headers = None

            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    headers = [str(h) if h else f"col_{j}" for j, h in enumerate(row)]
                else:
                    row_dict = {headers[j]: row[j] for j in range(len(row)) if j < len(headers)}
                    rows.append(row_dict)

            sheets_data[sheet_name] = rows
            total_rows += len(rows)

        wb.close()

        all_rows = []
        for sheet_name, rows in sheets_data.items():
            for row in rows:
                row["_sheet"] = sheet_name
                all_rows.append(row)

        transactions = _extract_transactions_from_rows(all_rows)

        total_income = sum(t["amount"] for t in transactions if t["amount"] > 0)
        total_expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)

        df = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()
        summary_stats = {}
        if not df.empty:
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            for col in numeric_cols:
                summary_stats[col] = {
                    "sum": round(float(df[col].sum()), 2),
                    "mean": round(float(df[col].mean()), 2),
                    "min": round(float(df[col].min()), 2),
                    "max": round(float(df[col].max()), 2),
                }

        return {
            "type": "XLSX",
            "sheets": sheet_names,
            "total_rows": total_rows,
            "sheets_data": {k: v[:100] for k, v in sheets_data.items()},
            "summary_stats": summary_stats,
            "columns": list(df.columns) if not df.empty else [],
            "transactions": transactions,
            "total_transactions": len(transactions),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "summary": f"Planilha Excel com {len(sheets_data)} aba(s) e {total_rows} linhas. "
                       f"Transações: {len(transactions)}. "
                       f"Receitas: R$ {total_income:,.2f}. Despesas: R$ {total_expenses:,.2f}.",
        }

    except Exception as e:
        return {
            "type": "XLSX",
            "error": str(e),
            "transactions": [],
            "sheets_data": {},
            "summary": f"Erro ao processar Excel: {e}",
        }


def _detect_csv_delimiter(text: str) -> str:
    first_lines = text.split("\n")[:5]
    comma_count = sum(line.count(",") for line in first_lines)
    semicolon_count = sum(line.count(";") for line in first_lines)
    if semicolon_count > comma_count:
        return ";"
    return ","


def _decode_with_fallback(file_content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            return file_content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return file_content.decode("utf-8", errors="replace")


def parse_csv(file_content: bytes, filename: str = "") -> dict:
    try:
        if not file_content or not file_content.strip():
            return {
                "type": "CSV",
                "transactions": [],
                "data": [],
                "summary": "Arquivo CSV vazio.",
            }

        text = _decode_with_fallback(file_content)
        delimiter = _detect_csv_delimiter(text)
        df = pd.read_csv(StringIO(text), sep=delimiter, on_bad_lines="skip")

        if df.empty or len(df.columns) < 2:
            return {
                "type": "CSV",
                "columns": list(df.columns) if not df.empty else [],
                "total_rows": 0,
                "data": [],
                "transactions": [],
                "summary": "Arquivo CSV sem dados tabulares válidos.",
            }

        rows = df.head(500).to_dict(orient="records")
        transactions = _extract_transactions_from_rows(rows)

        total_income = sum(t["amount"] for t in transactions if t["amount"] > 0)
        total_expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        summary_stats = {}
        for col in numeric_cols:
            summary_stats[col] = {
                "sum": round(float(df[col].sum()), 2),
                "mean": round(float(df[col].mean()), 2),
                "min": round(float(df[col].min()), 2),
                "max": round(float(df[col].max()), 2),
            }

        return {
            "type": "CSV",
            "columns": list(df.columns),
            "total_rows": len(df),
            "data": rows[:200],
            "summary_stats": summary_stats,
            "transactions": transactions,
            "total_transactions": len(transactions),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "summary": f"Planilha CSV com {len(df)} linhas e {len(df.columns)} colunas. "
                       f"Transações: {len(transactions)}. "
                       f"Receitas: R$ {total_income:,.2f}. Despesas: R$ {total_expenses:,.2f}.",
        }

    except Exception as e:
        return {
            "type": "CSV",
            "error": str(e),
            "transactions": [],
            "data": [],
            "summary": f"Erro ao processar CSV: {e}",
        }
