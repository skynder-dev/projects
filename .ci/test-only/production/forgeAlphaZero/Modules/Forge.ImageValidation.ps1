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

function Test-ForgePrintPngBytes([byte[]]$Bytes,[int]$Width,[int]$Height) {
    $base=Test-ForgeGenerationPngBytes $Bytes $Width $Height
    if(-not $base.ok){return $base}
    # Decode actual pixels: an alpha channel and a clear border do not prove artwork exists.
    $ms=New-Object IO.MemoryStream -ArgumentList (,$Bytes)
    try{$img=[Drawing.Image]::FromStream($ms,$true,$true);try{$bmp=New-Object Drawing.Bitmap $img
        try{
            $rect=New-Object Drawing.Rectangle 0,0,$bmp.Width,$bmp.Height
            $locked=$bmp.LockBits($rect,[Drawing.Imaging.ImageLockMode]::ReadOnly,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
            try{[byte[]]$row=New-Object byte[] ($bmp.Width*4);$content=$false
                for($y=0;$y-lt$bmp.Height-and-not$content;$y++){
                    [Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($locked.Scan0,$y*$locked.Stride),$row,0,$row.Length)
                    for($x=3;$x-lt$row.Length;$x+=4){if($row[$x]-gt8){$content=$true;break}}
                }
            }finally{$bmp.UnlockBits($locked)}
            if(-not$content){return [pscustomobject]@{ok=$false;reason='print_artwork_is_empty'}}
        }finally{$bmp.Dispose()}
    }finally{$img.Dispose()}}finally{$ms.Dispose()}
    return [pscustomobject]@{ok=$true;reason=''}
}

function Test-ForgeFlexibleUploadRules($Profile) {
    if($Profile-isnot[pscustomobject]){return $false}
    $policy=$Profile.PSObject.Properties['upload_dimension_policy']
    if($null-eq$policy){return $true} # Existing explicit-canvas profiles retain their semantics.
    if($policy.Value-isnot[string]-or$policy.Value-cne'flexible'){return $false}
    $p=$Profile.PSObject.Properties['upload_rules'];if($null-eq$p){return $false};$r=$p.Value
    if($r-isnot[pscustomobject]){return $false}
    foreach($name in @('min_width_px_exclusive','min_height_px_exclusive','max_file_bytes_exclusive','png_bit_depth')){
        $f=$r.PSObject.Properties[$name];if($null-eq$f-or($f.Value-isnot[int]-and$f.Value-isnot[long])){return $false}
    }
    if($r.min_width_px_exclusive-lt0-or$r.min_height_px_exclusive-lt0-or$r.max_file_bytes_exclusive-le0-or$r.png_bit_depth-ne8){return $false}
    if($r.png_color_model-isnot[string]-or$r.required_color_space-isnot[string]-or$r.png_color_model-cne'RGB'-or$r.required_color_space-cne'sRGB'){return $false}
    return $true
}
function Test-ForgeAmazonPrintProfile($Profile,[bool]$RequireCurrent=$true) {
    try {
        if($Profile-isnot[pscustomobject]){return $false}
        foreach($name in @('schema','authority_kind','marketplace','product_type_key','template_key','file_format','background','template_file_sha256','source_file_sha256')){$p=$Profile.PSObject.Properties[$name];if($null-eq$p-or$p.Value-isnot[string]-or[string]::IsNullOrWhiteSpace($p.Value)){return $false}}
        if($Profile.schema-cne'forge.amazon_print_profile.v1'-or$Profile.authority_kind-cne'owner_attested_external'-or$Profile.attested-isnot[bool]-or!$Profile.attested-or$Profile.independent_verification-isnot[bool]-or$Profile.independent_verification){return $false}
        foreach($name in @('canvas_width_px','canvas_height_px','dpi')){$p=$Profile.PSObject.Properties[$name];if($null-eq$p-or($p.Value-isnot[int]-and$p.Value-isnot[long])){return $false}}
        if($Profile.canvas_width_px-lt500-or$Profile.canvas_width_px-gt10000-or$Profile.canvas_height_px-lt500-or$Profile.canvas_height_px-gt10000-or$Profile.dpi-lt72-or$Profile.dpi-gt600-or$Profile.file_format-ine'png'-or$Profile.background-ine'transparent'-or$Profile.template_file_sha256-cnotmatch'^[0-9a-fA-F]{64}$'-or$Profile.source_file_sha256-cnotmatch'^[0-9a-fA-F]{64}$'){return $false}
        $refs=$Profile.PSObject.Properties['source_refs'];if($null-eq$refs-or$refs.Value-isnot[array]-or$refs.Value.Count-lt1){return $false}
        foreach($ref in $refs.Value){if($ref-isnot[string]-or[string]::IsNullOrWhiteSpace($ref)){return $false};$uri=[Uri]$ref;if(!$uri.IsAbsoluteUri-or$uri.Scheme-cne'https'-or$uri.Host.ToLowerInvariant()-notin@('developer.amazon.com','merch.amazon.com','sellercentral.amazon.com')){return $false}}
        $dates=@{};foreach($name in @('captured_at','valid_until')){
            $p=$Profile.PSObject.Properties[$name];if($null-eq$p){return $false};$value=$p.Value
            if($value-is[DateTime]){if($value.Kind-eq[DateTimeKind]::Unspecified){return $false};$dates[$name]=$value.ToUniversalTime()}
            elseif($value-is[DateTimeOffset]){$dates[$name]=$value.UtcDateTime}
            elseif($value-is[string]-and$value-cmatch'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|[+-]\d{2}:\d{2})$'){$dto=[DateTimeOffset]::MinValue;if(![DateTimeOffset]::TryParse($value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$dto)){return $false};$dates[$name]=$dto.UtcDateTime}
            else{return $false}
        }
        $capt=$dates.captured_at;$valid=$dates.valid_until
        if($capt-gt[DateTime]::UtcNow.AddMinutes(10)-or$valid-le$capt-or($valid-$capt).TotalDays-gt120-or($RequireCurrent-and$valid-le[DateTime]::UtcNow)){return $false}
        return (Test-ForgeFlexibleUploadRules $Profile)
    }catch{return $false}
}
function Get-ForgeUploadTechnicalSnapshot([byte[]]$Bytes,$Profile) {
    $m=Get-ForgePngMetadata $Bytes
    $flex=($Profile.PSObject.Properties['upload_dimension_policy']-and$Profile.upload_dimension_policy-ceq'flexible')
    if($flex){
        if(-not(Test-ForgeFlexibleUploadRules $Profile)){return [pscustomobject]@{ok=$false;reason='invalid_upload_rules'}}
        $r=$Profile.upload_rules
        $size=($m.width-gt$r.min_width_px_exclusive-and$m.height-gt$r.min_height_px_exclusive)
        $bytesOk=($Bytes.Length-lt$r.max_file_bytes_exclusive)
        $rgb8=($m.valid-and$Bytes[24]-eq$r.png_bit_depth-and$m.color_type-in@(2,6))
    }else{
        $size=($m.width-eq$Profile.canvas_width_px-and$m.height-eq$Profile.canvas_height_px)
        # Legacy profiles retain exact canvas dimensions, not exemptions from PNG upload constraints.
        $bytesOk=($Bytes.Length-lt26214400);$rgb8=($m.valid-and$Bytes[24]-eq8-and$m.color_type-in@(2,6))
    }
    $transparency=(Test-ForgeGenerationPngBytes $Bytes $m.width $m.height).ok
    # No mandatory embedded ICC/sRGB chunk is assumed. The actual colour space
    # must be checked in the existing exact-file owner print review.
    return [pscustomobject]@{ok=($size-and$bytesOk-and$rgb8-and$transparency);dimensions_allowed=$size;file_size_allowed=$bytesOk;png_format_allowed=$rgb8;transparency_checks_pass=$transparency;dimension_policy=if($flex){'flexible'}else{'exact_canvas'};recommended_canvas_match=($m.width-eq$Profile.canvas_width_px-and$m.height-eq$Profile.canvas_height_px);color_space_status='sRGB_requires_exact_file_review';reason=if(-not$size){'upload_dimensions_not_allowed'}elseif(-not$bytesOk){'upload_file_size_not_allowed'}elseif(-not$rgb8){'upload_requires_rgb_8bit_png'}elseif(-not$transparency){'upload_transparency_check_failed'}else{'upload_measurable_constraints_pass'};detail_quality_verified=$false}
}
