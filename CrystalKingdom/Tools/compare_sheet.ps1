# Side-by-side sheet: columns = images, row 1 = full frame, row 2 = same-region crop (relative coords).
# usage: & Tools\compare_sheet.ps1 -Out Screenshots\x.png -Images a.png,b.png,c.png -Labels "A","B","C" [-Crop 0.33,0.62,0.36,0.36]
param([string]$Out, [string[]]$Images, [string[]]$Labels, [double[]]$Crop = @(0.33, 0.62, 0.36, 0.36), [int]$CellW = 640, [string]$CropSuffix = " (crop)")
Add-Type -AssemblyName System.Drawing
$cellH = [int]($CellW * 9 / 16)
$labelH = 34
$n = $Images.Count
$bmp = New-Object System.Drawing.Bitmap ($CellW * $n), (($cellH + $labelH) * 2)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.Clear([System.Drawing.Color]::FromArgb(20, 22, 26))
$font = New-Object System.Drawing.Font "Malgun Gothic", 13, ([System.Drawing.FontStyle]::Bold)
$brush = [System.Drawing.Brushes]::White
for ($i = 0; $i -lt $n; $i++) {
  $img = [System.Drawing.Image]::FromFile((Resolve-Path $Images[$i]).Path)
  $x = $i * $CellW
  $g.DrawImage($img, (New-Object System.Drawing.Rectangle $x, $labelH, $CellW, $cellH))
  $src = New-Object System.Drawing.RectangleF ($img.Width * $Crop[0]), ($img.Height * $Crop[1]), ($img.Width * $Crop[2]), ($img.Height * $Crop[3])
  $dst = New-Object System.Drawing.RectangleF $x, ($labelH * 2 + $cellH), $CellW, $cellH
  $g.DrawImage($img, $dst, $src, [System.Drawing.GraphicsUnit]::Pixel)
  $g.DrawString($Labels[$i], $font, $brush, ($x + 10), 6)
  $g.DrawString($Labels[$i] + $CropSuffix, $font, $brush, ($x + 10), ($labelH + $cellH + 6))
  $img.Dispose()
}
$g.Dispose()
$bmp.Save((Join-Path (Get-Location) $Out), [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
"saved $Out"
