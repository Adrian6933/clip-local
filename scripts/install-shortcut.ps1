$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$desktopPath = [Environment]::GetFolderPath('Desktop')
$iconPath = Join-Path $projectRoot 'public\clippa-sharp.ico'
Add-Type -AssemblyName System.Drawing
$images = @()
foreach ($size in @(16,20,24,32,40,48,64,128,256)) {
    $bitmap = New-Object System.Drawing.Bitmap $size,$size
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $accent = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#C4F577'))
    $dark = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#172015'))
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $radius = [int][Math]::Round($size / 4)
    $shape = New-Object System.Drawing.Drawing2D.GraphicsPath
    $shape.AddArc(0,0,$radius,$radius,180,90)
    $shape.AddArc(($size-$radius),0,$radius,$radius,270,90)
    $shape.AddArc(($size-$radius),($size-$radius),$radius,$radius,0,90)
    $shape.AddArc(0,($size-$radius),$radius,$radius,90,90)
    $shape.CloseFigure()
    $graphics.FillPath($accent,$shape)
    # Draw at each native resolution, with pixel-aligned edges and no rotation.
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::None
    $left = [int][Math]::Round($size * .25)
    $top = [int][Math]::Round($size * .25)
    $width = $size - 2*$left
    $height = [int][Math]::Round($size * .5)
    $line = [Math]::Max(1,[int][Math]::Round($size / 16))
    $graphics.FillRectangle($dark,$left,$top,$width,$height)
    $graphics.FillRectangle($accent,($left+$line),($top+3*$line),($width-2*$line),($height-4*$line))
    $graphics.FillRectangle($accent,($left+2*$line),$top,$line,$line)
    $graphics.FillRectangle($accent,($left+5*$line),$top,$line,$line)
    if ($size -ge 32) {
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $points = [System.Drawing.Point[]]@([System.Drawing.Point]::new([int]($size*.44),[int]($size*.48)),[System.Drawing.Point]::new([int]($size*.62),[int]($size*.58)),[System.Drawing.Point]::new([int]($size*.44),[int]($size*.68)))
        $graphics.FillPolygon($dark,$points)
    }
    $stream = New-Object System.IO.MemoryStream
    $bitmap.Save($stream,[System.Drawing.Imaging.ImageFormat]::Png)
    $images += @{Size=$size;Bytes=$stream.ToArray()}
    $stream.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
    $accent.Dispose(); $dark.Dispose(); $shape.Dispose()
}
$file = [System.IO.File]::Create($iconPath)
$writer = New-Object System.IO.BinaryWriter $file
$writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$images.Count)
$offset = 6 + 16*$images.Count
foreach ($entry in $images) {
    $dimension = if ($entry.Size -eq 256) {0} else {$entry.Size}
    $writer.Write([byte]$dimension); $writer.Write([byte]$dimension)
    $writer.Write([byte]0); $writer.Write([byte]0)
    $writer.Write([uint16]1); $writer.Write([uint16]32)
    $writer.Write([uint32]$entry.Bytes.Length); $writer.Write([uint32]$offset)
    $offset += $entry.Bytes.Length
}
foreach ($entry in $images) { $writer.Write([byte[]]$entry.Bytes) }
$writer.Dispose()
$shellObject = New-Object -ComObject WScript.Shell
foreach ($entry in @(@{Name='Clippa';Args='';Description='Abrir Clippa, tu estudio local de clips'},@{Name='Detener Clippa';Args=' --stop';Description='Detener el motor local de Clippa; interrumpe los trabajos en curso'})) {
    $shortcutPath = Join-Path $desktopPath ($entry.Name + '.lnk')
    if (Test-Path -LiteralPath $shortcutPath) {
        $existing = $shellObject.CreateShortcut($shortcutPath)
        if ($existing.Arguments -notlike '*desktop-launch.py*') { throw "Ya existe un acceso diferente: $shortcutPath" }
    }
    $shortcut = $shellObject.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
    $shortcut.Arguments = '"' + (Join-Path $PSScriptRoot 'desktop-launch.py') + '"' + $entry.Args
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.IconLocation = $iconPath + ',0'
    $shortcut.Description = $entry.Description
    $shortcut.WindowStyle = 7
    $shortcut.Save()
    Write-Output "Creado: $shortcutPath"
}
