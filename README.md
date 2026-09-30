# GF Dashboard Controller

MVP desktop local para controle de farm em Grand Fantasia.

## Download

A [pré-release v0.1.2](https://github.com/starzynhobr/gf-dashboard/releases/tag/v0.1.2) contém o instalador Windows x64 e seu checksum SHA-256. O MVP permanece em desenvolvimento; os limites da validação estão nas notas da release.

## Arquitetura inicial

- Python para domínio, aplicação e persistência local;
- PySide6/QWebEngine como shell Windows;
- React + TypeScript + Vite + Tailwind como única interface;
- Qt WebChannel por um contrato `AppGateway`;
- SQLite como fonte de verdade local, com migrations SQL, checksum e backups verificados.

Supabase, autenticação, API HTTP e distribuição no navegador não fazem parte do MVP atual.

## Regras e planejamento

Antes de implementar, leia `AGENTS.md`. O diretório `vault/` é o vault do Obsidian que mantém fonte da verdade, ADRs, modelo de dados, roadmap, backlog, kanban e plano mestre; mudanças relevantes no código devem manter esses documentos alinhados.

## Desenvolvimento

```powershell
uv sync --dev
npm --prefix frontend install
npm --prefix frontend run build
uv run gf-dashboard
```

Para trabalhar com hot reload:

```powershell
npm --prefix frontend run dev
$env:GF_DASHBOARD_DEV_URL = "http://127.0.0.1:5173"
uv run gf-dashboard
```

## Qualidade

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv lock --check
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## Dados locais

Na inicialização, o aplicativo prepara o banco SQLite em `QStandardPaths.AppLocalDataLocation`, dentro de `data/gf-dashboard.sqlite3`. Esse caminho é separado da instalação e do repositório; migrations pendentes criam um backup verificado antes de alterar um banco existente.

## Publicação e privacidade

Projeto independente para Grand Fantasia, sem afiliação oficial com o jogo. O MVP ainda está em desenvolvimento; publicar o código não representa uma release pública validada do aplicativo.

Dados de demonstração são exemplos e não devem ser interpretados como resultados reais. Ao abrir uma issue, use dados fictícios e remova nomes de contas/personagens, observações privadas e caminhos pessoais de prints ou logs. Não anexe seu banco, backups, exports ou credenciais.

O vault contém o planejamento do produto. Referências privadas não são necessárias para desenvolver: os requisitos confirmados estão consolidados nas notas. Antes de publicar, confira também o histórico Git, que mantém versões anteriores dos arquivos e os e-mails usados nos commits.

## Licença

O código e a documentação próprios do projeto estão sob a licença [MIT](LICENSE). Dependências e materiais de terceiros mantêm suas respectivas licenças; a MIT do projeto não concede direitos sobre marcas ou conteúdo de Grand Fantasia.

A interface usa ícones Phosphor e fontes do sistema, sem arquivos de fonte empacotados. A marca raster é registrada como ativo próprio em `design-qa.md`. O mockup e as capturas de comparação são referências de design; não são uma biblioteca de assets do jogo para redistribuição.

## Validação do pacote instalado

Para conferir o executável sem abrir o banco pessoal, execute `"GF Farmer.exe" --validation-profile UUID`, substituindo UUID por um identificador novo. Esse modo usa o diretório de teste do Qt e um perfil separado. Reutilize o mesmo UUID para validar persistência ao reabrir. Sem o parâmetro, o aplicativo mantém seu caminho de dados normal.
