#!/bin/bash

echo "🚀 Iniciando InvestIA..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instale Python 3.10+"
    exit 1
fi

# Create virtualenv
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "📦 Instalando dependências do backend..."
pip install -r backend/requirements.txt -q

echo "📦 Instalando dependências do frontend..."
pip install -r frontend/requirements.txt -q

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Edite o arquivo .env com sua GEMINI_API_KEY"
fi

echo ""
echo "✅ Dependências instaladas!"
echo ""
echo "Para iniciar:"
echo "  Terminal 1 (Backend):  source venv/bin/activate && uvicorn backend.main:app --reload --port 8000"
echo "  Terminal 2 (Frontend): source venv/bin/activate && streamlit run frontend/app.py --server.port 8501"
echo ""
echo "Ou use: ./start.sh para iniciar ambos"
