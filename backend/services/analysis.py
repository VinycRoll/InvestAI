import json
import re
from collections import defaultdict

EXPENSE_CATEGORIES = {
    "alimentacao": [
        "ifood", "rappi", "supermercado", "mercado", "padaria", "restaurante",
        "lanchonete", "mcdonald", "burger", "pizza", "comida", "acai", "açaí", "cafe", "café",
        "lanche", "jantar", "almoco", "almoço", "cafe da manha", "café da manhã", "subway", "outback",
        "spoleto", "giraffas", "habib", "kibon", "bobs", "divino fogao",
        "carrefour extra", "pao de acucar", "stok", "assai", "atacadao",
        "compra desconto", "mercado livre", "amazon fresh", "ifood market",
    ],
        "moradia": [
        "aluguel", "condominio", "iptu", "agua", "luz", "eletricidade", "gasnatural", "gas de cozinha",
        "internet", "telefone", "celular", "fixo", "vivo", "claro", "tim",
        "oi", "embratel", "claro net", "sky", "vivo fibra",
        "condominio portao", "taxa de limpeza", "seguro condominial",
        "manutencao predial", "elevador", "portaria",
    ],
    "transporte": [
        "uber", "99", "gasolina", "etanol", "estacionamento", "pedagio",
        "onibus", "metro", "bilhete", "bilhete unico", "recarga bilhete",
        "taxi", "iango", "cabify", "blablacar", "combustivel", "posto",
        "shell", "bp", "petrobras", "podebr", "alcool", "diesel",
        "rodagem", "estacionamento shopping", "zona azul",
    ],
    "saude": [
        "farmacia", "drogaria", "hospital", "medico", "dentista",
        "plano de saude", "academia", "personal trainer", "physio",
        "fisioterapia", "psicologo", "psicologia", "terapia",
        "exame", "laboratorio", "analise clinica", "ultrassom",
        "raio x", "ressonancia", "mamografia", "vacina",
        "drogasil", "drogaria sao paulo", "pacheco", "dimed",
        "venancio", "farmacia popular", "ultrafarma",
    ],
    "educacao": [
        "escola", "faculdade", "curso", "udemy", "alura", "livro",
        "material escolar", "uniforme", "mensalidade escolar",
        "universidade", "faculdade", "pos graduacao", "mba",
        "curso online", "coursera", "edx", "platzi", "digital house",
        "trybe", "helio", "fib", "puc", "faria lima",
    ],
    "lazer": [
        "netflix", "spotify", "amazon prime", "disney", "hbo", "cinema",
        "bar", "balada", "show", "ingresso", "parque", "museu",
        "teatro", "opera", "festival", "carnaval", "show ao vivo",
        "spotify premium", "youtube premium", "deezer", "tidal",
        "apple music", "globoplay", "paramount", "star plus",
        "hbomax", "disney plus", "prime video", "apple tv",
        "playstation", "xbox", "steam", "epic games", "nintendo",
    ],
    "assinaturas": [
        "apple.com", "apple tv", "apple music", "apple store",
        "google play", "google workspace", "google one",
        "microsoft 365", "microsoft store", "office 365",
        "adobe", "cloud", "hosting",
        "dominio", "dropbox", "onedrive", "icloud", "google drive",
        "canva", "figma", "notion", "trello", "slack", "zoom",
        "grammarly", "1password", "lastpass", "dashlane",
    ],
    "transferencias": [
        "pix", "ted", "doc", "transferencia", "envio", "recebimento",
        "transferencia pix", "pix recebido", "pix enviado",
        "ted recebido", "ted enviado", "doc recebido", "doc enviado",
        "transferencia bancaria", "remessa", "deposito",
    ],
    "investimentos": [
        "corretora", "tesouro", "fundo", "acao", "investimento",
        "aplicacao", "resgate", "rendimento", "dividendo",
        "b3", "bovespa", "ibovespa", "cambial", "cdb", "lci", "lca",
        "debenture", "titulos publicos", "selic", "ipca",
        "investidor pessoa fisica", "xp", "btg", "inter",
        "clear", "modal", "terra corretora",
    ],
    "vestuario": [
        "roupa", "camiseta", "calca", "tenis", "sapato", "bota",
        "jaqueta", "casaco", "vestido", "saia", "shorts",
        "zara", "h&m", "uniqlo", "renner", "riachuelo",
        "centauro", "nike", "adidas", "puma", "asics",
    ],
    "pets": [
        "pet", "petshop", "veterinario", "vacina pet", "ração",
        "cachorro", "gato", "peixe", "hamster",
        "petlove", "cobasi", "petz", "veterinaria",
        "banho e tosa", "hotel pet", "dog walker",
    ],
    "casa": [
        "moveis", "decoracao", "eletrodomesticos", "refrigerador",
        "maquina de roupa", "maquina de louca", "aspirador",
        "ar condicionado", "ventilador",
        "ikea", "leroy merlin", "casa&video", "tok&stok",
        "magalu", "americanas", "casas bahia", "extra supermercado",
    ],
}


