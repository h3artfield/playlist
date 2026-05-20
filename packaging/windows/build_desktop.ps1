param(
    [switch]$Clean,
    [switch]$Demo
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

$iconIco = "$Root\packaging\windows\ScheduleBuilder.ico"
$iconPng = "$Root\packaging\windows\ScheduleBuilder.png"
if (Test-Path $iconPng) {
    Write-Host "Building Windows app icon..."
    python -m pip install Pillow
    python "$Root\scripts\build_app_icon.py"
}

$splashSrc = "$Root\packaging\windows\assets\splash.mp4"
$splashPublic = "$Root\scheduler-ui\public\splash.mp4"
if (Test-Path $splashSrc) {
    Copy-Item $splashSrc $splashPublic -Force
    Write-Host "Copied splash video into scheduler-ui/public/splash.mp4"
} elseif (-not (Test-Path $splashPublic)) {
    Write-Warning "No splash.mp4 found. Add packaging/windows/assets/splash.mp4 for the desktop intro video."
}

if (Test-Path "$Root\scheduler-ui\package.json") {
    Push-Location "$Root\scheduler-ui"
    if (Test-Path "package-lock.json") {
        npm ci
    } else {
        npm install
    }
    if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
    # Use Vite directly so CI/local builds do not depend on tsc being on PATH.
    node node_modules/vite/bin/vite.js build
    if ($LASTEXITCODE -ne 0) { throw "React UI build failed." }
    if (-not (Test-Path "dist\index.html")) {
        throw "React UI build did not produce dist/index.html."
    }
    Write-Host "React UI built: dist/index.html"
    Pop-Location
} else {
    throw "scheduler-ui/package.json not found; cannot build desktop app."
}

if (Test-Path "$Root\config\april_2026.yaml") {
    Write-Host "Writing content-catalog.json into scheduler-ui/dist for desktop bundle..."
    python -m binge_schedule.cli catalog -c "$Root\config\april_2026.yaml" -o "$Root\scheduler-ui\dist\content-catalog.json"
}

$args = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "ScheduleBuilder",
    "--add-data", "binge_schedule;binge_schedule",
    "--add-data", "config;config",
    "--add-data", "data;data",
    "--add-data", "scheduler-ui\dist;scheduler-ui\dist",
    "--hidden-import", "binge_schedule.api",
    "--hidden-import", "binge_schedule.content_import",
    "--hidden-import", "binge_schedule.content_import_wizard",
    "--hidden-import", "binge_schedule.runtime_paths",
    "--hidden-import", "multipart",
    "--hidden-import", "fastapi",
    "--hidden-import", "uvicorn",
    "--hidden-import", "webview",
    "--hidden-import", "binge_schedule.desktop_window",
    "--collect-submodules", "webview",
    "--hidden-import", "starlette",
    "--hidden-import", "pydantic",
    "--collect-all", "pandas",
    "--collect-all", "openpyxl",
    "desktop_launcher.py"
)

if (Test-Path $iconIco) {
    $args += @("--icon", "packaging\windows\ScheduleBuilder.ico")
}

if (Test-Path "$Root\cloud") {
    $args += @("--add-data", "cloud;cloud")
}

python -m PyInstaller @args

$distApp = "$Root\dist\ScheduleBuilder"
$bundledReact = "$distApp\_internal\scheduler-ui\dist\index.html"
if (-not (Test-Path $bundledReact)) {
    throw "PyInstaller bundle is missing React UI at $bundledReact"
}
Write-Host "Verified bundled React UI: $bundledReact"
if (Test-Path $iconIco) {
    Copy-Item $iconIco $distApp -Force
    Write-Host "Copied ScheduleBuilder.ico for shortcuts and shell icon refresh."
}
if ($Demo) {
    $demoSaved = "$Root\packaging\demo_assets\saved_schedules"
    if (Test-Path $demoSaved) {
        $target = "$distApp\saved_schedules"
        if (Test-Path $target) { Remove-Item $target -Recurse -Force }
        Copy-Item $demoSaved $distApp -Recurse -Force
        Write-Host "Copied demo saved_schedules into desktop bundle."
    } else {
        Write-Warning "Demo assets missing; run prepare_demo_bundle.py first."
    }
}

Write-Host ""
Write-Host "Desktop bundle created at: $distApp"
if ($Demo) {
    Write-Host "Demo install includes station TEST week at saved_schedules/test/2026-05-19_21-33-48"
}
