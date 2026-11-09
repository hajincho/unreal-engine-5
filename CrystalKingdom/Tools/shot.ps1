# Render a CineCamera view through the real editor viewport (Lumen GI/reflections included).
# usage: & Tools\shot.ps1 <CameraLabel> <OutName> [settleSeconds] [timeoutSeconds]
# - A minimized editor never draws its viewport, so the window is restored first.
# - A new shot is detected by write time (HighResShot reuses file names), not by name.
param([string]$Cam = "CAM_Reference", [string]$Name = "shot", [int]$Settle = 12, [int]$Timeout = 300)
$root = Split-Path -Parent $PSScriptRoot
$dir = Join-Path $root "Saved\Screenshots\WindowsEditor"
New-Item -ItemType Directory -Force $dir | Out-Null
$uer = Join-Path $PSScriptRoot "uer.ps1"
$kick = "import unreal; unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()"

Add-Type -ErrorAction SilentlyContinue @"
using System; using System.Runtime.InteropServices;
public class CKWin {
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
}
"@
$ed = Get-Process UnrealEditor -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $ed) { Write-Output "EDITOR NOT RUNNING"; exit 2 }
if ([CKWin]::IsIconic($ed.MainWindowHandle)) {
  [CKWin]::ShowWindow($ed.MainWindowHandle, 9) | Out-Null   # SW_RESTORE
  Write-Output "editor window restored (was minimized)"
  Start-Sleep 3
}

& $uer Scripts\Unreal\ck_shot.py cam=$Cam phase=pilot | Out-Null
for ($i = 0; $i -lt $Settle; $i++) { Start-Sleep 1; & $uer -c $kick | Out-Null }

$start = Get-Date
& $uer -c "import unreal; w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(); unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1920x1080'); unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()" | Out-Null
$new = $null
for ($i = 0; $i -lt $Timeout -and -not $new; $i++) {
  Start-Sleep 1
  & $uer -c $kick | Out-Null
  $new = Get-ChildItem $dir -Filter *.png | Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($i -eq 60 -and -not $new -and [CKWin]::IsIconic($ed.MainWindowHandle)) {
    [CKWin]::ShowWindow($ed.MainWindowHandle, 9) | Out-Null   # minimized again mid-render
  }
}
if (-not $new) { Write-Output "NO SCREENSHOT after ${Timeout}s (shader compile still running?)"; exit 1 }
Start-Sleep 2   # let the writer finish
$dst = Join-Path $root ("Screenshots\" + $Name + ".png")
New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
Move-Item $new.FullName $dst -Force
Write-Output "saved $dst"
