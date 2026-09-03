"""Shared parser utilities for CSV, XLSX, and PDF parsers.

Provides robust parsing of monetary values, dates, and text normalization
used across multiple parser implementations.
"""
import logging
import re
import unicodedata
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalize unicode, strip, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = unicodedata.normalize("NFC", text)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


# ---------------------------------------------------------------------------
# Monetary value parsing
# ---------------------------------------------------------------------------

# Broad regex to capture anything that looks like a monetary value:
#   R$ 1.234,56  |  -R$ 1.234,56  |  (1.234,56)
#   1234.56      |  1,234.56      |  -25.90
_MONEY_RE = re.compile(
    r"""
    [Rr$\s]*                     # optional currency symbol + leading spaces
    (?:                          # grouped value (parens or plain)
        \([\s]*                  # opening paren
        [-+]?\s*                 # optional sign inside parens
        [\d.,\s]+                # digits with separators
        [\s]*\)                  # closing paren
    |
        [-+]?\s*                 # optional sign
        [\d.,\s]+                # digits with separators
    )
    """,
    re.VERBOSE,
)

# Matches a full monetary token more strictly: must end with digits
_MONEY_STRICT = re.compile(
    r"""
    [Rr$\s]*
    (?:
        \(\s*[-+]?\s*\d[\d.,\s]*\s*\)
    |
        [-+]?\s*\d[\d.,\s]*
    )
    """,
    re.VERBOSE,
)


