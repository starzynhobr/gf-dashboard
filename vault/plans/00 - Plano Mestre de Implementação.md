---
tipo: plano
status: em-execucao
ordem: linear
atualizado_em: 2026-08-27
---

# Plano Mestre de Implementação

## Como executar

Este é o caminho linear. Cada etapa termina com evidência e um portão. Não iniciar a etapa seguinte com pendência crítica no portão atual. IDs de trabalho vêm de [[06 - Backlog]].

## Etapa 0 — Congelar requisitos e referências

**Objetivo:** começar com decisões rastreáveis e um alvo visual reproduzível.

1. Revisar [[01 - Fonte da Verdade]] e registrar as decisões já confirmadas: React único dentro do shell PySide6/QWebEngine, bridge WebChannel, SQLite local, meia-noite local, catálogo de nove dungeons, ciclo de cinco rodadas, Torre separada, fixture 2×5 e avatar fora do MVP.
2. Criar o repositório Git e `.gitignore`, preservando o vault e a imagem de referência.
3. Registrar dimensões, escala, fonte e checksum do mockup.
4. Definir plataforma Windows mínima e o diretório estável compartilhado pela execução manual e futura instalação.
5. Converter decisões propostas que já tenham evidência em aceitas.
6. Registrar a seleção inicial de dungeons, preço do Saco PvE e trecho cortado do reset da Torre como pendências não bloqueadoras.

**Entregáveis:** repositório, requisitos aprovados, referência identificada e decisões bloqueadoras fechadas.

**Portão:** fluxo principal e estrutura extensível estão definidos; valores ainda desconhecidos possuem backlog e não estão codificados como constantes.

## Etapa 1 — Toolchains reproduzíveis, shell e bridge mínima

**Objetivo:** qualquer checkout limpo compila o React, abre o build no shell PySide6/QWebEngine e prova a comunicação assíncrona com Python.

1. Fixar versão do Python e gerenciador/lockfile.
2. Fixar versão do Node e criar lockfile do frontend.
3. Criar `pyproject.toml`, layout Python e comandos `run`, `test`, `lint` e `typecheck`.
4. Criar `frontend/` com React, TypeScript, Vite, Tailwind, Vitest, Testing Library, ESLint e scripts `dev/build/test/lint/typecheck`.
5. Adicionar PySide6 com Qt WebEngine/WebChannel, pytest, pytest-qt, Ruff e verificador de tipos Python.
6. Implementar `bootstrap.py`, logging sanitizado e tratamento global de exceções.
7. Criar shell `QWebEngineView` que carregue o Vite somente no modo dev e `frontend/dist` nos demais modos.
8. Definir `AppGateway`, implementar `QtGateway` e uma bridge Python mínima com resposta e erro tipados.
9. Provar round-trip React → WebChannel → Python → React e encerramento limpo.
10. Restringir o WebChannel ao build/origens aprovados e abrir links externos fora do shell.
11. Configurar CI de qualidade Python/TypeScript sem empacotamento e sem deploy web.

**Testes:** import limpo, build Vite, componente mínimo, smoke QWebEngine, contrato da bridge, origem negada e encerramento em ambiente novo.

**Portão:** o build estático abre/fecha no shell, o round-trip tipado passa e todas as verificações reproduzem a partir dos lockfiles.

## Etapa 2 — Contratos do domínio antes do banco

**Objetivo:** fixar a linguagem do produto sem acoplar ao SQLite.

**Status:** concluída em 2026-08-26. O domínio e os casos de uso centrais rodam com adaptadores em memória; a persistência SQLite começa na Etapa 3.

1. Implementar tipos para UUID, UTC timestamp, data operacional, gold e dinheiro em unidade mínima.
2. Definir enums/estados de atividade e movimentos.
3. Modelar perfil, conta, personagem, atividade, versões de regra/missão, cotações, registro diário, conclusão, sessão com participantes, detalhe da Torre, item, movimento, venda e transação.
4. Definir portas de repositório e unidade de trabalho.
5. Implementar regras de conclusão idempotente, correção e cálculo derivado somente a partir de regras confirmadas.
6. Criar relógio e gerador de IDs injetáveis.

