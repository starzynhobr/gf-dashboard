---
tipo: design
status: referencia
atualizado_em: 2026-08-26
---

# Design e Interface

## Referência primária

Arquivo: `C:\Users\tz\Documents\PROJETOSGIT\gf-dashboard-controller\ChatGPT Image 26 de ago. de 2026, 05_35_03.png`

Viewport da referência: **1680×941**. A imagem é direção visual, enquanto o fluxo simples pendente/feito da [[01 - Fonte da Verdade]] prevalece sobre a obrigação de contar 25 runs.

Referência secundária do resumo: `C:\Users\tz\AppData\Local\Temp\codex-clipboard-2ff76f5e-62a0-466d-9ca8-606523d92664.png`. Ela define conteúdo e simplicidade do fluxo, não o tema visual claro/monoespaçado.

## Anatomia da tela Hoje

```text
┌ Sidebar 250 ┐┌ Header: data, ações, perfil e janela ────────────────┐
│ Marca       │├ Quatro cards de indicadores ─────────────────────────┤
│ Hoje        │├ Painel principal de personagens ─┬ Resumo do dia ────┤
│ Personagens ││                                  ├ Últimos drops ────┤
│ Relatórios  ││                                  ├ Desempenho mensal │
│ Histórico   ││                                  │                   │
│ Config.     ││                                  │                   │
│ Conta ativa │└──────────────────────────────────┴───────────────────┘
└─────────────┘
```

Medidas são inicialmente aproximadas e devem ser confirmadas por overlay:

- sidebar: ~250 px;
- header: ~86 px;
- margem de conteúdo: ~27 px;
- gaps principais: 16–18 px;
- cards: cantos ~14–16 px, borda fina e fundo azul translúcido;
- coluna central: aproximadamente 68% da largura útil; coluna direita: 32%;
- linhas de personagem: aproximadamente 45 px na referência.

## Linguagem visual

- Fundo azul-marinho muito escuro com leve gradiente/vinheta.
- Superfícies em azul elevado, bordas discretas e baixa opacidade.
- Tipografia clara; metadados em azul-cinza.
- Dourado para economia e destaques do universo do jogo.
- Verde para concluído, âmbar para em andamento, cinza-azulado para pendente.
- Acento índigo/azul na navegação ativa e gráfico.
- Ícones lineares consistentes. Personagens usam iniciais, número ou marcador neutro no MVP; avatares não são requisito.

## Tokens iniciais

Os valores abaixo são ponto de partida, não amostras finais. A fase de fidelidade deve extrair e ajustar cores pela imagem.

| Token | Valor inicial |
|---|---|
| `color.background` | `#071A2B` |
| `color.sidebar` | `#061827` |
| `color.surface` | `#13283A` |
| `color.surfaceBorder` | `#294055` |
| `color.textPrimary` | `#F4F6FA` |
| `color.textSecondary` | `#9DAABD` |
| `color.accent` | `#6078E8` |
| `color.success` | `#4CCB73` |
| `color.warning` | `#F0BD35` |
| `color.gold` | `#FFCA45` |
| `radius.card` | `15` |
| `spacing.unit` | `4` |

## Componentes React

- `AppWindow`, `Sidebar`, `SidebarItem`, `WindowControls`, `AccountIndicator`.
- `PageHeader`, `SectionTitle`, `StatCard`, `IconDisc`.
- `Panel`, `CharacterTable`, `CharacterRow`, `ProgressBar`, `StatusBadge`.
- `DailySummary`, `RecentDrops`, `DropRow`, `MonthlyPerformanceChart`.
- `PrimaryButton`, `SecondaryButton`, `IconButton`, `MenuPopover`.
- `EmptyState`, `LoadingSkeleton`, `ErrorBanner`, `Toast`, `ConfirmDialog`.
- `FormField`, `NumberField`, `DateField`, `SearchField`, `FilterChip`.
- `CharacterCompletionSummary`, `DungeonCompletionRow`, `OptionalResultsForm`.
- `TowerSessionForm`, `SessionParticipants`, `RelevantDropsEditor`.
- `DashboardModuleHost`, `DashboardEditMode`, `ModuleVisibilityMenu`.

## Comportamento responsivo

- **1680×941:** reprodução fiel do mockup.
- **1440×810:** reduzir margens/gaps; manter duas colunas.
- **1280×720:** cards podem usar grade 2×2; coluna direita vira painel rolável ou seção abaixo.
- Abaixo do mínimo suportado: impedir compressão ilegível e documentar tamanho mínimo da janela.
- Escala 125% e 150% do Windows deve manter texto, foco e alvos clicáveis sem corte.

