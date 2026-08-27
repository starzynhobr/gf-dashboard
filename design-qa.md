# Design QA — Tela Hoje

## Evidências

- Fonte visual: `C:\Users\tz\Documents\PROJETOSGIT\gf-dashboard-controller\ChatGPT Image 26 de ago. de 2026, 05_35_03.png`
- Implementação renderizada: `C:\Users\tz\Documents\PROJETOSGIT\gf-dashboard-controller\design-qa-implementation.png`
- Comparação completa empilhada: `C:\Users\tz\Documents\PROJETOSGIT\gf-dashboard-controller\design-qa-comparison.png`
- Comparação focada dos KPIs: `C:\Users\tz\Documents\PROJETOSGIT\gf-dashboard-controller\design-qa-focused-kpis.png`
- Comparação focada do conteúdo: `C:\Users\tz\Documents\PROJETOSGIT\gf-dashboard-controller\design-qa-focused-content.png`
- URL de implementação: `http://127.0.0.1:4173/?preview=1`
- Viewport CSS: 1680×941, `devicePixelRatio: 1`.
- Fonte: 1672×941 px normalizada horizontalmente para 1680×941 na comparação.
- Implementação: 1680×941 px, sem overflow horizontal ou vertical.
- Estado: fixture visual local de 10 personagens; o preview não grava nem substitui dados reais.

## Findings

Não restam diferenças acionáveis P0, P1 ou P2 no escopo da tela Hoje somente leitura.

- Geometria e ritmo: sidebar fixa, header, quatro KPIs, painel principal e coluna direita preservam as proporções e a densidade do mockup.
- Tipografia: Segoe UI Variable/Segoe UI, pesos e hierarquia equivalentes; não há síntese de itálico.
- Cores/tokens: fundo azul-marinho, painéis, bordas suaves, estados verde/amarelo e destaque dourado permanecem coerentes com a referência.
- Imagem/ativos: a marca usa um PNG transparente próprio; ícones funcionais vêm do Phosphor. Avatares individuais continuam como iniciais neutras por decisão do MVP.
- Conteúdo: os números do preview são determinísticos; na execução normal, KPIs, Torre, drops e gráfico vêm do SQLite. Valores diferentes da imagem são dados, não drift visual.

Desvios intencionais e aceitos:

- Torre não aparece como coluna por personagem, pois foi definida como sessão independente.
- A rotina mostra 9 dungeons selecionadas, não 25 runs genéricas da imagem.
- Conta/servidor ilustrativos foram substituídos por “Workspace local / Dados no SQLite” até existir o read model de contas.
- Controles nativos de minimizar/maximizar/fechar permanecem no item UI-002 e não fazem parte do preview web desta tela.

## Comparação focada

As comparações focadas foram necessárias porque a tabela, os badges, os drops e os eixos do gráfico ficam pequenos na captura completa. Elas confirmam alinhamento de colunas, alturas de linha, progress bars, espaçamento dos KPIs, hierarquia tipográfica e densidade da coluna direita.

## Histórico de iterações

1. P2 — tipografia aparecia inclinada e a tela excedia o viewport em 5 px. Correção: fallback para Segoe UI Variable/Segoe UI, `font-synthesis: none` e ajuste do footer/padding. Evidência posterior: 1680×941 sem overflow.
2. P2 — drops e desempenho mensal preservavam a geometria, mas estavam vazios no preview. Correção: read model SQLite, contrato da bridge, gateway React, lista de drops e gráfico Recharts carregado sob demanda. Evidência posterior: cinco drops e um gráfico mensal renderizados.
3. P2 — o emblema de marca era uma aproximação de biblioteca. Correção: ativo raster transparente próprio em `frontend/src/assets/gf-farmer-mark.png`. Evidência posterior: captura final e comparação completa.

## Verificações funcionais

- Dados carregados de modo assíncrono por `AppGateway`.
- Lazy loading do gráfico confirmado no browser.
- Cinco drops, série mensal, total mensal e estados de Torre confirmados no DOM.
- Navegação futura aparece desabilitada em vez de simular ações inexistentes.
- Preview sem overflow em 1680×941.
- Stream do Vite inspecionado sem erro de runtime; testes React e smoke QWebEngine cobrem a fronteira Qt/React.

## Follow-up polish (P3)

- Validar 1440×810, 1280×720 e escalas Windows 125%/150%.
- Implementar a janela sem moldura e os controles nativos de UI-002.
- Substituir iniciais por avatares somente se essa prioridade mudar.

final result: passed
