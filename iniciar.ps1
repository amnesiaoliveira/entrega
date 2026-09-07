$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
uv sync --locked
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python manage.py migrate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$contagemUsuarios = uv run python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_superuser=True).count())" --no-imports
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($contagemUsuarios.Trim() -eq '0') {
    Write-Host 'Crie a conta do responsavel pelo Super Baranda:'
    uv run python manage.py createsuperuser
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'Abra http://127.0.0.1:8000 no navegador. Ctrl+C encerra o servidor.'
uv run python manage.py runserver 127.0.0.1:8000
