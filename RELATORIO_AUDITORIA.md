# RELATÓRIO DE AUDITORIA - InvestIA v2.0

**Data:** 29/08/2026  
**Auditor:** Analista Técnico  
**Escopo:** Revisão completa linha por linha do código-fonte  

---

## 0. STATUS ATUAL DOS APONTAMENTOS (reconciliação em 02/09/2026)

> Este relatório foi gerado na FASE 1. Desde então, as Fases 1–7 corrigiram os itens
> listados abaixo. A tabela resume o estado atual de cada apontamento no código.

| # | Apontamento original | Estado atual |
|---|---|---|
| 1 | `auth.py:10` SECRET_KEY hardcoded | **Corrigido.** Secret lida via `os.getenv("JWT_SECRET")` em `auth.py` (`JWT_SECRET`). |
| 2 | `bcrypt` definido mas não usado | **Corrigido.** bcrypt usado na verificação/hash de senha (`verify_password`). |
| 3 | `init_db()` no startup sem migrations | **Aceito/Controlado.** `create_all()` é idempotente e funciona como rede de segurança; **Alembic** agora disponível e validado para controle de schema (`alembic/`). |
| 4 | CORS `allow_origins=["*"]` | **Corrigido.** `allow_origins=CORS_ORIGINS` a partir de env (`CORS_ORIGINS`, padrão localhost). |
| 5 | Upload sem validação de tamanho | **Corrigido.** Limite de 10MB com leitura em streaming por chunks. |
| 6 | Dispatch de parsers condicional inconsistente | **Corrigido** na FASE 2 (dispatch por `file_type`). |
| 7 | CSV lido duas vezes (`excel_parser.py:71-75`) | **Corrigido.** Leitura única. |
| 8 | `wb.sheetnames` após `wb.close()` | **Corrigido.** |
| 9 | `abs()` inconsistente em income/expenses | **Corrigido.** |
| 10 | `suggested_investment` fixo em 20% | **Alterado (documentado).** Passou a 80% da margem mensal (decisão de produto); rotulado como estimativa educacional. |
| 11 | `savings_rate` fora dos limites | **Corrigido.** Clampado em 0–100%. |
| 12 | Imports não usados (`analysis.py`) | **Corrigido.** Removidos. |
| 13 | URL Gemini hardcoded `v1beta` | **Corrigido.** via env `GEMINI_API_URL`. |
| 14 | `timeout` fixo | **Mantido/Parametrizado** (defaults; retry com `GEMINI_RETRIES`). |
| 15 | `data["candidates"][0]` sem checagem | **Corrigido.** Verifica existência/`candidates` antes de acessar; retry em 4xx/5xx/vazio. |
| 16 | `analyze_financial_data()` não usado | **Removido.** |
| 17 | PDF truncado em 15000 chars | **Corrigido.** Lê tabelas + texto; truncamento configurável. |
| 18 | PDF não retorna transações | **Corrigido.** Extrai transações de tabelas + texto. |
| 19 | CSV export sem dados de transações | **Corrigido.** Export CSV inclui transações com escaping correto. |
| 20 | `API_URL` hardcoded no frontend | **Corrigido.** `services/api.py` lê de env (`API_URL`), com fallback localhost. |
| 21 | `timeout=60` fixo | **Mantido** como default configurável. |
| 22/23/24 | Imports `plotly`/`requests` dentro de função | **Corrigido.** Código refatorado em módulos (`components/`, `services/`, `pages/`); imports no topo. |
| 25 | `DATABASE_URL` caminho relativo | **Corrigido.** Config centralizada via `config.py` + env. |
| 26 | `datetime.utcnow()` deprecado | **Corrigido.** `datetime.now(timezone.utc)`. |
| 27 | Backend sem `--reload` | **Mantido (correto).** Em produção não deve ter reload. |
| 28 | API Key no `.env` | **Aceito.** `.env` é gitignored; projeto usa `.env.example` sem secrets. |

