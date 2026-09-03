#!/bin/bash
# Sobe o backend (FastAPI) e o frontend (Streamlit) do InvestIA.
# Uso: ./subir.sh
set -e

cd "$(dirname "$0")"

# Resolve um interpretador do venv que seja DETERMINÍSTICO. Não usamos
# `venv/bin/python` diretamente porque, nesse ambiente, ele é um symlink
# `python3 -> /usr/bin/python3` que pode resolver para o Python do SISTEMA
# (3.12) em vez do do venv (3.13). Preferimos o binário fixo do venv.
PYTHON=""
for cand in "$PWD/venv/bin/python3.13" "$PWD/venv/bin/python3.12"; do
    if [ -x "$cand" ]; then
        PYTHON="$cand"
        break
    fi
done

if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
    echo "venv não encontrado (sem python3.13/3.12 em $PWD/venv)."
    echo "Rode: ls -la $PWD/venv/bin/python*"
    exit 1
fi

# Descobre o diretório de site-packages do venv (ex.: .../lib/python3.13/site-packages).
# Tenta via sysconfig; se falhar, usa o glob de venv/lib/*/site-packages.
SP=$( "$PYTHON" -c "import sysconfig; print(sysconfig.get_path('purelib'))" 2>/dev/null )

if [ -z "$SP" ] || [ ! -d "$SP" ]; then
    SP=$( ls -d "$PWD"/venv/lib/*/site-packages 2>/dev/null | head -n1 )
fi

if [ -z "$SP" ] || [ ! -d "$SP" ]; then
    echo "Não consegui localizar site-packages do venv."
    echo "Rode: ls -d venv/lib/*/site-packages"
    exit 1
fi

# Força o site-packages do venv como PRIMEIRO no sys.path, ignorando
# qualquer interferência de /app ou /var/data que exista no interpretador do sistema.
export PYTHONPATH="$SP"
export PYTHONNOUSERSITE=1

# Pré-valida que o interpretador do venv e as dependências críticas batem.
PV=$( "$PYTHON" -c "import sys; print('%d.%d' % (sys.version_info[0], sys.version_info[1]))" 2>/dev/null )
echo "Interpretador do venv: $PYTHON (Python $PV)"

if ! "$PYTHON" -c "import fastapi, pydantic, pydantic_core, dotenv, uvicorn" 2> /dev/null; then
    echo "❌ O venv (Python $PV) não consegue carregar as dependências críticas."
    echo "   Isso normalmente ocorre quando o interpretador do venv não bate com os"
    echo "   pacotes instalados (ex.: venv de 3.13 sendo executado como 3.12)."
    echo "   Execute manualmente para ver o erro:"
    echo "     $PYTHON -c 'import fastapi, pydantic, pydantic_core, dotenv, uvicorn'"
    exit 1
fi

# Diretório de logs PERSISTENTE do projeto (não em /tmp, que pode ser limpo).
mkdir -p "$PWD/logs"

# Encerra processos órfãos anteriores antes de subir de novo.
# Nota: `pkill` retorna 1 se nada for morto; com `set -e` isso abortaria o
# script silenciosamente, por isso o `|| true`.
pkill -f "uvicorn backend.main" 2>/dev/null || true
pkill -f "streamlit run frontend/app.py" 2>/dev/null || true
sleep 1

echo "🚀 Iniciando InvestIA (site-packages: $SP)..."

echo "🔧 Backend (http://localhost:8000)..."
setsid nohup "$PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    > "$PWD/logs/backend.log" 2>&1 < /dev/null &

echo "🎨 Frontend (http://localhost:8501)..."
setsid nohup "$PYTHON" -m streamlit run frontend/app.py \
    --server.port 8501 --server.address 0.0.0.0 \
    > "$PWD/logs/frontend.log" 2>&1 < /dev/null &

sleep 6

echo ""
echo "✅ Pronto:"
echo "   Frontend: http://localhost:8501"
echo "   Backend : http://localhost:8000"
echo "   Logs:     $PWD/logs/"

exit 0