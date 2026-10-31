# Rejected proposals are inert, bounded local records; never active drafts or approvals.
$script:RejectedAIEditDirty=$false
$script:RejectedAIViewId=''
$script:RejectedAIEditSha=''
$script:RejectedAIUiLoading=$false
function Get-ForgeRejectedRoot { return (Join-Path $script:StateRoot 'rejected-ai-v1') }
function Assert-ForgeRejectedPath([string]$Path) {
 $state=[IO.Path]::GetFullPath($script:StateRoot).TrimEnd('\','/');$full=[IO.Path]::GetFullPath($Path)
 if(!$full.StartsWith($state+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'REJECTED_PATH: outside owned state'}
 $cursor=$full
 while($cursor.Length-ge$state.Length){
  if(Test-Path -LiteralPath $cursor){$item=Get-Item -LiteralPath $cursor -Force;if($item.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'REJECTED_PATH: redirected state is forbidden'}}
  if($cursor-ieq$state){break};$cursor=[IO.Path]::GetDirectoryName($cursor)
 }
 return $full
}
function Get-ForgeRejectedDirectory([string]$Id) {
 if($Id-cnotmatch'^rej-[0-9a-f]{32}$'){throw 'REJECTED_ID: invalid record id'}
 return (Assert-ForgeRejectedPath (Join-Path (Get-ForgeRejectedRoot) $Id))
}
function Read-ForgeRejectedBytes([string]$Path,[int]$Limit) {
 $path=Assert-ForgeRejectedPath $Path;$item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
 if($item-isnot[IO.FileInfo]-or$item.Length-lt1-or$item.Length-gt$Limit){throw 'REJECTED_SIZE: missing or oversized file'}
 $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
 try{if($stream.Length-lt1-or$stream.Length-gt$Limit){throw 'REJECTED_SIZE: file changed'};$b=New-Object byte[] ([int]$stream.Length);$n=0;while($n-lt$b.Length){$k=$stream.Read($b,$n,$b.Length-$n);if(!$k){throw 'REJECTED_READ: incomplete file'};$n+=$k};return ,$b}finally{$stream.Dispose()}
}
function Read-ForgeRejectedJson([string]$Path,[int]$Limit=65536) {
 $b=Read-ForgeRejectedBytes $Path $Limit
 return (ConvertFrom-ForgeJsonObjectStrict ([Text.UTF8Encoding]::new($false,$true).GetString($b).TrimStart([char]0xFEFF)))
}
function Write-ForgeRejectedBytes([string]$Path,[byte[]]$Bytes) {
 $path=Assert-ForgeRejectedPath $Path
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($Bytes,0,$Bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function Get-ForgeRejectedJsonBytes($Value) { return ,([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 60 -Compress))) }
function Assert-ForgeRejectedQuota {
 $root=Assert-ForgeRejectedPath (Get-ForgeRejectedRoot);$count=0;$bytes=0L
 if(!(Test-Path -LiteralPath $root)){return}
 foreach($dir in [IO.Directory]::EnumerateDirectories($root)){
  $null=Assert-ForgeRejectedPath $dir;$count++;if($count-gt40){throw 'REJECTED_QUOTA: forty records/stages maximum; retain originals and remove an unwanted record explicitly'}
  foreach($file in [IO.Directory]::EnumerateFiles($dir)){$null=Assert-ForgeRejectedPath $file;$bytes+=(Get-Item -LiteralPath $file).Length;if($bytes-gt8MB){throw 'REJECTED_QUOTA: local record storage exceeds 8 MiB'}}
 }
}
function Enter-ForgeRejectedWriteLock {
 $root=Assert-ForgeRejectedPath (Get-ForgeRejectedRoot);[void][IO.Directory]::CreateDirectory($root)
 return [IO.File]::Open((Join-Path $root 'write.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
}
function Get-ForgeRejectedBaseBinding($Request) {
 $key=[string](Get-PropertyValue $Request 'Key');$revision=[string](Get-PropertyValue $Request 'Revision');$hash=[string](Get-PropertyValue $Request 'RevisionHash')
 if($key){
  $d=Get-ResearchDraft $key;if($null-eq$d){throw 'REJECTED_BASE: parent draft missing'}
  $matches=@($d.revisions|Where-Object{$_.revision_id-ceq$revision});if($matches.Count-ne1){throw 'REJECTED_BASE: parent revision missing'}
  if($hash-and$hash-cne$matches[0].revision_hash){throw 'REJECTED_BASE: request revision hash changed'};$hash=[string]$matches[0].revision_hash
 }elseif($revision-or$hash){throw 'REJECTED_BASE: revision without parent'}
 $ctx=Get-PropertyValue $Request 'EvidenceContext';$sha=[string](Get-PropertyValue (Get-PropertyValue $ctx 'packet') 'source_sha256')
 if($sha-and$sha-cnotmatch'^[0-9a-f]{64}$'){throw 'REJECTED_SOURCE: invalid source identity'}
 return [ordered]@{concept_key=$key;revision_id=$revision;revision_hash=$hash;source_sha256=$sha;selected_records_sha256=$(if($null-ne$ctx){Get-ForgeBriefSha256 $ctx.selected_records}else{''})}
}
function Save-ForgeRejectedResponse($Request,[string]$OriginalResponse,[byte[]]$OriginalBytes=$null,[string]$RejectionReason='Rejected by normal AI validation') {
 if($null-eq$OriginalBytes){$OriginalBytes=[Text.Encoding]::UTF8.GetBytes($OriginalResponse)}
 if(!$OriginalBytes.Length){return $null};if($OriginalBytes.Length-gt65536){throw 'REJECTED_SIZE: response exceeds 64 KiB'}
 $requestText=$Request.Content.ReadAsStringAsync().GetAwaiter().GetResult();$requestBytes=[Text.Encoding]::UTF8.GetBytes($requestText)
 if($requestBytes.Length-gt65536){throw 'REJECTED_SIZE: request exceeds 64 KiB'}
 $body=ConvertFrom-ForgeJsonObjectStrict $requestText
 foreach($p in $body.PSObject.Properties){if($p.Name-cnotin@('model','stream','think','keep_alive','format','messages','options')){throw 'REJECTED_REQUEST: unexpected body field; headers/credentials are never retained'}}
 if($body.model-cne'qwen3.5:9b'-or(Get-ForgeBriefSha256 $body.format)-cne(Get-ForgeBriefSha256 $Request.ResponseSchema)){throw 'REJECTED_REQUEST: model/schema mismatch'}
 foreach($p in $body.options.PSObject.Properties){if($p.Name-cnotin@('num_ctx','num_predict','temperature','seed','num_thread','num_gpu','top_k','top_p','min_p','repeat_penalty','presence_penalty','frequency_penalty','stop')){throw 'REJECTED_REQUEST: unexpected sampling/credential field'}}
 foreach($message in @($body.messages)){foreach($p in $message.PSObject.Properties){if($p.Name-cnotin@('role','content')){throw 'REJECTED_REQUEST: unexpected message field'}}}
 $binding=Get-ForgeRejectedBaseBinding $Request;$id='rej-'+[guid]::NewGuid().ToString('N');$dir=Get-ForgeRejectedDirectory $id
 $inner='';try{$outer=ConvertFrom-ForgeJsonObjectStrict $OriginalResponse;if($outer.message.content-is[string]){$inner=$outer.message.content}}catch{}
 $originalInnerSha=if($inner){Get-StringSha256Hex $inner}else{''}
 $oversizeInner=($inner.Length-gt24000);if($oversizeInner){$inner=''} # Raw is intact; oversize parsed editing is explicitly unavailable.
 $flag=Get-PropertyValue (Get-PropertyValue $Request 'EvidenceContext') 'require_all_references';if($null-ne$flag-and$flag-isnot[bool]){throw 'REJECTED_POLICY: malformed reference policy'}
 $policy=if($flag-is[bool]-and!$flag){'explicit_subset'}else{'all_selected'}
 $record=[ordered]@{schema='forge.rejected_ai.v1';id=$id;created_at=[datetime]::UtcNow.ToString('o');binding=$binding;model=$body.model;reference_policy=$policy;rejection_reason=$RejectionReason.Substring(0,[Math]::Min(2000,$RejectionReason.Length));original_content_sha256=$originalInnerSha;original_content_oversize=$oversizeInner;schema_sha256=(Get-ForgeBriefSha256 $body.format);response_sha256=(Get-ByteSha256Hex $OriginalBytes);request_sha256=(Get-ByteSha256Hex $requestBytes);status='rejected_unapproved';approved=$false;semantic_verified=$false}
 $recordBytes=Get-ForgeRejectedJsonBytes $record;if($recordBytes.Length-gt32768){throw 'REJECTED_SIZE: record metadata too large'}
 $edit=[ordered]@{schema='forge.rejected_ai_edit.v1';id=$id;record_sha256=(Get-ByteSha256Hex $recordBytes);content=$inner;content_sha256=(Get-StringSha256Hex $inner);saved_at=[datetime]::UtcNow.ToString('o')}
 $editBytes=Get-ForgeRejectedJsonBytes $edit;if($editBytes.Length-gt131072){throw 'REJECTED_SIZE: working copy too large'}
 $lock=Enter-ForgeRejectedWriteLock
 try{
  Assert-ForgeRejectedQuota
  if(@([IO.Directory]::EnumerateDirectories((Get-ForgeRejectedRoot))).Count-ge40){throw 'REJECTED_QUOTA: no new record slot available'}
  $stage=Assert-ForgeRejectedPath (Join-Path (Get-ForgeRejectedRoot) ('.stage-'+[guid]::NewGuid().ToString('N')));[void][IO.Directory]::CreateDirectory($stage)
  foreach($entry in @(@('response.raw',$OriginalBytes),@('request.json',$requestBytes),@('record.json',$recordBytes),@('edit.json',$editBytes))){Write-ForgeRejectedBytes (Join-Path $stage $entry[0]) $entry[1]}
  $manifest=[ordered]@{schema='forge.rejected_ai_manifest.v1';files=[ordered]@{'response.raw'=$record.response_sha256;'request.json'=$record.request_sha256;'record.json'=(Get-ByteSha256Hex $recordBytes)}}
  Write-ForgeRejectedBytes (Join-Path $stage 'manifest.json') (Get-ForgeRejectedJsonBytes $manifest)
  Assert-ForgeRejectedQuota;$null=Assert-ForgeRejectedPath $dir;$null=Assert-ForgeRejectedPath $stage
  [IO.Directory]::Move($stage,$dir)
  return [pscustomobject]@{id=$id;retained=$true;approved=$false}
 }finally{$lock.Dispose()}
}
function Read-ForgeRejectedProposal([string]$Id) {
 $dir=Get-ForgeRejectedDirectory $Id;$manifest=Read-ForgeRejectedJson (Join-Path $dir 'manifest.json') 4096
 if($manifest.schema-cne'forge.rejected_ai_manifest.v1'-or@($manifest.files.PSObject.Properties).Count-ne3){throw 'REJECTED_CORRUPT: invalid manifest'}
 $bytes=@{}
 foreach($name in @('response.raw','request.json','record.json')){
  $limit=if($name-ceq'record.json'){32768}else{65536};$b=Read-ForgeRejectedBytes (Join-Path $dir $name) $limit
  if([string]$manifest.files.$name-cnotmatch'^[0-9a-f]{64}$'-or(Get-ByteSha256Hex $b)-cne$manifest.files.$name){throw 'REJECTED_CORRUPT: immutable file hash mismatch'};$bytes[$name]=$b
 }
 $utf8=[Text.UTF8Encoding]::new($false,$true);$record=ConvertFrom-ForgeJsonObjectStrict ($utf8.GetString($bytes['record.json']));$request=ConvertFrom-ForgeJsonObjectStrict ($utf8.GetString($bytes['request.json']))
 if($record.schema-cne'forge.rejected_ai.v1'-or$record.id-cne$Id-or$record.approved-isnot[bool]-or$record.approved-or$record.semantic_verified-isnot[bool]-or$record.semantic_verified-or$record.status-cne'rejected_unapproved'){throw 'REJECTED_CORRUPT: record authority/schema invalid'}
 if($record.request_sha256-cne(Get-ByteSha256Hex $bytes['request.json'])-or$record.response_sha256-cne(Get-ByteSha256Hex $bytes['response.raw'])-or$record.schema_sha256-cne(Get-ForgeBriefSha256 $request.format)){throw 'REJECTED_CORRUPT: request/response binding mismatch'}
 $edit=Read-ForgeRejectedJson (Join-Path $dir 'edit.json') 131072
 if($edit.schema-cne'forge.rejected_ai_edit.v1'-or$edit.id-cne$Id-or$edit.record_sha256-cne(Get-ByteSha256Hex $bytes['record.json'])-or$edit.content-isnot[string]-or$edit.content.Length-gt24000-or$edit.content_sha256-cne(Get-StringSha256Hex $edit.content)){throw 'REJECTED_CORRUPT: edited copy invalid'}
 $rawText='';try{$rawText=$utf8.GetString($bytes['response.raw'])}catch{$rawText='Original bytes are not valid UTF-8; retained read-only, no automatic repair.'}
 $originalContent='';try{$outer=ConvertFrom-ForgeJsonObjectStrict $rawText;if($outer.message.content-is[string]){$originalContent=$outer.message.content}}catch{}
 if($record.original_content_sha256-and(Get-StringSha256Hex $originalContent)-cne$record.original_content_sha256){throw 'REJECTED_CORRUPT: original content identity mismatch'}
 return [pscustomobject]@{id=$Id;record=$record;request=$request;raw_bytes=$bytes['response.raw'];raw_text=$rawText;original_content=$originalContent;edit=$edit;record_sha256=(Get-ByteSha256Hex $bytes['record.json'])}
}
function Get-ForgeRejectedProposals {
 $root=Assert-ForgeRejectedPath (Get-ForgeRejectedRoot);if(!(Test-Path -LiteralPath $root)){return @()};Assert-ForgeRejectedQuota
 $out=@();foreach($dir in [IO.Directory]::EnumerateDirectories($root)){
  $id=[IO.Path]::GetFileName($dir);if($id-cnotmatch'^rej-[0-9a-f]{32}$'){continue}
  try{$r=Read-ForgeRejectedProposal $id;$out+=[pscustomobject]@{id=$id;label=($r.record.created_at+' — '+$r.record.binding.concept_key+' — отклонён, не проверен')}}catch{$out+=[pscustomobject]@{id=$id;label=($id+' — повреждён, сохранение заблокировано')}}
 };return @($out)
}
function Write-ForgeRejectedAtomicJson([string]$Path,$Value) {
 $path=Assert-ForgeRejectedPath $Path;$bytes=Get-ForgeRejectedJsonBytes $Value;if($bytes.Length-gt131072){throw 'REJECTED_SIZE: working metadata too large'}
 $tmp=Assert-ForgeRejectedPath (Join-Path ([IO.Path]::GetDirectoryName($path)) ('.work-'+[guid]::NewGuid().ToString('N')+'.tmp'))
 Write-ForgeRejectedBytes $tmp $bytes;Assert-ForgeRejectedQuota;$null=Assert-ForgeRejectedPath $path
 if(Test-Path -LiteralPath $path){[IO.File]::Replace($tmp,$path,[NullString]::Value)}else{[IO.File]::Move($tmp,$path)}
}
function Save-ForgeRejectedEdit([string]$Id,[string]$Content,[string]$ExpectedEditSha) {
 if($Content.Length-gt24000){throw 'REJECTED_SIZE: edit exceeds 24000 characters; text was not discarded'}
 $lock=Enter-ForgeRejectedWriteLock
 try{$r=Read-ForgeRejectedProposal $Id;if(!$ExpectedEditSha-or$r.edit.content_sha256-cne$ExpectedEditSha){throw 'REJECTED_EDIT_STALE: reopen/compare before overwriting another edited copy'}
  $edit=[ordered]@{schema='forge.rejected_ai_edit.v1';id=$Id;record_sha256=$r.record_sha256;content=$Content;content_sha256=(Get-StringSha256Hex $Content);saved_at=[datetime]::UtcNow.ToString('o')}
  Write-ForgeRejectedAtomicJson (Join-Path (Get-ForgeRejectedDirectory $Id) 'edit.json') $edit;return [pscustomobject]$edit
 }finally{$lock.Dispose()}
}
function Get-ForgeRejectedValidationContext($Proposal) {
 $b=$Proposal.record.binding;$key=[string]$b.concept_key;$draft=$null
 $activeKey=[string](Get-PropertyValue (Get-PropertyValue $script:Current 'concept') 'concept_key')
 if($activeKey-and$key-cne$activeKey){throw 'REJECTED_CONTEXT: active concept differs; no context switch or implicit rebase'}
 if($key){$draft=Get-ResearchDraft $key;if($null-eq$draft-or$draft.current_revision_id-cne$b.revision_id-or$draft.current_revision_hash-cne$b.revision_hash){throw 'DRAFT_STALE: rejected proposal parent changed; no automatic rebase'}}
 $source=[string]$b.source_sha256
 if($draft){$currentSource=[string](Get-PropertyValue (Get-PropertyValue (Get-PropertyValue $draft 'provenance') 'research_packet') 'source_sha256');if($currentSource-cne$source){throw 'REJECTED_SOURCE_STALE: parent source binding changed'}}
 if(!$source){if($b.selected_records_sha256){throw 'REJECTED_SOURCE: missing bound archive'};return $null}
 if($source-cnotmatch'^[0-9a-f]{64}$'){throw 'REJECTED_SOURCE: invalid archive identity'}
 $oldCurrent=$script:Current;$oldDiscover=$script:DiscoverSnapshot
 try{
  # Resolve the immutable original archive through the real freshness/hash gate; do not use a later active pointer.
  $script:Current=[pscustomobject]@{draft=[pscustomobject]@{provenance=[pscustomobject]@{research_packet=[pscustomobject]@{source_sha256=$source}}}};$script:DiscoverSnapshot=$null
  $ctx=Get-ResearchEvidenceContext
  if($null-eq$ctx-or(Get-ForgeBriefSha256 $ctx.selected_records)-cne$b.selected_records_sha256){throw 'REJECTED_SOURCE_STALE: selected evidence changed'}
  $policy=if((Get-PropertyValue $ctx 'require_all_references')-is[bool]-and!$ctx.require_all_references){'explicit_subset'}else{'all_selected'}
  if($Proposal.record.reference_policy-cne$policy){throw 'REJECTED_POLICY_STALE: original source policy differs; no automatic policy change'}
  return $ctx
 }finally{$script:Current=$oldCurrent;$script:DiscoverSnapshot=$oldDiscover}
}
function Test-ForgeRejectedProposal([string]$Id,[string]$ExpectedEditSha) {
 $r=Read-ForgeRejectedProposal $Id;if(!$ExpectedEditSha-or$r.edit.content_sha256-cne$ExpectedEditSha){throw 'REJECTED_EDIT_STALE: edited copy changed'}
 # Canonical records retain their original schema and raw/edit bytes. The
 # legacy review transaction cannot create a canonical HOLD or its provenance;
 # refuse explicitly rather than misparse or silently save a flat projection.
 $properties=Get-PropertyValue $r.request.format 'properties'
 if($null-ne(Get-PropertyValue $properties 'design')-or$null-ne(Get-PropertyValue $properties 'owner_context')){
  throw 'REJECTED_CANONICAL_RECOVERY_UNAVAILABLE: Original canonical response and edited copy are retained. This legacy review path cannot safely save canonical proposals; no draft or approval was changed.'
 }
 Assert-ForgeLocalAIWireContract $r.edit.content $r.request.format
 $fields=ConvertFrom-ForgeLocalAIContent $r.edit.content
 $ctx=Get-ForgeRejectedValidationContext $r;Assert-ForgeAIFieldsForSave $fields $ctx
 $fields|Add-Member NoteProperty __forge_rejection_id $Id
 return [pscustomobject]@{proposal=$r;fields=$fields;evidence=$ctx;mechanical_valid=$true;semantic_verified=$false;approved=$false}
}
function Assert-ForgeRejectedSaveBinding([string]$Id,[string]$Key,[string]$ExpectedRevision,$Fields,[string]$Reason) {
 if($Id-cnotmatch'^rej-[0-9a-f]{32}$'-or$Reason-cne('local_ai_rejection_review_'+$Id)){throw 'REJECTED_MANUAL_BYPASS: retained AI provenance requires explicit AI review save'}
 $attempt=Read-ForgeRejectedJson (Join-Path (Get-ForgeRejectedDirectory $Id) 'save-attempt.json')
 if($attempt.outcome-cne'pending'){throw 'REJECTED_SAVE_RECONCILE: no pending explicit review save'}
 $v=Test-ForgeRejectedProposal $Id $attempt.edit_sha256;$binding=$v.proposal.record.binding
 if($binding.concept_key){if($binding.concept_key-cne$Key-or$binding.revision_id-cne$ExpectedRevision){throw 'DRAFT_STALE: review parent binding differs'}}elseif($ExpectedRevision-or$null-ne(Get-ResearchDraft $Key)){throw 'REJECTED_BASE: new proposal cannot replace an existing parent'}
 $expected=$v.fields;if($binding.concept_key){$expected=Merge-ForgeLocalAIManualFields (Get-ResearchDraft $Key) $expected}
 if((Get-ResearchDraftContentHash '' $Fields)-cne(Get-ResearchDraftContentHash '' $expected)){throw 'REJECTED_EDIT_STALE: save fields differ from validated retained copy'}
}
function Find-ForgeRejectedCommittedRevision($Proposal,$Attempt) {
 $matches=@();$s=Read-LocalCoreState
 foreach($d in @(Get-ResearchDraftList $s)){foreach($revision in @($d.revisions)){
  if($revision.reason-cne('local_ai_rejection_review_'+$Proposal.id)){continue}
  if($Proposal.record.binding.concept_key-and$d.concept_key-cne$Proposal.record.binding.concept_key){throw 'REJECTED_RECOVERY: commit parent mismatch'}
  if((Get-ResearchDraftContentHash '' $revision)-cne$Attempt.planned_fields_sha256){throw 'REJECTED_RECOVERY: committed content differs'}
  $matches+=[pscustomobject]@{draft=$d;revision=$revision}
 }}
 if($matches.Count-gt1){throw 'REJECTED_RECOVERY: multiple commits found; no retry'}
 if($matches.Count){return $matches[0]};return $null
}
function Get-ForgeRejectedAttemptHistory($Attempt) {
 $history=@((Get-PropertyValue $Attempt 'history')|Where-Object {$null-ne$_});if($history.Count-ge16){throw 'REJECTED_RECOVERY_LIMIT: attempt history is full; no records discarded'}
 $entry=[ordered]@{};foreach($p in $Attempt.PSObject.Properties){if($p.Name-cne'history'){$entry[$p.Name]=$p.Value}}
 return @($history)+@([pscustomobject]$entry)
}
function Resolve-ForgeRejectedSave([string]$Id,[switch]$ConfirmNotCommitted) {
 $lock=Enter-ForgeRejectedWriteLock
 try{
  $r=Read-ForgeRejectedProposal $Id;$path=Join-Path (Get-ForgeRejectedDirectory $Id) 'save-attempt.json'
  if(!(Test-Path -LiteralPath $path)){return [pscustomobject]@{outcome='not_attempted';saved=$false;approved=$false}}
  $attempt=Read-ForgeRejectedJson $path;$found=Find-ForgeRejectedCommittedRevision $r $attempt
  if($null-eq$found){
   if(!$ConfirmNotCommitted){return [pscustomobject]@{outcome='not_committed_at_readback';saved=$false;automatic_retry=$false;approved=$false}}
   $pre=[string](Get-PropertyValue $attempt 'pre_state_sha256')
   if($attempt.outcome-cnotin@('pending','unchanged')-or$pre-cnotmatch'^[0-9a-f]{64}$'-or(Get-FileSha256Hex $script:LocalCoreStatePath)-cne$pre){throw 'REJECTED_RECOVERY_UNCERTAIN: exact precommit state not proven; no retry authorized'}
   # A confirmed no-op may be followed by an explicit edit of the retained copy.
   # Exact pre-state proof above forbids parent rebase; pending attempts still
   # require their original edit identity until noncommit is reconciled.
   $reviewEditSha=if($attempt.outcome-ceq'unchanged'){$r.edit.content_sha256}else{$attempt.edit_sha256}
   $null=Test-ForgeRejectedProposal $Id $reviewEditSha
   Add-OrSetProperty $attempt 'history' @(Get-ForgeRejectedAttemptHistory $attempt);$attempt.outcome='reconciled_not_committed'
   Write-ForgeRejectedAtomicJson $path $attempt
   return [pscustomobject]@{outcome='reconciled_not_committed';saved=$false;explicit_save_required=$true;automatic_retry=$false;approved=$false}
  }
  $attempt.outcome='saved_unapproved';Add-OrSetProperty $attempt 'revision_id' $found.revision.revision_id;Write-ForgeRejectedAtomicJson $path $attempt
  return [pscustomobject]@{outcome='recovered_committed_revision';saved=$true;recovered=$true;draft=$found.draft;revision_id=$found.revision.revision_id;automatic_retry=$false;approved=$false}
 }finally{$lock.Dispose()}
}
function Save-ForgeRejectedProposal([string]$Id,[string]$ExpectedEditSha,[switch]$Cancel) {
 if($Cancel){return [pscustomobject]@{outcome='cancelled';saved=$false;approved=$false}}
 if($script:Dirty-or$script:PublicationDirty){throw 'REJECTED_ACTIVE_EDITS: save or keep existing unsaved editor text before explicit proposal save'}
 $lock=Enter-ForgeRejectedWriteLock
 try{
  $r=Read-ForgeRejectedProposal $Id;$dir=Get-ForgeRejectedDirectory $Id
  $attemptPath=Join-Path $dir 'save-attempt.json';$history=@()
  if(Test-Path -LiteralPath $attemptPath){$prior=Read-ForgeRejectedJson $attemptPath;$committed=Find-ForgeRejectedCommittedRevision $r $prior;if($null-ne$committed){return [pscustomobject]@{outcome='already_committed';saved=$false;draft=$committed.draft;revision_id=$committed.revision.revision_id;approved=$false}};if($prior.outcome-cne'reconciled_not_committed'-or(Get-FileSha256Hex $script:LocalCoreStatePath)-cne$prior.pre_state_sha256){throw 'REJECTED_SAVE_RECONCILE: prior save needs explicit proven noncommit recovery, no retry'};$history=@(Get-ForgeRejectedAttemptHistory $prior)}
  $validated=Test-ForgeRejectedProposal $Id $ExpectedEditSha
  $planned=$validated.fields;if($r.record.binding.concept_key){$planned=Merge-ForgeLocalAIManualFields (Get-ResearchDraft $r.record.binding.concept_key) $planned}
  $plannedSha=Get-ResearchDraftContentHash '' $planned
  $pending=[pscustomobject][ordered]@{outcome='pending';id=$Id;attempt_id=[guid]::NewGuid().ToString('N');history=$history;pre_state_sha256=(Get-FileSha256Hex $script:LocalCoreStatePath);edit_sha256=$ExpectedEditSha;planned_fields_sha256=$plannedSha;expected_revision=$r.record.binding.revision_id;at_utc=[datetime]::UtcNow.ToString('o');approved=$false};Write-ForgeRejectedAtomicJson $attemptPath $pending
  try{$saved=Save-ForgeLocalAIDraft $validated.fields 'Explicit review of retained rejected AI proposal; no new inference.' $r.record.binding.concept_key $r.record.binding.revision_id -EvidenceContext $validated.evidence -ReviewToken $Id}
  catch{throw ('REJECTED_SAVE_UNCERTAIN: inspect current revision before retry; original/edit retained. '+$_.Exception.Message)}
  if($null-eq$saved-or$saved.saved-isnot[bool]){throw 'REJECTED_SAVE_UNCERTAIN: invalid save acknowledgement'}
  try{$pending.outcome=$(if($saved.saved){'saved_unapproved'}else{'unchanged'});Add-OrSetProperty $pending 'revision_id' $saved.draft.current_revision_id;Write-ForgeRejectedAtomicJson $attemptPath $pending}catch{throw 'REJECTED_SAVE_UNCERTAIN: draft may be saved; quarantine receipt write failed, inspect revision before retry'}
  return $saved
 }finally{$lock.Dispose()}
}
function Save-ForgeRejectedUiBuffer {
 if(!$script:RejectedAIViewId-or$script:RejectedAIUiLoading){return}
 $edit=Save-ForgeRejectedEdit $script:RejectedAIViewId ([string]$script:RejectedAIEditor.Text) $script:RejectedAIEditSha
 $script:RejectedAIEditSha=$edit.content_sha256;$script:RejectedAIEditDirty=$false
}
function Refresh-ForgeRejectedUiList {
 $script:RejectedAIList.ItemsSource=@(Get-ForgeRejectedProposals)
}
function Open-ForgeRejectedUiProposal {
 if($script:RejectedAIEditDirty){Save-ForgeRejectedUiBuffer} # Failure leaves previous text and active draft untouched.
 $sel=$script:RejectedAIList.SelectedItem;if($null-eq$sel){throw 'Выберите отклонённый ответ.'}
 $r=Read-ForgeRejectedProposal $sel.id;$script:RejectedAIUiLoading=$true
 try{
  $script:RejectedAIViewId=$r.id;$script:RejectedAIEditSha=$r.edit.content_sha256
  $script:RejectedAIRaw.Text=$r.raw_text;$script:RejectedAIEditor.Text=$r.edit.content
  $script:RejectedAIReviewStatus.Text=('Отклонён, не проверен. '+$r.record.rejection_reason+"`nИзменение копии не является смысловым одобрением. Основной черновик не заменён.")
  $script:RejectedAIEditDirty=$false
 }finally{$script:RejectedAIUiLoading=$false}
}
function Initialize-ForgeRejectedAIUI {
 if($null-ne(Get-Variable RejectedAIExpander -Scope Script -ErrorAction SilentlyContinue)){return}
 $parent=$LocalAIStatus.Parent
 if($null-eq$parent-or$parent-isnot[Windows.Controls.Panel]){throw 'Existing Local AI panel unavailable; rejected records remain accessible through local functions.'}
 $script:RejectedAIExpander=New-Object Windows.Controls.Expander;$script:RejectedAIExpander.Header='Отклонённые ответы AI — не проверены'
 $panel=New-Object Windows.Controls.StackPanel;$script:RejectedAIExpander.Content=$panel
 $script:RejectedAIList=New-Object Windows.Controls.ComboBox;$script:RejectedAIList.DisplayMemberPath='label';[void]$panel.Children.Add($script:RejectedAIList)
 $buttons=New-Object Windows.Controls.WrapPanel;[void]$panel.Children.Add($buttons)
 foreach($name in @('Обновить список','Открыть','Проверить копию','Сохранить проверенную копию')){$b=New-Object Windows.Controls.Button;$b.Content=$name;[void]$buttons.Children.Add($b)}
 $script:RejectedAIReviewStatus=New-Object Windows.Controls.TextBlock;$script:RejectedAIReviewStatus.TextWrapping='Wrap';$script:RejectedAIReviewStatus.Text='Оригинал неизменяем. Копия сохраняется отдельно; проверка не подтверждает смысл или качество.';[void]$panel.Children.Add($script:RejectedAIReviewStatus)
 $script:RejectedAIRaw=New-Object Windows.Controls.TextBox;$script:RejectedAIRaw.IsReadOnly=$true;$script:RejectedAIRaw.AcceptsReturn=$true;$script:RejectedAIRaw.MaxHeight=160;$script:RejectedAIRaw.VerticalScrollBarVisibility='Auto';[void]$panel.Children.Add($script:RejectedAIRaw)
 $script:RejectedAIEditor=New-Object Windows.Controls.TextBox;$script:RejectedAIEditor.AcceptsReturn=$true;$script:RejectedAIEditor.TextWrapping='Wrap';$script:RejectedAIEditor.MinHeight=100;$script:RejectedAIEditor.MaxHeight=300;$script:RejectedAIEditor.MaxLength=24000;$script:RejectedAIEditor.VerticalScrollBarVisibility='Auto';[void]$panel.Children.Add($script:RejectedAIEditor)
 $script:RejectedAIEditor.Add_TextChanged({if(!$script:RejectedAIUiLoading-and$script:RejectedAIViewId){$script:RejectedAIEditDirty=$true;try{Save-ForgeRejectedUiBuffer;$script:RejectedAIReviewStatus.Text='Копия сохранена отдельно. Не проверена; активный черновик не изменён.'}catch{$script:RejectedAIReviewStatus.Text=('КОПИЯ НЕ СОХРАНЕНА; текст остаётся в редакторе. '+$_.Exception.Message)}}})
 $buttons.Children[0].Add_Click({try{Refresh-ForgeRejectedUiList}catch{$script:RejectedAIReviewStatus.Text=$_.Exception.Message}})
 $buttons.Children[1].Add_Click({try{Open-ForgeRejectedUiProposal}catch{$script:RejectedAIReviewStatus.Text=$_.Exception.Message}})
 $buttons.Children[2].Add_Click({try{if($script:RejectedAIEditDirty){Save-ForgeRejectedUiBuffer};$null=Test-ForgeRejectedProposal $script:RejectedAIViewId $script:RejectedAIEditSha;$script:RejectedAIReviewStatus.Text='Механические проверки пройдены. Смысл, права, спрос и качество не подтверждены. Активная ревизия не изменена.'}catch{$script:RejectedAIReviewStatus.Text=('Копия не прошла проверку: '+$_.Exception.Message)}})
 $buttons.Children[3].Add_Click({try{if($script:RejectedAIEditDirty){Save-ForgeRejectedUiBuffer};$saved=Save-ForgeRejectedProposal $script:RejectedAIViewId $script:RejectedAIEditSha;if($saved.saved){Set-ForgeLocalAISavedPresentation $saved};$script:RejectedAIReviewStatus.Text='Сохранение подтверждено. Ревизия не одобрена; смысловая проверка остаётся необходимой.'}catch{$script:RejectedAIReviewStatus.Text=$_.Exception.Message}})
 $recover=New-Object Windows.Controls.Button;$recover.Content='Explicit noncommit recovery';[void]$buttons.Children.Add($recover)
 $recover.Add_Click({try{if($script:RejectedAIEditDirty){Save-ForgeRejectedUiBuffer};$result=Resolve-ForgeRejectedSave $script:RejectedAIViewId -ConfirmNotCommitted;$script:RejectedAIReviewStatus.Text=$result.outcome+'; no automatic save or approval.'}catch{$script:RejectedAIReviewStatus.Text=$_.Exception.Message}})
 [void]$parent.Children.Add($script:RejectedAIExpander)
 try{Refresh-ForgeRejectedUiList}catch{$script:RejectedAIReviewStatus.Text=('Хранилище отклонённых ответов недоступно: '+$_.Exception.Message)}
}
