# InvestIA v2.0

Análise financeira pessoal com inteligência artificial. Envie extratos bancários (OFX, QFX, CSV, XLSX, XLS, PDF) e receba análises detalhadas, categorização automática, alertas, gastos recorrentes, comparativo mensal e recomendações educacionais de investimento via Google Gemini.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| Frontend | Streamlit |
| IA | Google Gemini (via `GEMINI_API_URL`) |
| Auth | JWT (python-jose, `access` + `refresh`) |
| Migrations | Alembic |
| Deploy | Docker (multi-stage), Railway/Heroku (Procfile) |

## Funcionalidades

- **Upload multi-formato**: OFX, QFX, CSV, XLSX, XLS, PDF (máx. 10MB)
- **Categorização automática**: 150+ keywords em 12 categorias + categorias personalizadas
- **Análise com IA**: Gemini gera insights (disclaimer educacional, sem recomendação personalizada)
- **Comparativo mensal**: Delta % entre meses
- **Alertas inteligentes**: Gastos acima da média
- **Gastos recorrentes**: Identificação automática
- **Taxa de poupança**: Clampada em 0–100%
- **Sugestão de investimento**: 80% da margem mensal (estimativa)
- **Export**: HTML, CSV, JSON e PDF
- **Chat financeiro**: Conversa sobre seus dados e mercado
- **Isolamento entre usuários**: dados restritos ao dono (JWT)

## Setup

### Requisitos

