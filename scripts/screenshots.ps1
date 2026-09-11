# Capture dashboard pages with headless Microsoft Edge.
#   powershell -File scripts\screenshots.ps1 -Base http://localhost:8010 -Out frontend\screenshots
param(
  [string]$Base = "http://localhost:8000",
  [string]$Out = "frontend\screenshots",
  [string[]]$Only = @()
)
$Only = @($Only | ForEach-Object { $_ -split "," } | Where-Object { $_ })   # -File passes "a,b" as one string
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "C:\Program Files\Microsoft\Edge\Application\msedge.exe" }
New-Item -ItemType Directory -Force $Out | Out-Null
$pages = @(
  @{ name = "overview";        path = "/";                          w = 1440; h = 1500 },
  @{ name = "monitor";         path = "/monitor?feed=alerts";       w = 1440; h = 1700 },
  @{ name = "tester";          path = "/tester?preset=night";       w = 1440; h = 1900 },
  @{ name = "scenarios";       path = "/scenarios?run=card_testing"; w = 1440; h = 2000 },
  @{ name = "cases";           path = "/cases";                     w = 1440; h = 1200 },
  @{ name = "results";         path = "/results";                   w = 1440; h = 1800 },
  @{ name = "results_policy";  path = "/results?tab=policy";        w = 1440; h = 1500 },
  @{ name = "results_protocol"; path = "/results?tab=protocol";     w = 1440; h = 1700 },
  @{ name = "report";          path = "/report";                    w = 1440; h = 1900 },
  @{ name = "about";           path = "/about";                     w = 1440; h = 2100 },
  # headless Edge will not lay a page out narrower than 500 px, so "mobile" is captured at 500
  @{ name = "mobile_overview"; path = "/";                          w = 500;  h = 1800 },
  @{ name = "mobile_tester";   path = "/tester?preset=night";       w = 500;  h = 2400 }
)
foreach ($p in $pages) {
  if ($Only.Count -and ($Only -notcontains $p.name)) { continue }
  $file = Join-Path (Resolve-Path $Out) "$($p.name).png"
  & $edge --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 `
    "--window-size=$($p.w),$($p.h)" --virtual-time-budget=15000 "--screenshot=$file" "$Base$($p.path)" 2>$null | Out-Null
  Write-Output "$($p.name): $file"
}
