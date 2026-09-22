---
tipo: dados
status: ativa-v1
atualizado_em: 2026-08-27
---

# Modelo de Dados e Supabase

## Filosofia

Persistir **fatos e contexto histórico**, não somente o estado atual nem métricas deriváveis. “Dado dormente” é aceito quando tem significado, baixo custo e origem clara; não justifica coletar informação pessoal ou criar colunas especulativas sem semântica.

## Convenções globais

- PK: UUID armazenado como `TEXT` no SQLite e `uuid` no Postgres.
- Escopo de propriedade: `workspace_id`; o MVP cria um workspace local com UUID estável. Usuários autenticados e memberships só entram na fase cloud.
- Auditoria: `created_at`, `updated_at`, `deleted_at` em UTC ISO-8601.
- Origem: `device_id` quando o registro puder ser sincronizado.
- Dia operacional: `activity_date` muda à meia-noite no fuso local configurado e permanece separado do timestamp UTC.
- Gold/quantidades: inteiros.
- Dinheiro: inteiro em unidade mínima (`amount_minor`) + código ISO da moeda.
- Status: strings legíveis com validação de domínio e `CHECK` quando adequado.
- Preços históricos: snapshot no evento que os utilizou.
- Exclusão sincronizável: soft delete; limpeza física é manutenção explícita.
- Extensões: `metadata_json`, versionado e limitado a dados não essenciais.
- Todas as tabelas de catálogo, operação, preferências e ledger pertencentes ao produto carregam `workspace_id`, com unicidade e consultas escopadas por workspace.

## Entidades iniciais

### Identidade e catálogo

| Tabela | Responsabilidade | Campos essenciais adicionais |
|---|---|---|
| `workspaces` | Unidade estável de propriedade dos dados | `name`, `mode`, `created_at` |
| `local_profiles` | Preferências locais do operador | `workspace_id`, `display_name`, `timezone`, `locale` |
| `accounts` | Conta de jogo | `name`, `server_name`, `notes`, `is_active` |
| `characters` | Personagem de uma conta | `account_id`, `name`, `class_name`, `level`, `sort_order`, `is_active`, `notes` |
| `activities` | Definição reutilizável de atividade | `name`, `category`, `frequency_type`, `default_target_amount`, `is_active`, `is_special` |
| `character_activities` | Dungeons/atividades habilitadas por personagem | `character_id`, `activity_id`, `target_amount`, `sort_order`, `is_active` |
| `activity_rule_versions` | Regras válidas em um período | `activity_id`, `effective_from`, `effective_to`, `max_completions`, `target_amount`, `rules_status`, `notes` |
| `activity_reward_rules` | Recompensa por missão e rodada | `rule_version_id`, `mission_key`, `mission_limit_type`, `reward_type`, `item_id`, `amount_per_completion` |
| `activity_cost_rules` | Custo versionado da atividade | `rule_version_id`, `cost_type`, `item_id`, `amount` |
| `activity_windows` | Janela de disponibilidade | `rule_version_id`, `weekday`, `opens_at_local`, `duration_seconds`, `timezone` |
| `items` | Catálogo de itens | `name`, `category`, `rarity`, `icon_ref`, `notes` |
| `market_price_quotes` | Histórico do preço de mercado configurado | `item_id`, `unit_value_gold`, `observed_at`, `source`, `notes` |
| `gold_exchange_quotes` | Cotação gold → moeda real | `gold_amount`, `amount_minor`, `currency`, `observed_at`, `source`, `notes` |

### Operação e fatos

