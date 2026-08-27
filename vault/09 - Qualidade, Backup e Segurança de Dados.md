---
tipo: qualidade
status: ativo
atualizado_em: 2026-08-26
---

# Qualidade, Backup e Segurança de Dados

## Pirâmide de testes

- **Unidade:** value objects, estados, cálculos e políticas de conflito.
- **Aplicação:** casos de uso com relógio/UUID/repositórios controlados.
- **Integração SQLite:** migrations de ida, constraints, repositórios e consultas.
- **Contrato:** DTOs Python, `AppGateway` e `QtGateway` preservam a mesma semântica; `HttpGateway` só entra na fase web.
- **React:** componentes, formulários, módulos, navegação, foco e estados assíncronos com Vitest/Testing Library.
- **Qt/WebChannel:** shell, origens permitidas, round-trip, erros, ciclo de vida e carregamento do build estático.
- **Visual:** componentes e telas em viewports/escala fixos.
- **Empacotamento:** instalação limpa, atualização, execução sem ambiente Python e preservação do banco.
- **Recuperação:** falha durante migration, banco inválido, backup ausente e restauração.

## Fixtures obrigatórias

- Base vazia.
- Base determinística inspirada no mockup, com 2 contas e 5 personagens por conta, sem avatares obrigatórios.
- Catálogo das 9 dungeons com totais conhecidos por rodada e ciclo de cinco.
- Sessões de Torre individual e com 2–3 participantes, custo único e drops relevantes.
- Histórico de cotações do Saco PvE para provar que estimativa atual muda sem alterar vendas passadas.
- Layout com Desempenho mensal ativado/desativado, módulo desconhecido e módulo novo recebendo defaults.
- Base grande com anos de sessões/movimentos.
- Banco de cada versão histórica suportada.
- Banco com migration interrompida/corrompida de forma controlada.
- Dois dispositivos com alterações concorrentes para a fase cloud.

## Política de backup

- Banco ativo fica em `QStandardPaths.AppLocalDataLocation` (`%LOCALAPPDATA%` no Windows), fora da pasta de instalação e sem exigir administrador.
- Execução manual e app instalado podem usar esse mesmo banco estável; suites automatizadas nunca.
- Backup antes de migration, restauração, importação ou reparo.
- Backups automáticos rotacionados por quantidade/idade configurável.
- Cada backup inclui versão do schema, versão do app, timestamp e checksum.
- Um backup só é anunciado como válido depois de abrir e passar verificação de integridade.
- Restauração nunca sobrescreve a única cópia: preserva o banco atual como arquivo de recuperação.
- Exportação lógica versionada complementa o backup binário; não o substitui.

## Falha segura

Se abrir ou migrar falhar:

1. interromper novas escritas;
2. preservar o arquivo original;
3. registrar diagnóstico sanitizado;
4. tentar apenas ações automáticas comprovadamente não destrutivas;
5. oferecer abrir em modo seguro, restaurar backup ou escolher outro arquivo;
6. verificar o estado final após qualquer recuperação.

## Segurança local

- Não armazenar credenciais do jogo.
- Sanitizar logs: nomes/observações do usuário não são necessários em stack traces.
- Validar caminhos de backup/importação e evitar traversal/sobrescrita acidental.
- Tratar JSON/importações como dados não confiáveis.
- Incluir uma trava de teste que rejeita o caminho do banco pessoal e exige diretório temporário.
- Recusar escrita quando `schema_migrations` indicar versão mais nova que a suportada pelo executável atual.
- Nunca carregar JavaScript/componente por URL ou caminho fornecido pelos dados do usuário; módulos vêm do registro React confiável do pacote.
- Somente o build empacotado e origens de desenvolvimento explicitamente permitidas recebem acesso ao WebChannel.
- A bridge não expõe SQL, filesystem ou execução de processos de forma genérica e revalida inputs no Python.
- Assinar artefatos de release quando o processo estiver disponível.
- Dependências e licenças entram no portão de empacotamento pessoal.

## Segurança Supabase futura

- Revalidar documentação e changelog antes de implementar; nenhuma configuração atual é tratada como permanente.
- Chave publicável pode estar no cliente quando a integração existir; `service_role`/secret nunca.
- RLS habilitada nas tabelas expostas e testada com pelo menos dois usuários e dois workspaces.
- Policies combinam autenticação com membership/propriedade; apenas `TO authenticated` não autoriza uma linha.
- Views/funções privilegiadas exigem revisão específica; não usar `security definer` para contornar RLS.
- Operações críticas são idempotentes e validadas no servidor.
- Logs de sync não incluem tokens nem payloads pessoais completos.
- Revogação/logout não apaga dados locais sem confirmação explícita.

## Portões de release

- Lint, tipos e testes passam no ambiente limpo.
- Migration da versão anterior e instalação limpa passam.
- Backup/restauração passam com comparação de contagens e totais.
- Screenshot e checklist visual aprovados.
- Build React estático carregado pelo shell passa; o servidor Vite não conta como artefato de release.
- Pacote abre sem terminal e sem Python instalado globalmente.
- Dados permanecem após atualizar e desinstalar/reinstalar conforme política documentada.
- Notas de versão informam qualquer migration e caminho de recuperação.
