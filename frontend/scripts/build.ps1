$ErrorActionPreference = 'Stop'
$frontend = Resolve-Path (Join-Path $PSScriptRoot '..')
$python = Join-Path $frontend '..\.venv\Scripts\python.exe'
Push-Location $frontend
try {
  & $python -m PyInstaller --noconfirm --clean (Join-Path $frontend 'student-information-system.spec')
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
Write-Host "Built distributable at $frontend\dist\StudentInformationSystem\StudentInformationSystem.exe"
