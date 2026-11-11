. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
# Local research adapter boundary. No HTTP, credentials, polling, or score mutation.
function Get-ForgeResearchAdapters {return @([pscustomobject]@{key='public_observations_v1';schema='forge.research_import.v1';network_enabled=$false})}
function Assert-ResearchNoSecrets($Value){
 if($null-eq$Value){return}
 if($Value-is[string]){if($Value-match'(?i)[?&](key|api_key|token)=|\bBearer\s+\S+'){throw 'Credential-bearing values are not importable'};return}
 if($Value-is[Array]){foreach($v in $Value){Assert-ResearchNoSecrets $v};return}
 if($Value-is[pscustomobject]){foreach($p in $Value.PSObject.Properties){if($p.Name-match'(?i)^(key|api_?key|access_?key|authorization|password|credentials|token)$'){throw 'Credential fields are not importable'};Assert-ResearchNoSecrets $p.Value}}
}
function ConvertFrom-ResearchUtc($Value){
 if($Value-is[DateTime]){return $Value.ToUniversalTime()}
 if([string]$Value-notmatch'(Z|[+-]\d\d:\d\d)$'){throw 'Research timestamps require a time zone'}
 return [DateTime]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}
function ConvertFrom-KeepaMinute($Value){
 if($null-eq$Value-or($Value-isnot[int]-and$Value-isnot[long])-or$Value-lt0){return $null}
 return ([DateTime]'2011-01-01T00:00:00Z').ToUniversalTime().AddMinutes($Value)
}
function ConvertFrom-KeepaPairs($History,[DateTime]$CollectedAt,[bool]$Rank=$false){
 if($null-eq$History){return ,@()}
 if($History-isnot[Array]-or$History.Count%2-or$History.Count-gt100000){throw 'Malformed or oversized Keepa time series'}
 $out=@();$last=-1L
 for($i=0;$i-lt$History.Count;$i+=2){
  $t=ConvertFrom-KeepaMinute $History[$i];$v=$History[$i+1]
  if($null-eq$t-or$t-gt$CollectedAt.AddMinutes(5)-or$History[$i]-le$last-or($v-isnot[int]-and$v-isnot[long])){throw 'Invalid/out-of-order Keepa history'}
  $last=[long]$History[$i];$known=($v-ge0-and(-not$Rank-or$v-gt0))
  $out+=[pscustomobject]@{at=$t.ToString('o');value=if($known){[long]$v}else{$null};raw_value=$v}
 }
 return ,$out
}
function Get-KeepaSeries($Product,[int]$Index){$csv=Get-PropertyValue $Product 'csv';if($csv-is[Array]-and$csv.Count-gt$Index){return ,$csv[$Index]};return $null}
function ConvertTo-ResearchDiscoverSnapshotOriginal($Packet){
 $state=if($Packet.synthetic){'FIXTURE'}else{'Imported, not independently verified'}
 $sources=@([pscustomobject]@{id=$Packet.source_sha256;name=('Public observations '+$state);source_class='imported_observations';url=[string]$Packet.rows[0].source_url;last_checked_at=$Packet.collected_at})
 foreach($r in $Packet.rows){$sources+=[pscustomobject]@{id=$r.evidence_id;name=($r.observation_kind+' | '+$r.freshness+' | creator: '+[string](Get-PropertyValue $r 'creator'));source_class='public_observation';url=$r.source_url;last_checked_at=$r.observed_at}}
 return [pscustomobject]@{contract='forge.discover_snapshot.v1';origin='local_import';research_verified=$false;synthetic=$Packet.synthetic;stats=[pscustomobject]@{niches=1;research_notes=1;active_sources=0;concepts=0};niches=@([pscustomobject]@{niche_key=$Packet.niche_key;name=$Packet.niche_name;audience=$Packet.audience;category='Imported public observations; Amazon coverage unverified';score_total=$null;score_confidence=$null;concept_count=0;research_summary=($state+': '+$Packet.summary);dimensions=[pscustomobject]@{}});notes=@([pscustomobject]@{niche_key=$Packet.niche_key;topic='Imported observations';conclusion=($Packet.summary+' Gaps/limits: '+($Packet.limitations-join'; '));evidence_refs=@($Packet.rows.evidence_id)});sources=$sources;research_packet=$Packet;generated_at=[DateTime]::UtcNow.ToString('o')}
}
function ConvertTo-ResearchDiscoverSnapshot($Packet){
 $snapshot=ConvertTo-ResearchDiscoverSnapshotOriginal $Packet
 $language=[pscustomobject]@{schema='forge.import_language_review.v1';audience=(Get-ForgeOwnerTextLanguage ([string]$Packet.audience));summary=(Get-ForgeOwnerTextLanguage ([string]$Packet.summary));semantic_translation_verified=$false;original_text_preserved=$true}
 $snapshot|Add-Member -NotePropertyName owner_language_review -NotePropertyValue $language -Force
 return $snapshot
}
function Import-ForgeResearchFile([string]$Path,[bool]$Activate=$true){
 $f=Get-Item -LiteralPath $Path;if($f.Length-gt10MB){throw 'Research import exceeds 10MiB'}
 $bytes=[IO.File]::ReadAllBytes($f.FullName);if($bytes.Length-gt10MB){throw 'Research import exceeds 10MiB'}
 $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes).TrimStart([char]0xfeff);$data=ConvertFrom-ForgeJsonObjectStrict $text
 $h=[Security.Cryptography.SHA256]::Create();try{$sha=([BitConverter]::ToString($h.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()};$packet=ConvertFrom-PublicResearchExport $data $sha
 $root=Join-Path $script:StateRoot 'research-import-v1';Ensure-Dir $root
 $archive=Join-Path $root ($sha+'.source.json');$utf8=New-Object Text.UTF8Encoding($false)
 if(Test-Path $archive){if((Get-FileSha256Hex $archive)-cne$sha){throw 'Existing research archive hash mismatch'}}else{[IO.File]::WriteAllBytes($archive,$bytes);if((Get-FileSha256Hex $archive)-cne$sha){throw 'Source encoding changed; import not activated'}}
 # Pointer contains only a SHA, never a user-selected path or credentials.
 if($Activate){$temp=Join-Path $root ('active.tmp.'+[guid]::NewGuid().ToString('N'));[IO.File]::WriteAllText($temp,$sha,$utf8);Move-Item -LiteralPath $temp -Destination (Join-Path $root 'active.sha256') -Force}
 return ConvertTo-ResearchDiscoverSnapshot $packet
}
function Read-ForgeImportedResearch {
 $root=Join-Path $script:StateRoot 'research-import-v1';$pointer=Join-Path $root 'active.sha256';if(!(Test-Path $pointer)){return $null}
 $dir=Get-Item -LiteralPath $root -Force;$item=Get-Item -LiteralPath $pointer -Force
 if($dir-isnot[IO.DirectoryInfo]-or($dir.Attributes-band[IO.FileAttributes]::ReparsePoint)-or$item-isnot[IO.FileInfo]-or$item.Length-gt128-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Research pointer is oversized, redirected or not an ordinary file'}
 $sha=[IO.File]::ReadAllText($pointer).Trim();if($sha-cnotmatch'^[0-9a-f]{64}$'){throw 'Invalid research pointer'}
 $p=Join-Path $root ($sha+'.source.json');$source=Get-Item -LiteralPath $p -Force
 if($source-isnot[IO.FileInfo]-or($source.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Research archive is not an ordinary source file'}
 $payload=Read-LocalCheckEvidencePayload $p;if($payload.sha256-cne$sha){throw 'Imported research source changed'}
 return ConvertTo-ResearchDiscoverSnapshot (ConvertFrom-PublicResearchExport $payload.data $sha)
}
function Invoke-ResearchImportDialog {
 try{$d=New-Object Microsoft.Win32.OpenFileDialog;$d.Filter='Research JSON (*.json)|*.json';$d.Title='Import research JSON (no API call)';if($d.ShowDialog()-ne$true){return};$script:DiscoverSnapshot=Import-ForgeResearchFile $d.FileName;$script:DiscoverLoadedAt=[DateTime]::UtcNow;Render-DiscoverSnapshot $script:DiscoverSnapshot;$DiscoverStatusText.Text='Импортированы оригинальные наблюдения. Язык исходного текста указан; русского смыслового перевода может не быть. Спрос не подтверждён.';Update-DiscoverDraftControls}catch{Show-Error $_.Exception.Message}
}
