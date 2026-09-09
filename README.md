# Super Baranda · Entregas

Aplicação PWA em português para organizar as entregas da loja, com Django, SQLite e uma interface responsiva sem dependências externas de JavaScript, fontes ou CSS.

## Executar no Windows (desenvolvimento)

Pré-requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) e Python 3.12. O uv pode instalar o Python necessário automaticamente.

No PowerShell, dentro de `C:\entrega`:

```powershell
.\iniciar.ps1
```

Na primeira execução, o script instala as dependências, prepara o banco e solicita a criação da conta do responsável. Escolha seu usuário e senha. Depois abra **http://127.0.0.1:8000**. Não há senha padrão nem dados de clientes pré-carregados.

Alternativa, comando a comando:

```powershell
uv sync --locked
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver 127.0.0.1:8000
```

O banco é `db.sqlite3`, criado na raiz e excluído do Git. Para encerrar o servidor, pressione Ctrl+C.

## Operação

- **Nova entrega:** nome, endereço, telefone, cupom, volumes e data são obrigatórios. Horário, entregador e observações são opcionais no cadastro. A sequência é gerada pelo banco e não se repete entre operadores na mesma data.
- **Rascunho:** o formulário de uma nova entrega é salvo neste navegador enquanto você digita e recuperado ao reabrir. O rascunho ainda não é uma entrega cadastrada.
- **Visão geral:** começa na data de hoje. Os indicadores refletem a data e a busca selecionadas. Os cartões e abas filtram a lista por status; canceladas entram no total.
- **Todas as entregas:** consulta o histórico de qualquer data. A busca aceita cliente, endereço, cupom, entregador ou sequência.
- **Fluxo:** pendente → em rota → entregue. É obrigatório atribuir um entregador para iniciar a rota. Os botões de edição e cancelamento ficam disponíveis na lista durante a rota. Entregues e canceladas permanecem no histórico, sem edição.
- **Ações:** a coluna da lista oferece “Iniciar rota” para pendentes, com atribuição do entregador na confirmação. Em rota, exibe “Imprimir ficha”, “Editar”, “Cancelar” e “Confirmar entrega”. Entregues e canceladas oferecem apenas “Detalhes”. As ações de alteração e impressão ficam desabilitadas sem conexão.
- **Detalhes:** histórico com autor e horário, ligação para o cliente e link do endereço no Google Maps. O mapa abre uma busca pelo endereço; não há rastreamento GPS.
- **Impressão:** a ficha individual usa A6 retrato (105 × 148 mm, um quarto de A4), preservando os campos do modelo fornecido. O roteiro usa duas colunas em A4 retrato, margens de 8 mm e espaçamento reduzido, com os dados completos e espaço para recebimento. Desative cabeçalhos e rodapés do navegador e use escala de 100%. Para imprimir várias páginas A6 em papel A4, selecione quatro páginas por folha no visualizador de PDF ou na impressora. Endereços e observações longos podem aumentar a quantidade de páginas; o conteúdo não é truncado para forçar o encaixe.
- **Exportação:** CSV compatível com Excel, com separador `;`, respeitando data, busca e status. Os valores que poderiam ser interpretados como fórmulas são neutralizados.
- **Guia de roteiro:** marque as caixas ao lado dos clientes ou use “Selecionar página”. A seleção permanece ao mudar de página ou filtro, até “Limpar seleção” ou recarregar a tela. Selecione até 100 entregas e clique em “Emitir guia de roteiro”. A guia abre em outra aba com os dados atuais das entregas, totais de volumes, contatos, observações e espaços para motorista, veículo e recebimento. Use as setas para ajustar a ordem das paradas e “Imprimir / salvar PDF” para emitir em A4. A ordem inicial segue a seleção; não há otimização automática por distância. A guia requer conexão e é gerada para impressão, sem cadastrar uma rota no banco nem mudar o status das entregas.
- **Equipe:** o responsável pode criar contas em `/admin/`. Todos os usuários ativos com login operam as entregas da loja. Somente contas com acesso administrativo autorizado gerenciam usuários.
- **Entregadores:** o menu “Entregadores” abre `/entregadores/`, com tabela, busca e filtro de ativos/inativos. Cadastre nome e telefone, edite os dados ou inative/reative o cadastro. O telefone é opcional e tem máscara. Os seletores das entregas e da confirmação de início de rota usam o cadastro; novos vínculos e saídas exigem entregadores ativos. Cadastros vinculados não são excluídos. Uma entrega já em rota pode manter seu entregador inativado, mas não receber uma nova atribuição inativa.

Os nomes de entregadores que já constavam nas entregas foram importados e vinculados pela migração. Complete seus telefones na tabela. O nome registrado na entrega é preservado como histórico ao renomear o cadastro; uma nova atribuição ou início de rota usa o nome atual. Cadastro de entregador não cria uma conta de acesso ao sistema.

Pedidos de cadastro repetidos com a mesma identificação retornam a entrega já criada, evitando duplicação após uma resposta de rede perdida. Alterações simultâneas são detectadas pela versão do registro: recarregue os detalhes quando outra pessoa tiver alterado a entrega.

O roteiro inclui **somente entregas com status pendente no momento da emissão**. Entregas em rota, entregues e canceladas são ignoradas, inclusive em uma seleção mista. Os totais e a numeração consideram apenas as pendentes. Se não houver nenhuma pendente, a página informa o motivo e não apresenta a guia nem o botão de impressão. A regra é validada no servidor, também ao acessar o endereço da guia diretamente.