**Testes:** invariantes, transições válidas/inválidas, limites numéricos, timezone e idempotência.

**Portão:** casos de uso centrais executam em memória sem importar PySide6 ou SQLite.

## Etapa 3 — Banco v1, migrations e recuperação

**Objetivo:** persistir sem risco silencioso de perda.

**Status:** concluída em 2026-08-26. O schema v1 e os índices mínimos são migrations SQL versionadas; a abertura do app prepara o banco pessoal, e as integrações exercitam repetição, checksum, falha, backup e restauração em bancos temporários.

1. Implementar resolução por `QStandardPaths.AppLocalDataLocation` (`%LOCALAPPDATA%` no Windows), separada da instalação.
2. Permitir que execução manual e futura instalação apontem para esse banco estável; criar trava que proíbe testes de usá-lo.
3. Criar conexão SQLite com FKs ativas, timeout e transações explícitas.
4. Implementar tabela/runner de migrations com ordem e checksum.
5. Criar `001_initial.sql` com entidades da [[04 - Modelo de Dados e Supabase]].
6. Criar `002_indexes.sql` a partir das consultas do vertical slice.
7. Implementar backup consistente e verificação antes de migration.
8. Implementar `quick_check`, `foreign_key_check`, falha segura e restauração preservando o original.
9. Recusar escrita quando o schema for mais novo que o suportado pelo build atual.
10. Criar fixtures de bancos v0/v1 e migrations interrompidas.

**Testes:** instalação limpa, migration repetida, checksum divergente, falha no meio, restauração, constraints e concorrência básica.

**Portão:** nenhuma falha simulada perde a única cópia; schema e backup são verificáveis.

## Etapa 4 — Repositórios e casos de uso operacionais

**Objetivo:** completar uma rotina diária pela camada de aplicação.

**Status:** em execução. O vertical slice SQLite de conta/personagem/dungeon, regras confirmadas, conclusão idempotente, reabertura, sessão base da Torre e drops com snapshot de valor está implementado. A fixture dourada 2×5, a projeção inicial de gold previsível, as cotações versionadas de Sacos PvE e o primeiro card real da tela Hoje, exposto pela bridge, também existem; ainda faltam os demais read models operacionais.

1. Implementar repositories SQLite de perfil, conta e personagem.
2. Implementar catálogo das nove dungeons, duas missões por regra e seleção configurável por personagem/plano.
3. Criar consulta que materializa/retorna o estado do dia sem apagar o dia anterior.
4. Implementar `complete_activity`, `skip_activity`, `reopen_activity` e salvamento atômico do resumo do personagem.
5. Marcar uma dungeon como feita gera cinco conclusões, aplica as duas missões e soma cinco Sacos PvE na mesma transação.
6. Implementar sessão opcional e registro de runs, duração, gold, sacos e notas.
7. Implementar sessão independente da Torre com participantes opcionais, custo fixo de 25.000, conclusão e drops relevantes.
8. Implementar catálogo e drops com preço snapshot.
9. Implementar cotações do Saco PvE e read models que separam gold fixo, valor estimado, custos e realizado.
10. Criar read models de cards, resumo, drops recentes e série mensal.
11. Criar fixture determinística com duas contas e cinco personagens por conta.

**Testes:** transações, reabertura, virada do dia/timezone, queries e reconciliação de totais.

**Portão:** fixture 2×5 produz exatamente os estados e totais esperados sem lógica na UI nem recompensas inventadas.

## Etapa 5 — Design system React e shell fiel

**Estado em 2026-08-26:** baseline macro 1680×941 aprovado; tokens, marca, ícones, sidebar, header, cards, tabela, coluna direita e `DashboardModuleHost` com registro confiável/lazy loading estão implementados. Permanecem janela sem moldura e validações nos viewports/escalas adicionais.

**Objetivo:** construir a geometria e os componentes antes de ligar todas as ações.

