param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root

if ($Clean) {
    if (Test-Path "$Root\build") { Remove-Item "$Root\build" -Recurse -Force }
    if (Test-Path "$Root\dist") { Remove-Item "$Root\dist" -Recurse -Force }
}

python -m pip install --upgrade pip
python -m pip install -r "$Root\requirements.txt"
python -m pip install pyinstaller

$args = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "ScheduleBuilder",
    "--add-data", "streamlit_app.py;.",
    "--add-data", "binge_schedule;binge_schedule",
    "--add-data", "config;config",
    "--add-data", "data;data",
    "--add-data", "cloud;cloud",
    "--collect-all", "streamlit",
    "--collect-all", "pandas",
    "--collect-all", "openpyxl",
    "desktop_launcher.py"
)

python -m PyInstaller @args

Write-Host ""
Write-Host "Desktop bundle created at: $Root\dist\ScheduleBuilder"
