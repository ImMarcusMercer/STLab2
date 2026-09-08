$ErrorActionPreference = 'Stop'
$repo = Resolve-Path $PSScriptRoot
$venv = Join-Path $repo '.venv'
if (-not (Test-Path -LiteralPath $venv)) { python -m venv $venv }
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install -r (Join-Path $repo 'backend\requirements.txt')
& $python -m pip install -r (Join-Path $repo 'frontend\requirements-dev.txt')
& $python (Join-Path $repo 'backend\scripts\setup_local.py')
& $python (Join-Path $repo 'frontend\scripts\setup_local.py')
& $python (Join-Path $repo 'backend\manage.py') migrate
& $python (Join-Path $repo 'backend\manage.py') seed_demo
Write-Host 'Setup complete. Read backend\.env locally for DEMO_PASSWORD.'
