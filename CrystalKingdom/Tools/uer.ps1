# Wrapper: run a Python file inside the running CrystalKingdom editor.
# usage: & Tools\uer.ps1 Scripts\Unreal\ck_import.py kind=tex
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
$root = Split-Path -Parent $PSScriptRoot
$script = $args[0]
if ($script -ne "-c" -and -not [IO.Path]::IsPathRooted($script)) { $script = Join-Path $root $script }
$rest = @()
if ($args.Count -gt 1) { $rest = $args[1..($args.Count - 1)] }
& $py -I (Join-Path $PSScriptRoot "ue_remote.py") $script @rest
exit $LASTEXITCODE
