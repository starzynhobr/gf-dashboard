---
tipo: arquitetura
status: aceita
atualizado_em: 2026-08-26
---

# Stack e Arquitetura

## Direção oficial

O MVP é um aplicativo Windows local. **PySide6 é o shell nativo, React é a única interface, Python contém domínio/casos de uso e SQLite é a fonte de verdade local.** Não implementar navegador, API HTTP, login, Supabase ou sincronização no MVP.

A separação por contratos deve permitir que, no futuro, o mesmo frontend React seja hospedado e troque `QtGateway` por `HttpGateway`, enquanto os casos de uso Python podem ser publicados por uma API. Essa possibilidade não autoriza infraestrutura remota antecipada.

## Stack-base

| Área | Escolha | Motivo |
|---|---|---|
| Backend local | Python, versão fixada | Domínio, casos de uso, SQLite, backup e integrações nativas |
| Shell desktop | PySide6 + Qt WebEngine | Janela Windows, ciclo de vida e hospedagem do frontend compilado |
| Bridge do MVP | Qt WebChannel | Comunicação local assíncrona sem servidor HTTP local |
| Frontend único | React + TypeScript + Vite | Reuso futuro no navegador, composição modular e produtividade visual |
| Estilos | Tailwind CSS + tokens próprios | Fidelidade ao mockup e design system consistente |
| Banco local | SQLite | Arquivo transacional, simples de distribuir e suficiente para o MVP |
| SQL | SQL explícito em repositórios, sujeito ao spike ADR-013 | Consultas controladas e isolamento físico do banco |
| Migrations | Runner pequeno + SQL numerado | Ordem, checksum, backup e auditoria reproduzíveis |
| Backend tests | pytest e pytest-qt | Domínio, SQLite, bridge e shell Qt |
| Frontend tests | Vitest + Testing Library | Componentes, estado e contratos sem exigir versão web hospedada |
| Qualidade | Ruff, tipos Python, ESLint e TypeScript | Contratos claros nos dois lados da bridge |
| Empacotamento | PyInstaller + Inno Setup | Executável pessoal Windows após o núcleo local |
| Cloud futura | API HTTP + Supabase Auth/Postgres/RLS | Somente após validação e disponibilidade de projeto |

As versões de Node, Python e dependências serão fixadas em lockfiles. A compatibilidade Supabase será reavaliada contra documentação/changelog somente quando a fase remota começar.

## Organização-alvo

```text
gf-dashboard-controller/
├─ pyproject.toml
├─ uv.lock
├─ package.json
├─ package-lock.json
├─ migrations/
│  ├─ 001_initial.sql
│  └─ ...
├─ src/gf_dashboard/
│  ├─ bootstrap.py
│  ├─ domain/
│  │  ├─ entities.py
│  │  ├─ value_objects.py
│  │  ├─ enums.py
│  │  └─ errors.py
│  ├─ application/
│  │  ├─ commands/
│  │  ├─ queries/
│  │  ├─ services/
│  │  ├─ dto.py
│  │  └─ ports.py
│  ├─ infrastructure/
│  │  ├─ database/
│  │  ├─ repositories/
│  │  └─ backup/
│  └─ presentation/
│     ├─ qt_bridge/
│     └─ serializers/
├─ desktop/
│  ├─ window.py
│  ├─ webengine.py
│  └─ resources/
├─ frontend/
│  ├─ src/
│  │  ├─ app/
│  │  ├─ components/
│  │  ├─ features/
│  │  ├─ gateway/
│  │  │  ├─ AppGateway.ts
│  │  │  └─ QtGateway.ts
│  │  ├─ modules/
│  │  ├─ styles/
│  │  └─ types/
│  └─ dist/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ bridge/
│  └─ fixtures/
└─ vault/
```

`frontend/dist` é artefato gerado, não fonte editada manualmente. No desenvolvimento, Vite pode servir a UI para iteração; o portão desktop sempre valida também o build estático carregado pelo `QWebEngine`.

