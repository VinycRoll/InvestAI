# ============================================================
# InvestIA - Multi-stage build
#
# Targets:
#   backend  -> API FastAPI (porta 8000)
#   frontend -> Streamlit UI (porta 8501)
#
# Ambos executam como usuário não-root ("app") e o SQLite do
# backend é persistido via volume em /app/data (definido no
# docker-compose.yml).
# ============================================================

# ------------------------------------------------------------
# Stage 1: Backend
# ------------------------------------------------------------
FROM python:3.11-slim AS backend

WORKDIR /app

# Dependências primeiro para aproveitar cache de build.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código da API + migrations.
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Executa como usuário não-root e prepara o diretório persiste nte.
RUN adduser --system --group --home /nonexistent app \
    && mkdir -p /app/data \
    && chown -R app:app /app

# Porta padrão (overridável em produção via $PORT / docker-compose).
EXPOSE 8000

USER app

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------
# Stage 2: Frontend
# ------------------------------------------------------------
FROM python:3.11-slim AS frontend

WORKDIR /app

COPY frontend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Interface + tema customizado (.streamlit/config.toml).
COPY frontend/ ./frontend/
COPY .streamlit/ ./.streamlit/

RUN adduser --system --group --home /nonexistent app \
    && chown -R app:app /app

EXPOSE 8501

USER app

CMD ["python", "-m", "streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]