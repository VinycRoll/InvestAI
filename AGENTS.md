# Instruções do projeto InvestAI

## Regra geral
Antes de alterar qualquer arquivo, analise o código e entenda o problema.
Faça mudanças pequenas, objetivas e compatíveis com a arquitetura existente.

## Segurança
- NUNCA leia, mostre, copie ou altere o conteúdo do arquivo `.env`.
- NUNCA exponha API keys, JWT secrets, senhas ou tokens.
- Não coloque segredos em código, logs, mensagens de erro ou commits.
- Não remova mecanismos de autenticação, autorização ou rate limiting sem autorização explícita.
- Não faça alterações destrutivas sem autorização do usuário.

## Processo de desenvolvimento
Para cada tarefa:
1. Analise os arquivos relacionados.
2. Explique brevemente o que pretende alterar.
3. Faça a menor alteração necessária.
4. Execute testes ou verificações relevantes.
5. Verifique `git diff`.
6. Informe claramente o que foi alterado e se os testes passaram.

## Git
- A branch principal é `main`.
- O remote principal é `origin`.
- NÃO execute `git push` sem autorização explícita do usuário.
- NÃO faça `git reset --hard`, `git clean`, rebase destrutivo ou apague alterações do usuário sem autorização.
- Antes de qualquer commit, verifique `git status` e `git diff`.
- Nunca faça commit de `.env`, bancos locais, ambientes virtuais, caches ou arquivos com segredos.
- Use mensagens de commit claras e objetivas.

## Backend
- O backend utiliza FastAPI.
- Preserve a separação entre rotas, autenticação, banco de dados, parsers e services.
- Use Alembic para alterações de banco de dados destinadas a produção.
- Não use `create_all()` como substituto de migrations em produção.
- Valide entradas e uploads.
- Não exponha detalhes internos de exceções ao usuário.
- Evite `except Exception` genérico quando houver tratamento mais específico.

## Frontend
- O frontend utiliza Streamlit.
- Preserve a estrutura modular existente.
- Não reintroduza dependências desnecessárias.
- Mantenha suporte aos temas claro e escuro.
- Preserve os textos e a experiência atual da aplicação, salvo quando a tarefa pedir mudança.

## Dados financeiros
- Não apresente heurísticas como garantias de investimento.
- Não invente dados de mercado ou informações em tempo real.
- Preserve avisos e limitações relacionados a análises financeiras.
- Considere risco, reserva financeira e contexto antes de apresentar sugestões de investimento.

## Testes
Depois de alterações relevantes:
- Execute os testes relacionados à mudança.
- Quando possível, execute a suíte completa de testes.
- Se um teste falhar por problema do ambiente, diferencie claramente isso de uma falha no código.

## Documentação
Quando uma alteração modificar o comportamento da aplicação, atualize a documentação relevante.

## Princípio principal
Priorize:
segurança > estabilidade > correção > simplicidade > novas funcionalidades.