1. Extrair medidas e cores da referência; registrar tokens finais.
2. Selecionar e empacotar fonte e ícones gerais com licença compatível; usar iniciais/marcador neutro para personagens.
3. Criar janela PySide6, comportamento de arrastar, minimizar, maximizar/restaurar e fechar; expor somente capacidades necessárias ao React.
4. Criar tokens de cor, tipografia, spacing, radius, elevation e motion.
5. Implementar Sidebar, Header, Panel, StatCard, StatusBadge, ProgressBar e botões.
6. Definir contrato/registro de módulos e `DashboardModuleHost` React com grade responsiva e lazy loading controlado.
7. Implementar estados de foco, hover, pressed, disabled, loading e error.
8. Validar 1680×941, 1440×810, 1280×720 e escala 100/125/150%.

**Testes:** Vitest/Testing Library, smoke no QWebEngine, navegação por teclado e screenshots por componente no shell desktop.

**Portão:** shell e componentes macro aprovados por overlay antes de duplicar imperfeições nas páginas.

## Etapa 6 — Tela Hoje somente leitura

**Estado em 2026-08-26:** leitura SQLite já alimenta estimativa, personagens, runs concluídas, sessões da Torre, cinco drops recentes e série/total mensal. Ocultação/restauração dos módulos está persistida em layout versionado e desmonta o gráfico mensal. O baseline completo está em `design-qa.md`. Permanecem virtualização e gráfico com fallback textual detalhado.

**Objetivo:** reproduzir o mockup usando dados reais do SQLite.

1. Implementar query/read model Python do dia, DTOs da bridge e hooks/estado React correspondentes.
2. Montar cards com gold fixo, Sacos PvE, estimativa pela cotação atual e custos separados; sem cotação, não inventar total.
3. Criar lista virtualizada de personagens, ranking, marcador neutro, classe, progresso opcional, tempo e status.
4. Criar coluna Resumo do dia e Últimos drops.
5. Implementar gráfico mensal acessível com fallback textual.
6. Implementar estados sem perfil, sem personagens, sem atividade, carregando e erro recuperável.
7. Rodar overlay/diff da tela completa com a fixture dourada.
8. Provar que ocultar Desempenho mensal desmonta o componente, interrompe consultas/timers e preserva/restaura a preferência.

**Testes:** contrato gateway, componentes, formatação, lista grande, vazios, erros e baseline visual no shell.

**Portão:** tela deriva todos os dados do banco e atende os critérios de [[08 - Design e Interface]].

## Etapa 7 — Interação rápida e captura opcional

**Estado em 2026-08-26:** resumo diário por personagem salva seleções em uma transação, conclui/reabre ciclos de cinco rodadas e atualiza o dashboard. A Torre possui fluxo separado e transacional com custo fixo, participantes opcionais e drops relevantes. Permanecem drops/notas no resumo de dungeon, desfazer/histórico, atalhos e validação específica de clique duplo na UI.

**Objetivo:** tornar Hoje utilizável durante o jogo sem fricção.

1. Abrir o resumo pelo personagem, exibindo seu nome e somente as dungeons selecionadas.
2. Marcar uma dungeon como feita assume cinco rodadas e calcula as duas missões + cinco Sacos PvE.
3. Preparar componente futuro de checkboxes/rodadas sem exigir seu uso no MVP.
4. Capturar drops e notas no mesmo resumo; duração permanece detalhe opcional.
5. Salvar todas as mudanças do resumo numa única transação.
6. Criar ação própria “Nova sessão de Torre”, fora do checklist do personagem.
7. Na Torre, registrar participantes opcionais, custo, conclusão, drops relevantes e observações.
8. Oferecer desfazer imediato e reabrir pelo histórico.
9. Atualizar cards, linha, resumo e gráfico incrementalmente.
10. Garantir idempotência contra clique duplo e reenvio.
11. Definir atalhos de teclado e ordem de foco.

**Testes:** casos de uso via `QtGateway`, duplo clique, cancelamento, erro de escrita e consistência após reiniciar.

**Portão:** resumo calcula o ciclo confirmado das dungeons; Torre funciona como sessão independente; ambos persistem após reiniciar.

## Etapa 8 — Cadastros e configuração

**Estado em 2026-08-27:** cadastro e edição segura de contas/personagens, herança da rotina global, ativação das nove dungeons e configuração persistente dos módulos estão funcionais. Edição preserva IDs, vínculos e fatos já registrados. Permanecem arquivamento seguro, ordenação manual, catálogo/cotação editáveis e demais configurações locais.

