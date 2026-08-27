---
tipo: arquitetura-de-interface
status: aceito
atualizado_em: 2026-08-26
---

# Dashboard Modular e Escolha de Stack

## Decisão

Usar **React + TypeScript + Vite + Tailwind como única interface**, empacotada no MVP dentro de **PySide6/QWebEngine**. Python continua como backend local e SQLite como fonte de verdade. A integração do MVP usa Qt WebChannel por um `AppGateway` abstrato.

Não criar agora versão web, servidor HTTP, autenticação, projeto Supabase, RLS, deploy ou sincronização. A escolha do React existe para produtividade visual e para evitar reescrever o frontend caso o navegador seja validado depois.

## Distribuições possíveis

```text
MVP
React compilado → QWebEngine → QtGateway/WebChannel → Python → SQLite

Futuro opcional
Mesmo React hospedado → HttpGateway → API Python → Supabase/Postgres
```

O frontend não detecta Python ou WebChannel dentro dos componentes. Um provider injeta a implementação de `AppGateway` ativa. Recursos exclusivos do Windows usam contrato separado de capacidades do runtime.

## O que será personalizável

### Primeira versão

- mostrar ou ocultar módulos;
- restaurar layout padrão;
- salvar preferência automaticamente;
- não iniciar consulta, timer ou animação de módulo desativado.

Exemplos de chaves:

- `today.kpi_completion`;
- `today.kpi_gold`;
- `today.characters`;
- `today.daily_summary`;
- `today.recent_drops`;
- `today.monthly_performance`;
- `today.tower_quick_action`.

### Evolução posterior

- mudar ordem;
- escolher tamanho/colspan;
- layouts diferentes por página ou resolução;
- registrar módulos novos sem editar o componente principal;
- presets “Operação”, “Financeiro” e “Compacto”.

## Contrato de módulo React

| Campo | Função |
|---|---|
| `moduleKey` | Identidade estável persistida |
| `titleKey` | Chave de texto localizado |
| `component` | Componente React empacotado |
| `queryKey` | Read model/consulta necessária |
| `defaultEnabled` | Visibilidade inicial |
| `defaultRegion/order/span` | Posição sugerida |
| `minWidth/minHeight` | Limites responsivos |
| `settingsSchemaVersion` | Migração das preferências |

O registro é código confiável do frontend. O host filtra módulos ativos e os renderiza numa grade responsiva sem conhecer a regra interna de cada módulo. Importação dinâmica pode dividir o bundle, mas nunca carrega URL/código fornecido pelo usuário.

## Persistência

- `dashboard_layouts` guarda nome e versão do layout.
- `dashboard_layout_items` guarda `module_key`, ligado/desligado, ordem, região, spans e configuração específica.
- Módulo removido do código não apaga sua preferência; fica ignorado até existir novamente.
- Módulo novo recebe defaults sem invalidar layouts antigos.
- Preferências usam `settings_schema_version` e migrations.

## Limites

Ativar/desativar módulos existentes não exige alterar o dashboard. Um novo **tipo de negócio** ainda exige domínio Python, caso de uso, persistência, DTO/bridge e componente React. A arquitetura localiza a mudança; não promete “zero código”.

React reutilizável também não significa backend automaticamente reutilizável no navegador. A futura distribuição web exige `HttpGateway`, API hospedada, autenticação, banco remoto, segurança e testes próprios. Esses trabalhos ficam adiados até existir validação.

## Por que React foi escolhido apesar do MVP local

| Critério | Decisão |
|---|---|
| Fidelidade ao mockup | CSS/Tailwind e ecossistema React favorecem iteração rápida |
| Dashboard modular | Componentes, registry e lazy loading são naturais |
| Integração local | Custo aceito: fronteira assíncrona via WebChannel |
| Empacotamento | PyInstaller deve incluir Qt WebEngine e build Vite; requer spike |
| Web futura | Componentes e design system podem ser hospedados sem reescrita |
| Escopo atual | Não implementar nenhuma distribuição web agora |

QML permanece uma tecnologia válida, mas foi substituído nesta aplicação porque criaria uma segunda interface caso o navegador se tornasse um canal real. O custo adicional do WebEngine/bridge é aceito agora para preservar a interface React.

## Contrato do gateway

O contrato expõe intenções de produto, por exemplo:

```typescript
interface AppGateway {
  getDashboard(date: string): Promise<DashboardData>
  listCharacters(): Promise<CharacterSummary[]>
  saveCharacterFarm(input: SaveCharacterFarmInput): Promise<void>
  createTowerSession(input: CreateTowerSessionInput): Promise<void>
}
```

Regras:

- sem `executeSql`, nomes de tabela ou paths internos;
- inputs/outputs validados e serializáveis;
- erros usam códigos estáveis e mensagens apresentáveis;
- chamadas de escrita recebem chave de idempotência quando necessário;
- mudanças incompatíveis exigem versão de contrato e migração coordenada;
- `QtGateway` é a única implementação no MVP;
- `HttpGateway` é backlog futuro e não recebe código especulativo.

## Segurança do shell

- carregar somente `frontend/dist` empacotado no modo de produção;
- restringir quais páginas/origens recebem o WebChannel;
- links externos abrem no navegador padrão;
- não habilitar ferramentas de desenvolvimento no build final;
- não expor API genérica de filesystem, processo ou SQL ao JavaScript;
- validar todos os inputs novamente no Python.

## Rotina e lembretes

Planejar como módulo opcional posterior:

- horário local de início;
- dias da semana;
- aviso antes/no início;
- atalho para abrir Hoje;
- lembretes da Torre baseados na janela versionada;
- silenciar/adiar sem marcar atividade como feita.

Lembretes são opt-in e não alteram o estado de farm automaticamente.

## Referências técnicas

- Qt WebEngine: <https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineWidgets/index.html>
- Qt WebChannel: <https://doc.qt.io/qtforpython-6/PySide6/QtWebChannel/index.html>
- React: <https://react.dev/>
- Vite: <https://vite.dev/>
- Tailwind CSS: <https://tailwindcss.com/>
