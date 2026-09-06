$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$environmentFile = Join-Path $projectRoot "backend\.env"
if (Test-Path -LiteralPath $environmentFile) {
    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
            $name = $Matches[1]
            $value = $Matches[2].Trim('"', "'")
            if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
}

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"
}
if (-not $env:DATA_SOURCE) {
    $env:DATA_SOURCE = "mock"
}
if (-not $env:MOCK_DATA_DIR) {
    $env:MOCK_DATA_DIR = Join-Path $projectRoot "mock\generated"
}

# The mock API depends on generated fixtures, and authentication depends on the
# local schema. Prepare both on first start so a fresh checkout does not appear
# to have a network/API failure in the frontend.
$mockRooms = Join-Path $env:MOCK_DATA_DIR "rooms.json"
$mockLive = Join-Path $env:MOCK_DATA_DIR "live_occupancy.json"
$mockHistory = Join-Path $env:MOCK_DATA_DIR "historical_api_views.json"
if ($env:DATA_SOURCE -eq "mock" -and (-not (Test-Path $mockRooms) -or -not (Test-Path $mockLive) -or -not (Test-Path $mockHistory))) {
    & (Join-Path $projectRoot ".venv\Scripts\python.exe") (Join-Path $projectRoot "mock\generate_mock_data.py") --output-dir $env:MOCK_DATA_DIR --seed 42
    if ($LASTEXITCODE -ne 0) { throw "Unable to generate mock API fixtures." }
}

& (Join-Path $projectRoot ".venv\Scripts\alembic.exe") upgrade head
if ($LASTEXITCODE -ne 0) { throw "Unable to apply database migrations." }

$apiHost = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

uv run uvicorn backend.app:app --host $apiHost --port $apiPort --reload
