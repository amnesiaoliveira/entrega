# Testes sem instalar servicos ou alterar o Windows.
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$installerPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'instalador.ps1'
$ast = [System.Management.Automation.Language.Parser]::ParseFile($installerPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { $parseErrors | Format-List; exit 1 }
$preflight = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Assert-SupportedWindows' }, $true)
. ([scriptblock]::Create($preflight.Extent.Text))
function Get-CimInstance { [pscustomobject]@{ Version = '6.2.9200'; Caption = 'Windows Server 2012' } }
try {
    Assert-SupportedWindows
    throw 'Teste falhou: Windows anterior ao 2012 R2 foi aceito.'
} catch {
    if ($_.Exception.Message -notlike '*Windows nao compativel*') { throw }
}
function Get-CimInstance { [pscustomobject]@{ Version = '6.3.9600'; Caption = 'Windows Server 2012 R2' } }
Assert-SupportedWindows
function Get-CimInstance { [pscustomobject]@{ Version = '10.0.14393'; Caption = 'Windows Server 2016' } }
Assert-SupportedWindows
Write-Output 'Sintaxe e verificacao de Windows: OK (sistemas simulados; sem instalar servico).'