**Novo desde a FASE 1:** security headers middleware (X-Content-Type-Options,
X-Frame-Options, Referrer-Policy), healthcheck, Docker não-root, CI com lint+testes+build,
deploy via Railway CLI, migrações Alembic funcionais, 188 testes coletados.

*Reconciliação feita em 02/09/2026 (FASE 7). A análise original segue abaixo para histórico.*

---

## I. PARECER EXECUTIVO DO AUDITOR

**Classificação:** COM RESSALVAS

**Resumo de Riscos:**
1. **SEGURANÇA CRÍTICA:** Secret key JWT hardcoded em `auth.py:10` — vulnerabilidade grave
2. **INTEGRIDADE DE DADOS:** Parser CSV lê arquivo duas vezes (`excel_parser.py:71-75`) — desperdício e risco de inconsistência
3. **CÁLCULO FINANCEIRO:** `savings_rate` pode retornar valores >100% ou negativos (`analysis.py:89`)

---

## II. TABELA DE APONTAMENTOS (Audit Findings)

| # | Arquivo:Linha | Divergência Encontrada | Impacto/Risco | Severidade |
|---|---|---|---|---|
| 1 | `auth.py:10` | SECRET_KEY hardcoded: `"investia-secret-change-in-production"` | Tokens JWT podem ser forjados por qualquer pessoa que veja o código | **CRÍTICO** |
| 2 | `auth.py:14` | `pwd_context` com bcrypt definido mas NUNCA utilizado | Código morto, dependência desnecessária | Baixo |
| 3 | `main.py:30` | `init_db()` chamado no startup sem migrations | Destrói dados em alterações de schema | **ALTO** |
| 4 | `main.py:22-28` | CORS com `allow_origins=["*"]` | Permite qualquer origem — vulnerabilidade CSRF | **ALTO** |
| 5 | `main.py:72` | Upload sem validação de tamanho de arquivo | Ataque de negação de serviço (DoS) por arquivo gigante | **ALTO** |
| 6 | `main.py:88-95` | Dispatch de parsers com lógica condicional inconsistente | Difícil manutenção, código duplicado | Médio |
| 7 | `excel_parser.py:71-75` | CSV lido DUAS VEZES com `pd.read_csv` | Desperdício de memória e CPU | Médio |
| 8 | `excel_parser.py:51` | `wb.sheetnames` acessado DEPOIS de `wb.close()` | Pode falhar em versões futuras do openpyxl | Médio |
| 9 | `analysis.py:53-54` | Cálculo de income/expenses usa `abs()` inconsistente | `total_income` soma valores positivos corretamente, mas `total_expenses` também usa `abs()` em valores já negativos (redundante) | Baixo |
| 10 | `analysis.py:78` | `suggested_investment` fixo em 20% da receita | Não considera perfil de risco nem despesas fixas | Médio |
| 11 | `analysis.py:89` | `savings_rate` pode retornar >100% ou negativo | Se despesas > receitas, taxa fica negativa; se receitas muito altas, pode parecer irreal | Médio |
| 12 | `analysis.py:1` | Import `json` e `datetime` não utilizados | Código morto | Baixo |
| 13 | `gemini.py:5` | URL da API hardcoded com versão `v1beta` | Pode quebrar quando Google mudar a versão | Médio |
| 14 | `gemini.py:54` | `timeout=60` fixo para todas as chamadas | Análises grandes podem falhar por timeout | Médio |
| 15 | `gemini.py:61` | Acesso direto a `data["candidates"][0]` sem verificação | Pode falhar se resposta vier vazia | **ALTO** |
| 16 | `gemini.py:63-76` | `analyze_financial_data()` não é usado em lugar nenhum | Código morto — função existe mas nunca é chamada | Baixo |
| 17 | `pdf_parser.py:35` | Texto truncado em 15000 caracteres | Perde dados de PDFs grandes | Médio |
| 18 | `pdf_parser.py:5` | Parser não retorna `transactions` | CSV fica vazio para arquivos PDF | **ALTO** |
| 19 | `export.py:175-219` | CSV não inclui dados de transações individuais | Relatório CSV incompleto | Médio |
| 20 | `frontend/app.py:5` | `API_URL` hardcoded como `localhost:8000` | Não funciona em produção/deploy | **ALTO** |
| 21 | `frontend/app.py:28` | `timeout=60` fixo para todas as chamadas API | Uploads grandes podem falhar | Médio |
| 22 | `frontend/app.py:123` | `import plotly` DENTRO da função | Import repetido a cada renderização | Baixo |
| 23 | `frontend/app.py:237` | `import plotly` repetido na mesma função | Import duplicado | Baixo |
| 24 | `frontend/app.py:317` | `import requests as req` dentro da função | Import desnecessário — requests já importado no topo | Baixo |
| 25 | `database.py:6` | `DATABASE_URL` com caminho relativo `./investia.db` | Pode criar DB em local errado dependendo de onde o servidor é iniciado | Médio |
| 26 | `database.py:21` | `datetime.utcnow()` deprecado no Python 3.12+ | Usar `datetime.now(timezone.utc)` | Médio |
| 27 | `start.sh:22` | Backend iniciado sem `--reload` em produção | Não detecta mudanças em código | Baixo |
| 28 | `.env:2` | API Key do Gemini exposta no `.env` (mesmo protegido pelo .gitignore) | Risco se repositório for público | Médio |

