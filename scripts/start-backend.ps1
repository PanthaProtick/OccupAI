$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"
}
if (-not $env:DATA_SOURCE) {
    $env:DATA_SOURCE = "mock"
}
if (-not $env:MOCK_DATA_DIR) {
    $env:MOCK_DATA_DIR = Join-Path $projectRoot "mock\generated"
}

$apiHost = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

uv run uvicorn backend.app:app --host $apiHost --port $apiPort --reload

