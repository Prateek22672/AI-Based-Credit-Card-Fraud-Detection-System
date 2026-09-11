# Final, clean run on an idle machine (everything sequential, nothing else running).
# The deep-learning baselines (mlp, cnn) keep their earlier accuracy results.
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
& $py -u -m fraudlens.pipeline "benchmark:rules,lr,dt,rf,xgb,lgbm,iforest,hybrid" artifacts latency analysis explain policy scenarios unseen ulb *> "reports\final.log"
& $py -m fraudlens.plots *> "reports\plots.log"
"FINAL DONE" | Out-File "reports\final.done"
