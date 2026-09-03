"""PDF parser with layered extraction strategy.

Extraction layers:
1. Table extraction (pdfplumber tables)
2. Raw text extraction
3. Transaction candidate detection
4. Multi-line transaction reconstruction
5. Normalization and deduplication

Supports both tabular and text-based PDF statements.
"""
import logging
import re
from io import BytesIO

import pdfplumber

from .utils import (
    CREDIT_KEYWORDS,
    DEBIT_KEYWORDS,
    NON_AMOUNT_KEYWORDS,
    _PT_MONTH_ABBR,
    normalize_text,
    parse_date,
    parse_money,
)

logger = logging.getLogger(__name__)

# Keep legacy names for backward compatibility with tests
extract_transactions_from_table_legacy = None  # placeholder

# ---------------------------------------------------------------------------
# Amount pattern — matches monetary values with optional sign, currency,
# thousands separators, and exactly 2 decimal digits
# ---------------------------------------------------------------------------
AMOUNT_PATTERN = re.compile(
    r"""
    [Rr$\s]*                    # optional currency prefix
    (?:                         # negative: parenthesized or leading sign
        \(\s*[-+]?\s*           # opening paren + optional sign
        \d[\d.,]*               # digits with optional separators
        [,\.]\d{2}              # decimal separator + 2 digits
        \s*\)                   # closing paren
    |
        [-+]?\s*                # optional leading sign
        \d[\d.,]*               # digits with optional separators
        [,\.]\d{2}              # decimal separator + 2 digits
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Non-transaction line patterns (headers, footers, totals, balances)
# ---------------------------------------------------------------------------

_NON_TRANSACTION_PATTERNS = [
    re.compile(r"saldo\s+(anterior|atual|final|dispon[ií]vel)", re.IGNORECASE),
    re.compile(r"(opening|closing)\s+balance", re.IGNORECASE),
    re.compile(r"^total", re.IGNORECASE),
    re.compile(r"^subtotal", re.IGNORECASE),
    re.compile(r"^p[aá]gina|^page\s+\d+", re.IGNORECASE),
    re.compile(r"extrato\s+banc[aá]rio", re.IGNORECASE),
    re.compile(r"comprovante", re.IGNORECASE),
    re.compile(r"impresso\s+em", re.IGNORECASE),
    re.compile(r"\bag[êe]ncia\b|\bagency\b", re.IGNORECASE),
    re.compile(r"conta\s+(corrente|poupan[cç]a)", re.IGNORECASE),
    re.compile(r" cpf[:\s]?\d", re.IGNORECASE),
    re.compile(r" cnpj[:\s]?\d", re.IGNORECASE),
]


def _is_non_transaction_line(line: str) -> bool:
    """Check if a line is metadata, header, footer, or balance line."""
    s = line.strip()
    if not s or len(s) < 3:
        return True
    return any(p.search(s) for p in _NON_TRANSACTION_PATTERNS)


# ---------------------------------------------------------------------------
# Table-based extraction (Layer 1)
# ---------------------------------------------------------------------------

def _detect_table_columns(headers: list[str]) -> dict:
    """Detect date, description, amount, credit, debit columns from table headers."""
    result = {"date": None, "desc": None, "amount": None, "credit": None, "debit": None}

    for i, h in enumerate(headers):
        hl = h.lower().strip()
        if any(kw in hl for kw in ("data", "date", "dt")):
            if result["date"] is None:
                result["date"] = i
        elif any(kw in hl for kw in CREDIT_KEYWORDS):
            if result["credit"] is None:
                result["credit"] = i
        elif any(kw in hl for kw in DEBIT_KEYWORDS):
            if result["debit"] is None:
                result["debit"] = i
        elif any(kw in hl for kw in ("valor", "amount", "value", "total", "vlr", "importe", "mov")):
            if result["amount"] is None:
                result["amount"] = i
        elif any(kw in hl for kw in ("descri", "hist", "memo", "nome", "desc", "evento", "documento")):
            if result["desc"] is None:
                result["desc"] = i

    return result


def _extract_from_table(table: dict) -> tuple[list[dict], dict]:
    """Extract transactions from a parsed table structure.

    Returns (transactions, diagnostics).
    """
    headers = [str(h).strip() if h else f"col_{j}" for j, h in enumerate(table.get("headers", []))]
    cols = _detect_table_columns(headers)

    diag = {
        "method": "table",
        "headers": headers,
        "columns_detected": cols,
        "rows_processed": 0,
        "transactions_found": 0,
        "rejection_counts": {"missing_date": 0, "missing_amount": 0},
    }

    if cols["date"] is None and cols["amount"] is None and cols["credit"] is None:
        logger.warning("Table extraction: no date or amount column found")
        return [], diag

    use_dual = cols["credit"] is not None and cols["debit"] is not None and cols["amount"] is None
    rows = table.get("rows", [])
    diag["rows_processed"] = len(rows)

    transactions = []
    for row in rows:
        row_values = list(row.values()) if isinstance(row, dict) else row

        # Parse date
        if cols["date"] is not None and cols["date"] < len(row_values):
            raw_date = row_values[cols["date"]]
            parsed_date = _parse_date_from_utils(str(raw_date)) if raw_date is not None else None
        else:
            parsed_date = None

        if not parsed_date:
            diag["rejection_counts"]["missing_date"] += 1
            continue

        # Parse description
        if cols["desc"] is not None and cols["desc"] < len(row_values):
            description = normalize_text(str(row_values[cols["desc"]] or ""))
        else:
            description = ""

        # Parse amount
        if use_dual:
            credit_raw = row_values[cols["credit"]] if cols["credit"] < len(row_values) else None
            debit_raw = row_values[cols["debit"]] if cols["debit"] < len(row_values) else None
            credit_val = parse_money(str(credit_raw)) if credit_raw is not None else None
            debit_val = parse_money(str(debit_raw)) if debit_raw is not None else None
            if credit_val is None and debit_val is None:
                diag["rejection_counts"]["missing_amount"] += 1
                continue
            amount = (credit_val or 0.0) - (debit_val or 0.0)
        else:
            if cols["amount"] is None or cols["amount"] >= len(row_values):
                diag["rejection_counts"]["missing_amount"] += 1
                continue
            raw_amount = row_values[cols["amount"]]
            amount = parse_money(str(raw_amount)) if raw_amount is not None else None
            if amount is None:
                diag["rejection_counts"]["missing_amount"] += 1
                continue

        transactions.append({
            "date": parsed_date,
            "amount": round(amount, 2),
            "description": description,
            "type": "credit" if amount > 0 else "debit",
        })

    diag["transactions_found"] = len(transactions)
    return transactions, diag


# ---------------------------------------------------------------------------
# Text-based extraction (Layer 2)
# ---------------------------------------------------------------------------

def _extract_transactions_from_text(text: str) -> tuple[list[dict], dict]:
    """Extract transactions from raw PDF text using multi-line reconstruction.

    Strategy:
    1. First pass: extract complete single-line transactions (date + amount on same line)
    2. Second pass: pair date-only lines with nearby amount-only lines
    3. Filter out non-transaction lines
    4. Deduplicate
    """
    diag = {
        "method": "text",
        "rows_processed": 0,
        "transactions_found": 0,
        "rejection_counts": {"missing_date": 0, "missing_amount": 0, "non_transaction": 0},
    }

    if not text or not text.strip():
        return [], diag

    lines = text.split("\n")
    diag["rows_processed"] = len(lines)

    # Classify each line
    line_info = []
    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or _is_non_transaction_line(stripped):
            line_info.append({"idx": line_idx, "text": stripped, "dates": [], "amounts": [], "skip": True})
            continue

        dates_found = re.findall(
            rf"\d{{2}}/\d{{2}}/\d{{4}}|\d{{2}}-\d{{2}}-\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}}|\d{{2}}\.\d{{2}}\.\d{{4}}|\d{{2}}\s*(?:{_PT_MONTH_ABBR})\s*\d{{4}}",
            stripped,
            re.IGNORECASE,
        )
        amounts_found = AMOUNT_PATTERN.findall(stripped)
        line_info.append({"idx": line_idx, "text": stripped, "dates": dates_found, "amounts": amounts_found, "skip": False})

    # Pass 1: Complete single-line transactions (has both date AND amount)
    transactions = []
    used_lines = set()

    for info in line_info:
        if info["skip"] or not info["dates"] or not info["amounts"]:
            continue

        parsed_date = _parse_date_from_utils(info["dates"][0])
        parsed_amount = parse_money(info["amounts"][-1])

        if parsed_date and parsed_amount is not None:
            desc = info["text"]
            for d in info["dates"]:
                desc = desc.replace(d, "")
            for a in info["amounts"]:
                desc = desc.replace(a, "")
            desc = re.sub(r"[R$\s]+", " ", desc).strip()
            desc = re.sub(r"\s+", " ", desc).strip()

            if desc and len(desc) >= 2 and not _is_non_transaction_line(desc):
                transactions.append({
                    "date": parsed_date,
                    "amount": round(parsed_amount, 2),
                    "description": desc[:200],
                    "type": "credit" if parsed_amount > 0 else "debit",
                })
                used_lines.add(info["idx"])

    # Pass 2: Multi-line reconstruction — pair date lines with nearby amount-only lines
    # Allows date lines that also have amounts (e.g., daily totals) to serve as
    # date anchors for subsequent individual transaction lines.
    MAX_GAP = 2
    for i, info in enumerate(line_info):
        if info["skip"] or info["idx"] in used_lines:
            continue
        if not info["dates"]:
            continue  # Need at least a date

        parsed_date = _parse_date_from_utils(info["dates"][0])
        if not parsed_date:
            diag["rejection_counts"]["missing_date"] += 1
            continue

        # Search forward for an amount-only line within MAX_GAP
        for j in range(i + 1, min(i + 1 + MAX_GAP, len(line_info))):
            candidate = line_info[j]
            if candidate["skip"] or candidate["idx"] in used_lines:
                continue
            if not candidate["amounts"]:
                continue

            parsed_amount = parse_money(candidate["amounts"][-1])
            if parsed_amount is None:
                continue

            # For daily-summary lines (date line also has amounts), infer the
            # sign of individual transactions from the daily total's sign.
            # Individual lines in this format are always unsigned; the summary
            # line uses "+" for income days and "-" for expense days.
            date_has_amounts = bool(info["amounts"])
            if date_has_amounts and parsed_amount > 0:
                summary_amount = parse_money(info["amounts"][-1])
                if summary_amount is not None and summary_amount < 0:
                    parsed_amount = -parsed_amount

            # Build description from intervening lines
            desc_parts = []
            for k in range(i + 1, j):
                if not line_info[k]["skip"]:
                    desc_parts.append(line_info[k]["text"])

            # For daily-summary lines (date line also has amounts), the actual
            # transaction description is on the candidate amount line itself.
            date_has_amounts = bool(info["amounts"])
            if date_has_amounts and candidate["text"]:
                # Use candidate line's text as the primary description
                cand_text = candidate["text"]
                for a in candidate["amounts"]:
                    cand_text = cand_text.replace(a, "")
                cand_text = re.sub(r"[R$\s]+", " ", cand_text).strip()
                if cand_text and len(cand_text) >= 2:
                    desc_parts.insert(0, cand_text)
            elif not desc_parts:
                # Fallback: use date-line text minus the date
                date_line_text = info["text"]
                for d in info["dates"]:
                    date_line_text = date_line_text.replace(d, "")
                date_line_text = re.sub(r"[R$\s]+", " ", date_line_text).strip()
                if date_line_text:
                    desc_parts.insert(0, date_line_text)

            desc = " ".join(desc_parts).strip()
            desc = re.sub(r"\s+", " ", desc).strip()

            if not desc or len(desc) < 2:
                desc = "(sem descrição)"

            transactions.append({
                "date": parsed_date,
                "amount": round(parsed_amount, 2),
                "description": desc[:200],
                "type": "credit" if parsed_amount > 0 else "debit",
            })
            used_lines.add(info["idx"])
            used_lines.add(candidate["idx"])
            break
        else:
            diag["rejection_counts"]["missing_amount"] += 1

    # Step 3: Deduplicate by (date, amount, description) — keep first occurrence
    seen = set()
    unique_transactions = []
    for txn in transactions:
        key = (txn["date"], txn["amount"], txn["description"])
        if key not in seen:
            seen.add(key)
            unique_transactions.append(txn)

    diag["transactions_found"] = len(unique_transactions)
    logger.info(
        "Text extraction: %d lines processed, %d transactions found",
        diag["rows_processed"], len(unique_transactions),
    )
    return unique_transactions, diag


# ---------------------------------------------------------------------------
# Main PDF parser
# ---------------------------------------------------------------------------

def extract_transactions_from_text(text: str) -> list[dict]:
    """Legacy wrapper: extract transactions from text (returns list only)."""
    txns, _ = _extract_transactions_from_text(text)
    return txns


def extract_transactions_from_table(table: dict) -> list[dict]:
    """Legacy wrapper: extract transactions from table dict (returns list only)."""
    txns, _ = _extract_from_table(table)
    return txns


def parse_amount(amount_str: str) -> float | None:
    """Legacy wrapper for backward compatibility."""
    return parse_money(amount_str)


# Keep a direct reference to the utils parse_date before any shadowing
_parse_date_from_utils = parse_date


def parse_date_legacy(date_str: str) -> str | None:
    """Legacy wrapper for backward compatibility."""
    return _parse_date_from_utils(date_str)


# Re-export as parse_date for backward compatibility with tests
parse_date = parse_date_legacy


def parse_pdf(file_content: bytes) -> dict:
    """Parse a PDF file and extract transactions using layered strategy.

    Layer 1: Table extraction
    Layer 2: Text-based extraction with multi-line reconstruction
    """
    logger.info("Starting PDF parse, size=%d bytes", len(file_content))

    try:
        pdf = pdfplumber.open(BytesIO(file_content))
        pages_text = []
        all_tables = []
        all_transactions = []
        extraction_diagnostics = []

        for i, page in enumerate(pdf.pages):
            logger.debug("Processing page %d/%d", i + 1, len(pdf.pages))

            # Layer 1: Table extraction
            tables = page.extract_tables()
            for table in tables:
                if table and len(table) > 1:
                    headers = [str(h) if h else f"col_{j}" for j, h in enumerate(table[0])]
                    rows = []
                    for row in table[1:]:
                        row_dict = {headers[j]: row[j] for j in range(len(row)) if j < len(headers)}
                        rows.append(row_dict)

                    table_struct = {"headers": headers, "rows": rows}
                    all_tables.append(table_struct)

                    txns, tdiag = _extract_from_table(table_struct)
                    extraction_diagnostics.append(tdiag)
                    all_transactions.extend(txns)

            # Collect text for Layer 2
            text = page.extract_text() or ""
            pages_text.append({"page": i + 1, "text": text})

        full_text = "\n\n".join(p["text"] for p in pages_text)

        # Layer 2: Text extraction (only if tables didn't yield results)
        if not all_transactions:
            logger.info("No transactions from tables, falling back to text extraction")
            txns, tdiag = _extract_transactions_from_text(full_text)
            extraction_diagnostics.append(tdiag)
            all_transactions.extend(txns)

        # Deduplicate across all layers
        seen = set()
        unique_transactions = []
        for txn in all_transactions:
            key = (txn["date"], txn["amount"], txn["description"])
            if key not in seen:
                seen.add(key)
                unique_transactions.append(txn)

        total_income = sum(t["amount"] for t in unique_transactions if t["amount"] > 0)
        total_expenses = sum(abs(t["amount"]) for t in unique_transactions if t["amount"] < 0)

        pdf.close()

        # Aggregate diagnostics
        agg_rejection = {"missing_date": 0, "missing_amount": 0, "non_transaction": 0}
        agg_rows = 0
        for d in extraction_diagnostics:
            agg_rows += d.get("rows_processed", 0)
            for k, v in d.get("rejection_counts", {}).items():
                agg_rejection[k] = agg_rejection.get(k, 0) + v

        diagnostics = {
            "rows_processed": agg_rows,
            "transactions_found": len(unique_transactions),
            "rejection_counts": agg_rejection,
            "pages_processed": len(pages_text),
            "tables_found": len(all_tables),
            "extraction_methods": [d.get("method", "unknown") for d in extraction_diagnostics],
        }

        logger.info(
            "PDF parse complete: %d pages, %d tables, %d transactions",
            len(pages_text), len(all_tables), len(unique_transactions),
        )

        return {
            "type": "PDF",
            "pages": len(pages_text),
            "full_text": full_text,
            "tables": all_tables,
            "has_tables": len(all_tables) > 0,
            "transactions": unique_transactions,
            "total_transactions": len(unique_transactions),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "summary": (
                f"Documento PDF com {len(pages_text)} página(s), {len(all_tables)} tabela(s) "
                f"e {len(unique_transactions)} transação(ões) extraída(s)."
            ),
            "_diagnostics": diagnostics,
        }

    except Exception as e:
        logger.exception("PDF parse failed")
        return {
            "type": "PDF",
            "error": str(e),
            "full_text": "",
            "tables": [],
            "transactions": [],
            "summary": f"Erro ao processar PDF: {e}",
            "_diagnostics": {"rows_processed": 0, "transactions_found": 0, "rejection_counts": {}},
        }
