# Merch Forge · generation image validation (dependency-free)
function Read-ForgeUInt32BE([byte[]]$Bytes,[int]$Offset) {
    if($null -eq $Bytes -or $Offset -lt 0 -or ($Offset+4) -gt $Bytes.Length){throw 'PNG integer read is outside the byte array.'}
    [byte[]]$x=@($Bytes[$Offset+3],$Bytes[$Offset+2],$Bytes[$Offset+1],$Bytes[$Offset]);return [BitConverter]::ToUInt32($x,0)
}
function Get-ForgePngMetadata([byte[]]$Bytes) {
    $bad=[pscustomobject]@{valid=$false;width=0;height=0;has_alpha=$false;color_type=-1;reason='invalid_png'}
    if($null-eq$Bytes -or $Bytes.Length -lt 33){return $bad}
    [byte[]]$sig=@(137,80,78,71,13,10,26,10);for($i=0;$i-lt8;$i++){if($Bytes[$i]-ne$sig[$i]){return $bad}}
    try{$ihdrLen=Read-ForgeUInt32BE $Bytes 8}catch{return $bad};if($ihdrLen-ne13){return $bad}
    $type=[Text.Encoding]::ASCII.GetString($Bytes,12,4);if($type-ne'IHDR'){return $bad}
    try{$w=[int](Read-ForgeUInt32BE $Bytes 16);$h=[int](Read-ForgeUInt32BE $Bytes 20)}catch{return $bad};if($w-lt1-or$h-lt1){return $bad}
    $ct=[int]$Bytes[25];$alpha=($ct-eq4-or$ct-eq6);$off=8
    while(($off+12)-le$Bytes.Length){
        try{$len=[int64](Read-ForgeUInt32BE $Bytes $off)}catch{break};if($len-lt0-or$len-gt2147483647){break};$chunkEnd=$off+12+$len;if($chunkEnd-gt$Bytes.Length){break};$chunk=[Text.Encoding]::ASCII.GetString($Bytes,$off+4,4);if($chunk-eq'tRNS'){$alpha=$true};if($chunk-eq'IEND'){break};$off=[int]$chunkEnd
    }
    return [pscustomobject]@{valid=$true;width=$w;height=$h;has_alpha=$alpha;color_type=$ct;reason=if($alpha){''}else{'png_has_no_alpha_channel'}}
}
function Test-ForgeGenerationPngBytes([byte[]]$Bytes,[int]$ExpectedWidth=0,[int]$ExpectedHeight=0) {
    $m=Get-ForgePngMetadata $Bytes;if(-not [bool]$m.valid){return [pscustomobject]@{ok=$false;metadata=$m;reason='invalid_png'}}
    if(-not [bool]$m.has_alpha){return [pscustomobject]@{ok=$false;metadata=$m;reason='transparent_png_required'}}
    if($ExpectedWidth -gt 0 -and [int]$m.width -ne $ExpectedWidth){return [pscustomobject]@{ok=$false;metadata=$m;reason='wrong_width'}}
    if($ExpectedHeight -gt 0 -and [int]$m.height -ne $ExpectedHeight){return [pscustomobject]@{ok=$false;metadata=$m;reason='wrong_height'}}
    try {
        Add-Type -AssemblyName System.Drawing -ErrorAction Stop
        $ms=New-Object IO.MemoryStream -ArgumentList (,$Bytes)
        try {$img=[Drawing.Image]::FromStream($ms,$true,$true);try{$nativeAlpha=[Drawing.Image]::IsAlphaPixelFormat($img.PixelFormat);if($ExpectedWidth -gt 0 -and $img.Width -ne $ExpectedWidth){return [pscustomobject]@{ok=$false;metadata=$m;reason='native_wrong_width'}};if($ExpectedHeight -gt 0 -and $img.Height -ne $ExpectedHeight){return [pscustomobject]@{ok=$false;metadata=$m;reason='native_wrong_height'}};if(-not $nativeAlpha){return [pscustomobject]@{ok=$false;metadata=$m;reason='native_alpha_channel_missing'}};$bmp=New-Object Drawing.Bitmap $img;try{$samples=@();$steps=8;for($i=0;$i-lt$steps;$i++){$x=[int][Math]::Round(($bmp.Width-1)*$i/($steps-1));$y=[int][Math]::Round(($bmp.Height-1)*$i/($steps-1));$samples+=,@($x,0);$samples+=,@($x,($bmp.Height-1));$samples+=,@(0,$y);$samples+=,@(($bmp.Width-1),$y)};$opaque=@();foreach($pt in $samples){$a=[int]$bmp.GetPixel([int]$pt[0],[int]$pt[1]).A;if($a-gt8){$opaque+=(''+[int]$pt[0]+','+[int]$pt[1]+':'+$a)}};if($opaque.Count-gt0){return [pscustomobject]@{ok=$false;metadata=$m;reason=('transparent_canvas_border_required: '+($opaque -join ';'))}}}finally{$bmp.Dispose()}}finally{$img.Dispose()}}finally{$ms.Dispose()}
    } catch {return [pscustomobject]@{ok=$false;metadata=$m;reason=('native_png_decode_failed: '+$_.Exception.Message)}}
    return [pscustomobject]@{ok=$true;metadata=$m;reason=''}
}
function Test-ForgeGenerationPngFile([string]$Path,[int]$ExpectedWidth=0,[int]$ExpectedHeight=0) {
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){return [pscustomobject]@{ok=$false;metadata=$null;reason='file_missing'}}
    try{[byte[]]$b=[IO.File]::ReadAllBytes($Path);return Test-ForgeGenerationPngBytes $b $ExpectedWidth $ExpectedHeight}catch{return [pscustomobject]@{ok=$false;metadata=$null;reason=$_.Exception.Message}}
}
