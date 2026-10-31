. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
# Merch Forge · Explicit owner actions
# Mutating Generate/Accept/Publication/package actions live here; all remain explicit and gated.
function Prepare-DeliveryPackage {
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; if($null -eq $script:Current){return}; $c=$script:Current.concept
    Set-Busy $true 'Preparing delivery manifest…'
    try { $null=Invoke-ForgeApi 'prepare_delivery_bundle' @{concept_key=$c.concept_key}; Load-Delivery ([string]$c.concept_key); $StatusText.Text='Delivery manifest prepared. No ZIP was claimed saved.' }
    catch { Show-Error $_.Exception.Message; $StatusText.Text='Delivery package needs attention.' }
    finally { Set-Busy $false $StatusText.Text }
}
function Prepare-SocialHandoff {
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; if($null -eq $script:Current -or $null -eq $script:Delivery){return}; $c=$script:Current.concept; $w=$script:Delivery.workspace
    if([string]::IsNullOrWhiteSpace([string]$w.delivery_bundle_id)){Show-Error 'Prepare the delivery package first.';return}
    if(-not (Confirm 'Prepare this exact accepted design as source material for the separate Social workflow? This does not approve or publish a Social post.' 'Send to Social')){return}
    Set-Busy $true 'Preparing Social handoff…'
    try { $null=Invoke-ForgeApi 'prepare_social_handoff' @{delivery_bundle_id=$w.delivery_bundle_id;owner_notes='';explanations=@{}}; Load-Delivery ([string]$c.concept_key); $StatusText.Text='Social source envelope prepared. Social was not approved or published.' }
    catch { Show-Error $_.Exception.Message; $StatusText.Text='Social handoff needs attention.' }
    finally { Set-Busy $false $StatusText.Text }
}
function Prepare-OwnerPackage {
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; if($null -eq $script:Current -or $null -eq $script:Delivery){return}; $c=$script:Current.concept; $w=$script:Delivery.workspace
    if([string]::IsNullOrWhiteSpace([string]$w.delivery_bundle_id)){Show-Error 'Prepare the delivery package first.';return}
    $kind='generic_owner_export'; if($null -ne $PackageTargetBox.SelectedItem){$kind=[string]$PackageTargetBox.SelectedItem.Tag}
    $payload=@{package_kind=$kind;delivery_bundle_id=$w.delivery_bundle_id;social_handoff_id=$null;amazon_preflight_package_id=$null}
    if($kind -eq 'social_source_package'){$payload.social_handoff_id=$w.social_handoff_id}
    if($kind -eq 'amazon_owner_package'){
        if($null -eq $script:Publication -or [string]::IsNullOrWhiteSpace([string]$script:Publication.workspace.preflight_package_id)){Show-Error 'A current Amazon preflight package is required first.';return}
        $payload.amazon_preflight_package_id=$script:Publication.workspace.preflight_package_id
    }
    Set-Busy $true 'Preparing owner package…'
    try { $null=Invoke-ForgeApi 'prepare_publish_package' $payload; Load-Delivery ([string]$c.concept_key); $StatusText.Text='Owner package prepared. Nothing was submitted or published.' }
    catch { Show-Error $_.Exception.Message; $StatusText.Text='Owner package needs attention.' }
    finally { Set-Busy $false $StatusText.Text }
}
function Get-ForgePublicationPayloadSnapshot($Workspace) {
    if($null-eq$Workspace){throw 'Listing workspace is unavailable.'}
    $result=[ordered]@{}
    foreach($field in @('listing_title','brand','bullet_1','bullet_2','description','locale')){
        $property=$Workspace.PSObject.Properties[$field]
        if($null-eq$property-or($null-ne$property.Value-and$property.Value-isnot[string])){throw ('Listing field is missing or invalid: '+$field)}
        $result[$field]=[string]$property.Value
    }
    $property=$Workspace.PSObject.Properties['keywords'];if($null-eq$property-or($null-ne$property.Value-and$property.Value-isnot[Array])){throw 'Listing keywords are missing or invalid.'}
    if($null-ne$property.Value){foreach($keyword in $property.Value){if($keyword-isnot[string]){throw 'Listing keyword is invalid.'}};$result.keywords=@($property.Value)}else{$result.keywords=@()}
    return [pscustomobject]$result
}
function Assert-ForgePublicationWorkspaceIdentity($Workspace) {
    if($null-eq$Workspace-or(Get-PropertyValue $Workspace 'current_revision_accepted')-isnot[bool]){throw 'The accepted listing context could not be verified.'}
    foreach($field in @('current_acceptance_id','current_metadata_revision_id','metadata_content_hash')){
        $value=Get-PropertyValue $Workspace $field
        if($null-ne$value-and$value-isnot[string]){throw 'The listing version identity is invalid.'}
    }
    if([bool]$Workspace.current_revision_accepted-and![string](Get-PropertyValue $Workspace 'current_acceptance_id')){throw 'The accepted listing context is missing its identity.'}
    $hash=[string](Get-PropertyValue $Workspace 'metadata_content_hash')
    if($hash-and$hash-cnotmatch'^[0-9a-fA-F]{64}$'){throw 'The listing content fingerprint is invalid.'}
    if(([bool][string](Get-PropertyValue $Workspace 'current_metadata_revision_id'))-ne([bool]$hash)){throw 'The listing version and fingerprint are incomplete.'}
    $null=Get-ForgePublicationPayloadSnapshot $Workspace
}
function Save-PublicationMetadata {
    if($null-ne$script:Publication-and[bool](Get-PropertyValue $script:Publication 'local_core')){return (Save-LocalPublicationMetadata)}
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return $false}
    if(!(Has-Cap 'prepare_publication')){Show-Error 'Your workspace role cannot edit publication metadata.';return $false}
    if($null-eq$script:Current-or$null-eq$script:Publication-or!$script:PublicationDirty){return $false}
    if((Get-PropertyValue $script:Publication 'save_outcome_unverified')-is[bool]-and(Get-PropertyValue $script:Publication 'save_outcome_unverified')){Show-Error 'The previous listing save or reload is unverified. Refresh Publication before retrying; no repeated request was sent.';return $false}
    $view=Get-ForgeLocalRefreshView;$sent=$false;$acknowledged=$false;$failed=$false
    Set-Busy $true 'Saving listing version.'
    try {
        $c=$script:Current.concept;$w=$script:Publication.workspace
        if([string](Get-PropertyValue $script:Publication 'loaded_concept_key')-cne[string]$c.concept_key){throw 'This listing editor belongs to another or unverified idea. Refresh Publication before saving.'}
        Assert-ForgePublicationWorkspaceIdentity $w
        if(!$w.current_revision_accepted){throw 'Accept a design version before saving listing details.'}
        $title=([string]$PublicationTitleBox.Text).Trim();if(!$title){throw 'Listing title is required.'}
        $keywords=@();foreach($k in (([string]$PublicationKeywordsBox.Text)-split'[,;]')){$t=$k.Trim();if($t){$keywords+=$t}}
        $payload=[pscustomobject]@{listing_title=$title;brand=[string]$PublicationBrandBox.Text;bullet_1=[string]$PublicationBullet1Box.Text;bullet_2=[string]$PublicationBullet2Box.Text;description=[string]$PublicationDescriptionBox.Text;keywords=@($keywords);locale=(Get-PublicationLocale)}
        $expected=ConvertTo-ForgeBriefCanonicalJson (Get-ForgePublicationPayloadSnapshot $payload)
        $oldPayload=ConvertTo-ForgeBriefCanonicalJson (Get-ForgePublicationPayloadSnapshot $w)
        $acceptance=[string]$w.current_acceptance_id;$revision=[string](Get-PropertyValue $w 'current_metadata_revision_id');$contentHash=[string](Get-PropertyValue $w 'metadata_content_hash')
        $sent=$true;$null=Invoke-ForgeApi 'save_publication_metadata' @{concept_key=$c.concept_key;expected_acceptance_id=$acceptance;expected_metadata_revision_id=$revision;expected_metadata_content_hash=$contentHash;payload=$payload;edit_reason=[string]$PublicationReasonBox.Text};$acknowledged=$true
        $null=Load-Publication ([string]$c.concept_key)
        if($null-eq$script:Publication){throw 'The saved listing could not be reloaded.'}
        $fresh=$script:Publication.workspace;Assert-ForgePublicationWorkspaceIdentity $fresh
        if((Get-PropertyValue $script:Publication 'save_outcome_unverified')-or[string](Get-PropertyValue $script:Publication 'loaded_concept_key')-cne[string]$c.concept_key-or!$fresh.current_revision_accepted-or[string]$fresh.current_acceptance_id-cne$acceptance-or![string](Get-PropertyValue $fresh 'current_metadata_revision_id')-or[string](Get-PropertyValue $fresh 'metadata_content_hash')-cnotmatch'^[0-9a-fA-F]{64}$'-or(ConvertTo-ForgeBriefCanonicalJson (Get-ForgePublicationPayloadSnapshot $fresh))-cne$expected-or($oldPayload-cne$expected-and[string]$fresh.current_metadata_revision_id-ceq$revision)){throw 'The acknowledged listing does not match the reloaded accepted version.'}
        Set-PublicationDirty $false;$StatusText.Text='Listing saved and reloaded; accepted design unchanged.';return $true
    } catch {
        $failed=$true;$technical=$_.Exception.Message;Restore-ForgeLocalRefreshView $view
        if($sent-and$null-ne$script:Publication){Add-OrSetProperty $script:Publication 'save_outcome_unverified' $true}
        $message=if($acknowledged){'The server acknowledged the listing save, but the saved version could not be verified. Your fields were preserved. Refresh Publication before retrying; no automatic repeat was sent.'}elseif($sent){'The listing save outcome could not be verified. Your fields were preserved. Refresh Publication before retrying; no automatic repeat was sent.'}else{$technical}
        Write-AppLog 'WARN' ('Listing save outcome: '+$technical);Set-LastDiagnostic 'publication_save' 0 'refresh_before_retry' $technical $message
        Show-Error $message;$StatusText.Text=$message;return $false
    } finally {Set-Busy $false $StatusText.Text;if($failed){Set-ForgeLocalReadUnavailable;$SavePublicationButton.IsEnabled=$false;$StatusText.Text=$message}}
}