# Keywords that must match whole words (word boundaries) to avoid false positives.
# e.g. "ventilador" contains "vent", "99" inside other numbers, "pet" in "appetite".
WORD_ONLY_KEYWORDS = {
    "ifood", "rappi", "uber", "99", "pet", "taxi", "pix", "ted", "doc",
    "netflix", "spotify", "oi", "inter", "xp", "acai", "cafe", "sky", "bar",
}


def _escape_keyword(keyword: str) -> str:
    return re.escape(keyword).replace(r"\ ", r"[\s\-\._/]+")


# Cache of compiled keyword regexes. Built lazily on first use: compiling the
# same keyword pattern over and over (once per transaction) dominated the
# categorization cost, so patterns are compiled exactly once per keyword.
_keyword_regex_cache: dict[str, re.Pattern] = {}


def _keyword_regex(keyword: str) -> re.Pattern:
    pattern = _keyword_regex_cache.get(keyword)
    if pattern is not None:
        return pattern
    if keyword in WORD_ONLY_KEYWORDS or re.fullmatch(r"[a-zA-Z0-9]{2,3}", keyword):
        pattern = re.compile(r"(?<![a-zA-Z0-9])" + _escape_keyword(keyword) + r"(?![a-zA-Z0-9])", re.IGNORECASE)
    else:
        pattern = re.compile(_escape_keyword(keyword), re.IGNORECASE)
    _keyword_regex_cache[keyword] = pattern
    return pattern


def decode_user_categories(user_categories: list[dict] | None) -> list[dict]:
    if not user_categories:
        return []
    decoded = []
    for uc in user_categories:
        keywords = uc.get("keywords", [])
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except (TypeError, ValueError, json.JSONDecodeError):
                keywords = []
        decoded.append({"name": uc["name"], "keywords": keywords})
    return decoded


def categorize_transaction(description: str, user_categories: list[dict] = None) -> str:
    if not description:
        return "outros"
    desc = str(description)

    if user_categories:
        for uc in user_categories:
            keywords = uc.get("keywords", [])
            for keyword in keywords:
                if _keyword_regex(str(keyword)).search(desc):
                    return uc["name"]
    for category, keywords in EXPENSE_CATEGORIES.items():
        for keyword in keywords:
            if _keyword_regex(keyword).search(desc):
                return category
    return "outros"


def analyze_transactions(transactions: list[dict], user_categories: list[dict] = None) -> dict:
    categorized = defaultdict(lambda: {"count": 0, "total": 0})
    monthly_data = defaultdict(lambda: {"income": 0, "expenses": 0})
    daily_data = defaultdict(lambda: {"income": 0, "expenses": 0})

    decoded_cats = decode_user_categories(user_categories)

    total_income = 0.0
    total_expenses = 0.0

    for txn in transactions:
        amount = txn.get("amount", 0)
        date_str = txn.get("date", "")
        desc = txn.get("description", "")

        category = categorize_transaction(desc, decoded_cats or None)
        categorized[category]["count"] += 1
        categorized[category]["total"] += abs(amount)

        if amount > 0:
            total_income += abs(amount)
        elif amount < 0:
            total_expenses += abs(amount)

        if date_str:
            try:
                month_key = date_str[:7]
                day_key = date_str[:10]
                if amount > 0:
                    monthly_data[month_key]["income"] += amount
                    daily_data[day_key]["income"] += amount
                else:
                    monthly_data[month_key]["expenses"] += abs(amount)
                    daily_data[day_key]["expenses"] += abs(amount)
            except (TypeError, ValueError):
                pass

    top_expenses = sorted(
        [t for t in transactions if t.get("amount", 0) < 0],
        key=lambda x: abs(x.get("amount", 0)),
        reverse=True
    )[:5]

    recurring = []
    desc_counts = defaultdict(list)
    for txn in transactions:
        if txn.get("amount", 0) < 0:
            desc_counts[txn.get("description", "")].append(txn)

    for desc, txns in desc_counts.items():
        if len(txns) >= 2:
            avg_amount = sum(abs(t["amount"]) for t in txns) / len(txns)
            recurring.append({
                "description": desc,
                "count": len(txns),
                "avg_amount": round(avg_amount, 2),
                "total": round(sum(abs(t["amount"]) for t in txns), 2),
            })

    sorted_months = sorted(monthly_data.keys())
    monthly_comparison = []
    for i in range(1, len(sorted_months)):
        prev_month = monthly_data[sorted_months[i - 1]]
        curr_month = monthly_data[sorted_months[i]]

        prev_income = prev_month["income"]
        prev_expenses = prev_month["expenses"]
        income_change = (
            (curr_month["income"] - prev_income) / prev_income * 100
            if prev_income > 0
            else 0
        )
        expense_change = (
            (curr_month["expenses"] - prev_expenses) / prev_expenses * 100
            if prev_expenses > 0
            else 0
        )

        monthly_comparison.append({
            "month": sorted_months[i],
            "income": round(curr_month["income"], 2),
            "expenses": round(curr_month["expenses"], 2),
            "balance": round(curr_month["income"] - curr_month["expenses"], 2),
            "income_change_pct": round(income_change, 1),
            "expense_change_pct": round(expense_change, 1),
        })

    alerts = []
    if total_income > 0:
        avg_monthly_expenses = total_expenses / max(len(sorted_months), 1)
        for month, data in monthly_data.items():
            if data["expenses"] > avg_monthly_expenses * 1.5:
                alerts.append({
                    "type": "high_expense",
                    "month": month,
                    "amount": round(data["expenses"], 2),
                    "avg": round(avg_monthly_expenses, 2),
                    "message": (
                        f"Gasto em {month} ({data['expenses']:,.2f}) foi "
                        f"{((data['expenses'] / avg_monthly_expenses) - 1) * 100:.0f}% acima da média"
                    ),
                })

    savings_rate = 0
    if total_income > 0:
        raw_rate = (1 - total_expenses / total_income) * 100
        savings_rate = round(max(0, min(100, raw_rate)), 1)

    suggested_investment = 0
    if total_income > 0 and total_expenses > 0:
        monthly_income = total_income / max(len(sorted_months), 1)
        monthly_expenses = total_expenses / max(len(sorted_months), 1)
        current_savings = monthly_income - monthly_expenses

        if current_savings > 0:
            suggested_investment = round(current_savings * 0.8, 2)
        else:
            suggested_investment = 0

    categories_result = {k: {"count": v["count"], "total": round(v["total"], 2)} for k, v in categorized.items()}

    suggested_investment_note = (
        "Estimativa de capacidade de investimento baseada em 80% da sobra mensal média. "
        "Não é uma recomendação financeira personalizada. Consulte um profissional antes de investir."
    )

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "balance": round(total_income - total_expenses, 2),
        "categories": categories_result,
        "top_expenses": top_expenses,
        "recurring_expenses": sorted(recurring, key=lambda x: x["total"], reverse=True)[:10],
        "monthly_data": dict(monthly_data),
        "monthly_comparison": monthly_comparison,
        "daily_data": dict(daily_data),
        "alerts": alerts,
        "suggested_investment": suggested_investment,
        "suggested_investment_note": suggested_investment_note,
        "savings_rate": savings_rate,
        "months_analyzed": len(sorted_months),
        "avg_monthly_income": round(total_income / max(len(sorted_months), 1), 2),
        "avg_monthly_expenses": round(total_expenses / max(len(sorted_months), 1), 2),
    }


