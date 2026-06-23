param(
    [switch]$Clean,
    [switch]$Demo
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root

$versionFile = "$Root\packaging\windows\app_version.txt"
if (-not (Test-Path $versionFile)) {
    throw "Missing version file: $versionFile"
}
$AppVersion = (Get-Content $versionFile -Raw).Trim()
if (-not $AppVersion) {
    throw "packaging/windows/app_version.txt is empty."
}
Write-Host "Desktop app version: $AppVersion"
"#define AppVersion `"$AppVersion`"" | Set-Content -Encoding ascii "$Root\packaging\windows\app_version.inc"

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
    $uiJs = Get-ChildItem "dist/assets/*.js" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $uiJs) { throw "React UI build did not produce dist/assets/*.js." }
    if (-not (Select-String -Path $uiJs.FullName -Pattern "Title start time" -Quiet)) {
        throw "React UI bundle is missing the movie Title start time control."
    }
    if (Select-String -Path $uiJs.FullName -Pattern "Some movies fit by runtime but need a title-start timing note" -Quiet) {
        throw "React UI bundle still contains the removed movie timing-note sidebar text."
    }
    Write-Host "React UI built: dist/index.html (verified movie title-start UI)"
    Pop-Location
} else {
    throw "scheduler-ui/package.json not found; cannot build desktop app."
}

Write-Host "Writing empty content-catalog.json (fresh import after install)..."
$emptyCatalog = @'
{
  "schema_version": 1,
  "row_count": 0,
  "rows": []
}
'@
$emptyCatalog | Set-Content -Encoding utf8 "$Root\scheduler-ui\dist\content-catalog.json"

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
& "$Root\scripts\bundle_desktop_runtime.ps1" -AppDir $distApp

& "$Root\scripts\fetch_vc_redist.ps1"
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
$AppVersion | Set-Content -Encoding ascii "$distApp\VERSION.txt"
Write-Host "Wrote VERSION.txt ($AppVersion)"
$indexHtml = "$Root\scheduler-ui\dist\index.html"
if (Test-Path $indexHtml) {
    $html = Get-Content $indexHtml -Raw
    $html = $html -replace '<title>Schedule Builder</title>', "<title>Schedule Builder $AppVersion</title>"
    if ($html -notmatch 'schedule-builder-version') {
        $html = $html -replace '</head>', "    <meta name=`"schedule-builder-version`" content=`"$AppVersion`" />`n  </head>"
    } else {
        $html = $html -replace 'content="[^"]*"(\s*/>\s*<!-- schedule-builder-version -->|"\s*/>)', "content=`"$AppVersion`"`" />"
    }
    Set-Content -Encoding utf8 $indexHtml $html
    Write-Host "Stamped scheduler-ui/dist/index.html with version $AppVersion"
}
if ($Demo) {
    Write-Host "Demo install includes station TEST week at saved_schedules/test/2026-05-19_21-33-48"
}