function Save-Revision {
    if(Test-CurrentIsResearchDraft){Save-CurrentResearchDraftRevision;return}
    if(-not(Has-Cap 'edit')){Show-Error 'Your workspace role cannot edit concepts.';return}
    if($null-eq$script:Current){return}
    if([bool]$script:Current.concept.current_revision_accepted){Show-Error 'This revision is accepted. Use Start new iteration - edited brief so the accepted version stays in history.';return}
    if($script:PublicationDirty-and!(Confirm 'Saving a new creative revision invalidates the current publication context and discards unsaved publication metadata. Continue?')){return}
    $view=Get-ForgeLocalRefreshView;$sent=$false;$acknowledged=$false;$saveFailed=$false
    Set-Busy $true 'Saving new revision.'
    try{
        $c=$script:Current.concept;$editedSpec=ConvertFrom-ForgeProductionSpecJson ([string]$SpecBox.Text);$patch=Build-Patch;$dirty=Get-ProductionSpecDirtyValues $c.production_spec $editedSpec
        $proposed=New-ForgeGenerationBriefSnapshot $c;foreach($field in $patch.Keys){Add-OrSetProperty $proposed $field $patch[$field]};$proposed.production_spec=$editedSpec
        $payload=@{concept_key=$c.concept_key;expected_revision_id=$c.current_revision_id;expected_content_hash=$c.current_content_hash;patch=$patch;production_spec_dirty_values=$dirty;edit_reason=$ReasonBox.Text};if($script:RestoreSourceRevisionId){$payload.source_revision_id=$script:RestoreSourceRevisionId}
        # Persist uncertainty and revoke changed-brief approval before transport.
        $ownerLanguageNotice=Format-ForgeOwnerLanguageReview $proposed
        $intent=Start-ForgeSourceSaveIntent $proposed
        $sent=$true;$r=Invoke-ForgeApi 'save_revision' $payload;$acknowledged=$true
        $opened=@(Load-Concept ([string]$c.concept_key) $true $intent.proposed_brief_sha256)
        if(!(@($opened|Where-Object{$_-is[bool]-and$_}).Count)){throw 'Saved source could not be reopened.'}
        $saved=Get-LocalCoreConcept ([string]$c.concept_key)
        if($null-ne(Get-PropertyValue $saved 'source_save_intent')-or(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $script:Current.concept))-cne$intent.proposed_brief_sha256){throw 'Reloaded source does not match the requested full brief. Review the saved revision before retrying.'}
        Set-PublicationDirty $false;Set-Dirty $false
        $StatusText.Text=('Ревизия {0} сохранена; оригиналы не переведены автоматически. Язык пояснений указан в обзоре.'-f[string](Get-PropertyValue $script:Current.concept 'current_revision_no'))
        return $true
    }catch{
        $saveFailed=$true;$failure=$_.Exception.Message;Restore-ForgeLocalRefreshView $view
        Write-AppLog 'WARN' ('Creative save outcome: '+$failure)
        $message=if($acknowledged){Get-UiText 'source.save.ack_unverified' 'The server acknowledged the save, but the current full brief could not be verified. Your edits were preserved. Refresh the saved idea before retrying; no automatic repeat was sent.'}elseif($sent){Get-UiText 'source.save.unverified' 'The save outcome could not be verified. Your edits were preserved. Refresh the saved idea before retrying; no automatic repeat was sent.'}else{$failure}
        Show-Error $message;$StatusText.Text=$message
        return $false
    }finally{Set-Busy $false $StatusText.Text;if($saveFailed){Set-ForgeLocalReadUnavailable;$StatusText.Text=$message}}
}
function Resolve-LocalGeneratedArtworkSource($Selected,[object[]]$Generated) {
    if([string](Get-PropertyValue $Selected 'provider_key')-cne'local_birefnet_preparation'){return $Selected}
    $prep=Get-PropertyValue $Selected 'preparation';$sha=[string](Get-PropertyValue $prep 'source_sha256');$id=[string](Get-PropertyValue $prep 'source_variant_id');$request=[string](Get-PropertyValue $prep 'source_generation_request_id')
    $candidates=@($Generated|Where-Object{[string](Get-PropertyValue $_ 'asset_sha256')-ceq$sha-and(!$id-or[string](Get-PropertyValue $_ 'id')-ceq$id)-and(!$request-or[string](Get-PropertyValue $_ 'generation_request_id')-ceq$request)})
    if($candidates.Count-ne1){
        $message=switch($script:Locale){'ru'{'Выберите исходный сгенерированный эскиз во вкладке арта для новой генерации. Исходник этого подготовленного кандидата не определён однозначно.'}'es'{'Selecciona la vista previa original generada para volver a generar. El origen de este candidato preparado no se identifica de forma única.'}default{'Select the original generated preview in Artwork before regenerating. This prepared candidate does not identify one unique original.'}}
        throw $message
    }
    return $candidates[0]
}
function Queue-Generation {
    if($null -ne $script:Current){try{$null=Sync-LocalGenerationResults}catch{Write-AppLog 'WARN' ('Pre-generate local result recovery failed: '+$_.Exception.Message)}}
    $localCfg=Get-GenerationProviderRuntimeConfig;$localReadiness=Get-GenerationProviderLocalReadiness;$localEnabled=[bool](Get-PropertyValue $localCfg 'enabled');$localReady=[bool](Get-PropertyValue $localReadiness 'ready')
    if([string](Get-PropertyValue $localCfg 'configuration_status')-ceq'invalid'){Show-Error ((Get-UiText 'generation.config.invalid' 'Provider configuration is invalid and was preserved. Review or restore it before generating. {0}')-f[string](Get-PropertyValue $localCfg 'configuration_error'));return}
    if($localEnabled -and -not $localReady){$code=[string](Get-PropertyValue $localReadiness 'code');$detail=if($code -eq 'daily_request_limit_reached'){('Daily provider request ceiling reached: {0}/{1}. Increase the ceiling explicitly in Configure Image Provider, or wait for the next UTC day.' -f [int](Get-PropertyValue $localReadiness 'paid_requests_today'),[int](Get-PropertyValue $localReadiness 'daily_request_limit'))}elseif($code -eq 'credential_missing'){'The local image provider is enabled but its credential is missing. Run Configure Image Provider or set OPENAI_API_KEY.'}elseif($code -eq 'unsafe_config'){'The local image provider configuration failed its safety contract. Run Configure Image Provider again.'}else{('The local image provider is enabled but not ready: '+$code)};Show-Error $detail;return}
    if($localReady){
        if($null -eq $script:Current -or $script:Dirty){return};$c=$script:Current.concept;if([bool](Get-PropertyValue $c 'current_revision_accepted')){Show-Error 'Accepted revisions are frozen. Start a new iteration before generating again.';return}
        try{if(-not(Confirm-LocalGenerationBriefApproval)){return}}catch{Show-Error $_.Exception.Message;return}
        $jobs=@(Get-LocalGenerationJobsForCurrent);$pendingImport=@($jobs|Where-Object{$_.status -eq 'completed_pending_import'});if($pendingImport.Count -gt 0){Show-Error ('A completed provider result is waiting for verified import/recovery before another paid request can start: '+[string]$pendingImport[0].id+'. Use Refresh; if it remains blocked, review Diagnostics instead of generating again.');return};$ambiguous=@($jobs|Where-Object{$_.status -eq 'ambiguous'});if($ambiguous.Count -gt 0){$a=$ambiguous[0];$dispatchBinding=Get-LocalGenerationDispatchBinding $localCfg;$warning=Get-LocalGenerationAmbiguousWarning $a $ambiguous.Count ([string](Get-PropertyValue $localCfg 'provider_key')) $localCfg;$warn=$warning.message;if(-not(Confirm $warn $warning.title)){return};Set-Busy $true 'Starting explicit generation after ambiguous provider outcome…';try{$r=Queue-LocalGeneration 'generate' ([string]$a.id) $dispatchBinding;Refresh-LocalArtworkUi;$StatusText.Text=("New explicit generation job {0} started after ambiguous job {1}." -f [string](Get-PropertyValue (Get-PropertyValue $r 'job') 'job_id'),[string]$a.id)}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local generation could not start.'}finally{Set-Busy $false $StatusText.Text};return};$localVariants=@(Get-LocalCoreVariantsForCurrent);$generatedVariants=@($localVariants|Where-Object{Test-LocalProviderArtworkLineage $_});$kind=if($generatedVariants.Count){'regenerate'}else{'generate'};$label=if($kind-eq'regenerate'){'Re-generate'}else{'Generate'};$prior='';$variantLabel=''
        if($kind -eq 'regenerate'){$selected=@($VariantList.SelectedItems);if($selected.Count -ne 1){Show-Error 'Select exactly one generated current-revision local artwork before Re-generate.';return};$wasPrepared=([string](Get-PropertyValue $selected[0] 'provider_key')-ceq'local_birefnet_preparation');try{$source=Resolve-LocalGeneratedArtworkSource $selected[0] $generatedVariants}catch{Show-Error $_.Exception.Message;return};if([string](Get-PropertyValue $source 'concept_revision_id') -ne [string](Get-PropertyValue $c 'current_revision_id')){Show-Error 'The selected artwork belongs to another revision.';return};if(!(Test-LocalProviderArtworkLineage $source)){Show-Error 'Re-generate requires artwork produced by the local provider. Manual imports do not have provider request lineage.';return};$prior=([string](Get-PropertyValue $source 'generation_request_id')).Trim();if([string]::IsNullOrWhiteSpace($prior)){Show-Error 'The selected generated artwork has no exact local provider request lineage. Refresh before Re-generate.';return};$variantLabel=("`nSource artwork SHA: {0}" -f [string](Get-PropertyValue $source 'asset_sha256'));if($wasPrepared){$variantLabel+="`n"+$(switch($script:Locale){'ru'{'История новой генерации связана с исходным эскизом подготовленного кандидата.'}'es'{'La nueva solicitud conserva el vínculo con la vista previa original del candidato preparado.'}default{'The new request keeps the original preview lineage of the prepared candidate.'}})}}
        $cfg=Get-GenerationProviderRuntimeConfig;$dispatchBinding=Get-LocalGenerationDispatchBinding $cfg;$preview=Get-GenerationDispatchPreview $cfg;$firstLiveNote=if([bool](Get-PropertyValue $preview 'first_live_guard_active')){"`n`nFIRST LIVE SAFETY: this Smoke job can make exactly one paid image request and one image. Draft/Final remain locked until this exact result is successfully imported."}else{''};$summary=("{0} exact revision {1}?`n`nProvider: {2}`nProfile: {3}`nModel: {4}`nRender: {5} · {6} · {7} image(s)`nPaid requests today: {8}/{9}`nPre-request dollar cost: not deterministic; actual usage is recorded when returned by the provider.`n`nTitle: {10}`nHook: {11}`nVisual direction: {12}{13}`n`nExactly ONE provider request is allowed for this job. There is NO automatic paid retry. This does not publish or accept anything.{14}" -f $label,[string](Get-PropertyValue $c 'current_revision_no'),[string](Get-PropertyValue $preview 'provider_key'),[string](Get-PropertyValue $preview 'profile_key'),[string](Get-PropertyValue $preview 'model'),[string](Get-PropertyValue $preview 'size'),[string](Get-PropertyValue $preview 'quality'),[int](Get-PropertyValue $preview 'output_count'),[int](Get-PropertyValue $preview 'paid_requests_today'),[int](Get-PropertyValue $preview 'daily_request_limit'),[string](Get-PropertyValue $c 'title'),[string](Get-PropertyValue $c 'hook'),[string](Get-PropertyValue $c 'visual_direction_text'),$variantLabel,$firstLiveNote);if([string](Get-PropertyValue $cfg 'provider_key')-eq'local_comfy_flux2_klein_4b'){$summary='Generate exactly ONE local RGB preview of the approved revision? No paid API. Local ComfyUI only. This is not transparent or print-ready artwork. No automatic retry.'+$variantLabel};if(-not(Confirm $summary ($label+' variants'))){return}
        Set-Busy $true 'Starting local generation worker…';try{$r=Queue-LocalGeneration $kind $prior $dispatchBinding;Refresh-LocalArtworkUi;$StatusText.Text=("Local generation job {0} started in worker process {1}. Reopen Artwork or Refresh to import completed variants." -f [string](Get-PropertyValue (Get-PropertyValue $r 'job') 'job_id'),[string](Get-PropertyValue $r 'worker_pid'))}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local generation could not start.'}finally{Set-Busy $false $StatusText.Text};return
    }
    # forge-app 0.2.70 compiles selected production-spec fields and rejects client
    # snapshot overrides. It cannot forward this entire approved brief. Fail closed;
    # never silently fall back to a lossy server request after local readiness fails.
    Show-Error (Get-UiText 'generation.server.fullbrief.blocked' 'Configure a local image provider to generate the complete approved brief. Server generation is blocked until the server can preserve every field of that brief.')
}

function Cancel-Generation {
    $selected=$GenerationRequestList.SelectedItem
    if($null-ne$selected-and[string](Get-PropertyValue $selected 'request_origin')-ceq'local_worker'){
        $target=Get-LocalGenerationCancellationTarget $selected
        if($null-eq$target){Show-Error (Get-UiText 'generation.cancel.stale' 'The selected local request is stale or does not belong to this exact idea. Refresh its history before cancelling.');return}
        try {
            if((Get-FileSha256Hex $target.job_path)-cne$target.job_sha256){throw 'The selected local request changed; refresh before cancelling.'}
            if(Test-Path -LiteralPath $target.cancel_path){$item=Get-Item -LiteralPath $target.cancel_path -Force;if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Existing cancellation artifact retained; inspect Diagnostics.'}}
            else{$bytes=[Text.Encoding]::UTF8.GetBytes('cancel own local request '+$target.job_id+' '+$target.job_sha256);$stream=[IO.File]::Open($target.cancel_path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}}
            $StatusText.Text=Get-UiText 'generation.cancel.requested' 'Local cancellation requested. Running computation may finish; result will not be imported. No shared process interrupted.'
        } catch {Show-Error $_.Exception.Message}
        return
    }
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; if($null -eq $script:Current){return}; $g=$GenerationRequestList.SelectedItem; if($null -eq $g -or [string](Get-PropertyValue $g 'status') -ne 'queued'){return}
    if([string](Get-PropertyValue $g 'request_origin') -eq 'local_worker'){Show-Error 'Local provider jobs are not server queue requests. Refresh Artwork to see the local worker result; no server cancel action was sent.';return}
    if(-not (Has-Cap 'generate')){Show-Error 'Your workspace role cannot cancel generation requests.';return}
    $c=$script:Current.concept
    if(-not (Confirm ("Cancel queued generation request {0}? Existing variants and earlier runs are preserved." -f $g.request_no),'Cancel generation request')){return}
    Set-Busy $true 'Cancelling queued generation request…'; try { $r=Invoke-ForgeApi 'cancel_generation_request' @{concept_key=$c.concept_key;request_id=$g.id}; Load-Concept ([string]$c.concept_key)|Out-Null; $StatusText.Text=("Generation request {0} cancelled." -f $g.request_no) } catch { Show-Error $_.Exception.Message; $StatusText.Text='Cancel failed' } finally { Set-Busy $false $StatusText.Text }
}
function Save-VariantReview {
    if($null -eq $script:Current){return};$selected=@($VariantList.SelectedItems);if($selected.Count -ne 1){return};$v=$selected[0]
    if([bool](Get-PropertyValue $v 'local_only')){Show-Error 'Local artwork is reviewed through exact Local Accept. No server review event was sent.';return}
    if(-not (Has-Cap 'review')){Show-Error 'Your workspace role cannot review variants.';return}
    if($null -eq $script:ReviewWorkspace){return}
    if($null -ne $v.allowed_actions -and -not [bool]$v.allowed_actions.review){Show-Error 'This variant is not review-ready. Refresh or restore its verified preview first.';return}
    $state=[string]$VariantReviewState.SelectedItem.Content; $reason=[string]$VariantReviewReason.SelectedItem
    if($state -eq 'reject' -and [string]::IsNullOrWhiteSpace($reason)){Show-Error 'Choose a structured reason before rejecting this variant.';return}
    $reasonCodes=if([string]::IsNullOrWhiteSpace($reason)){@()}else{@($reason)}
    $c=$script:Current.concept
    $payloadKey=("review|{0}|{1}|{2}|{3}|{4}|{5}|{6}" -f $c.current_revision_id,$v.id,$state,[string]$v.latest_review_id,[string]$v.latest_review_state,$reason,([string]$VariantReviewNote.Text))
    $idem=Get-OwnerActionIdempotencyKey $payloadKey
    Set-Busy $true 'Saving variant review…'
    try {
        $null=Invoke-ForgeApi 'review_variant_v2' @{
          variant_id=$v.id;review_state=$state;reason_codes=$reasonCodes;note=$VariantReviewNote.Text;
          expected_revision_id=$c.current_revision_id;expected_revision_hash=$c.current_content_hash;
          expected_latest_review_id=([string]$v.latest_review_id);expected_latest_review_state=([string]$v.latest_review_state);
          idempotency_key=$idem;explicit_human_action=$true
        }
        Clear-OwnerActionIdempotencyKey $payloadKey
        Load-Concept ([string]$c.concept_key)|Out-Null
        $StatusText.Text='Variant review saved. Favorite/Reject did not Accept or regenerate anything.'
    } catch { Show-Error $_.Exception.Message; $StatusText.Text='Variant review needs attention; retry reuses the same action key.' }
    finally { Set-Busy $false $StatusText.Text }
}
function Accept-Current {
    if($null -eq $script:Current -or $script:Dirty){return};$c=$script:Current.concept
    $selected=@($VariantList.SelectedItems);if($selected.Count -ne 1){Show-Error 'Select exactly one review-ready visual for Final Accept.';return};$v=$selected[0]
    if([bool](Get-PropertyValue $v 'local_only')){try{if(Set-LocalExactAcceptance $v $false){Refresh-LocalArtworkUi;$StatusText.Text='Exact local artwork accepted for the current revision. Downstream checks were rebound fail-closed.'}}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local artwork acceptance failed.'};return}
    if(-not (Has-Cap 'accept')){Show-Error 'Your workspace role cannot Accept exact versions.';return}
    if($null -eq $script:ReviewWorkspace){return}
    if([bool]$c.current_revision_accepted){Show-Error 'Current revision is already accepted. Reopen it or start a new iteration explicitly.';return}
    if($null -ne $v.allowed_actions -and -not [bool]$v.allowed_actions.accept){Show-Error 'This visual cannot be accepted in its current review/preview state.';return}
    $vid=[string]$v.id; $vsha=[string]$v.asset_sha256
    if([string]::IsNullOrWhiteSpace($vsha)){Show-Error 'Selected visual has no exact SHA-256 identity.';return}
    if(-not (Confirm ("Accept exact design?`n`nConcept: {0}`nRevision: {1}`nVariant: {2}`n`nThis records the exact visual. Favorite is not Accept. This does not authorize Amazon submission." -f $c.title,$c.current_revision_no,$v.variant_index) 'Accept exact visual')){return}
    $expected=[string]$script:ReviewWorkspace.workspace.active_acceptance_id
    $payloadKey=("accept|{0}|{1}|{2}|{3}" -f $c.current_revision_id,$vid,$vsha,$expected)
    $idem=Get-OwnerActionIdempotencyKey $payloadKey
    Set-Busy $true 'Saving exact visual acceptance…'
    try {
        $null=Invoke-ForgeApi 'accept_visual_v2' @{
          concept_key=$c.concept_key;revision_id=$c.current_revision_id;revision_hash=$c.current_content_hash;
          variant_id=$vid;variant_sha256=$vsha;expected_active_acceptance_id=$expected;
          idempotency_key=$idem;explicit_human_action=$true;note='Accepted from Theme 9 Workbench candidate'
        }
        Clear-OwnerActionIdempotencyKey $payloadKey
        Load-Concept ([string]$c.concept_key)|Out-Null
        $StatusText.Text='Exact visual accepted. External submission remains locked.'
    } catch { Show-Error $_.Exception.Message; $StatusText.Text='Accept needs attention; retry reuses the same action key.' }
    finally { Set-Busy $false $StatusText.Text }
}
function Reopen-CurrentAcceptance {
    if($null-ne$script:LocalReopenTarget){
        try{if(Reopen-LocalExactAcceptance $script:LocalReopenTarget ([string]$ReopenReasonBox.Text)){$StatusText.Text='Local acceptance withdrawn. Artwork, archives and historical receipts were preserved; no new revision or publication was created.'}}
        catch{Show-Error $_.Exception.Message;$StatusText.Text='Local Reopen needs attention; refresh to verify the current acceptance.'}
        return
    }
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; if(-not (Has-Cap 'accept')){Show-Error 'Your workspace role cannot Reopen acceptances.';return}
    if($null -eq $script:Current -or $script:Dirty -or $null -eq $script:ReviewWorkspace){return}; if($script:PublicationDirty){if(-not (Confirm 'Reopening acceptance discards unsaved publication metadata. Continue?')){return};Set-PublicationDirty $false}; $c=$script:Current.concept
    $acceptanceId=[string]$script:ReviewWorkspace.workspace.active_acceptance_id
    if([string]::IsNullOrWhiteSpace($acceptanceId)){return}
    $reason=([string]$ReopenReasonBox.Text).Trim(); if([string]::IsNullOrWhiteSpace($reason)){Show-Error 'Enter a reason before reopening the current acceptance.';return}
    if(-not (Confirm ("Reopen accepted revision {0}?`n`nReason: {1}`n`nThis withdraws the current acceptance but does not create a new iteration or publish anything." -f $c.current_revision_no,$reason) 'Reopen exact acceptance')){return}
    $payloadKey=("reopen|{0}|{1}|{2}" -f $c.current_revision_id,$acceptanceId,$reason); $idem=Get-OwnerActionIdempotencyKey $payloadKey
    Set-Busy $true 'Reopening exact acceptance…'
    try {
        $null=Invoke-ForgeApi 'reopen_acceptance_v2' @{concept_key=$c.concept_key;acceptance_id=$acceptanceId;expected_revision_id=$c.current_revision_id;expected_revision_hash=$c.current_content_hash;reason=$reason;idempotency_key=$idem;explicit_human_action=$true}
        Clear-OwnerActionIdempotencyKey $payloadKey
        Load-Concept ([string]$c.concept_key)|Out-Null
        $StatusText.Text='Acceptance reopened; no new iteration was created.'
    } catch { Show-Error $_.Exception.Message; $StatusText.Text='Reopen needs attention; retry reuses the same action key.' }
    finally { Set-Busy $false $StatusText.Text }
}
function Get-ForgeIterationActionKey($Payload) {
    # Keep the existing 32-hex format, derived from the complete exact action.
    # Reopening/restarting cannot allocate a different key for the same transition.
    # The outer action wrapper does not consume the already validated spec depth budget.
    return (Get-StringSha256Hex (ConvertTo-ForgeBriefCanonicalJson $Payload -1)).Substring(0,32)
}
function Start-NewIteration([string]$Mode) {
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}
    if(-not(Has-Cap 'edit')){Show-Error 'Your workspace role cannot start a new iteration.';return}
    if($null-eq$script:Current-or$null-eq$script:ReviewWorkspace){return}
    $view=Get-ForgeLocalRefreshView;$sent=$false;$acknowledged=$false;$failed=$false
    try{
        if($Mode-cnotin@('same_brief','edit_brief')){throw 'Choose a supported iteration mode.'}
        $c=$script:Current.concept;$acceptanceId=[string]$script:ReviewWorkspace.workspace.active_acceptance_id
        if([string]::IsNullOrWhiteSpace($acceptanceId)){throw 'A current accepted visual is required before starting an accepted-history iteration.'}
        $patch=@{};$dirty=@{};$proposed=New-ForgeGenerationBriefSnapshot $c
        if($Mode-ceq'edit_brief'){
            $editedSpec=ConvertFrom-ForgeProductionSpecJson ([string]$SpecBox.Text);$patch=Build-Patch;$dirty=Get-ProductionSpecDirtyValues $c.production_spec $editedSpec
            foreach($field in $patch.Keys){Add-OrSetProperty $proposed $field $patch[$field]};$proposed.production_spec=$editedSpec
            if((Get-ForgeBriefSha256 $proposed)-ceq(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $c))){throw 'Edit the brief first, then start the edited iteration.'}
        }elseif($script:Dirty){throw 'You have unsaved edits. Use Start new iteration - edited brief or discard the edits.'}
        $label=if($Mode-ceq'same_brief'){'same brief'}else{'edited brief'}
        $listingWarning=if($script:PublicationDirty){Get-UiText 'iteration.listing_discard' ' Unsaved publication metadata will be discarded.'}else{''}
        if(!(Confirm (("Start a new iteration with {0}?`n`nThe accepted revision {1} stays in history. A new unaccepted current revision is created. No image generation starts automatically."-f$label,$c.current_revision_no)+$listingWarning) 'Start new iteration')){return $false}
        $payload=@{concept_key=$c.concept_key;expected_revision_id=$c.current_revision_id;expected_revision_hash=$c.current_content_hash;expected_acceptance_id=$acceptanceId;mode=$Mode;patch=$patch;production_spec_dirty_values=$dirty;explicit_human_action=$true}
        $payload.idempotency_key=Get-ForgeIterationActionKey $payload
        Set-Busy $true 'Starting new iteration.'
        $ownerLanguageNotice=Format-ForgeOwnerLanguageReview $proposed
        $intent=Start-ForgeSourceSaveIntent $proposed
        $sent=$true;$null=Invoke-ForgeApi 'start_review_iteration' $payload;$acknowledged=$true
        $opened=@(Load-Concept ([string]$c.concept_key) $true $intent.proposed_brief_sha256 ([string]$c.current_revision_id))
        if(!(@($opened|Where-Object{$_-is[bool]-and$_}).Count)){throw 'New iteration source could not be reopened.'}
        $saved=Get-LocalCoreConcept ([string]$c.concept_key)
        if($null-ne(Get-PropertyValue $saved 'source_save_intent')){throw 'Iteration source remains unresolved.'}
        Set-Dirty $false;Set-PublicationDirty $false
        $StatusText.Text='New iteration created and reloaded. Previous accepted visual remains in history; generation did not start.'
        return $true
    }catch{
        $failed=$true;$failure=$_.Exception.Message;Restore-ForgeLocalRefreshView $view;Write-AppLog 'WARN' ('Iteration outcome: '+$failure)
        $message=if($acknowledged){Get-UiText 'iteration.ack_unverified' 'The server acknowledged the iteration, but the new unaccepted full brief could not be verified. Your edits were preserved. Refresh the saved idea before retrying; generation did not start.'}elseif($sent){Get-UiText 'iteration.unverified' 'The iteration outcome could not be verified. Your edits were preserved. Refresh the saved idea before retrying; no automatic repeat or generation started.'}else{$failure}
        Show-Error $message;$StatusText.Text=$message;return $false
    }finally{Set-Busy $false $StatusText.Text;if($failed){Set-ForgeLocalReadUnavailable;$StatusText.Text=$message}}
}
