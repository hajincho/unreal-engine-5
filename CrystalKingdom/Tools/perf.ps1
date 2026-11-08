# Standalone (-game) performance capture with the CSV profiler.
# usage: & Tools\perf.ps1 <ResX> <ResY> <Label> [Seconds]
param([int]$ResX = 1920, [int]$ResY = 1080, [string]$Label = "1080p", [int]$Seconds = 100, [int]$ScreenPct = 100)
$root = Split-Path -Parent $PSScriptRoot
$csvDir = Join-Path $root "Saved\Profiling\CSV"
$before = @(Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | ForEach-Object FullName)
$exe = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproj = Join-Path $root "CrystalKingdom.uproject"
$args = @("`"$uproj`"", "-game", "-windowed", "-ResX=$ResX", "-ResY=$ResY", "-nosplash", "-NoVerifyGC", "-csvGpuStats",
          "-ExecCmds=`"t.MaxFPS 0,r.VSync 0,r.ScreenPercentage $ScreenPct,CsvProfile Frames=900`"", "-log=Perf_$Label.log")
$p = Start-Process -FilePath $exe -ArgumentList $args -PassThru
Start-Sleep $Seconds
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Start-Sleep 3
$csv = Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.FullName } | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $csv) { Write-Output "NO CSV"; exit 1 }
$rows = Import-Csv $csv.FullName | Where-Object { $_.FrameTime -and $_.FrameTime -match '^[0-9.]+$' }
$rows = $rows | Select-Object -Skip 120   # drop warm-up frames (shader/Lumen settling)
$ft = $rows | ForEach-Object { [double]$_.FrameTime }
$gpu = $rows | Where-Object { $_.GPUTime -match '^[0-9.]+$' } | ForEach-Object { [double]$_.GPUTime }
$avg = ($ft | Measure-Object -Average).Average
$sorted = $ft | Sort-Object
$p95 = $sorted[[int]([math]::Floor($sorted.Count * 0.95))]
$gavg = if ($gpu) { ($gpu | Measure-Object -Average).Average } else { 0 }
"{0}: frames={1} avg_frame={2:N2} ms ({3:N1} fps)  p95_frame={4:N2} ms  avg_gpu={5:N2} ms  csv={6}" -f $Label, $ft.Count, $avg, (1000 / $avg), $p95, $gavg, $csv.Name
