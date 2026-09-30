---
kanban-plugin: basic
tipo: kanban
---

## Próximo

- [ ] UI-002 — Criar janela sem moldura e controles Windows
- [ ] UI-005 — Virtualizar lista de personagens e validar base grande
- [ ] DOM-004 — Implementar sessões, produção e drops opcionais nos repositórios SQLite
- [ ] DOM-005 — Implementar regras versionadas nos repositórios SQLite
- [ ] GME-010 — Fama dos Mercados como estimativa calibrável, após consolidar medições de ganhos e custos

## Em andamento

- [ ] REL-001 — Build, instalação isolada, aceitação do executável e release v0.1.2 no GitHub

- [ ] Etapa 10 — Exportação de relatórios CSV/JSON (`EXP-001`)
- [ ] REP-001 e REP-002 — Completar métricas de tempo/conclusão, inventário e filtros/exportação
- [ ] Etapas 5–6 — Fechar responsividade, shell sem moldura, virtualização e fallback textual do gráfico

## Bloqueado

- [ ] GME-009 — Linha cortada sobre o reset da Torre

## Concluído

- [x] PUB-001 — Privacidade proporcional: referências portáveis, demonstração e fixtures fictícias, dados locais ignorados e histórico preservado documentado
- [x] PUB-002 — Licença MIT escolhida pelo proprietário e fontes/limites dos assets documentados; checks registrados no Backlog

- [x] UI-019 — Desempenho mensal em gold equivalente com o valor dos Sacos PvE pela cotação atual e detalhamento no tooltip
- [x] UI-020 — Botão “Concluir tudo” para as dungeons pendentes dos personagens de hoje, com confirmação única
- [x] HIS-003 — Corrigir divergência entre resumo e detalhe do histórico; “Parcial” e “Incompletos” seguem as dungeons ativas
- [x] PKG-003 — Excluir ICU incompatível do pacote e validar a inicialização do executável congelado antes do instalador
- [x] PKG-001 e PKG-002 — Empacotamento Windows com PyInstaller, Qt WebEngine, assets React e instalador oficial Inno Setup 6 que preserva `%LOCALAPPDATA%`
- [x] FIN-001 — Registro de vendas multimoeda idempotente, com valor original, conversão BRL calculada no backend e snapshot da origem da cotação
- [x] FIN-002 — Despesa manual em gold no ledger financeiro e detalhamento mensal de VIP, Torre e outras despesas
- [x] FIN-003 — Histórico, correção por substituição e estorno auditável de despesas manuais
- [x] TIM-001 — Sessão de rotina persistida na Home com iniciar, pausar, retomar e encerrar
- [x] TIM-002 — Histórico e comparação de tempo de rotina nos relatórios
- [x] TIM-003 — Excluir sessões com menos de 5 minutos ativos do histórico e dos relatórios
- [x] REP-004, UI-015 — Meta mensal por gold equivalente (gold + Sacos PvE) e calculadora local de BRL
- [x] UI-016 — Abertura imediata da calculadora sem consulta de câmbio bloqueante; taxas indicativas editáveis
- [x] UI-017 — Altura uniforme de 50 px nos botões de ação da Home
- [x] UI-018 — Exibir versão do aplicativo no cartão do workspace local e conferir consistência com o instalador
- [x] REP-005 — Feed de últimas movimentações nos relatórios para conferência rápida
- [x] REP-006 — Comparação mensal e histórico de vendas nos relatórios
- [x] REP-007 — Comparar acumulado atual com mês anterior completo, sem exigir dias coincidentes
- [x] DOM-009, UI-013 — Diária operacional por personagem/data com marcação rápida na Home, sem impacto financeiro
- [x] CFG-004, REP-003 — Meta mensal persistida e atalhos de relatórios com destinos reais
- [x] DOM-010, UI-014 — VIP por personagem com dias/horas restantes, ajuste de validade e despesa única em gold
- [x] Etapa 9 — Histórico de farm (`HIS-001`), cotação rápida do Saco PvE (`DOM-008`, `UI-012`) e estimativa dinâmica no card de ouro

- [x] FND-001 — Inicializar Git, pyproject, lockfile e estrutura Python
- [x] FND-002 — Configurar qualidade e comandos Python/TypeScript
- [x] FND-003 — Criar shell PySide6/QWebEngine mínimo
- [x] FND-004 — Criar frontend React/Vite/Tailwind mínimo
- [x] FND-005 — Provar round-trip AppGateway/QtGateway/WebChannel no build estático
- [x] FND-006 — Implementar contratos do domínio, portas, adaptadores em memória e conclusão idempotente
- [x] DAT-001 — Implementar conexão SQLite segura e caminho de dados por usuário
- [x] DAT-002 — Implementar runner de migrations com checksums
- [x] DAT-003 — Criar migration inicial e índices mínimos
- [x] DAT-004 — Implementar backup verificado e restauração que preserva cópia de recuperação
- [x] Criar vault e planejamento mestre
- [x] Fechar decisões iniciais de reset, resumo, volume, avatar e empacotamento
- [x] Confirmar catálogo/recompensas das nove dungeons e regras principais da Torre
- [x] DOM-008 — Persistir cotações versionadas do Saco PvE e estimativa complementar
- [x] UI-001, UI-003 e UI-004 — Tokens, marca/ícones, sidebar, header, KPIs e estados visuais
- [x] UI-006 e UI-007 — Resumo, Torre, drops e gráfico mensal ligados a read models SQLite
- [x] TST-002 — Baseline e QA visual 1680×941 aprovados em `design-qa.md`
- [x] DOM-002, DOM-003 e DOM-007 — Atividades globais, vínculos, catálogo versionado e fechamento diário atômico
- [x] DOM-006 e UI-009 — Torre independente com custo fixo, participantes opcionais e drops em uma transação
- [x] UI-008 — Resumo por personagem com seleção global e ciclos completos de cinco rodadas
- [x] UI-010, UI-011 e CFG-003 — Registro/host de módulos, lazy loading, visibilidade persistida e restauração padrão
- [x] MGT-002 — Seleção global da rotina de dungeons, herdada por novos personagens
- [x] HIS-001 — Histórico de farm com filtros por período, conta e personagem, listagem de dias e detalhamento completo
- [x] DOM-001 — Cadastro e edição de contas/personagens nos repositórios SQLite
- [x] DOM-008 & UI-012 — Modal e botão de cotação do Saco PvE no Farm de Hoje ao lado de Registrar Torre com recálculo automático

%% kanban:settings
```
{"kanban-plugin":"basic","list-collapse":[false,false,false,false]}
```
%%
