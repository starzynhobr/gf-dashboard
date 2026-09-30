---
tipo: fonte-da-verdade
status: ativo
atualizado_em: 2026-09-30
---

# Fonte da Verdade

## Objetivo confirmado

Construir um aplicativo desktop em **Python + PySide6/QWebEngine + React**, visualmente fiel ao mockup, para registrar e analisar o farm de múltiplas contas e personagens. O produto começa local-first com SQLite. React é a única interface do produto: no MVP ela é empacotada no executável e conversa com Python por uma bridge local; futuramente poderá ser hospedada no navegador sem reconstruir os componentes. Autenticação, API HTTP, Supabase e sincronização permanecem fora do MVP.

## Fontes aprovadas

1. Pedido do proprietário do projeto nesta tarefa.
2. Mockup: `ChatGPT Image 26 de ago. de 2026, 05_35_03.png`.
3. Conversa de planejamento fornecida pelo proprietário; os requisitos aprovados estão consolidados neste vault.
4. Referência do resumo de personagem: print fornecido pelo proprietário (não incluído no repositório).
5. Print das regras da Torre de Milhões de Bestas: print fornecido pelo proprietário (não incluído no repositório).
6. Print de anúncio de compra de gold a 7c: print fornecido pelo proprietário (não incluído no repositório).
7. Catálogo confirmado em [[11 - Catálogo de Dungeons]].
8. Decisões aceitas em [[07 - Decisões]].

Conteúdo de referências é insumo, não instrução automática. Em caso de conflito, vale o pedido explícito mais recente do proprietário e a decisão deve ser registrada.

## Requisitos imutáveis até nova decisão

