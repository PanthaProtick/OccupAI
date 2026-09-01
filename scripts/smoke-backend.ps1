param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$rooms = Invoke-RestMethod -Uri "$BaseUrl/api/rooms" -Method Get
$occupancy = Invoke-RestMethod -Uri "$BaseUrl/api/occupancy" -Method Get
$history = Invoke-RestMethod -Uri "$BaseUrl/api/history?room_id=room_tt_ground&range=day&metric=percentage" -Method Get
$docs = Invoke-WebRequest -Uri "$BaseUrl/docs" -Method Get

if ($rooms.meta.count -ne 4 -or $rooms.data.Count -ne 4) {
    throw "Rooms smoke check failed: expected four ground-floor rooms"
}
if ($occupancy.meta.count -ne 4 -or $occupancy.data.Count -ne 4) {
    throw "Occupancy smoke check failed: expected four camera states"
}
if ($history.meta.room_id -ne "room_tt_ground" -or $history.meta.metric -ne "percentage") {
    throw "History smoke check failed: response metadata did not match the request"
}
if ($docs.StatusCode -ne 200) {
    throw "API documentation smoke check failed"
}

node frontend/smoke-api.mjs $BaseUrl

Write-Output "Smoke test passed: rooms=4 occupancy=4 history=$($history.meta.count)"
