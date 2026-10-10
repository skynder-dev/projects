# Merch Forge · Local media/preview boundary
# Owns preview cache, hashing and bitmap loading. No product submission.
function Get-ByteSha256Hex([byte[]]$Bytes) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
}
function Get-ObjectTextProperty($Object,[string]$Name) {
    if($null -eq $Object){return ''}
    $p=$Object.PSObject.Properties[$Name]
    if($null -eq $p -or $null -eq $p.Value){return ''}
    return ([string]$p.Value).Trim()
}
function Get-PreviewCachePaths([string]$AssetSha256) {
    $h=([string]$AssetSha256).Trim().ToLowerInvariant()
    if($h -notmatch '^[0-9a-f]{64}$'){throw 'Preview cache identity is invalid.'}
    return [pscustomobject]@{
        DataPath=(Join-Path $script:PreviewCacheRoot ($h + '.preview'))
        MetaPath=(Join-Path $script:PreviewCacheRoot ($h + '.json'))
    }
}
function Trim-PreviewCache {
    try {
        if(-not (Test-Path -LiteralPath $script:PreviewCacheRoot)){return}
        $files=@(Get-ChildItem -LiteralPath $script:PreviewCacheRoot -Filter '*.preview' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending)
        [int64]$used=0; [int]$kept=0
        foreach($f in $files){
            $wouldOverflow=(($kept + 1) -gt $script:PreviewCacheMaxFiles) -or (($used + [int64]$f.Length) -gt $script:PreviewCacheMaxBytes)
            if($wouldOverflow){
                $meta=[IO.Path]::ChangeExtension($f.FullName,'.json')
                Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
                Remove-Item -LiteralPath $meta -Force -ErrorAction SilentlyContinue
            } else {
                $kept++; $used += [int64]$f.Length
            }
        }
        Get-ChildItem -LiteralPath $script:PreviewCacheRoot -Filter '*.json' -File -ErrorAction SilentlyContinue | ForEach-Object {
            $data=[IO.Path]::ChangeExtension($_.FullName,'.preview')
            if(-not (Test-Path -LiteralPath $data)){Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue}
        }
    } catch { Write-AppLog 'WARN' ('Preview cache cleanup failed: ' + $_.Exception.Message) }
}
function Save-VerifiedPreviewCache([string]$VariantId,[string]$PreviewKey,[string]$ExpectedSha,[byte[]]$Bytes,[string]$MimeType) {
    $variant=([string]$VariantId).Trim(); $key=([string]$PreviewKey).Trim(); $expected=([string]$ExpectedSha).Trim().ToLowerInvariant()
    if([string]::IsNullOrWhiteSpace($variant) -or [string]::IsNullOrWhiteSpace($key)){throw 'Verified preview cache requires exact variant and preview identity.'}
    if($expected -notmatch '^[0-9a-f]{64}$'){throw 'Verified preview cache requires a valid SHA-256 identity.'}
    if($null -eq $Bytes -or $Bytes.Length -lt 1 -or (Get-ByteSha256Hex $Bytes) -ne $expected){throw 'Verified preview cache refused bytes that failed integrity verification.'}
    Ensure-Dir $script:PreviewCacheRoot
    $paths=Get-PreviewCachePaths $expected
    $variantIds=@(); $previewKeys=@()
    if((Test-Path -LiteralPath $paths.DataPath) -and (Test-Path -LiteralPath $paths.MetaPath)){
        try {
            $existing=Get-Content -LiteralPath $paths.MetaPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if($null -ne $existing.PSObject.Properties['variant_ids']){$variantIds=@($existing.variant_ids | ForEach-Object {([string]$_).Trim()} | Where-Object {$_})}
            if($null -ne $existing.PSObject.Properties['preview_keys']){$previewKeys=@($existing.preview_keys | ForEach-Object {([string]$_).Trim()} | Where-Object {$_})}
        } catch {}
    }
    if($variantIds -notcontains $variant){$variantIds += $variant}
    if($previewKeys -notcontains $key){$previewKeys += $key}
    $tempData=$paths.DataPath + '.tmp.' + [Guid]::NewGuid().ToString('N')
    $tempMeta=$paths.MetaPath + '.tmp.' + [Guid]::NewGuid().ToString('N')
    try {
        [IO.File]::WriteAllBytes($tempData,$Bytes)
        if((Get-ByteSha256Hex ([IO.File]::ReadAllBytes($tempData))) -ne $expected){throw 'Preview cache temp write failed integrity verification.'}
        $meta=[ordered]@{
            contract_version=$script:PreviewCacheContract
            asset_sha256=$expected
            variant_ids=@($variantIds)
            preview_keys=@($previewKeys)
            mime_type=([string]$MimeType).Trim()
            verified_at_utc=[DateTime]::UtcNow.ToString('o')
            source='verified_online_preview'
            disposable=$true
            authoritative=$false
        }
        $utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false
        [IO.File]::WriteAllText($tempMeta,($meta | ConvertTo-Json -Depth 6 -Compress),$utf8)
        if(Test-Path -LiteralPath $paths.DataPath){Remove-Item -LiteralPath $paths.DataPath -Force}
        Move-Item -LiteralPath $tempData -Destination $paths.DataPath -Force
        if(Test-Path -LiteralPath $paths.MetaPath){Remove-Item -LiteralPath $paths.MetaPath -Force}
        Move-Item -LiteralPath $tempMeta -Destination $paths.MetaPath -Force
        Trim-PreviewCache
    } finally {
        Remove-Item -LiteralPath $tempData -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $tempMeta -Force -ErrorAction SilentlyContinue
    }
}
function Read-VerifiedPreviewCache($Variant) {
    if($null -eq $Variant){return $null}
    $variantId=Get-ObjectTextProperty $Variant 'id'
    $expected=(Get-ObjectTextProperty $Variant 'asset_sha256').ToLowerInvariant()
    $previewKey=Get-ObjectTextProperty $Variant 'preview_key'
    if([string]::IsNullOrWhiteSpace($variantId) -or $expected -notmatch '^[0-9a-f]{64}$'){return $null}
    $paths=Get-PreviewCachePaths $expected
    if(-not (Test-Path -LiteralPath $paths.DataPath) -or -not (Test-Path -LiteralPath $paths.MetaPath)){return $null}
    try { $meta=Get-Content -LiteralPath $paths.MetaPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
    if((Get-ObjectTextProperty $meta 'contract_version') -ne $script:PreviewCacheContract){return $null}
    if((Get-ObjectTextProperty $meta 'asset_sha256').ToLowerInvariant() -ne $expected){return $null}
    if($null -eq $meta.PSObject.Properties['variant_ids'] -or $null -eq $meta.PSObject.Properties['preview_keys'] -or $null -eq $meta.PSObject.Properties['disposable'] -or $null -eq $meta.PSObject.Properties['authoritative']){return $null}
    $variantIds=@($meta.variant_ids | ForEach-Object {([string]$_).Trim()})
    $previewKeys=@($meta.preview_keys | ForEach-Object {([string]$_).Trim()})
    if($variantIds -notcontains $variantId){return $null}
    if(-not [string]::IsNullOrWhiteSpace($previewKey) -and $previewKeys -notcontains $previewKey){return $null}
    if($meta.disposable -ne $true -or $meta.authoritative -ne $false){return $null}
    $bytes=[IO.File]::ReadAllBytes($paths.DataPath)
    if($null -eq $bytes -or $bytes.Length -lt 1 -or (Get-ByteSha256Hex $bytes) -ne $expected){
        Remove-Item -LiteralPath $paths.DataPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $paths.MetaPath -Force -ErrorAction SilentlyContinue
        throw 'Cached preview failed integrity verification.'
    }
    try {[IO.File]::SetLastWriteTimeUtc($paths.DataPath,[DateTime]::UtcNow)}catch{}
    return $bytes
}
function ConvertTo-FrozenBitmapImage([byte[]]$Bytes) {
    $ms=New-Object IO.MemoryStream(,$Bytes)
    try {
        $bmp=New-Object Windows.Media.Imaging.BitmapImage
        $bmp.BeginInit(); $bmp.CacheOption=[Windows.Media.Imaging.BitmapCacheOption]::OnLoad; $bmp.StreamSource=$ms; $bmp.EndInit(); $bmp.Freeze(); return $bmp
    } finally { $ms.Dispose() }
}
function Clear-VariantPreviewImage($ImageControl,$StatusControl,[string]$Message) {
    $ImageControl.Source=$null; $StatusControl.Text=$Message; $StatusControl.Visibility='Visible'
}
function Get-VariantPreviewBitmap($Variant) {
    if($null -eq $Variant){throw 'Select a visual variant first.'}
    $script:LastPreviewSource=''
    $variantId=Get-ObjectTextProperty $Variant 'id'
    $variantHash=(Get-ObjectTextProperty $Variant 'asset_sha256').ToLowerInvariant()
    if([string]::IsNullOrWhiteSpace($variantId)){throw 'Selected variant has no preview identity.'}
    if($variantHash -notmatch '^[0-9a-f]{64}$'){throw 'Selected variant has no valid asset SHA-256 identity.'}
    $localPath=Get-ObjectTextProperty $Variant 'local_file_path'
    $localOnly=[bool](Get-PropertyValue $Variant 'local_only')
    if($localOnly -and -not [string]::IsNullOrWhiteSpace($localPath)){
        if(-not(Test-Path -LiteralPath $localPath -PathType Leaf)){throw 'Local artwork file is missing.'}
        $bytes=[IO.File]::ReadAllBytes($localPath)
        if($bytes.Length -lt 1 -or (Get-ByteSha256Hex $bytes) -ne $variantHash){throw 'Local artwork failed SHA-256 preview verification.'}
        $script:LastPreviewSource='local'
        return ConvertTo-FrozenBitmapImage $bytes
    }
    $fallbackReason=''
    $base=([string]$env:MERCH_FORGE_ASSET_BASE_URL).Trim().TrimEnd('/')
    $uriCheck=$null
    if([string]::IsNullOrWhiteSpace($base)){
        $fallbackReason='Image preview service is not configured on this PC.'
    } elseif(-not [Uri]::TryCreate($base,[UriKind]::Absolute,[ref]$uriCheck) -or $uriCheck.Scheme -notin @('http','https')){
        $fallbackReason='Image preview service address is invalid.'
    } else {
        $ticket=$null
        try { $ticket=Invoke-ForgeApi 'asset_preview_ticket' @{variant_id=$variantId;ttl_seconds=300} }
        catch { $fallbackReason='Preview API is unavailable: ' + $_.Exception.Message }
        if($null -ne $ticket){
            $availability=([string]$ticket.availability).Trim().ToLowerInvariant()
            if($availability -eq 'corrupt'){throw 'Preview is corrupt.'}
            if($availability -ne 'available'){
                $fallbackReason=("Preview is {0}." -f $(if($availability){$availability}else{'unavailable'}))
            } else {
                $previewKey=([string]$ticket.preview_key).Trim(); $ticketValue=([string]$ticket.ticket).Trim(); $expected=([string]$ticket.asset_sha256).Trim().ToLowerInvariant()
                if([string]::IsNullOrWhiteSpace($previewKey) -or [string]::IsNullOrWhiteSpace($ticketValue)){throw 'Preview ticket is incomplete.'}
                if($expected -notmatch '^[0-9a-f]{64}$'){throw 'Preview integrity hash is missing or invalid.'}
                if($variantHash -ne $expected){throw 'Preview lineage hash does not match the selected variant.'}
                $url=$base + '/forge-assets/preview/' + [Uri]::EscapeDataString($previewKey)
                $bytes=$null
                $client=$null; $request=$null; $response=$null
                try {
                    $client=New-Object Net.Http.HttpClient
                    $request=New-Object Net.Http.HttpRequestMessage([Net.Http.HttpMethod]::Get,$url)
                    $null=$request.Headers.TryAddWithoutValidation('x-forge-asset-ticket',$ticketValue)
                    $response=$client.SendAsync($request).GetAwaiter().GetResult()
                    if(-not $response.IsSuccessStatusCode){throw ("Preview service returned HTTP {0}." -f [int]$response.StatusCode)}
                    $bytes=$response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
                } catch { $fallbackReason='Preview service is unavailable: ' + $_.Exception.Message }
                finally {
                    if($null -ne $response){$response.Dispose()}
                    if($null -ne $request){$request.Dispose()}
                    if($null -ne $client){$client.Dispose()}
                }
                if($null -ne $bytes){
                    if($bytes.Length -lt 1){$fallbackReason='Preview service returned an empty image.'}
                    else {
                        if((Get-ByteSha256Hex $bytes) -ne $expected){throw 'Preview failed integrity verification.'}
                        try { Save-VerifiedPreviewCache $variantId $previewKey $expected $bytes ([string]$ticket.mime_type) }
                        catch { Write-AppLog 'WARN' ('Verified preview cache write skipped: ' + $_.Exception.Message) }
                        $script:LastPreviewSource='online'
                        return ConvertTo-FrozenBitmapImage $bytes
                    }
                }
            }
        }
    }
    $cached=Read-VerifiedPreviewCache $Variant
    if($null -ne $cached){
        $script:LastPreviewSource='cache'
        Write-AppLog 'WARN' (("Using verified disposable preview cache for variant {0}. Reason: {1}" -f $variantId,$fallbackReason).Trim())
        return ConvertTo-FrozenBitmapImage $cached
    }
    if([string]::IsNullOrWhiteSpace($fallbackReason)){$fallbackReason='Preview is unavailable.'}
    throw ($fallbackReason + ' No verified cached preview is available.')
}
function Set-VariantPreviewImage($ImageControl,$StatusControl,$Variant,[string]$EmptyMessage) {
    if($null -eq $Variant){Clear-VariantPreviewImage $ImageControl $StatusControl $EmptyMessage; return}
    $StatusControl.Text='Loading preview…'; $StatusControl.Visibility='Visible'; $ImageControl.Source=$null
    try {
        $ImageControl.Source=Get-VariantPreviewBitmap $Variant
        if($script:LastPreviewSource -eq 'cache'){$StatusControl.Text='Cached preview · offline';$StatusControl.Visibility='Visible'}elseif($script:LastPreviewSource -eq 'local'){$StatusControl.Text='Local artwork · SHA-256 verified';$StatusControl.Visibility='Visible'}else{$StatusControl.Visibility='Collapsed'}
    }
    catch { Clear-VariantPreviewImage $ImageControl $StatusControl $_.Exception.Message }
}
function Update-VariantVisualPreview {
    $selected=@($VariantList.SelectedItems)
    if($selected.Count -eq 0){Clear-VariantPreviewImage $VariantImageA $VariantImageStatusA 'Select a variant'; Clear-VariantPreviewImage $VariantImageB $VariantImageStatusB 'Select a second variant to compare'; return}
    Set-VariantPreviewImage $VariantImageA $VariantImageStatusA $selected[0] 'Select a variant'
    if($selected.Count -ge 2){Set-VariantPreviewImage $VariantImageB $VariantImageStatusB $selected[1] 'Select a second variant to compare'}else{Clear-VariantPreviewImage $VariantImageB $VariantImageStatusB 'Select a second variant to compare'}
}
