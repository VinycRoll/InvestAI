# Contribuindo com InvestIA

Obrigado por considerar contribuir!

## Como Contribuir

### Reportando Bugs

1. Verifique se o bug já foi reportado nas [Issues](https://github.com/seu-usuario/InvestIA/issues)
2. Se não, crie uma nova issue com:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Logs/prints se aplicável
   - Ambiente (OS, Python version, browser)

### Sugerindo Features

1. Abra uma issue com label `enhancement`
2. Descreva o problema que resolve
3. Explique a solução proposta
4. Considere casos de uso

### Pull Requests

1. Fork o repositório
2. Crie uma branch: `git checkout -b feature/nome-da-feature`
3. Faça suas alterações
4. Rode os testes: `pytest -q` (offline, determinístico — banco temporário + Gemini simulado)
5. Commit com mensagem clara: `git commit -m "feat: adiciona X"`
6. Push: `git push origin feature/nome-da-feature`
7. Abra o PR

## Padrões de Código

### Python
- **Formatter**: `ruff format` (ou `black`)
- **Linting**: `ruff check` (ou `flake8`)
- **Type hints**: Obrigatórios em funções públicas
- **Docstrings**: Google style para funções públicas

### Commits (Conventional Commits)
```
feat: nova funcionalidade
fix: correção de bug
docs: documentação
style: formatação (sem mudança de lógica)
refactor: refatoração
test: testes
chore: manutenção (deps, config)
```

Exemplos:
- `feat: adiciona categorização por IA no PDF parser`
- `fix: corrige export CSV vazio para PDFs`
- `docs: atualiza README com instruções Docker`

### Testes
- Todo código novo deve ter testes
- Rode `pytest -q` antes do PR (188 casos coletados; 158 executáveis offline, passando)
- Não há métrica de cobertura configurada no projeto (pytest-cov não instalado)

## Estrutura de Branches

- `main` — produção (protegida)
- `feature/*` — novas features
- `fix/*` — correções
- `docs/*` — documentação

## Setup de Desenvolvimento

```bash
# Clone
git clone https://github.com/seu-usuario/InvestIA.git
cd InvestIA

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest ruff

# Frontend
cd ../frontend
pip install -r requirements.txt

# Testes
cd ..
pytest -q

# Compilação (sintaxe)
python -m compileall -q backend frontend tests alembic

# Lint
ruff check backend frontend tests alembic
```

## Variáveis de Ambiente

Copie `.env.example` para `.env` e configure:

```env
GEMINI_API_KEY=sua_chave_aqui
JWT_SECRET=secret_forte_em_producao
CORS_ORIGINS=http://localhost:8501
```

## Code Review

Todos os PRs passam por review. Verificamos:
- Testes passam
- Cobertura mantida
- Código limpo e tipado
- Documentação atualizada
- Sem secrets no código

## Comunidade

- Seja respeitoso
- Use português ou inglês
- Ajude outros contribuidores

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob MIT.