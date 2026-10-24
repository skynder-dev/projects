# Merch Forge · Local-first core workflow
# Owns local artwork import, local exact acceptance, local check evidence, manual-upload package generation,
# and local sales CSV import. It never submits to an external marketplace and never pretends local state is server state.
. (Join-Path $PSScriptRoot 'Forge.PrintChecks.ps1')
. (Join-Path $PSScriptRoot 'Forge.BriefApproval.ps1')
$script:LocalPublicationEditor=$null

function Enter-LocalCoreMutationLock {
    Ensure-Dir $script:LocalCoreRoot;$path=Join-Path $script:LocalCoreRoot 'state-mutation.lock'
    try{return [IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{throw 'Local Forge state is being updated in another window. Nothing was overwritten; refresh and try again.'}
}
function Assert-LocalCoreFreshStart {
    # Empty scaffolding is a first start; existing work is never treated as an empty database.
    foreach($path in @($script:LocalCoreStatePath,$script:LocalCoreBackupPath)){if(Test-Path -LiteralPath $path){throw 'Local Forge state is missing or unavailable while state artifacts remain. Original files were preserved; restore a verified data copy.'}}
    if(!(Test-Path -LiteralPath $script:LocalCoreRoot)){return}
    $emptyDirectories=@('artwork','packages','exports','imports')
    foreach($item in @(Get-ChildItem -LiteralPath $script:LocalCoreRoot -Force -ErrorAction Stop)){
        if($item.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'Local Forge state is missing and recovery artifacts require inspection. No empty state was created.'}
        if(!$item.PSIsContainer-and$item.Name-ceq'state-mutation.lock'){continue}
        if($item.PSIsContainer-and$item.Name-in$emptyDirectories-and@(Get-ChildItem -LiteralPath $item.FullName -Force -ErrorAction Stop).Count-eq0){continue}
        throw 'Local Forge state is missing but previous work remains. No empty state was created. Use My data > Restore with a verified ZIP copy; existing files were preserved.'
    }
}
function Initialize-LocalCore {
    foreach($p in @($script:LocalCoreRoot,$script:LocalCoreArtworkRoot,$script:LocalCorePackageRoot,$script:LocalCoreExportRoot,$script:LocalCoreImportRoot)){Ensure-Dir $p}
    $null=Initialize-GenerationProviderRegistry
    $null=Assert-GenerationProviderConfigSafe
    Initialize-PrintChecks
    $hasPrimary=Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf;$hasBackup=Test-Path -LiteralPath $script:LocalCoreBackupPath -PathType Leaf
    if(-not $hasPrimary -and -not $hasBackup){Assert-LocalCoreFreshStart;try{Write-LocalCoreState (New-LocalCoreState)}catch{if($_.Exception.Message -like 'Local Forge state changed in another window*' -or $_.Exception.Message -like 'Local Forge state is being updated in another window*'){$null=Read-LocalCoreState}else{throw}}}else{$null=Read-LocalCoreState}
}
function New-LocalCoreState {
    return [pscustomobject]@{
        schema='forge.local_core.v2'
        state_revision=0
        last_write_id=''
        updated_at=[DateTime]::UtcNow.ToString('o')
        concepts=@()
        sales_imports=@()
        sales_rows=@()
        publication_receipts=@()
    }
}
function Get-StringSha256Hex([string]$Text) {
    $bytes=[System.Text.Encoding]::UTF8.GetBytes([string]$Text);return (Get-ByteSha256Hex $bytes)
}
function Get-LocalCurrentRevisionIdentity($Concept=$null) {
    if($null -eq $Concept -and $null -ne $script:Current){$Concept=Get-PropertyValue $script:Current 'concept'}
    if($null -eq $Concept){return [pscustomobject]@{id='';hash=''}}
    $rid=([string](Get-PropertyValue $Concept 'current_revision_id')).Trim();$hash=([string](Get-PropertyValue $Concept 'current_content_hash')).Trim().ToLowerInvariant()
    if($hash -notmatch '^[0-9a-f]{64}$'){
        $material=([ordered]@{concept_key=[string](Get-PropertyValue $Concept 'concept_key');title=[string](Get-PropertyValue $Concept 'title');hook=[string](Get-PropertyValue $Concept 'hook');concept_text=[string](Get-PropertyValue $Concept 'concept_text');visual_direction_text=[string](Get-PropertyValue $Concept 'visual_direction_text')}|ConvertTo-Json -Depth 8 -Compress)
        $hash=Get-StringSha256Hex $material
    }
    if([string]::IsNullOrWhiteSpace($rid)){$rid=('snapshot-'+$hash.Substring(0,24))}
    return [pscustomobject]@{id=$rid;hash=$hash}
}
function New-LocalAcceptanceFingerprint([string]$ConceptKey,[string]$RevisionId,[string]$RevisionHash,[string]$ArtworkSha) {
    return (Get-StringSha256Hex ((@($ConceptKey,$RevisionId,$RevisionHash,$ArtworkSha)-join '|').ToLowerInvariant()))
}
function Get-LocalPublicationHash($Publication) {
    if($null -eq $Publication){return ''}
    $normalized=[ordered]@{listing_title=[string](Get-PropertyValue $Publication 'listing_title');brand=[string](Get-PropertyValue $Publication 'brand');bullet_1=[string](Get-PropertyValue $Publication 'bullet_1');bullet_2=[string](Get-PropertyValue $Publication 'bullet_2');description=[string](Get-PropertyValue $Publication 'description');keywords=@((Get-PropertyValue $Publication 'keywords'));locale=[string](Get-PropertyValue $Publication 'locale')}
    return (Get-StringSha256Hex ($normalized|ConvertTo-Json -Depth 12 -Compress))
}
function Get-LocalPublicationHashFromLiveWorkspace($Workspace) {
    if($null -eq $Workspace){return ''}
    $snapshot=[pscustomobject]@{listing_title=[string](Get-PropertyValue $Workspace 'listing_title');brand=[string](Get-PropertyValue $Workspace 'brand');bullet_1=[string](Get-PropertyValue $Workspace 'bullet_1');bullet_2=[string](Get-PropertyValue $Workspace 'bullet_2');description=[string](Get-PropertyValue $Workspace 'description');keywords=@((Get-PropertyValue $Workspace 'keywords'));locale=[string](Get-PropertyValue $Workspace 'locale')}
    return (Get-LocalPublicationHash $snapshot)
}
function Test-LocalPublicationMatchesLiveWorkspace($Publication,$Workspace) {
    $localHash=Get-LocalPublicationHash $Publication;$liveHash=Get-LocalPublicationHashFromLiveWorkspace $Workspace
    return (-not[string]::IsNullOrWhiteSpace($localHash) -and -not[string]::IsNullOrWhiteSpace($liveHash) -and $localHash -eq $liveHash)
}
function Get-LocalPolicyProfileBinding {
    $profile=Get-LocalAmazonPrintProfile;if($null-eq$profile){return $null}
    $binding=[ordered]@{
        schema='forge.policy_profile_binding.v1'
        marketplace=([string](Get-PropertyValue $profile 'marketplace')).Trim().ToLowerInvariant()
        product_type_key=([string](Get-PropertyValue $profile 'product_type_key')).Trim().ToLowerInvariant()
        template_key=([string](Get-PropertyValue $profile 'template_key')).Trim().ToLowerInvariant()
        canvas_width_px=[int](Get-PropertyValue $profile 'canvas_width_px')
        canvas_height_px=[int](Get-PropertyValue $profile 'canvas_height_px')
        dpi=[int](Get-PropertyValue $profile 'dpi')
        file_format=([string](Get-PropertyValue $profile 'file_format')).Trim().ToLowerInvariant()
        background=([string](Get-PropertyValue $profile 'background')).Trim().ToLowerInvariant()
        template_file_sha256=([string](Get-PropertyValue $profile 'template_file_sha256')).Trim().ToLowerInvariant()
    }
    if($profile.PSObject.Properties['upload_dimension_policy']){$binding.upload_dimension_policy=$profile.upload_dimension_policy;$binding.upload_rules=$profile.upload_rules}
    foreach($required in @('marketplace','product_type_key','template_key','file_format','background','template_file_sha256')){if([string]::IsNullOrWhiteSpace([string]$binding[$required])){return $null}}
    if($binding.template_file_sha256 -notmatch '^[0-9a-f]{64}$'){return $null}
    $fingerprint=Get-StringSha256Hex ($binding|ConvertTo-Json -Depth 10 -Compress)
    return [pscustomobject]@{profile_fingerprint=$fingerprint;marketplace=$binding.marketplace;product_type_key=$binding.product_type_key;template_key=$binding.template_key;template_file_sha256=$binding.template_file_sha256}
}
function Test-LocalPolicyProfileBinding($Check) {
    if($null-eq$Check){return $false};$current=Get-LocalPolicyProfileBinding;if($null-eq$current){return $false}
    $fp=([string](Get-PropertyValue $Check 'channel_profile_fingerprint')).Trim().ToLowerInvariant()
    $market=([string](Get-PropertyValue $Check 'marketplace')).Trim().ToLowerInvariant()
    $product=([string](Get-PropertyValue $Check 'product_type_key')).Trim().ToLowerInvariant()
    $template=([string](Get-PropertyValue $Check 'template_key')).Trim().ToLowerInvariant()
    return ($fp -eq [string]$current.profile_fingerprint -and $market -eq [string]$current.marketplace -and $product -eq [string]$current.product_type_key -and $template -eq [string]$current.template_key)
}
function Test-LocalPolicyProfileMatchesLiveWorkspace($Binding,$Workspace) {
    if($null-eq$Binding -or $null-eq$Workspace){return $false}
    $market=([string](Get-PropertyValue $Workspace 'marketplace_key')).Trim().ToLowerInvariant()
    $product=([string](Get-PropertyValue $Workspace 'product_type_key')).Trim().ToLowerInvariant()
    $template=([string](Get-PropertyValue $Workspace 'template_key')).Trim().ToLowerInvariant()
    $liveProfileHash=([string](Get-PropertyValue $Workspace 'channel_profile_hash')).Trim().ToLowerInvariant()
    return (-not[string]::IsNullOrWhiteSpace($market) -and -not[string]::IsNullOrWhiteSpace($product) -and -not[string]::IsNullOrWhiteSpace($template) -and $liveProfileHash -match '^[0-9a-f]{64}$' -and $market -eq [string]$Binding.marketplace -and $product -eq [string]$Binding.product_type_key -and $template -eq [string]$Binding.template_key)
}
function Add-OrSetProperty($Object,[string]$Name,$Value) {
    if($null -eq $Object){return};if($null -eq $Object.PSObject.Properties[$Name]){$Object|Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force}else{$Object.PSObject.Properties[$Name].Value=$Value}
}
function Invalidate-LocalCorePackages($Concept,[string]$Reason) {
    foreach($pkg in @((Get-PropertyValue $Concept 'packages'))){Add-OrSetProperty $pkg 'valid' $false;Add-OrSetProperty $pkg 'invalidated_at' ([DateTime]::UtcNow.ToString('o'));Add-OrSetProperty $pkg 'invalidation_reason' $Reason}
}
function Preserve-ForgeLocalReviewHistory($Lc,[string]$Reason) {
    if($null-eq$Lc){return $false}
    $pub=Get-PropertyValue $Lc 'publication';$approval=Get-PropertyValue $Lc 'brief_approval';$accept=Get-PropertyValue $Lc 'active_acceptance';$decision=[string](Get-PropertyValue $Lc 'owner_decision')
    $meaningful=($null-ne$approval-or$null-ne$accept-or![string]::IsNullOrWhiteSpace([string](Get-PropertyValue $pub 'saved_at'))-or(Get-PropertyValue $pub 'legacy_imported_draft')-eq$true-or$decision-in@('KEEP','EDIT','REGEN','SKIP'))
    foreach($name in @('ip','visual','print','policy','metadata')){if([string](Get-PropertyValue (Get-PropertyValue (Get-PropertyValue $Lc 'checks') $name) 'state')-in@('pass','blocked','not_required')){$meaningful=$true}}
    if(!$meaningful){return $false}
    $prop=$Lc.PSObject.Properties['review_history'];$prior=@();if($null-ne$prop){if($prop.Value-isnot[Array]){throw 'Saved local review history is malformed; current records were preserved.'};$prior=@($prop.Value)}
    $payload=[pscustomobject][ordered]@{concept_key=[string](Get-PropertyValue $Lc 'concept_key');source_revision_id=[string](Get-PropertyValue $Lc 'source_revision_id');source_revision_hash=[string](Get-PropertyValue $Lc 'source_revision_hash');brief_snapshot=(Get-PropertyValue $Lc 'generation_brief_snapshot');brief_sha256=[string](Get-PropertyValue $Lc 'generation_brief_sha256');publication=$pub;checks=(Get-PropertyValue $Lc 'checks');active_acceptance=$accept;owner_decision=$decision;owner_decision_revision_id=[string](Get-PropertyValue $Lc 'owner_decision_revision_id');owner_decision_revision_hash=[string](Get-PropertyValue $Lc 'owner_decision_revision_hash');owner_decision_at=[string](Get-PropertyValue $Lc 'owner_decision_at')}
    $payload=ConvertFrom-Json (ConvertTo-Json -InputObject $payload -Depth 60 -Compress)
    $contextSha=Get-StringSha256Hex (ConvertTo-Json -InputObject $payload -Depth 60 -Compress)
    $approvalSha=if($null-eq$approval){''}else{Get-StringSha256Hex (ConvertTo-Json -InputObject $approval -Depth 60 -Compress)}
    $id='review-'+(Get-StringSha256Hex ($contextSha+'|'+$approvalSha))
    foreach($entry in $prior){if($entry-isnot[pscustomobject]-or[string](Get-PropertyValue $entry 'schema')-cne'forge.local_review_history.v1'-or(Get-PropertyValue $entry 'history_only')-isnot[bool]-or!(Get-PropertyValue $entry 'history_only')){throw 'Saved local review history could not be verified; no history was overwritten.'};if([string]$entry.id-ceq$id-or(!$approvalSha-and[string]$entry.context_sha256-ceq$contextSha)){return $false}}
    Add-OrSetProperty $payload 'brief_approval' $(if($null-eq$approval){$null}else{ConvertFrom-Json (ConvertTo-Json -InputObject $approval -Depth 60 -Compress)})
    $entry=[pscustomobject][ordered]@{schema='forge.local_review_history.v1';id=$id;history_only=$true;context_sha256=$contextSha;captured_at=[DateTime]::UtcNow.ToString('o');reason=$Reason;payload=$payload}
    Add-OrSetProperty $Lc 'review_history' ([object[]]@($prior+@($entry)))
    return $true
}
function Get-ForgeLocalReviewHistoryEvents($Lc) {
    if($null-eq$Lc){return @()};$rows=@();$prop=$Lc.PSObject.Properties['review_history'];if($null-ne$prop-and$prop.Value-is[Array]){$rows=@($prop.Value)}
    $legacy=Get-PropertyValue $Lc 'legacy_v1_content';if($null-ne$legacy-and[string](Get-PropertyValue $legacy 'schema')-ceq'forge.legacy_v1_content.v1'){$rows+=@([pscustomobject]@{id='legacy-v1';history_only=$true;reason='legacy_v1_migration';captured_at='';payload=$legacy})}
    $events=@();foreach($entry in @($rows|Sort-Object captured_at -Descending)){
        if((Get-PropertyValue $entry 'history_only')-isnot[bool]-or!(Get-PropertyValue $entry 'history_only')){continue};$v=Get-PropertyValue $entry 'payload';if($null-eq$v){continue}
        $title=if($script:Locale-ceq'ru'){'Сохранённая история локальной проверки'}elseif($script:Locale-ceq'es'){'Historial de revision local conservado'}else{'Saved local review history'}
        $intro=if($script:Locale-ceq'ru'){'Историческая запись. Она не одобряет текущую идею, файл или публикацию.'}elseif($script:Locale-ceq'es'){'Registro historico. No aprueba la idea, archivo ni publicacion actuales.'}else{'Historical record. It does not approve the current idea, file or publication.'}
        $reason=[string](Get-PropertyValue $entry 'reason')
        $reasonKeys=@('source_save_started','research_revision_changed','concept_revision_changed','owner_decision_changed','artwork_acceptance_changed','listing_changed','check_evidence_changed','legacy_v1_migration')
        $reasonLabels=if($script:Locale-ceq'ru'){@('Перед сохранением идеи','Перед сменой ревизии идеи','Перед сменой ревизии идеи','Перед сменой решения','Перед новой приёмкой файла','Перед изменением текста карточки','Перед изменением проверки','Восстановление старого проекта')}elseif($script:Locale-ceq'es'){@('Antes de guardar la idea','Antes de cambiar revision','Antes de cambiar revision','Antes de cambiar decision','Antes de aceptar otro archivo','Antes de cambiar la ficha','Antes de cambiar la revision','Proyecto antiguo recuperado')}else{@('Before saving idea changes','Before changing idea revision','Before changing idea revision','Before changing owner decision','Before accepting artwork','Before changing listing text','Before changing check result','Old project recovered')}
        $ix=[Array]::IndexOf($reasonKeys,$reason);$reasonLabel=if($ix-ge0){$reasonLabels[$ix]}else{$title}
        $when=if($script:Locale-ceq'ru'){'Время неизвестно'}elseif($script:Locale-ceq'es'){'Fecha no disponible'}else{'Time unavailable'}
        try{$when=([DateTimeOffset]::Parse([string](Get-PropertyValue $entry 'captured_at'))).ToLocalTime().ToString('yyyy-MM-dd HH:mm')}catch{}
        $lines=New-Object 'System.Collections.Generic.List[string]';$lines.Add($intro);$lines.Add('');$lines.Add('Revision: '+[string](Get-PropertyValue $v 'source_revision_id'));$lines.Add('Previous decision: '+[string](Get-PropertyValue $v 'owner_decision'))
        $p=Get-PropertyValue $v 'publication';foreach($pair in @(@('Title','listing_title'),@('Brand','brand'),@('Bullet 1','bullet_1'),@('Bullet 2','bullet_2'),@('Description','description'),@('Locale','locale'),@('Edit reason','edit_reason'))){$lines.Add($pair[0]+': '+[string](Get-PropertyValue $p $pair[1]))};$lines.Add('Keywords: '+(@(Get-PropertyValue $p 'keywords')-join', '))
        foreach($name in @('ip','visual','print','policy','metadata')){$c=Get-PropertyValue (Get-PropertyValue $v 'checks') $name;if($null-ne$c){$lines.Add('');$lines.Add($name+': '+[string](Get-PropertyValue $c 'state'));$lines.Add([string](Get-PropertyValue $c 'note'));$lines.Add('References: '+(@(Get-PropertyValue $c 'evidence_refs')-join'; '))}}
        $brief=Get-PropertyValue $v 'brief_snapshot';if($null-ne$brief){$lines.Add('');$lines.Add('Saved idea: '+[string](Get-PropertyValue $brief 'title'));$lines.Add([string](Get-PropertyValue $brief 'concept_text'));$lines.Add([string](Get-PropertyValue $brief 'visual_direction_text'))}
        $evidence=[pscustomobject]@{history_only=$true;record_id=[string](Get-PropertyValue $entry 'id');revision_hash=[string](Get-PropertyValue $v 'source_revision_hash');brief_sha256=[string](Get-PropertyValue $v 'brief_sha256');artwork_sha256=[string](Get-PropertyValue (Get-PropertyValue $v 'active_acceptance') 'asset_sha256');listing_hash=(Get-LocalPublicationHash $p);approval_id=[string](Get-PropertyValue (Get-PropertyValue $v 'brief_approval') 'approval_id')}
        $at=[string](Get-PropertyValue $entry 'captured_at');$events+=@([pscustomobject]@{event_at=$at;title=$title;summary=($lines-join"`r`n");display=($when+' | '+$reasonLabel+' | '+[string](Get-PropertyValue $v 'source_revision_id'));event_type='local_review_history';actor='local historical record';revision_id=[string](Get-PropertyValue $v 'source_revision_id');visual_candidate_id='';acceptance_id=[string](Get-PropertyValue (Get-PropertyValue $v 'active_acceptance') 'lineage_fingerprint');evidence=$evidence})
    }
    return @($events)
}
function Convert-LocalCoreStateToV2($State) {
    if($null -eq $State){return (New-LocalCoreState)}
    $schema=[string](Get-PropertyValue $State 'schema');if($schema -eq 'forge.local_core.v2'){if($null -eq $State.PSObject.Properties['state_revision']){Add-OrSetProperty $State 'state_revision' 0};if($null -eq $State.PSObject.Properties['last_write_id']){Add-OrSetProperty $State 'last_write_id' ''};return $State};if($schema -ne 'forge.local_core.v1'){throw 'Unsupported local-core state schema.'}
    foreach($name in @('concepts','sales_imports','sales_rows','publication_receipts','research_drafts')){$p=$State.PSObject.Properties[$name];if($null-ne$p-and$p.Value-is[pscustomobject]){$p.Value=@($p.Value)}}
    Add-OrSetProperty $State 'schema' 'forge.local_core.v2';Add-OrSetProperty $State 'state_revision' 0;Add-OrSetProperty $State 'last_write_id' ''
    if($null-eq$State.PSObject.Properties['updated_at']){Add-OrSetProperty $State 'updated_at' ([DateTime]::UtcNow.ToString('o'))}
    foreach($c in @((Get-PropertyValue $State 'concepts'))){
        $legacy=[pscustomobject]@{schema='forge.legacy_v1_content.v1';history_only=$true;artwork=[object[]]@(Get-PropertyValue $c 'artwork');packages=[object[]]@(Get-PropertyValue $c 'packages');source_revision_id=[string](Get-PropertyValue $c 'source_revision_id');source_revision_hash=[string](Get-PropertyValue $c 'source_revision_hash');publication=(Get-PropertyValue $c 'publication');checks=(Get-PropertyValue $c 'checks');active_acceptance=(Get-PropertyValue $c 'active_acceptance');brief_approval=(Get-PropertyValue $c 'brief_approval');owner_decision=[string](Get-PropertyValue $c 'owner_decision');owner_decision_revision_id=[string](Get-PropertyValue $c 'owner_decision_revision_id');owner_decision_revision_hash=[string](Get-PropertyValue $c 'owner_decision_revision_hash');owner_decision_at=[string](Get-PropertyValue $c 'owner_decision_at')}
        $legacy=ConvertFrom-Json (ConvertTo-Json -InputObject $legacy -Depth 60 -Compress)
        Add-OrSetProperty $c 'legacy_v1_content' $legacy
        Add-OrSetProperty $c 'legacy_listing_restore_pending' ($null-ne$legacy.publication)
        Add-OrSetProperty $c 'brief_approval' $null
        Add-OrSetProperty $c 'approval_recovery_review_required' $true
        Add-OrSetProperty $c 'approval_recovery_source' 'legacy_v1_migration'
        Add-OrSetProperty $c 'source_revision_hash' ''
        foreach($a in @((Get-PropertyValue $c 'artwork'))){Add-OrSetProperty $a 'accepted' $false;Add-OrSetProperty $a 'source_revision_hash' '';Add-OrSetProperty $a 'integrity_check' $null}
        Add-OrSetProperty $c 'active_acceptance' $null;Add-OrSetProperty $c 'checks' (New-LocalCoreChecks);Add-OrSetProperty $c 'publication' $null
        Invalidate-LocalCorePackages $c 'v1_state_migrated_without_exact_lineage_binding'
    }
    foreach($r in @((Get-PropertyValue $State 'publication_receipts'))){Add-OrSetProperty $r 'lineage_verified' $false}
    foreach($r in @((Get-PropertyValue $State 'sales_rows'))){Add-OrSetProperty $r 'linked' $false;Add-OrSetProperty $r 'linked_product_key' ''}
    return $State
}
function Test-LocalCorePersistedStateEnvelope($State) {
    return (Test-ForgePersistedStateEnvelope $State)
}
function Read-LocalCoreStateCandidate([string]$Path) {
    if(!(Test-Path -LiteralPath $Path -PathType Leaf)){return $null}
    return (Convert-LocalCoreStateToV2 (Read-ForgeStateFileSnapshot $Path $true).data)
}
function Preserve-LocalCoreUnreadableArtifacts {
    foreach($path in @($script:LocalCoreStatePath,$script:LocalCoreBackupPath)){try{if(Test-Path -LiteralPath $path -PathType Leaf){$sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();$copy=$path+'.corrupt.'+$sha.Substring(0,16);if(-not(Test-Path -LiteralPath $copy -PathType Leaf)){Copy-Item -LiteralPath $path -Destination $copy -Force}}}catch{}}
}
function Set-ForgeRecoveredSnapshotReview($State,[string]$Kind,[string]$SourceSha) {
    $now=[DateTime]::UtcNow.ToString('o');$count=0
    foreach($lc in @($State.concepts)){
        Add-OrSetProperty $lc 'brief_approval' $null
        Add-OrSetProperty $lc 'approval_recovery_review_required' $true
        Add-OrSetProperty $lc 'approval_recovery_source' $Kind
        Add-OrSetProperty $lc 'approval_recovery_at' $now
        Invalidate-LocalCorePackages $lc 'recovered_snapshot_requires_owner_review'
        $count++
    }
    Add-OrSetProperty $State 'authority_recovery_notice' ([pscustomobject]@{schema='forge.recovery_review.v1';kind=$Kind;source_state_sha256=$SourceSha;recovered_at=$now;concepts_requiring_review=$count})
}
function Repair-LocalCorePrimaryFromBackup {
    $lock=$null;$tmpOwned=$false;$tmp=$script:LocalCoreStatePath+'.restore.'+[guid]::NewGuid().ToString('N')
    try{
        $lock=Enter-LocalCoreMutationLock
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){try{$current=Read-LocalCoreStateCandidate $script:LocalCoreStatePath;if($null-ne$current){return $current}}catch{if($_.Exception.Message-like'Unsupported local-core state schema*'){throw}}}
        $sourceSha=Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath;if($sourceSha-ceq'missing'){throw 'Local-core last-good backup is unavailable.'}
        [IO.File]::Copy($script:LocalCoreBackupPath,$tmp,$false);$tmpOwned=$true
        if((Get-FileSha256Hex $tmp)-cne$sourceSha){throw 'Last-good snapshot changed during capture. Recovery copies were preserved.'}
        $verified=Read-LocalCoreStateCandidate $tmp;if($null-eq$verified){throw 'Local-core last-good copy failed validation.'}
        Set-ForgeRecoveredSnapshotReview $verified 'automatic_last_good' $sourceSha
        $context=New-LocalCoreRestoreContext $verified $lock
        if($context.backup_sha256-cne$sourceSha){throw 'The last-good snapshot changed before recovery. Nothing was overwritten.'}
        Write-LocalCoreState $verified -MutationLock $lock -RestoreContext $context
        $recovered=Read-LocalCoreStateCandidate $script:LocalCoreStatePath
        if($null-eq$recovered-or$recovered.last_write_id-cne$verified.last_write_id){throw 'Recovered primary could not be verified. All recovery snapshots were preserved.'}
        Write-AppLog 'WARN' 'Recovered workspace data from last-good snapshot; prior brief approvals require a new exact owner review.'
        return $recovered
    }finally{if($tmpOwned-and(Test-Path -LiteralPath $tmp)){try{if((Get-FileSha256Hex $tmp)-ceq$sourceSha){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}}catch{}};if($null-ne$lock){try{$lock.Dispose()}catch{}}}
}
function Read-LocalCoreState {
    $primaryExists=Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf;$backupExists=Test-Path -LiteralPath $script:LocalCoreBackupPath -PathType Leaf;$hadArtifact=($primaryExists -or $backupExists);$primaryError='';$backupError=''
    if($primaryExists){try{return (Read-LocalCoreStateCandidate $script:LocalCoreStatePath)}catch{$primaryError=$_.Exception.Message;if($primaryError -like 'Unsupported local-core state schema*'){Preserve-LocalCoreUnreadableArtifacts;throw ('Local Forge state uses an unsupported schema. Recovery stopped; no empty state was created. '+$primaryError)}}}
    if($backupExists){try{return (Repair-LocalCorePrimaryFromBackup)}catch{$backupError=$_.Exception.Message}}
    if(-not $hadArtifact){Assert-LocalCoreFreshStart;$fresh=New-LocalCoreState;try{Write-LocalCoreState $fresh;return $fresh}catch{if($_.Exception.Message -like 'Local Forge state changed in another window*' -or $_.Exception.Message -like 'Local Forge state is being updated in another window*'){return (Read-LocalCoreState)};throw}}
    Preserve-LocalCoreUnreadableArtifacts;$detail=(@($primaryError,$backupError)|Where-Object{-not[string]::IsNullOrWhiteSpace($_)}) -join ' | ';Write-AppLog 'ERROR' ('Local core recovery stopped; existing state artifacts are unreadable or invalid. '+$detail);throw ('Local Forge state recovery stopped because existing primary/last-good state could not be validated. No empty state was created. Preserved recovery copies remain under '+$script:LocalCoreRoot+'.')
}
function Assert-LocalCoreMutationLock($Lock) {
    $expected=[IO.Path]::GetFullPath((Join-Path $script:LocalCoreRoot 'state-mutation.lock'))
    if($Lock-isnot[IO.FileStream]-or!$Lock.CanWrite-or[IO.Path]::GetFullPath($Lock.Name)-ine$expected){throw 'A valid local-core mutation lock is required.'}
}
function Get-LocalCoreRestoreFileFence([string]$Path) {
    if(!(Test-Path -LiteralPath $Path)){return 'missing'}
    $item=Get-Item -LiteralPath $Path -Force
    if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'A state recovery path is not an ordinary file; it was preserved.'}
    return (Get-FileSha256Hex $Path)
}
function New-LocalCoreRestoreContext($State,[IO.FileStream]$MutationLock) {
    Assert-LocalCoreMutationLock $MutationLock
    $check=($State|ConvertTo-Json -Depth 60|ConvertFrom-Json);Add-OrSetProperty $check 'state_revision' ([Math]::Max(1,[int64](Get-PropertyValue $check 'state_revision')))
    if(!(Test-LocalCorePersistedStateEnvelope $check)){throw 'The selected restore state is structurally invalid.'}
    foreach($path in @($script:LocalCoreStatePath,$script:LocalCoreBackupPath)){try{$null=Read-LocalCoreStateCandidate $path}catch{if($_.Exception.Message-like'Unsupported local-core state schema*'){throw}}}
    $context=[pscustomobject]@{schema='forge.verified_data_restore_state.v1';core_root=[IO.Path]::GetFullPath($script:LocalCoreRoot);primary_sha256=(Get-LocalCoreRestoreFileFence $script:LocalCoreStatePath);backup_sha256=(Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath);target_state_sha256=(Get-StringSha256Hex ($State|ConvertTo-Json -Depth 60 -Compress));written_primary_sha256='';written_backup_sha256=''}
    $context.PSTypeNames.Insert(0,'Forge.VerifiedDataRestoreContext')
    return $context
}
function Assert-LocalCoreRestoreContext($Context,$State,[IO.FileStream]$MutationLock) {
    Assert-LocalCoreMutationLock $MutationLock
    if($Context.PSTypeNames-notcontains'Forge.VerifiedDataRestoreContext'-or$Context.schema-cne'forge.verified_data_restore_state.v1'-or$Context.core_root-ine[IO.Path]::GetFullPath($script:LocalCoreRoot)-or$Context.target_state_sha256-cne(Get-StringSha256Hex ($State|ConvertTo-Json -Depth 60 -Compress))){throw 'Verified restore context does not match this state and folder.'}
    if($Context.primary_sha256-cne(Get-LocalCoreRestoreFileFence $script:LocalCoreStatePath)-or$Context.backup_sha256-cne(Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath)){throw 'Local Forge state changed in another window during restore. Existing files were preserved.'}
}
function Preserve-LocalCoreRestorePreimages($Context) {
    $preserved=@()
    foreach($pair in @(@($script:LocalCoreStatePath,$Context.primary_sha256),@($script:LocalCoreBackupPath,$Context.backup_sha256))){
        $path=[string]$pair[0];$sha=[string]$pair[1];if($sha-ceq'missing'){continue}
        $copy=$path+'.restore-before.'+$sha.Substring(0,16)+'.json'
        if(Test-Path -LiteralPath $copy){if((Get-LocalCoreRestoreFileFence $copy)-ceq$sha){$preserved+=$copy;continue};$copy+='.'+[Guid]::NewGuid().ToString('N').Substring(0,8)}
        [IO.File]::Copy($path,$copy,$false)
        if((Get-FileSha256Hex $copy)-cne$sha){throw 'State preimage changed during preservation; recovery stopped.'}
        $preserved+=$copy
    }
    Add-OrSetProperty $Context 'preimage_paths' $preserved
}
function Write-LocalCoreRestoredBackup([byte[]]$Bytes,$State,$Context) {
    $pending=$script:LocalCoreBackupPath+'.tmp.'+[Guid]::NewGuid().ToString('N')
    $stream=New-Object IO.FileStream($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($Bytes,0,$Bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    $good=Read-LocalCoreStateCandidate $pending
    if($null-eq$good-or$good.last_write_id-cne$State.last_write_id-or$good.state_revision-ne$State.state_revision){throw 'Restored last-good backup failed verification; snapshots retained.'}
    if(Test-Path -LiteralPath $script:LocalCoreBackupPath){$previous=$script:LocalCoreBackupPath+'.restore-replaced.'+[Guid]::NewGuid().ToString('N').Substring(0,16)+'.json';if(Test-Path -LiteralPath $previous){throw 'Existing recovery snapshot was preserved.'};[IO.File]::Replace($pending,$script:LocalCoreBackupPath,$previous,$true)}else{[IO.File]::Move($pending,$script:LocalCoreBackupPath)}
    $Context.written_backup_sha256=Get-FileSha256Hex $script:LocalCoreBackupPath
}
function Write-LocalCoreState($State,[IO.FileStream]$MutationLock=$null,$RestoreContext=$null) {
    Ensure-Dir $script:LocalCoreRoot
    $State=Convert-LocalCoreStateToV2 $State
    Assert-ForgeStateRecordArrays $State
    $inputRevision=Get-PropertyValue $State 'state_revision';if(($inputRevision-isnot[int]-and$inputRevision-isnot[long])-or$inputRevision-lt0){throw 'Local state revision must be a nonnegative integer.'}
    $expectedRev=0;try{$expectedRev=[int64](Get-PropertyValue $State 'state_revision')}catch{};$expectedWriteId=[string](Get-PropertyValue $State 'last_write_id')
    $stateLock=$null;$tmp=$script:LocalCoreStatePath+'.tmp.'+[Guid]::NewGuid().ToString('N');$backupTmp=$script:LocalCoreBackupPath+'.tmp.'+[Guid]::NewGuid().ToString('N');$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false
    $tmpOwned=$false;$backupOwned=$false;$keepBackup=$false;$ownsStateLock=($null-eq$MutationLock);$damagedRestore=$false
    try {
        if($ownsStateLock){$stateLock=Enter-LocalCoreMutationLock}else{Assert-LocalCoreMutationLock $MutationLock;$stateLock=$MutationLock}
        if($null-ne$RestoreContext){if($ownsStateLock){throw 'Verified data recovery requires the restore transaction lock.'};Assert-LocalCoreRestoreContext $RestoreContext $State $MutationLock;Preserve-LocalCoreRestorePreimages $RestoreContext}
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){
            try{
                $disk=(Read-ForgeStateFileSnapshot $script:LocalCoreStatePath $true).data
                $diskSchema=[string](Get-PropertyValue $disk 'schema');$diskRev=0;try{$diskRev=[int64](Get-PropertyValue $disk 'state_revision')}catch{}
                if($diskSchema-notin@('forge.local_core.v1','forge.local_core.v2')){throw 'Unsupported local-core state schema.'}
                if(!(Test-LocalCorePersistedStateEnvelope $disk)){throw 'Current state envelope is structurally incomplete.'}
                if($diskRev-eq$expectedRev-and[string](Get-PropertyValue $disk 'last_write_id')-cne$expectedWriteId){throw 'Local Forge state changed in another window. The saved write identity differs although the revision number is unchanged. Nothing was overwritten; refresh and try again.'}
                if($diskRev-ne$expectedRev){throw ('Local Forge state changed in another window. Expected revision '+$expectedRev+' but current revision is '+$diskRev+'. Nothing was overwritten; refresh and try again.')}
            }catch{
                if($_.Exception.Message-like'Local Forge state changed in another window*'-or$_.Exception.Message-like'Unsupported local-core state schema*'){throw}
                if($null-ne$RestoreContext){$damagedRestore=$true;Preserve-LocalCoreRestorePreimages $RestoreContext}else{throw ('Current local-core state cannot be safely compared before write: '+$_.Exception.Message)}
            }
        }elseif($null-ne$RestoreContext){$damagedRestore=$true;Preserve-LocalCoreRestorePreimages $RestoreContext
        }elseif($expectedRev-ne0){throw ('Local Forge state changed in another window. Expected revision '+$expectedRev+' but the current state file is missing. Nothing was overwritten; refresh and try again.')}else{Assert-LocalCoreFreshStart}
        $State.state_revision=$expectedRev+1;$State.last_write_id=[Guid]::NewGuid().ToString('N');$State.updated_at=[DateTime]::UtcNow.ToString('o')
        $json=$State|ConvertTo-Json -Depth 60
        if($null-ne$RestoreContext){Add-OrSetProperty $RestoreContext 'planned_primary_sha256' (Get-StringSha256Hex $json);Add-OrSetProperty $RestoreContext 'planned_backup_sha256' $(if($damagedRestore){Get-StringSha256Hex $json}else{$RestoreContext.primary_sha256})}
        $fs=New-Object IO.FileStream($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $tmpOwned=$true
        try{$bytes=$utf8.GetBytes($json);$fs.Write($bytes,0,$bytes.Length);$fs.Flush($true)}finally{$fs.Dispose()}
        $verify=(Read-ForgeStateFileSnapshot $tmp).data
        if(!(Test-LocalCorePersistedStateEnvelope $verify)){throw 'Local core temp envelope failed validation.'}
        if([string](Get-PropertyValue $verify 'schema') -ne 'forge.local_core.v2' -or [string](Get-PropertyValue $verify 'last_write_id') -ne [string]$State.last_write_id -or [int64](Get-PropertyValue $verify 'state_revision') -ne ($expectedRev+1)){throw 'Local core temp state failed verification.'}
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){
            if(Test-Path -LiteralPath $backupTmp){throw 'An existing backup staging file was preserved; refresh and retry.'}
            [IO.File]::Replace($tmp,$script:LocalCoreStatePath,$backupTmp,$true)
            $backupOwned=$true
            if($damagedRestore){
                $keepBackup=$true
                try{Write-LocalCoreRestoredBackup $bytes $State $RestoreContext}catch{
                    $committed=Read-LocalCoreStateCandidate $script:LocalCoreStatePath
                    if($null-eq$committed-or$committed.last_write_id-cne$State.last_write_id){throw 'Recovered primary commit could not be verified; all snapshots retained.'}
                    try{Write-AppLog 'WARN' ('Recovered primary saved; last-good repair failed and snapshots remain: '+$_.Exception.Message)}catch{}
                }
            }else{try{Move-Item -LiteralPath $backupTmp -Destination $script:LocalCoreBackupPath -Force;$backupOwned=$false}catch{
                $backupError=$_.Exception.Message;$keepBackup=$true
                $committed=Read-LocalCoreStateCandidate $script:LocalCoreStatePath
                if($null-eq$committed-or$committed.last_write_id-cne$State.last_write_id-or$committed.state_revision-ne$State.state_revision){throw 'Primary state commit could not be verified after a backup error. Existing snapshots were preserved.'}
                $retained=$script:LocalCoreBackupPath+'.retained.'+$State.last_write_id+'.json'
                try{[IO.File]::Move($backupTmp,$retained);$backupOwned=$false}catch{$retained=$backupTmp}
                try{Write-AppLog 'WARN' ('Primary state saved and verified; last-good backup could not be replaced. Latest prior snapshot retained at '+$retained+'. '+$backupError)}catch{}
            }}
        } else {
            [IO.File]::Move($tmp,$script:LocalCoreStatePath)
            try{if($damagedRestore){Write-LocalCoreRestoredBackup $bytes $State $RestoreContext}else{Copy-Item -LiteralPath $script:LocalCoreStatePath -Destination $script:LocalCoreBackupPath -Force}}catch{
                $backupError=$_.Exception.Message;$committed=Read-LocalCoreStateCandidate $script:LocalCoreStatePath
                if($null-eq$committed-or$committed.last_write_id-cne$State.last_write_id-or$committed.state_revision-ne$State.state_revision){throw 'Initial primary state commit could not be verified after a backup error.'}
                try{Write-AppLog 'WARN' ('Initial primary state saved and verified; backup copy failed. '+$backupError)}catch{}
            }
        }
    } finally {if($ownsStateLock-and$null-ne$stateLock){try{$stateLock.Dispose()}catch{}};if($tmpOwned){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue};if($backupOwned-and-not$keepBackup){Remove-Item -LiteralPath $backupTmp -Force -ErrorAction SilentlyContinue}}
}
function Get-LocalCoreConcept([string]$ConceptKey,$State=$null) {
    if([string]::IsNullOrWhiteSpace($ConceptKey)){return $null}
    if($null -eq $State){$State=Read-LocalCoreState}
    foreach($c in @($State.concepts)){if([string](Get-PropertyValue $c 'concept_key') -eq $ConceptKey){return $c}}
    return $null
}
function New-LocalCoreCheckRecord([string]$State,[string]$Source,[string]$Note,[string]$Scope,[string]$RevisionId,[string]$ArtworkSha,[string]$ListingHash,[string]$AuthorityKind='none',$EvidenceRefs=@(),[string]$EvidenceFileSha='',[string]$EvidenceSchema='') {
    return [pscustomobject]@{state=$State;source=$Source;note=$Note;checked_at='';scope=$Scope;concept_revision_id=$RevisionId;asset_sha256=$ArtworkSha;listing_hash=$ListingHash;channel_profile_fingerprint='';marketplace='';product_type_key='';template_key='';authority_kind=$AuthorityKind;evidence_refs=@($EvidenceRefs);evidence_source_file_sha256=$EvidenceFileSha;evidence_schema=$EvidenceSchema}
}
function New-LocalCoreChecks([string]$RevisionId='',[string]$ArtworkSha='',[string]$ListingHash='') {
    $ip=New-LocalCoreCheckRecord 'needs_review' 'local_default' 'IP screen is not available locally. No legal clearance is implied.' 'revision' $RevisionId '' ''
    $ip|Add-Member -NotePropertyName legal_clearance -NotePropertyValue $false -Force
    return [pscustomobject]@{
        ip=$ip
        visual=(New-LocalCoreCheckRecord 'needs_review' 'local_default' 'Accept exact artwork to bind visual integrity evidence.' 'artwork' $RevisionId $ArtworkSha '')
        print=(New-LocalCoreCheckRecord 'needs_review' 'local_default' 'Authoritative channel print profile is not available locally.' 'artwork' $RevisionId $ArtworkSha '')
        policy=(New-LocalCoreCheckRecord 'needs_review' 'local_default' 'Marketplace policy evidence must be bound to this exact listing revision.' 'listing' $RevisionId $ArtworkSha $ListingHash)
        metadata=(New-LocalCoreCheckRecord 'needs_review' 'local_default' 'Marketplace metadata must be checked against this exact listing revision.' 'listing' $RevisionId $ArtworkSha $ListingHash)
    }
}
function Get-LocalCheckAllowedAuthority([string]$Name,[string]$State) {
    if($State -eq 'not_required'){return @('not_required_documented')}
    if($State -ne 'pass'){return @('none','owner_attested_external','verified_worker','verified_channel_profile','live_backend_exact','owner_exact_accept')}
    switch($Name){
        'visual' { return @('owner_exact_accept','verified_worker','live_backend_exact') }
        'ip' { return @('owner_attested_external','verified_worker','live_backend_exact') }
        'print' { return @('owner_attested_external','verified_worker','verified_channel_profile','live_backend_exact') }
        'policy' { return @('owner_attested_external','verified_worker','verified_channel_profile','live_backend_exact') }
        'metadata' { return @('owner_attested_external','verified_worker','verified_channel_profile','live_backend_exact') }
        default { return @() }
    }
}
function Get-LocalEvidenceRefValidation($Refs) {
    $valid=@();$invalid=0
    foreach($r in @($Refs)){
        if($null -eq $r -or -not($r -is [string])){$invalid++;continue}
        $v=([string]$r).Trim();if([string]::IsNullOrWhiteSpace($v)){$invalid++;continue};$valid+=$v
    }
    return [pscustomobject]@{valid_refs=@($valid);invalid_count=$invalid}
}
function Test-LocalCheckEvidenceAuthority([string]$Name,$Check) {
    if($null -eq $Check){return $false};$state=([string](Get-PropertyValue $Check 'state')).Trim().ToLowerInvariant();if($state -notin @('pass','not_required')){return $false}
    $authority=([string](Get-PropertyValue $Check 'authority_kind')).Trim().ToLowerInvariant();if(-not((Get-LocalCheckAllowedAuthority $Name $state) -contains $authority)){return $false}
    $source=([string](Get-PropertyValue $Check 'source')).Trim();$checkedAt=([string](Get-PropertyValue $Check 'checked_at')).Trim();if([string]::IsNullOrWhiteSpace($source) -or [string]::IsNullOrWhiteSpace($checkedAt)){return $false}
    try{$checkedTime=[DateTime]::Parse($checkedAt,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind);if($checkedTime.ToUniversalTime() -gt [DateTime]::UtcNow.AddMinutes(10)){return $false}}catch{return $false}
    if($authority -notin @('owner_exact_accept','live_backend_exact')){$refValidation=Get-LocalEvidenceRefValidation (Get-PropertyValue $Check 'evidence_refs');if([int](Get-PropertyValue $refValidation 'invalid_count') -gt 0 -or @(Get-PropertyValue $refValidation 'valid_refs').Count -lt 1){return $false}}
    if($authority -eq 'owner_attested_external'-and!(Test-LocalOwnerEvidenceCapture $Name $Check)){return $false}
    return $true
}
function Complete-ForgeOfflineBriefFrame($Concept,[string]$BriefSha) {
    if((Get-PropertyValue $Concept 'offline_materialization_pending')-is[bool]-and(Get-PropertyValue $Concept 'offline_materialization_pending')){
        $Concept.offline_materialization_pending=$false;$Concept.offline_brief_basis='saved_local_brief';$Concept.offline_saved_brief_sha256=$BriefSha
    }
}
function Assert-ForgeSourceSaveIntent($Intent) {
    if($null-eq$Intent-or[string](Get-PropertyValue $Intent 'schema')-cne'forge.source_save_intent.v1'-or[string](Get-PropertyValue $Intent 'intent_id')-cnotmatch'^[0-9a-f]{32}$'-or(Get-PropertyValue $Intent 'substantive_change')-isnot[bool]){throw 'Pending source-save evidence is invalid. Restore or inspect it before continuing.'}
    foreach($field in @('prior_revision_hash','prior_brief_sha256','proposed_brief_sha256')){if([string](Get-PropertyValue $Intent $field)-cnotmatch'^[0-9a-fA-F]{64}$'){throw 'Pending source-save fingerprint is invalid. Existing evidence was preserved.'}}
    if([string]::IsNullOrWhiteSpace([string](Get-PropertyValue $Intent 'prior_revision_id'))){throw 'Pending source-save identity is invalid.'}
    $date=[DateTimeOffset]::MinValue;if(![DateTimeOffset]::TryParse([string](Get-PropertyValue $Intent 'created_at'),[ref]$date)-or$date.Offset-ne[TimeSpan]::Zero){throw 'Pending source-save timestamp is invalid.'}
}
function Get-ForgePendingSourceSaveId([string]$Key) {
    $lc=Get-LocalCoreConcept $Key
    $pending=Get-PropertyValue $lc 'source_save_intent'
    if($null-eq$pending){return ''}
    Assert-ForgeSourceSaveIntent $pending
    $id=[string](Get-PropertyValue $pending 'intent_id')
    if([string](Get-PropertyValue $pending 'schema')-cne'forge.source_save_intent.v1'-or$id-cnotmatch'^[0-9a-f]{32}$'){throw 'Pending source-save evidence is invalid. Restore or inspect it before continuing.'}
    return $id
}
function Start-ForgeSourceSaveIntent($ProposedBrief) {
    $c=$script:Current.concept;$key=[string]$c.concept_key
    $oldBrief=New-ForgeGenerationBriefSnapshot $c;$oldSha=Get-ForgeBriefSha256 $oldBrief;$newSha=Get-ForgeBriefSha256 $ProposedBrief
    $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept $key $s
    if($null-eq$lc){$null=Ensure-LocalCoreConceptFromCurrent;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept $key $s}
    if($null-ne(Get-PropertyValue $lc 'source_save_intent')){throw 'A previous source save is unresolved. Refresh the saved idea before retrying; no automatic repeat was sent.'}
    if($null-eq$lc-or[string](Get-PropertyValue $lc 'source_revision_id')-cne[string]$c.current_revision_id-or[string](Get-PropertyValue $lc 'source_revision_hash')-cne[string]$c.current_content_hash-or[string](Get-PropertyValue $lc 'generation_brief_sha256')-cne$oldSha-or(Get-ForgeBriefSha256 (Get-PropertyValue $lc 'generation_brief_snapshot'))-cne$oldSha){throw 'The saved source changed. Refresh before saving; nothing was sent.'}
    $intent=[pscustomobject]@{schema='forge.source_save_intent.v1';intent_id=[guid]::NewGuid().ToString('N');created_at=[DateTime]::UtcNow.ToString('o');prior_revision_id=[string]$c.current_revision_id;prior_revision_hash=[string]$c.current_content_hash;prior_brief_sha256=$oldSha;proposed_brief_sha256=$newSha;substantive_change=($newSha-cne$oldSha)}
    Assert-ForgeSourceSaveIntent $intent
    Add-OrSetProperty $lc 'source_save_intent' $intent
    if($intent.substantive_change){$null=Preserve-ForgeLocalReviewHistory $lc 'source_save_started';Add-OrSetProperty $lc 'brief_approval' $null}
    Write-LocalCoreState $s
    return $intent
}
function Get-ForgeLiveReadFrame([string]$Key) {
    $state=Read-LocalCoreState;$record=Get-LocalCoreConcept $Key $state
    return $(if($null-eq$record){'absent'}else{Get-StringSha256Hex ($record|ConvertTo-Json -Depth 60 -Compress)})
}
function Complete-ForgeCoreBriefFrame($Concept,[string]$BriefSha) {
    Add-OrSetProperty $Concept 'core_materialization_pending' $false
    Add-OrSetProperty $Concept 'core_brief_frame' ([pscustomobject]@{schema='forge.core_brief_frame.v1';revision_id=[string]$Concept.current_revision_id;revision_hash=[string]$Concept.current_content_hash;brief_sha256=$BriefSha})
}
function Ensure-LocalCoreConceptFromCurrent([string]$VerifiedLiveIntentId='') {
    if($null -eq $script:Current){return $null};$c=Get-PropertyValue $script:Current 'concept';if($null -eq $c){return $null}
    $key=([string](Get-PropertyValue $c 'concept_key')).Trim();if([string]::IsNullOrWhiteSpace($key)){return $null}
    $identity=Get-LocalCurrentRevisionIdentity $c
    Add-OrSetProperty $c 'current_revision_id' $identity.id;Add-OrSetProperty $c 'current_content_hash' $identity.hash
    $s=Read-LocalCoreState;$existing=Get-LocalCoreConcept $key $s
    $pending=Get-PropertyValue $existing 'source_save_intent';$resolvePending=$false
    if($null-ne$pending){
        Assert-ForgeSourceSaveIntent $pending
        if(!$VerifiedLiveIntentId-or[string](Get-PropertyValue $pending 'schema')-cne'forge.source_save_intent.v1'-or[string](Get-PropertyValue $pending 'intent_id')-cne$VerifiedLiveIntentId-or$VerifiedLiveIntentId-cnotmatch'^[0-9a-f]{32}$'){throw 'Source save is unresolved. Reload the saved idea from the connected workspace before deciding or generating.'}
        $resolvePending=$true
    }
    if(Test-CurrentIsResearchDraft){$activeDraft=Get-ResearchDraft $key $s;if($null-eq$activeDraft-or[string](Get-PropertyValue $activeDraft 'status')-cne'draft'){throw (Get-UiText 'local.refresh.missingdraft' 'This local draft is no longer in the saved workspace. Your editor was preserved; select or restore a current draft before deciding or generating.')}}
    if((Get-PropertyValue $c 'offline_materialization_pending')-is[bool]-and(Get-PropertyValue $c 'offline_materialization_pending')){
        $actualRecord=if($null-eq$existing){'absent'}else{Get-StringSha256Hex ($existing|ConvertTo-Json -Depth 60 -Compress)}
        if([string](Get-PropertyValue $c 'offline_prior_record_sha256')-cne$actualRecord){throw (Get-UiText 'offline.brief.changed' 'The saved local full brief changed. Reopen it before deciding or exporting.')}
    }
    if([string](Get-PropertyValue $c 'offline_brief_basis')-ceq'saved_local_brief'){
        $expectedBrief=[string](Get-PropertyValue $c 'offline_saved_brief_sha256')
        if($expectedBrief-cnotmatch'^[0-9a-f]{64}$'-or$null-eq$existing-or[string](Get-PropertyValue $existing 'generation_brief_sha256')-cne$expectedBrief-or[string](Get-PropertyValue $existing 'source_revision_id')-cne$identity.id-or[string](Get-PropertyValue $existing 'source_revision_hash')-cne$identity.hash-or(Get-ForgeBriefSha256 (Get-PropertyValue $existing 'generation_brief_snapshot'))-cne$expectedBrief-or(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $c))-cne$expectedBrief){throw (Get-UiText 'offline.brief.changed' 'The saved local full brief changed. Reopen the current saved version before deciding or exporting.')}
    }
    $liveRead=(Get-PropertyValue $c 'core_materialization_pending')-is[bool]-and(Get-PropertyValue $c 'core_materialization_pending')
    $frame=Get-PropertyValue $c 'core_brief_frame'
    if($liveRead){
        $actualRecord=if($null-eq$existing){'absent'}else{Get-StringSha256Hex ($existing|ConvertTo-Json -Depth 60 -Compress)}
        if([string](Get-PropertyValue $c 'core_prior_record_sha256')-cne$actualRecord){throw 'The saved idea changed while loading. Refresh before deciding; the newer version was preserved.'}
    } elseif(Test-CurrentIsResearchDraft){
        $savedConcept=ConvertTo-ResearchDraftConcept $activeDraft
        if($identity.id-cne[string]$savedConcept.current_revision_id-or$identity.hash-cne[string]$savedConcept.current_content_hash-or(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $c))-cne(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $savedConcept))){throw 'The saved draft changed. Reopen its current full brief before deciding.'}
    } elseif($null-ne$frame){
        if([string](Get-PropertyValue $frame 'schema')-cne'forge.core_brief_frame.v1'-or$null-eq$existing-or[string](Get-PropertyValue $existing 'source_revision_id')-cne[string](Get-PropertyValue $frame 'revision_id')-or[string](Get-PropertyValue $existing 'source_revision_hash')-cne[string](Get-PropertyValue $frame 'revision_hash')-or[string](Get-PropertyValue $existing 'generation_brief_sha256')-cne[string](Get-PropertyValue $frame 'brief_sha256')-or(Get-ForgeBriefSha256 (Get-PropertyValue $existing 'generation_brief_snapshot'))-cne[string](Get-PropertyValue $frame 'brief_sha256')){throw 'The open idea is older than the saved full brief. Refresh before deciding; the newer version was preserved.'}
    } elseif($null-ne$existing-and!((Get-PropertyValue $c 'offline_materialization_pending')-is[bool]-and(Get-PropertyValue $c 'offline_materialization_pending'))){
        $visibleSha=Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $c)
        if([string](Get-PropertyValue $existing 'source_revision_id')-cne$identity.id-or[string](Get-PropertyValue $existing 'source_revision_hash')-cne$identity.hash-or[string](Get-PropertyValue $existing 'generation_brief_sha256')-cne$visibleSha-or(Get-ForgeBriefSha256 (Get-PropertyValue $existing 'generation_brief_snapshot'))-cne$visibleSha){throw 'The source of this open idea is unverified. Reload its full saved brief before deciding.'}
    }
    $beforeJson=if($null-ne$existing){ConvertTo-Json -InputObject $existing -Depth 60 -Compress}else{''}
    foreach($draft in @((Get-PropertyValue $s 'research_drafts'))){if([string](Get-PropertyValue $draft 'concept_key') -eq $key -and ([string](Get-PropertyValue $draft 'current_revision_id') -ne $identity.id -or [string](Get-PropertyValue $draft 'current_revision_hash') -ne $identity.hash)){throw 'The draft changed in another window. Reopen it before approving or generating.'}}
    $brief=New-ForgeGenerationBriefSnapshot $c;$briefSha=Get-ForgeBriefSha256 $brief
    if($null -eq $existing){
        $existing=[pscustomobject]@{concept_key=$key;title=[string](Get-PropertyValue $c 'title');hook=[string](Get-PropertyValue $c 'hook');niche_name=[string](Get-PropertyValue $c 'niche_name');concept_text=[string](Get-PropertyValue $c 'concept_text');visual_direction_text=[string](Get-PropertyValue $c 'visual_direction_text');source_revision_id=$identity.id;source_revision_hash=$identity.hash;owner_decision='UNDECIDED';owner_decision_revision_id=$identity.id;owner_decision_revision_hash=$identity.hash;owner_decision_at='';artwork=@();active_acceptance=$null;checks=(New-LocalCoreChecks $identity.id);publication=$null;packages=@()}
        $s.concepts=@($s.concepts)+@($existing)
    } else {
        $oldId=[string](Get-PropertyValue $existing 'source_revision_id');$oldHash=[string](Get-PropertyValue $existing 'source_revision_hash')
        $oldBriefSha=[string](Get-PropertyValue $existing 'generation_brief_sha256');$revisionChanged=(($oldId -and $oldId -ne $identity.id) -or ($oldHash -and $oldHash -ne $identity.hash) -or ($oldBriefSha -and $oldBriefSha -ne $briefSha))
        if($revisionChanged){$null=Preserve-ForgeLocalReviewHistory $existing 'concept_revision_changed'}
        foreach($pair in @(@('title','title'),@('hook','hook'),@('niche_name','niche_name'),@('concept_text','concept_text'),@('visual_direction_text','visual_direction_text'))){$v=[string](Get-PropertyValue $c $pair[1]);if(-not [string]::IsNullOrWhiteSpace($v)){Add-OrSetProperty $existing $pair[0] $v}}
        Add-OrSetProperty $existing 'source_revision_id' $identity.id;Add-OrSetProperty $existing 'source_revision_hash' $identity.hash
        if($null -eq $existing.PSObject.Properties['artwork']){$existing|Add-Member -NotePropertyName artwork -NotePropertyValue @() -Force};if($null -eq $existing.PSObject.Properties['packages']){$existing|Add-Member -NotePropertyName packages -NotePropertyValue @() -Force}
        if($null -eq $existing.PSObject.Properties['owner_decision']){Add-OrSetProperty $existing 'owner_decision' 'UNDECIDED'}
        if($null -eq $existing.PSObject.Properties['owner_decision_revision_id']){Add-OrSetProperty $existing 'owner_decision_revision_id' $identity.id}
        if($null -eq $existing.PSObject.Properties['owner_decision_revision_hash']){Add-OrSetProperty $existing 'owner_decision_revision_hash' $identity.hash}
        if($null -eq $existing.PSObject.Properties['owner_decision_at']){Add-OrSetProperty $existing 'owner_decision_at' ''}
        if($revisionChanged){
            Add-OrSetProperty $existing 'brief_approval' $null
            foreach($a in @($existing.artwork)){$a.accepted=$false};$existing.active_acceptance=$null;$existing.checks=New-LocalCoreChecks $identity.id;$existing.publication=$null;Invalidate-LocalCorePackages $existing 'concept_revision_changed';Add-OrSetProperty $existing 'owner_decision' 'UNDECIDED';Add-OrSetProperty $existing 'owner_decision_revision_id' $identity.id;Add-OrSetProperty $existing 'owner_decision_revision_hash' $identity.hash;Add-OrSetProperty $existing 'owner_decision_at' ''
        } else {
            if($null -eq $existing.PSObject.Properties['checks']){$existing|Add-Member -NotePropertyName checks -NotePropertyValue (New-LocalCoreChecks $identity.id) -Force}
            $defaults=New-LocalCoreChecks $identity.id;foreach($n in @('ip','visual','print','policy','metadata')){if($null -eq $existing.checks.PSObject.Properties[$n]){$existing.checks|Add-Member -NotePropertyName $n -NotePropertyValue (Get-PropertyValue $defaults $n) -Force}}
        }
    }
    if($resolvePending){Add-OrSetProperty $existing 'source_save_intent' $null}
    Add-OrSetProperty $existing 'generation_brief_snapshot' $brief;Add-OrSetProperty $existing 'generation_brief_sha256' $briefSha
    if($beforeJson-and$beforeJson-ceq(ConvertTo-Json -InputObject $existing -Depth 60 -Compress)){
        # Preserve the optimistic concurrency check without incrementing the global
        # state revision for an unchanged display/read operation.
        $latest=Read-LocalCoreState
        if([string](Get-PropertyValue $latest 'state_revision')-cne[string](Get-PropertyValue $s 'state_revision')-or[string](Get-PropertyValue $latest 'last_write_id')-cne[string](Get-PropertyValue $s 'last_write_id')){throw 'Local Forge state changed in another window. Nothing was overwritten; refresh and try again.'}
        Complete-ForgeOfflineBriefFrame $c $briefSha;Complete-ForgeCoreBriefFrame $c $briefSha;return $existing
    }
    Write-LocalCoreState $s;Complete-ForgeOfflineBriefFrame $c $briefSha;Complete-ForgeCoreBriefFrame $c $briefSha;return $existing
}
function Get-LocalOwnerDecisionRecord([string]$ConceptKey,$Concept=$null,$State=$null) {
    $key=([string]$ConceptKey).Trim();if([string]::IsNullOrWhiteSpace($key)){return [pscustomobject]@{decision='UNDECIDED';revision_id='';revision_hash='';decided_at='';is_current=$false}}
    if($null-eq$State){$State=Read-LocalCoreState};$lc=Get-LocalCoreConcept $key $State;if($null-eq$lc){return [pscustomobject]@{decision='UNDECIDED';revision_id='';revision_hash='';decided_at='';is_current=$false}}
    if($null-eq$Concept -and $null-ne$script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq $key){$Concept=$script:Current.concept}
    $currentIdentity=if($null-ne$Concept){Get-LocalCurrentRevisionIdentity $Concept}else{[pscustomobject]@{id=[string](Get-PropertyValue $lc 'source_revision_id');hash=[string](Get-PropertyValue $lc 'source_revision_hash')}}
    $visibleRevisionCurrent=$true
    $savedDraft=Get-ResearchDraft $key $State
    if($null-ne$savedDraft){
        if($null-ne$Concept){$visibleRevisionCurrent=($currentIdentity.id-ceq$savedDraft.current_revision_id-and$currentIdentity.hash-ceq$savedDraft.current_revision_hash)}
        $currentIdentity=[pscustomobject]@{id=$savedDraft.current_revision_id;hash=$savedDraft.current_revision_hash}
    }
    $decision=([string](Get-PropertyValue $lc 'owner_decision')).Trim().ToUpperInvariant();if($decision -notin @('KEEP','EDIT','REGEN','SKIP')){$decision='UNDECIDED'}
    $rid=([string](Get-PropertyValue $lc 'owner_decision_revision_id')).Trim();$rhash=([string](Get-PropertyValue $lc 'owner_decision_revision_hash')).Trim().ToLowerInvariant();$isCurrent=(-not[string]::IsNullOrWhiteSpace($rid) -and -not[string]::IsNullOrWhiteSpace($rhash) -and $rid -eq [string]$currentIdentity.id -and $rhash -eq ([string]$currentIdentity.hash).ToLowerInvariant())
    $isCurrent=$isCurrent-and$visibleRevisionCurrent
    if(-not$isCurrent){$decision='UNDECIDED'}
    return [pscustomobject]@{decision=$decision;revision_id=$rid;revision_hash=$rhash;decided_at=[string](Get-PropertyValue $lc 'owner_decision_at');is_current=$isCurrent}
}
function Set-LocalOwnerDecision([string]$Decision) {
    if($null-eq$script:Current){Show-Error 'Choose an idea first.';return $false}
    if($script:Dirty){Show-Error 'Save or discard creative edits before choosing a decision for this revision.';return $false}
    $d=([string]$Decision).Trim().ToUpperInvariant();if($d -notin @('KEEP','EDIT','REGEN','SKIP','UNDECIDED')){Show-Error 'Invalid owner decision.';return $false}
    try {
        $null=Ensure-LocalCoreConceptFromCurrent;$key=[string](Get-PropertyValue $script:Current.concept 'concept_key');$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept $key $s;if($null-eq$lc){throw 'Local concept state is unavailable.'}
        if([string](Get-PropertyValue $lc 'owner_decision')-cne$d){$null=Preserve-ForgeLocalReviewHistory $lc 'owner_decision_changed'}
        Add-OrSetProperty $lc 'owner_decision' $d;Add-OrSetProperty $lc 'owner_decision_revision_id' $identity.id;Add-OrSetProperty $lc 'owner_decision_revision_hash' $identity.hash;Add-OrSetProperty $lc 'owner_decision_at' $(if($d-eq'UNDECIDED'){''}else{[DateTime]::UtcNow.ToString('o')})
        if($d -ne 'KEEP'){Add-OrSetProperty $lc 'brief_approval' $null;Invalidate-LocalCorePackages $lc 'idea_and_design_approval_revoked'}
        Write-LocalCoreState $s
        try{Update-OwnerDecisionControls}catch{}
        Refresh-StageFilterIfActive
        if($null-ne$StatusText){$StatusText.Text=if($d-eq'UNDECIDED'){'Owner decision cleared.'}else{('Owner decision saved locally: '+$d)}}
        return $true
    } catch {Show-Error ('Owner decision was not saved: '+$_.Exception.Message);return $false}
}
function Assert-LocalGenerationBriefApproved($Concept=$null) {
    if($null -eq $Concept -and $null -ne $script:Current){$Concept=$script:Current.concept}
    $dirty=Get-Variable -Name Dirty -Scope Script -ErrorAction SilentlyContinue
    if($null -ne $dirty -and [bool]$dirty.Value){throw 'Save the edited brief and approve that revision before generation.'}
    if($null -eq $Concept){throw 'Choose an idea first.'}
    if([bool](Get-PropertyValue $Concept 'current_revision_accepted')){throw 'Accepted revisions are frozen. Start a new iteration before generating again.'}
    $identity=Get-LocalCurrentRevisionIdentity $Concept;$brief=New-ForgeGenerationBriefSnapshot $Concept;$sha=Get-ForgeBriefSha256 $brief
    $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string](Get-PropertyValue $Concept 'concept_key')) $s;$approval=Get-PropertyValue $lc 'brief_approval'
    $check=[pscustomobject]@{concept_key=[string](Get-PropertyValue $Concept 'concept_key');source_revision_id=$identity.id;source_revision_hash=$identity.hash;brief_snapshot=$brief;brief_sha256=$sha;brief_approval=$approval;prompt=(Get-ForgeGenerationBriefPrompt $brief)}
    Assert-ForgeGenerationJobBriefApproval $check $s
    return [pscustomobject]@{brief=$brief;sha256=$sha;approval=$approval;identity=$identity}
}
function Show-LocalGenerationBriefApprovalDialog([string]$Summary,[string]$Title) {
    # A MessageBox cannot display a complete 32k brief reliably. This modal is scrollable;
    # the main workbench layout stays unchanged, and Close/Escape never grants approval.
    [xml]$markup=@'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Width="780" Height="720" MinWidth="420" MinHeight="300" WindowStartupLocation="CenterOwner" ShowInTaskbar="False" Background="#17191D" Foreground="#F5F5F5">
  <Grid Margin="20">
    <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
    <TextBox x:Name="BriefReviewText" IsReadOnly="True" AcceptsReturn="True" TextWrapping="Wrap" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled" Background="#202329" Foreground="#F5F5F5" BorderBrush="#4A4D54" Padding="12" FontSize="14"/>
    <WrapPanel Grid.Row="1" HorizontalAlignment="Right" Margin="0,16,0,0">
      <Button x:Name="CancelBriefApproval" MinWidth="110" Padding="14,8" Margin="0,0,12,0" IsCancel="True"/>
      <Button x:Name="ApproveBrief" MinWidth="160" Padding="14,8" Background="#F08A35" Foreground="#17191D"/>
    </WrapPanel>
  </Grid>
</Window>
'@
    $reader=New-Object System.Xml.XmlNodeReader $markup
    try{$dialog=[Windows.Markup.XamlReader]::Load($reader)}finally{$reader.Close()}
    $dialog.Owner=$Window;$dialog.Title=$Title
    $area=[Windows.SystemParameters]::WorkArea;$dialog.Width=[Math]::Min(780,[Math]::Max(420,$area.Width-40));$dialog.Height=[Math]::Min(720,[Math]::Max(300,$area.Height-40))
    $text=$dialog.FindName('BriefReviewText');$text.Text=$Summary
    $approve=$dialog.FindName('ApproveBrief');$approve.Content=Get-UiText 'brief.approval.approve' 'Approve idea and design'
    $cancel=$dialog.FindName('CancelBriefApproval');$cancel.Content=Get-UiText 'brief.approval.cancel' 'Cancel'
    $cancel.Add_Click({param($sender,$eventArgs) [Windows.Window]::GetWindow($sender).DialogResult=$false})
    $approve.Add_Click({param($sender,$eventArgs) [Windows.Window]::GetWindow($sender).DialogResult=$true})
    return ($dialog.ShowDialog() -eq $true)
}
function Confirm-LocalGenerationBriefApproval {
    if($null -eq $script:Current -or $script:Dirty){throw 'Save the idea and design brief before approving it.'}
    $c=$script:Current.concept;$identity=Get-LocalCurrentRevisionIdentity $c;$brief=New-ForgeGenerationBriefSnapshot $c
    Assert-ForgeGenerationBriefComplete $brief;$null=Get-ForgeGenerationBriefPrompt $brief
    $null=Ensure-LocalCoreConceptFromCurrent
    try{$null=Assert-LocalGenerationBriefApproved $c;return $true}catch{}
    $sha=Get-ForgeBriefSha256 $brief
    $summary=((Get-UiText 'brief.approval.summary' "Approve BOTH the idea and design concept in this complete saved brief?`n`nRevision: {0}`nFull brief SHA-256: {1}`n`n{2}`n`nThis approval applies only to this exact saved content. Any brief edit requires approval again. KEEP alone is not approval. Payment/provider dispatch requires the separate Generate confirmation.") -f $identity.id,$sha,($brief|ConvertTo-Json -Depth 60))
    $lettering=Get-ForgeGenerationBriefLettering $brief
    $reviewText=switch($script:Locale){
        'ru' { @('Планируемая надпись из сохранённого брифа:','Надписи не запрошены.','Сохранённые строки макета имеют приоритет над коротким слоганом.','Проверьте точные слова, регистр и переносы строк. Изменения внесите в редакторе до одобрения.') }
        'es' { @('Texto previsto del brief guardado:','No se ha solicitado texto.','Las líneas guardadas de la composición tienen prioridad sobre el lema corto.','Revisa palabras, mayúsculas y saltos de línea. Edita antes de aprobar si hace falta.') }
        default { @('Planned lettering from the saved brief:','No lettering requested.','Saved layout text lines take priority over the short hook.','Review the exact words, case and line breaks. Make any changes in the editor before approving.') }
    }
    $shownText=if([string]::IsNullOrWhiteSpace($lettering.text)){$reviewText[1]}else{$lettering.text}
    $letteringNote=if($lettering.source-ceq'hierarchy'){$reviewText[2]}else{$reviewText[3]}
    $summary=$reviewText[0]+"`r`n"+$shownText+"`r`n"+$letteringNote+"`r`n`r`n"+$summary
    if(Test-ForgeRecoveryReviewRequired (Get-LocalCoreConcept ([string]$c.concept_key))){$summary=(Get-UiText 'recovery.approval.dialog' 'Workspace data was recovered from an earlier snapshot. Previous approval was not restored. Review the complete saved idea and design below before giving new approval.')+"`r`n`r`n"+$summary}
    if(-not(Show-LocalGenerationBriefApprovalDialog $summary (Get-UiText 'brief.approval.title' 'Approve idea and design brief'))){return $false}
    # The decision is bound to the shown snapshot, never to later UI changes.
    if($script:Dirty -or (Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $script:Current.concept)) -ne $sha){throw 'The brief changed while approval was open. Review it again.'}
    $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string](Get-PropertyValue $c 'concept_key')) $s
    $approval=New-ForgeBriefApprovalRecord $brief $identity.id $identity.hash
    $check=[pscustomobject]@{concept_key=[string](Get-PropertyValue $c 'concept_key');source_revision_id=$identity.id;source_revision_hash=$identity.hash;brief_snapshot=$brief;brief_sha256=$sha;brief_approval=$approval;prompt=(Get-ForgeGenerationBriefPrompt $brief)}
    Add-OrSetProperty $lc 'brief_approval' $approval
    Add-OrSetProperty $lc 'approval_recovery_review_required' $false
    Assert-ForgeGenerationJobBriefApproval $check $s
    Write-LocalCoreState $s
    return $true
}
function Get-LocalOwnerDecisionProgress {
    $total=0;$decided=0;$keep=0;$edit=0;$regen=0;$skip=0;$s=$null
    try{$s=Read-LocalCoreState}catch{return [pscustomobject]@{total=0;decided=0;keep=0;edit=0;regen=0;skip=0}}
    $seen=@{}
    foreach($item in @($script:Queue)){
        $key=([string](Get-PropertyValue $item 'concept_key')).Trim();if([string]::IsNullOrWhiteSpace($key)-or$seen.ContainsKey($key)){continue};$seen[$key]=$true;$total++
        $concept=$null;if($null-ne$script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq $key){$concept=$script:Current.concept}
        $rec=Get-LocalOwnerDecisionRecord $key $concept $s;switch([string]$rec.decision){'KEEP'{$decided++;$keep++};'EDIT'{$decided++;$edit++};'REGEN'{$decided++;$regen++};'SKIP'{$decided++;$skip++}}
    }
    return [pscustomobject]@{total=$total;decided=$decided;keep=$keep;edit=$edit;regen=$regen;skip=$skip}
}
function Get-LocalCoreSafeKey([string]$Text) {
    $v=([string]$Text).Trim();if([string]::IsNullOrWhiteSpace($v)){$v='concept'}
    $v=[regex]::Replace($v,'[^A-Za-z0-9_-]+','_').Trim('_')
    if($v.Length -gt 72){$v=$v.Substring(0,72)}
    if([string]::IsNullOrWhiteSpace($v)){$v='concept'}
    return $v
}
function Get-FileSha256Hex([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Read-ForgeArtworkFileSnapshot([string]$Path,[long]$MaxBytes=134217728) {
    if($MaxBytes-lt1-or$MaxBytes-gt134217728){throw 'Invalid artwork read limit.'}
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop;if($item-isnot[IO.FileInfo]){throw 'Artwork source must be a file.'}
    $stream=[IO.File]::Open($item.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);$memory=New-Object IO.MemoryStream
    try {
        if($stream.Length-lt1){throw 'Artwork file is empty.'};if($stream.Length-gt$MaxBytes){throw 'Artwork exceeds the local 128MiB reading limit. The source was preserved; this limit is not an Amazon upload rule.'}
        $buffer=New-Object byte[] 65536;while(($n=$stream.Read($buffer,0,$buffer.Length))-gt0){if($memory.Length+$n-gt$MaxBytes){throw 'Artwork grew beyond the local reading limit. The source was preserved.'};$memory.Write($buffer,0,$n)}
        $bytes=$memory.ToArray();if($bytes.Length-lt1){throw 'Artwork file is empty.'}
        return [pscustomobject]@{bytes=$bytes;sha256=(Get-ByteSha256Hex $bytes);source_size_bytes=$bytes.Length;source_path=$item.FullName}
    }finally{$memory.Dispose();$stream.Dispose()}
}
function Get-LocalArtworkInfo([string]$Path) {
    $capture=Read-ForgeArtworkFileSnapshot $Path;$bytes=$capture.bytes
    $png=Get-ForgePngMetadata $bytes
    if($png.valid){$mime='image/png';$ext='.png'}
    elseif($bytes.Length-ge3-and$bytes[0]-eq255-and$bytes[1]-eq216-and$bytes[2]-eq255){$mime='image/jpeg';$ext='.jpg'}
    else{throw 'Artwork must contain a decodable PNG or JPEG image. A filename extension does not establish its format.'}
    $bmp=ConvertTo-FrozenBitmapImage $bytes
    return [pscustomobject]@{bytes=$bytes;sha256=$capture.sha256;width_px=$bmp.PixelWidth;height_px=$bmp.PixelHeight;mime_type=$mime;extension=$ext;source_extension=[IO.Path]::GetExtension($Path).ToLowerInvariant()}
}
function Add-LocalArtworkFromPath([string]$Path,[string]$GenerationRequestId='local-import',[string]$ProviderKey='manual_artwork_bridge',[string]$ExpectedRevisionId='',[string]$ExpectedRevisionHash='',[string]$ExpectedAssetSha='',$Provenance=$null) {
    if($null -eq $script:Current){throw 'Choose an idea first.'};if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw 'Artwork file is missing.'};$info=Get-LocalArtworkInfo $Path;if($info.mime_type -notin @('image/png','image/jpeg')){throw 'Only PNG and JPEG artwork are supported.'}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;if($ExpectedRevisionId -and $ExpectedRevisionId -ne $identity.id){throw 'Generated artwork belongs to another revision.'};if($ExpectedRevisionHash -and $ExpectedRevisionHash -ne $identity.hash){throw 'Generated artwork revision hash is stale.'};if($ExpectedAssetSha -and $ExpectedAssetSha.ToLowerInvariant() -ne $info.sha256){throw 'Generated artwork SHA-256 does not match its result manifest.'}
    $null=Ensure-LocalCoreConceptFromCurrent;$state=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $state;$safe=Get-LocalCoreSafeKey $lc.concept_key;$dir=Join-Path $script:LocalCoreArtworkRoot $safe;Ensure-Dir $dir;$dest=Join-Path $dir ($info.sha256+$info.extension);if(-not(Test-Path -LiteralPath $dest)){[IO.File]::WriteAllBytes($dest,$info.bytes)};if((Get-FileSha256Hex $dest) -ne $info.sha256){throw 'Local artwork copy failed SHA-256 verification.'}
    $generationMethod=if($ProviderKey-ceq'manual_artwork_bridge'){'local_import'}elseif($ProviderKey-ceq'local_birefnet_preparation'){'local_preparation'}else{'local_provider_worker'}
    $preparationMetadata=$null;if($ProviderKey-ceq'local_birefnet_preparation'){$preparationMetadata=[pscustomobject]@{source_sha256=[string](Get-PropertyValue $Provenance 'preparation_source_sha256');source_variant_id=[string](Get-PropertyValue $Provenance 'preparation_source_variant_id');source_generation_request_id=[string](Get-PropertyValue $Provenance 'preparation_source_generation_request_id');result_path=[string](Get-PropertyValue $Provenance 'preparation_result_path');model_sha256=[string](Get-PropertyValue $Provenance 'preparation_model_sha256');method='BiRefNet_CPU_alpha_only';owner_approved=$false;print_ready=$false}}
    $requiresRequestLineage=($ProviderKey-cne'manual_artwork_bridge');$existing=$null
    foreach($v in @($lc.artwork)){
        if([string](Get-PropertyValue $v 'asset_sha256')-cne$info.sha256-or[string](Get-PropertyValue $v 'concept_revision_id')-cne$identity.id-or[string](Get-PropertyValue $v 'source_revision_hash')-cne$identity.hash){continue}
        if($requiresRequestLineage-and([string](Get-PropertyValue $v 'generation_request_id')-cne$GenerationRequestId-or[string](Get-PropertyValue $v 'provider_key')-cne$ProviderKey)){continue}
        $existing=$v;break
    }
    if($null -ne $existing -and $null -ne $Provenance){Add-OrSetProperty $existing 'generation_request_id' $GenerationRequestId;Add-OrSetProperty $existing 'provider_key' $ProviderKey;foreach($n in @('provider_profile','provider_model','provider_contract_version','provider_registry_sha256','provider_config_fingerprint','prompt_compiler_version','prompt_template_sha256','provider_request_id','generation_result_sha256','generation_attempt_sha256','prompt_sha256','revised_prompt','provider_usage')){Add-OrSetProperty $existing $n (Get-PropertyValue $Provenance $n)};Add-OrSetProperty $existing 'generation_method' 'local_provider_worker';Add-OrSetProperty $existing 'local_file_path' $dest;Add-OrSetProperty $existing 'local_only' $true;Add-OrSetProperty $existing 'asset_availability' 'available';Add-OrSetProperty $existing 'generation_method' $generationMethod;if($null-ne$preparationMetadata){Add-OrSetProperty $existing 'preparation' $preparationMetadata};Write-LocalCoreState $state}
    if($null -eq $existing){$idx=@($lc.artwork).Count+1;$variantId='local-'+[guid]::NewGuid().ToString('N');$integrity=[pscustomobject]@{state='pass';source='local_integrity';note=("Image decoded successfully; SHA-256 verified; {0}×{1}; {2}." -f $info.width_px,$info.height_px,$info.mime_type);checked_at=[DateTime]::UtcNow.ToString('o');scope='artwork';concept_revision_id=$identity.id;asset_sha256=$info.sha256;listing_hash=''};$existing=[pscustomobject]@{id=$variantId;variant_key=$variantId;variant_index=$idx;status='available';review_state='neutral';review_note='';latest_reason_codes=@();asset_sha256=$info.sha256;preview_key='';concept_revision_id=$identity.id;source_revision_hash=$identity.hash;generation_request_id=$GenerationRequestId;provider_key=$ProviderKey;provider_profile=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_profile')}else{''};provider_model=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_model')}else{''};provider_contract_version=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_contract_version')}else{''};provider_registry_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_registry_sha256')}else{''};provider_config_fingerprint=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_config_fingerprint')}else{''};prompt_compiler_version=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'prompt_compiler_version')}else{''};prompt_template_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'prompt_template_sha256')}else{''};provider_request_id=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_request_id')}else{''};generation_result_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'generation_result_sha256')}else{''};generation_attempt_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'generation_attempt_sha256')}else{''};prompt_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'prompt_sha256')}else{''};revised_prompt=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'revised_prompt')}else{''};provider_usage=if($null-ne$Provenance){Get-PropertyValue $Provenance 'provider_usage'}else{$null};generation_method=$generationMethod;asset_metadata=[pscustomobject]@{preview_health='available';mime_type=$info.mime_type;width_px=$info.width_px;height_px=$info.height_px};asset_availability='available';mime_type=$info.mime_type;width_px=$info.width_px;height_px=$info.height_px;local_file_path=$dest;local_only=$true;accepted=$false;integrity_check=$integrity;created_at=[DateTime]::UtcNow.ToString('o');allowed_actions=[pscustomobject]@{review=$true;accept=$true}};$lc.artwork=@($lc.artwork)+@($existing);if($null-ne$preparationMetadata){Add-OrSetProperty $existing 'preparation' $preparationMetadata};Write-LocalCoreState $state}
    return $existing
}
function Test-LocalProviderArtworkLineage($Variant) {
    return ($null-ne$Variant-and[string](Get-PropertyValue $Variant 'generation_method')-ceq'local_provider_worker'-and[string](Get-PropertyValue $Variant 'provider_key')-cne'local_birefnet_preparation'-and[string](Get-PropertyValue $Variant 'generation_request_id')-cmatch'^gen-[0-9a-f]{32}$')
}
function New-LocalVariantDisplay($Variant) {
    # The variant list UI (Format-Variant, Format-VariantAdvanced, Update-VariantSelection) reads server-variant fields
    # directly; under StrictMode a missing field throws on selection. Give local artwork neutral values for all of them.
    $defaults=[ordered]@{status='available';review_state='neutral';review_note='';latest_reason_codes=@();variant_key=[string](Get-PropertyValue $Variant 'id');preview_key='';generation_request_id='';stale_revision=$false;created_at=[string](Get-PropertyValue $Variant 'imported_at');asset_metadata=[pscustomobject]@{mime_type=[string](Get-PropertyValue $Variant 'mime_type');width_px=(Get-PropertyValue $Variant 'width_px');height_px=(Get-PropertyValue $Variant 'height_px');source='local'}}
    foreach($k in $defaults.Keys){if($null -eq $Variant.PSObject.Properties[$k]){$Variant|Add-Member -NotePropertyName $k -NotePropertyValue $defaults[$k] -Force}}
    $Variant|Add-Member -NotePropertyName display -NotePropertyValue ("Local artwork {0} · {1}×{2} · {3}" -f (Get-PropertyValue $Variant 'variant_index'),(Get-PropertyValue $Variant 'width_px'),(Get-PropertyValue $Variant 'height_px'),$(if([bool](Get-PropertyValue $Variant 'accepted')){'accepted'}else{'review'})) -Force
    return $Variant
}
function Get-LocalCoreVariantsForCurrent {
    if($null -eq $script:Current){return @()};$c=$script:Current.concept;$key=[string](Get-PropertyValue $c 'concept_key');$identity=Get-LocalCurrentRevisionIdentity $c;$lc=Get-LocalCoreConcept $key
    $out=@();foreach($v in @((Get-PropertyValue $lc 'artwork'))){if([string](Get-PropertyValue $v 'concept_revision_id') -eq $identity.id){$out+=New-LocalVariantDisplay $v}};return @($out)
}
function Refresh-LocalArtworkUi {
    if($null -eq $VariantList){return}
    try{$null=Sync-LocalGenerationResults}catch{Write-AppLog 'WARN' ('Local generation sync: '+$_.Exception.Message)}
    $vars=@(Get-LocalCoreVariantsForCurrent);$VariantList.ItemsSource=$vars
    try{$GenerationRequestList.ItemsSource=@(Get-LocalGenerationJobsForCurrent)}catch{$GenerationRequestList.ItemsSource=$null}
    if($vars.Count -gt 0){$GenerationStatus.Text=("Local artwork: {0} file(s)." -f $vars.Count);$VariantPreview.Text='Select local artwork.'}
    else{$GenerationStatus.Text=if(Test-LocalProductionProviderReady){'Production image provider ready. Use Generate, then revisit Artwork or Refresh to import completed variants.'}else{'No local artwork yet. Export the generation brief or import a finished PNG/JPG.'};$VariantPreview.Text='No local artwork imported.'}
    $VariantImageA.Source=$null;$VariantImageB.Source=$null
    $VariantImageStatusA.Text='Select local artwork';$VariantImageStatusA.Visibility='Visible';$VariantImageStatusB.Text='Select a second artwork';$VariantImageStatusB.Visibility='Visible'
    if($null -ne $LocalAcceptButton){$LocalAcceptButton.IsEnabled=$false}
    Update-LocalCoreStatusUi
}
function Write-ForgeGenerationBriefDocument([string]$Path,[string]$Text) {
    $bytes=[Text.Encoding]::UTF8.GetBytes($Text);$stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    if((Get-FileSha256Hex $Path)-cne(Get-ByteSha256Hex $bytes)){throw 'Generation brief document write could not be verified.'}
}
function Commit-ForgeGenerationBriefDocuments([string]$Stage,[string]$Destination,[string]$Root) {
    $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\')+'\';$stageFull=[IO.Path]::GetFullPath($Stage);$targetFull=[IO.Path]::GetFullPath($Destination)
    if(!$stageFull.StartsWith($rootFull,[StringComparison]::OrdinalIgnoreCase)-or!$targetFull.StartsWith($rootFull,[StringComparison]::OrdinalIgnoreCase)-or$stageFull-eq$targetFull-or(Test-Path -LiteralPath $targetFull)){throw 'Unsafe or existing generation brief destination; original files were preserved.'}
    $files=@(Get-ChildItem -LiteralPath $stageFull -Force)
    if($files.Count-ne2-or@($files|Where-Object{$_.PSIsContainer-or($_.Attributes-band[IO.FileAttributes]::ReparsePoint)-or$_.Name-notin@('generation-brief.json','generation-brief.txt')}).Count){throw 'Incomplete generation brief pair; staged files were preserved.'}
    [IO.Directory]::Move($stageFull,$targetFull)
}

