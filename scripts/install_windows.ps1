$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is required but was not found."
    Write-Host "Install it with one of:"
    Write-Host "  winget install --id=astral-sh.uv -e"
    Write-Host "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    exit 1
}

if (-not (Test-Path "pyproject.toml")) {
    Write-Host "pyproject.toml was not found. Run this script from the project checkout."
    exit 1
}

if ((Test-Path "pywheels") -and -not (Get-ChildItem "pywheels" -Filter "*.whl" -File -Recurse)) {
    Write-Host "pywheels/ exists but contains no .whl files."
    exit 1
}

Write-Host "Syncing Python environment with uv..."
uv sync --frozen

Write-Host "Installing Playwright Chromium browser..."
uv run playwright install chromium

Write-Host ""
Write-Host "Install complete."
Write-Host "Run the bot with:"
Write-Host "  uv run python main.py"