## Limites entre camadas

- **Domain:** regras puras e entidades; não importa PySide6, React, SQLite ou Supabase.
- **Application:** casos de uso, DTOs e portas; controla validação e transações.
- **Infrastructure:** implementa SQLite, backups, relógio, IDs e exportação.
- **Presentation Python:** adapta casos de uso para mensagens/DTOs da bridge; não contém regra de farm.
- **Frontend React:** apresenta estado e interação; não conhece SQL nem chama objetos Python fora de `AppGateway`.
- **Desktop shell:** hospeda o build, registra o WebChannel e controla janela/ciclo de vida.

## Fluxo do MVP

```text
Componente React
      ↓
AppGateway (contrato TypeScript)
      ↓
QtGateway + Qt WebChannel
      ↓
Bridge Python + DTO validado
      ↓
caso de uso → porta de repositório → transação SQLite
      ↓
resposta serializável → React atualiza consultas/estado
```

Todas as chamadas da bridge são assíncronas, possuem resultado/erro tipado e não expõem entidades internas diretamente.

## Caminho futuro, não implementado

```text
Mesmo React hospedado
      ↓
HttpGateway
      ↓
API Python hospedada
      ↓
Postgres/Supabase
```

Somente `HttpGateway`, autenticação e implantação são específicos da web. Componentes, rotas, tokens, módulos e modelos de apresentação continuam compartilhados. Recursos nativos ficam atrás de um contrato separado de capacidades do runtime.

## Regras arquiteturais

- React nunca executa SQL e nunca depende diretamente do schema SQLite.
- A bridge expõe casos de uso, não métodos genéricos como `execute_sql`.
- DTOs cruzando Python/TypeScript usam JSON simples, versão quando persistidos e validação nos dois lados.
- Escritas relacionadas ocorrem em uma transação e são idempotentes quando houver risco de reenvio/clique duplo.
- Serviços de tempo e UUID são injetáveis.
- O dashboard consome registro de módulos React confiáveis; módulo desativado não inicia consultas, timers ou animações.
- Não carregar JavaScript remoto no shell desktop do MVP. O executável carrega somente o build empacotado.
- Navegação externa abre no navegador padrão; conteúdo remoto não recebe acesso ao WebChannel.
- Nenhum segredo futuro do Supabase entra no aplicativo; `service_role` jamais pertence a um cliente público/desktop.
- Desenvolvimento manual e instalação resolvem o mesmo diretório por `QStandardPaths.AppLocalDataLocation`; testes usam diretório temporário obrigatório.
- Banco com schema mais novo que o build atual recusa escrita e nunca sofre downgrade automático.

## Estado da UI

- Dados vindos da bridge são estado assíncrono, com loading/error/empty explícitos.
- Um provider central injeta `AppGateway`; componentes não detectam WebChannel diretamente.
- Features mantêm estado local de formulário; fatos confirmados são recarregados/invalidados pela camada de consulta.
- O registro do dashboard define chave, componente React, provider/consulta, defaults de layout e versão das preferências.
- As capacidades do runtime (`isDesktop`, notificações, arquivos locais) são consultadas por interface própria, sem condicionais espalhadas.

Detalhes em [[12 - Dashboard Modular e Escolha de Stack]].

## Spikes obrigatórios

1. Carregar um build Vite mínimo por `QWebEngine` em execução manual e empacotada.
2. Provar chamada assíncrona React → WebChannel → Python → resposta/erro tipado.
3. Confirmar recarga de desenvolvimento sem conceder bridge privilegiada a origens não aprovadas.
4. Validar PyInstaller + Inno Setup incluindo Qt WebEngine, subprocessos auxiliares e `frontend/dist`.
5. Medir tamanho, startup e memória do shell com WebEngine.
6. Confirmar estratégia de screenshots/overlay no shell desktop sem criar uma versão web pública.
