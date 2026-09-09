# Histórico de versões

## 1.1.0 — 2026-09-09

- Navegação principal unificada entre entregas e entregadores, com links reais, indicação da tela atual, histórico do navegador e menu lateral recolhível preservado.
- Melhorias de usabilidade e acessibilidade: breadcrumbs, retorno entre telas, limpeza de filtros, atalho `/` para busca, estados de carregamento e navegação por teclado.
- Confirmação antes de inativar ou reativar entregadores, com explicação do efeito da ação.
- Tela de login reduzida aos dados essenciais, com formulário organizado em uma caixa centralizada e responsiva.
- Guia de roteiro padronizada como manifesto de transporte, usando os dados reais da entrega e comprovante por parada.
- Impressão compacta em A4 retrato validada com oito pedidos em uma única página, distribuídos em grade 2 × 4.
- Cache da PWA renovado para distribuir os novos estilos aos dispositivos instalados.

Atualize pelo instalador com os mesmos parâmetros da instalação anterior, **sem `-ImportarBanco`**. O instalador cria um backup antes da atualização. Não há novas migrações nesta versão. Após atualizar, recarregue o navegador com Ctrl + F5.

## 1.0.4 — 2026-09-08

- Corrige a abertura de Nova entrega em HTTP pelo nome/IP do servidor, onde `crypto.randomUUID()` não está disponível.
- Gera UUID v4 com `crypto.getRandomValues()` nesse cenário, preservando a identificação de requisições e os rascunhos.
- Teste de navegador em origem HTTP fora de localhost cobre abertura, cadastro e uma segunda nova entrega sem erros de JavaScript.

Atualize pelo instalador e recarregue o navegador com Ctrl + F5. Não há novas migrações nesta versão.

## 1.0.3 — 2026-09-08

- CPF opcional com máscara, como primeiro campo da nova entrega.
- Preenchimento automático de nome, telefone e endereço a partir da compra cadastrada mais recentemente com o CPF informado.
- Busca no histórico por CPF com ou sem pontuação e exibição nos detalhes.
- Consulta autenticada, preservação de alterações manuais feitas durante a busca e limpeza dos dados preenchidos ao trocar o CPF.
- Migração `0004_entrega_cpf`: adiciona o campo sem alterar as entregas anteriores.

Atualize com os mesmos parâmetros da instalação anterior, **sem `-ImportarBanco`**. O instalador cria backup antes de aplicar a migração. Após atualizar, recarregue a página com Ctrl + F5.

## 1.0.2 — 2026-09-07

- Menu lateral recolhível pelo botão ao lado de Operação, preservando os ícones de navegação.
- Preferência salva no navegador e mantida ao recarregar ou retornar ao painel.
- Rótulos acessíveis, nomes dos menus ao passar o mouse e layout compacto preservado no celular.
- Quatro testes de navegador aprovados, incluindo recolhimento, expansão e persistência da preferência.

Atualize pelo instalador com os mesmos parâmetros da instalação anterior, sem `-ImportarBanco`. Esta versão não adiciona migrações de banco.

## 1.0.1 — 2026-09-07

- Instalador adaptado ao PowerShell 4.0 e à plataforma Windows Server 2012 R2.
- Python 3.12 no lugar de 3.14; criação da conta de segurança sem `::new()`.
- Instalação automática do Python 3.12.10 com SHA256, sem exigir uv/winget no servidor.
- Dependências de produção travadas com hashes para pip; opção de Python 3.12 externo.
- Verificação da versão do Windows antes de alterações; documentação dos limites de suporte e validação no servidor de destino.

## 1.0.0 — 2026-09-07

- Controle de entregas, histórico, filtros, CSV e ações conforme o status.
- Cadastro de entregadores, seleção de entregas e roteiro apenas de pendentes.
- Numeração por data, sem apagar o histórico na virada do dia.
- Ficha A6 e roteiro A4 compactos em retrato.
- Tema Clinical Tech, fontes locais e telefones com máscara e limite de 15 caracteres.
- Consulta offline PWA em contextos seguros.
- Instalador Windows x64 com Waitress/NSSM, conta LocalService, firewall local e logs.
- Backup SQLite diário, verificação de integridade, retenção e restauração sem sobrescrita.
- Configuração privada e banco separados do código; distribuição sem ferramentas de desenvolvimento.

O registro do serviço e da tarefa requer execução do instalador como Administrador no servidor de destino. HTTPS com certificado confiável é necessário para instalar a PWA em dispositivos remotos; proxy e certificado não são incluídos no instalador.
