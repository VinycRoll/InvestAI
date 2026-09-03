# InvestIA v2 - Plano de Projeto

## Visão Geral
Aplicativo de análise financeira pessoal com IA. Analisa extratos bancários e planilhas, categoriza gastos, recomenda investimentos e permite chat com assistente financeiro. Projeto elevado a nível **production-ready** em 6 fases (29/08/2026).

## Stack
| Camada | Tecnologia |
|--------|-----------|
| Backend API | Python + FastAPI |
| Frontend UI | Streamlit + HTML/CSS premium dark theme |
| IA | Google Gemini 3.5 Flash |
| Banco | SQLite + SQLAlchemy + Alembic |
| Auth | JWT (python-jose, bcrypt, SECRET_KEY obrigatório no .env) |
| Parsing | ofxparse, openpyxl, pdfplumber, pandas |
| Gráficos | Plotly (donut, barras, line, heatmap) |
| Export | HTML (Jinja2 + markdown), CSV, JSON, PDF (WeasyPrint) |
| Testes | pytest (90 testes) |
| Deploy | Docker (multi-stage), docker-compose, Procfile, Railway |
| CI/CD | GitHub Actions (test + deploy workflows) |
| Lint | Ruff (line-length=120) |

## Status do Projeto (31/08/2026)

### ✅ Fase 1: Segurança e Bugs Críticos — Concluída
- `JWT_SECRET` movido para `.env` via `os.getenv()` (`backend/auth.py:11`)
- Validação de email com regex, `validate_email()` (`backend/auth.py:79`)
- CORS restritivo via `CORS_ORIGINS` no `.env`, métodos restritos GET/POST/DELETE (`backend/main.py:23`)
- Limite upload 10MB (`MAX_FILE_SIZE`, `backend/main.py:32` + 413)
- Sanitização nome arquivo, headers segurança (X-Content-Type-Options, X-Frame-Options)
- Correções: CSV lido 2x removido (`parsers/excel_parser.py`), Gemini resposta vazia tratada (`services/gemini.py:61` checa `candidates`), `datetime.utcnow()` → `datetime.now(timezone.utc)`, imports não usados removidos, `savings_rate` clamp 0-100% (`services/analysis.py:192`), keyword "gas" → "gasnatural"/"gas de cozinha" (evita casar "drogasil"), "net" removido de moradia (evita casar Netflix)

### ✅ Fase 2: Infraestrutura e DevOps — Concluída
- Alembic inicializado, baseline `fe96d7ea4f1b_baseline_schema.py` (`alembic/`)
- `Dockerfile` multi-stage, `docker-compose.yml` (backend+frontend), `Procfile`, `.dockerignore`
- `.env.example` atualizado com todas as vars (`GEMINI_API_KEY`, `JWT_SECRET`, `CORS_ORIGINS`)
- Health check aprimorado (`GET /api/health` checa API, DB via `SELECT 1`, Gemini configured) (`backend/main.py:361`)
- **CI/CD GitHub Actions**: `.github/workflows/test.yml` (Python 3.11, ruff, pytest) + `.github/workflows/deploy.yml` (Railway placeholder)
- **Ruff lint**: `pyproject.toml` configurado (line-length=120, E/W/F/I/B/UP rules)
- **mypy**: configurado em `pyproject.toml` (Python 3.11, ignore_missing_imports)
- **Railway**: `railway.json` criado (Nixpacks, uvicorn, ON_FAILURE restart)

