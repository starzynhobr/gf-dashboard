---
tipo: decisoes
status: ativo
atualizado_em: 2026-08-30
---

# Decisões

## Estados

- **Aceita:** orienta a implementação atual.
- **Proposta:** precisa de spike ou aprovação.
- **Substituída:** preservada para histórico, com link para a nova decisão.

## Registro

| ID | Estado | Decisão | Consequência principal |
|---|---|---|---|
| ADR-001 | Substituída por ADR-038 | Python + PySide6 + QML | React passa a ser a única interface para preservar reuso futuro |
| ADR-002 | Aceita | SQLite local-first | O fluxo essencial funciona offline |
| ADR-003 | Aceita | Registrar fatos e derivar métricas | Dashboards futuros podem ser criados sem reescrever o histórico |
| ADR-004 | Aceita | Conclusão rápida; runs detalhadas são opcionais | Baixo atrito durante o jogo |
| ADR-005 | Substituída por ADR-039 | UUID, UTC, `activity_date`, soft delete e `user_id` desde v0.1 | Propriedade futura será escopada por workspace, não diretamente por usuário |
| ADR-006 | Aceita | Migrations SQL numeradas, com checksum e backup verificado | Alterações de schema são reproduzíveis e recuperáveis |
| ADR-007 | Aceita | Gold e dinheiro como inteiros | Evita erro de precisão |
| ADR-008 | Aceita | Ledger para inventário e financeiro | Saldo é reconstruível e auditável |
| ADR-009 | Aceita | Snapshots de valor no evento histórico | Mudança de preço atual não altera resultados passados |
| ADR-010 | Substituída por ADR-040 | QML sem acesso direto a SQL | A mesma separação passa a existir pelo `AppGateway` React |
| ADR-011 | Aceita | Supabase é opcional e posterior ao local confiável | Cloud não bloqueia o MVP nem o uso offline |
| ADR-012 | Aceita | Fidelidade medida no viewport 1680×941 | O mockup possui um alvo reproduzível |
| ADR-013 | Proposta | SQL explícito e repositórios, sem ORM no MVP | Validar no primeiro vertical slice antes de consolidar |
| ADR-014 | Substituída por ADR-038 | Gráfico mensal com QML `Canvas`/`Shape` | A implementação visual passa ao ecossistema React |
| ADR-015 | Aceita | Empacotamento futuro com PyInstaller + Inno Setup | Distribuição fica adiada, mas o caminho de instalação já está escolhido |
| ADR-016 | Aceita | Dia de farm vira à meia-noite no fuso local configurado | `activity_date` é derivada pela meia-noite local e preservada no fato |
| ADR-017 | Substituída por ADR-024 | Torre como atividade especial atribuída ao personagem | A compreensão mais recente tornou a Torre uma sessão independente |
| ADR-018 | Substituída por ADR-024 | Resumo do personagem com Dungeon e Torre | Torre sai do checklist diário do personagem |
| ADR-019 | Aceita | Recompensas automáticas vêm de regras versionadas | Valores confirmados depois não exigem reescrever o histórico |
| ADR-020 | Substituída por ADR-031 | Gold estimado totalmente dormente | A base previsível e a cotação do Saco PvE agora foram definidas |
| ADR-021 | Aceita | Avatares individuais não fazem parte do MVP | Prioridade é funcionamento ERP/dashboard; usar marcador neutro/iniciais |
| ADR-022 | Aceita | Fixture real do MVP tem 2 contas e 5 personagens por conta | Os testes funcionais refletem os 10 personagens de uso real |
| ADR-023 | Aceita | Desenvolvimento manual e app instalado podem compartilhar o banco estável | Testes permanecem isolados e builds incompatíveis devem recusar o schema |
| ADR-024 | Aceita | Torre é sessão de farm independente das dungeons/checklist diário | Pode ocorrer ocasionalmente e envolver 1–3 personagens sem ser atribuída a todos |
| ADR-025 | Aceita | Cada abertura da Torre da guild custa 25.000 gold fixos | O custo é lançado uma vez por sessão, independentemente do número de participantes |
| ADR-026 | Aceita | Torre registra conclusão e drops relevantes | Piso/tentativas detalhadas não fazem parte do fluxo principal |
| ADR-027 | Aceita | Existem 9 dungeons cadastradas e a rotina usa uma seleção configurável | A preferência comum de cerca de 6 não vira regra global |
| ADR-028 | Aceita | Ciclo padrão executa duas missões simultâneas por 5 rodadas | Missão limitada dá gold + 1 saco; missão ilimitada dá somente gold |
| ADR-029 | Aceita | Marcar dungeon como feita assume as 5 rodadas | Não solicitar quantidade no fluxo normal |
| ADR-030 | Aceita | Cada rodada padrão concede exatamente 1 Saco PvE | Concluir uma dungeon gera 5 sacos no ciclo atual |
| ADR-031 | Aceita | MVP recebe manualmente o preço atual do Saco PvE e salva cada cotação | Dashboard atualiza com o mercado; histórico mantém snapshots e dispensa integração externa |
| ADR-032 | Aceita | Banco pessoal fica no caminho padrão em `%LOCALAPPDATA%` | Não exige administrador e é compartilhado por dev manual/instalação |
| ADR-033 | Aceita | Valores iniciais: Saco PvE 1.000 gold e gold 7–8c por 1.000 | Cotações são versionadas e podem mudar sem alterar históricos |
| ADR-034 | Substituída por ADR-041 | Dashboard usa registro de módulos QML ativáveis | O contrato modular passa a usar componentes React |
| ADR-035 | Aceita | Personalização começa por visibilidade e ordem | Redimensionamento/drag-and-drop vêm depois de validar o uso real |
| ADR-036 | Substituída por ADR-038 | Permanecer em PySide6 + QML no produto local | O proprietário aceitou a bridge para evitar futura reescrita do frontend |
| ADR-037 | Proposta | Rotina de trabalho com horário e lembretes configuráveis | Implementar depois do fluxo diário confiável e com opt-in |
| ADR-038 | Aceita | PySide6/QWebEngine como shell e React/TypeScript/Vite/Tailwind como única UI | O MVP continua instalável/local e a interface pode ser reutilizada num canal web futuro |
| ADR-039 | Aceita | UUID e `workspace_id` desde v0.1; workspace local automático | Auth/memberships podem ser adicionados depois sem reatribuir fatos por usuário |
| ADR-040 | Aceita | Frontend acessa casos de uso somente por `AppGateway`; MVP usa `QtGateway`/WebChannel | Componentes não dependem de Python, SQLite ou runtime desktop |
| ADR-041 | Aceita | Dashboard usa registro de módulos React ativáveis | Visibilidade, ordem e expansão ficam localizadas e persistíveis |
| ADR-042 | Aceita | Não implementar navegador, API HTTP, Supabase, Auth, RLS ou sync no MVP | Validação local não paga custo de infraestrutura/testes remotos prematuramente |
| ADR-043 | Aceita | Canal web futuro reutiliza o mesmo React por `HttpGateway` e API hospedada | A evolução troca o adaptador e adiciona segurança/infraestrutura, não reconstrói a UI |
| ADR-044 | Aceita | MVP usa WebChannel, não servidor HTTP local | Menor superfície operacional agora; a API HTTP nasce apenas quando houver canal web |
| ADR-045 | Aceita | Rotina inicial global com as nove dungeons selecionadas | Fixture e dashboard começam determinísticos; a configuração global pode reduzir a seleção depois |
| ADR-046 | Aceita | “Ouro estimado hoje” começa pelo gold previsível das dungeons selecionadas | Não deduz Torre nem depende de drops; Sacos PvE aparecem como estimativa complementar quando houver cotação |
| ADR-047 | Aceita | Venda calcula conversão no backend e usa chave de idempotência | O frontend só fornece intenção e valor/cotação; o fato preserva origem, moeda e total BRL derivados |
| ADR-048 | Aceita | Diárias são um fato operacional agregado por personagem e `activity_date` | Elas mostram a preparação de fama/tempo sem contaminar recompensas de dungeon, gold ou inventário |
| ADR-049 | Aceita | Meta de gold é configurável e persistida por workspace/mês | O dashboard usa 25.000.000 apenas como fallback antes da primeira configuração mensal |
| ADR-050 | Aceita | VIP é assinatura por personagem de trinta dias, com custo em gold | A ativação cria fato de vigência e despesa `vip`; relatórios separam VIP e custo de Torre |
| ADR-051 | Aceita | Média diária de gold considera somente dias com produção registrada | Evita diluir o desempenho pelos dias de calendário sem farm e preserva zero quando não há fatos no mês |
| ADR-052 | Aceita | Home atualiza na virada do dia local e ao retornar ao foco | O dashboard aberto não exige reinicialização para trocar o recorte operacional; a consulta continua sendo a fonte de verdade |
| ADR-053 | Aceita | Despesa manual é fato no ledger `transactions` | Relatórios somam VIP, Torre e categorias manuais sem duplicar sistemas financeiros |
| ADR-054 | Aceita | Rotina v1 é uma sessão persistida, não apenas cronômetro visual | Pausa e retomada sobrevivem ao fechamento do app; agenda e lembretes ficam posteriores |
| ADR-055 | Aceita | Meta mensal usa gold equivalente de produção | Gold realizado e Sacos PvE ganhos entram na meta pelo preço atual do saco; fatos históricos não são reescritos |
| ADR-056 | Aceita | Calculadora de gold é local e não autoritativa | O padrão de 8c por 1.000 gold serve só à estimativa de BRL, sem criar cotação persistida |
| ADR-057 | Aceita | Correção de despesa manual cria substituição auditável | O lançamento anterior deixa de compor totais sem perder antes/depois e vínculo da correção |
| ADR-058 | Aceita | Relatórios priorizam feed de movimentações em vez de gráfico acumulado redundante | Com poucos pontos históricos, conferência de dungeon, Torre, venda e despesa é mais útil; o card Farm total preserva o acumulado |
| ADR-059 | Aceita | Tempo de rotina é derivado apenas de sessões encerradas | Comparações usam `accumulated_seconds`; `created_at` preserva o início original diante de pausas e retomadas |
| ADR-060 | Aceita | Comparação mensal usa período equivalente e percentuais seguros | Meses em andamento comparam até o mesmo dia do mês anterior; quando não há base histórica, exibe 'Sem base comparável'; vendas ganham histórico mensal e recentes |
| ADR-061 | Aceita | VIP usa expiração UTC com precisão de hora e tempo restante informado | A Home mostra dias/horas; ajuste da vigência ativa não duplica a despesa original; a migration preserva datas legadas |

## Questões abertas

- A estimativa principal mostrará bruto previsível e líquido separadamente, descontando custos como a Torre?
- Quais drops da Torre merecem cadastro/valor e quais serão apenas ignorados?
- O app deve apenas informar a janela/requisitos da Torre ou emitir lembrete quando ela estiver disponível?
- A linha parcialmente visível no print sobre reset das oportunidades da Torre precisa ser confirmada antes de automatizar esse contador.

## Como adicionar uma decisão

Use [[templates/Template - Decisão]]. Decisões com impacto em dados devem incluir estratégia de migração, compatibilidade reversa e recuperação.
