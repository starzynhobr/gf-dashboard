---
tipo: regras-do-jogo
status: ativo
atualizado_em: 2026-08-26
---

# Regras do Jogo

Este documento separa fatos confirmados de informações ainda em verificação. Somente regras com estado **Confirmada** podem alimentar cálculos automáticos como fonte de verdade. Veja o modelo versionado em [[04 - Modelo de Dados e Supabase]].

## Estados

- **Confirmada:** validada pelo proprietário e pronta para implementação.
- **Informada:** provável/observada, mas ainda precisa de confirmação precisa.
- **Desconhecida:** valor ou comportamento ainda não levantado.

## Contexto geral

| Regra | Estado | Valor atual |
|---|---|---|
| Virada do dia de farm | Confirmada | Meia-noite no fuso local configurado |
| Contas em uso | Confirmada | 2 |
| Personagens por conta | Confirmada | 5 |
| Total de personagens | Confirmada | 10 |
| Avatares individuais | Confirmada | Irrelevantes para o MVP |
| Cotação inicial do gold | Confirmada | R$ 0,07–R$ 0,08 por 1.000 gold |
| Evidência visual da cotação | Confirmada | Anúncio de compra de 5kk a 7c no print fornecido |

## Dungeons

Os valores exatos por dungeon estão em [[11 - Catálogo de Dungeons]].

| Regra | Estado | Valor atual |
|---|---|---|
| Dungeons disponíveis no catálogo | Confirmada | 9 |
| Seleção inicial da rotina | Confirmada | Global no workspace, com as 9 dungeons ativas para todos os personagens |
| Missões aceitas simultaneamente | Confirmada | 2 por dungeon |
| Missão 1 | Confirmada | Limitada a 5; fornece gold + 1 Saco PvE por rodada |
| Missão 2 | Confirmada | Ilimitada; fornece somente gold por rodada |
| Ciclo-meta | Confirmada | 5 rodadas e depois avançar à próxima dungeon |
| Repetir apenas a missão ilimitada | Confirmada | Não faz parte do meta; retorno não compensa o tempo |
| É necessário registrar cada rodada no MVP | Confirmada | Não |
| Ao marcar dungeon como feita | Confirmada | Assumir todas as 5 rodadas |
| Sacos PvE por rodada padrão | Confirmada | 1 |
| Checkboxes por rodada | Informada | Ideia futura; não obrigatórios |

## Torre de Milhões de Bestas

Fonte visual fornecida: print fornecido pelo proprietário (não incluído no repositório).

### Uso no app

| Regra | Estado | Valor atual |
|---|---|---|
| Natureza | Confirmada | Sessão de farm separada das dungeons e do checklist diário |
| Frequência pessoal | Confirmada | Ocasional; não necessariamente diária |
| Abertura | Confirmada | Torre da guild, 25.000 gold fixos por sessão |
| Participantes | Confirmada | Todos os membros elegíveis podem entrar; sessão normalmente individual, às vezes com 2–3 personagens para funções diferentes |
| Quantidade pessoal | Confirmada | Podem existir várias sessões; o app não presume 10 personagens nem uma sessão diária |
| Objetivo | Confirmada | Chegar ao piso 30 e observar drops de valor para venda |
| Registro principal | Confirmada | Concluída/não concluída + drops relevantes |

### Regras exibidas no jogo

| Regra | Estado | Valor atual |
|---|---|---|
| Disponibilidade | Confirmada pelo print | Todos os dias, 20:00–22:00 |
| Registro/cancelamento antecipado | Confirmada pelo print | 19:30–20:00 |
| Fechamento do registro | Confirmada pelo print | 20 minutos após a abertura; depois não troca membros |
| Grupos de desafio | Confirmada pelo print | Máximo de 20 grupos por dia |
| Tamanho do grupo | Confirmada pelo print | Até 30 membros |
| Entrada após convocação | Confirmada pelo print | Até 3 minutos; ausência remove do grupo e libera a vaga |
| Nível mínimo | Confirmada pelo print | 91 |
| Oportunidades necessárias | Confirmada pelo print | Personagem precisa ter oportunidades restantes |
| Impedimentos de registro | Confirmada pelo print | Não estar em dungeon, campo de batalha ou equipe |
| Oportunidades diárias | Confirmada pelo print | 20 por jogador, compartilhadas na conta |
| Perda de oportunidade | Confirmada pelo print | Morrer ou sair do grupo consome 1 |
| Sem oportunidades | Confirmada pelo print | Não pode entrar novamente e é teleportado para fora |
| Faixa de pisos | Confirmada pelo usuário | 1–30 |
| Reset das oportunidades | Parcial no print | A última regra está cortada; não automatizar até confirmar o texto completo |

As regras de participação podem aparecer como informação/aviso. O MVP não deve bloquear uma sessão apenas com base nelas, pois são regras externas e podem mudar; a regra versionada registra a fonte e a vigência.

## Gold estimado

| Regra | Estado | Valor atual |
|---|---|---|
| Base previsível inicial | Confirmada | Gold fixo das duas missões × 5 rodadas das dungeons concluídas |
| Valor dos Sacos PvE | Confirmada | 1.000 gold por saco atualmente; cada alteração cria histórico de cotação |
| Atualização do dashboard | Confirmada | Estimativa atual muda quando o preço de mercado configurado muda |
| Histórico realizado | Confirmada | Vendas e valores observados preservam snapshots e não mudam retroativamente |
| Torre | Confirmada | Custo de 25.000 por sessão fica separado; drops entram quando registrados/avaliados |
| Visão bruta/líquida | Desconhecida | Definir apresentação final |

## Política de cálculo

1. Valores manuais são armazenados como fatos informados pelo usuário.
2. Valores automáticos registram a versão da regra que os gerou.
3. Alterar uma regra só afeta conclusões futuras; históricos guardam snapshots.
4. Regra `Informada` ou `Desconhecida` não calcula recompensa automaticamente.
5. Correção histórica é explícita e auditável; nunca ocorre por simples mudança do valor atual.
6. Estimativa prospectiva usa o preço atual do Saco PvE; valor realizado usa a venda/movimento registrado.
7. Conversão para BRL usa uma cotação versionada por 1.000 gold; o valor inicial é exibido como faixa de 7–8 centavos.

## Próxima coleta

- [ ] Definir quais dungeons ficam selecionadas inicialmente entre as nove.
- [ ] Definir se a seleção varia globalmente, por conta ou por personagem.
- [ ] Confirmar a linha cortada do print sobre reset das oportunidades da Torre.
- [x] Informar o preço inicial do Saco PvE: 1.000 gold.
- [ ] Definir quais drops relevantes da Torre entram no catálogo.