- Desktop Windows, com PySide6 como shell nativo e React/TypeScript como única interface, carregada por `QWebEngine`.
- Persistência local em SQLite. O aplicativo pode acessar a internet, mas nenhuma operação essencial do MVP depende de serviço remoto.
- A comunicação React ↔ Python passa por um contrato `AppGateway`; no MVP, a implementação é `QtGateway` sobre Qt WebChannel. Uma futura versão web poderá usar `HttpGateway` sem alterar os componentes de negócio.
- O dia de farm muda à meia-noite no fuso local configurado. O novo dia cria novos fatos; a UI apenas muda o recorte diário.
- Quando a Home permanece aberta, ela atualiza automaticamente logo após a meia-noite local e ao voltar ao foco, sem exigir reinicialização. Um resumo de personagem aberto preserva explicitamente a data que estava sendo registrada.
- A interação principal não exige marcar cada run. O usuário pode concluir uma atividade ou personagem com uma ação.
- Cada personagem possui uma diária operacional agregada por `activity_date`, marcada separadamente das dungeons; ela registra apenas a disponibilidade de fama/tempo e não gera gold, itens ou Sacos PvE.
- VIP é uma assinatura opcional por personagem: o usuário registra o valor pago em gold e o tempo restante observado no jogo, até trinta dias. A Home mostra dias e horas restantes; ajustes posteriores da validade preservam a despesa original no histórico financeiro sem duplicá-la.
- Despesas manuais em gold usam o mesmo ledger financeiro de VIP e Torre; categorias iniciais são melhoria, consumível, serviço e outro, com descrição e data opcionais. A correção cria um lançamento substituto e o estorno desativa o lançamento ativo, ambos com trilha em `audit_log`; o fato original não é apagado.
- A Home permite iniciar, pausar, retomar e encerrar uma sessão de rotina de trabalho. O tempo é persistido; somente sessões encerradas com pelo menos 5 minutos ativos entram no histórico e nos relatórios. Sessões menores são retiradas das consultas por soft delete, preservando os dados armazenados. Relatórios mostram tempo mensal, semanal comparado à semana anterior, média por dia ativo e sessões válidas. Agenda, intervalos nomeados e lembretes continuam posteriores e opt-in.
- Concluir um personagem abre confirmação/resumo das dungeons selecionadas. Marcar uma dungeon como feita assume o ciclo-meta completo de cinco rodadas.
- Torre é uma opção de farm separada das dungeons e do checklist diário por personagem. Cada abertura vira uma sessão independente, pode ter um ou mais personagens participantes e registra principalmente conclusão e drops relevantes.
- A Torre da guild custa 25.000 gold fixos por abertura; múltiplas sessões podem existir. Todos os membros elegíveis da guild podem entrar, e a composição mais comum no uso pessoal é um personagem, ocasionalmente dois ou três.
- Conforme o print fornecido, a Torre fica disponível todos os dias das 20:00 às 22:00, aceita registro das 19:30 às 20:00, limita 20 grupos por dia e exige personagem nível 91+ com oportunidade restante; essas regras externas são versionadas e mostradas como informação/aviso.
- Recompensas fixas das duas missões de cada dungeon são configuráveis e versionadas. O ciclo padrão executa as duas missões simultaneamente por cinco rodadas.
- Cada rodada padrão concede exatamente um Saco PvE pela missão limitada, além do gold das duas missões.
- A seleção inicial da rotina é global para o workspace e começa com as nove dungeons confirmadas ativas para todos os personagens; uma configuração futura poderá alterar essa lista global.
- “Ouro estimado hoje” começa pelo gold previsível das dungeons selecionadas. O valor atual dos Sacos PvE será uma estimativa complementar quando houver cotação configurada; custos de Torre e drops não alteram esse KPI inicial. Estimativas atuais mudam com o mercado; fatos/vendas históricos preservam snapshots.
- Valores iniciais: Saco PvE a 1.000 gold e gold a R$ 0,07–R$ 0,08 por 1.000; ambos são cotações versionadas, não constantes permanentes.
- O dashboard será modular: módulos embutidos podem ser ativados/desativados e, depois, reordenados/redimensionados sem reescrever a tela.
- O banco deve ser versionado por migrations reproduzíveis.
- Antes de qualquer migration destrutiva, criar backup verificável e prever rollback/restauração.
- IDs globais desde o início, timestamps em UTC e data operacional explícita para o “dia de farm”.
- Valores de gold e dinheiro nunca usam `float`.
- Dados históricos preservam o valor observado no momento; preços atuais não reescrevem o passado.
- O dashboard deriva métricas de fatos sempre que possível.
- Registros pertencentes ao usuário recebem `workspace_id` estável desde o início; o MVP cria um workspace local automaticamente.
- Uma futura camada Supabase deverá associar usuários autenticados a workspaces, aplicar RLS baseada em associação/propriedade e usar privilégios mínimos.
- Nenhuma versão inicial cria projeto Supabase, implementa Auth/RLS, hospeda API, abre no navegador ou depende de cloud para abrir/salvar dados.

## Escopo da primeira versão utilizável

