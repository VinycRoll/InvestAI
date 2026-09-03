# PLANO DE AÇÃO — InvestIA Nível Profissional

**Objetivo:** Transformar o InvestIA de protótipo funcional para aplicação production-ready.

---

## FASE 1: SEGURANÇA E CORREÇÕES CRÍTICAS (1-2 dias)

### 1.1 Autenticação Segura
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Mover SECRET_KEY para `.env` | `auth.py` | Ler `os.getenv("JWT_SECRET")` em vez de hardcoded |
| Adicionar validação de email | `auth.py` | Regex para formato de email válido |
| Implementar refresh token | `auth.py` | Token de acesso (15min) + refresh (7d) |
| Rate limiting no login | `main.py` | Max 5 tentativas/minuto por IP |

### 1.2 Segurança da API
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Configurar CORS restritivo | `main.py` | Origins específicas via `.env` |
| Validar tamanho de upload | `main.py` | Max 10MB por arquivo |
| Sanitizar nomes de arquivo | `main.py` | Prevenir path traversal |
| Adicionar headers de segurança | `main.py` | X-Content-Type-Options, X-Frame-Options |
| Input validation em todas as rotas | `main.py` | Pydantic models completos |

### 1.3 Correções de Bugs
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Remover CSV lido 2x | `excel_parser.py:71-75` | Manter apenas StringIO |
| Tratar erro vazio Gemini | `gemini.py:61` | Verificar se candidates existe |
| Fechar workbook antes de ler sheetnames | `excel_parser.py:51` | Mover lógica antes de `wb.close()` |
| Limitar savings_rate entre 0-100% | `analysis.py:89` | Adicionar `max(0, min(100, ...))` |
| Remover imports não utilizados | Vários | json, datetime, passlib, etc |

---

## FASE 2: INFRAESTRUTURA E DEVOPS (2-3 dias)

### 2.1 Database
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Implementar Alembic | `alembic/` | Migrations para alterações de schema |
| Criar primeira migration | `alembic/` | Schema atual como baseline |
| Adicionar índices | `database.py` | user_id, created_at em todas as tabelas |
| Connection pooling | `database.py` | Configurar pool para produção |

### 2.2 Deploy
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Criar `Dockerfile` | raiz | Multi-stage build (backend + frontend) |
| Criar `docker-compose.yml` | raiz | Backend + Frontend + Nginx |
| Configurar `Procfile` | raiz | Para Railway/Heroku |
| Variáveis de ambiente | `.env.example` | Todas as configs necessárias |
| Health check endpoint | `main.py` | Verificar DB e Gemini API |

### 2.3 CI/CD
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Criar `.github/workflows/test.yml` | GitHub | Rodar testes em PRs |
| Criar `.github/workflows/deploy.yml` | GitHub | Deploy automático em main |
| Adicionar linting | `pyproject.toml` | Ruff ou Flake8 |
| Type checking | `pyproject.toml` | MyPy ou Pyright |

---

## FASE 3: FUNCIONALIDADES PROFISSIONAIS (3-5 dias)

### 3.1 Parser PDF Inteligente
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Extrair transações de tabelas PDF | `pdf_parser.py` | Identificar colunas data/descrição/valor |
| OCR para PDFs escaneados | `pdf_parser.py` | Usar `pytesseract` ou `pdfplumber` |
| Normalizar datas | `pdf_parser.py` | Unificar formato DD/MM/YYYY |
| Parse de extratos bancários PDF | `pdf_parser.py` | Templates para Itaú, Nubank, Bradesco, etc |

### 3.2 Categorização Inteligente
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Expansão de keywords | `analysis.py` | +200 termos por categoria |
| Categorização por IA | `gemini.py` | Fallback quando keyword não encontra |
| Aprendizado do usuário | `database.py` | Salvar correções de categorias |
| Categorias personalizáveis | `database.py` | Usuário criar suas próprias categorias |

### 3.3 Análise Financeira Avançada
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Comparativo mês a mês | `analysis.py` | Delta % entre meses |
| Projeção de gastos | `analysis.py` | Tendência baseada no histórico |
| Alertas de gastos altos | `analysis.py` | Quando gasto > 2x média |
| Meta de economia | `database.py` | Usuário definir meta mensal |
| Reserva de emergência | `analysis.py` | Calcular meses de cobertura |

