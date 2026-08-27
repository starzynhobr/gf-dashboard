---
tipo: roadmap
status: ativo
atualizado_em: 2026-08-26
---

# Roadmap

As datas serão estimadas somente depois do primeiro spike técnico. A ordem é obrigatória; cada marco depende do portão anterior.

| Marco | Resultado demonstrável | Portão de saída |
|---|---|---|
| M0 — Fundação | Toolchains Python/Node, shell PySide6/QWebEngine, React mínimo e bridge tipada | Build React carrega no shell e round-trip WebChannel passa |
| M1 — Banco seguro | Schema v1, runner de migrations, backup e repositories | Migração, rollback de falha e integridade testados |
| M2 — Domínio operacional | Contas, personagens, atividades e conclusão diária | Casos de uso funcionam sem UI e preservam histórico |
| M3 — Shell visual modular | Janela, sidebar, header, tokens, registro e host de módulos | Comparação 1680×941 aprovada; módulo pode ser ocultado/restaurado |
| M4 — Hoje utilizável | Cards, checklist das dungeons selecionadas, estimativa e sessão de Torre | Ciclo de cinco rodadas calcula recompensas e Torre funciona como sessão independente |
| M5 — Gestão e personalização | CRUD, filtros, histórico, inventário, financeiro e preferências visuais | Totais reconciliam e layout salvo sobrevive ao reinício/módulos novos |
| M6 — Relatórios e exportação | Tendências, filtros e exportações | Relatórios reproduzíveis a partir de fixtures conhecidas |
| M7 — Robustez pessoal | Recuperação, desempenho, acessibilidade e uso contínuo do mesmo banco | Build manual e instalado preservam o banco sem expor o arquivo aos testes |
| M7.1 — Empacotamento posterior | PyInstaller + Inno Setup com Qt WebEngine e `frontend/dist` | Instalação/atualização preserva dados e shell React funciona |
| M8 — Canal web/cloud opcional | HttpGateway, API, Auth, memberships, RLS e banco remoto | Mesmo frontend atende desktop/web e dados ficam isolados por workspace |
| M9 — Sincronização opcional | Upload local, outbox e sync incremental, somente se necessário | Dois dispositivos convergem sem duplicação ou perda |

## Sequência de releases sugerida

- **0.1 — Vertical slice local:** M0–M4, apenas dados de farm essenciais.
- **0.2 — Histórico rico:** M5, drops/inventário/financeiro.
- **0.3 — Relatórios e robustez pessoal:** M6–M7.
- **1.0 — Local confiável:** fluxo completo, recuperação validada e UX polida.
- **1.0.x — Instalação pessoal opcional:** M7.1, quando empacotar trouxer benefício real.
- **1.x — Web/cloud opcional:** M8 somente após validação, slot/projeto disponível e replanejamento técnico.
- **1.x posterior — Sync opcional:** M9 apenas se existir exigência real de operação local e remota simultânea.

## Regra para mudança de marco

Uma funcionalidade futura não entra antecipadamente se obrigar a pular um portão. Preparação estrutural é permitida; comportamento sem teste ou tela sem dados reais não conta como avanço do marco.