## Diferença intencional em relação à imagem

- A lista não exige progresso `0/25…25/25`. O estado principal é conclusão rápida.
- Se `runs_count` ou `progress_amount` existir, a barra e a fração aparecem como enriquecimento opcional.
- “Runs totais” no card pode ser ocultado ou substituído quando não houver dados suficientes.
- “Gold estimado” fica oculto, marcado como não configurado ou substituído por um fato confirmado enquanto a fórmula estiver dormente.
- A linha abre um resumo inspirado na segunda referência: nome do personagem; dungeons selecionadas; gold fixo e Sacos PvE calculados; drops/observações opcionais; Salvar.
- Marcar uma dungeon como feita assume cinco rodadas. Um futuro detalhamento por checkbox pode existir, mas não faz parte do fluxo normal.
- Torre não aparece no checklist do personagem. Uma ação própria “Nova sessão de Torre” abre custo fixo, participantes opcionais, conclusão e drops relevantes.

## Fluxo do resumo de personagem

1. Usuário abre a linha do personagem.
2. O painel mostra apenas as dungeons selecionadas para esse personagem/plano.
3. Usuário marca cada dungeon concluída; cada marca representa o ciclo completo de cinco rodadas.
4. A UI calcula gold das duas missões e cinco Sacos PvE usando a versão vigente.
5. Usuário adiciona drops se desejar e salva uma única transação.
6. A tela Hoje atualiza os estados e oferece desfazer/reabrir.

O painel deve manter a hierarquia e simplicidade do print fornecido, mas adotar os tokens dark do dashboard principal.

## Fluxo da Torre

1. Usuário escolhe “Nova sessão de Torre” quando decidir fazer esse farm.
2. O formulário já apresenta custo de 25.000 gold e, como informação, janela/requisitos vigentes.
3. Participantes são opcionais; normalmente um personagem, podendo selecionar dois ou três.
4. Ao finalizar, registra apenas concluída/não concluída, drops relevantes e observações.
5. O custo entra uma vez no ledger financeiro da sessão; drops entram no inventário/estimativa quando registrados.

## Estimativa de gold

- Card pode separar `Gold fixo das dungeons`, `Valor estimado dos sacos` e `Custos`.
- Sem preço atual do Saco PvE, mostrar o gold fixo e solicitar configuração da cotação, sem exibir total enganoso.
- Alterar a cotação atualiza a estimativa atual, mas não valores realizados históricos.

## Processo de fidelidade

Baseline atual aprovado em 2026-08-26:

- implementação: `design-qa-implementation.png`;
- comparação completa: `design-qa-comparison.png`;
- comparações focadas: `design-qa-focused-kpis.png` e `design-qa-focused-content.png`;
- relatório: `design-qa.md` com `final result: passed`;
- emblema de marca: `frontend/src/assets/gf-farmer-mark.png`.

1. Criar fixture determinística com os mesmos nomes, estados e totais do mockup.
2. Renderizar em 1680×941, mesma escala e fonte empacotada.
3. Gerar overlay 50% e diff perceptual.
4. Ajustar primeiro geometria macro, depois tipografia, cores, ícones e detalhes.
5. Mascarar somente dados realmente dinâmicos; não mascarar desalinhamentos.
6. Registrar screenshot aprovada como baseline versionada.
7. Rodar teste visual nos componentes e na tela completa antes de release.

## Personalização da visualização

- A página Hoje é uma composição de módulos registrados, não um arquivo monolítico com todos os painéis fixos.
- No primeiro incremento, Configurar visualização permite mostrar/ocultar módulos e restaurar o padrão.
- Desempenho mensal pode ser desligado sem manter consultas/animações ativas.
- Ordem e tamanho entram depois, preservando a geometria padrão fiel ao mockup.
- Um módulo novo declara chave, componente React, consulta/provider de dados, região e tamanho; o host não precisa conhecer sua implementação.
- Preferências são persistidas e versionadas conforme [[12 - Dashboard Modular e Escolha de Stack]].

## Critérios de aceite visual

- Estrutura, proporções e alinhamentos principais diferem no máximo 4 px no viewport de referência após calibração.
- Não há cortes, sobreposição ou salto de layout em 100%, 125% e 150% de escala.
- Estados hover, pressed, focus, disabled, loading, empty e error existem nos componentes interativos.
- Contraste e foco não são sacrificados para copiar um detalhe decorativo.
- Animações duram pouco e respeitam configuração de redução de movimento quando disponível.
