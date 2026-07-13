# Compare manifest MP3 expectations vs deploy/music/liked/
param(
    [string]$Manifest = "playlist-latest1000.json",
    [string]$MusicDir = "music/liked"
)

$Deploy = Split-Path $PSScriptRoot -Parent
$manifestPath = Join-Path $Deploy $Manifest
$musicPath = Join-Path $Deploy $MusicDir

$data = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$have = @{}
Get-ChildItem $musicPath -Filter "*.mp3" -ErrorAction SilentlyContinue | ForEach-Object {
    $have[$_.Name] = $_.Length
}

$missing = @()
$small = @()
$ok = 0

foreach ($s in $data.songs) {
    $artist = if ($s.artist) { $s.artist } else { "Unknown" }
    $name = "$artist - $($s.name).mp3"
    $name = $name -replace '[<>:"/\\|?*]', '_'
    if ($name.Length -gt 200) { $name = $name.Substring(0, 200) + ".mp3" }
    if (-not $have.ContainsKey($name)) {
        $missing += [PSCustomObject]@{ id = $s.id; likedIndex = $s.likedIndex; file = $name }
    } elseif ($have[$name] -lt 500000) {
        $small += [PSCustomObject]@{ id = $s.id; file = $name; size = $have[$name] }
    } else {
        $ok++
    }
}

Write-Host "manifest: $Manifest"
Write-Host "expected: $($data.songs.Count) | ok: $ok | missing: $($missing.Count) | too_small: $($small.Count)"
if ($missing.Count -gt 0 -and $missing.Count -le 20) {
    $missing | Format-Table -AutoSize
} elseif ($missing.Count -gt 20) {
    $missing | Select-Object -First 10 | Format-Table -AutoSize
    Write-Host "... and $($missing.Count - 10) more"
}
