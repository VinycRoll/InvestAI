#!/bin/bash
# Para o backend e o frontend do InvestIA.
# Uso: ./parar.sh
pkill -f "uvicorn backend.main" 2>/dev/null
pkill -f "streamlit run frontend/app.py" 2>/dev/null
echo "✅ Processos do InvestIA encerrados (se estavam rodando)."
exit 0