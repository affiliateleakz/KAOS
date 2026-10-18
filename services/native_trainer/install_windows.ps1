param([Parameter(Mandatory=$true)][string]$ExtensionId)
$ErrorActionPreference='Stop'
if($ExtensionId -notmatch '^[a-p]{32}$'){throw 'Invalid Chrome extension ID. Get it from chrome://extensions.'}
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$python=(Get-Command py -ErrorAction SilentlyContinue)
if(-not $python){throw 'Python launcher py.exe not found. Install Python 3.10+ first.'}
& py -3 -m pip install --user numpy xgboost
if($LASTEXITCODE -ne 0){throw 'Python dependency install failed.'}
$launcher=Join-Path $here 'run_host.bat'
$launcherContent="@echo off`r`npy -3 `"$here\host.py`"`r`n"
[IO.File]::WriteAllText($launcher,$launcherContent,[Text.Encoding]::ASCII)
$manifest=@{name='com.kaos.aidata';description='KAOS XGBoost Native Trainer';path=$launcher;type='stdio';allowed_origins=@("chrome-extension://$ExtensionId/")} | ConvertTo-Json -Depth 5
$manifestPath=Join-Path $here 'com.kaos.aidata.json'
[IO.File]::WriteAllText($manifestPath,$manifest,[Text.Encoding]::UTF8)
$reg='HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.kaos.aidata'
New-Item -Path $reg -Force | Out-Null
Set-Item -Path $reg -Value $manifestPath
Write-Host "KAOS trainer registered for Chrome extension $ExtensionId. Restart Chrome."