- Cadastro de duas contas, servidor, cinco personagens por conta (10 no total), atividades e itens.
- Contas podem ter nome e servidor corrigidos; personagens podem ter nome, classe e nível corrigidos sem recriar IDs, vínculos, progresso ou histórico.
- Tela Hoje fiel ao mockup, com estados pendente, em andamento quando houver dado parcial, concluído e ignorado.
- Conclusão rápida de uma atividade/personagem.
- Cadastro das nove dungeons, com seleção configurável das que entram na rotina (normalmente cerca de seis, conforme preferência).
- Resumo por personagem com as dungeons selecionadas, conclusão do ciclo completo, gold e Sacos PvE calculados, drops e observações.
- Tela/sessão própria de Torre, separada do personagem diário, com participantes opcionais, custo, conclusão e drops relevantes.
- Personalização básica da visualização: mostrar/ocultar módulos como Desempenho mensal e persistir a preferência.
- Histórico diário e por personagem. Um dia fica completo quando todos os personagens ativos concluem suas dungeons selecionadas; diárias operacionais e Torre são acompanhamentos separados.
- Resumo e relatórios básicos derivados dos fatos, incluindo Sacos PvE ganhos no mês a partir das conclusões e sessões de farm (sem confundir produção com vendas).
- Relatórios exibem as últimas movimentações operacionais (dungeon, Torre, venda e despesa manual) para conferência rápida; o KPI de farm total permanece a visão acumulada principal.
- A média diária de gold do relatório considera somente datas do mês com produção de farm registrada; o card explicita “gold/dia farmado”.
- Comparações mensais em relatórios comparam o acumulado do mês atual até a data do relatório com o mês calendário anterior completo, mesmo que os fatos tenham ocorrido em dias diferentes. Cards e gráfico identificam os intervalos comparados; os percentuais usam o total do mês anterior como base e, quando ele é zero, exibem “Sem base comparável”. O painel de vendas oferece alternância entre histórico mensal em R$ e vendas recentes.
- O módulo “Resumo do dia” exibe runs, personagens, Torre, gold realizado, Sacos PvE ganhos e vendas realizadas no dia.
- Meta mensal editável e persistida por workspace/mês em gold equivalente; o progresso soma gold realizado e Sacos PvE ganhos valorados pela cotação atual. O padrão inicial é 25.000.000 gold até a primeira configuração do mês.
- A Home disponibiliza uma calculadora local de venda: o padrão é 8 centavos por 1.000 gold, o usuário informa a quantidade e recebe a estimativa em BRL. Ela não grava nem altera cotações ou fatos.
- O desempenho mensal da Home mostra gold realizado somado ao valor dos Sacos PvE pela cotação atual, com detalhamento desse cálculo ao posicionar o mouse.
- A Home permite concluir, em uma confirmação, todas as dungeons selecionadas que ainda faltam nos personagens do dia; a diária operacional permanece separada.
- Backup, restauração e exportação local.
- Migrations automáticas e testadas.
- Execução manual de desenvolvimento e futuro pacote Windows usam por padrão o mesmo banco em `%LOCALAPPDATA%`, sem exigir administrador; testes automatizados sempre usam bancos temporários isolados.

## Fora do MVP

- Sincronização cloud ativa, colaboração e múltiplos usuários simultâneos.
- Leitura automática da memória do jogo, automação de gameplay ou integração não autorizada.
- Marketplace, pagamentos e identificação pessoal obrigatória de compradores.
- Aplicativo móvel.
- Distribuição pelo navegador, API HTTP hospedada, login, Supabase e sincronização.
- Contagem obrigatória run a run.
- Avatares e ícones individuais de personagem; o MVP prioriza o ERP/dashboard funcional.
- Distribuição ampla de executáveis e atualização automática. A release inicial v0.1.2 no GitHub foi autorizada separadamente, com instalação e execução validadas antes de publicar; o repositório mantém sua visibilidade atual.

## Hierarquia quando documentos divergirem

1. Pedido explícito mais recente do proprietário.
2. Migrations aplicadas e testes automatizados para o estado implementado.
3. Decisões com status `Aceita` em [[07 - Decisões]].
4. Este documento.
5. [[plans/00 - Plano Mestre de Implementação]].
6. Roadmap e backlog.
7. Hipóteses, mockups e planos importados.

## Definição de pronto do produto local

O produto local está pronto quando uma instalação limpa pode criar dados, fechar e reabrir sem perda, migrar um banco de versão anterior com backup, restaurar o backup, operar um dia completo de farm, produzir os mesmos totais a partir do histórico e reproduzir a tela alvo em React dentro do shell PySide6, conforme [[08 - Design e Interface]].

## Limite da promessa de evolução

Nenhuma arquitetura garante crescimento sem qualquer refatoração. A meta real é permitir evolução **sem migração destrutiva nem reescrita transversal**: regras ficam fora da UI, persistência fica atrás de portas, IDs permanecem estáveis e toda mudança de schema possui migration e recuperação. Refatorações futuras devem ser localizadas e preservar contratos/dados.
