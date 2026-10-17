$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

try {
    Set-Location -LiteralPath $projectRoot

    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath (Join-Path $projectRoot ".venv")) {
        if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            throw "The .venv folder exists but its Python interpreter is missing: $venvPython"
        }
        $python = $venvPython
    }
    else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand) {
            throw "Python was not found. Create .venv or install Python and add it to PATH."
        }
        $python = $pythonCommand.Source
    }

    $dependencyCheck = "import importlib.util, sys; required = ['PyInstaller', 'PIL', 'requests', 'sv_ttk', 'tkinterdnd2']; missing = [name for name in required if importlib.util.find_spec(name) is None]; print(', '.join(missing)); sys.exit(bool(missing))"
    $missingDependencies = @(& $python -c $dependencyCheck)
    if ($LASTEXITCODE -ne 0) {
        $missingList = ($missingDependencies -join ", ").Trim()
        if (-not $missingList) {
            $missingList = "PyInstaller, Pillow, requests, sv-ttk, tkinterdnd2"
        }
        throw "Missing build dependencies ($missingList). From the project root, install them with: `"$python`" -m pip install -r packaging\requirements-build.txt"
    }

    $versionOutput = & $python -c "from moviq import __version__; print(__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read the project version from moviq.__version__."
    }
    $version = ($versionOutput | Out-String).Trim()
    if ($version -notmatch "^[0-9A-Za-z][0-9A-Za-z.+-]*$") {
        throw "The project version is empty or invalid: '$version'."
    }

    $releaseDistPath = Join-Path $projectRoot "release\dist"
    $releaseBuildPath = Join-Path $projectRoot "release\build"
    $executablePath = Join-Path $releaseDistPath "Moviq-$version.exe"
    if (Test-Path -LiteralPath $executablePath -PathType Leaf) {
        try {
            $outputFile = [System.IO.File]::Open(
                $executablePath,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            $outputFile.Dispose()
        }
        catch [System.IO.IOException] {
            throw "Cannot replace $executablePath because it is in use. Close all running Moviq windows and run the build again."
        }
        catch [System.UnauthorizedAccessException] {
            throw "Cannot replace $executablePath because access was denied. Close all running Moviq windows and check the file permissions."
        }
    }

    New-Item -ItemType Directory -Path $releaseBuildPath, $releaseDistPath -Force | Out-Null

    $entryScript = Join-Path $PSScriptRoot "run_moviq.py"
    if (-not (Test-Path -LiteralPath $entryScript -PathType Leaf)) {
        throw "The PyInstaller entry script is missing: $entryScript"
    }

    $specPath = Join-Path $PSScriptRoot "moviq.spec"
    if (-not (Test-Path -LiteralPath $specPath -PathType Leaf)) {
        throw "The PyInstaller spec is missing: $specPath"
    }

    & $python -m PyInstaller --noconfirm --clean `
        --distpath $releaseDistPath `
        --workpath $releaseBuildPath `
        $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
        throw "PyInstaller completed but the portable executable was not created."
    }

    Write-Host "Portable executable created: $executablePath"
}
catch {
    [Console]::Error.WriteLine("Build failed: $($_.Exception.Message)")
    exit 1
}