### ✅ Fase 3: Funcionalidades Profissionais — Concluída
- `parsers/pdf_parser.py` extrai transações de tabelas + texto, normaliza datas DD/MM/YYYY
- `services/analysis.py` expandido para ~160 keywords, 12 categorias (novas: vestuario, pets, casa)
- `analyze_transactions()` agora retorna: `categories`, `top_expenses`, `recurring_expenses`, `monthly_data`, `monthly_comparison` (delta % mês a mês), `alerts` (gasto >1.5x média), `suggested_investment` (80% da sobra mensal), `savings_rate` clamp, `avg_monthly_*`, `daily_data`
- `services/gemini.py` prompt reescrito para objetividade (150-400 palavras, sem auto-apresentação), `maxOutputTokens=2048`, `temperature=0.6`
- Bug Netflix categorização corrigido
- **PDF Export**: WeasyPrint com template HTML (KPIs, categorias, top despesas, análise IA) (`backend/services/export.py`)
- **Custom Categories**: `UserCategory` table + API endpoints (GET/POST/DELETE `/api/categories`) (`backend/database.py`, `backend/main.py`)
- **Category Learning**: `categorize_transaction()` aceita `user_categories` parameter, verifica categorias user-defined antes das built-in (`backend/services/analysis.py`)

### ✅ Fase 4: UX e Design Premium — Concluída
- Referências: Assetico (dark + electric blue #1938FF), Zenvest (glassmorphism), Payno, FinSight, Crystal Intelligence
- `.streamlit/config.toml` tema dark (`primaryColor #6C63FF`, `backgroundColor #0A0A0F`, `textColor #E8E8ED`, font Inter)
- `frontend/app.py` reescrito completo: paleta dark (`#0A0A0F`→`#12121A` fundo, `#1A1A25` cards, `#6C63FF` accent, `#00D4AA`/`#FF4757`), Inter via Google Fonts, sidebar com avatar + navegação estilizada, login com card glassmorphism, dashboard com KPIs + donut Plotly, upload grid colorido, chat com quick questions, relatórios com cards
- CSS premium: `stMetric` cards com hover, `stButton` gradiente, inputs com `border-radius 12px`, etc.
- **Sidebar arrows fix**: CSS selector agora exclui button/span dentro de sidebar collapse controls — ícones renderizam como `»`/`«`
- **Mobile responsiveness**: `@media (max-width: 768px)` — single column, smaller fonts, full-width metric cards
- **Skeleton loading**: `skeleton_loader(count, cols)` com CSS pulse animation para dashboard, analysis, upload
- **Toast notifications**: `toast(message, type)` — slide-in auto-dismiss (5s), 4 tipos (success/error/warning/info)
- **Settings page**: `settings_page()` — user info, change password, delete account. Added to sidebar nav
- **Logo optimization**: base64 cached in `st.session_state`
- **Dark/Light theme toggle**: sidebar toggle switches CSS variables, stored in session_state
- **Onboarding**: `onboarding_check()` — welcome modal on first login with 3 steps

### ✅ Fase 5: Testes e Qualidade — Concluída (90 testes passando)
- `tests/__init__.py`, `tests/test_analysis.py` (27 testes), `tests/test_auth.py` (19 testes), `tests/test_export.py` (17 testes)
- `tests/test_api.py` — fixed integration tests: rate limiting, refresh token, auth register/login with password, protected endpoints
- `tests/test_e2e.py` — Playwright E2E tests (login, register, navigation) — skip if not installed
- `tests/test_stress.py` — 50 concurrent health checks with threading.Barrier, p95 latency, throughput
- Bug real encontrado: "gas" casava "drogasil" → corrigido e teste ajustado para `COMPRA DROGARIA SAO PAULO`
- Rodar: `python3 -m pytest tests/ -v`

### ✅ Fase 6: Documentação — Concluída
- `README.md` novo (stack, features, setup, estrutura, API table, testes, licença)
- `LICENSE` MIT, `CHANGELOG.md` (1.0.0 → 2.0.0 com Added/Fixed/Changed), `CONTRIBUTING.md` (conventional commits, ruff, pytest)
- `backend/main.py` documentado com OpenAPI: `FastAPI(title, description, contact, license_info)` + `summary`/`description` em todas as rotas
- `MEMORY.md` atualizado (este arquivo)

### ✅ Branding & Login (29/08/2026)
- Logo fornecida `image.png` (657KB) copiada para `frontend/logo.png`
- `frontend/app.py:1-12` adicionado `import base64, Path` + helper `_get_logo_b64()` que lê `frontend/logo.png` (fallback para `image.png`) e retorna base64; fallback para emoji 💎 se não existir
- `login_page()` agora usa `<img src="data:image/png;base64,{_b64}" style="width:220px;max-width:80vw;...filter:drop-shadow...">`
- Espaço vazio entre subtítulo e "Entrar": `separator` 1px + `.stForm` estilizado como card

### ✅ Auditoria Independente (31/08/2026) — 14 itens corrigidos
- **CRIT #1**: `backend/parsers/excel_parser.py` — CSV e XLSX agora retornam `transactions` com detecção automática de colunas (data/descrição/valor) por nome de coluna + heurísticas de formato. Normalizados para `{date, description, amount}` igual ao OFX.
- **CRIT #2**: `backend/auth.py` — passlib removido (biblioteca morta), substituído por `bcrypt` direto. `requirements.txt` atualizado (`bcrypt>=4.0.0`).
- **CRIT #3**: `backend/auth.py` — `JWT_SECRET` obrigatório. `os.getenv("JWT_SECRET")` sem fallback → `raise RuntimeError` se não configurado.
- **ALTO #4**: `frontend/app.py` — `API_URL = os.getenv("API_URL", "http://localhost:8000")`.
- **ALTO #5**: `backend/database.py` — `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./investia.db")`.
- **ALTO #6**: `backend/database.py` — Índices `index=True` adicionados em `user_id` e `created_at` em todas as tabelas (User, File, Analysis, ChatMessage, UserCategory). `ondelete="SET NULL"` na FK `file_id` de Analysis.
- **ALTO #7**: `backend/services/gemini.py` — Exceção customizada `GeminiAPIError`. Rotas `/api/analysis`, `/api/chat`, `/api/investment` capturam `GeminiAPIError` e retornam HTTP 502.
- **MED #8**: `backend/services/gemini.py` — Função morta `analyze_financial_data()` removida.
- **MED #9**: `backend/main.py` — Imports `analyze_transactions`, `categorize_transaction` movidos para topo do arquivo. Import duplicado em loop removido.
- **MED #10**: `backend/main.py` — Rate limit store limpa chaves vazias (`del rate_limit_store[key]` quando lista fica vazia).
- **MED #11**: `backend/services/gemini.py` — `httpx.AsyncClient` compartilhado via `_get_client()` (connection pooling).
- **MED #12**: `backend/services/gemini.py` — API key enviada via header `x-goog-api-key` em vez de query string.
- **MED #13**: `backend/database.py` — `from sqlalchemy.orm import declarative_base` (substitui import deprecado `sqlalchemy.ext.declarative`).
- **MED #14**: `backend/database.py` — `ondelete="SET NULL"` na FK `file_id` de Analysis. Índices em todas as tabelas.
- **Testes**: 90 passed, 2 skipped (rate limit + playwright). `pytest tests/ -v`.

### ✅ Auditoria Independente #2 (31/08/2026) — 9 itens corrigidos
- **CRIT #1**: `backend/services/export.py` — XSS armazenado no relatório exportado. `jinja2.Template()` puro (sem autoescape) substituído por `jinja2.Environment(autoescape=select_autoescape(["html"]))`. Campo `ai_html` renderizado com `{{ ai_html|safe }}` para preservar HTML legítimo da IA.
- **CRIT #2**: `frontend/app.py` — XSS no Streamlit. Descrições de transações e nomes de arquivo interpolados em `unsafe_allow_html=True` agora escapados via `html_lib.escape()`. Imports de plotly movidos para topo do arquivo.
- **ALTO #3**: `backend/services/gemini.py` — Falha de rede (timeout, DNS, conexão recusada, JSON inválido) agora capturada com `except httpx.HTTPError` e relançada como `GeminiAPIError`, garantindo que rotas retornem 502 amigável em vez de 500 cru.
- **ALTO #4**: `backend/auth.py` — `validate_password()` agora valida `MAX_PASSWORD_LENGTH = 72` bytes UTF-8 (não caracteres), evitando ValueError do bcrypt com acentos. Mensagem de erro amigável.
- **ALTO #5**: `backend/services/analysis.py` — "magalu", "americanas", "casas bahia" removidos de `vestuario` (duplicados com `casa`). Compras nesses vendedores agora caem corretamente em "casa" (eletrodomésticos/móveis).
- **MED #6**: `backend/services/analysis.py` — `decode_user_categories()` decodifica keywords JSON uma vez antes do loop. `analyze_transactions()` e `get_transactions()` agora passam lista já decodificada, evitando `json.loads()` a cada transação.
- **MED #7**: `backend/services/analysis.py` — Keywords "apple", "google", "microsoft" soltas substituídas por "apple.com", "apple tv", "google play", "microsoft 365" etc. Evita falsos positivos com pagamentos via Apple Pay/Google Pay.
- **MED #8**: `frontend/app.py` — `import plotly.express as px` e `import plotly.graph_objects as go` movidos para topo do arquivo (5 imports redundantes dentro de funções removidos).
- **MED #9**: `backend/auth.py` — `register_user()` e `authenticate_user()` normalizam email com `email.strip().lower()` antes de comparação/gravação, prevenindo contas duplicadas por diferença de case.
- **Testes**: 90 passed, 2 skipped. `pytest tests/ -v`.

### ✅ Fase 7: Segurança Crítica / Bugs Funcionais Graves (01/09/2026) — Concluída
- **SEGREDOS**: `.env` em `.gitignore` (linha 1). Nenhuma credencial hardcoded em código Python (scan `AIza...`, `sk-`, `ghp_`, `xoxb-` limpo). `.env` mantido (docker-compose usa `env_file: .env`). **Não** revoguei a chave no provedor.
- **JWT (crítico)** `backend/auth.py`: `get_current_user` agora **rejeita refresh token como access token** — adicionada checagem `payload.get("type") == "access"`. Antes, refresh token (7 dias) valia em todos os endpoints protegidos. Mesma lógica no endpoint `/api/auth/refresh`. `sub` não numérico: antes `int(user_id)` → ValueError → HTTP 500; agora 401. Já correto: `algorithms=[ALGORITHM]` fixo (HS256 não manipulável), secret via env obrigatória. Formato dos tokens inalterado.
- **UPLOAD (crítico)** `backend/main.py`: antes lia corpo inteiro em memória antes de checar limite. Agora lê em **chunks de 1MB** e rejeita com 413 assim que excede `MAX_FILE_SIZE` (10MB), sem carregar arquivo grande. Formatos preservados (CSV, XLS, XLSX, PDF, OFX).
- **IDOR** `backend/main.py`: todos os endpoints com IDs já filtravam `user_id`. Reforço em `export_report` — busca do arquivo agora filtra `FileModel.user_id == user.id`.
- **XSS** `frontend/app.py`: escapados valores de origem user/DB/arquivo em `unsafe_allow_html`: `file_type` (lista de arquivos), `rec['description']` (recorrentes), `cat['name']` + `keywords_str` (categorias). Chat e IA já usavam `st.markdown` sem `unsafe_allow_html` (seguros). Nomes de arquivo, transações, filename do chat já escapados.
- **Exceção silenciosa** `frontend/app.py`: `download_report` tinha `except Exception: pass` que engolia tudo → agora mostra `st.error` com mensagem (sem expor secrets).
- **PDF MIME (bug confirmado)** `frontend/app.py`: `mime_map` não tinha `pdf` mas a página de relatórios chama `download_report(id, "pdf")` → KeyError silencioso. Adicionado `"pdf": "application/pdf"`.
- **CSV EXPORT (bug confirmado)** `backend/services/export.py`: montagem manual por f-string `f"{description},{value}"` quebrava colunas com vírgulas/aspas. Substituído por **`csv.writer` + `io.StringIO`** (`lineterminator="\n"`) — aspas, vírgulas, acentos, quebra de linha e negativos corretos.
- **DOCKER DB (bug confirmado)** `docker-compose.yml`: volume montava `./data:/app/data`, mas SQLite default `sqlite:///./investia.db` → `/app/investia.db` fora do volume. Adicionado `DATABASE_URL=sqlite:////app/data/investia.db`. Nenhuma migração de banco.
- **ALEMBIC**: **sem mudança**. `init_db()` (create_all) é idempotente/não destrói; migrações existentes têm `upgrade()` quase vazio (`pass`). Remover quebraria bootstrap/tests. Migração total = fase futura. **Risco documentado**.
- **Verificações manuais**: JWT live (refresh 401, access 200), upload live (CSV 200, 11MB 413), CSV com vírgulas/aspas. 90 passed, 2 skipped. `compileall` OK. **ruff não instalado** (não instalei).
- **Validação**: `python -m compileall backend frontend tests alembic` OK; `pytest -q` → 90 passed, 2 skipped.

### ✅ Implementado e Funcionando (Resumo)
- Backend FastAPI completo, DB SQLite, parsers OFX/CSV/XLSX/PDF, Gemini 3.5 Flash, JWT, Streamlit 7 páginas (login, dashboard, analysis, chat, categorias, reports, settings), categorização 12 categorias + custom, análise com métricas avançadas, chat conectado a dados financeiros, dashboard Plotly (donut + line + heatmap), relatórios HTML/CSV/JSON/PDF com exclusão, Docker, 90 testes, docs, OpenAPI, logo, login premium, mobile responsive, skeleton loading, toast notifications, dark/light toggle funcional, onboarding, rate limiting, refresh token, CI/CD, categorias personalizadas, aprendizado de categorias, atribuição manual de categorias na análise

### ⚠️ Parcialmente / Não Implementado
- OAuth Google/GitHub ainda simplificado por email
- Deploy Railway pendente (Docker + CI/CD prontos)
- Logo ainda 657KB (precisa otimizar para ~100KB WebP)

## Como Rodar
```bash
cd "Área de trabalho/InvestAI"

# Dependências
pip3 install -r backend/requirements.txt
pip3 install -r frontend/requirements.txt  # se existir
pip install pytest  # para testes

# Backend (Terminal 1)
python3 -m uvicorn backend.main:app --port 8000
# ou: nohup python3 -m uvicorn backend.main:app --port 8000 &

# Frontend (Terminal 2)
python3 -m streamlit run frontend/app.py --server.port 8501 --server.headless true
# ou: nohup python3 -m streamlit run frontend/app.py --server.port 8501 --server.headless true &

# Docker
docker compose up --build

# Testes
python3 -m pytest tests/ -v
# 63 testes (unitários + integração + E2E + stress)

# Lint
python3 -m ruff check backend/
```
### Links
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/api/health

### Configuração
- `.env` com `GEMINI_API_KEY=AQ.Ab8RN6Kq...` (já configurado, protegido por .gitignore), `JWT_SECRET=mude-esta-secret-em-producao`, `CORS_ORIGINS`
- `.env.example` template, `.gitignore` protege `.env`, `__pycache__`, `*.db`
- `frontend/logo.png` (cópia de `image.png`, 657KB, servida via base64 data URI, cached em session_state)
- `pyproject.toml` — ruff (line-length=120), mypy (Python 3.11), pytest (testpaths=["tests"])

## Estrutura de Arquivos (Atual)
```
InvestAI/
├── backend/
│   ├── main.py              ← FastAPI + OpenAPI + rate limiting + refresh token + custom categories
│   ├── database.py          ← SQLite + SQLAlchemy + UserCategory table
│   ├── auth.py              ← JWT + validate_email + refresh token
│   ├── parsers/
│   │   ├── ofx_parser.py
│   │   ├── excel_parser.py
│   │   └── pdf_parser.py    ← tabelas + texto
│   ├── services/
│   │   ├── gemini.py        ← tuned prompt
│   │   ├── analysis.py      ← 160 keywords, monthly_comparison, alerts, user_categories support
│   │   └── export.py        ← HTML/CSV/JSON/PDF (WeasyPrint)
│   └── requirements.txt
├── frontend/
│   ├── app.py               ← premium dark + logo + skeleton + toast + settings + theme toggle + onboarding + mobile
│   ├── logo.png             ← logo InvestAI (copia image.png)
│   └── requirements.txt
├── tests/
│   ├── __init__.py
│   ├── test_analysis.py     ← 27 testes
│   ├── test_auth.py         ← 19 testes
│   ├── test_export.py       ← 17 testes
│   ├── test_api.py          ← integração (rate limit, refresh token, auth, protected endpoints)
│   ├── test_e2e.py          ← Playwright E2E (login, register, navigation)
│   └── test_stress.py       ← 50 concurrent health checks
├── .github/workflows/
│   ├── test.yml             ← CI: Python 3.11, ruff, pytest
│   └── deploy.yml           ← CD: Railway deploy (placeholder)
├── .streamlit/config.toml   ← tema dark
├── alembic/                 ← migrations + password_hash migration
├── pyproject.toml           ← ruff + mypy + pytest config
├── railway.json             ← Railway deploy config
├── Dockerfile + docker-compose.yml + Procfile + .dockerignore
├── image.png + image copy.png ← logo original + screenshot referência
├── MEMORY.md                ← este arquivo
├── PLANO_ACAO.md            ← 6 fases
├── README.md + CHANGELOG.md + LICENSE + CONTRIBUTING.md
├── RELATORIO_AUDITORIA.md + auditor.md
└── .env / .env.example
```

## API Routes
```
POST   /api/auth/register     # Registro (email, name, password)
POST   /api/auth/login        # Login (email, password → JWT + refresh_token)
POST   /api/auth/refresh      # Refresh token (refresh_token → new access_token)
GET    /api/auth/me            # Usuário atual
POST   /api/upload             # Upload OFX/QFX/CSV/XLSX/PDF (10MB)
GET    /api/files              # Listar arquivos
DELETE /api/files/{id}         # Remover
POST   /api/analysis           # Análise (file_id + user_context)
GET    /api/analysis/history   # Histórico 50
POST   /api/investment         # Recomendação (profile, amount, categories)
POST   /api/chat               # Chat (message, file_id)
GET    /api/chat/history       # Histórico 100
POST   /api/reports/export     # Export HTML/CSV/JSON/PDF
GET    /api/dashboard/summary  # Contadores + last_analysis
GET    /api/categories         # Listar categorias personalizadas
POST   /api/categories         # Criar categoria (name, keywords)
DELETE /api/categories/{id}    # Excluir categoria
GET    /api/health             # Health check
```

## Database Schema
```sql
CREATE TABLE users (id, email UNIQUE, name, password_hash, avatar_url, provider, created_at);
CREATE TABLE files (id, user_id, filename, file_type, file_size, parsed_data JSON, created_at);
CREATE TABLE analyses (id, user_id, file_id, analysis_type, result JSON, created_at);
CREATE TABLE chat_messages (id, user_id, role, content, created_at);
CREATE TABLE user_categories (id, user_id, name, keywords JSON, created_at);
```

## Bugs Conhecidos (Atualizado)
- ✅ CSV vazio para PDFs: parcialmente corrigido (pdf_parser agora gera transactions)
- ✅ Análises antigas: novas funcionam
- ✅ Netflix/gas categorization: corrigidos
- ✅ Setas sidebar: corrigidas (CSS selector exclusão button/span)
- ✅ Refresh token usado como access token: corrigido (auth.py exige type=="access")
- ✅ Upload lendo corpo inteiro em memória: corrigido (chunked read com 413)
- ✅ PDF download sem MIME: corrigido (mime_map com application/pdf)
- ✅ CSV manual quebrando colunas: corrigido (csv.writer)
- ✅ Volume Docker não persistia SQLite: corrigido (DATABASE_URL=/app/data/investia.db)
- ⚠️ Alembic coexiste com create_all (idempotente, não destrói) — migração total pendente
- ⚠️ OAuth não implementado
- ✅ Testes cobrem regressões (gas/drogasil)

## Sessão 29/08-31/08/2026 — Log Resumido
- **29/08 manhã**: Fases 1-3 (segurança, DevOps, features)
- **29/08 tarde**: Fase 4 design premium (research Assetico/Zenvest/Crystal), reescrita `frontend/app.py`
- **29/08 noite**: Fase 5 testes (62 passando) + Fase 6 docs + Logo + Login premium + Bug setas sidebar
- **31/08**: Implementação completa das 23 melhorias do PLANO_ACAO.md:
  - ✅ #1 Rate limiting login (5/min/IP, in-memory)
  - ✅ #2 Refresh token (15min access + 7d refresh)
  - ✅ #3 Sidebar arrows fix (CSS selector exclusão)
  - ✅ #4 CI/CD GitHub Actions (test + deploy workflows)
  - ✅ #5 Ruff lint + mypy config (pyproject.toml)
  - ✅ #6 Railway deploy config (railway.json)
  - ✅ #7 Integration tests fixed (rate limit, refresh token, auth)
  - ✅ #8 Alembic migration (password_hash column)
  - ✅ #9 PDF export (WeasyPrint)
  - ✅ #10 Mobile responsiveness (media queries)
  - ✅ #11 Skeleton loading states
  - ✅ #12 Toast notifications
  - ✅ #13 Settings page (change password, delete account)
  - ✅ #14 Logo optimization (base64 cached)
  - ✅ #16 Onboarding modal
  - ✅ #17 Dark/Light theme toggle
  - ✅ #18 Trend line chart (Plotly income vs expenses)
  - ✅ #19 Heatmap calendar (Plotly daily spending)
  - ✅ #20 Custom categories API (UserCategory table)
  - ✅ #21 Category learning (user-defined keywords)
  - ✅ #22 E2E tests (Playwright)
  - ✅ #23 Stress tests (50 concurrent, p95 latency)
  - Total: 63 passed, 29 skipped (stress/E2E skip without backend/playwright)

## Sessão 01/09/2026 — Fase 7: Segurança Crítica
- **01/09**: Auditoria de segurança crítica (bugs graves):
  - ✅ SEGREDOS: `.env` confirmado no `.gitignore`; sem credenciais hardcoded no código
  - ✅ JWT: refresh token não pode mais ser usado como access token (checagem `type`)
  - ✅ JWT: `sub` inválido retorna 401 (antes 500 crash)
  - ✅ UPLOAD: chunked read 1MB + 413 (antes corpo inteiro em memória)
  - ✅ IDOR: `user_id` filter em toda busca de recursos
  - ✅ XSS: escape em `file_type`, recorrentes, categorias
  - ✅ Exceção silenciosa: `download_report` mostra erro em vez de `pass`
  - ✅ PDF MIME: `application/pdf` adicionado
  - ✅ CSV: `csv.writer` em vez de f-string manual
  - ✅ Docker: `DATABASE_URL` → `/app/data/investia.db` (volume persiste DB)
  - ✅ Alembic: sem mudança (create_all idempotente), risco documentado
  - Total: 90 passed, 2 skipped. `compileall` OK. ruff não instalado.
