import json
from datetime import datetime

import markdown
from jinja2 import Environment, select_autoescape

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1e293b; background: #f8fafc; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px;
            border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { color: #059669; border-bottom: 3px solid #10b981; padding-bottom: 12px; font-size: 28px; }
        h2 { color: #047857; margin-top: 30px; font-size: 20px; }
        .meta { color: #64748b; font-size: 13px; margin-bottom: 20px; }
        .metrics { display: flex; gap: 16px; margin: 20px 0; }
        .metric { flex: 1; padding: 20px; background: #f0fdf4; border-radius: 10px; text-align: center;
            border: 1px solid #bbf7d0; }
        .metric .value { font-size: 26px; font-weight: bold; }
        .metric .label { font-size: 12px; color: #64748b; margin-top: 6px; text-transform: uppercase;
            letter-spacing: 0.5px; }
        .positive { color: #059669; }
        .negative { color: #dc2626; }
        .neutral { color: #0284c7; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f1f5f9; font-weight: 600; color: #475569; font-size: 13px; text-transform: uppercase;
            letter-spacing: 0.5px; }
        td { font-size: 14px; }
        tr:hover { background: #f8fafc; }
        .ai-analysis { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px;
            border-radius: 0 8px 8px 0; margin: 20px 0; }
        .ai-analysis h3 { color: #1d4ed8; margin-top: 0; }
        .ai-analysis p, .ai-analysis li { line-height: 1.7; }
        .section { margin-bottom: 25px; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px;
            font-weight: 600; }
        .badge-green { background: #dcfce7; color: #166534; }
        .badge-blue { background: #dbeafe; color: #1e40af; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 11px;
            color: #94a3b8; text-align: center; }
        ul { padding-left: 20px; }
        li { margin: 6px 0; line-height: 1.6; }
        strong { color: #0f172a; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 InvestIA - Relatório Financeiro</h1>
        <p class="meta">Gerado em: {{ date }} {% if file_type %} | Arquivo: {{ file_type }}{% endif %}</p>

        {% if income > 0 or expenses > 0 %}
        <div class="metrics">
            <div class="metric">
                <div class="value positive">R$ {{ "{:,.2f}".format(income) }}</div>
                <div class="label">Receitas</div>
            </div>
            <div class="metric">
                <div class="value negative">R$ {{ "{:,.2f}".format(expenses) }}</div>
                <div class="label">Despesas</div>
            </div>
            <div class="metric">
                <div class="value {% if balance >= 0 %}positive{% else %}negative{% endif %}">
                    R$ {{ "{:,.2f}".format(balance) }}
                </div>
                <div class="label">Saldo</div>
            </div>
        </div>
        {% endif %}

        {% if categories %}
        <div class="section">
            <h2>📂 Categorização de Gastos</h2>
            <table>
                <tr><th>Categoria</th><th>Qtd</th><th>Total</th><th>%</th></tr>
                {% for cat, data in categories.items() %}
                <tr>
                    <td><strong>{{ cat|capitalize }}</strong></td>
                    <td>{{ data.count }}</td>
                    <td>R$ {{ "{:,.2f}".format(data.total) }}</td>
                    <td>{{ "%.1f"|format(data.total / total_expenses * 100 if total_expenses > 0 else 0) }}%</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}

        {% if top_expenses %}
        <div class="section">
            <h2>💸 Top Maiores Despesas</h2>
            <table>
                <tr><th>#</th><th>Descrição</th><th>Data</th><th>Valor</th></tr>
                {% for exp in top_expenses %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ exp.description or 'N/D' }}</td>
                    <td>{{ exp.date[:10] if exp.date else 'N/D' }}</td>
                    <td class="negative">R$ {{ "{:,.2f}".format(exp.amount|abs) }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}

        {% if recurring %}
        <div class="section">
            <h2>🔄 Gastos Recorrentes</h2>
            <table>
                <tr><th>Descrição</th><th>Frequência</th><th>Média</th><th>Total</th></tr>
                {% for rec in recurring %}
                <tr>
                    <td>{{ rec.description }}</td>
                    <td><span class="badge badge-blue">{{ rec.count }}x</span></td>
                    <td>R$ {{ "{:,.2f}".format(rec.avg_amount) }}</td>
                    <td>R$ {{ "{:,.2f}".format(rec.total) }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}

        {% if suggested_investment > 0 %}
        <div class="section">
            <h2>💡 Capacidade de Investimento (Estimativa)</h2>
            <div class="metric" style="max-width: 300px;">
                <div class="value neutral">R$ {{ "{:,.2f}".format(suggested_investment) }}</div>
                <div class="label">Investimento Mensal Sugerido</div>
            </div>
            <p style="font-size: 12px; color: #64748b;">
                Estimativa baseada em 80% da sobra mensal média. Não é recomendação financeira personalizada.
            </p>
        </div>
        {% endif %}

        {% if ai_analysis %}
        <div class="section">
            <h2>🤖 Análise da IA</h2>
            <div class="ai-analysis">
                {{ ai_html|safe }}
            </div>
        </div>
        {% endif %}

        <div class="footer">
            <p><strong>InvestIA</strong> - Analisador Financeiro Inteligente</p>
            <p>Este relatório é apenas informativo. Consulte um assessor financeiro antes de
                tomar decisões de investimento.</p>
        </div>
    </div>
</body>
</html>
"""


class ExportService:
    @staticmethod
    def generate_html_report(analysis: dict, ai_analysis: str = "", file_info: dict = None) -> str:
        env = Environment(autoescape=select_autoescape(["html"]))
        template = env.from_string(REPORT_TEMPLATE)

        ai_html = ""
        if ai_analysis:
            try:
                ai_html = markdown.markdown(ai_analysis, extensions=["tables", "fenced_code"])
            except Exception:
                ai_html = "<p>" + ai_analysis.replace("\n", "<br>") + "</p>"

        total_expenses = analysis.get("total_expenses", 0)

        return template.render(
            date=datetime.now().strftime("%d/%m/%Y %H:%M"),
            file_type=(file_info or {}).get("filename", ""),
            income=analysis.get("total_income", 0),
            expenses=total_expenses,
            balance=analysis.get("balance", 0),
            categories=analysis.get("categories", {}),
            total_expenses=total_expenses,
            top_expenses=analysis.get("top_expenses", []),
            recurring=analysis.get("recurring_expenses", []),
            suggested_investment=analysis.get("suggested_investment", 0),
            ai_analysis=ai_analysis,
            ai_html=ai_html,
        )

    @staticmethod
    def generate_csv_data(analysis: dict, ai_analysis: str = "") -> str:
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        writer.writerow(["InvestIA - Relatório Financeiro"])
        writer.writerow([f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
        writer.writerow([])

        income = analysis.get("total_income", 0)
        expenses = analysis.get("total_expenses", 0)
        balance = analysis.get("balance", 0)

        if income or expenses:
            writer.writerow(["Resumo"])
            writer.writerow(["Receitas", f"R$ {income:,.2f}"])
            writer.writerow(["Despesas", f"R$ {expenses:,.2f}"])
            writer.writerow(["Saldo", f"R$ {balance:,.2f}"])
            writer.writerow([])

        categories = analysis.get("categories", {})
        if categories:
            writer.writerow(["Categoria", "Quantidade", "Total", "Porcentagem"])
            for cat, data in categories.items():
                pct = (data["total"] / expenses * 100) if expenses > 0 else 0
                writer.writerow([cat, data["count"], f"R$ {data['total']:,.2f}", f"{pct:.1f}%"])
            writer.writerow([])

        top = analysis.get("top_expenses", [])
        if top:
            writer.writerow(["Top Despesas"])
            writer.writerow(["Descrição", "Data", "Valor"])
            for exp in top:
                writer.writerow([
                    exp.get("description", "N/D") or "N/D",
                    (exp.get("date") or "")[:10],
                    f"R$ {abs(exp.get('amount', 0)):,.2f}",
                ])
            writer.writerow([])

        recurring = analysis.get("recurring_expenses", [])
        if recurring:
            writer.writerow(["Gastos Recorrentes"])
            writer.writerow(["Descrição", "Frequência", "Média", "Total"])
            for rec in recurring:
                writer.writerow([
                    rec.get("description", ""),
                    f"{rec.get('count', 0)}x",
                    f"R$ {rec.get('avg_amount', 0):,.2f}",
                    f"R$ {rec.get('total', 0):,.2f}",
                ])
            writer.writerow([])

        suggested = analysis.get("suggested_investment", 0)
        if suggested:
            writer.writerow(["Capacidade de Investimento (Estimativa)"])
            writer.writerow(["Valor mensal sugerido", f"R$ {suggested:,.2f}"])
            writer.writerow(["Nota", "Estimativa baseada em 80% da sobra mensal média."])
            writer.writerow(["", "Não é recomendação financeira personalizada."])
            writer.writerow([])

        if ai_analysis:
            writer.writerow(["Análise da IA"])
            writer.writerow([ai_analysis])

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(data: dict, ai_text: str = "", file_info: dict = None) -> bytes:
        from weasyprint import HTML

        ai_html = ""
        if ai_text:
            try:
                ai_html = markdown.markdown(ai_text, extensions=["tables", "fenced_code"])
            except Exception:
                ai_html = "<p>" + ai_text.replace("\n", "<br>") + "</p>"

        total_expenses = data.get("total_expenses", 0)

        html_content = REPORT_TEMPLATE
        env = Environment(autoescape=select_autoescape(["html"]))
        template = env.from_string(html_content)
        rendered = template.render(
            date=datetime.now().strftime("%d/%m/%Y %H:%M"),
            file_type=(file_info or {}).get("filename", ""),
            income=data.get("total_income", 0),
            expenses=total_expenses,
            balance=data.get("balance", 0),
            categories=data.get("categories", {}),
            total_expenses=total_expenses,
            top_expenses=data.get("top_expenses", []),
            recurring=data.get("recurring_expenses", []),
            suggested_investment=data.get("suggested_investment", 0),
            ai_analysis=ai_text,
            ai_html=ai_html,
        )

        return HTML(string=rendered).write_pdf()

    @staticmethod
    def generate_json_report(result: dict) -> str:
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
