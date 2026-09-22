---
tipo: backlog
status: ativo
atualizado_em: 2026-08-30
---

# Backlog

IDs são permanentes. A execução detalhada e linear está em [[plans/00 - Plano Mestre de Implementação]].

## P0 — Fundamentos e vertical slice

- [x] **FND-001** Inicializar Git, `pyproject.toml`, lockfile e layout `src/`.
- [x] **FND-002** Configurar lint, tipos, testes e comandos de desenvolvimento.
- [x] **FND-003** Criar shell PySide6/QWebEngine e tratamento global de erro.
- [x] **FND-004** Criar frontend React/TypeScript/Vite/Tailwind com lockfile e build reproduzível.
- [x] **FND-005** Definir `AppGateway`, implementar `QtGateway`/WebChannel e provar round-trip tipado React ↔ Python.
- [x] **FND-006** Implementar contratos do domínio, portas, adaptadores em memória e conclusão idempotente sem SQLite.
- [x] **DAT-001** Implementar conexão SQLite segura e caminhos de dados por usuário.
- [x] **DAT-002** Implementar runner/checksum de migrations.
- [x] **DAT-003** Criar migration `001_initial` e índices mínimos.
- [x] **DAT-004** Criar backup verificado antes de migration e fluxo de recuperação.
- [x] **DOM-001** Implementar perfis, contas e personagens.
- [x] **DOM-002** Implementar atividades e vínculo por personagem.
- [x] **DOM-003** Implementar registro diário e conclusão rápida idempotente.
- [ ] **DOM-004** Implementar sessões, produção e drops opcionais.
- [ ] **DOM-005** Implementar regras versionadas de recompensas, custos e janelas de atividade.
- [x] **DOM-006** Implementar Torre como sessão independente com participantes opcionais, custo, conclusão e drops.
- [x] **DOM-007** Implementar catálogo das nove dungeons e duas missões versionadas.
- [x] **DOM-008** Implementar cotações versionadas do Saco PvE e estimativa complementar sem reescrever históricos.
- [x] **DOM-009** Registrar diária operacional por personagem/data sem recompensa econômica.
- [x] **DOM-010** Registrar VIP por personagem com vigência máxima de 30 dias, precisão de horas, ajuste sem duplicar despesa e custo em gold.
- [x] **UI-001** Criar tokens visuais e fontes/ícones licenciados.
- [ ] **UI-002** Criar janela sem moldura com comportamento Windows validado.
- [x] **UI-003** Criar sidebar, header e navegação da tela Hoje; destinos futuros permanecem desabilitados até existirem.
- [x] **UI-004** Criar cards estatísticos e componentes de status.
- [ ] **UI-005** Criar tabela/lista de personagens virtualizada.
- [x] **UI-006** Criar resumo diário (incluindo Sacos PvE ganhos), drops recentes e gráfico mensal com read models reais.
- [x] **UI-007** Ligar tela Hoje a dados reais e estados vazio/erro/carregando, com atualização na virada diária e ao retornar ao foco.
- [x] **UI-008** Criar resumo por personagem com dungeons selecionadas e ciclo automático de cinco rodadas.
- [x] **UI-009** Criar formulário de sessão da Torre separado do checklist diário.
- [x] **UI-010** Criar registro/contrato de módulos e host React com renderização/lazy loading controlados.
- [x] **UI-011** Permitir mostrar/ocultar módulos e restaurar layout padrão.
- [x] **UI-012** Registrar e atualizar a cotação atual do Saco PvE na Home.
- [x] **UI-013** Exibir e alternar a diária de cada personagem na Home.
- [x] **UI-014** Exibir dias/horas restantes, ativar e ajustar VIP por personagem na Home.
- [x] **UI-015** Calculadora local de valor de gold em BRL com padrão de 8c por 1.000 gold.
- [x] **UI-016** Abrir calculadora sem consulta de câmbio na bridge; manter taxas indicativas locais e editáveis.
- [ ] **TST-001** Criar fixture dourada que reproduza os valores do mockup.
- [x] **TST-002** Criar comparação visual 1680×941 e checklist de fidelidade em `design-qa.md`.

## P1 — Produto local completo

