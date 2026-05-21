param(
    [Parameter(Mandatory = $true)]
    [string]$AppDir
)

$ErrorActionPreference = "Stop"

# Python 3.9+ needs these UCRT apiset forwarders. Some PCs (older Win10, no updates)
# do not resolve them unless they sit next to python3*.dll in the bundle.
$apiSets = @(
    "api-ms-win-core-path-l1-1-0.dll",
    "api-ms-win-core-path-l1-1-1.dll"
)

$targets = @($AppDir)
$internal = Join-Path $AppDir "_internal"
if (Test-Path $internal) {
    $targets += $internal
}

foreach ($target in $targets) {
    foreach ($dll in $apiSets) {
        $src = Join-Path $env:SystemRoot "System32\$dll"
        if (-not (Test-Path $src)) {
            Write-Warning "System apiset not found: $src"
            continue
        }
        Copy-Item $src (Join-Path $target $dll) -Force
        Write-Host "Bundled runtime DLL: $dll -> $target"
    }
}
