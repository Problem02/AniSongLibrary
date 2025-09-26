# run_sync.ps1
$ErrorActionPreference = "Stop"
$repo = "C:\Users\bryan\git\AniSongLibrary"
$log  = Join-Path $repo "backend\catalog\logs\sync_$(Get-Date -Format 'yyyy-MM-dd').log"

New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
Set-Location $repo

# activate venv
& "$repo\.venv\Scripts\Activate.ps1"

# force UTF-8 mode for Python
$env:PYTHONUTF8 = "1"

# run the sync, append output
python backend\catalog\scripts\sync_amq_master_list.py `
  --api http://localhost:8001 `
  --target-rps 10 | Tee-Object -FilePath $log -Append
