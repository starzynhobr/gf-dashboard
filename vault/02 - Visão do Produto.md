---
tipo: produto
status: ativo
atualizado_em: 2026-08-26
---

# Visão do Produto

## Problema

Gerenciar várias contas e personagens por memória ou planilhas gera atrito, registros incompletos e pouca capacidade de responder quanto foi produzido, quanto tempo foi gasto e de onde vieram os itens ou valores.

## Proposta

Um painel desktop rápido, discreto e local-first que fica aberto ao lado do jogo. A tela Hoje responde em poucos segundos:

- o que ainda falta fazer;
- quais personagens já foram concluídos;
- quais drops e valores foram registrados;
- qual foi o resultado do dia e do mês.

## Princípios de experiência

- **Uma ação para concluir:** não interromper o jogo a cada rodada.
- **Detalhe opcional:** duração, runs e drops enriquecem o histórico, mas não bloqueiam a conclusão.
- **Local primeiro:** o MVP abre e salva sem login ou serviço remoto; acesso à internet é permitido, mas não necessário para o fluxo essencial.
- **Histórico confiável:** corrigir um lançamento gera uma alteração rastreável; não recalcular o passado com preço atual.
- **Densidade controlada:** exibir muitos personagens sem virar uma planilha hostil.
- **Feedback imediato:** salvar, concluir e desfazer devem produzir confirmação visual clara.

## Personas e uso principal

### Operador individual

Administra uma ou mais contas, alterna entre o jogo e o dashboard e quer reduzir esquecimentos.

### Usuário analítico futuro

Quer comparar personagens, atividades, horários, produção por minuto, drops e conversão financeira sem ter previsto cada relatório no primeiro dia.

## Jornadas essenciais

1. **Primeiro uso:** criar perfil local → duas contas → servidor → cinco personagens por conta → escolher atividades → começar o dia.
2. **Rotina rápida:** abrir Hoje → abrir o resumo do personagem → marcar as dungeons selecionadas → o app assume cinco rodadas e calcula recompensas → opcionalmente registrar drops.
3. **Correção:** abrir histórico do lançamento → editar com validação → totais derivados são atualizados.
4. **Análise:** filtrar período/conta/personagem → visualizar totais e tendências → exportar.
5. **Recuperação:** detectar banco incompatível/corrompido → preservar original → oferecer restauração do último backup válido.
6. **Torre ocasional:** criar sessão de Torre → selecionar participantes se útil → registrar conclusão e drops relevantes → lançar o custo único de 25.000 gold.
7. **Canal web futuro:** validar a demanda → hospedar o mesmo frontend React → autenticar → vincular o workspace local → migrar/enviar histórico com reconciliação.
8. **Sincronização futura opcional:** somente se for necessário editar local e remotamente ao mesmo tempo, adicionar outbox, pull e conflitos sem bloquear o uso local.

## Métricas de sucesso

- Abrir o resumo de um personagem e salvar suas atividades em poucos cliques, sem exigir acompanhamento rodada a rodada.
- Carregar o dashboard local em até 1 segundo com a base de referência e até 2 segundos com histórico amplo em hardware-alvo.
- Zero perda silenciosa de registros em migração, atualização ou fechamento inesperado.
- Totais do dashboard reconciliáveis com os fatos por consultas determinísticas.
- Fluxo essencial utilizável em 1280×720; fidelidade de referência validada em 1680×941.

## Entidades percebidas pelo usuário

Perfil local → duas contas → cinco personagens por conta → atividades diárias/sessões → drops/itens → inventário → vendas/transações → relatórios.