def format_analysis_for_ai(analysis: dict, parsed_data: dict) -> str:
    text = "=== DADOS FINANCEIROS PROCESSADOS ===\n\n"
    text += f"Receitas totais: R$ {analysis['total_income']:,.2f}\n"
    text += f"Despesas totais: R$ {analysis['total_expenses']:,.2f}\n"
    text += f"Saldo: R$ {analysis['balance']:,.2f}\n"
    text += f"Taxa de poupança: {analysis['savings_rate']}%\n"
    text += f"Meses analisados: {analysis['months_analyzed']}\n"
    text += f"Receita média mensal: R$ {analysis['avg_monthly_income']:,.2f}\n"
    text += f"Despesa média mensal: R$ {analysis['avg_monthly_expenses']:,.2f}\n\n"

    text += "CATEGORIZAÇÃO DOS GASTOS:\n"
    for cat, data in sorted(analysis["categories"].items(), key=lambda x: x[1]["total"], reverse=True):
        text += f"  - {cat}: R$ {data['total']:,.2f} ({data['count']} transações)\n"

    if analysis["top_expenses"]:
        text += "\nTOP 5 MAIORES DESPESAS:\n"
        for i, exp in enumerate(analysis["top_expenses"], 1):
            text += f"  {i}. {exp.get('description', 'N/D')} - R$ {abs(exp.get('amount', 0)):,.2f}\n"

    if analysis["recurring_expenses"]:
        text += "\nGASTOS RECORRENTES IDENTIFICADOS:\n"
        for rec in analysis["recurring_expenses"][:5]:
            text += f"  - {rec['description']}: R$ {rec['avg_amount']:,.2f}/x ({rec['count']}x)\n"

    if analysis["monthly_comparison"]:
        text += "\nCOMPARATIVO MÊS A MÊS:\n"
        for comp in analysis["monthly_comparison"]:
            text += (
                f"  - {comp['month']}: Receita {comp['income_change_pct']:+.1f}%, "
                f"Despesa {comp['expense_change_pct']:+.1f}%\n"
            )

    if analysis["alerts"]:
        text += "\nALERTAS:\n"
        for alert in analysis["alerts"]:
            text += f"  - {alert['message']}\n"

    text += (
        "\nSugestão de investimento mensal: "
        f"R$ {analysis['suggested_investment']:,.2f} "
        "(estimativa de capacidade de investimento — 80% da sobra mensal média; "
        "não é recomendação financeira personalizada)\n"
    )

    return text
