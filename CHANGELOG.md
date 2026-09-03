# Changelog

All notable changes to InvestIA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - FASE 6 & 7 (testabilidade e qualidade)

### Added
- **Tests**: `tests/test_phase6.py` com 50 casos offline (parsers, análise, auth,
  status codes, upload, export, Gemini mockado, `escape_html`) usando banco temporário
  e Gemini simulado. Total do projeto: **188 testes coletados** (158 executáveis offline).
- **Security**: middleware de security headers (`X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`) em `backend/main.py`.
- **DevOps**: healthchecks de Docker baseados em `urllib` (sem dependência de `curl`).

### Fixed
- **DevOps (Dockerfile)**: imagem multi-stage roda como usuário **não-root** (`app`),
  prepara `/app/data` com permissões, copia `.streamlit/config.toml` no frontend.
- **DevOps (compose)**: removido volume nomeado morto `data:`; volume persistente
  `investia_data:/app/data`; healthcheck da API e do frontend.
- **DevOps (CI)**: `test.yml` passou a instalar deps de backend **e** frontend, rodar
  `ruff` em `backend frontend tests alembic`, `compileall`, `pytest` e `docker build`;
  `deploy.yml` agora usa a Railway CLI real (antes usava placeholders `echo`).
- **DevOps (alembic)**: migration baseline criava nada (`pass`); recriada para gerar o
  schema inicial completo (incl. `user_categories`, antes ausente). `env.py` passou a
  importar `UserCategory` e usar `DATABASE_URL`. `alembic upgrade head`/`check`/`downgrade`
  validados contra banco novo.
- **Deps**: removidas dependências não utilizadas (`aiosqlite` do backend, `pandas` do frontend).

### Changed
- **Docs**: README, CHANGELOG e RELATORIO_AUDITORIA atualizados para refletir o estado real.

## [2.0.0] - 2026-08-29

### Added
- **Security**: JWT_SECRET moved to `.env` via `os.getenv()`
- **Security**: CORS restricted to specific origins via env var
- **Security**: Upload size limit (10MB)
- **Security**: Email validation regex
- **Security**: Security headers (X-Content-Type-Options, X-Frame-Options)
- **DevOps**: Alembic migrations with baseline
- **DevOps**: Multi-stage Dockerfile
- **DevOps**: docker-compose.yml with backend + frontend
- **DevOps**: Procfile for Railway/Heroku
- **DevOps**: Health check endpoint (API, DB, Gemini)
- **DevOps**: `.env.example` with all required variables
- **Features**: PDF parser extracts transactions from tables + text
- **Features**: Categorization expanded to 150+ keywords, new categories (vestuario, pets, casa)
- **Features**: Monthly comparison with delta %
- **Features**: High-expense alerts (gasto > 1.5x média)
- **Features**: Smarter investment suggestion (80% of monthly surplus)
- **Features**: Savings rate clamped 0-100%
- **Frontend**: Premium dark theme with glassmorphism
- **Frontend**: Custom Streamlit theme (.streamlit/config.toml)
- **Frontend**: Dashboard with KPI cards, donut charts, alerts
- **Frontend**: Modern login page with branding
- **Tests**: 54 unit tests (analysis, auth, export)
- **Tests**: 8 integration tests (API endpoints)

### Fixed
- **Bug**: CSV parser reading file twice (removed duplicate pandas.read_csv)
- **Bug**: PDF parser workbook close before sheetnames access
- **Bug**: Gemini empty response handling (check candidates exists)
- **Bug**: Netflix categorization (removed "net" from moradia keywords)
- **Bug**: "gas" keyword matching "drogasil" (renamed to "gasnatural", "gas de cozinha")
- **Bug**: datetime.utcnow() → datetime.now(timezone.utc) deprecation
- **Bug**: Unused imports removed (json, datetime, passlib in auth.py)

### Changed
- **Gemini**: System prompt rewritten for objectivity (150-400 words, no intro)
- **Gemini**: maxOutputTokens = 2048, temperature = 0.6
- **Auth**: JWT secret from env, email validation, simplified login

## [1.0.0] - 2026-08-28

### Added
- Initial FastAPI backend with upload, analysis, chat, reports
- SQLite database with users, files, analyses, chat_messages
- OFX, CSV, XLSX, PDF parsers
- Gemini 3.5 Flash integration
- JWT authentication (simplified)
- Streamlit frontend (Dashboard, Upload, Analysis, Chat, Reports)
- HTML, CSV, JSON export
- Basic categorization (alimentacao, moradia, transporte, saude, educacao, lazer, assinaturas, transferencias, investimentos)
- Plotly charts (pie, bar)
- Recurring expenses detection
- Investment suggestion based on surplus

### Security
- API key in .env (gitignored)
- Basic input validation