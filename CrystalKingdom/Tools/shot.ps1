# Render a CineCamera view through the real editor viewport (Lumen GI/reflections included).
# usage: & Tools\shot.ps1 <CameraLabel> <OutName> [settleSeconds]
param([string]$Cam = "CAM_Reference", [string]$Name = "shot", [int]$Settle = 12)
$root = Split-Path -Parent $PSScriptRoot
$dir = Join-Path $root "Saved\Screenshots\WindowsEditor"
New-Item -ItemType Directory -Force $dir | Out-Null
$before = @(Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue | ForEach-Object FullName)
& (Join-Path $PSScriptRoot "uer.ps1") Scripts\Unreal\ck_shot.py cam=$Cam phase=pilot | Out-Null
for ($i = 0; $i -lt $Settle; $i++) {
  Start-Sleep 1
  & (Join-Path $PSScriptRoot "uer.ps1") -c "import unreal; unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()" | Out-Null
}
& (Join-Path $PSScriptRoot "uer.ps1") -c "import unreal; w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(); unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1920x1080'); unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()" | Out-Null
$new = $null
for ($i = 0; $i -lt 90 -and -not $new; $i++) {
  Start-Sleep 1
  & (Join-Path $PSScriptRoot "uer.ps1") -c "import unreal; unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()" | Out-Null
  $new = Get-ChildItem $dir -Filter *.png | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1
}
if (-not $new) { Write-Output "NO SCREENSHOT"; exit 1 }
Start-Sleep 2
$dst = Join-Path $root ("Screenshots\" + $Name + ".png")
New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
Move-Item $new.FullName $dst -Force
Write-Output "saved $dst"
