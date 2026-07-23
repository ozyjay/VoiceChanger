param(
    [string] $IsccPath
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

Set-Location (Join-Path $PSScriptRoot "..")

function Invoke-CheckedNative {
    param(
        [scriptblock] $Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Find-InnoCompiler {
    if ($IsccPath) {
        if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
            throw "Inno Setup compiler not found at: $IsccPath"
        }
        return (Resolve-Path -LiteralPath $IsccPath).Path
    }

    $isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($isccCommand) {
        return $isccCommand.Source
    }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    throw "Inno Setup 6 is required. Install it with: winget install --id JRSoftware.InnoSetup --exact"
}

$projectText = Get-Content -Raw -LiteralPath "pyproject.toml"
$versionMatch = [regex]::Match($projectText, '(?m)^version\s*=\s*"(?<version>[^"]+)"')
if (-not $versionMatch.Success) {
    throw "Could not read the project version from pyproject.toml."
}
$appVersion = $versionMatch.Groups["version"].Value

Invoke-CheckedNative { poetry install }
Invoke-CheckedNative { poetry run pyinstaller --noconfirm --clean "VoiceChanger.spec" }

$compilerPath = Find-InnoCompiler
Invoke-CheckedNative { & $compilerPath "/DAppVersion=$appVersion" "installer\VoiceChanger.iss" }

$installerPath = Resolve-Path -LiteralPath "dist\installer\VoiceChanger-Setup-$appVersion.exe"
Write-Host "Installer created: $installerPath"
