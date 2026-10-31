$ErrorActionPreference='Stop';$root=$PSScriptRoot
function Get-PropertyValue($Object,$Name,$Default=$null){if($null-eq$Object){return $Default};if($Object-is[Collections.IDictionary]){return $Object[$Name]};$p=$Object.PSObject.Properties[$Name];if($null-ne$p){return $p.Value};return $Default}
function Ensure-Dir($Path){[void][IO.Directory]::CreateDirectory($Path)}
function Write-AppLog($Level,$Message){}
foreach($n in @('Forge.Media.ps1','Forge.DataViews.ps1','Forge.LocalCore.ps1','Forge.ResearchDrafts.ps1','Forge.ResearchImport.ps1','Forge.PublicEvidence.ps1','Forge.PublicRss.ps1','Forge.ResearchReview.ps1','Forge.LocalAI.ps1')){. (Join-Path $root ('runtime/Modules/'+$n))}
function New-ForgeLocalAIJsonRequest($Body){throw 'TEST_BOUNDARY: no model transport authorized'}
$fixture=Get-Content (Join-Path (Split-Path $root) 'forge-rejection-review-dev-001/acceptance-frozen-copy/fixtures/synthetic-valid-fields.json') -Raw -Encoding utf8|ConvertFrom-Json
$plan=[ordered]@{design=[ordered]@{print_plan_id='black_white';print_text_en='SYNTHETIC FIXTURE ONLY';title_ru=$fixture.title;artwork_subject_ru='Синтетическая геометрическая фигура для проверки адаптера';artwork_geometry_ru=$fixture.production_spec.illustration;arrangement='text_above_art';typography_style='bold_sans';alignment='center';avoid=@($fixture.production_spec.avoid)};owner_context=[ordered]@{source_and_idea_ru=$fixture.concept_text.Replace(' [E4]','');audience_hypothesis_ru=$fixture.target_buyer;purchase_hypothesis_ru=$fixture.purchase_reason;positioning_hypothesis_ru=$fixture.differentiation}}
[ordered]@{synthetic_transport_fixture=$true;not_design_quality_example=$true;source_envelope='Unchanged real public receipt; production refuses synthetic evidence, no flag falsified';plan=$plan}|ConvertTo-Json -Depth 40|Set-Content (Join-Path $root 'SYNTHETIC-ADAPTER-FIXTURE.json') -Encoding utf8
$results=[ordered]@{}
$plan.owner_context.text_image_relationship_ru='Надпись обозначает условный порядок, а геометрическая фигура показывает последовательность элементов; это синтетическая проверка хранения, не товарный замысел.'
foreach($caseName in @('positive','live_lookup_changed','missing_artwork','inconsistent_fixed_preset','missing_print_uncertainty','hook_CR','hook_LF','dirty','owner_edit','preset_metadata_changed')){
 $case=Join-Path $root ($caseName+'-'+[guid]::NewGuid().ToString('N'));Ensure-Dir $case
 $script:StateRoot=Join-Path $case 'state';Ensure-Dir $script:StateRoot
 foreach($dir in @('core','research-import-v1')){Copy-Item (Join-Path (Split-Path $root) ('forge-core-birding-trial-001/owned-state/'+$dir)) $script:StateRoot -Recurse}
 $script:LocalCoreRoot=Join-Path $script:StateRoot 'core';$script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json';$script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'backup.json'
 $d=@(Get-ResearchDraftList (Read-LocalCoreState))[0];$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d);draft=$d;local_research_draft=$true};$script:DiscoverSnapshot=$null;$script:Dirty=$false;$script:PublicationDirty=$false;$ctx=Get-ResearchEvidenceContext
 $script:LocalAIStatus=[pscustomobject]@{Text=''};$script:LocalAICreateButton=[pscustomobject]@{IsEnabled=$false};$script:LocalAIReviseButton=[pscustomobject]@{IsEnabled=$false};$script:LocalAICancelButton=[pscustomobject]@{IsEnabled=$true};$script:LastCanonicalResponse=$null;$script:LastLocalAISaveReceipt=$null
 if($caseName-eq'owner_edit'){$ownerFields=Get-ResearchDraftCurrentFields $d|ConvertTo-Json -Depth 40|ConvertFrom-Json;$ownerFields.title='Сохранённая правка владельца';$ownerSave=Save-ResearchDraftRevision $d.concept_key $ownerFields 'owner_edit' $d.current_revision_id;$d=$ownerSave.draft;$script:Current.concept=ConvertTo-ResearchDraftConcept $d;$script:Current.draft=$d;$ctx=Get-ResearchEvidenceContext}
 $value=$plan|ConvertTo-Json -Depth 40|ConvertFrom-Json
 if($caseName-eq'missing_artwork'){$value.design.PSObject.Properties.Remove('artwork_geometry_ru')}
 if($caseName-eq'missing_print_uncertainty'){$value.owner_context.positioning_hypothesis_ru=$value.owner_context.positioning_hypothesis_ru.Replace('Качество печати не проверено.','')}
 if($caseName-eq'hook_CR'){$value.design.print_text_en+="`r"};if($caseName-eq'hook_LF'){$value.design.print_text_en+="`n"}
 $requested=if($caseName-eq'inconsistent_fixed_preset'){'white_black'}else{''}
 $body=New-ForgeCanonicalDesignBody -Task 'Synthetic transport correctness control, not a design-quality example' -EvidenceContext $ctx -PrintPreset $requested;$bodyJson=$body|ConvertTo-Json -Depth 40 -Compress
 $schema=$body.format;$content=$value|ConvertTo-Json -Depth 40 -Compress
 $outer=[ordered]@{synthetic_transport_fixture=$true;model='qwen3.5:9b';done=$true;done_reason='stop';message=@{role='assistant';content=$content}}
 $wire=[Text.Encoding]::UTF8.GetBytes(($outer|ConvertTo-Json -Depth 45 -Compress));$response=[Net.Http.HttpResponseMessage]::new([Net.HttpStatusCode]::OK);$response.Content=[Net.Http.ByteArrayContent]::new($wire)
 $request=[pscustomobject]@{ResponseContract='canonical_v1';RequestedPrintPreset=$requested;ResponseSchema=$schema;EvidenceContext=$ctx;Key=$d.concept_key;Revision=$d.current_revision_id;RevisionHash=$d.current_revision_hash;Prompt='Synthetic adapter correctness control; not model output';Task=[Threading.Tasks.Task]::FromResult[Net.Http.HttpResponseMessage]($response);Cancel=[Threading.CancellationTokenSource]::new();Client=[Net.Http.HttpClient]::new();Content=[Net.Http.StringContent]::new($bodyJson)}
 if($caseName-eq'preset_metadata_changed'){$request.RequestedPrintPreset='white_black'}
 $script:OwnerBuffer='UNSAVED OWNER TEXT';if($caseName-eq'dirty'){$script:Dirty=$true}
 if($caseName-eq'live_lookup_changed'){$script:OriginalPresetFunction=${function:Get-ForgeLockedPrintPlan};function Get-ForgeLockedPrintPlan([string]$Preset){& $script:OriginalPresetFunction 'white_black'}}
 $before=Get-FileSha256Hex $script:LocalCoreStatePath;$script:LocalAIRequest=$request;$script:Trace=[Collections.Generic.List[string]]::new();$bps=@()
 foreach($fn in @('ConvertFrom-ForgeCanonicalDesign','Assert-ForgeAIFieldsForSave','Assert-ForgeOwnerLanguage','Assert-QwenEvidenceCitations','Save-ForgeCanonicalHeldDraft','Save-ForgeLocalAIDraft','Save-ResearchDraftRevision','Write-LocalCoreState')){$bps+=Set-PSBreakpoint -Command $fn -Action ([scriptblock]::Create('[void]$script:Trace.Add("'+$fn+'")'))}
 try{Complete-ForgeLocalAIRequest}finally{$bps|Remove-PSBreakpoint;if($caseName-eq'live_lookup_changed'){Set-Item Function:\Get-ForgeLockedPrintPlan $script:OriginalPresetFunction}}
 $after=Get-ResearchDraft $d.concept_key;$raw=$script:LastCanonicalResponse
 if($null-eq$raw-or(Get-FileSha256Hex (Join-Path $raw.directory 'canonical-content.txt'))-cne(Get-StringSha256Hex $content)){throw 'Original canonical content lost'}
 if((Get-FileSha256Hex (Join-Path $raw.directory 'wire.raw'))-cne(Get-ByteSha256Hex $wire)){throw 'Raw wire mismatch'}
 $decision=Get-LocalOwnerDecisionRecord $after.concept_key (ConvertTo-ResearchDraftConcept $after)
 if($caseName-in@('positive','live_lookup_changed')){
  if($after.revisions.Count-ne($d.revisions.Count+1)-or$decision.decision-cne'UNDECIDED'){try{Save-ForgeCanonicalHeldDraft $request $raw}catch{Write-Output $_.ToString();throw};throw ('Positive native save failed: '+$LocalAIStatus.Text)}
  $revision=Get-ResearchDraftCurrentFields $after;$mapping=Get-Content (Join-Path $raw.directory 'legacy-mapping.json') -Raw -Encoding utf8|ConvertFrom-Json
  if($revision.hook-cne$value.design.print_text_en-or!$revision.production_spec.composition.Contains($value.design.print_text_en)-or$revision.production_spec.illustration-cne($value.design.artwork_subject_ru+'. '+$value.design.artwork_geometry_ru)){throw 'Projection changed creative values'}
  $boundPayload=ConvertFrom-ForgeJsonObjectStrict $body.messages[1].content;$expectedPlan=@($boundPayload.allowed_product_print_plans|Where-Object{$_.preset_id-ceq$value.design.print_plan_id})[0]
  if((Get-ForgeBriefSha256 $mapping.fields.production_spec.ink_palette)-cne(Get-ForgeBriefSha256 $expectedPlan.actual_opaque_inks)-or!$mapping.fields.visual_direction_text.Contains($expectedPlan.garment_preview_context)){throw 'Physical plan reinterpreted instead of request binding'}
  if($mapping.print_preset_origin-cne'model_proposed_product_preset'-or$mapping.print_preset-cne$value.design.print_plan_id){throw 'Preset provenance lost'}
  if($after.semantic_review_hold.status-cne'PENDING'-or$revision.semantic_review_hold.relationship_exact-cne$value.owner_context.text_image_relationship_ru){throw 'Durable exact relationship/HOLD missing'}
  foreach($action in @({Assert-LocalGenerationBriefApproved (ConvertTo-ResearchDraftConcept $after)},{Confirm-LocalGenerationBriefApproval},{Export-LocalGenerationBrief},{Get-ForgeLocalAcceptanceTarget $null (Read-LocalCoreState)},{Assert-ForgeGenerationJobBriefApproval ([pscustomobject]@{concept_key=$after.concept_key}) (Read-LocalCoreState)})){
   $blocked=$false;try{& $action}catch{if($_.Exception.Message-like'SEMANTIC_REVIEW_HOLD:*'){$blocked=$true}else{throw}};if(!$blocked){throw 'HOLD downstream not blocked'}
  }
  foreach($fn in @('Save-ForgeCanonicalHeldDraft','Write-LocalCoreState')){if(!$script:Trace.Contains($fn)){throw ('Native save not observed: '+$fn)}}
 }else{
  if($before-cne(Get-FileSha256Hex $script:LocalCoreStatePath)-or$after.revisions.Count-ne$d.revisions.Count){throw 'Rejected proposal changed active state'}
  if($caseName-ne'dirty'-and(Test-Path (Join-Path $raw.directory 'legacy-mapping.json'))){throw 'Invalid plan was filled/mapped'}
 }
 if($caseName-eq'dirty'-and(!$script:Dirty-or$script:OwnerBuffer-cne'UNSAVED OWNER TEXT')){throw 'Dirty owner buffer overwritten'}
 if($caseName-eq'owner_edit'-and(Get-ResearchDraftCurrentFields $after).title-cne'Сохранённая правка владельца'){throw 'Owner edit overwritten'}
 $results[$caseName]=[ordered]@{passed=$true;synthetic_response=$true;real_model_calls=0;raw_content_sha256=(Get-StringSha256Hex $content);revision_before=$d.revisions.Count;revision_after=$after.revisions.Count;owner_decision=$decision.decision;status=$LocalAIStatus.Text;native_save_receipt=$script:LastLocalAISaveReceipt;trace=@($script:Trace);case_root=$case;raw_directory=$raw.directory;quality='NOT_MEASURED'}
}
$results|ConvertTo-Json -Depth 60|Set-Content (Join-Path $root 'ADAPTER-CORRECTNESS-RESULTS.json') -Encoding utf8
Write-Output 'POSITIVE_AND_REJECTIONS_PASS_NOT_MODEL_QUALITY'
