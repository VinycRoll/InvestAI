#!/bin/sh

mkdir -p /data
chmod 777 /data

exec su -s /bin/sh app -c "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