| Tabela | Responsabilidade | Campos essenciais adicionais |
|---|---|---|
| `daily_activity_entries` | Estado/fato de uma atividade no dia | `character_activity_id`, `activity_date`, `status`, `progress_amount`, `started_at`, `completed_at`, `skipped_at`, `notes` |
| `activity_completions` | Conclusões individuais ou geradas em lote | `daily_activity_entry_id`, `sequence_no`, `completed_at`, `gold_reward_snapshot`, `pve_bags_snapshot`, `rule_version_id` |
| `farm_sessions` | Sessão independente de farm | `session_type`, `primary_character_id`, `activity_id`, `activity_date`, `started_at`, `finished_at`, `duration_seconds`, `runs_count`, `gold_earned`, `pve_bags_earned`, `status`, `notes` |
| `farm_session_participants` | Personagens participantes da sessão | `farm_session_id`, `character_id`, `role`, `joined_at`, `left_at` |
| `tower_session_details` | Detalhe da sessão de Torre | `farm_session_id`, `guild_name_snapshot`, `opened_at`, `entry_cost_gold_snapshot`, `completed`, `completed_at`, `rules_version_id` |
| `farm_session_items` | Item obtido numa sessão | `farm_session_id`, `item_id`, `quantity`, `estimated_unit_value_at_drop`, `obtained_at` |
| `inventory_movements` | Ledger de estoque | `item_id`, `character_id`, `farm_session_id`, `movement_type`, `quantity_delta`, `unit_value_snapshot`, `occurred_at`, `notes` |
| `sales` | Evento comercial | `sale_type`, `status`, `gold_quantity`, `item_description`, `item_quantity`, `original_amount_minor`, `currency`, `exchange_rate_micros`, `exchange_rate_source`, `real_amount_minor`, `converted_currency`, `idempotency_key`, `sold_at`, `fees_minor`, `notes` |
| `transactions` | Ledger financeiro | `type`, `category`, `amount_gold`, `amount_minor`, `currency`, `character_id`, `item_id`, `sale_id`, `farm_session_id`, `occurred_at`, `description`, `notes` |

### Sistema

| Tabela | Responsabilidade | Campos essenciais adicionais |
|---|---|---|
| `devices` | Identificar origem de mudanças | `name`, `platform`, `app_version`, `last_seen_at` |
| `settings` | Preferências tipadas e versionadas | `scope`, `key`, `value_json`, `schema_version` |
| `schema_migrations` | Histórico das migrations locais | `version`, `name`, `checksum`, `applied_at`, `app_version` |
| `audit_log` | Alterações sensíveis e correções | `entity_type`, `entity_id`, `action`, `before_json`, `after_json`, `occurred_at` |
| `dashboard_layouts` | Layout salvo do dashboard | `name`, `is_default`, `layout_version`, `created_at`, `updated_at` |
| `dashboard_layout_items` | Estado de cada módulo | `layout_id`, `module_key`, `enabled`, `sort_order`, `region`, `column_span`, `row_span`, `settings_json` |
| `routine_schedules` | Rotina/lembrete configurável futuro | `name`, `start_time_local`, `timezone`, `weekdays_mask`, `notification_offset_minutes`, `enabled` |
| `work_routine_sessions` | Tempo operacional iniciado pelo usuário | `status`, `started_at`, `paused_at`, `finished_at`, `accumulated_seconds`, `notes` |

`sync_queue`, `sync_state`, usuários remotos e memberships não entram na migration inicial. Serão adicionados por migration quando a sincronização tiver caso de uso validado; UUIDs, `workspace_id`, timestamps e snapshots já preservam o caminho de migração sem criar infraestrutura dormente.

## Implementação SQLite v1

- `001_initial.sql` cria as entidades, restrições e chaves estrangeiras descritas acima.
- `002_indexes.sql` cria índices para recortes por workspace/data, personagem, atividade, item, cotação e transação.
- `003_activity_reward_pve_bags.sql` adiciona o snapshot de Sacos PvE por missão, necessário para persistir a regra confirmada de uma unidade por rodada.
- `004_currency_rates_and_sale_enhancements.sql` introduz cotações monetárias e snapshots de valor original/conversão das vendas.
- `005_sales_integrity.sql` adiciona descrição independente do comprador, origem da cotação, moeda convertida e chave de idempotência por workspace.
- O runner registra versão, nome, checksum, instante UTC e versão do aplicativo em `schema_migrations`.
- Antes de aplicar migrations pendentes a um banco existente, ele cria cópia consistente via backup SQLite, valida `quick_check` e registra metadata com checksum. A restauração preserva a cópia atual como arquivo de recuperação.

## Restrições importantes

- Único: `(account_id, name)` para personagem ativo, com política definida para soft delete.
- Único: `(character_activity_id, activity_date)` para o registro diário vigente.
- `quantity_delta` usa sinal: entrada positiva, saída negativa.
- `finished_at >= started_at`; `duration_seconds >= 0`.
- Status concluído requer `completed_at`; status não concluído não inventa horário de conclusão.
- Uma regra só participa de cálculo automático quando `rules_status = confirmed`; regras desconhecidas não produzem gold/sacos estimados.
- `activity_completions` é único por `(daily_activity_entry_id, sequence_no)` e guarda a regra/snapshot usado no cálculo.
- Sessão de Torre não pertence a um personagem: participantes ficam na tabela de junção e podem ser adicionados apenas quando útil ao histórico.
- Cada abertura da Torre gera exatamente um custo de 25.000 gold na sessão, independentemente de haver um, dois ou três personagens participantes.
- Torre registra conclusão e drops relevantes; piso/tentativa detalhados ficam fora do MVP.
- Uma cotação de mercado nunca altera transações antigas. Estimativas usam a cotação mais recente; venda/movimento histórico guarda `unit_value_snapshot`.
- FK sempre ativa; exclusão de catálogo com histórico usa `RESTRICT` ou soft delete, nunca cascade destrutivo.
- Índices começam pelos recortes reais: data, conta/personagem, atividade, item e campos de sync.