### 3.4 Investimentos
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Cálculo de perfil real | `analysis.py` | Baseado em idade, renda, objetivos |
| Cache de recomendações | `database.py` | Não recomendar todo dia |
| Dados de mercado em tempo real | `gemini.py` | Prompt com data atual |
| Simulador de portfólio | `analysis.py` | Projeção de rendimento |

---

## FASE 4: UX E DESIGN (2-3 dias)

### 4.1 Frontend
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Tema escuro/claro | `app.py` | Toggle no sidebar |
| Responsividade mobile | `app.py` | CSS adaptativo |
| Loading states | `app.py` | Skeleton screens |
| Notificações toast | `app.py` | Sucesso/erro/aviso |
| Onboarding | `app.py` | Tutorial no primeiro acesso |
| Página de configurações | `app.py` | Perfil, categorias, metas |

### 4.2 Dashboard
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Gráfico de tendência mensal | `app.py` | Linha temporal |
| Mapa de calor de gastos | `app.py` | Calendário com intensidade |
| KPIs comparativos | `app.py` | vs. mês anterior |
| Export do dashboard | `app.py` | Screenshot/PDF |

### 4.3 Relatórios
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Export em PDF | `export.py` | WeasyPrint |
| Relatório mensal automático | `export.py` | Agendado |
| Comparativo anual | `export.py` | 12 meses |
| Logo/marca d'água | `export.py` | No relatório HTML/PDF |

---

## FASE 5: TESTES E QUALIDADE (2-3 dias)

### 5.1 Testes Unitários
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Testes dos parsers | `tests/test_parsers.py` | OFX, CSV, XLSX, PDF |
| Testes de análise | `tests/test_analysis.py` | Categorização, métricas |
| Testes de auth | `tests/test_auth.py` | JWT, login, permissões |
| Testes de export | `tests/test_export.py` | HTML, CSV, JSON |

### 5.2 Testes de Integração
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Testes de API | `tests/test_api.py` | Todas as rotas |
| Testes de upload | `tests/test_upload.py` | Todos os formatos |
| Testes de chat | `tests/test_chat.py` | Fluxo completo |

### 5.3 Testes E2E
| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| Playwright/Selenium | `tests/e2e/` | Fluxo completo no browser |
| Teste de performance | `tests/performance/` | Stress test na API |

---

## FASE 6: DOCUMENTAÇÃO (1 dia)

| Tarefa | Arquivo | Descrição |
|--------|---------|-----------|
| README.md completo | raiz | Setup, features, screenshots |
| API docs (OpenAPI) | `main.py` | Descrições nas rotas |
| CHANGELOG.md | raiz | Histórico de versões |
| CONTRIBUTING.md | raiz | Guia para contribuidores |
| LICENSE | raiz | MIT ou GPL |

---

## ORDEM DE EXECUÇÃO RECOMENDADA

```
SEMANA 1:
├── Dia 1-2: Fase 1 (Segurança + Bugs)
├── Dia 3-4: Fase 2 (Infra + Deploy)
└── Dia 5:   Fase 5.1 (Testes unitários básicos)

SEMANA 2:
├── Dia 1-3: Fase 3 (Funcionalidades)
├── Dia 4-5: Fase 4 (UX + Design)

SEMANA 3:
├── Dia 1-2: Fase 5.2-5.3 (Testes completos)
├── Dia 3:   Fase 6 (Documentação)
└── Dia 4-5: Deploy + Testing final
```

---

## MÉTRICAS DE SUCESSO

| Métrica | Meta |
|---------|------|
| Cobertura de testes | > 80% |
| Tempo de resposta API | < 2s |
| Uptime | > 99% |
| Vulnerabilidades críticas | 0 |
| Bugs conhecidos | 0 |
| Documentação completa | Sim |

---

## CUSTOS ESTIMADOS

| Item | Custo |
|------|-------|
| Railway (deploy) | $5-20/mês |
| Gemini API | Gratuito (tier free) |
| Domínio | ~$10/ano |
| SSL | Gratuito (Let's Encrypt) |
| **Total** | **~$15-30/mês** |

---

*Plano gerado em 29/08/2026 — InvestIA v2.0*
