# Push local commits in small segments to avoid large-upload resets.
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\push_incremental.ps1
$ErrorActionPreference = "Continue"
$branch = "staged"
$remote = "origin"

$shas = git log --reverse --format="%H" $branch
if (-not $shas) { Write-Host "branch not found: $branch"; exit 1 }
$i = 0
foreach ($sha in $shas) {
  $i++
  $ref = "refs/heads/progress-$i"
  $ok = $false
  for ($try = 1; $try -le 3; $try++) {
    git push $remote ($sha + ":" + $ref) 2>$null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    Write-Host "segment $i failed, retry $try/3 ..."
    Start-Sleep -Seconds 5
  }
  if (-not $ok) { Write-Host "segment $i failed; check network/VPN and run again"; exit 1 }
  Write-Host "segment $i pushed"
}
git push $remote ($branch + ":main")
if ($LASTEXITCODE -ne 0) { Write-Host "final branch push failed"; exit 1 }
git branch -D main 2>$null
git branch -m main
git branch -u $remote/main
Write-Host "done: https://github.com/zhouhuaiqin/-"
