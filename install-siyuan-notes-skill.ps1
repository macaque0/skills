param(
    [string]$Source = (Join-Path $PSScriptRoot "skills\siyuan-notes"),
    [string]$Destination = (Join-Path $env:USERPROFILE ".codex\skills\siyuan-notes"),
    [switch]$Force,
    [switch]$Test
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Skill source not found: $Source"
}

$skillFile = Join-Path $Source "SKILL.md"
if (-not (Test-Path -LiteralPath $skillFile)) {
    throw "SKILL.md not found in source: $Source"
}

if ((Test-Path -LiteralPath $Destination) -and -not $Force) {
    throw "Destination already exists: $Destination. Re-run with -Force to replace it."
}

$parent = Split-Path -Parent $Destination
New-Item -ItemType Directory -Force -Path $parent | Out-Null

if (Test-Path -LiteralPath $Destination) {
    $resolvedDestination = Resolve-Path -LiteralPath $Destination
    $skillsRoot = Resolve-Path -LiteralPath $parent
    if (-not $resolvedDestination.Path.StartsWith($skillsRoot.Path, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove outside skills root: $($resolvedDestination.Path)"
    }
    Write-Step "Removing existing install"
    Remove-Item -LiteralPath $resolvedDestination.Path -Recurse -Force
}

Write-Step "Installing siyuan-notes skill"
Copy-Item -LiteralPath $Source -Destination $Destination -Recurse

Write-Step "Installed to $Destination"

if ($Test) {
    $script = Join-Path $Destination "scripts\siyuan_api.py"
    if (-not (Test-Path -LiteralPath $script)) {
        throw "Installed helper script not found: $script"
    }

    Write-Step "Checking helper script"
    python $script --help | Out-Null

    Write-Step "Checking SiYuan API"
    if (-not $env:SIYUAN_TOKEN) {
        Write-Warning "SIYUAN_TOKEN is not set in this shell. API calls may fail if SiYuan requires authentication."
    }
    python $script version
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Restart Codex so the new skill list refreshes."
Write-Host "2. Invoke it with: `$siyuan-notes 把下面内容整理并写入思源..."
Write-Host "3. Set SIYUAN_TOKEN in your user environment if API writes fail."
