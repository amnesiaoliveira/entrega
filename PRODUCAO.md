# Super Baranda 1.1.0 — instalação local no Windows

## Instalar

O instalador usa PowerShell 4.0 ou superior e Python 3.12 x64, incluindo a plataforma Windows Server 2012 R2. Verifica Windows 8.1 / Server 2012 R2 (versão 6.3) ou posterior antes de alterar arquivos. Consulte os [requisitos do Python 3.12 para Windows](https://docs.python.org/3.12/using/windows.html).

Não é necessário instalar uv ou winget no servidor. O instalador baixa o Python **3.12.10** de python.org com TLS 1.2, confere seu SHA256, instala-o para todos os usuários e prepara um ambiente virtual exclusivo. As dependências de produção são instaladas pelo pip com versões e hashes travados em `requirements-production.txt`, exportado de `uv.lock`. A instalação precisa de internet; o serviço instalado não depende de internet ou sessão de usuário aberta.

Python 3.12.10 é o [último instalador oficial Windows da série 3.12](https://www.python.org/downloads/release/python-31210/); versões posteriores dessa série recebem correções de segurança como código-fonte. Para usar uma compilação 3.12 x64 mantida e compatível já instalada, informe `-PythonExecutavel 'C:\Python312\python.exe'`. O executável e suas bibliotecas precisam ser acessíveis à conta LocalService, fora do perfil privado de um usuário. Não substitua o Python por 3.13/3.14 no Server 2012 R2.

A compatibilidade foi verificada no código e nos testes com Python 3.12.10 em Windows moderno; a instalação integral em Server 2012 R2 precisa ser validada no servidor de destino. Mantenha as atualizações do Windows, certificados raiz e Universal CRT em dia; falhas do instalador Python ficam em `logs\python-install.log`.

Reserve um IP fixo para o servidor. Abra **PowerShell como Administrador**, entre na pasta extraída do projeto e execute, substituindo o IP pelo endereço real:

```powershell
.\instalador.ps1 -HostsPermitidos '192.168.1.20,servidor' -ImportarBanco 'C:\entrega\db.sqlite3'
```

O parâmetro `-ImportarBanco` copia consistentemente o banco existente, preservando usuários, entregas e histórico. Não substitui um banco no destino. **Encerre o servidor antigo antes da importação definitiva**, para que ninguém continue gravando no banco antigo. Para uma instalação vazia, omita esse parâmetro; será solicitado um administrador sem senha padrão. Se a política local impedir a execução, use `powershell.exe -ExecutionPolicy Bypass -File .\instalador.ps1 ...` nesta execução, sem alterar a política global.

Padrões:

| Item | Valor |
|---|---|
| Aplicação e Python | `C:\SuperBaranda` |
| Banco e configuração privada | `C:\ProgramData\SuperBaranda` |
| Serviço Windows | `SuperBarandaEntregas` |
| Conta de execução | LocalService, sem privilégios de administrador |
| Endereço HTTP | `http://IP-DO-SERVIDOR:8000` |
| Backup | Diário às 23h, hora local do Windows |
| Retenção | 30 dias, removidos somente após novo backup verificado |
| Tarefa agendada | `SuperBaranda-BackupDiario` |
| Fuso da aplicação | `America/La_Paz`, alterável por `-Fuso` |

Outros parâmetros: `-Destino`, `-Dados`, `-Porta`, `-Fuso`, `-HorarioBackup`, `-RetencaoDias` e `-ProxyHttps`. Use pastas locais dedicadas; SQLite não deve ficar em compartilhamento de rede. O instalador não muda o perfil de rede do Windows: a regra de firewall só permite a sub-rede local nos perfis **Privado/Domínio**. Não configure redirecionamento dessa porta no roteador.

O runtime recebe somente aplicação, fontes, ícones, templates, migrações e utilitário de backup. Testes, modelos de referência, ferramentas de desenvolvimento, caches, banco e segredos da origem não são copiados automaticamente. Os arquivos de referência e testes continuam no repositório para manutenção, mas são excluídos do arquivo de distribuição por `.gitattributes`.

## HTTP local e PWA com HTTPS

O padrão do instalador é HTTP na rede local com `DEBUG=0`, hosts explícitos e cookies compatíveis com HTTP. **HTTP não cifra senhas nem dados em trânsito e não habilita a instalação PWA/offline em dispositivos remotos.** Para operação com HTTPS, use `-ProxyHttps`, um nome DNS local e um proxy TLS no mesmo servidor:

```powershell
.\instalador.ps1 -HostsPermitidos 'entregas.loja.local' -ProxyHttps
```

Neste modo o Waitress escuta somente `127.0.0.1:8000`, com esquema HTTPS, e os cookies exigem conexão segura. O instalador não instala proxy nem certificado: configure o proxy para encaminhar a raiz do site, preservar o cabeçalho Host e usar certificado confiável em **cada computador/celular**. Não exponha o listener interno como se fosse um endpoint TLS. HSTS cobre apenas o host, sem preload ou subdomínios. Consulte os [requisitos de instalação PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) e a [orientação de HTTPS do Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/#https).

## Verificar e operar

O instalador verifica a resposta HTTP do serviço e registra backup inicial. Confira também a execução da tarefa agendada com a conta de serviço:

```powershell
Get-Service SuperBarandaEntregas
Start-ScheduledTask -TaskName SuperBaranda-BackupDiario
Get-ScheduledTaskInfo -TaskName SuperBaranda-BackupDiario
Get-ChildItem 'C:\ProgramData\SuperBaranda\backups'
Get-Content 'C:\ProgramData\SuperBaranda\logs\backup.log' -Tail 20
```

Após o término da tarefa, `LastTaskResult` deve ser `0`. Se o computador estiver desligado no horário, a tarefa executa quando disponível. Falhas recebem até três tentativas adicionais com intervalo de dez minutos. Consulte o Histórico do Agendador e o Visualizador de Eventos para falhas anteriores ao início do Python.

O serviço inicia automaticamente com atraso após reiniciar o Windows e o NSSM reinicia o processo se ele falhar. Os logs ficam em `logs\servico.log` e `logs\erros.log`, com rotação de 10 MB; `backup.log` mantém cinco arquivos de 1 MB. Os logs rotacionados do serviço são limpos após 30 dias no backup diário.

```powershell
Restart-Service SuperBarandaEntregas
Stop-Service SuperBarandaEntregas
Start-Service SuperBarandaEntregas
```

Depois de editar `production.json`, reinicie o serviço. Este arquivo contém a chave privada; não o envie ao GitHub. As pastas permitem acesso apenas a administradores, SYSTEM e LocalService. Use contas individuais para os operadores; o cadastro de entregador não cria login.

## Recuperar um backup

Os ZIPs contêm banco completo, configuração e data de criação. A cópia usa a [API de backup do SQLite](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup), funciona com o banco aberto e é verificada antes de ficar disponível. A exportação CSV não substitui esse backup.

Primeiro restaure para **outro nome**, nunca sobre o banco em uso:

```powershell
$pythonBaranda = 'C:\SuperBaranda\app\.venv\Scripts\python.exe'
$utilitarioBackup = 'C:\SuperBaranda\app\scripts\backup.py'
& $pythonBaranda $utilitarioBackup verify 'C:\ProgramData\SuperBaranda\backups\ARQUIVO.zip'
& $pythonBaranda $utilitarioBackup restore 'C:\ProgramData\SuperBaranda\backups\ARQUIVO.zip' 'C:\ProgramData\SuperBaranda\restaurado.sqlite3'
```

Verifique o código de saída antes de continuar. Para efetivar, feche o acesso dos operadores, pare o serviço e preserve o banco atual:

```powershell
Stop-Service SuperBarandaEntregas
$copiaAnterior = 'db-antes-restauracao-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.sqlite3'
Rename-Item -LiteralPath 'C:\ProgramData\SuperBaranda\db.sqlite3' -NewName $copiaAnterior
Move-Item -LiteralPath 'C:\ProgramData\SuperBaranda\restaurado.sqlite3' -Destination 'C:\ProgramData\SuperBaranda\db.sqlite3'
$env:DJANGO_CONFIG_FILE = 'C:\ProgramData\SuperBaranda\production.json'
& $pythonBaranda 'C:\SuperBaranda\app\manage.py' migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Falha nas migracoes; mantenha o servico parado e recupere a versao correspondente ao backup.' }
Start-Service SuperBarandaEntregas
```

O utilitário não aplica automaticamente a configuração do ZIP, pois os caminhos e hosts podem pertencer a outra máquina. Em recuperação completa, extraia `production.json` para a pasta privada e ajuste esses campos antes de iniciar. Use o código da mesma versão do backup ou uma versão posterior com migrações compatíveis. Caso exista `db.sqlite3-wal` após parar todos os processos, não troque arquivos manualmente: preserve o conjunto e investigue o encerramento do processo antes de continuar.

Copie regularmente os ZIPs para outro disco ou local protegido; o backup no mesmo disco não cobre falha física. Os ZIPs incluem dados pessoais e a chave da aplicação; proteja o destino externo com controle de acesso e criptografia. A cópia externa não é configurada automaticamente, pois depende do destino da loja.

## Atualizar ou remover o serviço

Extraia a nova versão em uma pasta de origem separada e execute novamente o instalador, com os mesmos caminhos, hosts e modo HTTP/HTTPS. **Não passe `-ImportarBanco` na atualização.** O instalador para o serviço, cria backup antes das alterações, preserva a chave privada, sincroniza dependências sem ferramentas de desenvolvimento, aplica migrações e atualiza o serviço/tarefa. Uma falha interrompe a instalação; não há rollback automático de código ou migrações. Corrija a causa e execute novamente, ou recupere o código anterior e seu backup. Não edite arquivos dentro de `app` durante a operação.

Para remover somente serviço e tarefa, preservando dados e backups, execute como Administrador:

```powershell
Stop-Service SuperBarandaEntregas
& 'C:\SuperBaranda\nssm.exe' remove SuperBarandaEntregas confirm
Unregister-ScheduledTask -TaskName SuperBaranda-BackupDiario -Confirm:$false
Remove-NetFirewallRule -Name SuperBaranda-Entregas-LAN -ErrorAction SilentlyContinue
```

O instalador exige privilégios administrativos para registrar serviço, tarefa, ACL e firewall. Testes de aplicação não substituem a verificação do serviço no Windows da loja, o teste de acesso por outro dispositivo e uma restauração de ensaio.
