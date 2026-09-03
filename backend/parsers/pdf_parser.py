import re
from datetime import datetime
from io import BytesIO

import pdfplumber

DATE_PATTERNS = [
    r'\d{2}/\d{2}/\d{4}',
    r'\d{2}-\d{2}-\d{4}',
    r'\d{4}-\d{2}-\d{2}',
    r'\d{2}/\d{2}/\d{2}',
    r'\d{2}\.\d{2}\.\d{4}',
    r'\d{2}\.\d{2}\.\d{2}',
]

AMOUNT_PATTERN = re.compile(
    r'[-+]?\d{1,3}(?:\.\d{3})*,\d{2}|[-+]?\d+,\d{2}'
    r'|\(\d{1,3}(?:\.\d{3})*,\d{2}\)|\(\d+,\d{2}\)'
)


def extract_transactions_from_table(table: dict) -> list[dict]:
    transactions = []
    headers = [h.lower().strip() for h in table.get("headers", [])]

    date_col = None
    desc_col = None
    amount_col = None

    for i, h in enumerate(headers):
        if any(k in h for k in ["data", "date", "dt"]):
            date_col = i
        elif any(k in h for k in ["descri", "hist", "memo", "nome", "desc", "evento"]):
            desc_col = i
        elif any(k in h for k in ["valor", "amount", "mov", "r$", "importe"]):
            amount_col = i

    if date_col is None or amount_col is None:
        return transactions

    for row in table.get("rows", []):
        row_values = list(row.values()) if isinstance(row, dict) else row

        if date_col >= len(row_values) or amount_col >= len(row_values):
            continue

        date_str = str(row_values[date_col] or "")
        amount_str = str(row_values[amount_col] or "")
        desc = str(row_values[desc_col] if desc_col is not None and desc_col < len(row_values) else "")

        parsed_date = parse_date(date_str)
        parsed_amount = parse_amount(amount_str)

        if parsed_date and parsed_amount is not None:
            transactions.append({
                "date": parsed_date,
                "amount": parsed_amount,
                "description": desc.strip(),
                "type": "credit" if parsed_amount > 0 else "debit",
            })

    return transactions


def parse_date(date_str: str) -> str | None:
    date_str = date_str.strip()

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, date_str)
        if match:
            date_part = match.group()
            try:
                if re.match(r'\d{2}/\d{2}/\d{4}', date_part):
                    return datetime.strptime(date_part, "%d/%m/%Y").strftime("%Y-%m-%d")
                elif re.match(r'\d{2}-\d{2}-\d{4}', date_part):
                    return datetime.strptime(date_part, "%d-%m-%Y").strftime("%Y-%m-%d")
                elif re.match(r'\d{4}-\d{2}-\d{2}', date_part):
                    return date_part
                elif re.match(r'\d{2}/\d{2}/\d{2}', date_part):
                    return datetime.strptime(date_part, "%d/%m/%y").strftime("%Y-%m-%d")
                elif re.match(r'\d{2}\.\d{2}\.\d{4}', date_part):
                    return datetime.strptime(date_part, "%d.%m.%Y").strftime("%Y-%m-%d")
                elif re.match(r'\d{2}\.\d{2}\.\d{2}', date_part):
                    return datetime.strptime(date_part, "%d.%m.%y").strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def parse_amount(amount_str: str) -> float | None:
    amount_str = amount_str.strip()

    amount_str = re.sub(r'[R$\s]', '', amount_str)

    negative = '-' in amount_str or (amount_str.startswith('(') and amount_str.endswith(')'))
    amount_str = amount_str.replace('-', '').replace('+', '')
    amount_str = amount_str.lstrip('(').rstrip(')')

    if ',' in amount_str:
        # Formato brasileiro: ponto é milhar, vírgula é decimal (1.234,56 ou 1234,56)
        amount_str = amount_str.replace('.', '').replace(',', '.')
    elif '.' in amount_str and (amount_str.count('.') != 1 or len(amount_str.rsplit('.', 1)[-1]) > 2):
        # Sem vírgula: um único ponto com ≤2 casas decimais é formato internacional (1234.56);
        # múltiplos pontos ou 3+ casas são milhares brasileiros sem vírgula (1.234 / 1.234.567).
        amount_str = amount_str.replace('.', '')

    try:
        value = float(amount_str)
        return -value if negative else value
    except ValueError:
        return None


def parse_pdf(file_content: bytes) -> dict:
    try:
        pdf = pdfplumber.open(BytesIO(file_content))
        pages_text = []
        all_tables = []
        all_transactions = []

        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages_text.append({
                "page": i + 1,
                "text": text,
            })

            tables = page.extract_tables()
            for table in tables:
                if table and len(table) > 1:
                    headers = [str(h) if h else f"col_{j}" for j, h in enumerate(table[0])]
                    rows = []
                    for row in table[1:]:
                        row_dict = {headers[j]: row[j] for j in range(len(row)) if j < len(headers)}
                        rows.append(row_dict)
                    all_tables.append({"headers": headers, "rows": rows})

                    transactions = extract_transactions_from_table({"headers": headers, "rows": rows})
                    all_transactions.extend(transactions)

        full_text = "\n\n".join(p["text"] for p in pages_text)

        if not all_transactions:
            all_transactions = extract_transactions_from_text(full_text)

        total_income = sum(t["amount"] for t in all_transactions if t["amount"] > 0)
        total_expenses = sum(abs(t["amount"]) for t in all_transactions if t["amount"] < 0)

        pdf.close()

        return {
            "type": "PDF",
            "pages": len(pages_text),
            "full_text": full_text[:15000],
            "tables": all_tables,
            "has_tables": len(all_tables) > 0,
            "transactions": all_transactions,
            "total_transactions": len(all_transactions),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "summary": (
                f"Documento PDF com {len(pages_text)} página(s), {len(all_tables)} tabela(s) "
                f"e {len(all_transactions)} transação(ões) extraída(s)."
            ),
        }

    except Exception as e:
        return {
            "type": "PDF",
            "error": str(e),
            "full_text": "",
            "tables": [],
            "transactions": [],
            "summary": f"Erro ao processar PDF: {e}",
        }


def extract_transactions_from_text(text: str) -> list[dict]:
    transactions = []
    lines = text.split('\n')

    for line in lines:
        dates = re.findall(r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}', line)
        amounts = AMOUNT_PATTERN.findall(line)

        if dates and amounts:
            date_str = dates[0]
            amount_str = amounts[-1]

            parsed_date = parse_date(date_str)
            parsed_amount = parse_amount(amount_str)

            if parsed_date and parsed_amount is not None:
                desc = line
                for d in dates:
                    desc = desc.replace(d, '')
                for a in amounts:
                    desc = desc.replace(a, '')
                desc = re.sub(r'\s+', ' ', desc).strip()

                if len(desc) > 3:
                    transactions.append({
                        "date": parsed_date,
                        "amount": parsed_amount,
                        "description": desc[:100],
                        "type": "credit" if parsed_amount > 0 else "debit",
                    })

    return transactions
