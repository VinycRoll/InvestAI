# ============================================================
# InvestIA - Frontend (Streamlit)
#
# Serviço dedicado para deploy no Railway.
# Usa a variável de ambiente $PORT fornecida pelo Railway.
# ============================================================

FROM python:3.11-slim

WORKDIR /app

COPY frontend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/ ./frontend/
COPY .streamlit/ ./.streamlit/

RUN adduser --system --group --home /nonexistent app \
    && chown -R app:app /app

USER app

EXPOSE 8501

CMD streamlit run frontend/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