## Métricas derivadas, não persistidas como verdade

- gold por hora/run;
- total diário/mensal;
- gold e sacos PvE calculados a partir de conclusões × regra confirmada;
- valor estimado atual dos Sacos PvE usando a cotação mais recente;
- bruto previsível e, futuramente, líquido após custos de sessões como a Torre;
- quantidade atual do inventário (`SUM(quantity_delta)`);
- personagens concluídos;
- taxa de conclusão;
- ticket médio e receita por período.

Snapshots ou tabelas agregadas só serão adicionados após medição, com mecanismo claro de reconstrução.

## Regras conhecidas e pendentes de confirmação

O catálogo operacional dessas informações fica em [[10 - Regras do Jogo]].

| Regra | Estado | Tratamento no MVP |
|---|---|---|
| Dia vira à meia-noite local | Confirmada | Implementar desde a migration/caso de uso inicial |
| Torre vai do piso 1 ao 30 | Confirmada | O MVP registra apenas conclusão; regra permanece versionada |
| Torre custa 25.000 gold para abrir | Confirmada | Um custo por `tower_session_details` |
| Torre disponível todos os dias 20:00–22:00 | Confirmada pelo print | Janela versionada e aviso informativo |
| Registro da Torre 19:30–20:00 | Confirmada pelo print | Janela informativa; fechamento de roster após 20 minutos |
| Torre é separada do personagem diário | Confirmada | `farm_sessions` + participantes opcionais, sem `character_activities` |
| Dungeon usa ciclo-meta de 5 rodadas | Confirmada | `target_amount = 5`; marcar feita gera o ciclo completo |
| Cada rodada padrão dá 1 Saco PvE | Confirmada | Recompensa vinculada à Missão 1 |
| Gold das duas missões varia por dungeon | Confirmada | Catálogo em [[11 - Catálogo de Dungeons]] e snapshot por conclusão |

Ao marcar uma dungeon inteira como feita, o caso de uso gera cinco `activity_completions` na mesma transação, aplica as duas missões da versão vigente e registra cinco Sacos PvE. A seleção de quais dungeons entram na rotina continua configurável.

## Estimativa e preço do Saco PvE

- O usuário informa o preço de mercado atual; cada alteração cria uma `market_price_quote` em vez de sobrescrever a anterior.
- Cotação inicial do Saco PvE: 1.000 gold por unidade.
- A conversão para BRL usa `gold_exchange_quotes`; ponto de partida de R$ 0,07–R$ 0,08 por 1.000 gold, preservando a fonte/cotação utilizada.
- O dashboard prospectivo usa a cotação mais recente para valorar os sacos previstos/disponíveis.
- Uma venda efetiva registra quantidade, preço e momento próprios; relatórios realizados usam a venda, não a cotação atual.
- O read model pode exibir separadamente: gold fixo de missões, valor estimado dos sacos, custos de farm e total/líquido.

## Banco compartilhado entre desenvolvimento e instalação

- O banco de uso pessoal usa `QStandardPaths.AppLocalDataLocation`, que no Windows resolve dentro de `%LOCALAPPDATA%`, fora do source tree e da pasta de instalação e sem exigir administrador.
- Execução manual pode apontar para o mesmo caminho usado pelo executável instalado.
- O diretório é explícito na configuração/ambiente de desenvolvimento; não depende do diretório de trabalho.
- Testes automatizados abortam se o caminho resolvido não estiver dentro do diretório temporário do teste.
- Antes de uma migration, criar backup válido. Um build antigo recusa schema mais novo em modo somente leitura/erro orientado, sem tentar revertê-lo.

## Pipeline de migrations local

1. Abrir o banco e ativar `foreign_keys`, timeout e modo de journal aprovado nos testes.
2. Ler versão, checksums e integridade básica.
3. Se houver migrations pendentes, fechar escritas e criar backup com nome, versão e timestamp.
4. Verificar o backup abrindo-o em modo somente leitura e executando `quick_check`.
5. Aplicar cada migration em ordem, em transação quando suportado.
6. Registrar versão e checksum.
7. Executar `foreign_key_check` e teste de integridade.
8. Em falha, preservar banco e logs, restaurar cópia válida ou iniciar em modo seguro; nunca continuar silenciosamente.