**Objetivo:** eliminar dependência de dados-semente.

1. Criar onboarding do perfil local.
2. Criar CRUD/arquivamento de contas e servidores.
3. Criar CRUD/ordenação/arquivamento de personagens.
4. Criar catálogo das nove dungeons, planos/seleções reutilizáveis e vínculo por personagem.
5. Criar catálogo básico de itens, incluindo Saco PvE, e fluxo de cotação atual.
6. Criar configurações de timezone, locale, tema, banco estável e backups; o reset permanece à meia-noite local.
7. Criar Configurar visualização: mostrar/ocultar módulos, restaurar padrão e persistir layout versionado.
8. Prevenir exclusão física de entidades referenciadas.

**Testes:** validações, duplicatas, soft delete, reativação, ordenação e onboarding interrompido.

**Portão:** usuário inicia do zero sem editar arquivo/SQL e mantém o histórico ao arquivar cadastros.

## Etapa 9 — Histórico, inventário e financeiro

**Status:** em execução. Histórico de farm, vendas multimoeda, despesas de VIP/Torre e lançamento manual de despesas em gold estão disponíveis; VIP preserva expiração UTC com horas e permite ajustar a validade sem duplicar custo; despesas manuais possuem histórico, correção por substituição e estorno auditável. Inventário e correções auditadas de sessões permanecem pendentes.

**Objetivo:** transformar os fatos dormentes em rastreabilidade útil.

1. Criar histórico com filtros por período, conta, personagem e atividade.
2. Permitir correção auditada, mostrando impacto nos totais.
3. Implementar movimentos de inventário e saldo derivado.
4. Ligar drops a movimentos de entrada na mesma transação.
5. Implementar vendas e transações relacionadas sem `float`.
6. Preservar preço/valor no momento do evento.
7. Criar mecanismos de ajuste explícito em vez de editar saldo diretamente.

**Testes:** reconciliação dos ledgers, correção, estorno, soft delete e snapshots históricos.

**Portão:** qualquer saldo ou total exibido pode ser explicado por seus fatos de origem.

## Etapa 10 — Relatórios e exportação

**Status:** em execução. KPIs e gráficos de produção/vendas existem; a meta mensal agora é persistida por mês/workspace e os cards possuem navegação operacional. A Home já registra sessões de rotina com pausa/retomada, e os relatórios exibem histórico, totais mensais/semanais e comparação da semana anterior. Inventário, filtros e exportação ainda não atendem o portão desta etapa.

**Objetivo:** responder perguntas operacionais sem criar novas fontes de verdade.

1. Produção diária/mensal por conta, personagem e atividade.
2. Gold por tempo/run apenas quando os denominadores existirem.
3. Conclusão, duração e tendência.
4. Drops, inventário, vendas, receita e conversão com definições visíveis.
5. Exportar CSV/JSON versionado, em UTC e com moeda explícita.
6. Validar consultas em base grande e criar índices somente após medição.

**Testes:** fixtures com respostas conhecidas, ausência de denominador, filtros e export/import round-trip quando aplicável.

**Portão:** relatórios reconciliam com consultas de controle e permanecem responsivos no volume-alvo.

## Etapa 11 — Robustez, acessibilidade e desempenho

**Objetivo:** preparar o produto para uso diário prolongado.

1. Medir startup, consultas, memória e atualização da lista.
2. Corrigir gargalos com evidência e planos de consulta.
3. Testar queda/encerramento durante escrita e migration.
4. Finalizar modo seguro, restauração e diagnóstico sanitizado.
5. Validar teclado, leitor de tela quando viável, contraste, redução de movimento e DPI.
6. Testar paths com espaços, Unicode, perfil sem permissão e disco cheio.
7. Executar soak test com o app aberto e atualizações repetidas.
8. Testar manualmente desenvolvimento e build instalado alternando sobre o mesmo banco compatível.
9. Provar que a suite automatizada aborta antes de tocar o banco pessoal.
10. Testar layouts antigos com módulo removido/novo e garantir fallback para defaults.

**Portão:** metas de desempenho e matriz de falhas passam sem perda silenciosa.

## Etapa 12 — Empacotamento pessoal posterior

