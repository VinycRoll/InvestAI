from io import BytesIO

from ofxparse import OfxParser


def parse_ofx(file_content: bytes) -> dict:
    try:
        ofx = OfxParser.parse(BytesIO(file_content))

        account = ofx.account
        transactions = []

        if account and account.statement:
            for txn in account.statement.transactions:
                amount = 0.0
                if txn.amount is not None:
                    try:
                        amount = float(txn.amount)
                    except (TypeError, ValueError):
                        amount = 0.0
                transactions.append({
                    "date": txn.date.isoformat() if getattr(txn, "date", None) else None,
                    "amount": round(amount, 2),
                    "description": (txn.memo or txn.payee or "").strip(),
                    "type": txn.type or "",
                    "check_number": getattr(txn, "check_number", None),
                })

        balance = None
        if account and account.statement:
            try:
                raw_balance = getattr(account.statement, "balance", None)
                balance = float(raw_balance) if raw_balance else None
            except (TypeError, ValueError):
                balance = None

        account_id = ""
        if account:
            account_id = account.account_id or ""

        total_income = sum(t["amount"] for t in transactions if t["amount"] > 0)
        total_expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)

        return {
            "type": "OFX",
            "account_id": account_id,
            "balance": balance,
            "transactions": transactions,
            "total_transactions": len(transactions),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "summary": f"Extrato bancário com {len(transactions)} transações. "
                       f"Receitas: R$ {total_income:,.2f}. Despesas: R$ {total_expenses:,.2f}.",
        }

    except Exception as e:
        return {
            "type": "OFX",
            "error": str(e),
            "transactions": [],
            "summary": f"Erro ao processar OFX: {e}",
        }
