param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$rooms = Invoke-RestMethod -Uri "$BaseUrl/api/rooms" -Method Get
$occupancy = Invoke-RestMethod -Uri "$BaseUrl/api/occupancy" -Method Get
$history = Invoke-RestMethod -Uri "$BaseUrl/api/history?room_id=room_cse_201&range=day&metric=percentage" -Method Get
$docs = Invoke-WebRequest -Uri "$BaseUrl/docs" -Method Get

if ($rooms.meta.count -ne 7 -or $rooms.data.Count -ne 7) {
    throw "Rooms smoke check failed: expected seven canonical rooms"
}
if ($occupancy.meta.count -ne 7 -or $occupancy.data.Count -ne 7) {
    throw "Occupancy smoke check failed: expected seven camera states"
}
if ($history.meta.room_id -ne "room_cse_201" -or $history.meta.metric -ne "percentage") {
    throw "History smoke check failed: response metadata did not match the request"
}
if ($docs.StatusCode -ne 200) {
    throw "API documentation smoke check failed"
}

node frontend/smoke-api.mjs $BaseUrl

Write-Output "Smoke test passed: rooms=7 occupancy=7 history=$($history.meta.count)"
