#!/bin/bash

echo "🚀 Iniciando InvestIA..."

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Execute ./install.sh primeiro"
    exit 1
fi

# Check .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Edite .env com sua GEMINI_API_KEY antes de continuar"
    exit 1
fi

# Start backend
echo "🔧 Iniciando Backend (FastAPI)..."
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
echo "🎨 Iniciando Frontend (Streamlit)..."
streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

echo ""
echo "✅ InvestIA rodando!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:8501"
echo "   Docs API: http://localhost:8000/docs"
echo ""
echo "Pressione Ctrl+C para parar"

# Wait for both
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
