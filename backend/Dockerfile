FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY backend/start.sh ./start.sh

RUN adduser --system --group --home /nonexistent app \
    && chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
