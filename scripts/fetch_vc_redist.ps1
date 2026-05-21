param(
    [string]$OutDir = (Join-Path (Split-Path $PSScriptRoot -Parent) "packaging\windows\redist")
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$outFile = Join-Path $OutDir "vc_redist.x64.exe"
$url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

if (Test-Path $outFile) {
    Write-Host "VC++ redist already present: $outFile"
    exit 0
}

Write-Host "Downloading Microsoft VC++ 2015-2022 redist..."
Invoke-WebRequest -Uri $url -OutFile $outFile
Write-Host "Saved $outFile"
