# Padrão de desenvolvimento — Django + VS Code

> Guia reutilizável para manter uma forma consistente de organizar, instalar, executar, depurar, testar e entregar projetos Django.

**Local recomendado:** raiz do repositório, com o nome `PADRAO_PROJETOS_DJANGO.md`.

**Base de referência:** Python 3.13, Django 5.2 LTS, uv, Ruff, pytest e VS Code.

**Princípio central:** as extensões ajudam no desenvolvimento, mas as regras do projeto devem estar versionadas no repositório e ser verificáveis pelo terminal e pela integração contínua.

A combinação adotada neste guia é:

**Django organizado por funcionalidades + uv para dependências + Ruff para qualidade do código + pytest para testes + Kanban para tarefas + Git para controlar alterações.**

As versões e a estrutura apresentadas são uma base de referência, não uma exigência para rebaixar ou reorganizar imediatamente projetos existentes. Adapte-as de forma explícita e documentada quando houver necessidades diferentes.

## Sumário

1. [Metodologias de trabalho](#1-metodologias-de-trabalho)
2. [Estrutura e organização do projeto](#2-estrutura-e-organização-do-projeto)
3. [Python e gerenciamento de dependências](#3-python-e-gerenciamento-de-dependências)
4. [Extensões do VS Code](#4-extensões-do-vs-code)
5. [Configurações versionadas](#5-configurações-versionadas)
6. [Verificações, testes e segurança](#6-verificações-testes-e-segurança)
7. [Projeto-base e adoção do padrão](#7-projeto-base-e-adoção-do-padrão)
8. [Checklist de adoção](#8-checklist-de-adoção)
9. [Referências oficiais](#9-referências-oficiais)

---

## 1. Metodologias de trabalho

Separe a organização do trabalho da organização do código. O objetivo é manter um processo simples, visível e verificável.

### 1.1. Kanban para organizar tarefas

Utilize um quadro com as seguintes colunas:

```text
A fazer → Em andamento → Em revisão → Concluído
```

Limite a quantidade de tarefas iniciadas simultaneamente. Como ponto de partida individual, mantenha uma ou duas tarefas em andamento, em vez de abrir várias funcionalidades ao mesmo tempo.

O Kanban trabalha com visualização e controle do fluxo de trabalho. Consulte o [Guia Kanban][kanban].

### 1.2. GitHub Flow para controlar alterações

Adote uma branch por alteração, commits pequenos, revisão por pull request e integração na `main` depois das verificações.

Esse fluxo permite controlar mudanças sem exigir um processo complexo de branches. Consulte a [documentação do GitHub Flow][github-flow].

### 1.3. Definição de pronto

Uma tarefa só deve ser considerada concluída quando:

- O comportamento esperado estiver implementado e atender aos critérios de aceite.
- Os testes pertinentes passarem e as verificações de qualidade não apresentarem problemas pendentes.
- As migrações necessárias estiverem incluídas.
- A documentação afetada estiver atualizada.

A definição de pronto torna explícito o padrão de qualidade esperado. O conceito também é tratado no [Guia Scrum][scrum].

### 1.4. Quando utilizar Scrum

Para trabalho individual, a recomendação inicial é **Kanban + GitHub Flow**.

Scrum pode ser adotado quando uma equipe realmente quiser trabalhar com objetivos de sprint, responsabilidades e eventos definidos. Não o adote apenas para cumprir uma formalidade metodológica.

### 1.5. Como descrever uma tarefa

Uma tarefa deve especificar um resultado verificável.

**Exemplo:**

> **Tarefa:** permitir o cadastro de produtos.  
> **Critérios de aceite:** exigir nome e unidade de medida; impedir códigos duplicados; permitir cadastro apenas a usuários autorizados; apresentar mensagens de validação.

Para acompanhar tarefas de vários repositórios, utilize uma ferramenta como o **GitHub Projects**, que permite organizar issues e pull requests em quadros e tabelas, com campos de prioridade, responsável e datas. Consulte a [documentação do GitHub Projects][github-projects].

---

## 2. Estrutura e organização do projeto

### 2.1. Estrutura inicial recomendada

Comece com uma única aplicação implantável, dividida em apps por área de negócio, como `produtos`, `clientes` e `pedidos`.

Essa organização se apoia na separação entre projetos e aplicações do Django. A estrutura abaixo é uma convenção deste guia, não uma obrigação do framework. Consulte a [documentação de aplicações reutilizáveis do Django][django-apps].

```text
meu-projeto/
├── .vscode/
│   ├── settings.json
│   ├── extensions.json
│   └── launch.json
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── produtos/
│   ├── migrations/
│   ├── templates/
│   │   └── produtos/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   └── tests.py
├── docs/
├── .editorconfig
├── .env.example
├── .gitignore
├── .python-version
├── manage.py
├── pyproject.toml
├── uv.lock
├── README.md
└── PADRAO_PROJETOS_DJANGO.md
```

Arquivos como `forms.py`, `urls.py` e `services.py` dentro do app são criados conforme a necessidade; não precisam existir em todo app desde o início.

### 2.2. Apps por responsabilidade de negócio

Organize os apps por funcionalidades ou áreas de negócio.

Evite colocar todas as funcionalidades em um app genérico chamado `core`. Também não crie automaticamente um app para cada tabela do banco.

### 2.3. Views focadas no atendimento da requisição

Mantenha a view responsável por entrada, permissões, chamada da operação e resposta.

Quando uma operação envolver várias etapas ou vários modelos — por exemplo, confirmar um pedido e movimentar o estoque — considere colocá-la em `services.py`.

### 2.4. Sem camadas desnecessárias

`services.py` não precisa existir em todo app. Uma funcionalidade simples pode continuar usando diretamente os recursos normais do Django.

Não imponha uma camada de repositórios ou arquitetura hexagonal a todos os projetos sem uma necessidade concreta.

### 2.5. Nomes consistentes

Escolha um idioma para os nomes do domínio e mantenha a consistência.

Evite misturar nomes como `Produto`, `Customer` e `pedido_total` sem um motivo claro. Documente a convenção escolhida no `README.md`.

### 2.6. Configurações por ambiente

No início, `config/settings.py` pode ser suficiente.

Quando existirem diferenças relevantes entre desenvolvimento, testes e produção, separe as configurações. Ao fazer essa mudança, atualize as referências utilizadas pelos testes, pelo servidor e pelo depurador.

---

## 3. Python e gerenciamento de dependências

### 3.1. Gerenciador escolhido: uv

Utilize **uv** para gerenciar dependências e o ambiente do projeto.

O uv trabalha com `pyproject.toml`, cria o ambiente `.venv` e mantém um `uv.lock` com as versões resolvidas. Versione o `uv.lock` no Git para permitir instalações consistentes entre máquinas. Consulte o [guia de projetos do uv][uv-projects].

**Regra:** utilize um gerenciador de dependências por projeto. Não mantenha Poetry, Pipenv e uv disputando a mesma função.

### 3.2. Versões de referência

O exemplo deste guia utiliza:

| Componente | Base de referência |
|---|---|
| Python | 3.13 |
| Django | Série 5.2 LTS |
| Ambiente virtual | `.venv` |
| Declaração de dependências | `pyproject.toml` |
| Versões resolvidas | `uv.lock` |

Python 3.13 e Django 5.2 são uma combinação suportada. A série Django 5.2 tem suporte estendido para correções de segurança e perda de dados até abril de 2028. Consulte as [notas de versão do Django 5.2][django-52].

> Ao reutilizar este guia no futuro, revise a compatibilidade e o ciclo de suporte das versões. Não trate esta base de referência como uma indicação permanente da versão mais recente.

### 3.3. Criação de um projeto novo

**Pré-requisitos:** Git e uv instalados.

Execute os comandos abaixo apenas para iniciar um projeto novo:

```bash
mkdir meu-projeto
cd meu-projeto

git init

uv init --bare --python 3.13
uv python pin 3.13

uv add "Django>=5.2,<5.3"
uv add --dev ruff pytest pytest-django pre-commit djlint

uv run django-admin startproject config .
uv run python manage.py startapp produtos
uv run python manage.py migrate
```

O `--bare` cria uma base mínima, sem adicionar uma estrutura de pacote que não será usada neste exemplo. Consulte a [documentação de inicialização do uv][uv-init].

Depois de criar o app, adicione a entrada abaixo à lista `INSTALLED_APPS` em `config/settings.py`, preservando os apps existentes:

```python
("produtos.apps.ProdutosConfig",)
```

> **Projetos existentes:** não execute toda essa sequência por cima de um projeto já iniciado. Introduza o gerenciador e as configurações em uma branch separada, preservando a estrutura atual.

---

## 4. Extensões do VS Code

Pesquise pelos identificadores abaixo na aba de extensões para localizar o pacote correto.

### 4.1. Desenvolvimento e padronização

| Extensão | Identificador | Utilidade |
|---|---|---|
| Python | `ms-python.python` | Integração com ambientes Python, execução e testes. |
| Pylance | `ms-python.vscode-pylance` | Autocompletar, navegação e análise de tipos. |
| Python Debugger | `ms-python.debugpy` | Depuração com pontos de parada e inspeção de variáveis. |
| Ruff | `charliermarsh.ruff` | Formatação, análise de código e organização de imports. |
| EditorConfig | `EditorConfig.EditorConfig` | Padronização de indentação, codificação e finais de linha. |
| Django | `batisteo.vscode-django` | Destaque de sintaxe, snippets e navegação em templates Django. |
| djLint | `monosans.djlint` | Formatação e análise de templates HTML. |

A extensão Python instala, por padrão, Pylance e Python Debugger como dependências opcionais. Confira o que já foi instalado antes de procurar pacotes adicionais. Consulte a [página da extensão Python][ext-python].

**Não ative Black, autopep8 e Ruff simultaneamente como formatadores de Python.** Neste padrão, o formatador escolhido é o Ruff, que também faz análise de código e organização de imports. Consulte a [documentação do Ruff para VS Code][ext-ruff].

EditorConfig, Django e djLint têm funções diferentes: padronização básica dos arquivos, suporte à linguagem dos templates e formatação dos templates, respectivamente. O djLint também deve estar instalado no ambiente Python, conforme o comando `uv add --dev` apresentado anteriormente. Consulte as páginas das extensões [EditorConfig][ext-editorconfig], [Django][ext-django] e [djLint][ext-djlint].

### 4.2. Gerenciamento de projetos e alterações

| Extensão | Identificador | Quando utilizar |
|---|---|---|
| Project Manager | `alefragnani.project-manager` | Salvar e alternar rapidamente entre vários projetos. |
| GitLens | `eamodio.gitlens` | Investigar histórico, autoria e mudanças no código. |
| GitHub Pull Requests | `GitHub.vscode-pull-request-github` | Trabalhar com issues e revisar pull requests no VS Code. |

Consulte as páginas de [Project Manager][ext-project-manager], [GitLens][ext-gitlens] e [GitHub Pull Requests][ext-github-pr].

**Distinção importante:** Project Manager ajuda a abrir e organizar repositórios. Para acompanhar tarefas, responsáveis e prazos, utilize um quadro de trabalho, como o [GitHub Projects][github-projects].

---

## 5. Configurações versionadas

Salve as configurações abaixo no próprio repositório para que o padrão acompanhe o projeto.

### 5.1. Regras de qualidade — `pyproject.toml`

Acrescente estas seções ao arquivo existente, sem apagar as dependências geradas pelo uv. Se alguma seção já existir, ajuste-a em vez de duplicá-la.

```toml
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["test_*.py", "*_tests.py", "tests.py"]
```

O Ruff aceita configuração no `pyproject.toml`. A seção do pytest informa ao `pytest-django` qual módulo de configurações carregar e inclui o nome `tests.py`, usado pelo app inicial do exemplo.

Ajuste `config.settings` se o projeto utilizar outro caminho. Mantenha o `target-version` do Ruff coerente com a versão mínima de Python adotada pelo projeto.

As regras selecionadas são um ponto de partida: análise básica, organização de imports, modernização de sintaxe e verificações adicionais. Aumente o rigor gradualmente, em vez de ativar todas as regras de uma vez.

Referências: [configuração do Ruff][ruff-config] e [configuração do pytest-django][pytest-django-config].

### 5.2. Configurações do editor — `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv",
  "python.analysis.typeCheckingMode": "basic",

  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["."],

  "ruff.importStrategy": "fromEnvironment",

  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },

  "files.associations": {
    "**/templates/**/*.html": "django-html"
  },

  "emmet.includeLanguages": {
    "django-html": "html"
  },

  "djlint.useVenv": true,

  "[django-html]": {
    "editor.defaultFormatter": "monosans.djlint",
    "editor.formatOnSave": true
  }
}
```

Neste padrão, Ruff é responsável pelo Python, enquanto djLint formata os templates reconhecidos como `django-html`.

As ações configuradas como `explicit` executam as correções ao salvar explicitamente, por exemplo, com `Ctrl+S`. Consulte a [documentação da extensão Ruff][ext-ruff].

Após abrir o projeto:

1. Pressione `Ctrl+Shift+P`.
2. Execute `Python: Select Interpreter`.
3. Selecione o ambiente `.venv` do projeto.

Essa seleção é especialmente importante em projetos que já utilizavam outro interpretador. Alterar `python.defaultInterpreterPath` não substitui automaticamente uma seleção anterior. Consulte a [referência de configurações Python do VS Code][vscode-python-settings].

A opção `ruff.importStrategy` com valor `fromEnvironment` faz o Ruff procurar a instalação do ambiente, ajudando a utilizar a versão definida pelo projeto. Na ausência dela, a extensão pode utilizar sua versão embutida. Consulte as [configurações de editor do Ruff][ruff-editor-settings].

### 5.3. Extensões recomendadas — `.vscode/extensions.json`

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.debugpy",
    "charliermarsh.ruff",
    "EditorConfig.EditorConfig",
    "batisteo.vscode-django",
    "monosans.djlint"
  ]
}
```

Esse arquivo compartilha as extensões recomendadas para o projeto. Ele não obriga a instalação nem substitui verificações automáticas. Consulte a [documentação de extensões do VS Code][vscode-extensions].

Extensões pessoais, como Project Manager, podem ficar fora dessa lista, a menos que a equipe também queira recomendá-las.

### 5.4. Depuração — `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django: desenvolvimento",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["runserver"],
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "django": true,
      "justMyCode": true
    }
  ]
}
```

Com o interpretador correto selecionado, inicie a depuração com **F5**.

O parâmetro `"django": true` também habilita suporte à depuração de templates Django. Consulte o [tutorial de Django no VS Code][vscode-django].

### 5.5. Padronização básica — `.editorconfig`

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4
trim_trailing_whitespace = true

[*.{json,yml,yaml}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

Esse arquivo define convenções básicas compartilháveis entre editores que suportam EditorConfig. Mantenha Ruff e djLint como responsáveis pela formatação específica de Python e templates.

Referência: [EditorConfig][editorconfig].

---

## 6. Verificações, testes e segurança

### 6.1. O padrão deve funcionar fora do VS Code

O projeto deve conseguir verificar seu padrão pelo terminal, mesmo quando alguém utilizar outro editor.

Depois de criar os testes, utilize esta rotina de verificação:

```bash
uv sync --locked

uv run --locked ruff check .
uv run --locked ruff format --check
uv run --locked pytest

uv run --locked python manage.py check
uv run --locked python manage.py makemigrations --check --dry-run
```

O `--locked` impede que o uv atualize silenciosamente o arquivo de lock quando ele estiver incompatível com as dependências declaradas. Consulte a [documentação de sincronização do uv][uv-sync].

O Django oferece verificações do projeto e uma opção para detectar alterações de modelos sem as migrações correspondentes. Consulte a [referência de comandos do Django][django-admin].

### 6.2. Integração contínua

Execute a mesma sequência de verificações na integração contínua: as verificações automáticas disparadas quando uma alteração é enviada ao repositório.

O salvamento automático no editor não substitui essas verificações.

### 6.3. pre-commit

Configure o **pre-commit** para executar verificações rápidas antes dos commits.

Ele exige um arquivo `.pre-commit-config.yaml` com os hooks escolhidos e a instalação dos hooks no repositório. Apenas instalar o pacote não ativa essas verificações.

A configuração de hooks deve ser definida conforme as verificações adotadas no projeto. Consulte a [documentação do pre-commit][pre-commit].

### 6.4. Prioridades para os testes

Ao iniciar a suíte de testes, priorize:

- Regras de negócio e validações.
- Permissões de acesso.
- Regressões de erros já corrigidos.

Não persiga apenas uma porcentagem alta de cobertura. Os testes devem dar confiança sobre o comportamento relevante do sistema.

### 6.5. Configurações e segredos

Não inclua senhas, tokens ou a chave real de produção no repositório.

Mantenha `.env.example` apenas com nomes de variáveis e valores fictícios. Em produção, revise `DEBUG`, `SECRET_KEY` e `ALLOWED_HOSTS`, e execute `check --deploy` usando as configurações reais de produção.

Consulte o [checklist de implantação do Django][django-deployment].

> Criar um arquivo `.env` não basta para o Django carregá-lo. Defina explicitamente como as variáveis chegam ao processo: pelo ambiente de execução ou por um carregador configurado no projeto.

A opção `python.envFile` do VS Code não deve ser tratada como uma configuração universal para qualquer execução pelo terminal. Consulte a [referência de configurações Python do VS Code][vscode-python-settings].

---

## 7. Projeto-base e adoção do padrão

### 7.1. Crie um repositório modelo

Depois de validar a base, crie um repositório chamado, por exemplo:

```text
django-projeto-base
```

No GitHub, ele pode ser marcado como um **template repository**, permitindo iniciar novos repositórios com a mesma estrutura. Consulte a [documentação de repositórios modelo][github-template].

### 7.2. Documentação mínima

Mantenha no `README.md` um roteiro único para:

- Instalar e configurar o ambiente, incluindo as variáveis necessárias.
- Executar e depurar a aplicação.
- Rodar testes e verificações de qualidade.

Utilize `docs/` para registrar decisões importantes, como o motivo de uma operação estar em um serviço ou a abordagem adotada para uma integração.

Inclua no `README.md` um link para este guia:

```markdown
## Padrão de desenvolvimento

Consulte o [padrão de desenvolvimento Django + VS Code](PADRAO_PROJETOS_DJANGO.md)
para conhecer a estrutura, as ferramentas e as verificações adotadas neste projeto.
```

### 7.3. Perfil Django no VS Code

Crie um perfil chamado **Django** com as extensões e preferências pessoais utilizadas nesse tipo de projeto.

Perfis permitem manter conjuntos de configurações e extensões associados aos ambientes de trabalho. As regras obrigatórias do projeto devem continuar no repositório, não apenas no perfil pessoal. Consulte a [documentação de perfis do VS Code][vscode-profiles].

### 7.4. Adoção em projetos existentes

Adote o padrão nesta ordem:

1. **Ambiente e editor:** dependências, `.venv`, Ruff e configurações compartilhadas.
2. **Qualidade automatizada:** testes, verificações de migrações e integração contínua.
3. **Organização do código:** mova responsabilidades gradualmente, sem misturar uma grande reformatação com mudanças funcionais.

**Resultado esperado:** abrir qualquer projeto e encontrar a mesma forma de instalar, executar, depurar, testar e entregar uma alteração, sem precisar descobrir novamente como aquele projeto funciona.

---

## 8. Checklist de adoção

Use esta lista ao iniciar um projeto ou incorporar o padrão em um projeto existente. Marque os itens depois de implementá-los; manter este guia no repositório, por si só, não aplica as configurações.

### Ambiente e dependências

- [ ] Definir e registrar a versão de Python do projeto.
- [ ] Escolher uma versão suportada de Django e verificar sua compatibilidade com o Python.
- [ ] Utilizar um único gerenciador de dependências.
- [ ] Configurar o ambiente `.venv`.
- [ ] Versionar `pyproject.toml`, `uv.lock` e `.python-version`.

### Estrutura e editor

- [ ] Organizar apps por responsabilidade de negócio.
- [ ] Definir a convenção de nomes do domínio.
- [ ] Adicionar as configurações do Ruff e do pytest ao `pyproject.toml`.
- [ ] Criar ou ajustar `.vscode/settings.json`.
- [ ] Criar ou ajustar `.vscode/extensions.json`.
- [ ] Criar ou ajustar `.vscode/launch.json`.
- [ ] Criar ou ajustar `.editorconfig`.
- [ ] Selecionar o interpretador `.venv` no VS Code.
- [ ] Validar a formatação de Python e dos templates.
- [ ] Validar a depuração com F5.

### Qualidade e entrega

- [ ] Criar testes para os comportamentos prioritários.
- [ ] Validar a rotina de verificações pelo terminal.
- [ ] Configurar as verificações na integração contínua.
- [ ] Definir os hooks e instalar o pre-commit, quando adotado.
- [ ] Conferir as migrações necessárias.
- [ ] Garantir que segredos reais não sejam versionados.
- [ ] Documentar como as variáveis de ambiente são carregadas.

### Gestão e documentação

- [ ] Criar o quadro de tarefas e definir os critérios de aceite.
- [ ] Registrar a definição de pronto.
- [ ] Adotar branches e revisão de alterações.
- [ ] Documentar instalação, execução e testes no `README.md`.
- [ ] Incluir no `README.md` um link para este guia.
- [ ] Registrar decisões importantes em `docs/`.
- [ ] Registrar adaptações ou exceções ao padrão quando necessárias.

---

## 9. Referências oficiais

Os links abaixo acompanham as ferramentas e práticas citadas neste guia. Consulte a documentação correspondente à versão adotada pelo projeto ao atualizar a base.

| Assunto | Documentação |
|---|---|
| Kanban | [Guia Kanban][kanban] |
| Scrum e definição de pronto | [Guia Scrum][scrum] |
| Fluxo de alterações | [GitHub Flow][github-flow] |
| Gestão de tarefas | [GitHub Projects][github-projects] |
| Repositórios modelo | [Template repositories no GitHub][github-template] |
| Aplicações Django | [Aplicações reutilizáveis][django-apps] |
| Django 5.2 | [Notas de versão][django-52] |
| Comandos do Django | [Referência de django-admin e manage.py][django-admin] |
| Implantação Django | [Checklist de implantação][django-deployment] |
| Projetos com uv | [Guia de projetos][uv-projects] |
| Inicialização com uv | [Inicialização de projetos][uv-init] |
| Sincronização com uv | [Lock e sincronização][uv-sync] |
| Ruff | [Configuração][ruff-config] e [configurações do editor][ruff-editor-settings] |
| pytest-django | [Configuração do Django nos testes][pytest-django-config] |
| pre-commit | [Documentação][pre-commit] |
| VS Code e Python | [Referência de configurações][vscode-python-settings] |
| VS Code e Django | [Tutorial e depuração][vscode-django] |
| Extensões do VS Code | [Gerenciamento de extensões][vscode-extensions] |
| Perfis do VS Code | [Perfis][vscode-profiles] |
| EditorConfig | [Documentação][editorconfig] |

[kanban]: https://kanbanguides.org/english/
[scrum]: https://scrumguides.org/scrum-guide.html
[github-flow]: https://docs.github.com/en/get-started/using-github/github-flow
[github-projects]: https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects
[github-template]: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository
[django-apps]: https://docs.djangoproject.com/en/5.2/intro/reusable-apps/
[django-52]: https://docs.djangoproject.com/en/5.2/releases/5.2/
[django-admin]: https://docs.djangoproject.com/en/5.2/ref/django-admin/
[django-deployment]: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
[uv-projects]: https://docs.astral.sh/uv/guides/projects/
[uv-init]: https://docs.astral.sh/uv/concepts/projects/init/
[uv-sync]: https://docs.astral.sh/uv/concepts/projects/sync/
[ruff-config]: https://docs.astral.sh/ruff/configuration/
[ruff-editor-settings]: https://docs.astral.sh/ruff/editors/settings/
[pytest-django-config]: https://pytest-django.readthedocs.io/en/latest/configuring_django.html
[pre-commit]: https://pre-commit.com/
[vscode-python-settings]: https://code.visualstudio.com/docs/python/settings-reference
[vscode-django]: https://code.visualstudio.com/docs/python/tutorial-django
[vscode-extensions]: https://code.visualstudio.com/docs/configure/extensions/extension-marketplace
[vscode-profiles]: https://code.visualstudio.com/docs/configure/profiles
[editorconfig]: https://editorconfig.org/
[ext-python]: https://marketplace.visualstudio.com/items?itemName=ms-python.python
[ext-ruff]: https://github.com/astral-sh/ruff-vscode
[ext-editorconfig]: https://marketplace.visualstudio.com/items?itemName=EditorConfig.EditorConfig
[ext-django]: https://marketplace.visualstudio.com/items?itemName=batisteo.vscode-django
[ext-djlint]: https://marketplace.visualstudio.com/items?itemName=monosans.djlint
[ext-project-manager]: https://marketplace.visualstudio.com/items?itemName=alefragnani.project-manager
[ext-gitlens]: https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens
[ext-github-pr]: https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github