**Objetivo:** quando houver benefício real, entregar um aplicativo Windows pessoal sem alterar o banco usado durante o desenvolvimento.

1. Executar spike de PyInstaller com Qt WebEngine/WebChannel, subprocessos Qt, fontes, ícones e `frontend/dist`.
2. Criar instalador Inno Setup apontando o app para o diretório estável de dados.
3. Fixar versões/configuração das ferramentas e registrar limitações.
4. Criar pacote sem console, metadados, ícone e licenças.
5. Garantir que instalação e dados usem diretórios separados.
6. Testar instalação limpa, atualização, alternância com execução manual, rollback documentado e reinstalação.
7. Assinar artefatos quando disponível e gerar checksums.
8. Escrever notas de release, versão do schema e recuperação.

**Portão:** pacote funciona em VM Windows limpa sem Python global e preserva dados ao atualizar.

## Etapa 13 — Fechamento do produto local e operação contínua

**Objetivo:** estabelecer manutenção previsível.

1. Revisar todos os critérios da [[01 - Fonte da Verdade]].
2. Fechar bugs P0/P1, dívida de migrations e gaps de acessibilidade.
3. Testar upgrade desde toda versão publicada suportada.
4. Auditar dependências, licenças, logs e segredos.
5. Congelar baseline visual e fixtures de compatibilidade.
6. Publicar manual de backup/recuperação e política de suporte.
7. Atualizar roadmap e registrar decisões substituídas.

**Portão:** checklist de release completo, artefato reproduzível e caminho de recuperação exercitado.

## Extensões pós-MVP condicionais

As etapas seguintes não pertencem à sequência obrigatória do produto local e não começam automaticamente após a Etapa 13.

## Etapa 14 — Validação do canal web e preparação remota futura

**Pré-condição:** decisão explícita após validação do produto, necessidade real do navegador/login e disponibilidade de projeto Supabase.

**Objetivo:** reutilizar o frontend React e provar que o modelo local migra conceitualmente antes de expor dados reais.

1. Validar demanda, escopo do canal web, hospedagem, custos e política de dados.
2. Reconsultar documentação/changelog do Supabase e registrar nova ADR técnica.
3. Criar projeto/ambiente Supabase somente quando houver slot/conta autorizada pelo proprietário.
4. Escrever migrations Postgres equivalentes, aceitando diferenças físicas.
5. Modelar usuários, memberships e associação ao `workspace_id` local.
6. Criar RLS por workspace e grants mínimos para todas as tabelas expostas.
7. Implementar testes com dois usuários/dois workspaces e tentativas negativas.
8. Publicar API Python e implementar `HttpGateway` contra o mesmo contrato sem alterar os componentes React.
9. Hospedar o build React e adicionar testes específicos do runtime web.
10. Documentar mapeamento local/remoto e versionamento de payload.

**Portão:** o mesmo frontend funciona nos dois runtimes, schema/policies passam e o app local continua utilizável sem configuração Supabase.

## Etapa 15 — Sincronização bidirecional opcional

**Pré-condição:** provar que manter escrita local e remota simultaneamente é necessário. Se desktop e navegador puderem usar somente o banco remoto, não implementar sync bidirecional.

**Objetivo:** adicionar sincronização sem transformar falha de rede em perda de trabalho.

1. Implementar armazenamento seguro de sessão conforme cada runtime.
2. Vincular workspace/perfil local ao membership remoto preservando IDs.
3. Implementar outbox transacional: fato e item da fila são salvos juntos.
4. Criar upload inicial idempotente, retomável e com progresso real.
5. Implementar push em lotes, retry com backoff e erros observáveis.
6. Implementar pull incremental, tombstones e cursor durável.
7. Aplicar política de conflitos por entidade; ledgers permanecem orientados a eventos.
8. Recalcular/readquirir read models após merge.
9. Testar desconexão prolongada, relógios divergentes, dois dispositivos e reinstalação.

**Portão:** dois dispositivos convergem para os mesmos fatos/totais; duplicação, conflito e falha de rede têm testes de recuperação.

## Regra de mudança deste plano

Uma mudança que altere ordem, dados persistidos, compatibilidade, UX principal ou segurança requer atualização da fonte da verdade/ADR e do portão afetado antes da implementação.
