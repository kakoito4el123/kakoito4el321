param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$Notes
)

$ErrorActionPreference = "Stop"
Set-Content -Path VERSION -Value $Version -NoNewline
git add VERSION index.html main.py main.spec updater.py tools scripts .github
git commit -m "Release v$Version"
git tag "v$Version"
git push origin HEAD --follow-tags
Write-Host "Релиз отправлен. GitHub Actions соберёт ZIP и опубликует его автоматически."
