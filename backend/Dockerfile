# ============================================================
# InvestIA - Backend (FastAPI)
#
# Serviço dedicado para deploy no Railway.
# Usa a variável de ambiente $PORT fornecida pelo Railway.
# SQLite persistido via Railway Volume em /data.
# ============================================================

FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN adduser --system --group --home /nonexistent app \
    && mkdir -p /data \
    && chown -R app:app /app /data

USER app

EXPOSE 8000

CMD python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