### Numeração diária

Cada **data de entrega** possui seu próprio contador: `000001`, `000002` etc. A primeira entrega de uma nova data começa em `000001`, mesmo se for cadastrada antecipadamente. Não há tarefa agendada para zerar o banco: a reserva do número acontece na mesma transação do cadastro, com uma restrição de unicidade por data. O ID interno continua global, preservando vínculos, links e histórico.

Cancelamentos não devolvem números ao contador. Alterar a data reserva o próximo número do dia de destino e não reutiliza o número anterior. Consulte uma entrega pelo conjunto **data + sequência**; no histórico sem filtro podem existir sequências iguais em datas diferentes. Os números anteriores à implantação da regra foram preservados pela migração, e cada data já existente continua a partir do maior número reservado.

A visão geral acompanha a virada do dia no fuso `DJANGO_TIME_ZONE`: verifica a data a cada 30 segundos enquanto visível e ao retornar à janela. Ao mudar de dia, consulta as entregas da nova data e limpa a seleção de roteiro. Os registros antigos e seus status são preservados. Uma data escolhida manualmente ou o histórico não são trocados automaticamente. Sem conexão, a lista diária segue as limitações da cópia offline.

## Instalar e usar offline

Use **Instalar aplicativo** na barra lateral. Quando o navegador não oferece o instalador automático, o botão mostra as instruções para Android, computador e iPhone. No celular, a aplicação precisa ser servida por **HTTPS**; `http://127.0.0.1` é destinado ao desenvolvimento no próprio computador. Consulte os [requisitos oficiais de instalação de PWAs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).

Após uma consulta com conexão, a última lista carregada fica disponível offline neste navegador. Ao abrir a PWA sem conexão, aparecem a data da cópia, os dados de contato, os endereços, volumes e status, com busca local. **É uma consulta local: não há cadastro, impressão, alteração de status ou sincronização de alterações offline.** Um formulário novo já aberto pode continuar como rascunho e ser salvo ao reconectar.

Somente os registros da última consulta estão disponíveis offline, inclusive quando a consulta foi filtrada. Os dados offline ficam no armazenamento do navegador e não substituem o banco. Sair da conta apaga a cópia e os rascunhos. A tela offline também oferece **Apagar cópia deste dispositivo**. Não há cache de respostas da API nem de páginas autenticadas no service worker.

## Producao local no Windows

Consulte [PRODUCAO.md](PRODUCAO.md) para usar instalador.ps1, importar o banco existente, configurar servico, backup diario, restauracao e HTTPS. Versao: **1.1.0**; veja [CHANGELOG.md](CHANGELOG.md).

## Validação

```powershell
uv sync --locked
uv run playwright install chromium
uv run python manage.py collectstatic --noinput
uv run ruff check .
uv run ruff format --check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
```

Os testes cobrem autenticação, CSRF, validação, sequência e idempotência, fluxo de status, concorrência, histórico, filtros, CSV e impressão. O teste de navegador também percorre cadastro, rascunho, edição, entrega, exportação, paginação, tela móvel, instalação do service worker, consulta offline e limpeza após logout. Ele usa banco temporário e dados fictícios, sem alterar o banco da loja.

Para testar apenas o backend: `uv run pytest entregas -q`. As capturas de desktop, celular e offline e uma ficha PDF são produzidas em `test-results/`, excluído do Git.

Os ícones PNG já estão incluídos. Para regenerá-los após editar o SVG: `uv run python scripts/gerar_icones.py`. Para reconstruir a ficha a partir do HTML original: `uv run python scripts/preparar_ficha.py`.

## Padrão de desenvolvimento

Consulte o [padrão de desenvolvimento Django + VS Code](PADRAO_PROJETOS_DJANGO.md).

O domínio usa nomes em português, organizado no app `entregas`. As adaptações são Python 3.12, interface em JavaScript/CSS nativos, Playwright para testes de navegador, WhiteNoise para estáticos e Waitress para execução compatível com Windows. Ruff formata e verifica Python; os templates e os fluxos JavaScript são verificados pelo teste de navegador. O instalador e o procedimento de operacao estao em PRODUCAO.md.

## Identificação por CPF

O cadastro e a edição da entrega possuem CPF opcional, com máscara `000.000.000-00`. O banco armazena os 11 dígitos, preservando zeros à esquerda. O mesmo CPF pode aparecer em várias compras. Para localizar entregas anteriores, abra **Todas as entregas** e pesquise o CPF com ou sem pontuação; o documento também aparece nos detalhes. Registros antigos continuam sem CPF até serem preenchidos. A migração `0004_entrega_cpf` é aplicada pelo instalador nas próximas atualizações.

Em uma nova entrega, o CPF aparece primeiro. Ao completar os 11 dígitos, o sistema consulta automaticamente a entrega cadastrada mais recentemente com esse documento e preenche nome, telefone e endereço. Revise os dados antes de salvar. Cupom, volumes e demais dados da compra não são reaproveitados. A consulta exige conexão; se o CPF não for encontrado, preencha os dados manualmente. A edição de uma entrega existente preserva seus dados históricos.

## Tema visual

O tema compartilhado em static/theme.css aplica a referencia clinical-tech-styleguide.html: azul #0F52BA, fundo #F8FAFC, bordas suaves e fonte Inter local em static/fonts/, com licenca SIL OFL. As regras de tela preservam a impressao compacta em retrato.

## Atualizar

```powershell
.\instalador.ps1 -HostsPermitidos '192.168.1.20,servidor'
```