- Python 3.11+
- Google Gemini API key ([obter aqui](https://aistudio.google.com/apikey))

### Instalação local

```bash
git clone https://github.com/seu-usuario/InvestIA.git
cd InvestIA

# Backend
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Frontend (outro venv ou a mesma env, se desejar)
pip install -r frontend/requirements.txt

# Configurar variáveis
cp .env.example .env
# Edite .env com sua GEMINI_API_KEY e JWT_SECRET

# Backend
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (outra aba)
python -m streamlit run frontend/app.py --server.port 8501
```

### Docker

```bash
docker compose up --build
```

Acesse:
- Frontend: `http://localhost:8501`
- API: `http://localhost:8000/docs`

O SQLite é persistido em um volume nomeado (`investia_data`) e o container roda como usuário não-root. Os healthchecks usam `urllib` do próprio Python (a imagem `python:3.11-slim` não tem `curl`).

### Migrations (Alembic)

> A aplicação cria as tabelas automaticamente no primeiro boot (`init_db`). Para evolução controlada de schema, use Alembic:

```bash
# Criar schema em um banco novo e aplicar até o head
DATABASE_URL=sqlite:///./investia.db python -m alembic upgrade head

# Verificar se o schema real diverge dos models
DATABASE_URL=sqlite:///./investia.db python -m alembic check
```

> Para um banco já criado por `create_all` (sem `alembic_version`), reconcilie com `alembic stamp head` **antes** de aplicar novas migrations.

## Estrutura

```
InvestIA/
├── backend/
│   ├── main.py              # Rotas FastAPI + rate limiting + security headers
│   ├── auth.py              # JWT + validação (access/refresh)
│   ├── config.py            # Config centralizada (env)
│   ├── database.py          # Models SQLAlchemy (5 tabelas)
│   ├── parsers/
│   │   ├── excel_parser.py  # CSV/XLSX/XLS (vírgula, BOM, decimal BR)
│   │   ├── ofx_parser.py    # OFX/QFX
│   │   └── pdf_parser.py    # PDF (tabelas + texto)
│   └── services/
│       ├── analysis.py      # Categorização + métricas + comparativo
│       ├── export.py        # HTML/CSV/JSON/PDF
│       └── gemini.py        # Cliente IA (retry, timeout, truncamento)
├── frontend/
│   ├── app.py               # Entrypoint Streamlit (fino)
│   ├── helpers.py
│   ├── services/api.py      # Cliente HTTP centralizado (API_URL via env)
│   ├── components/          # cards, charts, icons, modals, navigation
│   ├── pages/               # dashboard, upload, analysis, chat, categories, settings, reports
│   └── styles/theme.py      # Tema, categorias default
├── tests/                   # 188 testes (ver seção Testes)
├── alembic/                 # Migrations
├── Dockerfile               # multi-stage (backend + frontend), não-root
├── docker-compose.yml
├── .github/workflows/       # CI (lint + testes + build) / Deploy
└── .env.example
```

## API

Todas as rotas, exceto `/api/health`, `/api/auth/login` e `/api/auth/register`, exigem header `Authorization: Bearer <token>`.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Health check (API/DB/Gemini) |
| POST | `/api/auth/register` | Criar conta → access + refresh |
| POST | `/api/auth/login` | Login → access + refresh |
| GET | `/api/auth/me` | Dados do usuário atual |
| POST | `/api/auth/refresh` | Renovar access via refresh token |
| GET | `/api/dashboard/summary` | Resumo do dashboard |
| POST | `/api/upload` | Upload de extrato (OFX/QFX/CSV/XLSX/XLS/PDF) |
| GET | `/api/files` | Listar arquivos (lista ou paginada) |
| GET | `/api/transactions/{file_id}` | Transações com categorias |
| DELETE | `/api/files/{file_id}` | Remover arquivo |
| POST | `/api/analysis` | Criar análise (local + IA) |
| GET | `/api/analysis/history` | Histórico (lista ou paginado) |
| DELETE | `/api/analysis/{analysis_id}` | Excluir análise |
| POST | `/api/investment` | Recomendação educacional de investimento |
| GET | `/api/categories` | Listar categorias personalizadas |
| POST | `/api/categories` | Criar categoria personalizada |
| POST | `/api/categories/learn` | Aprender categorias por atribuição |
| DELETE | `/api/categories/{category_id}` | Excluir categoria |
| POST | `/api/chat` | Chat com IA |
| GET | `/api/chat/history` | Histórico do chat |
| POST | `/api/reports/export` | Exportar relatório (`html`, `csv`, `json`, `pdf`) |

## Testes

Os testes são **determinísticos e offline**: usam `TestClient` + banco temporário + Gemini simulado (nenhuma chamada real à rede). Alguns casos (API ao vivo, Playwright, `weasyprint`) são pulados quando as dependências/execução não estão presentes.

```bash
python -m compileall -q backend frontend tests alembic
ruff check backend frontend tests alembic
pytest -q
```

**188 testes coletados**: 158 executáveis offline (passagem garantida) + 30 pulados por exigirem backend ao vivo/Playwright/`weasyprint`. Os `tests/test_fase2.py` e `tests/test_phase6.py` fornecem integração completa via `TestClient` sem servidor real.

## Variáveis de Ambiente

Veja `.env.example`. As principais:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `GEMINI_API_KEY` | Chave do Gemini (**obrigatória**) | — |
| `JWT_SECRET` | Secret JWT (**obrigatória em produção**) | — |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./investia.db` |
| `CORS_ORIGINS` | Origens permitidas (vírgula) | `localhost:8501,:3000` |
| `API_URL` | URL do backend usada pelo frontend | `http://localhost:8000` |
| `GEMINI_RETRIES` / `GEMINI_RETRY_DELAY` | Retry da IA | `2` / `1.0` |
| `GEMINI_MAX_CONTEXT_LENGTH` | Truncamento de contexto | `60000` |
| `MAX_FILE_SIZE` | Limite de upload | 10MB (constante) |

## Segurança

- CORS restrito por env (`CORS_ORIGINS`)
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- Upload limitado a 10MB com streaming por chunks
- Rate limiting em login/registro (em memória)
- JWT com `type` (`access`/`refresh`), isolamento de dados por usuário
- Secrets lidos de ambiente (nunca no código)

## Licença

MIT