---

## III. ANÁLISE TÉCNICA DETALHADA

### 3.1 SEGURANÇA

#### 3.1.1 Autenticação JWT (`auth.py`)
```
Linha 10: SECRET_KEY = "investia-secret-change-in-production"
```
**Problema:** A secret key está hardcoded. Qualquer pessoa com acesso ao repositório pode forjar tokens JWT e acessar dados de outros usuários.

**Conciliação:** O `.env` possui `JWT_SECRET=mude-esta-secret-em-producao`, mas o código NÃO lê essa variável. A secret usada é a hardcoded.

**Impacto:** CRÍTICO — Violação de confidencialidade e integridade dos dados.

#### 3.1.2 CORS (`main.py:22-28`)
```python
allow_origins=["*"]
```
**Problema:** Permite requisições de qualquer origem. Em produção, qualquer site malicioso pode fazer chamadas à API.

**Impacto:** ALTO — Vulnerabilidade de ataques CSRF e requisições não autorizadas.

#### 3.1.3 Upload sem limite (`main.py:72`)
```python
content = await file.read()
```
**Problema:** Não há validação de tamanho. Um arquivo de 10GB causaria estouro de memória.

**Impacto:** ALTO — Risco de DoS.

### 3.2 INTEGRIDADE DE DADOS

#### 3.2.1 Parser CSV duplicado (`excel_parser.py:71-75`)
```python
df = pd.read_csv(pd.io.common.StringIO(text) if hasattr(pd.io.common, "StringIO") else BytesIO(text.encode()))
# Handle StringIO properly
from io import StringIO
df = pd.read_csv(StringIO(text))
```
**Problema:** O CSV é lido duas vezes. A primeira leitura é descartada imediatamente.

**Impacto:** Médio — Desperdício de recursos e código confuso.

#### 3.2.2 Parser PDF sem transações (`pdf_parser.py`)
**Problema:** O parser de PDF retorna `full_text` e `tables`, mas NÃO retorna `transactions`. Isso quebra:
- CSV export (fica vazio)
- Análise financeira local (sem dados para categorizar)

**Impacto:** ALTO — Funcionalidade principal comprometida para arquivos PDF.

### 3.3 CÁLCULOS FINANCEIROS

#### 3.3.1 Taxa de poupança (`analysis.py:89`)
```python
"savings_rate": round((1 - total_expenses / total_income) * 100, 1) if total_income > 0 else 0
```
**Problema:** 
- Se `total_expenses > total_income`, resultado é negativo (ex: -50%)
- Se `total_income` é muito baixo e `total_expenses` próximo, pode gerar valores absurdos
- Não há validação de limites

