# Standalone (-game) performance capture with the CSV profiler.
# usage: & Tools\perf.ps1 <ResX> <ResY> <Label> [Seconds] [ScreenPct]
# The open editor is minimized while measuring: a visible editor viewport renders Lumen on the same GPU
# and cut the standalone result from ~60 fps to ~4 fps. It is restored afterwards.
param([int]$ResX = 1920, [int]$ResY = 1080, [string]$Label = "1080p", [int]$Seconds = 150, [int]$ScreenPct = 100, [string]$Extra = "")
$root = Split-Path -Parent $PSScriptRoot
$csvDir = Join-Path $root "Saved\Profiling\CSV"
$before = @(Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | ForEach-Object FullName)

Add-Type -ErrorAction SilentlyContinue @"
using System; using System.Runtime.InteropServices;
public class CKWinP { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd); }
"@
$ed = Get-Process UnrealEditor -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($ed) { [CKWinP]::ShowWindow($ed.MainWindowHandle, 6) | Out-Null }   # SW_MINIMIZE

$exe = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproj = Join-Path $root "CrystalKingdom.uproject"
$args = @("`"$uproj`"", "-game", "-windowed", "-ResX=$ResX", "-ResY=$ResY", "-nosplash", "-NoVerifyGC", "-csvGpuStats",
          "-ExecCmds=`"t.MaxFPS 0,r.VSync 0,r.ScreenPercentage $ScreenPct$(if ($Extra) { ',' + $Extra }),CsvProfile Frames=900`"", "-log=Perf_$Label.log")
$p = Start-Process -FilePath $exe -ArgumentList $args -PassThru
Start-Sleep $Seconds
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Start-Sleep 3
if ($ed) { [CKWinP]::ShowWindow($ed.MainWindowHandle, 9) | Out-Null }   # SW_RESTORE
$csv = Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.FullName -and $_.Length -gt 0 } | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $csv) { Write-Output "NO CSV (capture did not finish within ${Seconds}s?)"; exit 1 }
# Import-Csv fails on duplicate column names in newer captures -> python summariser
$py = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
& $py -I (Join-Path $PSScriptRoot "csvstats.py") $csv.FullName $Label 120
