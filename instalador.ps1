#Requires -Version 5.1
<#
.SYNOPSIS
Instala/atualiza o Super Baranda no Windows x64 como servico e agenda backup diario.
.EXAMPLE
.\instalador.ps1 -HostsPermitidos '192.168.1.20,servidor' -ImportarBanco 'C:\entrega\db.sqlite3'
#>
[CmdletBinding()]
param(
    [string]$Destino = 'C:\SuperBaranda',
    [string]$Dados = "$env:ProgramData\SuperBaranda",
    [Parameter(Mandatory = $true)][string]$HostsPermitidos,
    [ValidateRange(1024, 65535)][int]$Porta = 8000,
    [string]$Fuso = 'America/La_Paz',
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')][string]$HorarioBackup = '23:00',
    [ValidateRange(1, 3650)][int]$RetencaoDias = 30,
    [string]$ImportarBanco,
    [switch]$ProxyHttps
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$serviceName = 'SuperBarandaEntregas'
$taskName = 'SuperBaranda-BackupDiario'
$firewallName = 'SuperBaranda-Entregas-LAN'

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falha em $Executable (codigo $LASTEXITCODE)." }
}
function Protect-Directory {
    param([string]$Path, [string]$ServiceRights)
    # SIDs independem do idioma do Windows. Apenas administradores, SYSTEM e LocalService.
    $acl = New-Object System.Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($entry in @(@('S-1-5-32-544', 'FullControl'), @('S-1-5-18', 'FullControl'), @('S-1-5-19', $ServiceRights))) {
        $sid = New-Object System.Security.Principal.SecurityIdentifier($entry[0])
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, $entry[1], 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

$administrator = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $administrator.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra o PowerShell como Administrador para instalar servico, tarefa e regra de firewall.'
}
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Este pacote requer Windows x64.' }
$source = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$Destino = [IO.Path]::GetFullPath($Destino).TrimEnd('\')
$Dados = [IO.Path]::GetFullPath($Dados).TrimEnd('\')
foreach ($path in @($Destino, $Dados)) {
    if ($path -notmatch '^[A-Za-z]:\\.+' -or $path -match '["\r\n]' -or $path -eq $source -or $source.StartsWith($path + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Use pastas locais dedicadas, diferentes da origem e sem aspas.'
    }
}
if ($Destino -eq $Dados -or $Dados.StartsWith($Destino + '\', [StringComparison]::OrdinalIgnoreCase) -or $Destino.StartsWith($Dados + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'As pastas da aplicacao e dos dados devem ser separadas.'
}
$hostsList = @($HostsPermitidos.Split(',') | ForEach-Object { $_.Trim().ToLowerInvariant() } | Select-Object -Unique)
foreach ($hostName in $hostsList) {
    if ($hostName -notmatch '^[a-z0-9][a-z0-9.-]*$') { throw 'Informe nomes DNS ou IPv4 separados por virgula, sem protocolo, porta ou curingas.' }
}
$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
$configPath = Join-Path $Dados 'production.json'
$appPath = Join-Path $Destino 'app'
$python = Join-Path $appPath '.venv\Scripts\python.exe'
$nssm = Join-Path $Destino 'nssm.exe'
$backupPath = Join-Path $Dados 'backups'
$database = Join-Path $Dados 'db.sqlite3'
if ((Test-Path -LiteralPath $Destino) -and -not (Test-Path -LiteralPath (Join-Path $Destino '.baranda-install'))) {
    throw 'Destino existente sem identificacao do instalador. Escolha uma pasta nova.'
}
if ((Test-Path -LiteralPath $Dados) -and -not (Test-Path -LiteralPath (Join-Path $Dados '.baranda-data'))) {
    throw 'Pasta de dados existente sem identificacao do instalador. Escolha uma pasta nova.'
}
if ($existing) {
    $parameters = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\$serviceName\Parameters"
    if ($parameters.Application -ne $python) { throw 'Ja existe um servico com este nome em outro destino.' }
    if (-not (Test-Path -LiteralPath $configPath)) { throw 'Configuracao da instalacao existente nao encontrada.' }
}
if ($ImportarBanco -and (Test-Path -LiteralPath $database)) { throw 'O banco de destino ja existe; a importacao nunca o substitui.' }
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCommand) { throw 'Instale uv antes: winget install --id astral-sh.uv -e. Reabra o PowerShell.' }
# Verifica artefatos antes de parar qualquer servico.
foreach ($item in @('config', 'entregas', 'templates', 'static', 'manage.py', 'servico.py', 'pyproject.toml', 'uv.lock', '.python-version', 'scripts\backup.py', 'nssm\win64\nssm.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $item))) { throw "Arquivo do pacote ausente: $item" }
}
if ($ImportarBanco -and -not (Test-Path -LiteralPath $ImportarBanco -PathType Leaf)) { throw 'Banco de origem nao encontrado.' }
if ($existing -and $existing.Status -ne 'Stopped') { Stop-Service $serviceName; (Get-Service $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(45)) }
if (Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue) {
    if ($existing) { Start-Service $serviceName }
    throw "Porta $Porta ocupada. Encerre o servidor anterior ou escolha outra porta."
}
if ($existing) {
    Invoke-Checked $python @((Join-Path $appPath 'scripts\backup.py'), 'create', '--config', $configPath, '--destination', $backupPath, '--days', "$RetencaoDias")
}
foreach ($directory in @($Destino, $Dados, $appPath, $backupPath, (Join-Path $Dados 'logs'), (Join-Path $appPath 'scripts'))) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
Protect-Directory $Destino 'ReadAndExecute'
Protect-Directory $Dados 'Modify'
Set-Content -LiteralPath (Join-Path $Destino '.baranda-install') -Value 'SuperBaranda' -Encoding ASCII
Set-Content -LiteralPath (Join-Path $Dados '.baranda-data') -Value 'SuperBaranda' -Encoding ASCII
# Copia somente o runtime; nenhum banco, segredo, teste ou cache da origem.
foreach ($directory in @('config', 'entregas', 'templates', 'static')) {
    & robocopy (Join-Path $source $directory) (Join-Path $appPath $directory) /E /XD __pycache__ /XF '*.pyc' tests.py /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "Falha ao copiar $directory." }
}
foreach ($file in @('manage.py', 'servico.py', 'pyproject.toml', 'uv.lock', '.python-version')) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination $appPath -Force
}
Copy-Item -LiteralPath (Join-Path $source 'scripts\backup.py') -Destination (Join-Path $appPath 'scripts\backup.py') -Force
Copy-Item -LiteralPath (Join-Path $source 'nssm\win64\nssm.exe') -Destination $nssm -Force
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Destino 'python'
$env:UV_PYTHON_PREFERENCE = 'only-managed'
$env:UV_LINK_MODE = 'copy'
Invoke-Checked $uvCommand.Source @('sync', '--project', $appPath, '--locked', '--no-dev', '--python', '3.14')
if (Test-Path -LiteralPath $configPath) {
    $oldConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($oldConfig.DJANGO_DATABASE_PATH -ne $database) { throw 'Caminho do banco diverge da configuracao existente.' }
    $secret = $oldConfig.DJANGO_SECRET_KEY
} else {
    $secret = & $python -c 'import secrets; print(secrets.token_urlsafe(64))'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar chave privada.' }
}
$config = [ordered]@{
    DJANGO_DEBUG = '0'; DJANGO_SECRET_KEY = $secret.Trim()
    DJANGO_ALLOWED_HOSTS = (($hostsList + @('localhost', '127.0.0.1')) | Select-Object -Unique) -join ','
    DJANGO_CSRF_TRUSTED_ORIGINS = ''
    DJANGO_TIME_ZONE = $Fuso; DJANGO_DATABASE_PATH = $database
    DJANGO_HTTPS = $(if ($ProxyHttps) { '1' } else { '0' }); PORT = $Porta
}
$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
$env:DJANGO_CONFIG_FILE = $configPath
$env:PYTHONDONTWRITEBYTECODE = '1'
if ($ImportarBanco) {
    Invoke-Checked $python @((Join-Path $appPath 'scripts\backup.py'), 'snapshot', $ImportarBanco, $database)
}
Invoke-Checked $python @((Join-Path $appPath 'manage.py'), 'check')
Invoke-Checked $python @((Join-Path $appPath 'manage.py'), 'migrate', '--noinput')
Invoke-Checked $python @((Join-Path $appPath 'manage.py'), 'collectstatic', '--noinput')
$adminCount = & $python (Join-Path $appPath 'manage.py') shell --no-imports -c 'from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_superuser=True,is_active=True).count())'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao verificar usuarios.' }
if ($adminCount.Trim() -eq '0') {
    Write-Host 'Crie o administrador. Nenhuma senha padrao sera criada.'
    Invoke-Checked $python @((Join-Path $appPath 'manage.py'), 'createsuperuser')
}
Invoke-Checked $python @((Join-Path $appPath 'scripts\backup.py'), 'create', '--config', $configPath, '--destination', $backupPath, '--days', "$RetencaoDias")
if (-not $existing) { Invoke-Checked $nssm @('install', $serviceName, $python) }
Invoke-Checked $nssm @('set', $serviceName, 'AppDirectory', $appPath)
Invoke-Checked $nssm @('set', $serviceName, 'AppParameters', ('"{0}" --config "{1}"' -f (Join-Path $appPath 'servico.py'), $configPath))
Invoke-Checked $nssm @('set', $serviceName, 'AppEnvironmentExtra', 'PYTHONUNBUFFERED=1', 'PYTHONDONTWRITEBYTECODE=1', 'PYTHONUTF8=1')
Invoke-Checked $nssm @('set', $serviceName, 'ObjectName', 'NT AUTHORITY\LocalService')
Invoke-Checked $nssm @('set', $serviceName, 'DisplayName', 'Super Baranda - Entregas')
Invoke-Checked $nssm @('set', $serviceName, 'Start', 'SERVICE_DELAYED_AUTO_START')
Invoke-Checked $nssm @('set', $serviceName, 'AppExit', 'Default', 'Restart')
Invoke-Checked $nssm @('set', $serviceName, 'AppRestartDelay', '5000')
Invoke-Checked $nssm @('set', $serviceName, 'AppStdout', (Join-Path $Dados 'logs\servico.log'))
Invoke-Checked $nssm @('set', $serviceName, 'AppStderr', (Join-Path $Dados 'logs\erros.log'))
Invoke-Checked $nssm @('set', $serviceName, 'AppRotateFiles', '1')
Invoke-Checked $nssm @('set', $serviceName, 'AppRotateOnline', '1')
Invoke-Checked $nssm @('set', $serviceName, 'AppRotateBytes', '10485760')
Invoke-Checked $nssm @('set', $serviceName, 'AppRotateSeconds', '86400')
$taskArguments = '"{0}" create --config "{1}" --destination "{2}" --days {3}' -f (Join-Path $appPath 'scripts\backup.py'), $configPath, $backupPath, $RetencaoDias
$action = New-ScheduledTaskAction -Execute $python -Argument $taskArguments -WorkingDirectory $appPath
$trigger = New-ScheduledTaskTrigger -Daily -At $HorarioBackup
$principal = New-ScheduledTaskPrincipal -UserId 'S-1-5-19' -LogonType ServiceAccount
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Get-NetFirewallRule -Name $firewallName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
if (-not $ProxyHttps) {
    New-NetFirewallRule -Name $firewallName -DisplayName 'Super Baranda - rede local' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Porta -Profile Private,Domain -RemoteAddress LocalSubnet -Program $python | Out-Null
}
Start-Service $serviceName
$healthy = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        # Em modo proxy, o esquema https e definido pelo Waitress na interface loopback.
        $response = Invoke-WebRequest "http://127.0.0.1:$Porta/entrar/" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200 -and (Get-Service $serviceName).Status -eq 'Running') { $healthy = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $healthy) { throw "Servico sem resposta. Consulte $Dados\logs\erros.log e o Visualizador de Eventos." }
Write-Host "Instalacao concluida. Servico: $serviceName. Backup diario: $HorarioBackup (hora do Windows), retencao $RetencaoDias dias."
Write-Host "Dados e backups: $Dados. Configuracao privada: $configPath."
if ($ProxyHttps) { Write-Host "Configure o proxy HTTPS para 127.0.0.1:$Porta e um certificado confiavel nos dispositivos." }
else { Write-Host "Acesse http://$($hostsList[0]):$Porta. Este modo HTTP nao habilita instalacao PWA remota." }