**Impacto:** Médio — Dados enganosos para o usuário.

#### 3.3.2 Investimento sugerido (`analysis.py:78`)
```python
investable = round(total_income * 0.2, 2) if total_income > 0 else 0
```
**Problema:** Fixo em 20% sem considerar:
- Perfil de risco do usuário
- Despesas fixas obrigatórias
- Reserva de emergência

**Impacto:** Médio — Recomendação genérica e potencialmente irresponsável.

### 3.4 ARQUITETURA

#### 3.4.1 Database sem migrations (`main.py:30`)
```python
init_db()
```
**Problema:** Usa `create_all()` que não altera tabelas existentes. Se o schema mudar, será necessário deletar o DB manualmente.

**Impacto:** ALTO — Perda de dados em atualizações.

#### 3.4.2 Imports não utilizados
- `analysis.py:1`: `import json` e `from datetime import datetime` — nunca usados
- `auth.py:4`: `from passlib.context import CryptContext` — definido mas não utilizado
- `frontend/app.py:317`: `import requests as req` — duplicado

**Impacto:** Baixo — Código morto, mas atrapalha manutenção.

### 3.5 FRONTEND

#### 3.5.1 API URL hardcoded (`frontend/app.py:5`)
```python
API_URL = "http://localhost:8000"
```
**Problema:** Impossível fazer deploy sem alterar o código.

**Impacto:** ALTO — Bloqueia deploy em produção.

#### 3.5.2 Imports duplicados
`plotly.express` é importado dentro de `dashboard_page()` (linha 123) E dentro de `analysis_page()` (linha 237). Deveria ser importado uma vez no topo.

**Impacto:** Baixo — Ineficiência menor.

---

## IV. RECOMENDAÇÕES E PLANO DE AÇÃO

### Ações Corretivas Imediatas (Críticas)

| # | Ação | Arquivo | Esforço |
|---|---|---|---|
| 1 | Mover SECRET_KEY para `.env` e ler via `os.getenv()` | `auth.py` | 5 min |
| 2 | Adicionar validação de tamanho no upload (max 10MB) | `main.py` | 10 min |
| 3 | Tratar erro vazio em `gemini.py:61` | `gemini.py` | 5 min |
| 4 | Remover leitura duplicada do CSV | `excel_parser.py` | 5 min |

### Ações de Médio Prazo

| # | Ação | Arquivo | Esforço |
|---|---|---|---|
| 5 | Configurar CORS com origins específicas | `main.py` | 10 min |
| 6 | Usar variável de ambiente para `API_URL` no frontend | `frontend/app.py` | 10 min |
| 7 | Adicionar Alembic para migrations | `database.py` | 30 min |
| 8 | Parser PDF deve tentar extrair transações tabulares | `pdf_parser.py` | 30 min |
| 9 | Adicionar validação de limites no `savings_rate` | `analysis.py` | 10 min |
| 10 | Remover código morto (imports, funções não usadas) | Vários | 15 min |

### Ações de Melhoria Contínua

| # | Ação | Arquivo | Esforço |
|---|---|---|---|
| 11 | Implementar rate limiting na API | `main.py` | 20 min |
| 12 | Adicionar testes unitários | `tests/` | 2h |
| 13 | Implementar OAuth (Google/GitHub) | `auth.py` | 4h |
| 14 | Export em PDF (WeasyPrint) | `export.py` | 2h |
| 15 | Comparativo mensal | `analysis.py` | 1h |

---

## V. CONCLUSÃO

O projeto InvestIA possui uma **base sólida** com arquitetura bem estruturada e funcionalidades principais implementadas. No entanto, existem **vulnerabilidades de segurança críticas** (SECRET_KEY hardcoded, CORS aberto) e **bugs de integridade de dados** (parser CSV duplicado, PDF sem transações) que precisam ser corrigidos antes de qualquer produção.

**Prioridade máxima:** Corrigir os 4 itens críticos listados nas ações imediatas.

---

*Relatório gerado em 29/08/2026 — InvestIA v2.0*
