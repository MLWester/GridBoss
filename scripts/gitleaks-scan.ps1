Param(
    [string]$Source = "."
)

$ErrorActionPreference = "Stop"

function Run-GitleaksBinary {
    param([string]$SourcePath)
    & gitleaks detect --source $SourcePath --no-banner --redact
}

function Run-GitleaksDocker {
    param([string]$SourcePath)
    & docker run --rm `
        -v "$((Get-Location).Path):/repo" `
        -w /repo `
        zricethezav/gitleaks:latest `
        detect --source $SourcePath --no-banner --redact
}

if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
    Run-GitleaksBinary -SourcePath $Source
    exit 0
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Run-GitleaksDocker -SourcePath $Source
    exit 0
}

Write-Error "gitleaks is not installed and Docker is unavailable. Install one of them to run the scan."
