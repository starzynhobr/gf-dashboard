---
tipo: indice
status: ativo
atualizado_em: 2026-08-26
---

# GF Dashboard Controller

Dashboard desktop local-first para controlar atividades de farm, produção, inventário e resultados financeiros por conta e personagem de Grand Fantasia.

## Navegação

- [[01 - Fonte da Verdade]] — escopo confirmado, regras e hierarquia documental.
- [[02 - Visão do Produto]] — problema, público, jornadas e critérios de sucesso.
- [[03 - Stack e Arquitetura]] — estrutura técnica e limites entre camadas.
- [[04 - Modelo de Dados e Supabase]] — fatos persistidos, migrations e caminho para cloud.
- [[05 - Roadmap]] — marcos e portões de qualidade.
- [[06 - Backlog]] — itens priorizados com identificadores estáveis.
- [[07 - Decisões]] — decisões aceitas, propostas e questões abertas.
- [[08 - Design e Interface]] — decomposição do mockup e critérios de fidelidade.
- [[09 - Qualidade, Backup e Segurança de Dados]] — testes, recuperação e privacidade.
- [[10 - Regras do Jogo]] — parâmetros confirmados, informados e ainda desconhecidos.
- [[11 - Catálogo de Dungeons]] — recompensas fixas e cálculo do ciclo de cinco rodadas.
- [[12 - Dashboard Modular e Escolha de Stack]] — React único, bridge desktop, módulos ativáveis e evolução web.
- [[plans/00 - Plano Mestre de Implementação]] — sequência linear de execução.

## Estado atual

| Área | Estado em 2026-08-26 |
|---|---|
| Planejamento | Estrutura inicial criada e arquitetura registrada |
| Código | Fundação executável Python/React iniciada |
| Banco local | Ainda não criado |
| Interface | React mínimo carrega no PySide6/QWebEngine e conecta à bridge Python |
| Supabase | Fora do MVP; apenas compatibilidade conceitual no SQLite |
| Empacotamento pessoal | Posterior ao núcleo funcional |

## Regra de atualização

1. Mudança de escopo confirmado: atualizar [[01 - Fonte da Verdade]].
2. Decisão arquitetural: registrar em [[07 - Decisões]] antes de alterar o plano.
3. Trabalho novo: adicionar a [[06 - Backlog]] com ID e critério de aceite.
4. Execução: seguir [[plans/00 - Plano Mestre de Implementação]] na ordem dos portões.
5. Mudança persistente no banco: criar migration; nunca alterar um banco manualmente como solução final.
