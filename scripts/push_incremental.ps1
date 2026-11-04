# 网络恢复后运行：分段推送 2658 张图片，避免一次传 200MB 被重置。
# 用法：在项目目录执行  powershell -ExecutionPolicy Bypass -File scripts\push_incremental.ps1
$ErrorActionPreference = "Continue"
$branch = "staged"
$remote = "origin"

$shas = git log --reverse --format="%H" $branch
if (-not $shas) { Write-Host "找不到分支 $branch"; exit 1 }
$i = 0
foreach ($sha in $shas) {
  $i++
  $ref = "refs/heads/progress-$i"
  $ok = $false
  for ($try = 1; $try -le 3; $try++) {
    git push $remote "$sha`:$ref" 2>$null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    Write-Host "第 $i 段失败，重试 $try/3 ..."
    Start-Sleep -Seconds 5
  }
  if (-not $ok) { Write-Host "第 $i 段推送失败，请检查网络/代理后重新运行本脚本"; exit 1 }
  Write-Host "第 $i 段推送成功"
}
git push $remote "$branch`:main"
if ($LASTEXITCODE -ne 0) { Write-Host "最终分支推送失败"; exit 1 }
git branch -D main 2>$null
git branch -m main
git branch -u $remote/main
Write-Host "完成：https://github.com/zhouhuaiqin/-"
