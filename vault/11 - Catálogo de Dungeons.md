---
tipo: catalogo-de-dungeons
status: confirmado
atualizado_em: 2026-08-26
---

# Catálogo de Dungeons

Valores fornecidos pelo proprietário em 26 de agosto de 2026. Eles devem entrar como uma versão de regras com vigência e origem, não como constantes espalhadas pelo código.

## Funcionamento do ciclo-meta

- As duas missões são aceitas simultaneamente.
- Missão 1: limitada a cinco rodadas, concede gold + 1 Saco PvE por rodada.
- Missão 2: ilimitada, concede somente gold por rodada.
- O ciclo-meta realiza cinco rodadas e avança à próxima dungeon.
- Marcar a dungeon como feita assume as cinco rodadas.
- Repetir apenas a missão ilimitada não faz parte do fluxo padrão porque o retorno não compensa o tempo.

## Recompensas confirmadas

| Dungeon | Missão 1/rodada | Missão 2/rodada | Gold fixo em 5 | Sacos em 5 | Estimativa com saco a 1k | BRL a 7–8c/1k |
|---|---:|---:|---:|---:|---:|---:|
| Palácio de Proteção do Selo | 910 | 490 | 7.000 | 5 | 12.000 | R$ 0,84–0,96 |
| Câmara Secreta do Ritual das Trevas | 910 | 490 | 7.000 | 5 | 12.000 | R$ 0,84–0,96 |
| Destruidor do Vazio | 780 | 420 | 6.000 | 5 | 11.000 | R$ 0,77–0,88 |
| Igreja Subterrânea de Carso | 780 | 420 | 6.000 | 5 | 11.000 | R$ 0,77–0,88 |
| Santuário Maldito | 520 | 280 | 4.000 | 5 | 9.000 | R$ 0,63–0,72 |
| Dimensão Distorcida | 650 | 350 | 5.000 | 5 | 10.000 | R$ 0,70–0,80 |
| Primata | 650 | 350 | 5.000 | 5 | 10.000 | R$ 0,70–0,80 |
| Kaslow Ardente | 300 | 295 | 2.975 | 5 | 7.975 | R$ 0,56–0,64 |
| Ilha Condenada | 520 | 280 | 4.000 | 5 | 9.000 | R$ 0,63–0,72 |

Se todas as nove forem feitas por um personagem no mesmo ciclo: **46.975 gold fixos + 45 Sacos PvE**. Com o saco a 1.000 gold, a estimativa atual é **91.975 gold**, ou aproximadamente **R$ 6,44–R$ 7,36** na cotação inicial. Esta é a seleção global inicial definida para o MVP; a configuração poderá reduzi-la depois.

## Fórmulas

Para uma dungeon concluída:

```text
gold_fixo = 5 × (gold_missao_1_por_rodada + gold_missao_2_por_rodada)
sacos_pve = 5 × 1
estimativa_atual = gold_fixo + (sacos_pve × preco_atual_saco_pve)
estimativa_brl = (estimativa_atual / 1000) × cotacao_brl_por_1000_gold
```

Para o dashboard do personagem/dia, somar somente as dungeons selecionadas e concluídas.

## Persistência recomendada

- Uma `activity_rule_version` por dungeon e vigência.
- Duas `activity_reward_rules` por versão: Missão 1 e Missão 2.
- Recompensa de Saco PvE vinculada somente à Missão 1.
- `target_amount = 5` no ciclo-meta atual.
- Ao concluir, gravar snapshots das recompensas usadas.
- Preço atual do Saco PvE pertence a uma cotação/configuração de mercado separada; não altera o gold fixo.
- Conversão para BRL usa cotação própria e versionada; o ponto de partida é R$ 0,07–R$ 0,08 por 1.000 gold.

## Seleção da rotina

As nove dungeons ficam cadastradas e começam selecionadas globalmente para todos os personagens. A configuração posterior poderá alterar essa seleção global; seleção por conta/personagem ou planos reutilizáveis são evoluções futuras.
