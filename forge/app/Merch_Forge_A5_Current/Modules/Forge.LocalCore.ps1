# Merch Forge · Local-first core workflow
# Owns local artwork import, local exact acceptance, local check evidence, manual-upload package generation,
# and local sales CSV import. It never submits to an external marketplace and never pretends local state is server state.
. (Join-Path $PSScriptRoot 'Forge.PrintChecks.ps1')

function Enter-LocalCoreMutationLock {
    Ensure-Dir $script:LocalCoreRoot;$path=Join-Path $script:LocalCoreRoot 'state-mutation.lock'
    try{return [IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{throw 'Local Forge state is being updated in another window. Nothing was overwritten; refresh and try again.'}
}
function Initialize-LocalCore {
    foreach($p in @($script:LocalCoreRoot,$script:LocalCoreArtworkRoot,$script:LocalCorePackageRoot,$script:LocalCoreExportRoot,$script:LocalCoreImportRoot)){Ensure-Dir $p}
    $null=Initialize-GenerationProviderRegistry
    $null=Assert-GenerationProviderConfigSafe
    Initialize-PrintChecks
    $hasPrimary=Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf;$hasBackup=Test-Path -LiteralPath $script:LocalCoreBackupPath -PathType Leaf
    if(-not $hasPrimary -and -not $hasBackup){try{Write-LocalCoreState (New-LocalCoreState)}catch{if($_.Exception.Message -like 'Local Forge state changed in another window*' -or $_.Exception.Message -like 'Local Forge state is being updated in another window*'){$null=Read-LocalCoreState}else{throw}}}else{$null=Read-LocalCoreState}
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
function Convert-LocalCoreStateToV2($State) {
    if($null -eq $State){return (New-LocalCoreState)}
    $schema=[string](Get-PropertyValue $State 'schema');if($schema -eq 'forge.local_core.v2'){if($null -eq $State.PSObject.Properties['state_revision']){Add-OrSetProperty $State 'state_revision' 0};if($null -eq $State.PSObject.Properties['last_write_id']){Add-OrSetProperty $State 'last_write_id' ''};return $State};if($schema -ne 'forge.local_core.v1'){throw 'Unsupported local-core state schema.'}
    Add-OrSetProperty $State 'schema' 'forge.local_core.v2';Add-OrSetProperty $State 'state_revision' 0;Add-OrSetProperty $State 'last_write_id' ''
    foreach($c in @((Get-PropertyValue $State 'concepts'))){
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
    if($null -eq $State){return $false};$schema=[string](Get-PropertyValue $State 'schema');if($schema -notin @('forge.local_core.v1','forge.local_core.v2')){return $false}
    foreach($name in @('concepts','sales_imports','sales_rows','publication_receipts')){$prop=$State.PSObject.Properties[$name];if($null -eq $prop -or $null -eq $prop.Value){return $false}}
    if($schema -eq 'forge.local_core.v2'){
        if($null -eq $State.PSObject.Properties['state_revision']){return $false};try{$rev=[int64](Get-PropertyValue $State 'state_revision')}catch{return $false};if($rev -lt 1){return $false};$writeProp=$State.PSObject.Properties['last_write_id'];if($null -ne $writeProp){$writeId=[string]$writeProp.Value;if(-not[string]::IsNullOrWhiteSpace($writeId) -and $writeId -notmatch '^[0-9a-fA-F]{32}$'){return $false}}
    }
    return $true
}
function Read-LocalCoreStateCandidate([string]$Path) {
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){return $null};$state=Get-Content -LiteralPath $Path -Raw -Encoding UTF8|ConvertFrom-Json;$schema=[string](Get-PropertyValue $state 'schema');if($schema -notin @('forge.local_core.v1','forge.local_core.v2')){throw 'Unsupported local-core state schema.'};if(-not(Test-LocalCorePersistedStateEnvelope $state)){throw 'Local-core state envelope is structurally incomplete.'};return (Convert-LocalCoreStateToV2 $state)
}
function Preserve-LocalCoreUnreadableArtifacts {
    foreach($path in @($script:LocalCoreStatePath,$script:LocalCoreBackupPath)){try{if(Test-Path -LiteralPath $path -PathType Leaf){$sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();$copy=$path+'.corrupt.'+$sha.Substring(0,16);if(-not(Test-Path -LiteralPath $copy -PathType Leaf)){Copy-Item -LiteralPath $path -Destination $copy -Force}}}catch{}}
}
function Repair-LocalCorePrimaryFromBackup {
    $lock=$null;$tmp=$script:LocalCoreStatePath+'.restore.'+[Guid]::NewGuid().ToString('N');try{
        $lock=Enter-LocalCoreMutationLock
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){try{$current=Read-LocalCoreStateCandidate $script:LocalCoreStatePath;if($null -ne $current){return $current}}catch{if($_.Exception.Message -like 'Unsupported local-core state schema*'){throw}}}
        $backup=Read-LocalCoreStateCandidate $script:LocalCoreBackupPath;if($null -eq $backup){throw 'Local-core last-good backup is unavailable.'};Copy-Item -LiteralPath $script:LocalCoreBackupPath -Destination $tmp -Force;$verified=Read-LocalCoreStateCandidate $tmp;if($null -eq $verified){throw 'Local-core last-good backup copy failed verification.'}
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){$quarantine=$script:LocalCoreStatePath+'.corrupt.'+[DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff')+'.'+[Guid]::NewGuid().ToString('N');[IO.File]::Replace($tmp,$script:LocalCoreStatePath,$quarantine,$true)}else{Move-Item -LiteralPath $tmp -Destination $script:LocalCoreStatePath -Force}
        if((Get-FileHash -LiteralPath $script:LocalCoreStatePath -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $script:LocalCoreBackupPath -Algorithm SHA256).Hash){throw 'Recovered local-core primary does not match the last-good backup.'};Write-AppLog 'WARN' 'Recovered local-core primary state from exact last-good backup.';return (Read-LocalCoreStateCandidate $script:LocalCoreStatePath)
    } finally {if($null -ne $lock){try{$lock.Dispose()}catch{}};Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}
}
function Read-LocalCoreState {
    $primaryExists=Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf;$backupExists=Test-Path -LiteralPath $script:LocalCoreBackupPath -PathType Leaf;$hadArtifact=($primaryExists -or $backupExists);$primaryError='';$backupError=''
    if($primaryExists){try{return (Read-LocalCoreStateCandidate $script:LocalCoreStatePath)}catch{$primaryError=$_.Exception.Message;if($primaryError -like 'Unsupported local-core state schema*'){Preserve-LocalCoreUnreadableArtifacts;throw ('Local Forge state uses an unsupported schema. Recovery stopped; no empty state was created. '+$primaryError)}}}
    if($backupExists){try{return (Repair-LocalCorePrimaryFromBackup)}catch{$backupError=$_.Exception.Message}}
    if(-not $hadArtifact){$fresh=New-LocalCoreState;try{Write-LocalCoreState $fresh;return $fresh}catch{if($_.Exception.Message -like 'Local Forge state changed in another window*' -or $_.Exception.Message -like 'Local Forge state is being updated in another window*'){return (Read-LocalCoreState)};throw}}
    Preserve-LocalCoreUnreadableArtifacts;$detail=(@($primaryError,$backupError)|Where-Object{-not[string]::IsNullOrWhiteSpace($_)}) -join ' | ';Write-AppLog 'ERROR' ('Local core recovery stopped; existing state artifacts are unreadable or invalid. '+$detail);throw ('Local Forge state recovery stopped because existing primary/last-good state could not be validated. No empty state was created. Preserved recovery copies remain under '+$script:LocalCoreRoot+'.')
}
function Write-LocalCoreState($State) {
    Ensure-Dir $script:LocalCoreRoot
    $State=Convert-LocalCoreStateToV2 $State
    $expectedRev=0;try{$expectedRev=[int64](Get-PropertyValue $State 'state_revision')}catch{}
    $stateLock=$null;$tmp=$script:LocalCoreStatePath+'.tmp.'+[Guid]::NewGuid().ToString('N');$backupTmp=$script:LocalCoreBackupPath+'.tmp.'+[Guid]::NewGuid().ToString('N');$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false
    try {
        $stateLock=Enter-LocalCoreMutationLock
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){
            try{$disk=Get-Content -LiteralPath $script:LocalCoreStatePath -Raw -Encoding UTF8|ConvertFrom-Json;$diskSchema=[string](Get-PropertyValue $disk 'schema');$diskRev=0;try{$diskRev=[int64](Get-PropertyValue $disk 'state_revision')}catch{};if($diskSchema -notin @('forge.local_core.v1','forge.local_core.v2')){throw 'Unsupported local-core state schema.'};if($diskRev -ne $expectedRev){throw ('Local Forge state changed in another window. Expected revision '+$expectedRev+' but current revision is '+$diskRev+'. Nothing was overwritten; refresh and try again.')}}catch{if($_.Exception.Message -like 'Local Forge state changed in another window*'){throw};throw ('Current local-core state cannot be safely compared before write: '+$_.Exception.Message)}
        } elseif($expectedRev -ne 0){throw ('Local Forge state changed in another window. Expected revision '+$expectedRev+' but the current state file is missing. Nothing was overwritten; refresh and try again.')}
        $State.state_revision=$expectedRev+1;$State.last_write_id=[Guid]::NewGuid().ToString('N');$State.updated_at=[DateTime]::UtcNow.ToString('o')
        $json=$State|ConvertTo-Json -Depth 60
        $fs=New-Object IO.FileStream($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try{$bytes=$utf8.GetBytes($json);$fs.Write($bytes,0,$bytes.Length);$fs.Flush($true)}finally{$fs.Dispose()}
        $verify=Get-Content -LiteralPath $tmp -Raw -Encoding UTF8|ConvertFrom-Json
        if([string](Get-PropertyValue $verify 'schema') -ne 'forge.local_core.v2' -or [string](Get-PropertyValue $verify 'last_write_id') -ne [string]$State.last_write_id -or [int64](Get-PropertyValue $verify 'state_revision') -ne ($expectedRev+1)){throw 'Local core temp state failed verification.'}
        if(Test-Path -LiteralPath $script:LocalCoreStatePath -PathType Leaf){
            [IO.File]::Replace($tmp,$script:LocalCoreStatePath,$backupTmp,$true)
            Move-Item -LiteralPath $backupTmp -Destination $script:LocalCoreBackupPath -Force
        } else {
            Move-Item -LiteralPath $tmp -Destination $script:LocalCoreStatePath -Force
            Copy-Item -LiteralPath $script:LocalCoreStatePath -Destination $script:LocalCoreBackupPath -Force
        }
    } finally {if($null -ne $stateLock){try{$stateLock.Dispose()}catch{}};Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue;Remove-Item -LiteralPath $backupTmp -Force -ErrorAction SilentlyContinue}
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
    if($authority -eq 'owner_attested_external'){$fileSha=([string](Get-PropertyValue $Check 'evidence_source_file_sha256')).Trim().ToLowerInvariant();if($fileSha -notmatch '^[0-9a-f]{64}$'){return $false}}
    return $true
}
function Ensure-LocalCoreConceptFromCurrent {
    if($null -eq $script:Current){return $null};$c=Get-PropertyValue $script:Current 'concept';if($null -eq $c){return $null}
    $key=([string](Get-PropertyValue $c 'concept_key')).Trim();if([string]::IsNullOrWhiteSpace($key)){return $null}
    $identity=Get-LocalCurrentRevisionIdentity $c
    Add-OrSetProperty $c 'current_revision_id' $identity.id;Add-OrSetProperty $c 'current_content_hash' $identity.hash
    $s=Read-LocalCoreState;$existing=Get-LocalCoreConcept $key $s
    if($null -eq $existing){
        $existing=[pscustomobject]@{concept_key=$key;title=[string](Get-PropertyValue $c 'title');hook=[string](Get-PropertyValue $c 'hook');niche_name=[string](Get-PropertyValue $c 'niche_name');concept_text=[string](Get-PropertyValue $c 'concept_text');visual_direction_text=[string](Get-PropertyValue $c 'visual_direction_text');source_revision_id=$identity.id;source_revision_hash=$identity.hash;owner_decision='UNDECIDED';owner_decision_revision_id=$identity.id;owner_decision_revision_hash=$identity.hash;owner_decision_at='';artwork=@();active_acceptance=$null;checks=(New-LocalCoreChecks $identity.id);publication=$null;packages=@()}
        $s.concepts=@($s.concepts)+@($existing)
    } else {
        $oldId=[string](Get-PropertyValue $existing 'source_revision_id');$oldHash=[string](Get-PropertyValue $existing 'source_revision_hash')
        $revisionChanged=(($oldId -and $oldId -ne $identity.id) -or ($oldHash -and $oldHash -ne $identity.hash))
        foreach($pair in @(@('title','title'),@('hook','hook'),@('niche_name','niche_name'),@('concept_text','concept_text'),@('visual_direction_text','visual_direction_text'))){$v=[string](Get-PropertyValue $c $pair[1]);if(-not [string]::IsNullOrWhiteSpace($v)){Add-OrSetProperty $existing $pair[0] $v}}
        Add-OrSetProperty $existing 'source_revision_id' $identity.id;Add-OrSetProperty $existing 'source_revision_hash' $identity.hash
        if($null -eq $existing.PSObject.Properties['artwork']){$existing|Add-Member -NotePropertyName artwork -NotePropertyValue @() -Force};if($null -eq $existing.PSObject.Properties['packages']){$existing|Add-Member -NotePropertyName packages -NotePropertyValue @() -Force}
        if($null -eq $existing.PSObject.Properties['owner_decision']){Add-OrSetProperty $existing 'owner_decision' 'UNDECIDED'}
        if($null -eq $existing.PSObject.Properties['owner_decision_revision_id']){Add-OrSetProperty $existing 'owner_decision_revision_id' $identity.id}
        if($null -eq $existing.PSObject.Properties['owner_decision_revision_hash']){Add-OrSetProperty $existing 'owner_decision_revision_hash' $identity.hash}
        if($null -eq $existing.PSObject.Properties['owner_decision_at']){Add-OrSetProperty $existing 'owner_decision_at' ''}
        if($revisionChanged){
            foreach($a in @($existing.artwork)){$a.accepted=$false};$existing.active_acceptance=$null;$existing.checks=New-LocalCoreChecks $identity.id;$existing.publication=$null;Invalidate-LocalCorePackages $existing 'concept_revision_changed';Add-OrSetProperty $existing 'owner_decision' 'UNDECIDED';Add-OrSetProperty $existing 'owner_decision_revision_id' $identity.id;Add-OrSetProperty $existing 'owner_decision_revision_hash' $identity.hash;Add-OrSetProperty $existing 'owner_decision_at' ''
        } else {
            if($null -eq $existing.PSObject.Properties['checks']){$existing|Add-Member -NotePropertyName checks -NotePropertyValue (New-LocalCoreChecks $identity.id) -Force}
            $defaults=New-LocalCoreChecks $identity.id;foreach($n in @('ip','visual','print','policy','metadata')){if($null -eq $existing.checks.PSObject.Properties[$n]){$existing.checks|Add-Member -NotePropertyName $n -NotePropertyValue (Get-PropertyValue $defaults $n) -Force}}
        }
    }
    Write-LocalCoreState $s;return $existing
}
function Get-LocalOwnerDecisionRecord([string]$ConceptKey,$Concept=$null,$State=$null) {
    $key=([string]$ConceptKey).Trim();if([string]::IsNullOrWhiteSpace($key)){return [pscustomobject]@{decision='UNDECIDED';revision_id='';revision_hash='';decided_at='';is_current=$false}}
    if($null-eq$State){$State=Read-LocalCoreState};$lc=Get-LocalCoreConcept $key $State;if($null-eq$lc){return [pscustomobject]@{decision='UNDECIDED';revision_id='';revision_hash='';decided_at='';is_current=$false}}
    if($null-eq$Concept -and $null-ne$script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq $key){$Concept=$script:Current.concept}
    $currentIdentity=if($null-ne$Concept){Get-LocalCurrentRevisionIdentity $Concept}else{[pscustomobject]@{id=[string](Get-PropertyValue $lc 'source_revision_id');hash=[string](Get-PropertyValue $lc 'source_revision_hash')}}
    $decision=([string](Get-PropertyValue $lc 'owner_decision')).Trim().ToUpperInvariant();if($decision -notin @('KEEP','EDIT','REGEN','SKIP')){$decision='UNDECIDED'}
    $rid=([string](Get-PropertyValue $lc 'owner_decision_revision_id')).Trim();$rhash=([string](Get-PropertyValue $lc 'owner_decision_revision_hash')).Trim().ToLowerInvariant();$isCurrent=(-not[string]::IsNullOrWhiteSpace($rid) -and -not[string]::IsNullOrWhiteSpace($rhash) -and $rid -eq [string]$currentIdentity.id -and $rhash -eq ([string]$currentIdentity.hash).ToLowerInvariant())
    if(-not$isCurrent){$decision='UNDECIDED'}
    return [pscustomobject]@{decision=$decision;revision_id=$rid;revision_hash=$rhash;decided_at=[string](Get-PropertyValue $lc 'owner_decision_at');is_current=$isCurrent}
}
function Set-LocalOwnerDecision([string]$Decision) {
    if($null-eq$script:Current){Show-Error 'Choose an idea first.';return $false}
    $d=([string]$Decision).Trim().ToUpperInvariant();if($d -notin @('KEEP','EDIT','REGEN','SKIP','UNDECIDED')){Show-Error 'Invalid owner decision.';return $false}
    try {
        $null=Ensure-LocalCoreConceptFromCurrent;$key=[string](Get-PropertyValue $script:Current.concept 'concept_key');$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept $key $s;if($null-eq$lc){throw 'Local concept state is unavailable.'}
        Add-OrSetProperty $lc 'owner_decision' $d;Add-OrSetProperty $lc 'owner_decision_revision_id' $identity.id;Add-OrSetProperty $lc 'owner_decision_revision_hash' $identity.hash;Add-OrSetProperty $lc 'owner_decision_at' $(if($d-eq'UNDECIDED'){''}else{[DateTime]::UtcNow.ToString('o')})
        Write-LocalCoreState $s
        try{Update-OwnerDecisionControls}catch{}
        Refresh-StageFilterIfActive
        if($null-ne$StatusText){$StatusText.Text=if($d-eq'UNDECIDED'){'Owner decision cleared.'}else{('Owner decision saved locally: '+$d)}}
        return $true
    } catch {Show-Error ('Owner decision was not saved: '+$_.Exception.Message);return $false}
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
function Get-LocalArtworkInfo([string]$Path) {
    $bytes=[IO.File]::ReadAllBytes($Path);if($bytes.Length -lt 1){throw 'Artwork file is empty.'}
    $bmp=ConvertTo-FrozenBitmapImage $bytes
    $ext=[IO.Path]::GetExtension($Path).ToLowerInvariant()
    $mime=switch($ext){'.png'{'image/png'}'.jpg'{'image/jpeg'}'.jpeg'{'image/jpeg'}default{'application/octet-stream'}}
    return [pscustomobject]@{bytes=$bytes;sha256=(Get-ByteSha256Hex $bytes);width_px=$bmp.PixelWidth;height_px=$bmp.PixelHeight;mime_type=$mime;extension=$ext}
}
function Add-LocalArtworkFromPath([string]$Path,[string]$GenerationRequestId='local-import',[string]$ProviderKey='manual_artwork_bridge',[string]$ExpectedRevisionId='',[string]$ExpectedRevisionHash='',[string]$ExpectedAssetSha='',$Provenance=$null) {
    if($null -eq $script:Current){throw 'Choose an idea first.'};if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw 'Artwork file is missing.'};$info=Get-LocalArtworkInfo $Path;if($info.mime_type -notin @('image/png','image/jpeg')){throw 'Only PNG and JPEG artwork are supported.'}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;if($ExpectedRevisionId -and $ExpectedRevisionId -ne $identity.id){throw 'Generated artwork belongs to another revision.'};if($ExpectedRevisionHash -and $ExpectedRevisionHash -ne $identity.hash){throw 'Generated artwork revision hash is stale.'};if($ExpectedAssetSha -and $ExpectedAssetSha.ToLowerInvariant() -ne $info.sha256){throw 'Generated artwork SHA-256 does not match its result manifest.'}
    $null=Ensure-LocalCoreConceptFromCurrent;$state=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $state;$safe=Get-LocalCoreSafeKey $lc.concept_key;$dir=Join-Path $script:LocalCoreArtworkRoot $safe;Ensure-Dir $dir;$dest=Join-Path $dir ($info.sha256+$info.extension);if(-not(Test-Path -LiteralPath $dest)){[IO.File]::WriteAllBytes($dest,$info.bytes)};if((Get-FileSha256Hex $dest) -ne $info.sha256){throw 'Local artwork copy failed SHA-256 verification.'}
    $existing=$null;foreach($v in @($lc.artwork)){if([string](Get-PropertyValue $v 'asset_sha256') -eq $info.sha256 -and [string](Get-PropertyValue $v 'concept_revision_id') -eq $identity.id){$existing=$v;break}}
    if($null -ne $existing -and $null -ne $Provenance){Add-OrSetProperty $existing 'generation_request_id' $GenerationRequestId;Add-OrSetProperty $existing 'provider_key' $ProviderKey;foreach($n in @('provider_profile','provider_model','provider_contract_version','provider_registry_sha256','provider_config_fingerprint','prompt_compiler_version','prompt_template_sha256','provider_request_id','generation_result_sha256','generation_attempt_sha256','prompt_sha256','revised_prompt','provider_usage')){Add-OrSetProperty $existing $n (Get-PropertyValue $Provenance $n)};Add-OrSetProperty $existing 'generation_method' 'local_provider_worker';Add-OrSetProperty $existing 'local_file_path' $dest;Add-OrSetProperty $existing 'local_only' $true;Add-OrSetProperty $existing 'asset_availability' 'available';Write-LocalCoreState $state}
    if($null -eq $existing){$idx=@($lc.artwork).Count+1;$integrity=[pscustomobject]@{state='pass';source='local_integrity';note=("Image decoded successfully; SHA-256 verified; {0}×{1}; {2}." -f $info.width_px,$info.height_px,$info.mime_type);checked_at=[DateTime]::UtcNow.ToString('o');scope='artwork';concept_revision_id=$identity.id;asset_sha256=$info.sha256;listing_hash=''};$existing=[pscustomobject]@{id=('local-'+$info.sha256.Substring(0,16));variant_key=('local-'+$info.sha256.Substring(0,16));variant_index=$idx;status='available';review_state='neutral';review_note='';latest_reason_codes=@();asset_sha256=$info.sha256;preview_key='';concept_revision_id=$identity.id;source_revision_hash=$identity.hash;generation_request_id=$GenerationRequestId;provider_key=$ProviderKey;provider_profile=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_profile')}else{''};provider_model=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_model')}else{''};provider_contract_version=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_contract_version')}else{''};provider_registry_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_registry_sha256')}else{''};provider_config_fingerprint=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_config_fingerprint')}else{''};prompt_compiler_version=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'prompt_compiler_version')}else{''};prompt_template_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'prompt_template_sha256')}else{''};provider_request_id=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'provider_request_id')}else{''};generation_result_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'generation_result_sha256')}else{''};generation_attempt_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'generation_attempt_sha256')}else{''};prompt_sha256=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'prompt_sha256')}else{''};revised_prompt=if($null-ne$Provenance){[string](Get-PropertyValue $Provenance 'revised_prompt')}else{''};provider_usage=if($null-ne$Provenance){Get-PropertyValue $Provenance 'provider_usage'}else{$null};generation_method=if($ProviderKey-eq'manual_artwork_bridge'){'local_import'}else{'local_provider_worker'};asset_metadata=[pscustomobject]@{preview_health='available';mime_type=$info.mime_type;width_px=$info.width_px;height_px=$info.height_px};asset_availability='available';mime_type=$info.mime_type;width_px=$info.width_px;height_px=$info.height_px;local_file_path=$dest;local_only=$true;accepted=$false;integrity_check=$integrity;created_at=[DateTime]::UtcNow.ToString('o');allowed_actions=[pscustomobject]@{review=$true;accept=$true}};$lc.artwork=@($lc.artwork)+@($existing);Write-LocalCoreState $state}
    return $existing
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
function Export-LocalGenerationBrief {
    if($null -eq $script:Current){Show-Error 'Choose an idea first.';return};$lc=Ensure-LocalCoreConceptFromCurrent;if($null -eq $lc){Show-Error 'Local concept state could not be prepared.';return}
    $c=$script:Current.concept;$identity=Get-LocalCurrentRevisionIdentity $c;$key=Get-LocalCoreSafeKey ([string]$c.concept_key);$dir=Join-Path $script:LocalCoreExportRoot $key;Ensure-Dir $dir
    $brief=[ordered]@{schema='forge.local_generation_brief.v2';created_at=[DateTime]::UtcNow.ToString('o');concept_key=[string]$c.concept_key;title=[string]$c.title;hook=[string]$c.hook;niche_name=[string](Get-PropertyValue $c 'niche_name');concept=[string](Get-PropertyValue $c 'concept_text');visual_direction=[string](Get-PropertyValue $c 'visual_direction_text');source_revision_id=$identity.id;source_revision_hash=$identity.hash;provider_mode=$script:LocalGenerationProviderMode;external_generation_authorized=$false;note='Creative brief only. Import the finished image back into Merch Forge; exact SHA/revision binding is required before acceptance.'}
    $stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss');$jsonPath=Join-Path $dir ("generation-brief-$stamp.json");$txtPath=Join-Path $dir ("generation-brief-$stamp.txt");$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false
    [IO.File]::WriteAllText($jsonPath,($brief|ConvertTo-Json -Depth 12),$utf8);$txt=@('MERCH FORGE — GENERATION BRIEF','',"Title: $($brief.title)","Hook: $($brief.hook)","Niche: $($brief.niche_name)",'',"Revision: $($brief.source_revision_id)","Revision SHA256: $($brief.source_revision_hash)",'','Concept:',"$($brief.concept)",'','Visual direction:',"$($brief.visual_direction)",'','Boundary: creative brief only; no provider dispatch or publishing was authorized.') -join "`r`n";[IO.File]::WriteAllText($txtPath,$txt,$utf8)
    $StatusText.Text=('Generation brief saved locally: '+$txtPath);if($null -ne $LocalCoreStatusText){$LocalCoreStatusText.Text='Generation brief prepared. Import the resulting artwork for exact review.'}
}
function Import-LocalArtwork {
    if($null -eq $script:Current){Show-Error 'Choose an idea first.';return};$dlg=New-Object Microsoft.Win32.OpenFileDialog;$dlg.Title='Import artwork into Merch Forge';$dlg.Filter='Artwork (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg';$dlg.Multiselect=$false;if($dlg.ShowDialog() -ne $true){return}
    try{$null=Add-LocalArtworkFromPath $dlg.FileName 'local-import' 'manual_artwork_bridge';Refresh-LocalArtworkUi;$StatusText.Text='Artwork imported locally and SHA-256 verified for the current revision.'}catch{Show-Error $_.Exception.Message;$StatusText.Text='Artwork import failed.'}
}
function Set-LocalExactAcceptance($Variant,[bool]$SkipOwnerConfirm=$false) {
    if($null -eq $script:Current){throw 'Choose an idea first.'};$v=$Variant;if($null -eq $v){throw 'Select exactly one local artwork file first.'};if(-not [bool](Get-PropertyValue $v 'local_only')){throw 'Use the normal Accept action for server-managed variants.'}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;if([string](Get-PropertyValue $v 'concept_revision_id') -ne $identity.id -or [string](Get-PropertyValue $v 'source_revision_hash') -ne $identity.hash){throw 'This artwork belongs to another idea revision. Import artwork for the current revision.'}
    $sha=[string](Get-PropertyValue $v 'asset_sha256');$path=[string](Get-PropertyValue $v 'local_file_path');if($sha -notmatch '^[0-9a-f]{64}$' -or -not(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileSha256Hex $path) -ne $sha){throw 'Local artwork failed exact-file verification.'}
    if(-not $SkipOwnerConfirm){if(-not(Confirm ("Accept this exact local artwork?`n`nSHA-256: {0}`nRevision: {1}`n`nThis creates LOCAL acceptance only." -f $sha,$identity.id) 'Accept local artwork')){return $false}}
    $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc){throw 'Local concept state is unavailable.'};foreach($x in @($lc.artwork)){$x.accepted=([string]$x.asset_sha256 -eq $sha -and [string]$x.concept_revision_id -eq $identity.id)}
    $fp=New-LocalAcceptanceFingerprint ([string]$lc.concept_key) $identity.id $identity.hash $sha;$providerKey=([string](Get-PropertyValue $v 'provider_key')).Trim();if([string]::IsNullOrWhiteSpace($providerKey)){$providerKey='manual_artwork_bridge'};$lc.active_acceptance=[pscustomobject]@{concept_key=[string]$lc.concept_key;concept_revision_id=$identity.id;revision_hash=$identity.hash;variant_id=[string]$v.id;asset_sha256=$sha;local_file_path=$path;accepted_at=[DateTime]::UtcNow.ToString('o');lineage_fingerprint=$fp;sync_state='local_only';source=if($providerKey-eq'manual_artwork_bridge'){'local_artwork_import'}else{'local_provider_worker'};provider_key=$providerKey;generation_request_id=[string](Get-PropertyValue $v 'generation_request_id');provider_profile=[string](Get-PropertyValue $v 'provider_profile');provider_model=[string](Get-PropertyValue $v 'provider_model');provider_contract_version=[string](Get-PropertyValue $v 'provider_contract_version');provider_registry_sha256=[string](Get-PropertyValue $v 'provider_registry_sha256');provider_config_fingerprint=[string](Get-PropertyValue $v 'provider_config_fingerprint');prompt_compiler_version=[string](Get-PropertyValue $v 'prompt_compiler_version');prompt_template_sha256=[string](Get-PropertyValue $v 'prompt_template_sha256');provider_request_id=[string](Get-PropertyValue $v 'provider_request_id');generation_result_sha256=[string](Get-PropertyValue $v 'generation_result_sha256');generation_attempt_sha256=[string](Get-PropertyValue $v 'generation_attempt_sha256');prompt_sha256=[string](Get-PropertyValue $v 'prompt_sha256');revised_prompt=[string](Get-PropertyValue $v 'revised_prompt');provider_usage=(Get-PropertyValue $v 'provider_usage')}
    $oldIp=Get-PropertyValue $lc.checks 'ip';$lc.checks=New-LocalCoreChecks $identity.id $sha
    if($null -ne $oldIp -and [string](Get-PropertyValue $oldIp 'concept_revision_id') -eq $identity.id -and (Test-LocalCheckStatePass $oldIp)){$lc.checks.ip=$oldIp}
    $lc.checks.visual=[pscustomobject]@{state='pass';source='owner_exact_accept';note='Owner explicitly reviewed and accepted this exact artwork; the local file decoded successfully and its SHA-256 was verified before acceptance.';checked_at=[DateTime]::UtcNow.ToString('o');scope='artwork';concept_revision_id=$identity.id;asset_sha256=$sha;listing_hash='';authority_kind='owner_exact_accept';evidence_refs=@(('sha256:'+$sha));evidence_source_file_sha256='';evidence_schema='forge.owner_exact_accept.v1'}
    if($null -ne $lc.publication){Add-OrSetProperty $lc.publication 'concept_revision_id' $identity.id;Add-OrSetProperty $lc.publication 'accepted_artwork_sha256' $sha;Add-OrSetProperty $lc.publication 'acceptance_fingerprint' $fp;Add-OrSetProperty $lc.publication 'content_hash' (Get-LocalPublicationHash $lc.publication)}
    Invalidate-LocalCorePackages $lc 'accepted_artwork_changed';Write-LocalCoreState $s;try{$null=Write-LocalCheckRequestBundle}catch{Write-AppLog 'WARN' ('Check request export after Accept failed: '+$_.Exception.Message)};try{$null=Invoke-LocalCheckAutomation}catch{Write-AppLog 'WARN' ('Local check automation after Accept failed: '+$_.Exception.Message)};return $true
}
function Accept-LocalArtwork {
    if($null -eq $script:Current){return};$sel=@($VariantList.SelectedItems);if($sel.Count -ne 1){Show-Error 'Select exactly one local artwork file first.';return}
    try{if(Set-LocalExactAcceptance $sel[0] $false){Refresh-LocalArtworkUi;Refresh-StageFilterIfActive;$StatusText.Text='Exact local artwork accepted for the current revision. Downstream checks were rebound fail-closed.'}}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local artwork acceptance failed.'}
}
function Write-LocalCheckRequestBundle {
    if($null -eq $script:Current){return $null};$state=Read-LocalCoreState;$key=[string](Get-PropertyValue $script:Current.concept 'concept_key');$lc=Get-LocalCoreConcept $key $state;if($null -eq $lc -or $null -eq $lc.active_acceptance){return $null}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=$lc.active_acceptance;if([string](Get-PropertyValue $acc 'concept_revision_id') -ne $identity.id -or [string](Get-PropertyValue $acc 'revision_hash') -ne $identity.hash){return $null}
    $artPath=[string](Get-PropertyValue $acc 'local_file_path');$artSha=([string](Get-PropertyValue $acc 'asset_sha256')).ToLowerInvariant();if(-not(Test-Path -LiteralPath $artPath -PathType Leaf) -or $artSha -notmatch '^[0-9a-f]{64}$' -or (Get-FileSha256Hex $artPath) -ne $artSha){return $null}
    $info=Get-LocalArtworkInfo $artPath;$listingHash=Get-LocalPublicationHash $lc.publication;$policyProfile=Get-LocalPolicyProfileBinding;$lineageKey=Get-StringSha256Hex ((@($key,$identity.id,$identity.hash,$artSha,$listingHash)-join '|').ToLowerInvariant())
    $pngCheck=$null;if($info.mime_type -eq 'image/png'){try{$pngCheck=Test-ForgeGenerationPngFile $artPath $info.width_px $info.height_px}catch{}}
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
    $evidence=[ordered]@{schema='forge.local_check_evidence.v3';request_id=[string]$request.request_id;lineage_key=$lineageKey;concept_key=$key;concept_revision_id=$identity.id;artwork_sha256=$artSha;listing_hash=$listingHash}
    foreach($name in @('ip','visual','print','policy','metadata')){$cur=Get-PropertyValue $lc.checks $name;$evidence[$name]=[ordered]@{state=[string](Get-PropertyValue $cur 'state');source=[string](Get-PropertyValue $cur 'source');note=[string](Get-PropertyValue $cur 'note');checked_at=[string](Get-PropertyValue $cur 'checked_at');authority_kind=if($name-eq'visual'){'owner_exact_accept'}else{'owner_attested_external'};evidence_refs=@();attested=$false}}
    if($null-ne$policyProfile){$evidence['policy']['channel_profile_fingerprint']=[string]$policyProfile.profile_fingerprint;$evidence['policy']['marketplace']=[string]$policyProfile.marketplace;$evidence['policy']['product_type_key']=[string]$policyProfile.product_type_key;$evidence['policy']['template_key']=[string]$policyProfile.template_key}
    $safe=Get-LocalCoreSafeKey $key;$dir=Join-Path $script:LocalCoreExportRoot (Join-Path $safe 'checks');Ensure-Dir $dir;$requestPath=Join-Path $dir ('check-request-'+$lineageKey.Substring(0,16)+'.json');$evidencePath=Join-Path $dir ('check-evidence-'+$lineageKey.Substring(0,16)+'.template.json');$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false
    foreach($pair in @(@($requestPath,$request),@($evidencePath,$evidence))){$tmp=[string]$pair[0]+'.tmp.'+[Guid]::NewGuid().ToString('N');[IO.File]::WriteAllText($tmp,($pair[1]|ConvertTo-Json -Depth 50),$utf8);$verify=Get-Content -LiteralPath $tmp -Raw -Encoding UTF8|ConvertFrom-Json;if([string](Get-PropertyValue $verify 'concept_key') -ne $key){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue;throw 'Check request export verification failed.'};Move-Item -LiteralPath $tmp -Destination ([string]$pair[0]) -Force}
    try{if(Get-Command Write-LocalCheckChecklistFile -ErrorAction SilentlyContinue){$null=Write-LocalCheckChecklistFile $evidencePath}}catch{Write-AppLog 'WARN' ('Checklist file export failed: '+$_.Exception.Message)}
    return [pscustomobject]@{request_path=$requestPath;request_sha256=(Get-FileSha256Hex $requestPath);evidence_template_path=$evidencePath;evidence_template_sha256=(Get-FileSha256Hex $evidencePath);lineage_key=$lineageKey}
}
function Import-LocalCheckEvidence {
    if($null -eq $script:Current){Show-Error 'Choose an idea first.';return};$dlg=New-Object Microsoft.Win32.OpenFileDialog;$dlg.Title='Import check evidence';$dlg.Filter='JSON evidence (*.json)|*.json';if($dlg.ShowDialog() -ne $true){return};Import-LocalCheckEvidenceFromPath $dlg.FileName
}
function Import-LocalCheckEvidenceFromPath([string]$Path) {
    $script:LastCheckEvidenceImportOk=$false
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){Show-Error 'File not found.';return}
    try {
        $evidencePath=$Path;$evidenceFileSha=Get-FileSha256Hex $evidencePath;$e=$null;try{$e=Get-Content -LiteralPath $evidencePath -Raw -Encoding UTF8|ConvertFrom-Json}catch{throw 'The evidence file is not valid JSON. Open it in Notepad and check quotes and commas, or use Confirm checks.'};$schema=[string](Get-PropertyValue $e 'schema');if($schema -notin @('forge.local_check_evidence.v1','forge.local_check_evidence.v2','forge.local_check_evidence.v3')){throw 'Unsupported check evidence schema.'}
        $key=[string](Get-PropertyValue $e 'concept_key');if($key -and $key -ne [string]$script:Current.concept.concept_key){throw 'Evidence belongs to a different concept. Use the newest template from the checks folder, or press Confirm checks.'}
        $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc){$null=Ensure-LocalCoreConceptFromCurrent;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s}
        $accept=Get-PropertyValue $lc 'active_acceptance';$acceptedSha=if($null-ne $accept){[string](Get-PropertyValue $accept 'asset_sha256')}else{''};$listingHash=Get-LocalPublicationHash $lc.publication;$currentPolicyProfile=Get-LocalPolicyProfileBinding
        $eRev=([string](Get-PropertyValue $e 'concept_revision_id')).Trim();$eSha=([string](Get-PropertyValue $e 'artwork_sha256')).Trim().ToLowerInvariant();$eListing=([string](Get-PropertyValue $e 'listing_hash')).Trim().ToLowerInvariant()
        foreach($name in @('ip','visual','print','policy','metadata')){
            $incoming=Get-PropertyValue $e $name;if($null -eq $incoming){continue};$state=([string](Get-PropertyValue $incoming 'state')).Trim().ToLowerInvariant();if($state -notin @('pass','needs_review','blocked','not_required')){throw ("Invalid {0} state in evidence JSON." -f $name)}
            $isPassing=($state -in @('pass','not_required'));$scope=if($name -eq 'ip'){'revision'}elseif($name -in @('policy','metadata')){'listing'}else{'artwork'}
            if($name -eq 'visual'){if($isPassing){$existingVisual=Get-PropertyValue $lc.checks 'visual';if(-not(Test-LocalCheckPass $existingVisual $lc 'visual')){throw 'Visual PASS is created only by exact local Accept for the current artwork.'}};continue}
            $source=([string](Get-PropertyValue $incoming 'source')).Trim();$note=[string](Get-PropertyValue $incoming 'note');$checkedAt=([string](Get-PropertyValue $incoming 'checked_at')).Trim();$authority=([string](Get-PropertyValue $incoming 'authority_kind')).Trim().ToLowerInvariant();$refValidation=Get-LocalEvidenceRefValidation (Get-PropertyValue $incoming 'evidence_refs');$refs=@(Get-PropertyValue $refValidation 'valid_refs');$attested=[bool](Get-PropertyValue $incoming 'attested')
            if($isPassing){
                if($schema -ne 'forge.local_check_evidence.v3'){throw 'Only v3 authority-bound evidence may create a new passing check.'}
                if($eRev -ne $identity.id){throw ("{0} evidence revision does not match the current idea revision. Use the newest template from the checks folder, or press Confirm checks." -f $name)}
                if($scope -in @('artwork','listing')){if([string]::IsNullOrWhiteSpace($acceptedSha) -or $eSha -ne $acceptedSha){throw ("{0} evidence artwork SHA does not match the exact accepted artwork. Use the newest template from the checks folder, or press Confirm checks." -f $name)}}
                if($scope -eq 'listing'){if([string]::IsNullOrWhiteSpace($listingHash) -or $eListing -ne $listingHash){throw (([string]$name)+' evidence listing_hash does not match the current listing revision. Use the newest template from the checks folder, or press Confirm checks.')}}
                if([string]::IsNullOrWhiteSpace($source) -or [string]::IsNullOrWhiteSpace($checkedAt)){throw ("{0} passing evidence requires source and checked_at." -f $name)}
                try{$checkedTime=[DateTime]::Parse($checkedAt,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind);if($checkedTime.ToUniversalTime() -gt [DateTime]::UtcNow.AddMinutes(10)){throw 'future'}}catch{throw ("{0} checked_at must be a valid non-future ISO date/time." -f $name)}
                if(-not((Get-LocalCheckAllowedAuthority $name $state) -contains $authority)){throw ("{0} authority_kind is not allowed for state {1}." -f $name,$state)}
                if($authority -eq 'owner_attested_external' -and -not $attested){throw ("{0} owner_attested_external evidence requires attested=true." -f $name)}
                if($authority -notin @('owner_exact_accept','live_backend_exact')){if([int](Get-PropertyValue $refValidation 'invalid_count') -gt 0){throw ("{0} passing evidence contains an empty or non-string evidence_ref." -f $name)};if($refs.Count -lt 1){throw ("{0} passing evidence requires at least one non-empty string evidence_ref." -f $name)}}
                if($authority -in @('live_backend_exact','verified_worker','verified_channel_profile')){throw ("Imported owner JSON cannot self-assert authority_kind {0}; use the corresponding verified sync/worker/profile path." -f $authority)}
                if($name -eq 'visual' -and $authority -ne 'owner_exact_accept'){throw 'Imported owner JSON cannot replace the exact-accept visual authority.'}
                if($name -eq 'policy'){
                    if($null-eq$currentPolicyProfile){throw 'Passing policy evidence requires a current valid owner-attested Amazon print profile.'}
                    $eProfileFp=([string](Get-PropertyValue $incoming 'channel_profile_fingerprint')).Trim().ToLowerInvariant();$eMarket=([string](Get-PropertyValue $incoming 'marketplace')).Trim().ToLowerInvariant();$eProduct=([string](Get-PropertyValue $incoming 'product_type_key')).Trim().ToLowerInvariant();$eTemplate=([string](Get-PropertyValue $incoming 'template_key')).Trim().ToLowerInvariant()
                    if($eProfileFp -ne [string]$currentPolicyProfile.profile_fingerprint -or $eMarket -ne [string]$currentPolicyProfile.marketplace -or $eProduct -ne [string]$currentPolicyProfile.product_type_key -or $eTemplate -ne [string]$currentPolicyProfile.template_key){throw 'Policy evidence Amazon profile binding does not match the current owner-attested print profile. Use the newest template from the checks folder, or press Confirm checks.'}
                }
            }
            $obj=[pscustomobject]@{state=$state;source=$source;note=$note;checked_at=$checkedAt;scope=$scope;concept_revision_id=$eRev;asset_sha256=if($scope -in @('artwork','listing')){$eSha}else{''};listing_hash=if($scope -eq 'listing'){$eListing}else{''};channel_profile_fingerprint=if($name-eq'policy' -and $isPassing){([string](Get-PropertyValue $incoming 'channel_profile_fingerprint')).Trim().ToLowerInvariant()}else{''};marketplace=if($name-eq'policy' -and $isPassing){([string](Get-PropertyValue $incoming 'marketplace')).Trim().ToLowerInvariant()}else{''};product_type_key=if($name-eq'policy' -and $isPassing){([string](Get-PropertyValue $incoming 'product_type_key')).Trim().ToLowerInvariant()}else{''};template_key=if($name-eq'policy' -and $isPassing){([string](Get-PropertyValue $incoming 'template_key')).Trim().ToLowerInvariant()}else{''};authority_kind=if($isPassing){$authority}else{'none'};evidence_refs=if($isPassing){@($refs)}else{@()};evidence_source_file_sha256=$evidenceFileSha;evidence_schema=$schema}
            if($name -eq 'ip'){$obj|Add-Member -NotePropertyName legal_clearance -NotePropertyValue $false -Force};$lc.checks.PSObject.Properties[$name].Value=$obj
        }
        Write-LocalCoreState $s;try{$null=Write-LocalCheckRequestBundle}catch{Write-AppLog 'WARN' ('Check request refresh after evidence import failed: '+$_.Exception.Message)};Load-LocalChecksUi;$StatusText.Text='Authority-bound local check evidence imported.';$script:LastCheckEvidenceImportOk=$true
    } catch {Show-Error $_.Exception.Message;$StatusText.Text='Check evidence import failed.'}
}
function Format-LocalCheck([string]$Label,$Check) {
    $keys=@{IP='ip';Visual='visual';Print='print';Policy='policy';Metadata='metadata'}; $k=if($keys.ContainsKey($Label)){$keys[$Label]}else{$Label.ToLowerInvariant()}
    $lab=Get-UiText ('chk.label.'+$k) $Label
    if($null -eq $Check){return ("{0} · {1}" -f $lab,(Get-UiText 'chk.view.none' 'Not checked'))}
    $state=[string](Get-PropertyValue $Check 'state'); $st=Get-UiText ('chk.view.'+$state) $state
    $note=[string](Get-PropertyValue $Check 'note'); try{ if(Get-Command Translate-UiMessage -ErrorAction SilentlyContinue){ $note=Translate-UiMessage $note } }catch{}
    return ("{0} · {1}`n{2}" -f $lab,$st,$note)
}
function Load-LocalChecksUi {
    if($null -eq $script:Current){return};$lc=Ensure-LocalCoreConceptFromCurrent;if($null -eq $lc){return};try{if($null-ne$lc.active_acceptance){$null=Invoke-LocalCheckAutomation;$lc=Ensure-LocalCoreConceptFromCurrent}}catch{Write-AppLog 'WARN' ('Local check automation on Checks open failed: '+$_.Exception.Message)}
    $AnalysisEvidence.Text=(Format-LocalCheck 'IP' $lc.checks.ip)+"`n`n"+(Format-LocalCheck 'Visual' $lc.checks.visual)+"`n`n"+(Format-LocalCheck 'Print' $lc.checks.print)+"`n`n"+(Format-LocalCheck 'Policy' $lc.checks.policy)+"`n`n"+(Format-LocalCheck 'Metadata' $lc.checks.metadata)
    $AnalysisWarnings.Text='Local checks are evidence for workflow continuity only. IP pass is not a legal opinion; marketplace policy and print requirements must be revalidated before external publication.'
    if($null -ne $LocalCheckStatusText){$LocalCheckStatusText.Text=Get-UiText 'checks.loaded' 'Checks loaded. Press "Confirm checks…" to confirm IP, policy and listing text.'}
}
function Get-LocalPublicationDefault($lc) {
    $keywords=@();foreach($piece in @([string]$lc.niche_name,[string]$lc.title,[string]$lc.hook)){foreach($w in ($piece -split '[^A-Za-z0-9]+')){if($w.Length -ge 3 -and $keywords -notcontains $w.ToLowerInvariant()){$keywords+=$w.ToLowerInvariant()}}};if($keywords.Count -gt 12){$keywords=@($keywords[0..11])}
    $acc=Get-PropertyValue $lc 'active_acceptance';$p=[pscustomobject]@{listing_title=[string]$lc.title;brand='';bullet_1=[string]$lc.hook;bullet_2='';description=[string]$lc.concept_text;keywords=@($keywords);locale='en-US';saved_at='';revision_no=0;concept_revision_id=[string](Get-PropertyValue $lc 'source_revision_id');accepted_artwork_sha256=if($null-ne $acc){[string](Get-PropertyValue $acc 'asset_sha256')}else{''};acceptance_fingerprint=if($null-ne $acc){[string](Get-PropertyValue $acc 'lineage_fingerprint')}else{''};content_hash=''};$p.content_hash=Get-LocalPublicationHash $p;return $p
}
function Load-LocalPublicationUi {
    if($null -eq $script:Current){return};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc){$null=Ensure-LocalCoreConceptFromCurrent;$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s}
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=Get-PropertyValue $lc 'active_acceptance';$hasAccept=($null-ne$acc -and [string](Get-PropertyValue $acc 'concept_revision_id') -eq $identity.id -and [string](Get-PropertyValue $acc 'revision_hash') -eq $identity.hash)
    if($null -eq $lc.publication){$lc.publication=Get-LocalPublicationDefault $lc;Write-LocalCoreState $s};$p=$lc.publication
    $PublicationTitleBox.Text=[string]$p.listing_title;$PublicationBrandBox.Text=[string]$p.brand;$PublicationBullet1Box.Text=[string]$p.bullet_1;$PublicationBullet2Box.Text=[string]$p.bullet_2;$PublicationDescriptionBox.Text=[string]$p.description;$PublicationKeywordsBox.Text=(@($p.keywords)-join ', ')
    foreach($box in @($PublicationTitleBox,$PublicationBrandBox,$PublicationBullet1Box,$PublicationBullet2Box,$PublicationDescriptionBox,$PublicationKeywordsBox,$PublicationReasonBox)){$box.IsEnabled=$hasAccept;$box.IsReadOnly=(-not $hasAccept)};$PublicationLocaleBox.IsEnabled=$hasAccept
    $PublicationCreativeStatus.Text=if($hasAccept){'Exact local artwork is accepted for the current revision. Listing edits remain local until packaged.'}else{'Accept exact artwork for the current idea revision before preparing the listing.'}
    $PublicationCheckIp.Text=Format-LocalCheck 'IP' $lc.checks.ip;$PublicationCheckVisual.Text=Format-LocalCheck 'Visual' $lc.checks.visual;$PublicationCheckPrint.Text=Format-LocalCheck 'Print' $lc.checks.print;$PublicationCheckPolicy.Text=Format-LocalCheck 'Marketplace policy' $lc.checks.policy
    $PublicationEconomics.Text='No royalty amount is fabricated locally. Import verified commerce data after publication.';$PublicationPreflight.Text=Get-LocalPackageReadinessText $lc;$PublicationExternal.Text='External submission remains manual and locked inside Merch Forge. Local package creation never submits anything.';$DeliveryStatus.Text=if(@($lc.packages|Where-Object{[bool](Get-PropertyValue $_ 'valid')}).Count){('Valid local package(s): '+@($lc.packages|Where-Object{[bool](Get-PropertyValue $_ 'valid')}).Count)}else{'No valid local manual-upload package created yet.'}
    $script:Publication=[pscustomobject]@{local_core=$true;workspace=[pscustomobject]@{current_revision_accepted=$hasAccept}};Set-PublicationDirty $false;if($null-ne$SavePublicationButton){$SavePublicationButton.IsEnabled=$hasAccept};if($null-ne$LocalBuildPackageButton){$LocalBuildPackageButton.IsEnabled=$hasAccept}
}
function Save-LocalPublicationMetadata {
    if($null -eq $script:Current){return $false};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc -or $null -eq $lc.active_acceptance){Show-Error 'Accept local artwork first.';return $false}
    $acc=$lc.active_acceptance;$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;if([string]$acc.concept_revision_id -ne $identity.id -or [string]$acc.revision_hash -ne $identity.hash){Show-Error 'Local acceptance is stale for this idea revision.';return $false}
    $title=([string]$PublicationTitleBox.Text).Trim();if([string]::IsNullOrWhiteSpace($title)){Show-Error 'Listing title is required.';return $false};$kw=@();foreach($x in (([string]$PublicationKeywordsBox.Text)-split '[,;]')){$v=$x.Trim();if($v){$kw+=$v}};$rev=1;try{$rev=[int]$lc.publication.revision_no+1}catch{}
    $p=[pscustomobject]@{listing_title=$title;brand=[string]$PublicationBrandBox.Text;bullet_1=[string]$PublicationBullet1Box.Text;bullet_2=[string]$PublicationBullet2Box.Text;description=[string]$PublicationDescriptionBox.Text;keywords=@($kw);locale=(Get-PublicationLocale);saved_at=[DateTime]::UtcNow.ToString('o');revision_no=$rev;edit_reason=[string]$PublicationReasonBox.Text;concept_revision_id=$identity.id;accepted_artwork_sha256=[string]$acc.asset_sha256;acceptance_fingerprint=[string]$acc.lineage_fingerprint;content_hash=''};$p.content_hash=Get-LocalPublicationHash $p
    $oldHash=if($null-ne $lc.publication){[string](Get-PropertyValue $lc.publication 'content_hash')}else{''};$lc.publication=$p
    if($oldHash -ne $p.content_hash){$freshChecks=New-LocalCoreChecks $identity.id ([string]$acc.asset_sha256) $p.content_hash;$lc.checks.policy=$freshChecks.policy;$lc.checks.metadata=$freshChecks.metadata;Invalidate-LocalCorePackages $lc 'listing_metadata_changed'}
    Write-LocalCoreState $s;try{$bundle=Write-LocalCheckRequestBundle;if($null-ne$bundle){$StatusText.Text=('Local listing draft saved as revision '+$rev+'. Check request refreshed for this exact listing. Nothing was published.')}else{$StatusText.Text=('Local listing draft saved as revision '+$rev+'. Nothing was published.')}}catch{Write-AppLog 'WARN' ('Check request refresh after listing save failed: '+$_.Exception.Message);$StatusText.Text=('Local listing draft saved as revision '+$rev+'. Nothing was published.')};try{$null=Invoke-LocalCheckAutomation}catch{Write-AppLog 'WARN' ('Local check automation after listing save failed: '+$_.Exception.Message)};Set-PublicationDirty $false;Load-LocalPublicationUi;return $true
}
function Test-LocalCheckStatePass($Check) { return ([string](Get-PropertyValue $Check 'state') -in @('pass','not_required')) }
function Test-LocalCheckPass($Check,$lc,[string]$Name) {
    if(-not(Test-LocalCheckStatePass $Check) -or -not(Test-LocalCheckEvidenceAuthority $Name $Check) -or $null -eq $lc -or $null -eq $lc.active_acceptance){return $false};$acc=$lc.active_acceptance;$rev=[string](Get-PropertyValue $acc 'concept_revision_id');$sha=[string](Get-PropertyValue $acc 'asset_sha256')
    if([string](Get-PropertyValue $Check 'concept_revision_id') -ne $rev){return $false}
    if($Name -in @('visual','print','policy','metadata')){if([string](Get-PropertyValue $Check 'asset_sha256') -ne $sha){return $false}}
    if($Name -in @('policy','metadata')){$lh=Get-LocalPublicationHash $lc.publication;if([string]::IsNullOrWhiteSpace($lh) -or [string](Get-PropertyValue $Check 'listing_hash') -ne $lh){return $false}}
    if($Name -eq 'policy' -and -not(Test-LocalPolicyProfileBinding $Check)){return $false}
    return $true
}
function Get-LocalCheckGateSnapshot($lc) {
    $items=[ordered]@{};$allReady=$true
    foreach($name in @('ip','visual','print','policy','metadata')){$c=Get-PropertyValue $lc.checks $name;$ready=Test-LocalCheckPass $c $lc $name;if(-not $ready){$allReady=$false};$items[$name]=[ordered]@{state=[string](Get-PropertyValue $c 'state');ready=$ready;authority_kind=[string](Get-PropertyValue $c 'authority_kind');source=[string](Get-PropertyValue $c 'source');checked_at=[string](Get-PropertyValue $c 'checked_at');evidence_refs=@(Get-PropertyValue $c 'evidence_refs');evidence_source_file_sha256=[string](Get-PropertyValue $c 'evidence_source_file_sha256');evidence_schema=[string](Get-PropertyValue $c 'evidence_schema');channel_profile_fingerprint=[string](Get-PropertyValue $c 'channel_profile_fingerprint');marketplace=[string](Get-PropertyValue $c 'marketplace');product_type_key=[string](Get-PropertyValue $c 'product_type_key');template_key=[string](Get-PropertyValue $c 'template_key')}}
    return [pscustomobject]@{all_ready=$allReady;checks=$items}
}
function Get-LocalPackageReadinessText($lc) {
    if($null -eq $lc.active_acceptance){return 'Blocked: accept exact artwork first.'};$acc=$lc.active_acceptance;if([string](Get-PropertyValue $acc 'concept_revision_id') -ne [string](Get-PropertyValue $lc 'source_revision_id') -or [string](Get-PropertyValue $acc 'revision_hash') -ne [string](Get-PropertyValue $lc 'source_revision_hash')){return 'Blocked: local acceptance belongs to an older idea revision.'}
    if($null -eq $lc.publication){return 'Blocked: save listing metadata for this exact accepted artwork.'};if([string](Get-PropertyValue $lc.publication 'acceptance_fingerprint') -ne [string](Get-PropertyValue $acc 'lineage_fingerprint')){return 'Blocked: listing metadata belongs to another accepted artwork.'}
    $missing=@();foreach($n in @('ip','visual','print','policy','metadata')){if(-not(Test-LocalCheckPass (Get-PropertyValue $lc.checks $n) $lc $n)){$missing+=$n}}
    if($missing.Count -eq 0){return 'READY for manual-upload package creation. Exact revision/artwork/listing lineage is verified locally.'};return ('DRAFT package only. Exact-lineage checks need attention: '+($missing -join ', ')+'.')
}
function Build-LocalAmazonPackage {
    if($null -eq $script:Current){return}
    try {
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null -eq $lc -or $null -eq $lc.active_acceptance){throw 'Accept exact local artwork first.'};if(-not(Save-LocalPublicationMetadata)){throw 'Local listing draft could not be saved.'}
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;$acc=$lc.active_acceptance;$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept
        if([string]$acc.concept_revision_id -ne $identity.id -or [string]$acc.revision_hash -ne $identity.hash){throw 'Acceptance lineage is stale for the current idea revision.'};if([string](Get-PropertyValue $lc.publication 'acceptance_fingerprint') -ne [string]$acc.lineage_fingerprint){throw 'Listing metadata is not bound to the current accepted artwork.'}
        $art=[string]$acc.local_file_path;$sha=[string]$acc.asset_sha256;if(-not(Test-Path -LiteralPath $art -PathType Leaf) -or (Get-FileSha256Hex $art) -ne $sha){throw 'Accepted local artwork failed SHA-256 verification.'}
        $printProduction=Get-LocalPrintProductionSnapshot $lc $identity $acc;$gate=Get-LocalCheckGateSnapshot $lc;$checksReady=([bool]$gate.all_ready -and [bool](Get-PropertyValue $printProduction 'ready'))
        $status=if($checksReady){'READY_FOR_MANUAL_UPLOAD'}else{'DRAFT_BLOCKED'};$listingHash=Get-LocalPublicationHash $lc.publication
        $safe=Get-LocalCoreSafeKey $lc.concept_key;$stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff');$stage=Join-Path $script:LocalCorePackageRoot ($safe+'-'+$stamp+'-stage');Ensure-Dir $stage;$ext=[IO.Path]::GetExtension($art);$artName='artwork'+$ext;Copy-Item -LiteralPath $art -Destination (Join-Path $stage $artName) -Force
        $printPath=Join-Path $stage 'print-production.json';$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($printPath,($printProduction|ConvertTo-Json -Depth 40),$utf8);$printSha=Get-FileSha256Hex $printPath;$metadata=[ordered]@{schema='forge.amazon_manual_package.v3';status=$status;concept_key=$lc.concept_key;title=$lc.title;hook=$lc.hook;lineage=[ordered]@{concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string]$acc.lineage_fingerprint;accepted_artwork_sha256=$sha;listing_hash=$listingHash};accepted_artwork=[ordered]@{file=$artName;sha256=$sha;variant_id=$acc.variant_id;accepted_at=$acc.accepted_at;source=$acc.source;generation_request_id=[string](Get-PropertyValue $acc 'generation_request_id');provider_key=[string](Get-PropertyValue $acc 'provider_key');provider_profile=[string](Get-PropertyValue $acc 'provider_profile');provider_model=[string](Get-PropertyValue $acc 'provider_model');provider_contract_version=[string](Get-PropertyValue $acc 'provider_contract_version');provider_registry_sha256=[string](Get-PropertyValue $acc 'provider_registry_sha256');provider_config_fingerprint=[string](Get-PropertyValue $acc 'provider_config_fingerprint');prompt_compiler_version=[string](Get-PropertyValue $acc 'prompt_compiler_version');prompt_template_sha256=[string](Get-PropertyValue $acc 'prompt_template_sha256');provider_request_id=[string](Get-PropertyValue $acc 'provider_request_id');generation_result_sha256=[string](Get-PropertyValue $acc 'generation_result_sha256');generation_attempt_sha256=[string](Get-PropertyValue $acc 'generation_attempt_sha256');prompt_sha256=[string](Get-PropertyValue $acc 'prompt_sha256');revised_prompt=[string](Get-PropertyValue $acc 'revised_prompt');provider_usage=(Get-PropertyValue $acc 'provider_usage')};listing=$lc.publication;checks=$lc.checks;check_gate=$gate;print_production=$printProduction;print_production_sha256=$printSha;external_submission_authorized=$false;manual_upload_required=$true;created_at=[DateTime]::UtcNow.ToString('o')};[IO.File]::WriteAllText((Join-Path $stage 'metadata.json'),($metadata|ConvertTo-Json -Depth 40),$utf8);$preupload=[ordered]@{schema='forge.preupload_gate.v1';status=$status;concept_key=[string]$lc.concept_key;lineage=[ordered]@{concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string]$acc.lineage_fingerprint;accepted_artwork_sha256=$sha;listing_hash=$listingHash};all_checks_ready=([bool]$gate.all_ready -and [bool](Get-PropertyValue $printProduction 'ready'));checks=$gate.checks;print_production_sha256=$printSha;print_production_ready=[bool](Get-PropertyValue $printProduction 'ready');authority_boundary='READY means exact-lineage workflow evidence is present; IP owner attestation is not a legal opinion; external submission remains manual.';external_submission_authorized=$false;created_at=[DateTime]::UtcNow.ToString('o')};$preuploadPath=Join-Path $stage 'preupload-gate.json';[IO.File]::WriteAllText($preuploadPath,($preupload|ConvertTo-Json -Depth 40),$utf8);$preuploadSha=Get-FileSha256Hex $preuploadPath;$listing=@('MERCH FORGE — MANUAL UPLOAD PACKAGE',"Status: $status",'',"Concept revision: $($identity.id)","Revision SHA256: $($identity.hash)","Acceptance fingerprint: $($acc.lineage_fingerprint)","Listing SHA256: $listingHash",'',"Listing title: $($lc.publication.listing_title)","Brand: $($lc.publication.brand)","Bullet 1: $($lc.publication.bullet_1)","Bullet 2: $($lc.publication.bullet_2)","Description: $($lc.publication.description)","Keywords: $(@($lc.publication.keywords)-join ', ')","Locale: $($lc.publication.locale)",'',"Artwork SHA256: $sha",'','Boundary: local package only. Nothing was uploaded or submitted by Merch Forge.') -join "`r`n";[IO.File]::WriteAllText((Join-Path $stage 'LISTING.txt'),$listing,$utf8)
        $manifest=@();foreach($f in @(Get-ChildItem -LiteralPath $stage -File|Sort-Object Name)){$manifest+=[ordered]@{file=$f.Name;size_bytes=$f.Length;sha256=(Get-FileSha256Hex $f.FullName)}};[IO.File]::WriteAllText((Join-Path $stage 'manifest.json'),([ordered]@{hash_algorithm='SHA-256';lineage_fingerprint=[string]$acc.lineage_fingerprint;files=$manifest}|ConvertTo-Json -Depth 10),$utf8)
        Add-Type -AssemblyName System.IO.Compression.FileSystem;$zipName=($safe+'-'+$status+'-'+$stamp+'.zip');$zip=Join-Path $script:LocalCorePackageRoot $zipName;if(Test-Path -LiteralPath $zip){Remove-Item -LiteralPath $zip -Force};[IO.Compression.ZipFile]::CreateFromDirectory($stage,$zip,[IO.Compression.CompressionLevel]::Optimal,$false);Remove-Item -LiteralPath $stage -Recurse -Force;$pkgSha=Get-FileSha256Hex $zip
        $receiptProfile=Get-PropertyValue $printProduction 'channel_profile';$receiptMarketplace=if($null-ne$receiptProfile){([string](Get-PropertyValue $receiptProfile 'marketplace')).Trim()}else{''};$receiptProductType=if($null-ne$receiptProfile){([string](Get-PropertyValue $receiptProfile 'product_type_key')).Trim()}else{''};$receiptTemplateKey=if($null-ne$receiptProfile){([string](Get-PropertyValue $receiptProfile 'template_key')).Trim()}else{''};$receiptTemplatePath=$zip+'.publication-receipt.json';$receiptTemplate=[ordered]@{schema='forge.local_publication_receipt.v3';concept_key=[string]$lc.concept_key;package_sha256=$pkgSha;lineage_fingerprint=[string]$acc.lineage_fingerprint;listing_hash=$listingHash;preupload_gate_sha256=$preuploadSha;print_production_sha256=$printSha;channel='amazon_merch';marketplace=$receiptMarketplace;product_type_key=$receiptProductType;template_key=$receiptTemplateKey;product_id='';published_at='';source='owner_manual_upload_receipt';note='Fill product_id and published_at after manual publication, then import this receipt into Forge.'};[IO.File]::WriteAllText($receiptTemplatePath,($receiptTemplate|ConvertTo-Json -Depth 10),$utf8)
        $pkg=[pscustomobject]@{path=$zip;sha256=$pkgSha;status=$status;valid=$true;concept_revision_id=$identity.id;revision_hash=$identity.hash;acceptance_fingerprint=[string]$acc.lineage_fingerprint;artwork_sha256=$sha;listing_hash=$listingHash;preupload_gate_sha256=$preuploadSha;print_production_sha256=$printSha;marketplace=$receiptMarketplace;product_type_key=$receiptProductType;template_key=$receiptTemplateKey;channel_profile_captured_at=if($null-ne$receiptProfile){[string](Get-PropertyValue $receiptProfile 'captured_at')}else{''};channel_profile_valid_until=if($null-ne$receiptProfile){[string](Get-PropertyValue $receiptProfile 'valid_until')}else{''};created_at=[DateTime]::UtcNow.ToString('o');manual_upload_required=$true;external_submission_authorized=$false;publication_receipt_template=$receiptTemplatePath};$lc.packages=@($lc.packages)+@($pkg);Write-LocalCoreState $s
        $DeliveryStatus.Text=("Local package created: {0}`nStatus: {1}`nSHA-256: {2}`nPublication receipt template: {3}" -f $zip,$status,$pkgSha,$receiptTemplatePath);$PublicationPreflight.Text=Get-LocalPackageReadinessText $lc;$StatusText.Text=('Local manual-upload package created. Status: '+$status)
    } catch {Show-Error $_.Exception.Message;$StatusText.Text='Local package creation failed.'}
}
function Get-LocalPackageZipEntrySha256([string]$ZipPath,[string]$EntryName) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $entry=$null;foreach($e in @($zip.Entries)){if([string]$e.FullName -eq $EntryName){$entry=$e;break}}
        if($null -eq $entry){return ''}
        $stream=$entry.Open();try{$ms=New-Object IO.MemoryStream;$stream.CopyTo($ms);return Get-ByteSha256Hex $ms.ToArray()}finally{$stream.Dispose();if($null-ne$ms){$ms.Dispose()}}
    } finally {$zip.Dispose()}
}
function Get-LocalPackageZipJsonEntry([string]$ZipPath,[string]$EntryName) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $entry=$null;foreach($e in @($zip.Entries)){if([string]$e.FullName -eq $EntryName){$entry=$e;break}}
        if($null -eq $entry){return $null}
        $stream=$entry.Open();try{$ms=New-Object IO.MemoryStream;$stream.CopyTo($ms);$raw=[Text.Encoding]::UTF8.GetString($ms.ToArray());if([string]::IsNullOrWhiteSpace($raw)){return $null};try{return ($raw|ConvertFrom-Json)}catch{return $null}}finally{$stream.Dispose();if($null-ne$ms){$ms.Dispose()}}
    } finally {$zip.Dispose()}
}
function Get-LocalReadyPackageZipAuthority([string]$ZipPath,$Package,[string]$ConceptKey) {
    try {
        if([string]::IsNullOrWhiteSpace($ZipPath) -or -not(Test-Path -LiteralPath $ZipPath -PathType Leaf) -or $null-eq$Package){return $null}
        $expectedGateSha=([string](Get-PropertyValue $Package 'preupload_gate_sha256')).Trim().ToLowerInvariant();$expectedPrintSha=([string](Get-PropertyValue $Package 'print_production_sha256')).Trim().ToLowerInvariant();if($expectedGateSha -notmatch '^[0-9a-f]{64}$' -or $expectedPrintSha -notmatch '^[0-9a-f]{64}$'){return $null}
        $actualGateSha=Get-LocalPackageZipEntrySha256 $ZipPath 'preupload-gate.json';$actualPrintSha=Get-LocalPackageZipEntrySha256 $ZipPath 'print-production.json';if($actualGateSha -ne $expectedGateSha -or $actualPrintSha -ne $expectedPrintSha){return $null}
        $gate=Get-LocalPackageZipJsonEntry $ZipPath 'preupload-gate.json';if($null-eq$gate -or [string](Get-PropertyValue $gate 'schema') -ne 'forge.preupload_gate.v1' -or [string](Get-PropertyValue $gate 'status') -ne 'READY_FOR_MANUAL_UPLOAD' -or [bool](Get-PropertyValue $gate 'all_checks_ready') -ne $true -or [bool](Get-PropertyValue $gate 'print_production_ready') -ne $true -or [bool](Get-PropertyValue $gate 'external_submission_authorized') -ne $false){return $null}
        if(([string](Get-PropertyValue $gate 'concept_key')).Trim() -ne ([string]$ConceptKey).Trim()){return $null};$lineage=Get-PropertyValue $gate 'lineage';if($null-eq$lineage){return $null}
        $pairs=@(@('concept_revision_id','concept_revision_id'),@('revision_hash','revision_hash'),@('acceptance_fingerprint','acceptance_fingerprint'),@('accepted_artwork_sha256','artwork_sha256'),@('listing_hash','listing_hash'));foreach($pair in $pairs){$left=([string](Get-PropertyValue $lineage $pair[0])).Trim().ToLowerInvariant();$right=([string](Get-PropertyValue $Package $pair[1])).Trim().ToLowerInvariant();if([string]::IsNullOrWhiteSpace($left) -or [string]::IsNullOrWhiteSpace($right) -or $left-ne$right){return $null}}
        $gatePrint=([string](Get-PropertyValue $gate 'print_production_sha256')).Trim().ToLowerInvariant();if($gatePrint -ne $expectedPrintSha){return $null};$gateCreatedRaw=([string](Get-PropertyValue $gate 'created_at')).Trim();try{$gateCreated=[DateTime]::Parse($gateCreatedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $null};if($gateCreated -gt [DateTime]::UtcNow.AddMinutes(10)){return $null}
        $print=Get-LocalPackageZipJsonEntry $ZipPath 'print-production.json';if($null-eq$print -or [string](Get-PropertyValue $print 'schema') -ne 'forge.print_production_snapshot.v1' -or [bool](Get-PropertyValue $print 'ready') -ne $true){return $null};$profile=Get-PropertyValue $print 'channel_profile';if($null-eq$profile -or [string](Get-PropertyValue $profile 'schema') -ne 'forge.amazon_print_profile.v1' -or [bool](Get-PropertyValue $profile 'attested') -ne $true -or [string](Get-PropertyValue $profile 'authority_kind') -ne 'owner_attested_external'){return $null};$marketplace=([string](Get-PropertyValue $profile 'marketplace')).Trim();$productType=([string](Get-PropertyValue $profile 'product_type_key')).Trim();$templateKey=([string](Get-PropertyValue $profile 'template_key')).Trim();if([string]::IsNullOrWhiteSpace($marketplace) -or [string]::IsNullOrWhiteSpace($productType) -or [string]::IsNullOrWhiteSpace($templateKey)){return $null}
        $profileCapturedRaw=([string](Get-PropertyValue $profile 'captured_at')).Trim();$profileValidRaw=([string](Get-PropertyValue $profile 'valid_until')).Trim();try{$profileCaptured=[DateTime]::Parse($profileCapturedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime();$profileValidUntil=[DateTime]::Parse($profileValidRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{return $null};if($profileCaptured -gt [DateTime]::UtcNow.AddMinutes(10) -or $profileValidUntil -le $profileCaptured -or ($profileValidUntil-$profileCaptured).TotalDays -gt 120){return $null};if($gateCreated -lt $profileCaptured.AddMinutes(-10) -or $gateCreated -gt $profileValidUntil){return $null}
        return [pscustomobject]@{gate=$gate;gate_sha256=$actualGateSha;print_production_sha256=$actualPrintSha;created_at=$gateCreated;marketplace=$marketplace;product_type_key=$productType;template_key=$templateKey;profile_captured_at=$profileCaptured;profile_valid_until=$profileValidUntil}
    } catch {return $null}
}
function Get-LocalPublicationProductKey($Receipt) {
    try {
        if($null -eq $Receipt){return ''};$channel=([string](Get-PropertyValue $Receipt 'channel')).Trim().ToLowerInvariant();$marketplace=([string](Get-PropertyValue $Receipt 'marketplace')).Trim().ToLowerInvariant();$productId=([string](Get-PropertyValue $Receipt 'product_id')).Trim().ToLowerInvariant();if([string]::IsNullOrWhiteSpace($channel) -or [string]::IsNullOrWhiteSpace($productId)){return ''};if([string]::IsNullOrWhiteSpace($marketplace)){return ($channel+'|'+$productId).ToLowerInvariant()};return ($channel+'|'+$marketplace+'|'+$productId).ToLowerInvariant()
    } catch {return ''}
}
function Test-LocalPublicationReceiptAuthority($State,$Receipt) {
    try {
        if($null -eq $State -or $null -eq $Receipt -or [bool](Get-PropertyValue $Receipt 'lineage_verified') -ne $true){return $false}
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
        $r=Get-Content -LiteralPath $Path -Raw -Encoding UTF8|ConvertFrom-Json;if([string](Get-PropertyValue $r 'schema') -ne 'forge.local_publication_receipt.v3'){throw 'Hardened build requires a v3 publication receipt bound to the exact pre-upload gate.'}
        $conceptKey=([string](Get-PropertyValue $r 'concept_key')).Trim();if([string]::IsNullOrWhiteSpace($conceptKey)){throw 'Publication receipt concept_key is required.'};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept $conceptKey $s;if($null -eq $lc){throw 'Publication receipt concept is not present in local Forge state.'}
        $packageSha=([string](Get-PropertyValue $r 'package_sha256')).Trim().ToLowerInvariant();if($packageSha -notmatch '^[0-9a-f]{64}$'){throw 'Publication receipt package_sha256 is invalid.'};$packageMatch=$null;foreach($pkg in @($lc.packages)){if(([string](Get-PropertyValue $pkg 'sha256')).ToLowerInvariant() -eq $packageSha){$packageMatch=$pkg;break}};if($null -eq $packageMatch){throw 'Publication receipt does not match a package built by this local Forge state.'}
        if([bool](Get-PropertyValue $packageMatch 'valid') -ne $true -or [string](Get-PropertyValue $packageMatch 'status') -ne 'READY_FOR_MANUAL_UPLOAD'){throw 'Only a currently valid READY_FOR_MANUAL_UPLOAD package may be recorded as published.'}
        $path=[string](Get-PropertyValue $packageMatch 'path');if(-not(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileSha256Hex $path) -ne $packageSha){throw 'Published package bytes are missing or no longer match their SHA-256.'};$zipAuthority=Get-LocalReadyPackageZipAuthority $path $packageMatch $conceptKey;if($null-eq$zipAuthority){throw 'Exact package ZIP does not contain an authority-valid READY preupload gate matching the local package lineage.'};$zipGateSha=[string](Get-PropertyValue $zipAuthority 'gate_sha256');$zipPrintSha=[string](Get-PropertyValue $zipAuthority 'print_production_sha256')
        $fp=([string](Get-PropertyValue $r 'lineage_fingerprint')).Trim().ToLowerInvariant();$lh=([string](Get-PropertyValue $r 'listing_hash')).Trim().ToLowerInvariant();$gateSha=([string](Get-PropertyValue $r 'preupload_gate_sha256')).Trim().ToLowerInvariant();$printSha=([string](Get-PropertyValue $r 'print_production_sha256')).Trim().ToLowerInvariant();if($printSha -notmatch '^[0-9a-f]{64}$' -or $printSha -ne [string](Get-PropertyValue $packageMatch 'print_production_sha256')){throw 'Publication receipt print_production_sha256 does not match the exact READY package.'};if($fp -ne [string](Get-PropertyValue $packageMatch 'acceptance_fingerprint') -or $lh -ne [string](Get-PropertyValue $packageMatch 'listing_hash')){throw 'Publication receipt lineage does not match the exact Forge package.'};if($gateSha -notmatch '^[0-9a-f]{64}$' -or $gateSha -ne [string](Get-PropertyValue $packageMatch 'preupload_gate_sha256')){throw 'Publication receipt preupload_gate_sha256 does not match the exact READY package gate.'}
        $channel=([string](Get-PropertyValue $r 'channel')).Trim().ToLowerInvariant();$marketplace=([string](Get-PropertyValue $r 'marketplace')).Trim();$productId=([string](Get-PropertyValue $r 'product_id')).Trim();if($channel -ne 'amazon_merch' -or [string]::IsNullOrWhiteSpace($marketplace) -or [string]::IsNullOrWhiteSpace($productId)){throw 'Publication receipt must identify the amazon_merch channel, exact package marketplace, and product_id.'};if($marketplace -ne [string](Get-PropertyValue $zipAuthority 'marketplace')){throw 'Publication receipt marketplace does not match the exact Amazon print profile embedded in the READY package.'};$publishedRaw=([string](Get-PropertyValue $r 'published_at')).Trim();$published=$null;try{$published=[DateTime]::Parse($publishedRaw,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()}catch{throw 'Publication receipt published_at must be a valid date/time.'};if($published -gt [DateTime]::UtcNow.AddMinutes(10)){throw 'Publication receipt published_at cannot be in the future.'};$packageCreated=[DateTime](Get-PropertyValue $zipAuthority 'created_at');if($published -lt $packageCreated.AddMinutes(-10)){throw 'Publication receipt published_at predates creation of the exact Forge package.'};$profileValidUntil=[DateTime](Get-PropertyValue $zipAuthority 'profile_valid_until');if($published -gt $profileValidUntil){throw 'Publication receipt published_at is after the Amazon print profile valid_until used to build this package. Re-attest the current template and build a fresh READY package before publication.'}
        $fileSha=Get-FileSha256Hex $Path;foreach($existing in @($s.publication_receipts)){if((Test-LocalPublicationReceiptAuthority $s $existing) -and [string](Get-PropertyValue $existing 'source_file_sha256') -eq $fileSha){$StatusText.Text='This publication receipt was already imported.';Update-LocalCoreBusinessSurfaces;return}};$binding=Get-LocalPublicationReceiptBindingDecision $s $conceptKey $packageSha $fp $lh $gateSha $printSha $channel $marketplace $productId;if([string](Get-PropertyValue $binding 'status') -eq 'same'){$StatusText.Text='This exact published product/package binding is already recorded locally.';Update-LocalCoreBusinessSurfaces;return};if([string](Get-PropertyValue $binding 'status') -eq 'conflict'){throw 'This channel/product_id is already bound to a different verified Forge package. The conflicting receipt was not imported.'}
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
function ConvertFrom-ForgeMoney($Raw) {
    # "$1,234.56", "1.234,56 €", "1,50", "(0.35)" -> number. $null when the text is not a number.
    $s=([string]$Raw).Trim(); if(-not $s){return 0.0}
    $neg=($s -match '^\(.*\)$' -or $s -match '^[^0-9]*-'); $s=($s -replace '[^0-9.,]','')
    if(-not $s){return $null}
    $lc=$s.LastIndexOf(','); $ld=$s.LastIndexOf('.')
    if($lc -ge 0 -and $ld -ge 0){ if($lc -gt $ld){ $s=$s.Replace('.','').Replace(',','.') } else { $s=$s.Replace(',','') } }
    elseif($lc -ge 0){ $tail=$s.Length-$lc-1; if($s.Split(',').Count -eq 2 -and $tail -ge 1 -and $tail -le 2){ $s=$s.Replace(',','.') } else { $s=$s.Replace(',','') } }
    elseif($ld -ge 0 -and $s.Split('.').Count -gt 2){ $s=$s.Replace('.','') }
    $v=0.0; if(-not [double]::TryParse($s,[Globalization.NumberStyles]::AllowDecimalPoint,[Globalization.CultureInfo]::InvariantCulture,[ref]$v)){return $null}
    if($neg){$v=-$v}; return $v
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
function Import-LocalSalesCsvFromPath([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){Show-Error 'File not found.';return}
    try {
        $first=''; try{$first=[string](Get-Content -LiteralPath $Path -TotalCount 1 -Encoding UTF8)}catch{}
        $delim=if(($first.Split(';').Count) -gt ($first.Split(',').Count)){';'}else{','}
        $rows=@(Import-Csv -LiteralPath $Path -Delimiter $delim); if($rows.Count -eq 0){throw 'CSV contains no data rows.'}
        $names=@($rows[0].PSObject.Properties | ForEach-Object { [string]$_.Name })
        $cDate=Find-CsvColumn $names @('date','purchase date','order date','sale date','transaction date','shipment date','period','period start','day')
        $cUnits=Find-CsvColumn $names @('units','units sold','net units','quantity','qty','items sold','purchased','sold','units*')
        $cRoy=Find-CsvColumn $names @('royalty','royalties','net earnings','earnings','amount','royalt*','earning*')
        $cRev=Find-CsvColumn $names @('revenue','sales revenue','gross sales','gross','revenue*')
        $cTitle=Find-CsvColumn $names @('title','product title','design title','name')
        $cId=Find-CsvColumn $names @('asin','product asin','product id','listing id','sku','asin*')
        if($null -eq $cUnits -and $null -eq $cRoy){ throw ('This sales CSV has no units or royalty column. Columns found: {0}.' -f ($names -join ', ')) }
        $order=Get-CsvSlashDateOrder @($rows | ForEach-Object { if($cDate){ [string]$_.$cDate } }) $delim
        $normalized=@(); $badAmount=0
        foreach($row in $rows){
            $dateRaw=if($cDate){$row.$cDate}else{$null}; $unitsRaw=if($cUnits){$row.$cUnits}else{$null}; $royRaw=if($cRoy){$row.$cRoy}else{$null}; $revRaw=if($cRev){$row.$cRev}else{$null}; $title=if($cTitle){$row.$cTitle}else{''}; $id=if($cId){$row.$cId}else{''}
            $d=ConvertFrom-ForgeSalesDate $dateRaw $order
            [double]$units=0; [double]$roy=0; [double]$rev=0
            $uV=ConvertFrom-ForgeMoney $unitsRaw; if($null -ne $uV){$units=[double]$uV}else{$badAmount++}
            $royV=ConvertFrom-ForgeMoney $royRaw; if($null -ne $royV){$roy=[double]$royV}else{$badAmount++}
            $revV=ConvertFrom-ForgeMoney $revRaw; if($null -ne $revV){$rev=[double]$revV}
            $normalized+=[pscustomobject]@{date=if($null-ne$d){$d.ToString('yyyy-MM-dd')}else{''};units=$units;royalty=$roy;revenue=$rev;title=[string]$title;product_id=([string]$id).Trim();source_file=[IO.Path]::GetFileName($Path);linked=$false;linked_product_key=''}
        }
        $s=Read-LocalCoreState; $fileSha=Get-FileSha256Hex $Path; $existing=$false
        foreach($imp in @($s.sales_imports)){ if([string]$imp.sha256 -eq $fileSha){$existing=$true;break} }
        if(-not $existing){ $s.sales_rows=@($s.sales_rows)+@($normalized); $s.sales_imports=@($s.sales_imports)+@([pscustomobject]@{file=[IO.Path]::GetFileName($Path);sha256=$fileSha;rows=$rows.Count;imported_at=[DateTime]::UtcNow.ToString('o')}); Reconcile-LocalSalesLinks $s; Write-LocalCoreState $s }
        Update-LocalCoreBusinessSurfaces
        $linked=@($normalized | Where-Object { [bool]$_.linked }).Count; $unlinked=$normalized.Count-$linked
        $noId=@($normalized | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.product_id) }).Count; $noDate=@($normalized | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.date) }).Count
        if($existing){ $StatusText.Text='This sales CSV was already imported; no duplicate rows were added.' }
        elseif(($noId+$noDate+$badAmount) -gt 0){ $StatusText.Text=("Imported {0} row(s): {1} linked to verified Forge products, {2} unlinked. Not readable: {3} without a product ID (ASIN), {4} without a date, {5} unreadable amount(s)." -f $rows.Count,$linked,$unlinked,$noId,$noDate,$badAmount) }
        else { $StatusText.Text=("Imported {0} row(s): {1} linked to verified Forge products, {2} unlinked." -f $rows.Count,$linked,$unlinked) }
    } catch {Show-Error $_.Exception.Message;$StatusText.Text='Sales CSV import failed.'}
}
function Get-LocalSalesMetrics {
    $s=Read-LocalCoreState;Reconcile-LocalSalesLinks $s;$rows=@($s.sales_rows);$now=[DateTime]::UtcNow.Date;$m=[ordered]@{sales7=0.0;sales30=0.0;sales90=0.0;royalties7=0.0;royalties30=0.0;royalties90=0.0;rows=$rows.Count;linked_rows=0;unlinked_rows=0;undated_rows=0;future_rows=0}
    foreach($r in $rows){if(-not [bool](Get-PropertyValue $r 'linked')){$m.unlinked_rows++;continue};$m.linked_rows++;$d=$null;try{$d=[DateTime]::ParseExact([string]$r.date,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}catch{};$units=[double](Get-PropertyValue $r 'units');$roy=[double](Get-PropertyValue $r 'royalty');if($null-eq$d){$m.undated_rows++;continue};$age=($now-$d.Date).TotalDays;if($age -lt 0){$m.future_rows++;continue};if($age -le 90){$m.sales90+=$units;$m.royalties90+=$roy};if($age -le 30){$m.sales30+=$units;$m.royalties30+=$roy};if($age -le 7){$m.sales7+=$units;$m.royalties7+=$roy}}
    return [pscustomobject]$m
}
function Update-LocalCoreBusinessSurfaces {
    if($null -eq $HomeMetricSalesValue){return};$m=Get-LocalSalesMetrics;$s=Read-LocalCoreState;$packages=0;$accepted=0;foreach($c in @($s.concepts)){$packages+=@((Get-PropertyValue $c 'packages')|Where-Object{[bool](Get-PropertyValue $_ 'valid')}).Count;if($null-ne(Get-PropertyValue $c 'active_acceptance')){$accepted++}}
    $receipts=@($s.publication_receipts|Where-Object{Test-LocalPublicationReceiptAuthority $s $_});$productKeys=@{};$channelKeys=@{};foreach($receipt in $receipts){$pk=Get-LocalPublicationProductKey $receipt;$ch=([string](Get-PropertyValue $receipt 'channel')).Trim().ToLowerInvariant();if(-not[string]::IsNullOrWhiteSpace($pk)){$productKeys[$pk]=$true};if(-not[string]::IsNullOrWhiteSpace($ch)){$channelKeys[$ch]=$true}};$publishedCount=$productKeys.Count;$channelCount=$channelKeys.Count;$hasLinked=($m.linked_rows -gt 0)
    $HomeMetricSalesValue.Text=if($hasLinked){[string][int]$m.sales30}else{'—'};$HomeMetricRoyaltiesValue.Text=if($hasLinked){('$'+[string]::Format([Globalization.CultureInfo]::InvariantCulture,'{0:0.00}',$m.royalties30))}else{'—'};$HomeMetricPublishedValue.Text=if($publishedCount-gt0){[string]$publishedCount}else{'—'}
    if($null-ne$PortfolioProductsValue){$PortfolioProductsValue.Text=if($publishedCount-gt0){[string]$publishedCount}else{'—'}};if($null-ne$PortfolioChannelsValue){$PortfolioChannelsValue.Text=if($channelCount-gt0){[string]$channelCount}else{'—'}};if($null-ne$PortfolioHealthValue){$PortfolioHealthValue.Text='—'}
    if($null-ne$PerfSales7Value){$PerfSales7Value.Text=if($hasLinked){[string][int]$m.sales7}else{'—'}};if($null-ne$PerfSales30Value){$PerfSales30Value.Text=if($hasLinked){[string][int]$m.sales30}else{'—'}};if($null-ne$PerfRoyalties30Value){$PerfRoyalties30Value.Text=if($hasLinked){('$'+[string]::Format([Globalization.CultureInfo]::InvariantCulture,'{0:0.00}',$m.royalties30))}else{'—'}};if($null-ne$PerfSales90Value){$PerfSales90Value.Text=if($hasLinked){[string][int]$m.sales90}else{'—'}}
    if($null-ne$HomePerformanceBody){$HomePerformanceBody.Text=if($hasLinked){((Get-UiText 'biz.home.linked' 'Verified linked import · 7d: {0} sale(s), ${1:0.00} · 30d: {2}, ${3:0.00} · 90d: {4}, ${5:0.00}') -f [int]$m.sales7,$m.royalties7,[int]$m.sales30,$m.royalties30,[int]$m.sales90,$m.royalties90)}elseif($m.rows){((Get-UiText 'biz.home.unlinked' 'Imported data is not linked to a verified Forge publication receipt; {0} row(s) excluded.') -f $m.unlinked_rows)}else{Get-UiText 'biz.home.none' 'Import a sales/royalty CSV to populate local performance.'}}
    if($null-ne$PortfolioEmpty){$PortfolioEmpty.Text=((Get-UiText 'biz.portfolio.local' 'Local core: {0} accepted design(s), {1} valid package(s), {2} verified published product(s). Live listing health is not fabricated.') -f $accepted,$packages,$publishedCount)};if($null-ne$LocalPublicationStatusText){$LocalPublicationStatusText.Text=if($publishedCount-gt0){((Get-UiText 'biz.receipts.some' 'Verified published products: {0} · channels: {1}') -f $publishedCount,$channelCount)}else{Get-UiText 'biz.receipts.none' 'No verified local publication receipt imported.'}}
    if($null-ne$PerformanceEmpty){$PerformanceEmpty.Text=if($hasLinked){((Get-UiText 'biz.perf.linked' 'Verified linked sales rows: {0}. 30-day units: {1}; royalties: ${2:0.00}.') -f $m.linked_rows,[int]$m.sales30,$m.royalties30)}elseif($m.rows){((Get-UiText 'biz.perf.unlinked' 'No imported sales rows match a verified Forge product ID. Unlinked rows: {0}.') -f $m.unlinked_rows)}else{Get-UiText 'biz.perf.none' 'No local sales CSV imported yet.'}};if($null-ne$LocalSalesStatusText){$LocalSalesStatusText.Text=if($m.rows){((Get-UiText 'biz.sales.some' 'Imported: {0} · linked: {1} · unlinked: {2} · undated linked: {3} · future linked: {4}') -f $m.rows,$m.linked_rows,$m.unlinked_rows,$m.undated_rows,$m.future_rows)}else{Get-UiText 'biz.sales.none' 'No local sales data imported.'}}
    try{Update-PerformanceInsightsSurface}catch{Write-AppLog 'WARN' ('Performance insights refresh failed: '+$_.Exception.Message)}
    try{if(Get-Command Update-AmazonProfileSurface -ErrorAction SilentlyContinue){Update-AmazonProfileSurface}}catch{Write-AppLog 'WARN' ('Amazon profile status refresh failed: '+$_.Exception.Message)}
    try{if(Get-Command Update-DataCopySurface -ErrorAction SilentlyContinue){Update-DataCopySurface}}catch{}
    try{if(Get-Command Update-WhatsNewCard -ErrorAction SilentlyContinue){Update-WhatsNewCard}}catch{}
}
function Update-LocalCoreStatusUi {
    if($null -eq $script:Current){return};$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key);if($null -eq $lc){return};$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=Get-PropertyValue $lc 'active_acceptance';$accepted=($null-ne$acc -and [string](Get-PropertyValue $acc 'concept_revision_id') -eq $identity.id -and [string](Get-PropertyValue $acc 'revision_hash') -eq $identity.hash)
    $v=@(Get-LocalCoreVariantsForCurrent).Count;$validPackages=@($lc.packages|Where-Object{[bool](Get-PropertyValue $_ 'valid')}).Count;$text=((Get-UiText 'lc.status' 'Artwork: {0} · accepted: {1} · ready packages: {2}') -f $v,$(if($accepted){Get-UiText 'lc.yes' 'yes'}else{Get-UiText 'lc.no' 'no'}),$validPackages)
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
