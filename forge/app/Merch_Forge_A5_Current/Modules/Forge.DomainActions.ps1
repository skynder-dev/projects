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
function Save-PublicationMetadata {
    if($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core')){Save-LocalPublicationMetadata;return}
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; 
    if(-not (Has-Cap 'prepare_publication')){Show-Error 'Your workspace role cannot edit publication metadata.';return}
    if($null -eq $script:Current -or $null -eq $script:Publication -or -not $script:PublicationDirty){return}; $c=$script:Current.concept; $w=$script:Publication.workspace
    if(-not [bool]$w.current_revision_accepted -or [string]::IsNullOrWhiteSpace([string]$w.current_acceptance_id)){Show-Error 'Accept a design version before saving listing details.';return}
    $title=([string]$PublicationTitleBox.Text).Trim(); if([string]::IsNullOrWhiteSpace($title)){Show-Error 'Listing title is required.';return}
    $keywords=@(); foreach($k in (([string]$PublicationKeywordsBox.Text) -split '[,;]')){$t=$k.Trim();if($t){$keywords+=$t}}
    $payload=@{listing_title=$title;brand=$PublicationBrandBox.Text;bullet_1=$PublicationBullet1Box.Text;bullet_2=$PublicationBullet2Box.Text;description=$PublicationDescriptionBox.Text;keywords=$keywords;locale=(Get-PublicationLocale)}
    Set-Busy $true 'Saving listing version…'; try { $null=Invoke-ForgeApi 'save_publication_metadata' @{concept_key=$c.concept_key;expected_acceptance_id=$w.current_acceptance_id;expected_metadata_revision_id=([string]$w.current_metadata_revision_id);expected_metadata_content_hash=([string]$w.metadata_content_hash);payload=$payload;edit_reason=$PublicationReasonBox.Text}; Set-PublicationDirty $false; Load-Publication ([string]$c.concept_key); $StatusText.Text='Listing version saved; accepted design unchanged.' } catch { $technical=$_.Exception.Message; Write-AppLog 'ERROR' ("Publication metadata save failed: {0}" -f $technical); $human=if($technical -match 'Accepted creative lineage changed'){'The accepted design changed. Refresh Publication before saving.'}elseif($technical -match 'changed in another client|HTTP 409'){'This listing changed somewhere else. Refresh Publication before saving.'}else{Get-HumanErrorMessage $technical}; Set-LastDiagnostic 'publication_save' 0 'refresh_before_retry' $technical $human; [System.Windows.MessageBox]::Show($Window,("{0}`n`nTechnical details are available in Diagnostics." -f $human),'Merch Forge — Listing',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Warning)|Out-Null; $StatusText.Text='Listing save needs attention' } finally { Set-Busy $false $StatusText.Text }
}
function Save-Revision {
    if(Test-CurrentIsResearchDraft){Save-CurrentResearchDraftRevision;return}
    if(-not (Has-Cap 'edit')){Show-Error 'Your workspace role cannot edit concepts.';return}
    if($null -eq $script:Current){return}; if([bool]$script:Current.concept.current_revision_accepted){Show-Error 'This revision is accepted. Use Start new iteration · edited brief so the accepted version stays in history.';return}; if($script:PublicationDirty){if(-not (Confirm 'Saving a new creative revision invalidates the current publication context and discards unsaved publication metadata. Continue?')){return};Set-PublicationDirty $false}; Set-Busy $true 'Saving new revision…'
    try { $c=$script:Current.concept; $editedSpec=$null; try { $editedSpec=$SpecBox.Text|ConvertFrom-Json -ErrorAction Stop } catch { throw 'Production spec must be valid JSON.' }; $patch=Build-Patch; $dirty=Get-ProductionSpecDirtyValues $c.production_spec $editedSpec; $payload=@{concept_key=$c.concept_key;expected_revision_id=$c.current_revision_id;expected_content_hash=$c.current_content_hash;patch=$patch;production_spec_dirty_values=$dirty;edit_reason=$ReasonBox.Text}; if($script:RestoreSourceRevisionId){$payload.source_revision_id=$script:RestoreSourceRevisionId}; $r=Invoke-ForgeApi 'save_revision' $payload; Set-Dirty $false; Load-Concept ([string]$c.concept_key)|Out-Null; $StatusText.Text=("Saved revision {0}" -f $r.revision.revision_no) } catch { Show-Error $_.Exception.Message; $StatusText.Text='Save failed' } finally { Set-Busy $false $StatusText.Text }
}
function Queue-Generation {
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.generate.blocked' 'Research drafts cannot be generated from Forge yet. Use Export brief (no dispatch) and import the finished artwork.');return}
    if($null -ne $script:Current){try{$null=Sync-LocalGenerationResults}catch{Write-AppLog 'WARN' ('Pre-generate local result recovery failed: '+$_.Exception.Message)}}
    $localCfg=Get-GenerationProviderRuntimeConfig;$localReadiness=Get-GenerationProviderLocalReadiness;$localEnabled=[bool](Get-PropertyValue $localCfg 'enabled');$localReady=[bool](Get-PropertyValue $localReadiness 'ready')
    if($localEnabled -and -not $localReady){$code=[string](Get-PropertyValue $localReadiness 'code');$detail=if($code -eq 'daily_request_limit_reached'){('Daily provider request ceiling reached: {0}/{1}. Increase the ceiling explicitly in Configure Image Provider, or wait for the next UTC day.' -f [int](Get-PropertyValue $localReadiness 'paid_requests_today'),[int](Get-PropertyValue $localReadiness 'daily_request_limit'))}elseif($code -eq 'credential_missing'){'The local image provider is enabled but its credential is missing. Run Configure Image Provider or set OPENAI_API_KEY.'}elseif($code -eq 'unsafe_config'){'The local image provider configuration failed its safety contract. Run Configure Image Provider again.'}else{('The local image provider is enabled but not ready: '+$code)};Show-Error $detail;return}
    if($localReady){
        if($null -eq $script:Current -or $script:Dirty){return};$c=$script:Current.concept;if([bool](Get-PropertyValue $c 'current_revision_accepted')){Show-Error 'Accepted revisions are frozen. Start a new iteration before generating again.';return}
        $jobs=@(Get-LocalGenerationJobsForCurrent);$pendingImport=@($jobs|Where-Object{$_.status -eq 'completed_pending_import'});if($pendingImport.Count -gt 0){Show-Error ('A completed provider result is waiting for verified import/recovery before another paid request can start: '+[string]$pendingImport[0].id+'. Use Refresh; if it remains blocked, review Diagnostics instead of generating again.');return};$ambiguous=@($jobs|Where-Object{$_.status -eq 'ambiguous'});if($ambiguous.Count -gt 0){$a=$ambiguous[0];$warn=("The latest paid provider request {0} has an unknown outcome. There are {1} unresolved ambiguous request(s) in this revision chain. No automatic retry was attempted. Starting another request may incur another charge.`n`nStart ONE new explicit generation request anyway?" -f [string]$a.id,$ambiguous.Count);if(-not(Confirm $warn 'Provider outcome unknown')){return};Set-Busy $true 'Starting explicit generation after ambiguous provider outcome…';try{$r=Queue-LocalGeneration 'generate' ([string]$a.id);Refresh-LocalArtworkUi;$StatusText.Text=("New explicit generation job {0} started after ambiguous job {1}." -f [string](Get-PropertyValue (Get-PropertyValue $r 'job') 'job_id'),[string]$a.id)}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local generation could not start.'}finally{Set-Busy $false $StatusText.Text};return};$localVariants=@(Get-LocalCoreVariantsForCurrent);$generatedVariants=@($localVariants|Where-Object{[string](Get-PropertyValue $_ 'generation_method') -eq 'local_provider_worker' -and -not[string]::IsNullOrWhiteSpace(([string](Get-PropertyValue $_ 'generation_request_id')).Trim())});$kind=if($generatedVariants.Count){'regenerate'}else{'generate'};$label=if($kind-eq'regenerate'){'Re-generate'}else{'Generate'};$prior='';$variantLabel=''
        if($kind -eq 'regenerate'){$selected=@($VariantList.SelectedItems);if($selected.Count -ne 1){Show-Error 'Select exactly one generated current-revision local artwork before Re-generate.';return};$source=$selected[0];if([string](Get-PropertyValue $source 'concept_revision_id') -ne [string](Get-PropertyValue $c 'current_revision_id')){Show-Error 'The selected artwork belongs to another revision.';return};if([string](Get-PropertyValue $source 'generation_method') -ne 'local_provider_worker'){Show-Error 'Re-generate requires artwork produced by the local provider. Manual imports do not have provider request lineage.';return};$prior=([string](Get-PropertyValue $source 'generation_request_id')).Trim();if([string]::IsNullOrWhiteSpace($prior)){Show-Error 'The selected generated artwork has no exact local provider request lineage. Refresh before Re-generate.';return};$variantLabel=("`nSource artwork SHA: {0}" -f [string](Get-PropertyValue $source 'asset_sha256'))}
        $cfg=Get-GenerationProviderRuntimeConfig;$preview=Get-GenerationDispatchPreview;$firstLiveNote=if([bool](Get-PropertyValue $preview 'first_live_guard_active')){"`n`nFIRST LIVE SAFETY: this Smoke job can make exactly one paid image request and one image. Draft/Final remain locked until this exact result is successfully imported."}else{''};$summary=("{0} exact revision {1}?`n`nProvider: {2}`nProfile: {3}`nModel: {4}`nRender: {5} · {6} · {7} image(s)`nPaid requests today: {8}/{9}`nPre-request dollar cost: not deterministic; actual usage is recorded when returned by the provider.`n`nTitle: {10}`nHook: {11}`nVisual direction: {12}{13}`n`nExactly ONE provider request is allowed for this job. There is NO automatic paid retry. This does not publish or accept anything.{14}" -f $label,[string](Get-PropertyValue $c 'current_revision_no'),[string](Get-PropertyValue $preview 'provider_key'),[string](Get-PropertyValue $preview 'profile_key'),[string](Get-PropertyValue $preview 'model'),[string](Get-PropertyValue $preview 'size'),[string](Get-PropertyValue $preview 'quality'),[int](Get-PropertyValue $preview 'output_count'),[int](Get-PropertyValue $preview 'paid_requests_today'),[int](Get-PropertyValue $preview 'daily_request_limit'),[string](Get-PropertyValue $c 'title'),[string](Get-PropertyValue $c 'hook'),[string](Get-PropertyValue $c 'visual_direction_text'),$variantLabel,$firstLiveNote);if(-not(Confirm $summary ($label+' variants'))){return}
        Set-Busy $true 'Starting local generation worker…';try{$r=Queue-LocalGeneration $kind $prior;Refresh-LocalArtworkUi;$StatusText.Text=("Local generation job {0} started in worker process {1}. Reopen Artwork or Refresh to import completed variants." -f [string](Get-PropertyValue (Get-PropertyValue $r 'job') 'job_id'),[string](Get-PropertyValue $r 'worker_pid'))}catch{Show-Error $_.Exception.Message;$StatusText.Text='Local generation could not start.'}finally{Set-Busy $false $StatusText.Text};return
    }
    if(-not (Has-Cap 'generate')){Show-Error 'No production image provider is configured locally, and the live workspace cannot authorize generation. Use the manual artwork bridge or configure an image provider.';return}
    if($null -eq $script:Current -or $script:Dirty){return}; $c=$script:Current.concept
    if([bool]$c.current_revision_accepted){Show-Error 'Accepted revisions are frozen. Start a new iteration before generating again.';return}
    if($null -ne $script:ReviewWorkspace -and -not [bool]$script:ReviewWorkspace.workspace.allowed_actions.generate_or_regenerate_same_revision){Show-Error 'Generation is not available for the current review state. Refresh the workspace.';return}
    $kind=if(@($script:Current.generation_requests).Count){'regenerate'}else{'generate'}
    $label=if($kind -eq 'regenerate'){'Re-generate'}else{'Generate'}
    $priorRequestId=''
    $variantLabel=''
    if($kind -eq 'regenerate'){
        $selected=@($VariantList.SelectedItems)
        if($selected.Count -ne 1){Show-Error 'Select exactly one current-revision variant before Re-generate so lineage stays exact.';return}
        $sourceVariant=$selected[0]
        if([string]$sourceVariant.concept_revision_id -ne [string]$c.current_revision_id){Show-Error 'The selected variant belongs to another revision. Refresh before Re-generate.';return}
        $priorRequestId=([string]$sourceVariant.generation_request_id).Trim()
        if([string]::IsNullOrWhiteSpace($priorRequestId)){Show-Error 'The selected variant has no exact generation request lineage. Refresh before Re-generate.';return}
        $variantLabel=("`nSource variant: {0}`nPrior generation request: {1}" -f $sourceVariant.variant_index,$priorRequestId)
    }
    $summary=("{0} exact revision {1}?`n`nTitle: {2}`nHook: {3}`nVisual direction: {4}{5}`n`nThis records your explicit {0} intent for this saved revision. Existing runs/variants are preserved. It does not publish anything." -f $label,$c.current_revision_no,$c.title,$c.hook,$c.visual_direction_text,$variantLabel)
    if(-not (Confirm $summary,("{0} variants" -f $label))){return}
    $idemScope=("{0}|{1}|{2}" -f $c.current_revision_id,$kind,$priorRequestId)
    $idem=Get-GenerationIdempotencyKey ([string]$c.concept_key) $idemScope; $accepted=$false
    Set-Busy $true 'Queueing generation request…'
    try {
        $payload=@{concept_key=$c.concept_key;revision_id=$c.current_revision_id;expected_content_hash=$c.current_content_hash;idempotency_key=$idem;request_kind=$kind;explicit_human_action=$true}
        if($kind -eq 'regenerate'){$payload.prior_request_id=$priorRequestId}
        $r=Invoke-ForgeApi 'create_generation_request' $payload; $accepted=$true
        Load-Concept ([string]$c.concept_key)|Out-Null
        Clear-GenerationIdempotencyKey
        $StatusText.Text=("Generation request {0} queued." -f $r.request.request_no)
    } catch {
        $technical=$_.Exception.Message
        if($accepted){
            $human='The generation request was accepted, but the workspace could not refresh it. Refresh and try again; Merch Forge will safely reuse the same request.'
            Write-AppLog 'ERROR' ("Generation post-create refresh failed: {0}" -f $technical); Set-LastDiagnostic 'generation_refresh' 0 'refresh_then_retry_same_request' $technical $human
            [System.Windows.MessageBox]::Show($Window,("{0}`n`nTechnical details are available in Diagnostics." -f $human),'Merch Forge — Generation',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Warning)|Out-Null
            $StatusText.Text='Generation request accepted; refresh needed'
        } else {
            $human=Get-HumanErrorMessage $technical
            $uncertain=($technical -match 'timed out|timeout|name resolution|unable to connect|connection.*failed|network|offline|no such host')
            if($uncertain){$human='Merch Forge could not confirm whether the generation request was received. Try again; it will safely reuse the same request.'}
            $diagAction=if($uncertain){'retry_same_request'}else{'review_and_retry_same_request'}; Write-AppLog 'ERROR' ("Generation request needs attention: {0}" -f $technical); Set-LastDiagnostic 'generation_request' 0 $diagAction $technical $human
            [System.Windows.MessageBox]::Show($Window,("{0}`n`nTechnical details are available in Diagnostics." -f $human),'Merch Forge — Generation',[System.Windows.MessageBoxButton]::OK,[System.Windows.MessageBoxImage]::Warning)|Out-Null
            $StatusText.Text='Generation request needs attention'
        }
    } finally { Set-Busy $false $StatusText.Text }
}
function Cancel-Generation {
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
function Start-NewIteration([string]$Mode) {
    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; if(-not (Has-Cap 'edit')){Show-Error 'Your workspace role cannot start a new iteration.';return}
    if($null -eq $script:Current -or $null -eq $script:ReviewWorkspace){return}; $c=$script:Current.concept
    $acceptanceId=[string]$script:ReviewWorkspace.workspace.active_acceptance_id
    if([string]::IsNullOrWhiteSpace($acceptanceId)){Show-Error 'A current accepted visual is required before starting an accepted-history iteration.';return}
    $patch=@{}; $dirty=@{}
    if($Mode -eq 'edit_brief'){
        $editedSpec=$null; try{$editedSpec=$SpecBox.Text|ConvertFrom-Json -ErrorAction Stop}catch{Show-Error 'Production spec must be valid JSON.';return}
        $patch=@{title=$TitleBox.Text;hook=$HookBox.Text;concept_text=$ConceptTextBox.Text;target_buyer=$BuyerBox.Text;purchase_reason=$PurchaseBox.Text;differentiation=$DifferentiationBox.Text;visual_direction_text=$VisualBox.Text}
        $dirty=Get-ProductionSpecDirtyValues $c.production_spec $editedSpec
        if(-not $script:Dirty -and $dirty.Count -eq 0){Show-Error 'Edit the brief first, then start the edited iteration.';return}
    } else {
        if($script:Dirty){Show-Error 'You have unsaved edits. Use Start new iteration · edited brief or discard the edits.';return}
    }
    $label=if($Mode -eq 'same_brief'){'same brief'}else{'edited brief'}
    if(-not (Confirm ("Start a new iteration with {0}?`n`nThe accepted revision {1} stays in history. A new unaccepted current revision is created. No image generation starts automatically." -f $label,$c.current_revision_no) 'Start new iteration')){return}
    $payloadKey=("iterate|{0}|{1}|{2}|{3}|{4}" -f $c.current_revision_id,$acceptanceId,$Mode,($patch|ConvertTo-Json -Depth 20 -Compress),($dirty|ConvertTo-Json -Depth 20 -Compress))
    $idem=Get-OwnerActionIdempotencyKey $payloadKey
    Set-Busy $true 'Starting new iteration…'
    try {
        $null=Invoke-ForgeApi 'start_review_iteration' @{concept_key=$c.concept_key;expected_revision_id=$c.current_revision_id;expected_revision_hash=$c.current_content_hash;expected_acceptance_id=$acceptanceId;mode=$Mode;patch=$patch;production_spec_dirty_values=$dirty;idempotency_key=$idem;explicit_human_action=$true}
        Clear-OwnerActionIdempotencyKey $payloadKey
        Set-Dirty $false
        Load-Concept ([string]$c.concept_key)|Out-Null
        $StatusText.Text='New iteration created. Previous accepted visual remains in history; generation did not start.'
    } catch { Show-Error $_.Exception.Message; $StatusText.Text='New iteration needs attention; retry reuses the same action key.' }
    finally { Set-Busy $false $StatusText.Text }
}