## Fatos operacionais adicionais

`character_daily_missions` registra o checklist agregado de diárias por personagem e dia operacional. O fato pertence ao workspace, referencia o personagem e guarda somente `completed_at`; não se mistura a `daily_activity_entries` porque não representa uma dungeon, recompensa, consumo ou run.

`monthly_gold_targets` preserva uma meta de gold por `workspace_id` e mês no formato `YYYY-MM`. A meta é configurável e histórica: editar a meta de um mês não altera metas de outros meses nem fatos de farm já registrados. O leitor usa 25.000.000 gold apenas como fallback visual quando ainda não existe uma meta persistida para o mês.

`character_vip_subscriptions` preserva ativações de VIP por personagem, valor pago e início/expiração com precisão de data e hora em UTC (`activated_at` e `expires_at`). Os campos legados de data permanecem durante a migração compatível. Ajustar o tempo restante atualiza somente a vigência da assinatura ativa e não cria nova despesa. A despesa correspondente usa o ledger existente em `transactions` com `type = expense` e `category = vip`; a abertura de Torre permanece derivável de `tower_session_details`.

As despesas manuais não recebem tabela própria: são fatos `transactions` com `type = expense`, categoria controlada e `amount_gold` inteiro. Ao corrigir uma despesa, o lançamento anterior recebe `deleted_at`, um substituto é inserido e o `audit_log` registra antes/depois; estorno segue a mesma preservação. `work_routine_sessions` mantém no máximo uma sessão aberta por workspace; pausas consolidam o tempo decorrido e a retomada inicia novo trecho, sem depender do timer da interface. Relatórios de rotina usam somente sessões `completed`, `created_at` como início original, `finished_at` como término e `accumulated_seconds` como duração autoritativa.

A meta mensal continua persistida como `target_gold`, agora interpretada como gold equivalente: o read model soma `activity_completions.gold_reward_snapshot` e a quantidade de Sacos PvE ganhos multiplicada pela cotação atual. O valor dos sacos é prospectivo e pode mudar quando sua cotação muda; os fatos de produção não são alterados. A calculadora de BRL é somente apresentação e não persiste dados.

## Compatibilidade SQLite → Postgres/Supabase futuro

| Conceito | SQLite | Supabase/Postgres |
|---|---|---|
| UUID | `TEXT` validado pela aplicação | `uuid` |
| Timestamp | UTC ISO `TEXT` | `timestamptz` |
| Data operacional | ISO `TEXT` | `date` |
| JSON extra | JSON em `TEXT` | `jsonb` |
| Boolean | inteiro validado | `boolean` |
| Dinheiro | unidade mínima inteira | `bigint` + moeda |

O modelo conceitual e os casos de uso permanecem. O adaptador físico pode diferir; não tentar fazer SQLite fingir ser Postgres.

## Fases da cloud — fora do MVP

1. **Preparação local agora:** UUIDs, `workspace_id`, timestamps, soft delete, snapshots e repositórios isolados.
2. **Validação do produto:** confirmar que login, navegador ou múltiplos dispositivos resolvem uma dor real e obter um projeto Supabase disponível.
3. **Revalidação técnica:** consultar documentação/changelog atuais antes de escolher SDK, schema exposto e fluxo de Auth.
4. **Schema remoto conceitualmente equivalente:** migrations Postgres/Supabase separadas e testes de contrato; não reutilizar cegamente SQL do SQLite.
5. **Auth e memberships:** associar `auth.users` a workspaces sem alterar IDs dos fatos locais.
6. **RLS:** políticas baseadas em membership/propriedade para todas as tabelas expostas, grants mínimos e testes negativos entre usuários/workspaces.
7. **Gateway remoto:** `HttpGateway` no mesmo frontend React e API Python hospedada; `QtGateway` continua sendo o único gateway do MVP.
8. **Primeiro upload:** idempotente, interrompível e reconciliável; somente então adicionar outbox/sync state se sincronização bidirecional for necessária.
9. **Sync opcional:** push/pull, tombstones, cursores, conflitos e recuperação em segundo dispositivo.

## Dados que não devem ser coletados por padrão

- senha da conta do jogo;
- token do jogo;
- dados pessoais reais de compradores;
- conteúdo do clipboard ou telemetria não relacionada;
- segredo administrativo do Supabase.