- [ ] **MGT-001** Página de contas e personagens com arquivamento seguro.
- [x] **MGT-002** Página de dungeons/atividades, seleção da rotina e metas padrão.
- [x] **HIS-001** Histórico por data, conta, personagem e atividade.
- [ ] **HIS-002** Edição auditável de sessões e lançamentos.
- [ ] **INV-001** Catálogo de itens e ledger de inventário.
- [x] **FIN-001** Vendas e ledger financeiro em gold/moeda.
- [x] **FIN-002** Lançamento manual de despesas em gold e projeção mensal de VIP, Torre e outras despesas.
- [x] **FIN-003** Histórico, correção por substituição e estorno auditável de despesas manuais.
- [x] **TIM-001** Sessão de rotina persistida com iniciar, pausar, retomar e encerrar na Home.
- [x] **TIM-002** Histórico e comparação de tempo de rotina por sessões encerradas.
- [x] **REP-003** Ligar atalhos de relatórios aos destinos operacionais e permitir editar a meta mensal.
- [x] **REP-004** Considerar gold e Sacos PvE valorados pela cotação atual no progresso da meta mensal.
- [x] **REP-005** Feed de últimas movimentações para conferência rápida nos relatórios.
- [x] **REP-006** Comparação mensal de relatórios por período equivalente, transparência de valores absolutos e visão histórica de faturamento.
- [ ] **REP-001** Relatórios de produção, tempo e conclusão (inclui KPIs reais de Sacos PvE ganhos e média por dia farmado no mês; tempo/conclusão detalhados ainda pendentes).
- [ ] **REP-002** Relatórios de itens, vendas e conversão.
- [ ] **EXP-001** Exportação CSV/JSON com versão de formato.
- [ ] **BKP-001** Tela de backups, restauração e diagnóstico.
- [ ] **CFG-001** Configurações de timezone, idioma, tema e diretório de backup.
- [ ] **CFG-002** Caminho estável compartilhado entre execução manual e app instalado, com trava para testes.
- [x] **CFG-003** Persistir layouts/módulos visíveis com versionamento das preferências.
- [x] **CFG-004** Persistir meta mensal de gold por workspace/mês.
- [ ] **REM-001** Rotina de trabalho opt-in com horário/dias configuráveis e lembretes.
- [ ] **GME-010** Modelar Fama dos Mercados como saldo estimado calibrável, catálogo de missões e consumo de dungeon após confirmação dos custos.
- [x] **PKG-001** Spike PyInstaller + Inno Setup com Qt WebEngine, WebChannel e `frontend/dist`.
- [x] **PKG-002** Instalador/atualizador pessoal que preserva o diretório de dados.
- [ ] **A11Y-001** Navegação por teclado, foco, contraste e escala do Windows.
- [ ] **PERF-001** Medir abertura, consultas e memória com base grande.

## Dados do jogo

- [x] **GME-001** Confirmar dias, horário de abertura e duração da Torre.
- [x] **GME-002** Confirmar requisitos/elegibilidade da Torre conforme print fornecido.
- [x] **GME-003** Confirmar custo fixo de 25.000 gold por abertura da Torre.
- [x] **GME-004** Confirmar ciclo-meta de 5 rodadas por dungeon.
- [x] **GME-005** Confirmar gold e 1 Saco PvE por rodada/dungeon.
- [x] **GME-006** Definir que marcar Dungeon feita assume todas as 5 rodadas.
- [x] **GME-007** Definir a seleção inicial entre as nove dungeons e seu escopo global/conta/personagem: global, com as nove ativas.
- [x] **GME-008** Informar preço inicial do Saco PvE (1.000 gold) e cotação inicial do gold (7–8c/1k).
- [ ] **GME-009** Confirmar a linha cortada sobre reset das oportunidades da Torre.

## P2 — Escala e cloud opcional

- [ ] **WEB-001** Validar demanda do canal web e decidir hospedagem/API antes de implementar.
- [ ] **WEB-002** Implementar `HttpGateway` contra o mesmo contrato do `QtGateway`.
- [ ] **WEB-003** Hospedar o mesmo build React e criar testes específicos do runtime web.
- [ ] **CLD-001** Obter/criar projeto Supabase somente após validação e gerar migrations remotas revisadas.
- [ ] **CLD-002** Implementar Auth, memberships e vínculo seguro do workspace local.
- [ ] **CLD-003** Implementar RLS por workspace e testes negativos entre usuários/workspaces.
- [ ] **SYN-001** Implementar outbox e upload inicial idempotente.
- [ ] **SYN-002** Implementar pull incremental, tombstones e cursores.
- [ ] **SYN-003** Definir e testar resolução de conflitos.
- [ ] **SYN-004** Testar restauração completa em segundo dispositivo.
- [ ] **OBS-001** Diagnóstico local sanitizado e telemetria somente opt-in.

## Ideias estacionadas

- Captura automática de dados do jogo, condicionada a regras e viabilidade técnica.
- Aplicativo móvel complementar.
- Alertas e metas personalizadas.
- Importadores de planilhas antigas.
- Preços externos de mercado com fonte e timestamp.
- Módulos React de terceiros; reavaliar somente com modelo de confiança, assinatura e sandbox adequado.

## Critério para promover uma ideia

Definir problema, usuário, dado necessário, riscos, critério de aceite e marco-alvo. “Pode ser útil algum dia” justifica preservar fatos relevantes, não implementar uma feature sem caso de uso.