def parse_money(value: str) -> float | None:
    """Parse a monetary string into a float.

    Supports Brazilian format (1.234,56), international format (1,234.56),
    plain decimals (1234.56), parenthesized negatives ((1.234,56)),
    R$ prefix, signs before/after R$, and spaces between components.

    Returns None if the value cannot be parsed as a monetary amount.
    Returns 0.0 only if the value is a legitimate zero amount.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return None

    # --- Determine negativity from parentheses ---
    negative = False

    # Check for parenthesized negative: (1.234,56)
    paren_match = re.search(r"\(\s*[-+]?\s*[\d.,\s]+\s*\)", s)
    if paren_match:
        negative = True
        # Extract the content inside the parens
        inner = paren_match.group(0)
        inner = inner.strip("()")
        inner = inner.strip()
        if inner:
            s = inner
        else:
            return None

    # --- Extract numeric token ---
    # Strip R$/currency prefix and signs
    cleaned = re.sub(r"[Rr$\s]", "", s)
    cleaned = cleaned.strip()

    if not cleaned:
        return None

    # Detect leading sign
    if cleaned.startswith("-"):
        negative = True
        cleaned = cleaned[1:]
    elif cleaned.startswith("+"):
        cleaned = cleaned[1:]

    if not cleaned:
        return None

    # --- Determine format and convert ---
    has_comma = "," in cleaned
    has_dot = "." in cleaned

    if has_comma and has_dot:
        # Both present: last separator determines decimal point
        last_comma = cleaned.rfind(",")
        last_dot = cleaned.rfind(".")
        if last_comma > last_dot:
            # Brazilian: 1.234,56 → remove dots, replace comma with dot
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # International: 1,234.56 → remove commas
            cleaned = cleaned.replace(",", "")
    elif has_comma:
        # Only comma: determine if decimal or thousands
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely decimal: 1234,56 or 1,234,56
            cleaned = cleaned.replace(",", ".")
        else:
            # Multiple commas as thousands: 1,234,567
            cleaned = cleaned.replace(",", "")
    elif has_dot:
        # Only dot: determine if decimal or thousands
        parts = cleaned.split(".")
        if len(parts) > 2:
            # Multiple dots: thousands separator (1.234.567)
            cleaned = cleaned.replace(".", "")
        elif len(parts[-1]) > 2:
            # More than 2 decimal places: not standard decimal → treat as thousands
            cleaned = cleaned.replace(".", "")
        # else: single dot with ≤2 decimals → standard decimal format

    # Remove any remaining spaces
    cleaned = cleaned.replace(" ", "")

    if not cleaned:
        return None

    try:
        amount = float(cleaned)
        import math
        if math.isnan(amount) or math.isinf(amount):
            return None
        return -amount if negative else amount
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

# Portuguese month abbreviation mapping (no locale dependency)
_PT_MONTHS = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4,
    "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8,
    "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}

_PT_MONTH_ABBR = "|".join(_PT_MONTHS.keys())

_DATE_FORMATS = [
    ("%d/%m/%Y", True),   # 01/09/2026
    ("%d-%m-%Y", True),   # 01-09-2026
    ("%Y-%m-%d", True),   # 2026-09-01
    ("%d/%m/%y", True),   # 01/09/26
    ("%d.%m.%Y", True),   # 01.09.2026
    ("%d.%m.%y", True),   # 01.09.26
    ("%m/%d/%Y", False),  # 09/01/2026 (US format, low priority)
]

_DATE_PATTERNS = [
    r"\d{2}/\d{2}/\d{4}",
    r"\d{2}-\d{2}-\d{4}",
    r"\d{4}-\d{2}-\d{2}",
    r"\d{2}/\d{2}/\d{2}",
    r"\d{2}\.\d{2}\.\d{4}",
    r"\d{2}\.\d{2}\.\d{2}",
    rf"\d{{2}}\s*(?:{_PT_MONTH_ABBR})\s*\d{{4}}",  # 31 JUL 2026
]

_PT_DATE_RE = re.compile(
    rf"(\d{{2}})\s*({_PT_MONTH_ABBR})\s*(\d{{4}})",
    re.IGNORECASE,
)


def parse_date(date_str: str) -> str | None:
    """Parse a date string into ISO format (YYYY-MM-DD).

    Supports DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD/MM/YY,
    DD.MM.YYYY, DD.MM.YY, MM/DD/YYYY (US), and DD MMM YYYY
    (Portuguese abbreviated months: JAN–DEZ).

    Returns None if parsing fails.
    """
    if not date_str:
        return None

    s = str(date_str).strip()
    if not s:
        return None

    # Try Portuguese abbreviated month format first (DD MMM YYYY)
    pt_match = _PT_DATE_RE.search(s)
    if pt_match:
        day_str, month_str, year_str = pt_match.groups()
        month_num = _PT_MONTHS.get(month_str.upper())
        if month_num:
            try:
                day = int(day_str)
                year = int(year_str)
                if 1 <= day <= 31 and 1900 <= year <= 2100 and 1 <= month_num <= 12:
                    return f"{year:04d}-{month_num:02d}-{day:02d}"
            except (ValueError, TypeError):
                pass

    # Extract date-like substring if embedded in other text
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, s)
        if match:
            s = match.group()
            break
    else:
        return None

    for fmt, preferred in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            # Sanity check: reject dates before 1900 or after 2100
            if dt.year < 1900 or dt.year > 2100:
                continue
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


# ---------------------------------------------------------------------------
# Column detection helpers
# ---------------------------------------------------------------------------

DATE_KEYWORDS = frozenset({
    "data", "date", "dt", "dt.", "dat", "datap", "lancamento", "lançamento",
    "lancto", "movement", "post_date", "dtlanc", "dt.lanc", "data.lanc",
    "data.lancamento", "dt.movimento", "data.movimento",
})

DESC_KEYWORDS = frozenset({
    "descricao", "descrição", "description", "historico", "histórico", "memo",
    "detail", "detalhe", "descricao_da_transacao", "estabelecimento",
    "merchant", "payee", "beneficiario", "beneficiário", "favorecido",
    "nota", "complemento", "descricao/historico", "descrição/histórico",
    "hist/descrição", "documento", "transaction description",
})

# Generic amount keywords — NOT including credit/debit (those are separate)
AMOUNT_KEYWORDS = frozenset({
    "valor", "amount", "value", "total", "quantia", "montante", "vlr", "vlr.",
    "movimento", "mov", "importe",
})

CREDIT_KEYWORDS = frozenset({
    "credito", "crédito", "credit", "entradas", "recebimentos",
    "deposito", "depósito", "cred",
})

DEBIT_KEYWORDS = frozenset({
    "debito", "débito", "debit", "saques", "pagamentos", "sair",
    "despesas", "saidas", "saídas", "deb",
})

NON_AMOUNT_KEYWORDS = frozenset({
    "codigo", "código", "code", "id", "numero", "número", "conta", "account",
    "agency", "agencia", "sequence", "sequencia", "saldo", "balance",
    "saldo anterior", "saldo atual", "closing balance", "opening balance",
})


def is_date_column(col_name: str, sample_values: list) -> bool:
    """Check if a column contains date values."""
    col_lower = col_name.lower().strip()
    if any(kw in col_lower for kw in DATE_KEYWORDS):
        return True
    if not sample_values:
        return False
    match_count = 0
    for v in sample_values[:10]:
        s = str(v).strip()
        for pat in _DATE_PATTERNS:
            if re.search(pat, s):
                match_count += 1
                break
    return match_count >= max(1, len(sample_values) * 0.4)


def is_amount_column(col_name: str, sample_values: list) -> bool:
    """Check if a column contains monetary amount values."""
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
        parsed = parse_money(s)
        if parsed is not None:
            numeric_count += 1
            if "," in s or ("." in s and s.count(".") == 1 and len(s.split(".")[-1]) == 2):
                has_decimal += 1
    if numeric_count < max(1, len(sample_values) * 0.4):
        return False
    if has_decimal >= max(1, numeric_count * 0.4):
        return True
    return False


def is_credit_column(col_name: str) -> bool:
    """Check if a column name indicates credit amounts."""
    col_lower = col_name.lower().strip()
    return any(kw in col_lower for kw in CREDIT_KEYWORDS)


def is_debit_column(col_name: str) -> bool:
    """Check if a column name indicates debit amounts."""
    col_lower = col_name.lower().strip()
    return any(kw in col_lower for kw in DEBIT_KEYWORDS)


def is_desc_column(col_name: str, sample_values: list) -> bool:
    """Check if a column contains text descriptions."""
    col_lower = col_name.lower().strip()
    if any(kw in col_lower for kw in DESC_KEYWORDS):
        return True
    if not sample_values:
        return False
    text_count = sum(
        1 for v in sample_values[:10]
        if v and isinstance(v, str) and len(v) > 3
    )
    return text_count >= max(1, len(sample_values) * 0.4)