function Export-LocalGenerationBrief {
    if($null -eq $script:Current){Show-Error 'Choose an idea first.';return};$lc=Ensure-LocalCoreConceptFromCurrent;if($null -eq $lc){Show-Error 'Local concept state could not be prepared.';return}
    $c=$script:Current.concept;$identity=Get-LocalCurrentRevisionIdentity $c;$key=Get-LocalCoreSafeKey ([string]$c.concept_key);$dir=Join-Path $script:LocalCoreExportRoot $key;Ensure-Dir $dir
    $brief=[ordered]@{schema='forge.local_generation_brief.v2';created_at=[DateTime]::UtcNow.ToString('o');concept_key=[string]$c.concept_key;title=[string]$c.title;hook=[string]$c.hook;niche_name=[string](Get-PropertyValue $c 'niche_name');concept=[string](Get-PropertyValue $c 'concept_text');visual_direction=[string](Get-PropertyValue $c 'visual_direction_text');source_revision_id=$identity.id;source_revision_hash=$identity.hash;provider_mode=$script:LocalGenerationProviderMode;external_generation_authorized=$false;note='Creative brief only. Import the finished image back into Merch Forge; exact SHA/revision binding is required before acceptance.'}
    $brief['brief_snapshot']=New-ForgeGenerationBriefSnapshot $c;$brief['brief_sha256']=Get-ForgeBriefSha256 $brief.brief_snapshot
    $token=[guid]::NewGuid().ToString('N');$stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss');$stage=Join-Path $dir ('pending-generation-brief-'+$token);$destination=Join-Path $dir ('generation-brief-'+$stamp+'-'+$token)
    try {
    if(Test-Path -LiteralPath $stage){throw 'Generation brief staging path already exists.'};Ensure-Dir $stage
    $jsonPath=Join-Path $stage 'generation-brief.json';$txtPath=Join-Path $stage 'generation-brief.txt'
    Write-ForgeGenerationBriefDocument $jsonPath ($brief|ConvertTo-Json -Depth 60);$txt=@('MERCH FORGE — GENERATION BRIEF','',"Title: $($brief.title)","Hook: $($brief.hook)","Niche: $($brief.niche_name)",'',"Revision: $($brief.source_revision_id)","Revision SHA256: $($brief.source_revision_hash)",'','Concept:',"$($brief.concept)",'','Visual direction:',"$($brief.visual_direction)",'','Complete saved brief (including production spec):',($brief.brief_snapshot|ConvertTo-Json -Depth 60),'','Boundary: creative brief only; no provider dispatch or publishing was authorized.') -join "`r`n";Write-ForgeGenerationBriefDocument $txtPath $txt;Commit-ForgeGenerationBriefDocuments $stage $destination $dir;$txtPath=Join-Path $destination 'generation-brief.txt'
    $StatusText.Text=('Generation brief saved locally: '+$txtPath);if($null -ne $LocalCoreStatusText){$LocalCoreStatusText.Text='Generation brief prepared. Import the resulting artwork for exact review.'}
    }catch{
        $exportError=$_.Exception.Message;$committed=$false
        try{
            $finalJson=Join-Path $destination 'generation-brief.json';$finalText=Join-Path $destination 'generation-brief.txt'
            if((Test-Path -LiteralPath $finalJson -PathType Leaf)-and(Test-Path -LiteralPath $finalText -PathType Leaf)){
                $committed=((Get-FileSha256Hex $finalJson)-ceq(Get-StringSha256Hex ($brief|ConvertTo-Json -Depth 60))-and(Get-FileSha256Hex $finalText)-ceq(Get-StringSha256Hex $txt))
            }
        }catch{$committed=$false}
        if($committed){$StatusText.Text='Generation brief saved locally: '+$finalText;Write-AppLog 'WARN' ('Brief commit verified after an uncertain return: '+$exportError);return}
        $message='A complete generation brief export could not be verified. Previous exports were preserved. Inspect pending and destination paths: '+$stage+'; '+$destination+'; '+$exportError
        $StatusText.Text=$message;Show-Error $message
    }
}
function Import-LocalArtwork {
    if($null -eq $script:Current){Show-Error 'Choose an idea first.';return};$dlg=New-Object Microsoft.Win32.OpenFileDialog;$dlg.Title='Import artwork into Merch Forge';$dlg.Filter='Artwork (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg';$dlg.Multiselect=$false;if($dlg.ShowDialog() -ne $true){return}
    try{$null=Add-LocalArtworkFromPath $dlg.FileName 'local-import' 'manual_artwork_bridge';Refresh-LocalArtworkUi;$StatusText.Text='Artwork imported locally and SHA-256 verified for the current revision.'}catch{Show-Error $_.Exception.Message;$StatusText.Text='Artwork import failed.'}
}
function Get-ForgeLocalAcceptanceTarget($Variant,$State) {
    if($null-eq$script:Current-or$script:Dirty){throw 'Save or discard creative edits before accepting exact artwork.'}
    $c=$script:Current.concept;$identity=Get-LocalCurrentRevisionIdentity $c;$lc=Get-LocalCoreConcept ([string]$c.concept_key) $State
    $visibleSha=Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $c)
    if($null-eq$lc-or$null-ne(Get-PropertyValue $lc 'source_save_intent')-or[string](Get-PropertyValue $lc 'source_revision_id')-cne$identity.id-or[string](Get-PropertyValue $lc 'source_revision_hash')-cne$identity.hash-or[string](Get-PropertyValue $lc 'generation_brief_sha256')-cne$visibleSha-or(Get-ForgeBriefSha256 (Get-PropertyValue $lc 'generation_brief_snapshot'))-cne$visibleSha){throw 'The saved full brief changed. Refresh the idea before accepting artwork.'}
    if(Test-CurrentIsResearchDraft){$draft=Get-ResearchDraft ([string]$c.concept_key) $State;if($null-eq$draft-or[string](Get-PropertyValue $draft 'status')-cne'draft'){throw 'The saved draft is unavailable.'};$saved=ConvertTo-ResearchDraftConcept $draft;if($identity.id-cne[string]$saved.current_revision_id-or$identity.hash-cne[string]$saved.current_content_hash-or$visibleSha-cne(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $saved))){throw 'The saved research draft changed. Reopen it before accepting artwork.'}}
    if((Get-PropertyValue $Variant 'local_only')-isnot[bool]-or!(Get-PropertyValue $Variant 'local_only')){throw 'Select a verified local artwork record.'}
    $id=Get-PropertyValue $Variant 'id';if($id-isnot[string]-or![string]$id){throw 'The selected artwork identity is invalid.'}
    $rows=@((Get-PropertyValue $lc 'artwork')|Where-Object{[string](Get-PropertyValue $_ 'id')-ceq$id-and[string](Get-PropertyValue $_ 'concept_revision_id')-ceq$identity.id-and[string](Get-PropertyValue $_ 'source_revision_hash')-ceq$identity.hash})
    if($rows.Count-ne1){throw 'The selected artwork is missing or ambiguous in the saved workspace. Refresh Artwork before accepting.'}
    $row=$rows[0]
    if((Get-PropertyValue $row 'local_only')-isnot[bool]-or!(Get-PropertyValue $row 'local_only')){throw 'The saved artwork is not a verified local record.'}
    foreach($field in @('id','asset_sha256','local_file_path','concept_revision_id','source_revision_hash')){
        $value=Get-PropertyValue $Variant $field;$saved=Get-PropertyValue $row $field
        if($value-isnot[string]-or$saved-isnot[string]-or$value-cne$saved){throw 'The selected artwork record changed. Refresh Artwork before accepting.'}
    }
    if([string]$row.concept_revision_id-cne$identity.id-or[string]$row.source_revision_hash-cne$identity.hash-or[string]$row.asset_sha256-cnotmatch'^[0-9a-f]{64}$'){throw 'The selected artwork belongs to another saved revision.'}
    $file=Get-Item -LiteralPath ([string]$row.local_file_path) -Force -ErrorAction Stop
    if($file.PSIsContainer-or($file.Attributes-band[IO.FileAttributes]::ReparsePoint)-or(Get-FileSha256Hex $file.FullName)-cne[string]$row.asset_sha256){throw 'The selected exact artwork file changed or is unavailable.'}
    $frame=[ordered]@{revision_id=$identity.id;revision_hash=$identity.hash;brief_sha256=$visibleSha;artwork=$row;active_acceptance=(Get-PropertyValue $lc 'active_acceptance')}
    return [pscustomobject]@{concept=$lc;variant=$row;identity=$identity;frame_sha256=(Get-StringSha256Hex (ConvertTo-Json -InputObject $frame -Depth 60 -Compress))}
}
function Set-LocalExactAcceptance($Variant,[bool]$SkipOwnerConfirm=$false) {
    $target=Get-ForgeLocalAcceptanceTarget $Variant (Read-LocalCoreState)
    if($null -eq $script:Current){throw 'Choose an idea first.'};$v=$Variant;if($null -eq $v){throw 'Select exactly one local artwork file first.'};if(-not [bool](Get-PropertyValue $v 'local_only')){throw 'Use the normal Accept action for server-managed variants.'}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;if([string](Get-PropertyValue $v 'concept_revision_id') -ne $identity.id -or [string](Get-PropertyValue $v 'source_revision_hash') -ne $identity.hash){throw 'This artwork belongs to another idea revision. Import artwork for the current revision.'}
    $sha=[string](Get-PropertyValue $v 'asset_sha256');$path=[string](Get-PropertyValue $v 'local_file_path');if($sha -notmatch '^[0-9a-f]{64}$' -or -not(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileSha256Hex $path) -ne $sha){throw 'Local artwork failed exact-file verification.'}
    if(-not $SkipOwnerConfirm){if(-not(Confirm ("Accept this exact local artwork?`n`nSHA-256: {0}`nRevision: {1}`n`nThis creates LOCAL acceptance only." -f $sha,$identity.id) 'Accept local artwork')){return $false}}
    $s=Read-LocalCoreState;$fresh=Get-ForgeLocalAcceptanceTarget $Variant $s
    if($fresh.frame_sha256-cne$target.frame_sha256){throw 'The idea, selected file or acceptance changed while confirming. The newer saved choice was preserved; refresh before accepting again.'}
    $lc=$fresh.concept;$v=$fresh.variant;$null=Preserve-ForgeLocalReviewHistory $lc 'artwork_acceptance_changed';foreach($x in @($lc.artwork)){$x.accepted=([string]$x.asset_sha256 -eq $sha -and [string]$x.concept_revision_id -eq $identity.id)}
    $fp=New-LocalAcceptanceFingerprint ([string]$lc.concept_key) $identity.id $identity.hash $sha;$providerKey=([string](Get-PropertyValue $v 'provider_key')).Trim();if([string]::IsNullOrWhiteSpace($providerKey)){$providerKey='manual_artwork_bridge'};$lc.active_acceptance=[pscustomobject]@{concept_key=[string]$lc.concept_key;concept_revision_id=$identity.id;revision_hash=$identity.hash;variant_id=[string]$v.id;asset_sha256=$sha;local_file_path=$path;accepted_at=[DateTime]::UtcNow.ToString('o');lineage_fingerprint=$fp;sync_state='local_only';source=if($providerKey-eq'manual_artwork_bridge'){'local_artwork_import'}else{'local_provider_worker'};provider_key=$providerKey;generation_request_id=[string](Get-PropertyValue $v 'generation_request_id');provider_profile=[string](Get-PropertyValue $v 'provider_profile');provider_model=[string](Get-PropertyValue $v 'provider_model');provider_contract_version=[string](Get-PropertyValue $v 'provider_contract_version');provider_registry_sha256=[string](Get-PropertyValue $v 'provider_registry_sha256');provider_config_fingerprint=[string](Get-PropertyValue $v 'provider_config_fingerprint');prompt_compiler_version=[string](Get-PropertyValue $v 'prompt_compiler_version');prompt_template_sha256=[string](Get-PropertyValue $v 'prompt_template_sha256');provider_request_id=[string](Get-PropertyValue $v 'provider_request_id');generation_result_sha256=[string](Get-PropertyValue $v 'generation_result_sha256');generation_attempt_sha256=[string](Get-PropertyValue $v 'generation_attempt_sha256');prompt_sha256=[string](Get-PropertyValue $v 'prompt_sha256');revised_prompt=[string](Get-PropertyValue $v 'revised_prompt');provider_usage=(Get-PropertyValue $v 'provider_usage')}
    Add-OrSetProperty $lc.active_acceptance 'preparation' (Get-PropertyValue $v 'preparation');$oldIp=Get-PropertyValue $lc.checks 'ip';$lc.checks=New-LocalCoreChecks $identity.id $sha
    if($null -ne $oldIp -and [string](Get-PropertyValue $oldIp 'concept_revision_id') -eq $identity.id -and (Test-LocalCheckPass $oldIp $lc 'ip')){$lc.checks.ip=$oldIp}
    $lc.checks.visual=[pscustomobject]@{state='pass';source='owner_exact_accept';note='Owner explicitly reviewed and accepted this exact artwork; the local file decoded successfully and its SHA-256 was verified before acceptance.';checked_at=[DateTime]::UtcNow.ToString('o');scope='artwork';concept_revision_id=$identity.id;asset_sha256=$sha;listing_hash='';authority_kind='owner_exact_accept';evidence_refs=@(('sha256:'+$sha));evidence_source_file_sha256='';evidence_schema='forge.owner_exact_accept.v1'}
    if($null -ne $lc.publication){Add-OrSetProperty $lc.publication 'concept_revision_id' $identity.id;Add-OrSetProperty $lc.publication 'accepted_artwork_sha256' $sha;Add-OrSetProperty $lc.publication 'acceptance_fingerprint' $fp;Add-OrSetProperty $lc.publication 'content_hash' (Get-LocalPublicationHash $lc.publication)}
    Invalidate-LocalCorePackages $lc 'accepted_artwork_changed';Write-LocalCoreState $s;try{$null=Write-LocalCheckRequestBundle}catch{Write-AppLog 'WARN' ('Check request export after Accept failed: '+$_.Exception.Message)};try{$null=Invoke-LocalCheckAutomation}catch{Write-AppLog 'WARN' ('Local check automation after Accept failed: '+$_.Exception.Message)};return $true
}
function Accept-LocalArtwork {
    if($null -eq $script:Current){return};$sel=@($VariantList.SelectedItems);if($sel.Count -ne 1){Show-Error 'Select exactly one local artwork file first.';return}
    try{if(Set-LocalExactAcceptance $sel[0] $false){Refresh-LocalArtworkUi;Refresh-StageFilterIfActive;$StatusText.Text='Exact local artwork accepted for the current revision. Downstream checks were rebound fail-closed.'}}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local artwork acceptance failed.'}
}
function New-LocalCheckAttestationBinding($Lc,$Identity,$Profile) {
    $acc=Get-PropertyValue $Lc 'active_acceptance'
    return [pscustomobject][ordered]@{concept_key=[string](Get-PropertyValue $Lc 'concept_key');revision_id=[string]$Identity.id;revision_hash=([string]$Identity.hash).ToLowerInvariant();artwork_sha256=([string](Get-PropertyValue $acc 'asset_sha256')).ToLowerInvariant();acceptance_fingerprint=[string](Get-PropertyValue $acc 'lineage_fingerprint');listing_hash=(Get-LocalPublicationHash (Get-PropertyValue $Lc 'publication'));profile_fingerprint=[string](Get-PropertyValue $Profile 'profile_fingerprint');marketplace=[string](Get-PropertyValue $Profile 'marketplace');product_type_key=[string](Get-PropertyValue $Profile 'product_type_key');template_key=[string](Get-PropertyValue $Profile 'template_key')}
}
function Get-LocalCheckAttestationBinding {
    if($null-eq$script:Current){throw 'Choose an idea first.'};$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) (Read-LocalCoreState)
    if($null-eq$lc-or$null-eq$lc.active_acceptance){throw 'Accept exact artwork for this idea first.'}
    if([string]$lc.source_revision_id-cne$identity.id-or([string]$lc.source_revision_hash).ToLowerInvariant()-cne$identity.hash.ToLowerInvariant()-or[string]$lc.active_acceptance.concept_revision_id-cne$identity.id-or([string]$lc.active_acceptance.revision_hash).ToLowerInvariant()-cne$identity.hash.ToLowerInvariant()){throw 'The saved idea or acceptance changed. Reopen the current revision before confirming checks.'}
    return New-LocalCheckAttestationBinding $lc $identity (Get-LocalPolicyProfileBinding)
}
function Test-LocalCheckAttestationBinding($Expected,$Actual) {
    return ($null-ne$Expected-and$null-ne$Actual-and(ConvertTo-ForgeBriefCanonicalJson $Expected)-ceq(ConvertTo-ForgeBriefCanonicalJson $Actual))
}
function Write-LocalCheckRequestBundle {
    if($null -eq $script:Current){return $null};$state=Read-LocalCoreState;$key=[string](Get-PropertyValue $script:Current.concept 'concept_key');$lc=Get-LocalCoreConcept $key $state;if($null -eq $lc -or $null -eq $lc.active_acceptance){return $null}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=$lc.active_acceptance;if([string](Get-PropertyValue $acc 'concept_revision_id') -ne $identity.id -or [string](Get-PropertyValue $acc 'revision_hash') -ne $identity.hash){return $null}
    if([string]$lc.source_revision_id-cne$identity.id-or([string]$lc.source_revision_hash).ToLowerInvariant()-cne$identity.hash.ToLowerInvariant()){throw 'The saved idea changed. Reopen its current revision before checks.'}
    $artPath=[string](Get-PropertyValue $acc 'local_file_path');$artSha=([string](Get-PropertyValue $acc 'asset_sha256')).ToLowerInvariant();if(-not(Test-Path -LiteralPath $artPath -PathType Leaf) -or $artSha -notmatch '^[0-9a-f]{64}$'){return $null}
    $info=Get-LocalArtworkInfo $artPath;if([string]$info.sha256-cne$artSha){throw 'The accepted artwork bytes changed. Re-import and review the exact file.'}
    $listingHash=Get-LocalPublicationHash $lc.publication;$policyProfile=Get-LocalPolicyProfileBinding;$lineageKey=Get-StringSha256Hex ((@($key,$identity.id,$identity.hash,$artSha,$listingHash)-join '|').ToLowerInvariant())
    $pngCheck=$null;if($info.mime_type -eq 'image/png'){try{$pngCheck=Test-ForgeGenerationPngBytes $info.bytes $info.width_px $info.height_px}catch{}}
    $technical=[ordered]@{
      mime_type=$info.mime_type;file_size_bytes=[int64]$info.bytes.Length;width_px=[int]$info.width_px;height_px=[int]$info.height_px;
      max_print_width_in_at_300ppi=[Math]::Round(([double]$info.width_px/300.0),2);max_print_height_in_at_300ppi=[Math]::Round(([double]$info.height_px/300.0),2);
      png_native_validation=if($null-ne$pngCheck){[bool](Get-PropertyValue $pngCheck 'ok')}else{$false};png_validation_reason=if($null-ne$pngCheck){[string](Get-PropertyValue $pngCheck 'reason')}else{'not_png'};
      exact_sha256_verified=$true
    }
    $request=[ordered]@{
      schema='forge.local_check_request.v2';request_id=('check-'+$lineageKey.Substring(0,24));lineage_key=$lineageKey;created_at=[DateTime]::UtcNow.ToString('o');concept_key=$key;
      lineage=[ordered]@{concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string](Get-PropertyValue $acc 'lineage_fingerprint');accepted_artwork_sha256=$artSha;listing_hash=$listingHash};
      accepted_artwork=[ordered]@{file_name=[IO.Path]::GetFileName($artPath);mime_type=$info.mime_type;width_px=[int]$info.width_px;height_px=[int]$info.height_px;size_bytes=[int64]$info.bytes.Length;sha256=$artSha;provider_key=[string](Get-PropertyValue $acc 'provider_key');provider_profile=[string](Get-PropertyValue $acc 'provider_profile');provider_model=[string](Get-PropertyValue $acc 'provider_model');generation_request_id=[string](Get-PropertyValue $acc 'generation_request_id')};
      technical_facts=$technical;listing=if($null-ne$lc.publication){$lc.publication}else{$null};current_checks=$lc.checks;
      requested_external_checks=@('ip','print','policy','metadata');visual_authority='owner_exact_accept';
      channel_requirement_authority='not_asserted_without_current_verified_channel_profile';policy_profile_binding=if($null-ne$policyProfile){[ordered]@{schema='forge.policy_profile_binding.v1';profile_fingerprint=[string]$policyProfile.profile_fingerprint;marketplace=[string]$policyProfile.marketplace;product_type_key=[string]$policyProfile.product_type_key;template_key=[string]$policyProfile.template_key;template_file_sha256=[string]$policyProfile.template_file_sha256}}else{$null};local_check_worker_contract='forge.check_worker_result.v1';passing_evidence_requires_explicit_authority=$true;external_submission_authorized=$false
    }
    $evidence=[ordered]@{schema='forge.local_check_evidence.v4';revision_hash=$identity.hash;request_id=[string]$request.request_id;lineage_key=$lineageKey;concept_key=$key;concept_revision_id=$identity.id;artwork_sha256=$artSha;listing_hash=$listingHash}
    foreach($name in @('ip','visual','print','policy','metadata')){$cur=Get-PropertyValue $lc.checks $name;$evidence[$name]=[ordered]@{state=[string](Get-PropertyValue $cur 'state');source=[string](Get-PropertyValue $cur 'source');note=[string](Get-PropertyValue $cur 'note');checked_at=[string](Get-PropertyValue $cur 'checked_at');authority_kind=if($name-eq'visual'){'owner_exact_accept'}else{'owner_attested_external'};evidence_refs=@();attested=$false}}
    if($null-ne$policyProfile){foreach($name in @('ip','print','policy','metadata')){$evidence[$name]['channel_profile_fingerprint']=[string]$policyProfile.profile_fingerprint;$evidence[$name]['marketplace']=[string]$policyProfile.marketplace;$evidence[$name]['product_type_key']=[string]$policyProfile.product_type_key;$evidence[$name]['template_key']=[string]$policyProfile.template_key}}
    $safe=Get-LocalCoreSafeKey $key;$dir=Join-Path $script:LocalCoreExportRoot (Join-Path $safe 'checks');Ensure-Dir $dir;$requestPath=Join-Path $dir ('check-request-'+$lineageKey.Substring(0,16)+'.json');$evidencePath=Join-Path $dir ('check-evidence-'+$lineageKey.Substring(0,16)+'.template.json');$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false
    foreach($pair in @(@($requestPath,$request),@($evidencePath,$evidence))){$tmp=[string]$pair[0]+'.tmp.'+[Guid]::NewGuid().ToString('N');[IO.File]::WriteAllText($tmp,($pair[1]|ConvertTo-Json -Depth 50),$utf8);$verify=Get-Content -LiteralPath $tmp -Raw -Encoding UTF8|ConvertFrom-Json;if([string](Get-PropertyValue $verify 'concept_key') -ne $key){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue;throw 'Check request export verification failed.'};Move-Item -LiteralPath $tmp -Destination ([string]$pair[0]) -Force}
    try{if(Get-Command Write-LocalCheckChecklistFile -ErrorAction SilentlyContinue){$null=Write-LocalCheckChecklistFile $evidencePath}}catch{Write-AppLog 'WARN' ('Checklist file export failed: '+$_.Exception.Message)}
    return [pscustomobject]@{request_path=$requestPath;request_sha256=(Get-FileSha256Hex $requestPath);evidence_template_path=$evidencePath;evidence_template_sha256=(Get-FileSha256Hex $evidencePath);lineage_key=$lineageKey;attestation_binding=(New-LocalCheckAttestationBinding $lc $identity $policyProfile)}
}
function Import-LocalCheckEvidence {
    if($null -eq $script:Current){Show-Error 'Choose an idea first.';return};$dlg=New-Object Microsoft.Win32.OpenFileDialog;$dlg.Title='Import check evidence';$dlg.Filter='JSON evidence (*.json)|*.json';if($dlg.ShowDialog() -ne $true){return};Import-LocalCheckEvidenceFromPath $dlg.FileName
}
function Get-LocalCheckEvidenceArchivePath([string]$Sha) {
    if($Sha-cnotmatch'^[0-9a-f]{64}$'){throw 'Invalid evidence capture SHA.'}
    $root=Join-Path $script:LocalCoreRoot 'evidence-v1'
    if(Test-Path -LiteralPath $root){$item=Get-Item -LiteralPath $root -Force;if(!$item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Evidence archive is redirected or not a directory; existing artifact preserved.'}}
    $path=Join-Path $root ($Sha+'.json')
    if(Test-Path -LiteralPath $path){$item=Get-Item -LiteralPath $path -Force;if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Evidence capture is redirected or not an ordinary file; existing artifact preserved.'}}
    return $path
}
function Save-LocalCheckEvidenceCapture($Payload) {
    $sha=[string]$Payload.sha256;if($Payload.bytes-isnot[byte[]]-or(Get-ByteSha256Hex $Payload.bytes)-cne$sha){throw 'Evidence capture bytes/hash differ.'}
    $path=Get-LocalCheckEvidenceArchivePath $sha
    if(Test-Path -LiteralPath $path -PathType Leaf){if((Get-FileSha256Hex $path)-cne$sha){throw 'Existing evidence archive is corrupt; it was preserved. Restore it before retrying.'};return ('evidence-v1/'+$sha+'.json')}
    Ensure-Dir (Split-Path $path -Parent);$pending=$path+'.pending.'+[guid]::NewGuid().ToString('N')
    $stream=[IO.File]::Open($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($Payload.bytes,0,$Payload.bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    if((Get-FileSha256Hex $pending)-cne$sha){throw 'Evidence staging bytes differ; artifacts retained.'}
    try{[IO.File]::Move($pending,$path)}catch{if((Test-Path -LiteralPath $path -PathType Leaf)-and(Get-FileSha256Hex $path)-ceq$sha){[IO.File]::Delete($pending)}else{throw}}
    return ('evidence-v1/'+$sha+'.json')
}
function Test-LocalOwnerEvidenceCapture([string]$Name,$Check) {
    try{
        if([string](Get-PropertyValue $Check 'evidence_capture_schema')-cne'forge.local_check_capture.v1'){return $false}
        $sha=([string](Get-PropertyValue $Check 'evidence_source_file_sha256')).ToLowerInvariant();if([string](Get-PropertyValue $Check 'evidence_source_relative_path')-cne('evidence-v1/'+$sha+'.json')){return $false}
        $path=Get-LocalCheckEvidenceArchivePath $sha;if(!(Test-Path -LiteralPath $path -PathType Leaf)){return $false};$payload=Read-LocalCheckEvidencePayload $path;if($payload.sha256-cne$sha){return $false};$e=$payload.data
        if([string](Get-PropertyValue $e 'schema')-cne'forge.local_check_evidence.v4'){return $false}
        foreach($pair in @(@('concept_key','evidence_concept_key'),@('concept_revision_id','concept_revision_id'),@('revision_hash','revision_hash'),@('artwork_sha256','asset_sha256'))){$a=[string](Get-PropertyValue $e $pair[0]);$b=[string](Get-PropertyValue $Check $pair[1]);if($pair[0]-in@('revision_hash','artwork_sha256')){$a=$a.ToLowerInvariant();$b=$b.ToLowerInvariant()};if(!$a-or$a-cne$b){return $false}}
        if($Name-in@('policy','metadata')-and[string](Get-PropertyValue $e 'listing_hash')-cne[string](Get-PropertyValue $Check 'listing_hash')){return $false}
        $part=Get-PropertyValue $e $Name;$attested=Get-PropertyValue $part 'attested';if($null-eq$part-or$attested-isnot[bool]-or!$attested){return $false}
        if(([string](Get-PropertyValue $part 'state')).ToLowerInvariant()-cne([string](Get-PropertyValue $Check 'state')).ToLowerInvariant()-or[string](Get-PropertyValue $part 'checked_at')-cne[string](Get-PropertyValue $Check 'checked_at')){return $false}
        if(([string](Get-PropertyValue $part 'authority_kind')).ToLowerInvariant()-cne'owner_attested_external'){return $false}
        $refs=Get-LocalEvidenceRefValidation (Get-PropertyValue $part 'evidence_refs');if($refs.invalid_count-gt0-or@($refs.valid_refs).Count-lt1){return $false}
        if(([string](Get-PropertyValue $part 'source')).Trim()-cne([string](Get-PropertyValue $Check 'source')).Trim()-or[string](Get-PropertyValue $part 'note')-cne[string](Get-PropertyValue $Check 'note')){return $false}
        $storedRefs=Get-LocalEvidenceRefValidation (Get-PropertyValue $Check 'evidence_refs');if($storedRefs.invalid_count-gt0-or@($storedRefs.valid_refs).Count-ne@($refs.valid_refs).Count){return $false}
        for($i=0;$i-lt@($refs.valid_refs).Count;$i++){if([string]$refs.valid_refs[$i]-cne[string]$storedRefs.valid_refs[$i]){return $false}}
        foreach($field in @('channel_profile_fingerprint','marketplace','product_type_key','template_key')){if(([string](Get-PropertyValue $part $field)).ToLowerInvariant()-cne([string](Get-PropertyValue $Check $field)).ToLowerInvariant()){return $false}}
        return $true
    }catch{return $false}
}
function Read-LocalCheckEvidencePayload([string]$Path) {
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $memory=New-Object IO.MemoryStream
    try{if($stream.Length-gt10MB){throw 'Check evidence exceeds the local 10MiB import limit.'};$stream.CopyTo($memory);$bytes=$memory.ToArray()}finally{$memory.Dispose();$stream.Dispose()}
    $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes).TrimStart([char]0xfeff)
    $data=ConvertFrom-ForgeJsonObjectStrict $text
    return [pscustomobject]@{data=$data;sha256=(Get-ByteSha256Hex $bytes);size_bytes=$bytes.Length;bytes=$bytes}
}
function Import-LocalCheckEvidenceFromPath([string]$Path) {
    $script:LastCheckEvidenceImportOk=$false
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){Show-Error 'File not found.';return}
    try {
        $evidencePath=$Path;$e=$null;try{$payload=Read-LocalCheckEvidencePayload $evidencePath;$e=$payload.data;$evidenceFileSha=$payload.sha256}catch{throw ('Evidence must be a readable UTF-8 JSON object with unique property names, within the local 10MiB limit. Use Confirm checks or correct the file. '+$_.Exception.Message)};$schema=[string](Get-PropertyValue $e 'schema');if($schema -notin @('forge.local_check_evidence.v1','forge.local_check_evidence.v2','forge.local_check_evidence.v3','forge.local_check_evidence.v4')){throw 'Unsupported check evidence schema.'}
        $key=[string](Get-PropertyValue $e 'concept_key');if($key -and $key -cne [string]$script:Current.concept.concept_key){throw 'Evidence belongs to a different concept. Use the newest template from the checks folder, or press Confirm checks.'}
        $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc){$null=Ensure-LocalCoreConceptFromCurrent;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s}
        $accept=Get-PropertyValue $lc 'active_acceptance';$acceptedSha=if($null-ne $accept){[string](Get-PropertyValue $accept 'asset_sha256')}else{''};$listingHash=Get-LocalPublicationHash $lc.publication;$currentPolicyProfile=Get-LocalPolicyProfileBinding;$reviewHistoryCaptured=$false
        $eRev=([string](Get-PropertyValue $e 'concept_revision_id')).Trim();$eSha=([string](Get-PropertyValue $e 'artwork_sha256')).Trim().ToLowerInvariant();$eListing=([string](Get-PropertyValue $e 'listing_hash')).Trim().ToLowerInvariant()
        foreach($name in @('ip','visual','print','policy','metadata')){
            $incoming=Get-PropertyValue $e $name;if($null -eq $incoming){continue};$state=([string](Get-PropertyValue $incoming 'state')).Trim().ToLowerInvariant();if($state -notin @('pass','needs_review','blocked','not_required')){throw ("Invalid {0} state in evidence JSON." -f $name)}
            $isPassing=($state -in @('pass','not_required'));$scope=if($name -in @('policy','metadata')){'listing'}else{'artwork'}
            if($name -eq 'visual'){if($isPassing){$existingVisual=Get-PropertyValue $lc.checks 'visual';if(-not(Test-LocalCheckPass $existingVisual $lc 'visual')){throw 'Visual PASS is created only by exact local Accept for the current artwork.'}};continue}
            $source=([string](Get-PropertyValue $incoming 'source')).Trim();$note=[string](Get-PropertyValue $incoming 'note');$checkedAt=([string](Get-PropertyValue $incoming 'checked_at')).Trim();$authority=([string](Get-PropertyValue $incoming 'authority_kind')).Trim().ToLowerInvariant();$refValidation=Get-LocalEvidenceRefValidation (Get-PropertyValue $incoming 'evidence_refs');$refs=@(Get-PropertyValue $refValidation 'valid_refs');$attested=Get-PropertyValue $incoming 'attested'
            if($isPassing){
                if($schema -cne 'forge.local_check_evidence.v4'){throw 'Only v4 exact-version evidence may create a new passing check. Use the newest template or Confirm checks.'};if([string]::IsNullOrWhiteSpace($key)){throw 'Passing evidence requires the exact concept_key.'};$eHash=([string](Get-PropertyValue $e 'revision_hash')).ToLowerInvariant();if($eHash-cnotmatch'^[0-9a-f]{64}$'-or$eHash-cne$identity.hash.ToLowerInvariant()){throw 'Evidence revision_hash does not match the current exact concept content.'};if([string](Get-PropertyValue $lc 'source_revision_id')-cne$identity.id-or([string](Get-PropertyValue $lc 'source_revision_hash')).ToLowerInvariant()-cne$identity.hash.ToLowerInvariant()){throw 'The saved concept changed after this view was loaded. Reopen it before importing checks.'}
                if($eRev -cne $identity.id){throw ("{0} evidence revision does not match the current idea revision. Use the newest template from the checks folder, or press Confirm checks." -f $name)}
                if($scope -in @('artwork','listing')){if([string]::IsNullOrWhiteSpace($acceptedSha) -or $eSha -ne $acceptedSha){throw ("{0} evidence artwork SHA does not match the exact accepted artwork. Use the newest template from the checks folder, or press Confirm checks." -f $name)}}
                if($scope -eq 'listing'){if([string]::IsNullOrWhiteSpace($listingHash) -or $eListing -ne $listingHash){throw (([string]$name)+' evidence listing_hash does not match the current listing revision. Use the newest template from the checks folder, or press Confirm checks.')}}
                if([string]::IsNullOrWhiteSpace($source) -or [string]::IsNullOrWhiteSpace($checkedAt)){throw ("{0} passing evidence requires source and checked_at." -f $name)}
                try{$checkedTime=[DateTime]::Parse($checkedAt,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind);if($checkedTime.ToUniversalTime() -gt [DateTime]::UtcNow.AddMinutes(10)){throw 'future'}}catch{throw ("{0} checked_at must be a valid non-future ISO date/time." -f $name)}
                if(-not((Get-LocalCheckAllowedAuthority $name $state) -contains $authority)){throw ("{0} authority_kind is not allowed for state {1}." -f $name,$state)}
                if($authority -eq 'owner_attested_external' -and ($attested-isnot[bool]-or-not$attested)){throw ("{0} owner_attested_external evidence requires the JSON boolean attested=true." -f $name)}
                if($authority -notin @('owner_exact_accept','live_backend_exact')){if([int](Get-PropertyValue $refValidation 'invalid_count') -gt 0){throw ("{0} passing evidence contains an empty or non-string evidence_ref." -f $name)};if($refs.Count -lt 1){throw ("{0} passing evidence requires at least one non-empty string evidence_ref." -f $name)}}
                if($authority -in @('live_backend_exact','verified_worker','verified_channel_profile')){throw ("Imported owner JSON cannot self-assert authority_kind {0}; use the corresponding verified sync/worker/profile path." -f $authority)}
                if($name -eq 'visual' -and $authority -ne 'owner_exact_accept'){throw 'Imported owner JSON cannot replace the exact-accept visual authority.'}
                if($name -in @('ip','print','policy','metadata')){
                    if($null-eq$currentPolicyProfile){throw 'Passing owner evidence requires a current valid product/channel profile.'}
                    $eProfileFp=([string](Get-PropertyValue $incoming 'channel_profile_fingerprint')).Trim().ToLowerInvariant();$eMarket=([string](Get-PropertyValue $incoming 'marketplace')).Trim().ToLowerInvariant();$eProduct=([string](Get-PropertyValue $incoming 'product_type_key')).Trim().ToLowerInvariant();$eTemplate=([string](Get-PropertyValue $incoming 'template_key')).Trim().ToLowerInvariant()
                    if($eProfileFp -ne [string]$currentPolicyProfile.profile_fingerprint -or $eMarket -ne [string]$currentPolicyProfile.marketplace -or $eProduct -ne [string]$currentPolicyProfile.product_type_key -or $eTemplate -ne [string]$currentPolicyProfile.template_key){throw 'Evidence product/channel profile binding does not match the current owner-attested print profile. Use the newest template from the checks folder, or press Confirm checks.'}
                }
            }
            $obj=[pscustomobject]@{state=$state;source=$source;note=$note;checked_at=$checkedAt;scope=$scope;concept_revision_id=$eRev;asset_sha256=if($scope -in @('artwork','listing')){$eSha}else{''};listing_hash=if($scope -eq 'listing'){$eListing}else{''};channel_profile_fingerprint=if($isPassing){([string](Get-PropertyValue $incoming 'channel_profile_fingerprint')).Trim().ToLowerInvariant()}else{''};marketplace=if($isPassing){([string](Get-PropertyValue $incoming 'marketplace')).Trim().ToLowerInvariant()}else{''};product_type_key=if($isPassing){([string](Get-PropertyValue $incoming 'product_type_key')).Trim().ToLowerInvariant()}else{''};template_key=if($isPassing){([string](Get-PropertyValue $incoming 'template_key')).Trim().ToLowerInvariant()}else{''};authority_kind=if($isPassing){$authority}else{'none'};evidence_refs=if($isPassing){@($refs)}else{@()};evidence_source_file_sha256=$evidenceFileSha;evidence_schema=$schema;evidence_capture_schema='forge.local_check_capture.v1';evidence_source_relative_path=('evidence-v1/'+$evidenceFileSha+'.json');evidence_concept_key=$key;revision_hash=([string](Get-PropertyValue $e 'revision_hash')).ToLowerInvariant()}
            if($name -eq 'ip'){$obj|Add-Member -NotePropertyName legal_clearance -NotePropertyValue $false -Force};if(!$reviewHistoryCaptured-and($lc.checks.PSObject.Properties[$name].Value|ConvertTo-Json -Depth 60 -Compress)-cne($obj|ConvertTo-Json -Depth 60 -Compress)){$null=Preserve-ForgeLocalReviewHistory $lc 'check_evidence_changed';$reviewHistoryCaptured=$true};$lc.checks.PSObject.Properties[$name].Value=$obj
        }
        $null=Save-LocalCheckEvidenceCapture $payload
        Write-LocalCoreState $s;try{$null=Write-LocalCheckRequestBundle}catch{Write-AppLog 'WARN' ('Check request refresh after evidence import failed: '+$_.Exception.Message)};Load-LocalChecksUi;$StatusText.Text='Authority-bound local check evidence imported.';$script:LastCheckEvidenceImportOk=$true
    } catch {Show-Error $_.Exception.Message;$StatusText.Text='Check evidence import failed.'}
}
function Format-LocalCheck([string]$Label,$Check,$Context=$null) {
    $keys=@{IP='ip';Visual='visual';Print='print';Policy='policy';'Marketplace policy'='policy';Metadata='metadata'};$k=if($keys.ContainsKey($Label)){$keys[$Label]}else{$Label.ToLowerInvariant()}
    $lab=Get-UiText ('chk.label.'+$k) $Label
    if($null-eq$Check){return ("{0} - {1}"-f$lab,(Get-UiText 'chk.view.none' 'Not checked'))}
    $state=[string](Get-PropertyValue $Check 'state');$st=Get-UiText ('chk.view.'+$state) $state;$authority=[string](Get-PropertyValue $Check 'authority_kind')
    $passing=$state-in@('pass','not_required');$sourceUnavailable=$passing-and!(Test-LocalCheckEvidenceAuthority $k $Check)
    $stale=(!$sourceUnavailable-and$passing-and$null-ne$Context-and!(Test-LocalCheckPass $Check $Context $k))
    $technicalOnly=($k-ceq'print'-and$authority-cne'owner_attested_external'-and($authority-in@('verified_worker','verified_channel_profile','live_backend_exact')-or[string](Get-PropertyValue $Check 'source')-ceq'trusted_local_check_worker'))
    if($technicalOnly){$lab=Get-UiText 'chk.label.print_technical' 'Print technical checks'}
    if($sourceUnavailable){$st=Get-UiText 'chk.view.unverified_source' 'Evidence unavailable; review required'}
    elseif($stale){$st=Get-UiText 'chk.view.stale_target' 'Review required for the current target'}
    elseif($technicalOnly-and$passing){$st=Get-UiText 'chk.view.technical_only' 'Technical evidence recorded; owner print quality review required'}
    $note=[string](Get-PropertyValue $Check 'note');try{if(Get-Command Translate-UiMessage -ErrorAction SilentlyContinue){$note=Translate-UiMessage $note}}catch{}
    if($sourceUnavailable){$note+="`n"+(Get-UiText 'chk.source.reimport' 'Original record retained. Re-import its source JSON or confirm the exact current checks again.')}
    elseif($stale){$note+="`n"+(Get-UiText 'chk.source.recheck_target' 'Original evidence is retained, but the idea, artwork, listing or profile target changed. Review the exact current target.')}
    return ("{0} - {1}`n{2}"-f$lab,$st,$note)
}
function Load-LocalChecksUi {
    if($null -eq $script:Current){return};$lc=Ensure-LocalCoreConceptFromCurrent;if($null -eq $lc){return};try{if($null-ne$lc.active_acceptance){$null=Invoke-LocalCheckAutomation;$lc=Ensure-LocalCoreConceptFromCurrent}}catch{Write-AppLog 'WARN' ('Local check automation on Checks open failed: '+$_.Exception.Message)}
    if(Test-CurrentIsResearchDraft){
        $draft=Get-ResearchDraft ([string]$script:Current.concept.concept_key)
        $packet=Get-PropertyValue (Get-PropertyValue $draft 'provenance') 'research_packet'
        $AnalysisAdvanced.Text=if($null-ne$packet){'Saved research basis for revision '+[string]$draft.current_revision_id+' / '+[string]$draft.current_revision_hash+"`r`n`r`n"+(Format-ResearchEvidenceRows $packet)}else{'No captured source packet is bound to this draft. Research claims remain unverified.'}
    }
    $AnalysisEvidence.Text=(Format-LocalCheck 'IP' $lc.checks.ip $lc)+"`n`n"+(Format-LocalCheck 'Visual' $lc.checks.visual $lc)+"`n`n"+(Format-LocalCheck 'Print' $lc.checks.print $lc)+"`n`n"+(Format-LocalCheck 'Policy' $lc.checks.policy $lc)+"`n`n"+(Format-LocalCheck 'Metadata' $lc.checks.metadata $lc)
    $AnalysisWarnings.Text='Local checks are evidence for workflow continuity only. IP pass is not a legal opinion; marketplace policy and print requirements must be revalidated before external publication.'
    if($null -ne $LocalCheckStatusText){$LocalCheckStatusText.Text=Get-UiText 'checks.loaded' 'Checks loaded. Press "Confirm checks…" to confirm IP, policy and listing text.'}
}
function Get-ForgeLegacyProjectNotice($Lc) {
    $legacy=Get-PropertyValue $Lc 'legacy_v1_content';if($null-eq$legacy-or[string](Get-PropertyValue $legacy 'schema')-cne'forge.legacy_v1_content.v1'){return ''}
    $text=if($script:Locale-ceq'ru'){'Старый проект v1: сохранённое содержимое доступно для проверки; прежние проверки, решение и приёмка сохранены как история. Требуется новая проверка точной цели; старое approval не действует.'}elseif($script:Locale-ceq'es'){'Proyecto v1: contenido guardado conservado para revision; revisiones, decision y aceptacion anteriores conservadas como historial. Se requiere revisar el objetivo exacto; la aprobacion antigua no es valida.'}else{'Legacy v1 project: saved content retained for review; prior checks, decision and acceptance retained as history. Review the exact target again; old approval is not valid.'}
    $decision=[string](Get-PropertyValue $legacy 'owner_decision');if($decision-in@('KEEP','EDIT','REGEN','SKIP','UNDECIDED')){$text+=' '+$decision+' (v1).'}
    foreach($name in @('ip','visual','print','policy','metadata')){$check=Get-PropertyValue (Get-PropertyValue $legacy 'checks') $name;if([string](Get-PropertyValue $check 'state')-in@('blocked','needs_review')){$note=[string](Get-PropertyValue $check 'note');if($note.Length-gt300){$note=$note.Substring(0,300)+'...'};$text+=' ['+$name+': '+[string](Get-PropertyValue $check 'state')+'] '+$note}}
    return $text
}
function Get-LocalPublicationDefault($lc) {
    $keywords=@();foreach($piece in @([string]$lc.niche_name,[string]$lc.title,[string]$lc.hook)){foreach($w in ($piece -split '[^A-Za-z0-9]+')){if($w.Length -ge 3 -and $keywords -notcontains $w.ToLowerInvariant()){$keywords+=$w.ToLowerInvariant()}}};if($keywords.Count -gt 12){$keywords=@($keywords[0..11])}
    $acc=Get-PropertyValue $lc 'active_acceptance';$p=[pscustomobject]@{listing_title=[string]$lc.title;brand='';bullet_1=[string]$lc.hook;bullet_2='';description=[string]$lc.concept_text;keywords=@($keywords);locale='en-US';saved_at='';revision_no=0;concept_revision_id=[string](Get-PropertyValue $lc 'source_revision_id');accepted_artwork_sha256=if($null-ne $acc){[string](Get-PropertyValue $acc 'asset_sha256')}else{''};acceptance_fingerprint=if($null-ne $acc){[string](Get-PropertyValue $acc 'lineage_fingerprint')}else{''};content_hash=''};$legacy=Get-PropertyValue $lc 'legacy_v1_content';$pending=Get-PropertyValue $lc 'legacy_listing_restore_pending'
    if($pending-is[bool]-and$pending-and$null-ne$legacy-and[string](Get-PropertyValue $legacy 'schema')-ceq'forge.legacy_v1_content.v1'){
        $old=Get-PropertyValue $legacy 'publication'
        if($old-is[pscustomobject]){
            foreach($name in @('listing_title','brand','bullet_1','bullet_2','description','locale','edit_reason','saved_at')){$v=Get-PropertyValue $old $name;if($v-is[string]){Add-OrSetProperty $p $name $v}}
            $kwProperty=$old.PSObject.Properties['keywords'];if($null-ne$kwProperty-and$kwProperty.Value-is[Array]-and@($kwProperty.Value|Where-Object{$_-isnot[string]}).Count-eq0){$p.keywords=@($kwProperty.Value)}elseif($null-ne$kwProperty-and$kwProperty.Value-is[string]){$p.keywords=@([string]$kwProperty.Value)}
            Add-OrSetProperty $p 'legacy_imported_draft' $true
        }
    }
    $p.content_hash=Get-LocalPublicationHash $p;return $p
}
function Get-LocalPublicationEditorBinding($Lc) {
    return [pscustomobject][ordered]@{concept_key=[string](Get-PropertyValue $Lc 'concept_key');revision_id=[string](Get-PropertyValue $Lc 'source_revision_id');revision_hash=[string](Get-PropertyValue $Lc 'source_revision_hash');acceptance_fingerprint=[string](Get-PropertyValue (Get-PropertyValue $Lc 'active_acceptance') 'lineage_fingerprint');artwork_sha256=[string](Get-PropertyValue (Get-PropertyValue $Lc 'active_acceptance') 'asset_sha256');listing_hash=(Get-LocalPublicationHash (Get-PropertyValue $Lc 'publication'))}
}
function Set-LocalPublicationLocaleFromSaved([string]$Locale) {
    if($null-eq$PublicationLocaleBox-or!$PublicationLocaleBox.PSObject.Properties['Items']){return $false}
    $tag=$Locale.Replace('_','-')
    foreach($item in $PublicationLocaleBox.Items){if([string](Get-PropertyValue $item 'Tag')-ieq$tag){$PublicationLocaleBox.SelectedItem=$item;return $true}}
    $PublicationLocaleBox.SelectedIndex=-1;return $false
}
function Get-LocalPublicationSelectedLocale {
    if($null-eq$PublicationLocaleBox-or$null-eq$PublicationLocaleBox.SelectedItem){return ''}
    $tag=[string](Get-PropertyValue $PublicationLocaleBox.SelectedItem 'Tag')
    if($tag-in@('en-US','ru-RU','es-ES')){return $tag};return ''
}
function Load-LocalPublicationUi {
    try {
    if($script:PublicationDirty){
        $PublicationPreflight.Text=Get-UiText 'listing.unsaved.preserved' 'DRAFT: unsaved listing fields are preserved. Save them or explicitly discard them before reloading; current readiness is not established.'
        return
    }
    if($null -eq $script:Current){return};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc){$null=Ensure-LocalCoreConceptFromCurrent;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=Get-PropertyValue $lc 'active_acceptance';$hasAccept=($null-ne$acc -and [string](Get-PropertyValue $acc 'concept_revision_id') -eq $identity.id -and [string](Get-PropertyValue $acc 'revision_hash') -eq $identity.hash)
    if($null -eq $lc.publication){$lc.publication=Get-LocalPublicationDefault $lc;if((Get-PropertyValue $lc.publication 'legacy_imported_draft')-is[bool]-and(Get-PropertyValue $lc.publication 'legacy_imported_draft')){Add-OrSetProperty $lc 'legacy_listing_restore_pending' $false};Write-LocalCoreState $s};$p=$lc.publication
    $localeRestored=Set-LocalPublicationLocaleFromSaved ([string](Get-PropertyValue $p 'locale'))
    $PublicationTitleBox.Text=[string]$p.listing_title;$PublicationBrandBox.Text=[string]$p.brand;$PublicationBullet1Box.Text=[string]$p.bullet_1;$PublicationBullet2Box.Text=[string]$p.bullet_2;$PublicationDescriptionBox.Text=[string]$p.description;$PublicationKeywordsBox.Text=(@($p.keywords)-join ', ')
    foreach($box in @($PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox,$PublicationReasonBox)){$box.IsEnabled=$hasAccept;$box.IsReadOnly=(-not $hasAccept)};$PublicationLocaleBox.IsEnabled=$hasAccept
    $PublicationCreativeStatus.Text=if($hasAccept){'Exact local artwork is accepted for the current revision. Listing edits remain local until packaged.'}else{'Accept exact artwork for the current idea revision before preparing the listing.'}
    $legacyNotice=Get-ForgeLegacyProjectNotice $lc;if($legacyNotice){$PublicationCreativeStatus.Text+=(' '+$legacyNotice)}
    if(!$localeRestored){$PublicationCreativeStatus.Text+=' '+(Get-UiText 'listing.locale.choose' 'The saved listing locale is not selected; choose an explicit supported listing language before saving.')}
    $PublicationCheckIp.Text=Format-LocalCheck 'IP' $lc.checks.ip;$PublicationCheckVisual.Text=Format-LocalCheck 'Visual' $lc.checks.visual;$PublicationCheckPrint.Text=Format-LocalCheck 'Print' $lc.checks.print;$PublicationCheckPolicy.Text=Format-LocalCheck 'Marketplace policy' $lc.checks.policy
    $PublicationEconomics.Text=Format-LocalEconomicsSnapshot (Get-LocalEconomicsSnapshot $lc);if(Get-Variable -Name LocalEconomicsButton -ErrorAction SilentlyContinue){$LocalEconomicsButton.IsEnabled=$hasAccept;$LocalEconomicsButton.Content=Get-UiText 'econ.button' 'Review economics scenario'};$PublicationExternal.Text='External submission remains manual and locked inside Merch Forge. Local package creation never submits anything.';
    $script:Publication=[pscustomobject]@{local_core=$true;workspace=[pscustomobject]@{current_revision_accepted=$hasAccept}};$script:LocalPublicationEditor=Get-LocalPublicationEditorBinding $lc;Set-PublicationDirty $false;$PublicationPreflight.Text=Get-LocalPackageReadinessText $lc;$DeliveryStatus.Text=((Get-UiText 'pipe.delivery.archives' 'Recorded local archives: {0}; current verified READY packages: {1}.')-f@($lc.packages).Count,(Get-LocalCurrentReadyPackageCount $lc $s));if($null-ne$SavePublicationButton){$SavePublicationButton.IsEnabled=$hasAccept};if($null-ne$LocalBuildPackageButton){$LocalBuildPackageButton.IsEnabled=$hasAccept}

    } catch {
        Write-AppLog 'WARN' ('Listing refresh could not verify local state: '+$_.Exception.Message)
        $message=Get-UiText 'pipe.state.unavailable' 'Local state is unavailable; readiness cannot be verified. Retry refresh or use My data recovery. Unsaved editor fields are preserved.'
        $PublicationPreflight.Text=$message;$DeliveryStatus.Text=$message
        if($null-ne$LocalBuildPackageButton){$LocalBuildPackageButton.IsEnabled=$false}
        if($null-ne$SavePublicationButton){$SavePublicationButton.IsEnabled=($null-ne$script:LocalPublicationEditor)}
    }
}
function Save-LocalPublicationMetadata {
    try {
    if($null -eq $script:Current){return $false};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc -or $null -eq $lc.active_acceptance){Show-Error 'Accept local artwork first.';return $false}
    $acc=$lc.active_acceptance;$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;if([string]$acc.concept_revision_id -ne $identity.id -or [string]$acc.revision_hash -ne $identity.hash){Show-Error 'Local acceptance is stale for this idea revision.';return $false}
    $binding=Get-LocalPublicationEditorBinding $lc
    if($null-eq$script:LocalPublicationEditor-or($script:LocalPublicationEditor|ConvertTo-Json -Depth 10 -Compress)-cne($binding|ConvertTo-Json -Depth 10 -Compress)){Show-Error (Get-UiText 'listing.editor.stale' 'The saved artwork, concept or listing changed after this editor was loaded. Your fields are preserved; refresh and review the current target before saving.');return $false}
    $selectedLocale=Get-LocalPublicationSelectedLocale
    if(!$selectedLocale){Show-Error (Get-UiText 'listing.locale.choose' 'Choose an explicit supported listing language before saving.');return $false}
    $title=([string]$PublicationTitleBox.Text).Trim();if([string]::IsNullOrWhiteSpace($title)){Show-Error 'Listing title is required.';return $false};$kw=@();foreach($x in (([string]$PublicationKeywordsBox.Text)-split '[,;]')){$v=$x.Trim();if($v){$kw+=$v}};$rev=1;try{$rev=[int]$lc.publication.revision_no+1}catch{}
    $p=[pscustomobject]@{listing_title=$title;brand=[string]$PublicationBrandBox.Text;bullet_1=[string]$PublicationBullet1Box.Text;bullet_2=[string]$PublicationBullet2Box.Text;description=[string]$PublicationDescriptionBox.Text;keywords=@($kw);locale=$selectedLocale;saved_at=[DateTime]::UtcNow.ToString('o');revision_no=$rev;edit_reason=[string]$PublicationReasonBox.Text;concept_revision_id=$identity.id;accepted_artwork_sha256=[string]$acc.asset_sha256;acceptance_fingerprint=[string]$acc.lineage_fingerprint;content_hash=''};$p.content_hash=Get-LocalPublicationHash $p
    $oldHash=if($null-ne $lc.publication){[string](Get-PropertyValue $lc.publication 'content_hash')}else{''};if($oldHash-ne$p.content_hash){$null=Preserve-ForgeLocalReviewHistory $lc 'listing_changed'};$lc.publication=$p
    if($oldHash -ne $p.content_hash){$freshChecks=New-LocalCoreChecks $identity.id ([string]$acc.asset_sha256) $p.content_hash;$lc.checks.policy=$freshChecks.policy;$lc.checks.metadata=$freshChecks.metadata;Invalidate-LocalCorePackages $lc 'listing_metadata_changed'}
    try{Write-LocalCoreState $s}catch{
        $writeFailure=$_.Exception.Message;$verifiedCommit=$false
        try{
            $savedFrame=(Read-ForgeStateFileSnapshot $script:LocalCoreStatePath $true).data
            $savedConcept=Get-LocalCoreConcept ([string]$lc.concept_key) $savedFrame
            $verifiedCommit=([string]$savedFrame.last_write_id-ceq[string]$s.last_write_id-and$savedFrame.state_revision-eq$s.state_revision-and$null-ne$savedConcept-and[string]$savedConcept.source_revision_id-ceq[string]$identity.id-and[string]$savedConcept.source_revision_hash-ceq[string]$identity.hash-and[string]$savedConcept.active_acceptance.lineage_fingerprint-ceq[string]$acc.lineage_fingerprint-and($savedConcept.publication|ConvertTo-Json -Depth 60 -Compress)-ceq($p|ConvertTo-Json -Depth 60 -Compress))
        }catch{}
        if(!$verifiedCommit){throw ('Local listing save could not be confirmed. '+$writeFailure)}
        try{Write-AppLog 'WARN' ('Exact listing commit verified after write follow-up error: '+$writeFailure)}catch{}
    }
    try{$bundle=Write-LocalCheckRequestBundle;if($null-ne$bundle){$StatusText.Text=('Local listing draft saved as revision '+$rev+'. Check request refreshed for this exact listing. Nothing was published.')}else{$StatusText.Text=('Local listing draft saved as revision '+$rev+'. Nothing was published.')}}catch{Write-AppLog 'WARN' ('Check request refresh after listing save failed: '+$_.Exception.Message);$StatusText.Text=('Local listing draft saved as revision '+$rev+'. Nothing was published.')};try{$null=Invoke-LocalCheckAutomation}catch{Write-AppLog 'WARN' ('Local check automation after listing save failed: '+$_.Exception.Message)};Set-PublicationDirty $false;Load-LocalPublicationUi;return $true
    }catch{
        $failure=$_.Exception.Message
        try{Write-AppLog 'WARN' ('Local listing save not confirmed; editor preserved: '+$failure)}catch{}
        Set-PublicationDirty $true
        if($null-ne$LocalBuildPackageButton){$LocalBuildPackageButton.IsEnabled=$false}
        $message=if($script:Locale-ceq'ru'){'Сохранение текста карточки не подтверждено. Ваши поля сохранены в редакторе. Нет автоматического повтора. Проверьте сохранённое состояние через обновление перед повтором; при изменении цели старые данные не перезаписываются.'}elseif($script:Locale-ceq'es'){'No se confirmo el guardado de la ficha. Los campos siguen en el editor. No hay reintento automatico. Compruebe el estado guardado antes de reintentar; no se sobrescribe un objetivo cambiado.'}else{'Listing save could not be confirmed. Your fields remain in the editor. No automatic retry. Refresh and check the saved state before retrying; a changed target will not be overwritten.'}
        $StatusText.Text=$message;$PublicationPreflight.Text=$message;Show-Error ($message+"`r`n"+$failure)
        return $false
    }
}
function Test-LocalCheckStatePass($Check) { return ([string](Get-PropertyValue $Check 'state') -in @('pass','not_required')) }
function Test-LocalCheckPass($Check,$lc,[string]$Name) {
    if(-not(Test-LocalCheckStatePass $Check) -or -not(Test-LocalCheckEvidenceAuthority $Name $Check) -or $null -eq $lc -or $null -eq $lc.active_acceptance){return $false};$acc=$lc.active_acceptance;$rev=[string](Get-PropertyValue $acc 'concept_revision_id');$sha=[string](Get-PropertyValue $acc 'asset_sha256')
    if([string](Get-PropertyValue $Check 'concept_revision_id') -ne $rev){return $false}
    if([string](Get-PropertyValue $Check 'evidence_capture_schema')-ceq'forge.local_check_capture.v1'){
        if([string](Get-PropertyValue $Check 'evidence_concept_key')-cne[string](Get-PropertyValue $lc 'concept_key')-or([string](Get-PropertyValue $Check 'revision_hash')).ToLowerInvariant()-cne([string](Get-PropertyValue $lc 'source_revision_hash')).ToLowerInvariant()-or([string](Get-PropertyValue $Check 'revision_hash')).ToLowerInvariant()-cne([string](Get-PropertyValue $acc 'revision_hash')).ToLowerInvariant()){return $false}
        if([string](Get-PropertyValue $Check 'asset_sha256')-cne$sha-or!(Test-LocalPolicyProfileBinding $Check)){return $false}
    }
    if($Name -in @('visual','print','policy','metadata')){if([string](Get-PropertyValue $Check 'asset_sha256') -ne $sha){return $false}}
    if($Name -in @('policy','metadata')){$lh=Get-LocalPublicationHash $lc.publication;if([string]::IsNullOrWhiteSpace($lh) -or [string](Get-PropertyValue $Check 'listing_hash') -ne $lh){return $false}}
    if($Name -eq 'policy' -and -not(Test-LocalPolicyProfileBinding $Check)){return $false}
    return $true
}
function Get-LocalCheckGateSnapshot($lc) {
    $items=[ordered]@{};$allReady=$true
    foreach($name in @('ip','visual','print','policy','metadata')){$c=Get-PropertyValue $lc.checks $name;$ready=Test-LocalCheckPass $c $lc $name;if(-not $ready){$allReady=$false};$items[$name]=[ordered]@{state=[string](Get-PropertyValue $c 'state');ready=$ready;authority_kind=[string](Get-PropertyValue $c 'authority_kind');source=[string](Get-PropertyValue $c 'source');checked_at=[string](Get-PropertyValue $c 'checked_at');evidence_refs=@(Get-PropertyValue $c 'evidence_refs');evidence_source_file_sha256=[string](Get-PropertyValue $c 'evidence_source_file_sha256');evidence_schema=[string](Get-PropertyValue $c 'evidence_schema');channel_profile_fingerprint=[string](Get-PropertyValue $c 'channel_profile_fingerprint');marketplace=[string](Get-PropertyValue $c 'marketplace');product_type_key=[string](Get-PropertyValue $c 'product_type_key');template_key=[string](Get-PropertyValue $c 'template_key')}}
    $listing=Get-LocalListingConstraintSnapshot (Get-PropertyValue $lc 'publication')
    if(-not $listing.ready){$allReady=$false}
    return [pscustomobject]@{all_ready=$allReady;checks=$items;listing_constraints=$listing}
}
function Get-LocalListingConstraintSnapshot($Publication) {
    # Use only the limits already shipped by Forge. Phrase/IP hints remain advisory.
    . (Join-Path $script:ModuleRoot 'Forge.ListingHints.ps1')
    $issues=@();$mapping=[ordered]@{title='listing_title';brand='brand';bullet1='bullet_1';bullet2='bullet_2';description='description'};$labels=@{title='Title';brand='Brand';bullet1='Bullet 1';bullet2='Bullet 2';description='Description'}
    foreach($name in $mapping.Keys){
        $field=$mapping[$name];$value=$null
        if($Publication -is [Collections.IDictionary]){$value=$Publication[$field]}elseif($null-ne$Publication){$p=$Publication.PSObject.Properties[$field];if($null-ne$p){$value=$p.Value}}
        $limit=$script:ListingLimits[$name]
        if($null-eq$value){$value=''}
        if($value-isnot[string]){$issues+=@{field=$field;reason='text_value_required';message=($labels[$name]+' must be text.')};continue}
        if($value.Length-gt$limit.max){$issues+=@{field=$field;reason='maximum_length_exceeded';actual=$value.Length;limit=$limit.max;message=($labels[$name]+': '+$value.Length+' characters; maximum '+$limit.max+'.')}}
        elseif($value.Trim().Length-lt$limit.min){$issues+=@{field=$field;reason='minimum_length_not_met';actual=$value.Trim().Length;limit=$limit.min;message=($labels[$name]+' needs at least '+$limit.min+' characters.')}}
    }
    return [pscustomobject]@{ready=($issues.Count-eq0);issues=@($issues);source='shipped_Forge.ListingLimits';legal_or_ip_verification=$false}
}
function Copy-LocalAcceptedArtworkForPackage([string]$Source,[string]$Destination,[string]$ExpectedSha256) {
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    if((Get-FileSha256Hex $Destination)-cne$ExpectedSha256){throw 'Copied package artwork differs from exact accepted SHA-256. No READY package was created.'}
}
function Get-LocalPackageBriefApprovalSnapshot($Lc,$Identity) {
    try {
        if($null-ne(Get-PropertyValue $Lc 'source_save_intent')){throw 'Source save is unresolved.'}
        if(Test-ForgeRecoveryReviewRequired $Lc){throw 'Recovered snapshot requires new owner approval.'}
        $brief=Get-PropertyValue $Lc 'generation_brief_snapshot'
        Assert-ForgeBriefApproval (Get-PropertyValue $Lc 'brief_approval') $brief $Identity.id $Identity.hash
        if([string](Get-PropertyValue $Lc 'generation_brief_sha256')-cne(Get-ForgeBriefSha256 $brief)){throw 'Saved brief fingerprint changed.'}
        if($null-ne$script:Current-and[string]$script:Current.concept.concept_key-ceq[string]$Lc.concept_key){
            if($script:Dirty-or(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $script:Current.concept))-cne(Get-ForgeBriefSha256 $brief)){throw 'Current brief has unapproved changes.'}
        }
        return [pscustomobject]@{approved=$true;approval_id=[string]$Lc.brief_approval.approval_id;brief_sha256=(Get-ForgeBriefSha256 $brief);reason='exact_saved_idea_and_design_approved'}
    }catch{return [pscustomobject]@{approved=$false;approval_id='';brief_sha256='';reason='current_idea_and_design_approval_required'}}
}
function Get-LocalDeliveryReadiness($Lc,$State=$null) {
    $result=[pscustomobject]@{ready=$false;reason='accepted_artwork_required';identity=$null;approval=$null;gate=$null;print=$null;listing_hash='';acceptance=$null;financial_readiness_claim=$false}
    try {
        if($null-eq$Lc){return $result}
        if($null-eq$State){$State=Read-LocalCoreState}
        if($null-ne$script:Current-and[string](Get-PropertyValue $script:Current.concept 'concept_key')-ceq[string]$Lc.concept_key-and($script:Dirty-or$script:PublicationDirty)){$result.reason='unsaved_concept_or_listing_changes';return $result}
        $id=[pscustomobject]@{id=[string](Get-PropertyValue $Lc 'source_revision_id');hash=[string](Get-PropertyValue $Lc 'source_revision_hash')};$result.identity=$id
        if($null-ne$script:Current-and[string](Get-PropertyValue $script:Current.concept 'concept_key')-ceq[string]$Lc.concept_key){$visible=Get-LocalCurrentRevisionIdentity $script:Current.concept;if($visible.id-cne$id.id-or$visible.hash-cne$id.hash){$result.reason='visible_revision_changed';return $result}}
        if($null-ne$State){$draft=Get-ResearchDraft ([string]$Lc.concept_key) $State;if($null-ne$draft-and($id.id-cne$draft.current_revision_id-or$id.hash-cne$draft.current_revision_hash)){$result.reason='saved_revision_changed';return $result}}
        $acc=Get-PropertyValue $Lc 'active_acceptance';$result.acceptance=$acc
        if($null-eq$acc-or[string](Get-PropertyValue $acc 'concept_revision_id')-cne$id.id-or[string](Get-PropertyValue $acc 'revision_hash')-cne$id.hash){return $result}
        $pub=Get-PropertyValue $Lc 'publication';$result.reason='listing_acceptance_mismatch'
        if($null-eq$pub-or[string](Get-PropertyValue $pub 'acceptance_fingerprint')-cne[string](Get-PropertyValue $acc 'lineage_fingerprint')){return $result}
        $result.listing_hash=Get-LocalPublicationHash $pub
        $result.approval=Get-LocalPackageBriefApprovalSnapshot $Lc $id;$result.reason='current_idea_and_design_approval_required';if(!$result.approval.approved){return $result}
        $result.gate=Get-LocalCheckGateSnapshot $Lc;$result.reason='current_checks_required';if(!$result.gate.all_ready){return $result}
        $result.print=Get-LocalPrintProductionSnapshot $Lc $id $acc;$result.reason=[string](Get-PropertyValue $result.print 'reason');if(!$result.print.ready){return $result}
        $result.ready=$true;$result.reason='exact_lineage_workflow_checks_current';return $result
    }catch{$result.ready=$false;$result.reason='readiness_could_not_be_verified';return $result}
}
function Test-LocalPackageCurrentAuthority($Package,$Lc,$Readiness=$null,$State=$null) {
    try {
        $valid=Get-PropertyValue $Package 'valid'
        if($null-eq$Package-or$valid-isnot[bool]-or!$valid-or[string](Get-PropertyValue $Package 'status')-cne'READY_FOR_MANUAL_UPLOAD'){return $false}
        if($null-eq$Readiness){$Readiness=Get-LocalDeliveryReadiness $Lc $State};if(!$Readiness.ready){return $false}
        $expected=@{concept_revision_id=$Readiness.identity.id;revision_hash=$Readiness.identity.hash;acceptance_fingerprint=[string]$Readiness.acceptance.lineage_fingerprint;artwork_sha256=[string]$Readiness.acceptance.asset_sha256;listing_hash=$Readiness.listing_hash}
        foreach($k in $expected.Keys){if([string](Get-PropertyValue $Package $k)-cne[string]$expected[$k]){return $false}}
        foreach($k in @('marketplace','product_type_key','template_key')){if([string](Get-PropertyValue $Package $k)-cne[string](Get-PropertyValue $Readiness.print.channel_profile $k)){return $false}}
        $path=[string](Get-PropertyValue $Package 'path');$sha=[string](Get-PropertyValue $Package 'sha256')
        if($sha-notmatch'^[0-9a-f]{64}$'-or!(Test-Path -LiteralPath $path -PathType Leaf)-or(Get-FileSha256Hex $path)-cne$sha){return $false}
        $authority=Get-LocalReadyPackageZipAuthority $path $Package ([string]$Lc.concept_key)
        if($null-eq$authority-or$authority.profile_valid_until-lt[DateTime]::UtcNow){return $false}
        $archiveGate=Get-PropertyValue $authority 'gate';$archiveApproval=Get-PropertyValue $archiveGate 'concept_approval'
        foreach($flag in @('all_checks_ready','idea_and_design_approved','print_production_ready')){$value=Get-PropertyValue $archiveGate $flag;if($value-isnot[bool]-or!$value){return $false}}
        $approved=Get-PropertyValue $archiveApproval 'approved';if($approved-isnot[bool]-or!$approved-or[string](Get-PropertyValue $archiveApproval 'brief_sha256')-cne[string]$Readiness.approval.brief_sha256){return $false}
        $archivedPrint=Get-LocalPackageZipJsonEntry $path 'print-production.json';$archivedProfile=Get-PropertyValue $archivedPrint 'channel_profile'
        foreach($flag in @('ready','technical_ready','quality_reviewed')){$value=Get-PropertyValue $archivedPrint $flag;if($value-isnot[bool]-or!$value){return $false}}
        foreach($k in @('concept_revision_id','revision_hash','acceptance_fingerprint','artwork_sha256')){if([string](Get-PropertyValue $archivedPrint $k)-cne[string]$expected[$k]){return $false}}
        if(($archivedProfile|ConvertTo-Json -Depth 40 -Compress)-cne($Readiness.print.channel_profile|ConvertTo-Json -Depth 40 -Compress)){return $false}
        $metadata=Get-LocalPackageZipJsonEntry $path 'metadata.json';$art=Get-PropertyValue $metadata 'accepted_artwork';$name=[string](Get-PropertyValue $art 'file')
        if($name-notmatch'(?i)^artwork\.png$'-or[string](Get-PropertyValue $art 'sha256')-cne[string]$expected.artwork_sha256){return $false}
        if((Get-LocalPackageZipEntrySha256 $path $name)-cne[string]$expected.artwork_sha256-or(Get-LocalPublicationHash (Get-PropertyValue $metadata 'listing'))-cne$Readiness.listing_hash){return $false}
        # Also fence a replacement during the individual ZIP reads. The builder never overwrites package paths.
        return ((Get-FileSha256Hex $path)-ceq$sha)
    }catch{return $false}
}
function Get-LocalCurrentReadyPackageCount($Lc,$State=$null) {
    $candidates=@((Get-PropertyValue $Lc 'packages')|Where-Object{(Get-PropertyValue $_ 'valid')-is[bool]-and[bool](Get-PropertyValue $_ 'valid')-and[string](Get-PropertyValue $_ 'status')-ceq'READY_FOR_MANUAL_UPLOAD'})
    if(!$candidates.Count){return 0}
    $readiness=Get-LocalDeliveryReadiness $Lc $State;if(!$readiness.ready){return 0}
    $count=0;foreach($p in $candidates){if(Test-LocalPackageCurrentAuthority $p $Lc $readiness $State){$count++}};return $count
}
function Get-LocalPackageReadinessText($lc) {
    if($null-ne(Get-PropertyValue $lc 'source_save_intent')){return (Get-UiText 'source.save.pending_package' 'DRAFT package only. Source save is unresolved; reload the saved idea before reviewing readiness.')}
    if(Test-ForgeRecoveryReviewRequired $lc){return (Get-UiText 'recovery.approval.review' 'DRAFT package only. Workspace data was recovered; review and approve the exact saved idea and design again.')}
    if($null-ne$script:Current-and[string](Get-PropertyValue $script:Current.concept 'concept_key')-ceq[string]$lc.concept_key-and($script:Dirty-or$script:PublicationDirty)){return 'DRAFT package only. Save or discard the current concept/listing edits, then review current readiness.'}
    if($null -eq $lc.active_acceptance){return 'Blocked: accept exact artwork first.'};$acc=$lc.active_acceptance;if([string](Get-PropertyValue $acc 'concept_revision_id') -ne [string](Get-PropertyValue $lc 'source_revision_id') -or [string](Get-PropertyValue $acc 'revision_hash') -ne [string](Get-PropertyValue $lc 'source_revision_hash')){return 'Blocked: local acceptance belongs to an older idea revision.'}
    if($null -eq $lc.publication){return 'Blocked: save listing metadata for this exact accepted artwork.'};if([string](Get-PropertyValue $lc.publication 'acceptance_fingerprint') -ne [string](Get-PropertyValue $acc 'lineage_fingerprint')){return 'Blocked: listing metadata belongs to another accepted artwork.'}
    $listing=Get-LocalListingConstraintSnapshot $lc.publication;if(-not $listing.ready){return ('DRAFT package only. '+(($listing.issues|ForEach-Object{$_.message})-join ' '))}
    $identity=[pscustomobject]@{id=[string](Get-PropertyValue $lc 'source_revision_id');hash=[string](Get-PropertyValue $lc 'source_revision_hash')}
    $approval=Get-LocalPackageBriefApprovalSnapshot $lc $identity
    if(!$approval.approved){return 'DRAFT package only. Approve the exact saved idea and design concept again; earlier acceptance does not restore revoked approval.'}
    $print=Get-LocalPrintProductionSnapshot $lc $identity $acc
    if(-not[bool](Get-PropertyValue $print 'ready')){
        $reason=[string](Get-PropertyValue $print 'reason')
        $message=switch($reason){
            'accepted_artwork_dimensions_do_not_match_attested_channel_template' {if($null-ne$print.upload_technical-and$print.upload_technical.dimension_policy-eq'flexible'){return ('DRAFT package only. Upload technical constraint failed: '+$print.upload_technical.reason+'. The 4500 x 5400 template is recommended; enlargement does not prove detail.')};$t=$print.technical;$p=$print.channel_profile;('Accepted image is '+$t.width_px+' x '+$t.height_px+' pixels; the saved channel profile requires '+$p.canvas_width_px+' x '+$p.canvas_height_px+'. No resizing or cropping was performed.')}
            'local_flux_preview_requires_preparation' {'PREVIEW: local FLUX RGB file requires production preparation and exact-file review. Enlarging 512 pixels does not add detail. Import and review the prepared final file; no processing was performed.'}
            'exact_artwork_print_quality_review_required' {'PROCESSING / REVIEW REQUIRED: technical canvas checks passed. Import print review evidence for this exact file after checking sRGB, detail, edges and composition at final print size; alpha alone is insufficient.'}
            'channel_profile_missing_or_expired' {'PROCESSING / REVIEW REQUIRED: a current owner-attested product/channel profile is required. Product dimensions are not assumed.'}
            'accepted_artwork_sha256_mismatch' {'The accepted file has changed. Reimport and review the exact file before accepting it again.'}
            'accepted_png_failed_transparency_validation' {'The accepted PNG failed the existing transparency checks.'}
            'accepted_artwork_is_not_png' {'The saved channel profile requires PNG artwork.'}
            'upload_dimensions_not_allowed' {'The PNG does not meet the saved upload dimension rule. The 4500x5400 template is recommended for the flexible profile; enlargement alone does not establish detail.'}
            'upload_file_size_not_allowed' {'The PNG is not below the saved channel file-size limit. Export a smaller final file, then reimport and review those exact bytes.'}
            'upload_requires_rgb_8bit_png' {'The upload requires RGB PNG at 8 bits per channel. Re-export and review the exact final file; changing dimensions does not fix this format requirement.'}
            {$_-in@('upload_transparency_check_failed','transparent_png_required','native_alpha_channel_missing','png_has_no_alpha_channel')-or$_-like'transparent_canvas_border_required*'} {'The PNG failed transparency checks. Review its background and edge pixels, then reimport the exact prepared file.'}
            'print_artwork_is_empty' {'The PNG contains no visible artwork. An empty transparent image cannot be a print-ready design.'}
            'invalid_upload_rules' {'The saved upload rules could not be verified. Review or reimport the current product/channel profile before preparing an export.'}
            {$_-in@('accepted_artwork_revision_mismatch','saved_concept_revision_mismatch','accepted_artwork_fingerprint_mismatch')} {'The acceptance does not match the saved idea revision and exact artwork. Review and accept the current file again.'}
            default {'The accepted file could not be decoded and verified.'}
        }
        return ('DRAFT package only. '+$message)
    }
    $missing=@();foreach($n in @('ip','visual','print','policy','metadata')){if(-not(Test-LocalCheckPass (Get-PropertyValue $lc.checks $n) $lc $n)){$missing+=$n}}
    if($missing.Count -eq 0){return 'READY for manual-upload package creation. Exact revision/artwork/listing lineage is verified locally.'};return ('DRAFT package only. Exact-lineage checks need attention: '+($missing -join ', ')+'.')
}
function New-LocalPackageExportToken {return ([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff')+'-'+[Guid]::NewGuid().ToString('N'))}
function Assert-LocalPackageWorkspacePath([string]$Path) {
    $root=[IO.Path]::GetFullPath($script:LocalCorePackageRoot).TrimEnd('\');$full=[IO.Path]::GetFullPath($Path)
    if(!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Package staging path escaped its local package root.'}
    $walk=New-Object IO.DirectoryInfo $full
    while($null-ne$walk){
        if(Test-Path -LiteralPath $walk.FullName){$item=Get-Item -LiteralPath $walk.FullName -Force;if($item.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'Package staging path traverses a redirected directory.'}}
        if($walk.FullName-eq$root){return};$walk=$walk.Parent
    }
    throw 'Package staging root could not be verified.'
}
function Assert-LocalPackageStage([string]$Stage,[string]$ArtworkName,[switch]$IncludeManifest) {
    Assert-LocalPackageWorkspacePath $Stage
    $expected=@($ArtworkName,'print-production.json','metadata.json','preupload-gate.json','LISTING.txt');if($IncludeManifest){$expected+='manifest.json'}
    $items=@(Get-ChildItem -LiteralPath $Stage -Force)
    if($items.Count-ne$expected.Count){throw 'Unexpected package stage contents; all files were retained.'}
    foreach($item in $items){if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-or$expected-notcontains$item.Name){throw 'Unknown or redirected package stage content was retained.'}}
}
function Clear-LocalPackageStage([string]$Stage,[string]$ArtworkName) {
    Assert-LocalPackageStage $Stage $ArtworkName -IncludeManifest
    Remove-Item -LiteralPath ([IO.Path]::GetFullPath($Stage)) -Recurse -Force
}
function Write-LocalPackageReceipt([string]$Path,[string]$Json) {
    Assert-LocalPackageWorkspacePath $Path
    $pending=$Path+'.pending.'+[Guid]::NewGuid().ToString('N')
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($Json)
    $stream=New-Object IO.FileStream($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    [IO.File]::Move($pending,$Path)
}
function Get-LocalPackageCommitOutcome($Expected) {
    if($null-eq$Expected){return 'not_committed'}
    try{
        $state=Read-LocalCoreState
        foreach($concept in $state.concepts){foreach($record in @(Get-PropertyValue $concept 'packages')){
            if($null-eq$record-or[string](Get-PropertyValue $record 'path')-cne[string]$Expected.path){continue}
            foreach($name in @('sha256','status','concept_revision_id','revision_hash','artwork_sha256','listing_hash','preupload_gate_sha256','print_production_sha256')){if([string](Get-PropertyValue $record $name)-cne[string](Get-PropertyValue $Expected $name)){return 'unknown'}}
            if((Get-FileSha256Hex $Expected.path)-cne$Expected.sha256){return 'unknown'}
            return 'committed'
        }}
        return 'not_committed'
    }catch{return 'unknown'}
}
function Build-LocalAmazonPackage {
    if($null -eq $script:Current){return}
    $createdZip='';$createdReceipt='';$packageCommitted=$false;$pkg=$null
    try {
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc -or $null -eq $lc.active_acceptance){throw 'Accept exact local artwork first.'};if(-not(Save-LocalPublicationMetadata)){throw 'Local listing draft could not be saved.'}
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;$acc=$lc.active_acceptance;$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept
        if([string]$acc.concept_revision_id -ne $identity.id -or [string]$acc.revision_hash -ne $identity.hash){throw 'Acceptance lineage is stale for the current idea revision.'};if([string](Get-PropertyValue $lc.publication 'acceptance_fingerprint') -ne [string]$acc.lineage_fingerprint){throw 'Listing metadata is not bound to the current accepted artwork.'}
        $art=[string]$acc.local_file_path;$sha=[string]$acc.asset_sha256;if(-not(Test-Path -LiteralPath $art -PathType Leaf) -or (Get-FileSha256Hex $art) -ne $sha){throw 'Accepted local artwork failed SHA-256 verification.'}
        $packageArtwork=Get-LocalArtworkInfo $art;if($packageArtwork.sha256-cne$sha){throw 'Accepted artwork changed during format capture. No new package was created.'}
        $briefApproval=Get-LocalPackageBriefApprovalSnapshot $lc $identity
        $printProduction=Get-LocalPrintProductionSnapshot $lc $identity $acc;$gate=Get-LocalCheckGateSnapshot $lc;$checksReady=([bool]$gate.all_ready -and [bool](Get-PropertyValue $printProduction 'ready') -and $briefApproval.approved)
        $economics=Get-LocalEconomicsSnapshot $lc;$status=if($checksReady){'READY_FOR_MANUAL_UPLOAD'}else{'DRAFT_BLOCKED'};$listingHash=Get-LocalPublicationHash $lc.publication
        $safe=Get-LocalCoreSafeKey $lc.concept_key;$stamp=New-LocalPackageExportToken;$stage=Join-Path $script:LocalCorePackageRoot ($safe+'-'+$stamp+'-stage');Assert-LocalPackageWorkspacePath $stage;if(Test-Path -LiteralPath $stage){throw 'An existing package stage was preserved; retry creates a new transaction.'};New-Item -ItemType Directory -Path $stage -ErrorAction Stop|Out-Null;$ext=$packageArtwork.extension;$artName='artwork'+$ext;Copy-LocalAcceptedArtworkForPackage $art (Join-Path $stage $artName) $sha
        $printPath=Join-Path $stage 'print-production.json';$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($printPath,($printProduction|ConvertTo-Json -Depth 40),$utf8);$printSha=Get-FileSha256Hex $printPath;$metadata=[ordered]@{schema='forge.amazon_manual_package.v3';status=$status;concept_key=$lc.concept_key;title=$lc.title;hook=$lc.hook;lineage=[ordered]@{concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string]$acc.lineage_fingerprint;accepted_artwork_sha256=$sha;listing_hash=$listingHash};accepted_artwork=[ordered]@{file=$artName;sha256=$sha;variant_id=$acc.variant_id;accepted_at=$acc.accepted_at;source=$acc.source;generation_request_id=[string](Get-PropertyValue $acc 'generation_request_id');provider_key=[string](Get-PropertyValue $acc 'provider_key');provider_profile=[string](Get-PropertyValue $acc 'provider_profile');provider_model=[string](Get-PropertyValue $acc 'provider_model');provider_contract_version=[string](Get-PropertyValue $acc 'provider_contract_version');provider_registry_sha256=[string](Get-PropertyValue $acc 'provider_registry_sha256');provider_config_fingerprint=[string](Get-PropertyValue $acc 'provider_config_fingerprint');prompt_compiler_version=[string](Get-PropertyValue $acc 'prompt_compiler_version');prompt_template_sha256=[string](Get-PropertyValue $acc 'prompt_template_sha256');provider_request_id=[string](Get-PropertyValue $acc 'provider_request_id');generation_result_sha256=[string](Get-PropertyValue $acc 'generation_result_sha256');generation_attempt_sha256=[string](Get-PropertyValue $acc 'generation_attempt_sha256');prompt_sha256=[string](Get-PropertyValue $acc 'prompt_sha256');revised_prompt=[string](Get-PropertyValue $acc 'revised_prompt');provider_usage=(Get-PropertyValue $acc 'provider_usage');preparation=(Get-PropertyValue $acc 'preparation')};listing=$lc.publication;concept_approval=$briefApproval;economics=$economics;checks=$lc.checks;check_gate=$gate;print_production=$printProduction;print_production_sha256=$printSha;external_submission_authorized=$false;manual_upload_required=$true;created_at=[DateTime]::UtcNow.ToString('o')};[IO.File]::WriteAllText((Join-Path $stage 'metadata.json'),($metadata|ConvertTo-Json -Depth 40),$utf8);$preupload=[ordered]@{schema='forge.preupload_gate.v1';status=$status;concept_key=[string]$lc.concept_key;lineage=[ordered]@{concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string]$acc.lineage_fingerprint;accepted_artwork_sha256=$sha;listing_hash=$listingHash};all_checks_ready=$checksReady;idea_and_design_approved=[bool]$briefApproval.approved;concept_approval=$briefApproval;economics=$economics;checks=$gate.checks;print_production_sha256=$printSha;print_production_ready=[bool](Get-PropertyValue $printProduction 'ready');authority_boundary='READY means exact-lineage workflow evidence is present; IP owner attestation is not a legal opinion; external submission remains manual.';external_submission_authorized=$false;created_at=[DateTime]::UtcNow.ToString('o')};$preuploadPath=Join-Path $stage 'preupload-gate.json';[IO.File]::WriteAllText($preuploadPath,($preupload|ConvertTo-Json -Depth 40),$utf8);$preuploadSha=Get-FileSha256Hex $preuploadPath;$listing=@('MERCH FORGE — MANUAL UPLOAD PACKAGE',"Status: $status",'',"Concept revision: $($identity.id)","Revision SHA256: $($identity.hash)","Acceptance fingerprint: $($acc.lineage_fingerprint)","Listing SHA256: $listingHash",'',"Listing title: $($lc.publication.listing_title)","Brand: $($lc.publication.brand)","Bullet 1: $($lc.publication.bullet_1)","Bullet 2: $($lc.publication.bullet_2)","Description: $($lc.publication.description)","Keywords: $(@($lc.publication.keywords)-join ', ')","Locale: $($lc.publication.locale)",'',"Artwork SHA256: $sha",'','ECONOMICS - owner-entered assumptions only',(Format-LocalEconomicsSnapshot $economics),'Boundary: local package only. Nothing was uploaded or submitted by Merch Forge.') -join "`r`n";[IO.File]::WriteAllText((Join-Path $stage 'LISTING.txt'),$listing,$utf8)
        Assert-LocalPackageStage $stage $artName;$manifest=@();foreach($f in @(Get-ChildItem -LiteralPath $stage -File|Sort-Object Name)){$manifest+=[ordered]@{file=$f.Name;size_bytes=$f.Length;sha256=(Get-FileSha256Hex $f.FullName)}};[IO.File]::WriteAllText((Join-Path $stage 'manifest.json'),([ordered]@{hash_algorithm='SHA-256';lineage_fingerprint=[string]$acc.lineage_fingerprint;files=$manifest}|ConvertTo-Json -Depth 10),$utf8)
        Add-Type -AssemblyName System.IO.Compression.FileSystem;$zipName=($safe+'-'+$status+'-'+$stamp+'.zip');$zip=Join-Path $script:LocalCorePackageRoot $zipName;if(Test-Path -LiteralPath $zip){throw 'A local package with this name already exists; nothing was overwritten.'};$pendingZip=$zip+'.pending.'+[Guid]::NewGuid().ToString('N');[IO.Compression.ZipFile]::CreateFromDirectory($stage,$pendingZip,[IO.Compression.CompressionLevel]::Optimal,$false);if((Get-LocalPackageZipEntrySha256 $pendingZip $artName)-cne$sha){throw 'Final package artwork failed exact accepted SHA-256 verification.'};[IO.File]::Move($pendingZip,$zip);$createdZip=$zip;$pkgSha=Get-FileSha256Hex $zip
        $receiptProfile=Get-PropertyValue $printProduction 'channel_profile';$receiptMarketplace=if($null-ne$receiptProfile){([string](Get-PropertyValue $receiptProfile 'marketplace')).Trim()}else{''};$receiptProductType=if($null-ne$receiptProfile){([string](Get-PropertyValue $receiptProfile 'product_type_key')).Trim()}else{''};$receiptTemplateKey=if($null-ne$receiptProfile){([string](Get-PropertyValue $receiptProfile 'template_key')).Trim()}else{''};$receiptTemplatePath=$zip+'.publication-receipt.json';$receiptTemplate=[ordered]@{schema='forge.local_publication_receipt.v3';concept_key=[string]$lc.concept_key;package_sha256=$pkgSha;lineage_fingerprint=[string]$acc.lineage_fingerprint;listing_hash=$listingHash;preupload_gate_sha256=$preuploadSha;print_production_sha256=$printSha;channel='amazon_merch';marketplace=$receiptMarketplace;product_type_key=$receiptProductType;template_key=$receiptTemplateKey;product_id='';published_at='';source='owner_manual_upload_receipt';note='Fill product_id and published_at after manual publication, then import this receipt into Forge.'};Write-LocalPackageReceipt $receiptTemplatePath ($receiptTemplate|ConvertTo-Json -Depth 10);$createdReceipt=$receiptTemplatePath
        $pkg=[pscustomobject]@{path=$zip;sha256=$pkgSha;status=$status;valid=$true;concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string]$acc.lineage_fingerprint;artwork_sha256=$sha;listing_hash=$listingHash;preupload_gate_sha256=$preuploadSha;print_production_sha256=$printSha;marketplace=$receiptMarketplace;product_type_key=$receiptProductType;template_key=$receiptTemplateKey;channel_profile_captured_at=if($null-ne$receiptProfile){[string](Get-PropertyValue $receiptProfile 'captured_at')}else{''};channel_profile_valid_until=if($null-ne$receiptProfile){[string](Get-PropertyValue $receiptProfile 'valid_until')}else{''};created_at=[DateTime]::UtcNow.ToString('o');manual_upload_required=$true;external_submission_authorized=$false;publication_receipt_template=$receiptTemplatePath};$lc.packages=@($lc.packages)+@($pkg);Write-LocalCoreState $s;$packageCommitted=$true;try{Clear-LocalPackageStage $stage $artName}catch{Write-AppLog 'WARN' ('Package committed; staging retained because cleanup was not safe or available: '+$_.Exception.Message)}
        $DeliveryStatus.Text=("Local package created: {0}`nStatus: {1}`nSHA-256: {2}`nPublication receipt template: {3}" -f $zip,$status,$pkgSha,$receiptTemplatePath);$PublicationPreflight.Text=Get-LocalPackageReadinessText $lc;$StatusText.Text=('Local manual-upload package created. Status: '+$status)
    } catch {
        $failure=$_.Exception.Message;$outcome=Get-LocalPackageCommitOutcome $pkg
        if($outcome-ceq'committed'){
            $packageCommitted=$true
            try{Clear-LocalPackageStage $stage $artName}catch{}
            $DeliveryStatus.Text='Package commit verified after a follow-up error: '+$createdZip
            $StatusText.Text='Package saved and verified; a backup or follow-up step reported an error.'
            Write-AppLog 'WARN' ('Export commit verified; archive retained at its recorded path. '+$failure)
            return
        }
        $detail=''
        if($createdZip-and(Test-Path -LiteralPath $createdZip -PathType Leaf)){
            if($outcome-ceq'not_committed'){
                $retained=$createdZip+'.uncommitted.'+[Guid]::NewGuid().ToString('N')
                try{
                    [IO.File]::Move($createdZip,$retained)
                    if($createdReceipt-and(Test-Path -LiteralPath $createdReceipt -PathType Leaf)){[IO.File]::Move($createdReceipt,($retained+'.publication-receipt.json'))}
                    $detail='Uncommitted archive retained: '+$retained
                }catch{$detail='Export recovery could not rename every artifact; all files were preserved. Inspect '+$createdZip+' and '+$retained+'. '+$_.Exception.Message}
            }else{$detail='Export commit could not be verified. Archive preserved at '+$createdZip+'. Refresh local state before retrying.'}
            try{Write-LocalPackageReceipt ($createdZip+'.recovery.'+[Guid]::NewGuid().ToString('N')+'.json') ([ordered]@{schema='forge.export_recovery.v1';state_commit_outcome=$outcome;archive_original_path=$createdZip;receipt_original_path=$createdReceipt;detail=$detail;error=$failure;external_submission_authorized=$false;created_at=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Depth 8)}catch{}
            Write-AppLog 'WARN' $detail
        }
        $StatusText.Text=if($outcome-ceq'unknown'){'Local package completion is uncertain; archive preserved. Refresh state before retrying.'}else{'Local package creation failed; artifacts preserved.'}
        Show-Error ($failure+$(if($detail){"`r`n"+$detail}else{''}))
    }
}
function Get-LocalPackageZipEntrySha256([string]$ZipPath,[string]$EntryName,[long]$MaxBytes=([long]::MaxValue)) {
    $zip=$null;$stream=$null;$hash=$null
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath);$entries=@($zip.Entries|Where-Object{[string]::Equals([string]$_.FullName,$EntryName,[StringComparison]::OrdinalIgnoreCase)})
        if($entries.Count-ne1-or[string]$entries[0].FullName-cne$EntryName){return ''}
        if($EntryName.EndsWith('.json',[StringComparison]::OrdinalIgnoreCase)){$MaxBytes=[Math]::Min($MaxBytes,[long]32MB)}
        if($entries[0].Length-gt$MaxBytes){return ''}
        $stream=$entries[0].Open();$hash=[Security.Cryptography.SHA256]::Create();[byte[]]$buffer=New-Object byte[] 8192;$total=[long]0
        while(($read=$stream.Read($buffer,0,$buffer.Length))-gt0){$total+=$read;if($total-gt$MaxBytes){return ''};$null=$hash.TransformBlock($buffer,0,$read,$buffer,0)}
        $null=$hash.TransformFinalBlock([byte[]]@(),0,0);return ([BitConverter]::ToString($hash.Hash)).Replace('-','').ToLowerInvariant()
    } catch {return ''}
    finally {if($null-ne$hash){$hash.Dispose()};if($null-ne$stream){$stream.Dispose()};if($null-ne$zip){$zip.Dispose()}}
}
function Test-LocalPackageBoolean($Object,[string]$Name,[bool]$Expected) {
    $value=Get-PropertyValue $Object $Name;return ($value-is[bool]-and$value-eq$Expected)
}
function Get-LocalPackageZipJsonEntry([string]$ZipPath,[string]$EntryName) {
    $zip=$null;$stream=$null;$memory=$null
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
        $matches=@($zip.Entries|Where-Object{[string]::Equals([string]$_.FullName,$EntryName,[StringComparison]::OrdinalIgnoreCase)})
        if($matches.Count-ne1-or[string]$matches[0].FullName-cne$EntryName-or$matches[0].Length-gt32MB){return $null}
        $stream=$matches[0].Open();$memory=New-Object IO.MemoryStream;[byte[]]$buffer=New-Object byte[] 8192
        while(($read=$stream.Read($buffer,0,$buffer.Length))-gt0){if($memory.Length+$read-gt32MB){return $null};$memory.Write($buffer,0,$read)}
        $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($memory.ToArray()).TrimStart([char]0xfeff)
        return (ConvertFrom-ForgeJsonObjectStrict $text)
    } catch {return $null}
    finally {if($null-ne$memory){$memory.Dispose()};if($null-ne$stream){$stream.Dispose()};if($null-ne$zip){$zip.Dispose()}}
}
function Test-LocalPackageArtworkTechnical([string]$ZipPath,[string]$EntryName,[string]$ExpectedSha,$Profile) {
    $zip=$null;$stream=$null;$memory=$null
    try {
        $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath);$entries=@($zip.Entries|Where-Object{$_.FullName-ieq$EntryName})
        if($entries.Count-ne1-or$entries[0].FullName-cne$EntryName-or$entries[0].Length-le0-or$entries[0].Length-ge26214400){return $false}
        $stream=$entries[0].Open();$memory=New-Object IO.MemoryStream;$buffer=New-Object byte[] 65536
        while(($read=$stream.Read($buffer,0,$buffer.Length))-gt0){if($memory.Length+$read-ge26214400){return $false};$memory.Write($buffer,0,$read)}
        $bytes=$memory.ToArray();if((Get-ByteSha256Hex $bytes)-cne$ExpectedSha){return $false}
        if(!(Test-ForgeFlexibleUploadRules $Profile)){return $false}
        $meta=Get-ForgePngMetadata $bytes;if(!(Get-PropertyValue $meta 'valid')){return $false}
        $png=Test-ForgePrintPngBytes $bytes ([int](Get-PropertyValue $meta 'width')) ([int](Get-PropertyValue $meta 'height'))
        if(!(Get-PropertyValue $png 'ok')){return $false}
        $upload=Get-ForgeUploadTechnicalSnapshot $bytes $Profile
        return [bool](Get-PropertyValue $upload 'ok')
    }catch{return $false}finally{if($null-ne$memory){$memory.Dispose()};if($null-ne$stream){$stream.Dispose()};if($null-ne$zip){$zip.Dispose()}}
}
function Get-LocalReadyPackageZipAuthority([string]$ZipPath,$Package,[string]$ConceptKey) {
    $archiveLock=$null
    try {
        if([string]::IsNullOrWhiteSpace($ZipPath) -or -not(Test-Path -LiteralPath $ZipPath -PathType Leaf) -or $null-eq$Package){return $null}
        $expectedZipSha=([string](Get-PropertyValue $Package 'sha256')).ToLowerInvariant();if($expectedZipSha-cnotmatch'^[0-9a-f]{64}$'){return $null}
        $archiveLock=[IO.File]::Open($ZipPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $hash=[Security.Cryptography.SHA256]::Create();try{$actualZipSha=([BitConverter]::ToString($hash.ComputeHash($archiveLock))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
        if($actualZipSha-cne$expectedZipSha){return $null}
        $expectedGateSha=([string](Get-PropertyValue $Package 'preupload_gate_sha256')).Trim().ToLowerInvariant();$expectedPrintSha=([string](Get-PropertyValue $Package 'print_production_sha256')).Trim().ToLowerInvariant();if($expectedGateSha -notmatch '^[0-9a-f]{64}$' -or $expectedPrintSha -notmatch '^[0-9a-f]{64}$'){return $null}
        $actualGateSha=Get-LocalPackageZipEntrySha256 $ZipPath 'preupload-gate.json';$actualPrintSha=Get-LocalPackageZipEntrySha256 $ZipPath 'print-production.json';if($actualGateSha -ne $expectedGateSha -or $actualPrintSha -ne $expectedPrintSha){return $null}
        $gate=Get-LocalPackageZipJsonEntry $ZipPath 'preupload-gate.json';if($null-eq$gate -or [string](Get-PropertyValue $gate 'schema') -ne 'forge.preupload_gate.v1' -or [string](Get-PropertyValue $gate 'status') -ne 'READY_FOR_MANUAL_UPLOAD' -or [bool](Get-PropertyValue $gate 'all_checks_ready') -ne $true -or [bool](Get-PropertyValue $gate 'print_production_ready') -ne $true -or [bool](Get-PropertyValue $gate 'external_submission_authorized') -ne $false){return $null}
        if(([string](Get-PropertyValue $gate 'concept_key')).Trim() -ne ([string]$ConceptKey).Trim()){return $null};$lineage=Get-PropertyValue $gate 'lineage';if($null-eq$lineage){return $null}
        $pairs=@(@('concept_revision_id','concept_revision_id'),@('revision_hash','revision_hash'),@('acceptance_fingerprint','acceptance_fingerprint'),@('accepted_artwork_sha256','artwork_sha256'),@('listing_hash','listing_hash'));foreach($pair in $pairs){$left=([string](Get-PropertyValue $lineage $pair[0])).Trim().ToLowerInvariant();$right=([string](Get-PropertyValue $Package $pair[1])).Trim().ToLowerInvariant();if([string]::IsNullOrWhiteSpace($left) -or [string]::IsNullOrWhiteSpace($right) -or $left-ne$right){return $null}}
        $gatePrint=([string](Get-PropertyValue $gate 'print_production_sha256')).Trim().ToLowerInvariant();if($gatePrint -ne $expectedPrintSha){return $null};$gateCreatedRaw=([string](Get-PropertyValue $gate 'created_at')).Trim();try{$gateCreated=[DateTime]::Parse($gateCreatedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $null};if($gateCreated -gt [DateTime]::UtcNow.AddMinutes(10)){return $null}
        $print=Get-LocalPackageZipJsonEntry $ZipPath 'print-production.json';if($null-eq$print -or [string](Get-PropertyValue $print 'schema') -ne 'forge.print_production_snapshot.v1' -or [bool](Get-PropertyValue $print 'ready') -ne $true){return $null};$profile=Get-PropertyValue $print 'channel_profile';if(!(Test-ForgeAmazonPrintProfile $profile $false)){return $null};if($null-eq$profile -or [string](Get-PropertyValue $profile 'schema') -ne 'forge.amazon_print_profile.v1' -or [bool](Get-PropertyValue $profile 'attested') -ne $true -or [string](Get-PropertyValue $profile 'authority_kind') -ne 'owner_attested_external'){return $null};$marketplace=([string](Get-PropertyValue $profile 'marketplace')).Trim();$productType=([string](Get-PropertyValue $profile 'product_type_key')).Trim();$templateKey=([string](Get-PropertyValue $profile 'template_key')).Trim();if([string]::IsNullOrWhiteSpace($marketplace) -or [string]::IsNullOrWhiteSpace($productType) -or [string]::IsNullOrWhiteSpace($templateKey)){return $null}
        $profileCapturedRaw=([string](Get-PropertyValue $profile 'captured_at')).Trim();$profileValidRaw=([string](Get-PropertyValue $profile 'valid_until')).Trim();try{$profileCaptured=[DateTime]::Parse($profileCapturedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime();$profileValidUntil=[DateTime]::Parse($profileValidRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $null};if($profileCaptured -gt [DateTime]::UtcNow.AddMinutes(10) -or $profileValidUntil -le $profileCaptured -or ($profileValidUntil-$profileCaptured).TotalDays -gt 120){return $null};if($gateCreated -lt $profileCaptured.AddMinutes(-10) -or $gateCreated -gt $profileValidUntil){return $null}
        foreach($name in @('all_checks_ready','idea_and_design_approved','print_production_ready')){if(!(Test-LocalPackageBoolean $gate $name $true)){return $null}}
        if(!(Test-LocalPackageBoolean $gate 'external_submission_authorized' $false)){return $null}
        $approval=Get-PropertyValue $gate 'concept_approval';if(!(Test-LocalPackageBoolean $approval 'approved' $true)-or[string](Get-PropertyValue $approval 'brief_sha256')-cnotmatch'^[0-9a-f]{64}$'){return $null}
        foreach($name in @('ip','visual','print','policy','metadata')){$item=Get-PropertyValue (Get-PropertyValue $gate 'checks') $name;if(!(Test-LocalPackageBoolean $item 'ready' $true)-or[string](Get-PropertyValue $item 'state')-notin@('pass','not_required')){return $null}}
        foreach($name in @('ready','technical_ready','quality_reviewed')){if(!(Test-LocalPackageBoolean $print $name $true)){return $null}}
        if(!(Test-LocalPackageBoolean $profile 'attested' $true)-or!(Test-LocalPackageBoolean $profile 'independent_verification' $false)){return $null}
        foreach($pair in @(@('concept_revision_id','concept_revision_id'),@('revision_hash','revision_hash'),@('acceptance_fingerprint','acceptance_fingerprint'),@('artwork_sha256','artwork_sha256'))){if([string](Get-PropertyValue $print $pair[0])-cne[string](Get-PropertyValue $Package $pair[1])){return $null}}
        $metadata=Get-LocalPackageZipJsonEntry $ZipPath 'metadata.json'
        if($null-eq$metadata-or[string](Get-PropertyValue $metadata 'schema')-cne'forge.amazon_manual_package.v3'-or[string](Get-PropertyValue $metadata 'status')-cne'READY_FOR_MANUAL_UPLOAD'-or[string](Get-PropertyValue $metadata 'concept_key')-cne$ConceptKey){return $null}
        if(!(Test-LocalPackageBoolean $metadata 'manual_upload_required' $true)-or!(Test-LocalPackageBoolean $metadata 'external_submission_authorized' $false)){return $null}
        foreach($pair in $pairs){if([string](Get-PropertyValue (Get-PropertyValue $metadata 'lineage') $pair[0])-cne[string](Get-PropertyValue $Package $pair[1])){return $null}}
        $metaApproval=Get-PropertyValue $metadata 'concept_approval';if(!(Test-LocalPackageBoolean $metaApproval 'approved' $true)-or[string](Get-PropertyValue $metaApproval 'brief_sha256')-cne[string](Get-PropertyValue $approval 'brief_sha256')){return $null}
        if([string](Get-PropertyValue $metadata 'print_production_sha256')-cne$expectedPrintSha-or(Get-PropertyValue $metadata 'print_production'|ConvertTo-Json -Depth 40 -Compress)-cne($print|ConvertTo-Json -Depth 40 -Compress)){return $null}
        if((Get-LocalPublicationHash (Get-PropertyValue $metadata 'listing'))-cne[string](Get-PropertyValue $Package 'listing_hash')){return $null}
        $asset=Get-PropertyValue $metadata 'accepted_artwork';$assetName=[string](Get-PropertyValue $asset 'file');$assetSha=[string](Get-PropertyValue $asset 'sha256')
        if(!$assetName-or[IO.Path]::GetFileName($assetName)-cne$assetName-or$assetName-notmatch'\.png$'-or$assetSha-cne[string](Get-PropertyValue $Package 'artwork_sha256')-or(Get-LocalPackageZipEntrySha256 $ZipPath $assetName 26214400)-cne$assetSha){return $null}
        if(!(Test-LocalPackageArtworkTechnical $ZipPath $assetName $assetSha $profile)){return $null}
        return [pscustomobject]@{gate=$gate;gate_sha256=$actualGateSha;print_production_sha256=$actualPrintSha;created_at=$gateCreated;marketplace=$marketplace;product_type_key=$productType;template_key=$templateKey;profile_captured_at=$profileCaptured;profile_valid_until=$profileValidUntil}
    } catch {return $null} finally {if($null-ne$archiveLock){$archiveLock.Dispose()}}
}
function Get-LocalPublicationProductKey($Receipt) {
    try {
        if($null -eq $Receipt){return ''};$channel=([string](Get-PropertyValue $Receipt 'channel')).Trim().ToLowerInvariant();$marketplace=([string](Get-PropertyValue $Receipt 'marketplace')).Trim().ToLowerInvariant();$productId=([string](Get-PropertyValue $Receipt 'product_id')).Trim().ToLowerInvariant();if([string]::IsNullOrWhiteSpace($channel) -or [string]::IsNullOrWhiteSpace($productId)){return ''};if([string]::IsNullOrWhiteSpace($marketplace)){return ($channel+'|'+$productId).ToLowerInvariant()};return ($channel+'|'+$marketplace+'|'+$productId).ToLowerInvariant()
    } catch {return ''}
}
function Test-LocalPublicationReceiptAuthority($State,$Receipt) {
    try {
        if($null -eq $State -or $null -eq $Receipt -or -not(Test-LocalPackageBoolean $Receipt 'lineage_verified' $true)){return $false}
        $conceptKey=([string](Get-PropertyValue $Receipt 'concept_key')).Trim();if([string]::IsNullOrWhiteSpace($conceptKey)){return $false}
        $packageSha=([string](Get-PropertyValue $Receipt 'package_sha256')).Trim().ToLowerInvariant();if($packageSha -notmatch '^[0-9a-f]{64}$'){return $false}
        $lc=Get-LocalCoreConcept $conceptKey $State;if($null -eq $lc){return $false};$packageMatch=$null;foreach($pkg in @((Get-PropertyValue $lc 'packages'))){if(([string](Get-PropertyValue $pkg 'sha256')).Trim().ToLowerInvariant() -eq $packageSha){$packageMatch=$pkg;break}};if($null -eq $packageMatch){return $false}
        if([string](Get-PropertyValue $packageMatch 'status') -ne 'READY_FOR_MANUAL_UPLOAD'){return $false}
        $packagePrintHint=([string](Get-PropertyValue $packageMatch 'print_production_sha256')).Trim().ToLowerInvariant();$modernPrintBoundPackage=(-not[string]::IsNullOrWhiteSpace($packagePrintHint));$zipAuthority=$null;$packagePath=([string](Get-PropertyValue $packageMatch 'path')).Trim();if(-not[string]::IsNullOrWhiteSpace($packagePath) -and (Test-Path -LiteralPath $packagePath -PathType Leaf)){if((Get-FileSha256Hex $packagePath) -ne $packageSha){return $false};if($modernPrintBoundPackage){$zipAuthority=Get-LocalReadyPackageZipAuthority $packagePath $packageMatch $conceptKey;if($null-eq$zipAuthority){return $false}}}
        $fp=([string](Get-PropertyValue $Receipt 'lineage_fingerprint')).Trim().ToLowerInvariant();$lh=([string](Get-PropertyValue $Receipt 'listing_hash')).Trim().ToLowerInvariant();$gateSha=([string](Get-PropertyValue $Receipt 'preupload_gate_sha256')).Trim().ToLowerInvariant();if($fp -notmatch '^[0-9a-f]{64}$' -or $lh -notmatch '^[0-9a-f]{64}$' -or $gateSha -notmatch '^[0-9a-f]{64}$'){return $false}
        if($fp -ne ([string](Get-PropertyValue $packageMatch 'acceptance_fingerprint')).Trim().ToLowerInvariant() -or $lh -ne ([string](Get-PropertyValue $packageMatch 'listing_hash')).Trim().ToLowerInvariant() -or $gateSha -ne ([string](Get-PropertyValue $packageMatch 'preupload_gate_sha256')).Trim().ToLowerInvariant()){return $false}
        $receiptPrint=([string](Get-PropertyValue $Receipt 'print_production_sha256')).Trim().ToLowerInvariant();$packagePrint=([string](Get-PropertyValue $packageMatch 'print_production_sha256')).Trim().ToLowerInvariant();if(-not[string]::IsNullOrWhiteSpace($receiptPrint) -or -not[string]::IsNullOrWhiteSpace($packagePrint)){if($receiptPrint -notmatch '^[0-9a-f]{64}$' -or $packagePrint -notmatch '^[0-9a-f]{64}$' -or $receiptPrint -ne $packagePrint){return $false}}
        $channel=([string](Get-PropertyValue $Receipt 'channel')).Trim().ToLowerInvariant();$marketplace=([string](Get-PropertyValue $Receipt 'marketplace')).Trim().ToLowerInvariant();$productId=([string](Get-PropertyValue $Receipt 'product_id')).Trim();if($channel -ne 'amazon_merch' -or [string]::IsNullOrWhiteSpace($productId)){return $false};if($modernPrintBoundPackage){$expectedMarketplace=if($null-ne$zipAuthority){([string](Get-PropertyValue $zipAuthority 'marketplace')).Trim().ToLowerInvariant()}else{([string](Get-PropertyValue $packageMatch 'marketplace')).Trim().ToLowerInvariant()};if(-not[string]::IsNullOrWhiteSpace($expectedMarketplace)){if([string]::IsNullOrWhiteSpace($marketplace) -or $marketplace -ne $expectedMarketplace){return $false}}elseif([string]::IsNullOrWhiteSpace($marketplace)){return $false}};$legacyKey=($channel+'|'+$productId).ToLowerInvariant();$derivedKey=Get-LocalPublicationProductKey $Receipt;$storedKey=([string](Get-PropertyValue $Receipt 'product_key')).Trim().ToLowerInvariant();if(-not[string]::IsNullOrWhiteSpace($storedKey) -and $storedKey -ne $derivedKey -and $storedKey -ne $legacyKey){return $false}
        $publishedRaw=([string](Get-PropertyValue $Receipt 'published_at')).Trim();if([string]::IsNullOrWhiteSpace($publishedRaw)){return $false};$published=$null;try{$published=[DateTime]::Parse($publishedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $false};if($published -gt [DateTime]::UtcNow.AddMinutes(10)){return $false};$packageCreated=$null;$profileValidUntil=$null;if($null-ne$zipAuthority){$packageCreated=[DateTime](Get-PropertyValue $zipAuthority 'created_at');$profileValidUntil=[DateTime](Get-PropertyValue $zipAuthority 'profile_valid_until')}else{$packageCreatedRaw=([string](Get-PropertyValue $packageMatch 'created_at')).Trim();if(-not[string]::IsNullOrWhiteSpace($packageCreatedRaw)){try{$packageCreated=[DateTime]::Parse($packageCreatedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $false};if($packageCreated -gt [DateTime]::UtcNow.AddMinutes(10)){return $false}};$profileValidRaw=([string](Get-PropertyValue $packageMatch 'channel_profile_valid_until')).Trim();if(-not[string]::IsNullOrWhiteSpace($profileValidRaw)){try{$profileValidUntil=[DateTime]::Parse($profileValidRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $false}}};if($null-ne$packageCreated -and $published -lt $packageCreated.AddMinutes(-10)){return $false};if($null-ne$profileValidUntil -and $published -gt $profileValidUntil){return $false}
        return $true
    } catch {return $false}
}
function Get-LocalPublicationReceiptBindingDecision($State,[string]$ConceptKey,[string]$PackageSha,[string]$Fingerprint,[string]$ListingHash,[string]$GateSha,[string]$PrintSha,[string]$Channel,[string]$Marketplace,[string]$ProductId) {
    $wantChannel=([string]$Channel).Trim().ToLowerInvariant();$wantMarketplace=([string]$Marketplace).Trim().ToLowerInvariant();$wantProduct=([string]$ProductId).Trim().ToLowerInvariant();if([string]::IsNullOrWhiteSpace($wantChannel) -or [string]::IsNullOrWhiteSpace($wantProduct)){return [pscustomobject]@{status='none';existing=$null}};$sameExisting=$null
    foreach($existing in @((Get-PropertyValue $State 'publication_receipts'))){
        if(-not(Test-LocalPublicationReceiptAuthority $State $existing)){continue};$exChannel=([string](Get-PropertyValue $existing 'channel')).Trim().ToLowerInvariant();$exMarketplace=([string](Get-PropertyValue $existing 'marketplace')).Trim().ToLowerInvariant();$exProduct=([string](Get-PropertyValue $existing 'product_id')).Trim().ToLowerInvariant();if($exChannel -ne $wantChannel -or $exProduct -ne $wantProduct){continue};if(-not[string]::IsNullOrWhiteSpace($exMarketplace) -and -not[string]::IsNullOrWhiteSpace($wantMarketplace) -and $exMarketplace -ne $wantMarketplace){continue}
        $same=(([string](Get-PropertyValue $existing 'concept_key')).Trim().ToLowerInvariant() -eq ([string]$ConceptKey).Trim().ToLowerInvariant() -and ([string](Get-PropertyValue $existing 'package_sha256')).Trim().ToLowerInvariant() -eq ([string]$PackageSha).Trim().ToLowerInvariant() -and ([string](Get-PropertyValue $existing 'lineage_fingerprint')).Trim().ToLowerInvariant() -eq ([string]$Fingerprint).Trim().ToLowerInvariant() -and ([string](Get-PropertyValue $existing 'listing_hash')).Trim().ToLowerInvariant() -eq ([string]$ListingHash).Trim().ToLowerInvariant() -and ([string](Get-PropertyValue $existing 'preupload_gate_sha256')).Trim().ToLowerInvariant() -eq ([string]$GateSha).Trim().ToLowerInvariant() -and ([string](Get-PropertyValue $existing 'print_production_sha256')).Trim().ToLowerInvariant() -eq ([string]$PrintSha).Trim().ToLowerInvariant() -and ($exMarketplace -eq $wantMarketplace -or ([string]::IsNullOrWhiteSpace($exMarketplace) -and [string]::IsNullOrWhiteSpace($wantMarketplace))));if(-not$same){return [pscustomobject]@{status='conflict';existing=$existing}};$sameExisting=$existing
    }
    if($null -ne $sameExisting){return [pscustomobject]@{status='same';existing=$sameExisting}};return [pscustomobject]@{status='none';existing=$null}
}

function Import-LocalPublicationReceipt {
    $dlg=New-Object Microsoft.Win32.OpenFileDialog;$dlg.Title='Import publication receipt';$dlg.Filter='JSON receipt (*.json)|*.json';if($dlg.ShowDialog() -ne $true){return};Import-LocalPublicationReceiptFromPath $dlg.FileName
}
function Import-LocalPublicationReceiptFromPath([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){Show-Error 'File not found.';return}
    try {
        $receiptPayload=Read-LocalCheckEvidencePayload $Path;$r=$receiptPayload.data;if([string](Get-PropertyValue $r 'schema') -ne 'forge.local_publication_receipt.v3'){throw 'Hardened build requires a v3 publication receipt bound to the exact pre-upload gate.'}
        $conceptKey=([string](Get-PropertyValue $r 'concept_key')).Trim();if([string]::IsNullOrWhiteSpace($conceptKey)){throw 'Publication receipt concept_key is required.'};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept $conceptKey $s;if($null -eq $lc){throw 'Publication receipt concept is not present in local Forge state.'}
        $packageSha=([string](Get-PropertyValue $r 'package_sha256')).Trim().ToLowerInvariant();if($packageSha -notmatch '^[0-9a-f]{64}$'){throw 'Publication receipt package_sha256 is invalid.'};$packageMatch=$null;foreach($pkg in @($lc.packages)){if(([string](Get-PropertyValue $pkg 'sha256')).ToLowerInvariant() -eq $packageSha){$packageMatch=$pkg;break}};if($null -eq $packageMatch){throw 'Publication receipt does not match a package built by this local Forge state.'}
        if(-not(Test-LocalPackageBoolean $packageMatch 'valid' $true) -or [string](Get-PropertyValue $packageMatch 'status') -ne 'READY_FOR_MANUAL_UPLOAD'){throw 'Only a currently valid READY_FOR_MANUAL_UPLOAD package may be recorded as published.'}
        $packagePath=[string](Get-PropertyValue $packageMatch 'path');if(-not(Test-Path -LiteralPath $packagePath -PathType Leaf) -or (Get-FileSha256Hex $packagePath) -ne $packageSha){throw 'Published package bytes are missing or no longer match their SHA-256.'};$zipAuthority=Get-LocalReadyPackageZipAuthority $packagePath $packageMatch $conceptKey;if($null-eq$zipAuthority){throw 'Exact package ZIP does not contain an authority-valid READY preupload gate matching the local package lineage.'};$zipGateSha=[string](Get-PropertyValue $zipAuthority 'gate_sha256');$zipPrintSha=[string](Get-PropertyValue $zipAuthority 'print_production_sha256')
        $fp=([string](Get-PropertyValue $r 'lineage_fingerprint')).Trim().ToLowerInvariant();$lh=([string](Get-PropertyValue $r 'listing_hash')).Trim().ToLowerInvariant();$gateSha=([string](Get-PropertyValue $r 'preupload_gate_sha256')).Trim().ToLowerInvariant();$printSha=([string](Get-PropertyValue $r 'print_production_sha256')).Trim().ToLowerInvariant();if($printSha -notmatch '^[0-9a-f]{64}$' -or $printSha -ne [string](Get-PropertyValue $packageMatch 'print_production_sha256')){throw 'Publication receipt print_production_sha256 does not match the exact READY package.'};if($fp -ne [string](Get-PropertyValue $packageMatch 'acceptance_fingerprint') -or $lh -ne [string](Get-PropertyValue $packageMatch 'listing_hash')){throw 'Publication receipt lineage does not match the exact Forge package.'};if($gateSha -notmatch '^[0-9a-f]{64}$' -or $gateSha -ne [string](Get-PropertyValue $packageMatch 'preupload_gate_sha256')){throw 'Publication receipt preupload_gate_sha256 does not match the exact READY package gate.'}
        $channel=([string](Get-PropertyValue $r 'channel')).Trim().ToLowerInvariant();$marketplace=([string](Get-PropertyValue $r 'marketplace')).Trim();$productId=([string](Get-PropertyValue $r 'product_id')).Trim();if($channel -ne 'amazon_merch' -or [string]::IsNullOrWhiteSpace($marketplace) -or [string]::IsNullOrWhiteSpace($productId)){throw 'Publication receipt must identify the amazon_merch channel, exact package marketplace, and product_id.'};if($marketplace -ne [string](Get-PropertyValue $zipAuthority 'marketplace')){throw 'Publication receipt marketplace does not match the exact Amazon print profile embedded in the READY package.'};$publishedRaw=([string](Get-PropertyValue $r 'published_at')).Trim();$published=$null;try{$published=[DateTime]::Parse($publishedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{throw 'Publication receipt published_at must be a valid date/time.'};if($published -gt [DateTime]::UtcNow.AddMinutes(10)){throw 'Publication receipt published_at cannot be in the future.'};$packageCreated=[DateTime](Get-PropertyValue $zipAuthority 'created_at');if($published -lt $packageCreated.AddMinutes(-10)){throw 'Publication receipt published_at predates creation of the exact Forge package.'};$profileValidUntil=[DateTime](Get-PropertyValue $zipAuthority 'profile_valid_until');if($published -gt $profileValidUntil){throw 'Publication receipt published_at is after the Amazon print profile valid_until used to build this package. Re-attest the current template and build a fresh READY package before publication.'}
        $fileSha=$receiptPayload.sha256;foreach($existing in @($s.publication_receipts)){if((Test-LocalPublicationReceiptAuthority $s $existing) -and [string](Get-PropertyValue $existing 'source_file_sha256') -eq $fileSha){$StatusText.Text='This publication receipt was already imported.';Update-LocalCoreBusinessSurfaces;return}};$binding=Get-LocalPublicationReceiptBindingDecision $s $conceptKey $packageSha $fp $lh $gateSha $printSha $channel $marketplace $productId;if([string](Get-PropertyValue $binding 'status') -eq 'same'){$StatusText.Text='This exact published product/package binding is already recorded locally.';Update-LocalCoreBusinessSurfaces;return};if([string](Get-PropertyValue $binding 'status') -eq 'conflict'){throw 'This channel/product_id is already bound to a different verified Forge package. The conflicting receipt was not imported.'}
        $productKey=($channel+'|'+$marketplace.ToLowerInvariant()+'|'+$productId).ToLowerInvariant();$receipt=[pscustomobject]@{concept_key=$conceptKey;package_sha256=$packageSha;lineage_fingerprint=$fp;listing_hash=$lh;preupload_gate_sha256=$gateSha;print_production_sha256=$printSha;channel=$channel;marketplace=$marketplace;product_id=$productId;product_key=$productKey;published_at=$published.ToUniversalTime().ToString('o');source=[string](Get-PropertyValue $r 'source');note=[string](Get-PropertyValue $r 'note');source_file=[IO.Path]::GetFileName($Path);source_file_sha256=$fileSha;imported_at=[DateTime]::UtcNow.ToString('o');lineage_verified=$true;sync_state='owner_imported_local_receipt'};$s.publication_receipts=@($s.publication_receipts)+@($receipt);Reconcile-LocalSalesLinks $s;Write-LocalCoreState $s;Update-LocalCoreBusinessSurfaces;$StatusText.Text='Publication receipt imported and exact package lineage verified.'
    } catch {Show-Error $_.Exception.Message;$StatusText.Text='Publication receipt import failed.'}
}
function Reconcile-LocalSalesLinks($State) {
    $byId=@{};$ambiguous=@{};foreach($receipt in @($State.publication_receipts)){if(Test-LocalPublicationReceiptAuthority $State $receipt){$id=([string](Get-PropertyValue $receipt 'product_id')).Trim().ToLowerInvariant();if([string]::IsNullOrWhiteSpace($id)){continue};$productKey=Get-LocalPublicationProductKey $receipt;if([string]::IsNullOrWhiteSpace($productKey)){continue};if(-not$byId.ContainsKey($id)){$byId[$id]=[pscustomobject]@{receipt=$receipt;product_key=$productKey}}else{$existingKey=[string](Get-PropertyValue $byId[$id] 'product_key');if($existingKey -ne $productKey){$ambiguous[$id]=$true}}}}
    foreach($row in @($State.sales_rows)){$id=([string](Get-PropertyValue $row 'product_id')).Trim().ToLowerInvariant();$linked=($id -and $byId.ContainsKey($id) -and -not$ambiguous.ContainsKey($id));Add-OrSetProperty $row 'linked' $linked;Add-OrSetProperty $row 'linked_product_key' $(if($linked){[string](Get-PropertyValue $byId[$id] 'product_key')}else{''})}
}

function ConvertTo-CsvKey([string]$Name) { return (([string]$Name).ToLowerInvariant() -replace '[^a-z0-9]','') }
function Get-FirstCsvProperty($Row,[string[]]$Aliases) {
    # Column names are matched without case, spaces or punctuation ("Units Sold" = "units_sold"); an alias ending in * matches a prefix ("Royalty (USD)").
    foreach($a in $Aliases){ $want=ConvertTo-CsvKey $a.TrimEnd('*'); $prefix=$a.EndsWith('*'); foreach($p in $Row.PSObject.Properties){ $k=ConvertTo-CsvKey ([string]$p.Name); if($k -eq $want -or ($prefix -and $k.StartsWith($want))){ return $p.Value } } }
    return $null
}
function ConvertFrom-ForgeMoney($Raw,[string]$ExpectedCurrency='',[bool]$AllowCurrency=$true,$ParseInfo=$null) {
    $info=[pscustomobject]@{readable=$false;ambiguous=$false;reason='invalid'};if($null-ne$ParseInfo){$ParseInfo.Value=$info}
    if($null-eq$Raw){return 0.0}
    if($Raw-isnot[string]){
        $type=[Type]::GetTypeCode($Raw.GetType());if($type-notin@([TypeCode]::Byte,[TypeCode]::SByte,[TypeCode]::Int16,[TypeCode]::UInt16,[TypeCode]::Int32,[TypeCode]::UInt32,[TypeCode]::Int64,[TypeCode]::UInt64,[TypeCode]::Single,[TypeCode]::Double,[TypeCode]::Decimal)){return $null}
        $direct=[double]$Raw;if([double]::IsNaN($direct)-or[double]::IsInfinity($direct)-or[math]::Abs($direct)-gt1000000000000){return $null};$info.readable=$true;$info.reason='numeric_value';return $direct
    }
    $text=$Raw.Trim();if(!$text){return 0.0};if($text.Length-gt256){return $null}
    $parenthesized=($text.StartsWith('(')-and$text.EndsWith(')'));if($parenthesized){$text=$text.Substring(1,$text.Length-2).Trim()}
    $pattern='^(?<sign1>[+-])?\s*(?<pre>\p{Sc}|[A-Za-z]{3})?\s*(?<sign2>[+-])?\s*(?<num>[0-9.,][0-9.,'' \u00a0\u202f]*(?:[eE][+-]?[0-9]+)?)\s*(?<post>\p{Sc}|[A-Za-z]{3})?\s*(?<sign3>[+-])?$'
    $match=[regex]::Match($text,$pattern);if(!$match.Success){return $null}
    $signs=@(@('sign1','sign2','sign3')|Where-Object{$match.Groups[$_].Success});if($signs.Count-gt1-or($parenthesized-and$signs.Count)){return $null}
    $negative=$parenthesized;foreach($name in $signs){if($match.Groups[$name].Value-ceq'-'){$negative=$true}}
    if($match.Groups['pre'].Success-and$match.Groups['post'].Success){return $null}
    $currencyToken=if($match.Groups['pre'].Success){$match.Groups['pre'].Value}else{$match.Groups['post'].Value}
    if($currencyToken){
        if(!$AllowCurrency){return $null}
        if($currencyToken-match'^[A-Za-z]{3}$'){$found=Resolve-LocalSalesCurrency $currencyToken '';if(!$found.currency-or($ExpectedCurrency-and$found.currency-cne$ExpectedCurrency.ToUpperInvariant())){return $null}}
        elseif($ExpectedCurrency-and$currencyToken-cne'¤'){
            $symbols=@{USD='$';CAD='$';AUD='$';NZD='$';MXN='$';SGD='$';BRL='$';EUR='€';GBP='£';JPY='¥';CNY='¥';INR='₹';CHF='₣'}
            if(!$symbols.ContainsKey($ExpectedCurrency.ToUpperInvariant())-or$currencyToken-cne$symbols[$ExpectedCurrency.ToUpperInvariant()]){return $null}
        }
    }
    $number=$match.Groups['num'].Value.Trim();$exponent='';$mantissa=$number
    $exp=[regex]::Match($number,'^(?<m>.+)[eE](?<e>[+-]?\d+)$');if($exp.Success){$mantissa=$exp.Groups['m'].Value;$exponent='e'+$exp.Groups['e'].Value}
    if($mantissa-match'['' \u00a0\u202f]'){
        if($mantissa-notmatch'^\d{1,3}(?:['' \u00a0\u202f]\d{3})+(?:[.,]\d+)?$'){return $null}
        $mantissa=[regex]::Replace($mantissa,'['' \u00a0\u202f]','')
    }
    $nonzeroMantissa=($mantissa-match'[1-9]')
    $grouped={param([string]$Value,[string]$Separator)$sep=[regex]::Escape($Separator);return ($Value-match('^(?:\d{1,3}(?:'+$sep+'\d{3})+|\d{1,2}(?:'+$sep+'\d{2})+'+$sep+'\d{3})$'))}
    if($exponent){
        if($mantissa-notmatch'^(?:\d+(?:[.,]\d*)?|[.,]\d+)$'){return $null}
        if($mantissa-match'^[1-9]\d{0,2},\d{3}$'){return $null} # Grouping vs decimal comma cannot be established here.
        $normalized=$mantissa.Replace(',','.')+$exponent
    }else{
        $commas=$mantissa.Length-$mantissa.Replace(',','').Length;$dots=$mantissa.Length-$mantissa.Replace('.','').Length
        if($mantissa-match'^[1-9]\d{0,2}[.,]\d{3}$'){$info.ambiguous=$true}
        if($commas-and$dots){
            $decimal=if($mantissa.LastIndexOf(',')-gt$mantissa.LastIndexOf('.')){','}else{'.'};$group=if($decimal-ceq','){'.'}else{','};$at=$mantissa.LastIndexOf($decimal);$whole=$mantissa.Substring(0,$at);$fraction=$mantissa.Substring($at+1)
            if($fraction-notmatch'^\d+$'-or($whole-notmatch'^\d+$'-and!(&$grouped $whole $group))){return $null};$normalized=$whole.Replace($group,'')+'.'+$fraction
        }elseif($commas-gt1){if(!(&$grouped $mantissa ',')){return $null};$normalized=$mantissa.Replace(',','')}
        elseif($dots-gt1){if(!(&$grouped $mantissa '.')){return $null};$normalized=$mantissa.Replace('.','')}
        elseif($commas-eq1){$parts=$mantissa.Split(',');if($parts[1].Length-eq3-and$parts[0]-match'^[1-9]\d{0,2}$'){$normalized=$mantissa.Replace(',','')}else{$normalized=$mantissa.Replace(',','.')}}
        else{$normalized=$mantissa}
        if($normalized-notmatch'^(?:\d+(?:\.\d*)?|\.\d+)$'){return $null}
    }
    $value=[double]0;if(![double]::TryParse($normalized,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$value)-or[double]::IsNaN($value)-or[double]::IsInfinity($value)-or[math]::Abs($value)-gt1000000000000-or($value-eq0-and$nonzeroMantissa)){return $null}
    if($negative){$value=-$value};$info.readable=$true;$info.reason=if($info.ambiguous){'ambiguous_decimal_or_grouping'}else{'finite_numeric_value'};return $value
}

function ConvertFrom-ForgeSalesDate($Raw,[string]$SlashOrder='mdy') {
    # ISO dates first; slashes are read as US month/day (Amazon.com reports); dots as day.month. Anything else -> $null (counted as undated).
    $s=([string]$Raw).Trim(); if(-not $s){return $null}
    if($s -match '^\d{4}-\d{2}-\d{2}T'){ try{ return ([DateTimeOffset]::Parse($s,[Globalization.CultureInfo]::InvariantCulture)).DateTime.Date }catch{ return $null } }   # the date as written, not moved to this PC's time zone
    $slash=if($SlashOrder -eq 'dmy'){@('d/M/yyyy','d/M/yyyy H:mm','d/M/yyyy H:mm:ss')}else{@('M/d/yyyy','M/d/yyyy H:mm','M/d/yyyy h:mm tt','M/d/yyyy H:mm:ss')}
    $fmts=[string[]](@('yyyy-MM-dd','yyyy-MM-dd HH:mm:ss','yyyy-MM-dd HH:mm','yyyy/MM/dd','yyyy.MM.dd','d.M.yyyy','d.M.yyyy H:mm')+$slash)
    $d=[DateTime]::MinValue
    if([DateTime]::TryParseExact($s,$fmts,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::AllowWhiteSpaces,[ref]$d)){ return $d }
    return $null
}
function Import-LocalSalesCsv {
    $dlg=New-Object Microsoft.Win32.OpenFileDialog;$dlg.Title='Import sales / royalty CSV';$dlg.Filter='CSV files (*.csv)|*.csv';if($dlg.ShowDialog() -ne $true){return};Import-LocalSalesCsvFromPath $dlg.FileName
}
function Find-CsvColumn([string[]]$Names,[string[]]$Aliases) {
    # Exact names first; an alias ending in * matches a prefix, but never rate / currency / percent columns ("Royalty Rate", "Royalties Currency").
    foreach($a in $Aliases){ if($a.EndsWith('*')){continue}; $want=ConvertTo-CsvKey $a; foreach($n in $Names){ if((ConvertTo-CsvKey $n) -eq $want){ return $n } } }
    foreach($a in $Aliases){ if(-not $a.EndsWith('*')){continue}; $want=ConvertTo-CsvKey $a.TrimEnd('*'); foreach($n in $Names){ $k=ConvertTo-CsvKey $n; if($k.StartsWith($want) -and $k -notmatch 'rate|currency|percent|pct|code|type|return|cancel|refund'){ return $n } } }
    return $null
}
function Get-CsvSlashDateOrder([string[]]$Values,[string]$Delimiter) {
    # One order per file: a first part above 12 means day/month, a second part above 12 means month/day; if the file never says, ';' files (European Excel) are day/month.
    $dmy=$false; $mdy=$false
    foreach($v in $Values){ $m=[regex]::Match(([string]$v).Trim(),'^(\d{1,2})/(\d{1,2})/\d{4}'); if(-not $m.Success){continue}; if([int]$m.Groups[1].Value -gt 12){$dmy=$true}; if([int]$m.Groups[2].Value -gt 12){$mdy=$true} }
    if($dmy -and -not $mdy){ return 'dmy' }; if($mdy -and -not $dmy){ return 'mdy' }
    if($Delimiter -eq ';'){ return 'dmy' }; return 'mdy'
}
function Resolve-LocalSalesCurrency([string]$Explicit,[string]$RoyaltyColumn) {
    $known='USD|GBP|EUR|JPY|CAD|AUD|MXN|BRL|PLN|SEK|CHF|CNY|INR|NZD|DKK|NOK|SGD'
    $raw=$Explicit.Trim().ToUpperInvariant();$header=[regex]::Match($RoyaltyColumn.ToUpperInvariant(),('(?<![A-Z])('+$known+')(?![A-Z])'))
    if($raw){
        if($raw-notmatch('^('+$known+')$')){return [pscustomobject]@{currency='';source='unrecognized_explicit';raw=$Explicit}}
        if($header.Success-and$header.Groups[1].Value-cne$raw){return [pscustomobject]@{currency='';source='conflicting_column';raw=$Explicit}}
        return [pscustomobject]@{currency=$raw;source='explicit_column';raw=$Explicit}
    }
    if($header.Success){return [pscustomobject]@{currency=$header.Groups[1].Value;source='royalty_column_header';raw=$RoyaltyColumn}}
    return [pscustomobject]@{currency='';source='unspecified';raw=''}
}
function Get-LocalRoyaltyTotals($Rows,[datetime]$NowUtc=([DateTime]::UtcNow)) {
    $buckets=@{};$m=[ordered]@{royalties7=0.0;royalties30=0.0;royalties90=0.0;royalty_currency='';royalty_unknown7=0;royalty_unknown30=0;royalty_unknown90=0;royalty_currencies=@()}
    foreach($r in @($Rows)){
        if($null-eq$r){continue};$d=$null;try{$d=[DateTime]::ParseExact([string](Get-PropertyValue $r 'date'),'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}catch{}
        if($null-eq$d){continue};$age=($NowUtc.Date-$d.Date).TotalDays;if($age-lt0-or$age-ge90){continue}
        $c=([string](Get-PropertyValue $r 'currency')).Trim().ToUpperInvariant();$valid=Resolve-LocalSalesCurrency $c ''
        $amount=0.0;$numberOk=[double]::TryParse([string](Get-PropertyValue $r 'royalty'),[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$amount)-and![double]::IsNaN($amount)-and![double]::IsInfinity($amount)-and[math]::Abs($amount)-le1000000000000
        if(!$valid.currency-or!$numberOk-or($r.PSObject.Properties['royalty_amount_verified']-and($r.royalty_amount_verified-isnot[bool]-or!$r.royalty_amount_verified))){foreach($days in @(7,30,90)){if($age-lt$days){$m['royalty_unknown'+$days]++}};continue}
        if(!$buckets.ContainsKey($c)){$buckets[$c]=[pscustomobject]@{currency=$c;royalties7=0.0;royalties30=0.0;royalties90=0.0;rows7=0;rows30=0;rows90=0}}
        foreach($days in @(7,30,90)){if($age-lt$days){$buckets[$c].('royalties'+$days)+=$amount;$buckets[$c].('rows'+$days)++}}
    }
    $m.royalty_currencies=@($buckets.Values|Sort-Object currency)
    # Compatibility scalar fields have meaning only for a single known currency; never add unlike money.
    if($buckets.Count-eq1){$only=@($buckets.Values)[0];$m.royalty_currency=$only.currency;foreach($days in @(7,30,90)){$m['royalties'+$days]=$only.('royalties'+$days)}}
    $m['window_end']=$NowUtc.ToUniversalTime().Date.ToString('yyyy-MM-dd');foreach($days in @(7,30,90)){$m['window_start'+$days]=$NowUtc.ToUniversalTime().Date.AddDays(1-$days).ToString('yyyy-MM-dd')}
    return [pscustomobject]$m
}
function Format-LocalRoyaltyTotal($Metrics,[int]$Days=30,[switch]$Compact) {
    $parts=@();foreach($b in @(Get-PropertyValue $Metrics 'royalty_currencies')){if($null-ne$b-and[int](Get-PropertyValue $b ('rows'+$Days))-gt0){$parts+=([string]$b.currency+' '+[string]::Format([Globalization.CultureInfo]::InvariantCulture,'{0:0.00}',[double]$b.('royalties'+$Days)))}}
    $unknown=[int](Get-PropertyValue $Metrics ('royalty_unknown'+$Days))
    if($Compact-and$unknown-gt0){return (Get-UiText 'money.incomplete' 'Unverified')}
    if($Compact-and$parts.Count-gt1){return ((Get-UiText 'money.multiple' '{0} currencies')-f$parts.Count)}
    if($unknown-gt0){$parts+=((Get-UiText 'money.unknown' '{0} row(s): currency or amount unverified')-f$unknown)}
    if(!$parts.Count){return '-'};return ($parts-join'; ')
}
function Update-LocalSalesCurrencyFromExactImport($State,$Normalized,[string]$FileSha,[string]$FileName) {
    # Older imports discarded currency. Re-import may enrich only an unambiguous, byte-identical import.
    $imports=@($State.sales_imports|Where-Object{[string](Get-PropertyValue $_ 'file')-ieq$FileName})
    if($imports.Count-ne1-or[string]$imports[0].sha256-cne$FileSha){return 0}
    $old=@($State.sales_rows|Where-Object{[string](Get-PropertyValue $_ 'source_file')-ieq$FileName})
    if($old.Count-ne@($Normalized).Count){return 0}
    for($i=0;$i-lt$old.Count;$i++){
        foreach($k in @('date','product_id','title')){if([string](Get-PropertyValue $old[$i] $k)-cne[string](Get-PropertyValue $Normalized[$i] $k)){return 0}}
        foreach($k in @('units','royalty','revenue')){if([double](Get-PropertyValue $old[$i] $k)-ne[double](Get-PropertyValue $Normalized[$i] $k)){return 0}}
    }
    $changed=0
    for($i=0;$i-lt$old.Count;$i++){
        if($old[$i].PSObject.Properties['currency_source']){continue}
        foreach($k in @('currency','currency_source','currency_raw','royalty_amount_verified')){Add-OrSetProperty $old[$i] $k (Get-PropertyValue $Normalized[$i] $k)}
        $changed++
    }
    return $changed
}
function Get-LocalSalesOverlapSummary($State,$Incoming) {
    $index=@{};$existingMatches=0;$withinMatches=0;$files=@{}
    foreach($group in @(@{rows=@($State.sales_rows);incoming=$false},@{rows=@($Incoming);incoming=$true})){
        foreach($row in $group.rows){
            $id=([string](Get-PropertyValue $row 'product_id')).Trim().ToLowerInvariant();$date=[string](Get-PropertyValue $row 'date')
            if(!$id-or$date-notmatch'^\d{4}-\d{2}-\d{2}$'){continue}
            $values=@($date,$id);foreach($k in @('units','royalty','revenue')){$values+=([double](Get-PropertyValue $row $k)).ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
            $key=Get-StringSha256Hex ($values|ConvertTo-Json -Compress)
            $currency=([string](Get-PropertyValue $row 'currency')).Trim().ToUpperInvariant()
            if($group.incoming-and$index.ContainsKey($key)){
                $candidates=@($index[$key]|Where-Object{!$currency-or!$_.currency-or$_.currency-ceq$currency})
                if($candidates.Count){if(@($candidates|Where-Object{!$_.incoming}).Count){$existingMatches++}else{$withinMatches++};foreach($match in $candidates){if($match.file){$files[$match.file]=$true}}}
            }
            if(!$index.ContainsKey($key)){$index[$key]=@()}
            $index[$key]+=,[pscustomobject]@{currency=$currency;incoming=[bool]$group.incoming;file=[string](Get-PropertyValue $row 'source_file')}
        }
    }
    return [pscustomobject]@{rows=($existingMatches+$withinMatches);existing_rows=$existingMatches;within_file_rows=$withinMatches;source_files=@($files.Keys|Sort-Object|Select-Object -First 3)}
}
function Read-ForgeSalesCsvSnapshot([string]$Path,[int]$MaxBytes=67108864,[int]$MaxRows=100000) {
    if($MaxBytes-lt1-or$MaxBytes-gt67108864-or$MaxRows-lt1-or$MaxRows-gt100000){throw 'CSV capture limits are invalid.'}
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if($item-isnot[IO.FileInfo]-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'The sales CSV must be an ordinary local file.'}
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);$memory=New-Object IO.MemoryStream;$buffer=New-Object byte[] 65536
    try{if($stream.Length-gt$MaxBytes){throw ('The sales CSV exceeds the configured byte limit ('+$MaxBytes+' bytes).')};while(($n=$stream.Read($buffer,0,$buffer.Length))-gt0){if($memory.Length+$n-gt$MaxBytes){throw 'The sales CSV exceeds the bounded reading limit.'};$memory.Write($buffer,0,$n)};$bytes=$memory.ToArray()}finally{$memory.Dispose();$stream.Dispose()}
    $sha=[Security.Cryptography.SHA256]::Create();try{$hash=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
    $offset=0;$encoding=New-Object Text.UTF8Encoding($false,$true);$label='utf-8'
    if($bytes.Length-ge4-and$bytes[0]-eq255-and$bytes[1]-eq254-and$bytes[2]-eq0-and$bytes[3]-eq0){$encoding=New-Object Text.UTF32Encoding($false,$true,$true);$offset=4;$label='utf-32le'}
    elseif($bytes.Length-ge4-and$bytes[0]-eq0-and$bytes[1]-eq0-and$bytes[2]-eq254-and$bytes[3]-eq255){$encoding=New-Object Text.UTF32Encoding($true,$true,$true);$offset=4;$label='utf-32be'}
    elseif($bytes.Length-ge3-and$bytes[0]-eq239-and$bytes[1]-eq187-and$bytes[2]-eq191){$offset=3;$label='utf-8-bom'}
    elseif($bytes.Length-ge2-and$bytes[0]-eq255-and$bytes[1]-eq254){$encoding=New-Object Text.UnicodeEncoding($false,$true,$true);$offset=2;$label='utf-16le'}
    elseif($bytes.Length-ge2-and$bytes[0]-eq254-and$bytes[1]-eq255){$encoding=New-Object Text.UnicodeEncoding($true,$true,$true);$offset=2;$label='utf-16be'}
    try{$text=$encoding.GetString($bytes,$offset,$bytes.Length-$offset)}catch{throw 'The sales CSV text encoding is invalid. Export it as UTF-8 or BOM-marked Unicode; the source and existing data were preserved.'}
    if($text.IndexOf([char]0)-ge0){throw 'The sales CSV contains NUL characters. Export it as UTF-8 or BOM-marked Unicode before importing; existing data was preserved.'}
    $commas=0;$semicolons=0;$quoted=$false
    for($i=0;$i-lt$text.Length;$i++){
        $ch=$text[$i]
        if($ch-eq'"'){if($quoted-and$i+1-lt$text.Length-and$text[$i+1]-eq'"'){$i++}else{$quoted=!$quoted};continue}
        if(!$quoted){if($ch-eq','){$commas++}elseif($ch-eq';'){$semicolons++}elseif($ch-eq"`r"-or$ch-eq"`n"){break}}
    }
    $delimiter=if($semicolons-gt$commas){';'}else{','};$list=New-Object 'System.Collections.Generic.List[object]'
    ConvertFrom-Csv -InputObject $text -Delimiter $delimiter -ErrorAction Stop -WarningAction SilentlyContinue|ForEach-Object{if($list.Count-ge$MaxRows){throw ('The sales CSV exceeds the '+$MaxRows+'-row import limit. Export a smaller report; existing rows were preserved.')};[void]$list.Add($_)}
    if($list.Count-eq0){throw 'CSV contains no data rows.'}
    return [pscustomobject]@{rows=$list.ToArray();sha256=$hash;source_encoding=$label;delimiter=$delimiter;size_bytes=$bytes.Length}
}

function Get-ForgeSalesNormalizationSnapshot($Row) {
    $result=[ordered]@{}
    foreach($name in @('date','units','units_amount_verified','royalty','royalty_amount_verified','currency','currency_source','currency_raw','revenue','revenue_amount_verified','title','product_id','source_file','source_file_sha256','source_row_no','normalization_contract')){$result[$name]=Get-PropertyValue $Row $name}
    return [pscustomobject]$result
}
function Update-ForgeSalesExactSource($State,$Normalized,[string]$Sha,[string]$Encoding,[string]$SelectedName) {
    $imports=@($State.sales_imports);$allRows=@($State.sales_rows);$matchesBySha=@($imports|Where-Object{[string](Get-PropertyValue $_ 'sha256')-ieq$Sha})
    if($matchesBySha.Count-ne1){throw 'The saved CSV source identity is ambiguous. Existing rows were preserved; restore a consistent data copy before revalidating.'}
    $import=$matchesBySha[0];$contract=[string](Get-PropertyValue $import 'normalization_contract');if($contract-and$contract-cnotin@('forge.sales_csv_numeric.v1','forge.sales_csv_numeric.v2')){throw 'This CSV was normalized by an unsupported or newer contract. Existing rows were preserved; use its matching application version.'};$indices=New-Object 'System.Collections.Generic.List[int]';$byOrdinal=@{}
    for($i=0;$i-lt$allRows.Count;$i++){if([string](Get-PropertyValue $allRows[$i] 'source_file_sha256')-ieq$Sha){$no=Get-PropertyValue $allRows[$i] 'source_row_no';if(($no-isnot[int]-and$no-isnot[long])-or$no-lt1-or$byOrdinal.ContainsKey([string]$no)){throw 'The saved CSV row identities are ambiguous; existing data was preserved.'};$byOrdinal[[string]$no]=$i}}
    $recordCount=Get-PropertyValue $import 'rows'
    if(($recordCount-isnot[int]-and$recordCount-isnot[long])-or$recordCount-lt1){throw 'The saved CSV row count is invalid; existing data was preserved.'}
    if($byOrdinal.Count){
        if($byOrdinal.Count-ne$recordCount){throw 'The saved CSV row binding is incomplete; existing data was preserved.'}
        for($no=1;$no-le$recordCount;$no++){if(!$byOrdinal.ContainsKey([string]$no)){throw 'The saved CSV row sequence is incomplete; existing data was preserved.'};[void]$indices.Add([int]$byOrdinal[[string]$no])}
    }else{
        # Earlier imports append complete source blocks in import order. Require that exact invariant.
        $cursor=0
        foreach($entry in $imports){
            $count=Get-PropertyValue $entry 'rows';$file=[string](Get-PropertyValue $entry 'file');$hash=[string](Get-PropertyValue $entry 'sha256')
            if(($count-isnot[int]-and$count-isnot[long])-or$count-lt1-or!$file-or$hash-cnotmatch'^[0-9a-fA-F]{64}$'-or$cursor+$count-gt$allRows.Count){throw 'Legacy CSV source mapping is inconsistent; no row was guessed or rewritten.'}
            for($j=0;$j-lt$count;$j++){$row=$allRows[$cursor+$j];$bound=[string](Get-PropertyValue $row 'source_file_sha256');if($row-isnot[pscustomobject]-or[string](Get-PropertyValue $row 'source_file')-ine$file-or($bound-and$bound-ine$hash)){throw 'Legacy CSV source mapping is inconsistent; no row was guessed or rewritten.'}}
            if([object]::ReferenceEquals($entry,$import)){for($j=0;$j-lt$count;$j++){[void]$indices.Add([int]($cursor+$j))}}
            $cursor+=$count
        }
        if($cursor-ne$allRows.Count-or$indices.Count-ne$recordCount){throw 'Legacy CSV source mapping is incomplete; existing rows were preserved.'}
    }
    $oldRows=@($indices|ForEach-Object{$allRows[$_]});foreach($oldRow in $oldRows){$rowContract=[string](Get-PropertyValue $oldRow 'normalization_contract');if($rowContract-and$rowContract-cnotin@('forge.sales_csv_numeric.v1','forge.sales_csv_numeric.v2')){throw 'A source row uses an unsupported or newer numeric contract. Existing data was preserved.'}};$newRows=New-Object 'System.Collections.Generic.List[object]';$currencyRepaired=0;$dataChanged=($oldRows.Count-ne@($Normalized).Count)
    for($i=0;$i-lt@($Normalized).Count;$i++){
        $incoming=$Normalized[$i];$row=$null
        if($i-lt$oldRows.Count-and[string](Get-PropertyValue $oldRows[$i] 'date')-ceq[string]$incoming.date-and[string](Get-PropertyValue $oldRows[$i] 'product_id')-ceq[string]$incoming.product_id-and[string](Get-PropertyValue $oldRows[$i] 'title')-ceq[string]$incoming.title){$row=($oldRows[$i]|ConvertTo-Json -Depth 60 -Compress|ConvertFrom-Json)}else{$row=[pscustomobject]@{}}
        foreach($p in $incoming.PSObject.Properties){Add-OrSetProperty $row $p.Name $p.Value};Add-OrSetProperty $row 'source_file' ([string]$import.file)
        if($i-lt$oldRows.Count){$oldCurrency=[string](Get-PropertyValue $oldRows[$i] 'currency');if(!$oldCurrency-and[string](Get-PropertyValue $row 'currency')){$currencyRepaired++};if((ConvertTo-ForgeBriefCanonicalJson (Get-ForgeSalesNormalizationSnapshot $oldRows[$i]))-cne(ConvertTo-ForgeBriefCanonicalJson (Get-ForgeSalesNormalizationSnapshot $row))){$dataChanged=$true}}
        [void]$newRows.Add($row)
    }
    if(!$dataChanged-and[string](Get-PropertyValue $import 'source_encoding')-ceq$Encoding-and[string](Get-PropertyValue $import 'normalization_contract')-ceq'forge.sales_csv_numeric.v2'){return [pscustomobject]@{changed=$false;rows=0;currency_repaired=0;requires_overlap_confirmation=$false}}
    $historyProperty=$import.PSObject.Properties['normalization_history'];$history=$null;if($null-ne$historyProperty){$history=$historyProperty.Value};if($null-ne$history-and$history-isnot[array]){throw 'Saved source normalization history is malformed; existing rows were preserved.'}
    $priorRows=ConvertFrom-Json (ConvertTo-Json -InputObject $oldRows -Depth 60 -Compress)
    $entry=[pscustomobject]@{kind='exact_source_revalidation';at=[DateTime]::UtcNow.ToString('o');source_sha256=$Sha;selected_source_name=$SelectedName;previous_contract=[string](Get-PropertyValue $import 'normalization_contract');previous_rows=@($priorRows);previous_row_count=$oldRows.Count;current_row_count=$newRows.Count}
    Add-OrSetProperty $import 'normalization_history' (@($history|Where-Object{$null-ne$_})+@($entry));Add-OrSetProperty $import 'normalization_contract' 'forge.sales_csv_numeric.v2';Add-OrSetProperty $import 'source_encoding' $Encoding;Add-OrSetProperty $import 'rows' $newRows.Count
    $skip=New-Object 'System.Collections.Generic.HashSet[int]';foreach($index in $indices){[void]$skip.Add($index)};$first=($indices|Measure-Object -Minimum).Minimum;$kept=New-Object 'System.Collections.Generic.List[object]';$other=New-Object 'System.Collections.Generic.List[object]'
    for($i=0;$i-lt$allRows.Count;$i++){if($i-eq$first){foreach($row in $newRows){[void]$kept.Add($row)}};if(!$skip.Contains($i)){[void]$kept.Add($allRows[$i]);[void]$other.Add($allRows[$i])}}
    $otherState=[pscustomobject]@{sales_rows=$other.ToArray()};$overlap=Get-LocalSalesOverlapSummary $otherState ($newRows.ToArray());$ack=Get-PropertyValue $import 'overlap_acknowledged';$oldOverlap=[int](Get-PropertyValue $import 'potential_overlap_rows');$needs=($overlap.rows-gt0-and($ack-isnot[bool]-or!$ack-or$overlap.rows-gt$oldOverlap))
    Add-OrSetProperty $import 'potential_overlap_rows' $overlap.rows;Add-OrSetProperty $import 'unreadable_amounts' @($newRows|Where-Object{!(Get-PropertyValue $_ 'units_amount_verified')-or!(Get-PropertyValue $_ 'royalty_amount_verified')}).Count
    $State.sales_rows=$kept.ToArray()
    return [pscustomobject]@{changed=$true;rows=$newRows.Count;currency_repaired=$currencyRepaired;requires_overlap_confirmation=$needs;overlap_rows=$overlap.rows;import=$import}
}
function Format-LocalSalesUnits($Metrics,[int]$Days=30) {
    if($Days-notin@(7,30,90)){throw 'Unsupported sales date window.'}
    if($null-eq$Metrics-or$null-eq$Metrics.PSObject.Properties['sales'+$Days]){return (Get-UiText 'money.unverified' 'Unverified')}
    $unknown=[int](Get-PropertyValue $Metrics ('units_unknown'+$Days));$value=[double](Get-PropertyValue $Metrics ('sales'+$Days))
    if($unknown-gt0-or[double]::IsNaN($value)-or[double]::IsInfinity($value)){return (Get-UiText 'money.unverified' 'Unverified')}
    return $value.ToString('G15',[Globalization.CultureInfo]::InvariantCulture)
}

function Import-LocalSalesCsvFromPath([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){Show-Error 'File not found.';return}
    try {
        $capture=Read-ForgeSalesCsvSnapshot $Path;$rows=@($capture.rows);$delim=$capture.delimiter
        $names=@($rows[0].PSObject.Properties | ForEach-Object { [string]$_.Name })
        $cDate=Find-CsvColumn $names @('date','purchase date','order date','sale date','transaction date','shipment date','period','period start','day')
        $cUnits=Find-CsvColumn $names @('units','units sold','net units','quantity','qty','items sold','purchased','sold','units*')
        $cRoy=Find-CsvColumn $names @('royalty','royalties','net earnings','earnings','amount','royalt*','earning*')
        $cCurrency=Find-CsvColumn $names @('currency','royalty currency','royalties currency','currency code','payment currency')
        $cRev=Find-CsvColumn $names @('revenue','sales revenue','gross sales','gross','revenue*')
        $cTitle=Find-CsvColumn $names @('title','product title','design title','name')
        $cId=Find-CsvColumn $names @('asin','product asin','product id','listing id','sku','asin*')
        if($null -eq $cUnits -and $null -eq $cRoy){ throw ('This sales CSV has no units or royalty column. Columns found: {0}.' -f ($names -join ', ')) }
        $order=Get-CsvSlashDateOrder @($rows | ForEach-Object { if($cDate){ [string]$_.$cDate } }) $delim
        $normalizedList=New-Object 'System.Collections.Generic.List[object]'; $badAmount=0;$rowNo=0
        foreach($row in $rows){
            $dateRaw=if($cDate){$row.$cDate}else{$null}; $unitsRaw=if($cUnits){$row.$cUnits}else{$null}; $royRaw=if($cRoy){$row.$cRoy}else{$null}; $revRaw=if($cRev){$row.$cRev}else{$null}; $title=if($cTitle){$row.$cTitle}else{''}; $id=if($cId){$row.$cId}else{''}
            $d=ConvertFrom-ForgeSalesDate $dateRaw $order
            [double]$units=0; [double]$roy=0; [double]$rev=0
            $currency=Resolve-LocalSalesCurrency $(if($cCurrency){[string]$row.$cCurrency}else{''}) ([string]$cRoy)
            $unitInfo=$null;$royInfo=$null;$revInfo=$null
            $uV=ConvertFrom-ForgeMoney $unitsRaw '' $false ([ref]$unitInfo);if($null-ne$uV){$units=[double]$uV}
            $unitsVerified=($null-ne$uV-and$unitInfo.readable-and!$unitInfo.ambiguous-and$null-ne$cUnits-and![string]::IsNullOrWhiteSpace([string]$unitsRaw));if($null-ne$cUnits-and!$unitsVerified){$badAmount++}
            $royV=ConvertFrom-ForgeMoney $royRaw $currency.currency $true ([ref]$royInfo);if($null-ne$royV){$roy=[double]$royV}
            $royVerified=($null-ne$royV-and$royInfo.readable-and!$royInfo.ambiguous-and$null-ne$cRoy-and![string]::IsNullOrWhiteSpace([string]$royRaw));if($null-ne$cRoy-and!$royVerified){$badAmount++}
            $revV=ConvertFrom-ForgeMoney $revRaw $currency.currency $true ([ref]$revInfo);if($null-ne$revV){$rev=[double]$revV};$revVerified=($null-ne$revV-and$revInfo.readable-and!$revInfo.ambiguous-and$null-ne$cRev-and![string]::IsNullOrWhiteSpace([string]$revRaw));$rowNo++
            [void]$normalizedList.Add([pscustomobject]@{date=if($null-ne$d){$d.ToString('yyyy-MM-dd')}else{''};units=$units;units_amount_verified=$unitsVerified;royalty=$roy;royalty_amount_verified=$royVerified;currency=$currency.currency;currency_source=$currency.source;currency_raw=$currency.raw;revenue=$rev;revenue_amount_verified=$revVerified;title=[string]$title;product_id=([string]$id).Trim();source_file=[IO.Path]::GetFileName($Path);source_file_sha256=$capture.sha256;source_row_no=$rowNo;normalization_contract='forge.sales_csv_numeric.v2';linked=$false;linked_product_key=''})
        }
        $normalized=$normalizedList.ToArray();$s=Read-LocalCoreState; $fileSha=$capture.sha256; $existing=$false
        foreach($imp in @($s.sales_imports)){ if([string]$imp.sha256 -eq $fileSha){$existing=$true;break} }
        $overlap=$null
        if(!$existing){
            $overlap=Get-LocalSalesOverlapSummary $s $normalized
            if($overlap.rows-gt0){
                $question=((Get-UiText 'money.overlap.confirm' 'This CSV has {0} row(s) that may overlap existing imports or repeat inside this file. Matching date, product, units and amounts do not prove duplicate transactions. Appending all rows may overstate totals. No rows will be silently removed. Append anyway? Previous source files: {1}')-f$overlap.rows,($overlap.source_files-join', '))
                if(!(Confirm $question 'Merch Forge')){$StatusText.Text=Get-UiText 'money.overlap.cancelled' 'Sales import cancelled; existing rows and totals were preserved.';return}
            }
        }
        $currencyRepaired=0;$revalidation=$null
        if(-not $existing){ $s.sales_rows=@($s.sales_rows)+@($normalized); $s.sales_imports=@($s.sales_imports)+@([pscustomobject]@{file=[IO.Path]::GetFileName($Path);sha256=$fileSha;source_encoding=$capture.source_encoding;normalization_contract='forge.sales_csv_numeric.v2';unreadable_amounts=$badAmount;rows=$rows.Count;potential_overlap_rows=$overlap.rows;overlap_acknowledged=($overlap.rows-gt0);imported_at=[DateTime]::UtcNow.ToString('o')}); Reconcile-LocalSalesLinks $s; Write-LocalCoreState $s }
        else{$revalidation=Update-ForgeSalesExactSource $s $normalized $fileSha $capture.source_encoding ([IO.Path]::GetFileName($Path));$currencyRepaired=$revalidation.currency_repaired;if($revalidation.changed){
            if($revalidation.requires_overlap_confirmation){if(!(Confirm ('Revalidating this exact CSV changes existing parsed rows and may overlap '+$revalidation.overlap_rows+' other row(s). Previous normalization will be retained. Continue?') 'Merch Forge')){$StatusText.Text='Source revalidation cancelled; existing rows were preserved.';return};Add-OrSetProperty $revalidation.import 'overlap_acknowledged' $true}
            Reconcile-LocalSalesLinks $s;Write-LocalCoreState $s
        }}
        Update-LocalCoreBusinessSurfaces
        $linked=@($normalized | Where-Object { [bool]$_.linked }).Count; $unlinked=$normalized.Count-$linked
        $noId=@($normalized | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.product_id) }).Count; $noDate=@($normalized | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.date) }).Count
        if($existing){$StatusText.Text=if($currencyRepaired-gt0){('Currency evidence restored for '+$currencyRepaired+' existing row(s) from the byte-identical CSV; no duplicate rows were added.')}elseif($null-ne$revalidation-and$revalidation.changed){('Exact CSV source revalidated for '+$revalidation.rows+' row(s); previous normalization retained. No duplicate source import added.')}else{'This sales CSV was already imported; no duplicate rows were added. Existing currency evidence was preserved; unmatched legacy rows remain unverified.'}}
        elseif(($noId+$noDate+$badAmount) -gt 0){ $StatusText.Text=("Imported {0} row(s): {1} linked to verified Forge products, {2} unlinked. Not readable: {3} without a product ID (ASIN), {4} without a date, {5} unreadable amount(s)." -f $rows.Count,$linked,$unlinked,$noId,$noDate,$badAmount) }
        else { $StatusText.Text=("Imported {0} row(s): {1} linked to verified Forge products, {2} unlinked." -f $rows.Count,$linked,$unlinked) }
        if(!$existing-and$null-ne$overlap-and$overlap.rows-gt0){$StatusText.Text+=' '+((Get-UiText 'money.overlap.imported' '{0} potentially overlapping row(s) were appended after confirmation; totals may repeat transactions.')-f$overlap.rows)}
    } catch {Show-Error $_.Exception.Message;$StatusText.Text='Sales CSV import failed.'}
}
function Get-LocalSalesMetrics {
    $s=Read-LocalCoreState;Reconcile-LocalSalesLinks $s;$rows=@($s.sales_rows);$now=[DateTime]::UtcNow.Date;$m=[ordered]@{sales7=0.0;sales30=0.0;sales90=0.0;units_unknown7=0;units_unknown30=0;units_unknown90=0;royalties7=0.0;royalties30=0.0;royalties90=0.0;rows=$rows.Count;linked_rows=0;unlinked_rows=0;undated_rows=0;future_rows=0}
    foreach($r in $rows){
        if(-not[bool](Get-PropertyValue $r 'linked')){$m.unlinked_rows++;continue};$m.linked_rows++;$d=$null;try{$d=[DateTime]::ParseExact([string](Get-PropertyValue $r 'date'),'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}catch{}
        if($null-eq$d){$m.undated_rows++;continue};$age=($now-$d.Date).TotalDays;if($age-lt0){$m.future_rows++;continue}
        $flag=$r.PSObject.Properties['units_amount_verified'];$known=($null-eq$flag-or($flag.Value-is[bool]-and$flag.Value));$units=0.0
        try{if($null-eq$r.PSObject.Properties['units']-or$null-eq$r.PSObject.Properties['units'].Value-or($r.PSObject.Properties['units'].Value-is[string]-and[string]::IsNullOrWhiteSpace([string]$r.PSObject.Properties['units'].Value))){$known=$false};$units=[double](Get-PropertyValue $r 'units');if([double]::IsNaN($units)-or[double]::IsInfinity($units)-or[math]::Abs($units)-gt1000000000000){$known=$false}}catch{$known=$false}
        foreach($days in @(7,30,90)){if($age-lt$days){if($known){$m['sales'+$days]+=$units}else{$m['units_unknown'+$days]++}}}
    }
    $money=Get-LocalRoyaltyTotals @($rows|Where-Object{[bool](Get-PropertyValue $_ 'linked')}) $now;foreach($property in $money.PSObject.Properties){$m[$property.Name]=$property.Value}
    $m['overlap_imports']=@($s.sales_imports|Where-Object{[int](Get-PropertyValue $_ 'potential_overlap_rows')-gt0}).Count
    $m['incomplete_numeric_imports']=@($s.sales_imports|Where-Object{[int](Get-PropertyValue $_ 'unreadable_amounts')-gt0}).Count
    return [pscustomobject]$m
}
function Update-LocalCoreBusinessSurfaces {
    try {
    if($null -eq $HomeMetricSalesValue){return};$m=Get-LocalSalesMetrics;$s=Read-LocalCoreState;$packages=0;$accepted=0;foreach($c in @($s.concepts)){ $packages+=Get-LocalCurrentReadyPackageCount $c $s;$ca=Get-PropertyValue $c 'active_acceptance';if($null-ne$ca-and![string]::IsNullOrWhiteSpace([string](Get-PropertyValue $c 'source_revision_id'))-and[string](Get-PropertyValue $c 'source_revision_hash')-match'^[0-9a-f]{64}$'-and[string](Get-PropertyValue $ca 'concept_revision_id')-ceq[string](Get-PropertyValue $c 'source_revision_id')-and[string](Get-PropertyValue $ca 'revision_hash')-ceq[string](Get-PropertyValue $c 'source_revision_hash')){$accepted++}}
    $receipts=@($s.publication_receipts|Where-Object{Test-LocalPublicationReceiptAuthority $s $_});$productKeys=@{};$channelKeys=@{};foreach($receipt in $receipts){$pk=Get-LocalPublicationProductKey $receipt;$ch=([string](Get-PropertyValue $receipt 'channel')).Trim().ToLowerInvariant();if(-not[string]::IsNullOrWhiteSpace($pk)){$productKeys[$pk]=$true};if(-not[string]::IsNullOrWhiteSpace($ch)){$channelKeys[$ch]=$true}};$publishedCount=$productKeys.Count;$channelCount=$channelKeys.Count;$hasLinked=($m.linked_rows -gt 0)
    $HomeMetricSalesValue.Text=if($hasLinked){(Format-LocalSalesUnits $m 30)}else{'—'};$HomeMetricRoyaltiesValue.Text=if($hasLinked){(Format-LocalRoyaltyTotal $m 30 -Compact)}else{'—'};$HomeMetricPublishedValue.Text=if($publishedCount-gt0){[string]$publishedCount}else{'—'}
    if($null-ne$PortfolioProductsValue){$PortfolioProductsValue.Text=if($publishedCount-gt0){[string]$publishedCount}else{'—'}};if($null-ne$PortfolioChannelsValue){$PortfolioChannelsValue.Text=if($channelCount-gt0){[string]$channelCount}else{'—'}};if($null-ne$PortfolioHealthValue){$PortfolioHealthValue.Text='—'}
    if($null-ne$PerfSales7Value){$PerfSales7Value.Text=if($hasLinked){(Format-LocalSalesUnits $m 7)}else{'—'}};if($null-ne$PerfSales30Value){$PerfSales30Value.Text=if($hasLinked){(Format-LocalSalesUnits $m 30)}else{'—'}};if($null-ne$PerfRoyalties30Value){$PerfRoyalties30Value.Text=if($hasLinked){(Format-LocalRoyaltyTotal $m 30 -Compact)}else{'—'}};if($null-ne$PerfSales90Value){$PerfSales90Value.Text=if($hasLinked){(Format-LocalSalesUnits $m 90)}else{'—'}}
    if($null-ne$HomePerformanceBody){$HomePerformanceBody.Text=if($hasLinked){((Get-UiText 'money.home' 'Verified imported units / royalties: 7d {0} / {1}; 30d {2} / {3}; 90d {4} / {5}. Royalties are not net profit.') -f (Format-LocalSalesUnits $m 7),(Format-LocalRoyaltyTotal $m 7),(Format-LocalSalesUnits $m 30),(Format-LocalRoyaltyTotal $m 30),(Format-LocalSalesUnits $m 90),(Format-LocalRoyaltyTotal $m 90))}elseif($m.rows){((Get-UiText 'biz.home.unlinked' 'Imported data is not linked to a verified Forge publication receipt; {0} row(s) excluded.') -f $m.unlinked_rows)}else{Get-UiText 'biz.home.none' 'Import a sales/royalty CSV to populate local performance.'}}
    if($null-ne$PortfolioEmpty){$PortfolioEmpty.Text=((Get-UiText 'biz.portfolio.local' 'Local core: {0} accepted design(s), {1} valid package(s), {2} verified published product(s). Live listing health is not fabricated.') -f $accepted,$packages,$publishedCount)};if($null-ne$LocalPublicationStatusText){$LocalPublicationStatusText.Text=if($publishedCount-gt0){((Get-UiText 'biz.receipts.some' 'Verified published products: {0} · channels: {1}') -f $publishedCount,$channelCount)}else{Get-UiText 'biz.receipts.none' 'No verified local publication receipt imported.'}}
    if($null-ne$PerformanceEmpty){$PerformanceEmpty.Text=if($hasLinked){((Get-UiText 'money.performance' 'Verified linked sales rows: {0}. 30-day units: {1}; royalties: {2}. Royalties are not net profit.') -f $m.linked_rows,(Format-LocalSalesUnits $m 30),(Format-LocalRoyaltyTotal $m 30))}elseif($m.rows){((Get-UiText 'biz.perf.unlinked' 'No imported sales rows match a verified Forge product ID. Unlinked rows: {0}.') -f $m.unlinked_rows)}else{Get-UiText 'biz.perf.none' 'No local sales CSV imported yet.'}};if($null-ne$LocalSalesStatusText){$LocalSalesStatusText.Text=if($m.rows){((Get-UiText 'biz.sales.some' 'Imported: {0} · linked: {1} · unlinked: {2} · undated linked: {3} · future linked: {4}') -f $m.rows,$m.linked_rows,$m.unlinked_rows,$m.undated_rows,$m.future_rows)}else{Get-UiText 'biz.sales.none' 'No local sales data imported.'}}
    if($m.overlap_imports-gt0){$overlapNotice=(Get-UiText 'money.overlap.warning' 'Potential overlap was acknowledged in {0} import(s); totals may include repeated transactions.')-f$m.overlap_imports;foreach($label in @($HomePerformanceBody,$PerformanceEmpty)){if($null-ne$label){$label.Text+=[Environment]::NewLine+$overlapNotice}}}
    if($m.incomplete_numeric_imports-gt0-or$m.units_unknown30-gt0){
        $warning=switch($script:Locale){'ru'{'Часть числовых полей CSV отсутствует, неоднозначна или не читается; итоги неполные. Исходные значения сохраняются. Повторно импортируйте точный CSV для проверки сохранённого разбора.'}'es'{'Faltan campos numéricos o son ambiguos; los totales están incompletos. Se conservan los valores originales. Reimporta el CSV exacto para revisar su interpretación.'}default{'Some CSV numeric fields are missing, unreadable or ambiguous; totals are incomplete. Original values are retained. Re-import the exact CSV to revalidate saved interpretation.'}}
        foreach($label in @($HomePerformanceBody,$PerformanceEmpty)){if($null-ne$label){$label.Text+=[Environment]::NewLine+$warning}}
    }
    if($hasLinked){$basis=(Get-UiText 'money.windows' 'Imported calendar dates; today is the UTC date. 7d {0}–{3}; 30d {1}–{3}; 90d {2}–{3} (inclusive).')-f$m.window_start7,$m.window_start30,$m.window_start90,$m.window_end;foreach($label in @($HomePerformanceBody,$PerformanceEmpty)){if($null-ne$label){$label.Text+=[Environment]::NewLine+$basis}}}
    try{Update-PerformanceInsightsSurface}catch{Write-AppLog 'WARN' ('Performance insights refresh failed: '+$_.Exception.Message)}
    try{if(Get-Command Update-AmazonProfileSurface -ErrorAction SilentlyContinue){Update-AmazonProfileSurface}}catch{Write-AppLog 'WARN' ('Amazon profile status refresh failed: '+$_.Exception.Message)}
    try{if(Get-Command Update-DataCopySurface -ErrorAction SilentlyContinue){Update-DataCopySurface}}catch{}
    try{if(Get-Command Update-WhatsNewCard -ErrorAction SilentlyContinue){Update-WhatsNewCard}}catch{}

    } catch {
        Write-AppLog 'WARN' ('Business refresh could not verify local state: '+$_.Exception.Message)
        foreach($label in @($HomeMetricSalesValue,$HomeMetricRoyaltiesValue,$HomeMetricPublishedValue,$PortfolioProductsValue,$PortfolioChannelsValue,$PortfolioHealthValue,$PerfSales7Value,$PerfSales30Value,$PerfRoyalties30Value,$PerfSales90Value)){if($null-ne$label){$label.Text='-'}}
        $message=Get-UiText 'pipe.state.unavailable' 'Local state is unavailable; readiness and performance cannot be verified. Retry refresh or use My data recovery. Unsaved editor fields are preserved.'
        foreach($label in @($HomePerformanceBody,$PortfolioEmpty,$PerformanceEmpty,$LocalPublicationStatusText,$LocalSalesStatusText)){if($null-ne$label){$label.Text=$message}}
    }
}
function Update-LocalCoreStatusUi {
    if($null -eq $script:Current){return};$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key);if($null -eq $lc){return};$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=Get-PropertyValue $lc 'active_acceptance';$accepted=($null-ne$acc -and [string](Get-PropertyValue $acc 'concept_revision_id') -eq $identity.id -and [string](Get-PropertyValue $acc 'revision_hash') -eq $identity.hash)
    $v=@(Get-LocalCoreVariantsForCurrent).Count;$validPackages=Get-LocalCurrentReadyPackageCount $lc;$text=((Get-UiText 'lc.status' 'Artwork: {0} · accepted: {1} · ready packages: {2}') -f $v,$(if($accepted){Get-UiText 'lc.yes' 'yes'}else{Get-UiText 'lc.no' 'no'}),$validPackages)
    if(Test-ForgeRecoveryReviewRequired $lc){$text+=' '+(Get-UiText 'recovery.approval.review' 'DRAFT package only. Workspace data was recovered; review and approve the exact saved idea and design again.')}
    if($null-ne$LocalCoreStatusText){$LocalCoreStatusText.Text=$text};if($null-ne$LocalAcceptButton){$LocalAcceptButton.IsEnabled=($VariantList.SelectedItems.Count -eq 1 -and [bool](Get-PropertyValue $VariantList.SelectedItems[0] 'local_only'))};if($null-ne$LocalBuildPackageButton){$LocalBuildPackageButton.IsEnabled=$accepted}
}
function Enter-LocalCoreSection([string]$Section) {
    if($null -eq $script:Current){return}
    $null=Ensure-LocalCoreConceptFromCurrent
    $MainTabs.Visibility='Visible'
    foreach($tab in @($MainTabs.Items)){if($tab -is [Windows.Controls.TabItem]){$key=Get-MainTabKey $tab;$tab.IsEnabled=($key -in @('overview','visuals','evidence','publication'))}}
    switch($Section){
        'artwork'{Select-MainTab 'Visuals & Generate';Refresh-LocalArtworkUi}
        'checks'{Select-MainTab 'Evidence';Load-LocalChecksUi}
        'publish'{Select-MainTab 'Publication';Load-LocalPublicationUi}
        default{Select-MainTab 'Overview'}
    }
    Update-MainTabUi
}
function Convert-LiveCheckState([string]$State) {
    $v=([string]$State).Trim().ToLowerInvariant()
    switch($v){'pass'{return 'pass'}'not_required'{return 'not_required'}'blocked'{return 'blocked'}'fail'{return 'blocked'}'needs_review'{return 'needs_review'}default{return 'needs_review'}}
}
function Sync-LocalChecksFromLiveWorkspace($Workspace) {
    if($null -eq $script:Current -or $null -eq $Workspace){return}
    try {
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null-eq$lc){$null=Ensure-LocalCoreConceptFromCurrent;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s};$acc=Get-PropertyValue $lc 'active_acceptance';$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$now=[DateTime]::UtcNow.ToString('o')
        $ipRaw=[string](Get-PropertyValue $Workspace 'ip_status');if($ipRaw){$lc.checks.ip=[pscustomobject]@{state=(Convert-LiveCheckState $ipRaw);source='live_backend';note=('Imported from live workspace for exact current revision: '+$ipRaw);checked_at=$now;scope='revision';concept_revision_id=$identity.id;asset_sha256='';listing_hash='';legal_clearance=$false;authority_kind='live_backend_exact';evidence_refs=@(('live_backend:ip_status:'+$ipRaw));evidence_source_file_sha256='';evidence_schema='forge.live_workspace.v1'}}
        if($null-ne$acc){$liveSha=([string](Get-PropertyValue $Workspace 'accepted_variant_sha256')).Trim().ToLowerInvariant();$liveRev=[string](Get-PropertyValue $Workspace 'current_revision_id');if($liveSha -eq [string]$acc.asset_sha256 -and $liveRev -eq [string]$acc.concept_revision_id){
            foreach($pair in @(@('visual','visual_qa_status'),@('print','print_qa_status'))){$raw=[string](Get-PropertyValue $Workspace $pair[1]);if($raw){$lc.checks.PSObject.Properties[$pair[0]].Value=[pscustomobject]@{state=(Convert-LiveCheckState $raw);source='live_backend_exact_asset';note=('Imported from live workspace for exact accepted artwork: '+$raw);checked_at=$now;scope='artwork';concept_revision_id=[string]$acc.concept_revision_id;asset_sha256=[string]$acc.asset_sha256;listing_hash='';authority_kind='live_backend_exact';evidence_refs=@(('live_backend:'+$pair[1]+':'+$raw));evidence_source_file_sha256='';evidence_schema='forge.live_workspace.v1'}}}
            $policyRaw=[string](Get-PropertyValue $Workspace 'policy_preflight_status');if($policyRaw){
                $localListingHash=Get-LocalPublicationHash $lc.publication;$listingMatches=Test-LocalPublicationMatchesLiveWorkspace $lc.publication $Workspace;$policyProfile=Get-LocalPolicyProfileBinding;$profileMatches=Test-LocalPolicyProfileMatchesLiveWorkspace $policyProfile $Workspace
                if($listingMatches -and $profileMatches -and -not[string]::IsNullOrWhiteSpace($localListingHash)){
                    $liveProfileHash=([string](Get-PropertyValue $Workspace 'channel_profile_hash')).Trim().ToLowerInvariant();$policyRefs=@(('live_backend:policy_preflight_status:'+$policyRaw));if(-not[string]::IsNullOrWhiteSpace($liveProfileHash)){$policyRefs+=('live_backend:channel_profile_hash:'+$liveProfileHash)}
                    $lc.checks.policy=[pscustomobject]@{state=(Convert-LiveCheckState $policyRaw);source='live_backend_exact_listing_profile';note=('Imported from live workspace for exact accepted artwork, exact local listing, and matching Amazon marketplace/product/template profile: '+$policyRaw);checked_at=$now;scope='listing';concept_revision_id=[string]$acc.concept_revision_id;asset_sha256=[string]$acc.asset_sha256;listing_hash=$localListingHash;channel_profile_fingerprint=[string]$policyProfile.profile_fingerprint;marketplace=[string]$policyProfile.marketplace;product_type_key=[string]$policyProfile.product_type_key;template_key=[string]$policyProfile.template_key;authority_kind='live_backend_exact';evidence_refs=@($policyRefs);evidence_source_file_sha256='';evidence_schema='forge.live_workspace.v1'}
                }else{
                    $existingPolicy=Get-PropertyValue $lc.checks 'policy';if(([string](Get-PropertyValue $existingPolicy 'authority_kind')).Trim().ToLowerInvariant() -eq 'live_backend_exact'){$reason=if(-not$listingMatches){'live_backend_listing_mismatch'}elseif($null-eq$policyProfile){'local_policy_profile_missing_or_expired'}else{'live_backend_policy_profile_mismatch'};$lc.checks.policy=New-LocalCoreCheckRecord 'needs_review' $reason 'Live policy state is not authority for the current local listing and Amazon marketplace/product/template profile.' 'listing' ([string]$acc.concept_revision_id) ([string]$acc.asset_sha256) $localListingHash}
                }
            }
        }}
        # Metadata validation is deliberately not imported: only exact field equality is used to bind live policy to the local listing hash.
        Write-LocalCoreState $s
    } catch {Write-AppLog 'WARN' ('Live-to-local check sync failed: '+$_.Exception.Message)}
}
