# Merch Forge · Research -> concept draft self-test (headless)
# Runs the REAL Forge functions (workbench functions are extracted with the PowerShell parser, modules are dot-sourced)
# against an isolated temporary state root. WPF controls are replaced by inert property bags.
# Proof boundary: logic + persistence + authority guards. This is NOT a native WPF click/visual test.
# Network: Invoke-ForgeApi / Invoke-RestMethod / Invoke-WebRequest are replaced by recorders; any call fails the test.
param(
    [string]$PackageRoot = $PSScriptRoot,
    [string]$OutputPath = '',
    [ValidateSet('driver','create','restart','legacy054')][string]$Phase = 'driver',
    [string]$StateRoot = '',
    [string]$LegacyPackageRoot = ''
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function New-Report([string]$Name) { return [ordered]@{phase=$Name;checks=[ordered]@{};notes=@();api_calls=0;network_calls=0} }
$script:R = New-Report $Phase
function Check([string]$Name,[bool]$Ok,[string]$Detail='') { $script:R.checks[$Name]=[ordered]@{pass=$Ok;detail=$Detail} }

if($Phase -eq 'driver'){
    $exe=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    $tmpRoot=Join-Path ([IO.Path]::GetTempPath()) ('MerchForge-rdtest-'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmpRoot -Force | Out-Null
    $phases=@('create','restart'); if($LegacyPackageRoot){$phases+='legacy054'}
    $all=[ordered]@{}; $ok=$true; $api=0; $net=0
    foreach($ph in $phases){
        $out=Join-Path $tmpRoot ("$ph.json")
        $argList=@('-NoLogo','-NoProfile','-NonInteractive','-File',$PSCommandPath,'-PackageRoot',$PackageRoot,'-Phase',$ph,'-StateRoot',(Join-Path $tmpRoot 'state'),'-OutputPath',$out)
        if($LegacyPackageRoot){$argList+=@('-LegacyPackageRoot',$LegacyPackageRoot)}
        $log=& $exe @argList 2>&1 | Out-String
        if(-not (Test-Path -LiteralPath $out)){ $all[$ph]=[ordered]@{error='phase produced no report';log=$log}; $ok=$false; continue }
        $j=Get-Content -LiteralPath $out -Raw -Encoding UTF8 | ConvertFrom-Json
        $all[$ph]=$j; $api+=[int]$j.api_calls; $net+=[int]$j.network_calls
        foreach($p in $j.checks.PSObject.Properties){ if(-not [bool]$p.Value.pass){$ok=$false} }
        if($j.PSObject.Properties['fatal']){$ok=$false}
    }
    $total=0;$passed=0;foreach($ph in $all.Keys){$j=$all[$ph];if($j -is [System.Collections.IDictionary]){continue};foreach($p in $j.checks.PSObject.Properties){$total++;if([bool]$p.Value.pass){$passed++}}}
    if($api -ne 0 -or $net -ne 0){$ok=$false}
    $report=[ordered]@{
        schema='forge.research_draft_selftest.v1'; status=$(if($ok){'PASS'}else{'FAIL'}); passed=$passed; total=$total
        api_calls=$api; network_calls=$net; billable_requests=0; backend_mutations=0
        proof_boundary='Headless PowerShell execution of the real Forge functions with inert WPF control stubs and an isolated state root. Restart persistence is proven across separate PowerShell processes. Native Windows WPF rendering/click behaviour is NOT covered by this test.'
        powershell=$PSVersionTable.PSVersion.ToString(); platform=[Environment]::OSVersion.VersionString
        executed_at=[DateTime]::UtcNow.ToString('o'); phases=$all
    }
    $json=$report | ConvertTo-Json -Depth 30
    if($OutputPath){[IO.File]::WriteAllText($OutputPath,$json,(New-Object Text.UTF8Encoding($false)))}
    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output ("RESEARCH DRAFT SELFTEST {0}: {1}/{2} checks; api_calls={3}; network_calls={4}" -f $report.status,$passed,$total,$api,$net)
    if($ok){exit 0}else{exit 1}
}

# ---------------- phase setup: load real code ----------------
try {
$root = if($Phase -eq 'legacy054'){$LegacyPackageRoot}else{$PackageRoot}
$wbPath = Join-Path $root 'MerchForgeWorkbench.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($wbPath,[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw ('Workbench parse failed: '+(@($errors)[0].Message))}
foreach($f in $ast.FindAll({param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false)){ . ([scriptblock]::Create($f.Extent.Text)) }
foreach($a in $ast.FindAll({param($a) $a -is [System.Management.Automation.Language.AssignmentStatementAst]},$false)){
    $left=$a.Left.Extent.Text
    if($left -in @('$script:UiText','$script:StaticUiTranslations','$script:SupportedLocales')){ . ([scriptblock]::Create($a.Extent.Text)) }
}
$controlNames=@([regex]::Matches((Get-Content -LiteralPath $wbPath -Raw -Encoding UTF8),"\`$(\w+)=X '(\w+)'") | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
function New-Ctl { return [pscustomobject]@{Text='';Content='';IsEnabled=$true;Visibility='Visible';FontWeight='Normal';BorderBrush=$null;Background=$null;Foreground=$null;IsReadOnly=$false;ItemsSource=$null;SelectedItem=$null;SelectedIndex=-1;Items=@();SelectedItems=@();ToolTip=$null;Tag=$null} }
foreach($n in $controlNames){ Set-Variable -Name $n -Value (New-Ctl) -Scope Script }
$script:Window=[pscustomobject]@{}; $script:Window | Add-Member -MemberType ScriptMethod -Name FindResource -Value { param($k) return $k }
$script:MainTabs=New-Ctl

$mod=Join-Path $root 'Modules'
foreach($m in @('Forge.Media.ps1','Forge.LocalCore.ps1','Forge.ProductNavigation.ps1','Forge.Localization.ps1','Forge.Gates.ps1','Forge.DataViews.ps1','Forge.DomainActions.ps1')){ . (Join-Path $mod $m) }
$hasDraftModule = Test-Path -LiteralPath (Join-Path $mod 'Forge.ResearchDrafts.ps1')
if($hasDraftModule){ . (Join-Path $mod 'Forge.ResearchDrafts.ps1') }

# state root isolation
$script:StateRoot=$StateRoot; $script:LogRoot=Join-Path $StateRoot 'logs'; $script:RuntimeLogPath=Join-Path $script:LogRoot 'runtime.log'
$script:LocalCoreRoot=Join-Path $StateRoot 'local-core-v1'; $script:LocalCoreStatePath=Join-Path $script:LocalCoreRoot 'state.json'; $script:LocalCoreBackupPath=Join-Path $script:LocalCoreRoot 'state.lastgood.json'
$script:LocalCoreArtworkRoot=Join-Path $script:LocalCoreRoot 'artwork'; $script:LocalCorePackageRoot=Join-Path $script:LocalCoreRoot 'packages'; $script:LocalCoreExportRoot=Join-Path $script:LocalCoreRoot 'exports'; $script:LocalCoreImportRoot=Join-Path $script:LocalCoreRoot 'imports'
$script:QueueSnapshotPath=Join-Path $StateRoot 'queue-snapshot.json'; $script:EmbeddedIdeasPath=Join-Path (Join-Path $root 'Data') 'Forge.LastKnownIdeas.json'
foreach($p in @($script:LocalCoreRoot,$script:LocalCoreArtworkRoot,$script:LocalCorePackageRoot,$script:LocalCoreExportRoot,$script:LocalCoreImportRoot)){ if(-not (Test-Path -LiteralPath $p)){New-Item -ItemType Directory -Path $p -Force | Out-Null} }
$script:Locale='en'; $script:Queue=@(); $script:Current=$null; $script:Dirty=$false; $script:Busy=$false; $script:PublicationDirty=$false; $script:Session=$null; $script:OfflineMode=$false; $script:OfflineSnapshotMode=$false
$script:ProductSection='discover'; $script:LocalGenerationProviderMode='manual_artwork_bridge'; $script:BackendVersion='0.2.70'; $script:ReviewWorkspace=$null; $script:Delivery=$null; $script:Publication=$null; $script:RestoreSourceRevisionId=$null; $script:PendingOwnerActionKeys=@{}
$script:ConceptLoadInProgress=$false; $script:DiscoverSnapshot=$null; $script:DiscoverLoadedAt=$null; $script:ConnectionState='Connected'

# stubs: UI routing / dialogs / network recorders
$script:Errors=New-Object System.Collections.Generic.List[string]; $script:Sections=New-Object System.Collections.Generic.List[string]
function Show-Error([string]$Message){ $script:Errors.Add($Message) }
function Confirm([string]$Message,[string]$Title=''){ return $true }
function Write-AppLog([string]$Level,[string]$Message){}
function Invoke-ForgeApi([string]$Action,[hashtable]$Payload=@{}){ $script:R.api_calls++; throw ('TEST: API call attempted: '+$Action) }
function Invoke-RestMethod { $script:R.network_calls++; throw 'TEST: network call attempted' }
function Invoke-WebRequest { $script:R.network_calls++; throw 'TEST: network call attempted' }
function Show-ProductSection([string]$Section){ $script:ProductSection=$Section; $script:Sections.Add($Section) }
function Select-MainTab([string]$H){}; function Update-MainTabUi{}; function Update-ResponsiveLayout{}; function Set-QueueEmptyState($c){}
function Update-AcceptanceControls{}; function Update-CancelGenerationState{}; function Update-PackageButtons{}
function Test-LocalProductionProviderReady { return $false }
function Sync-LocalGenerationResults { return $null }  # local result import only; no network

$FilterBox.SelectedItem=[pscustomobject]@{Tag=''}; $SortBox.SelectedItem=[pscustomobject]@{Tag='score'}; $SearchBox.Text=''
if($hasDraftModule){ Register-ResearchDraftUiText }

function Get-Fixture {
    # Labeled test fixture shaped like forge.discover_snapshot.v1. Not market data.
    $n1=[pscustomobject]@{niche_id='fixture-niche-nurses';name='TEST FIXTURE · Night-shift nurses';category='profession';audience='ICU and ER nurses on night rotation';score_total=8.4;score_confidence=72;concept_count=3;research_summary='Fixture summary: recurring humor about night shifts and coffee.';dimensions=[pscustomobject]@{demand=8.1;competition=6.2;evergreen=9.0;ip_risk=2.0}}
    $n2=[pscustomobject]@{niche_id='fixture-niche-welders';name='TEST FIXTURE · Pipe welders';category='trade';audience='Union pipe welders';score_total=7.1;score_confidence=60;concept_count=0;research_summary='Fixture summary: pride and safety culture.';dimensions=[pscustomobject]@{demand=7.0}}
    return [pscustomobject]@{contract='forge.discover_snapshot.v1';stats=[pscustomobject]@{niches=2;research_notes=3;active_sources=2;concepts=3}
        niches=@($n1,$n2)
        notes=@([pscustomobject]@{id='fixture-note-1';niche_id='fixture-niche-nurses';topic='Shift humor';conclusion='Fixture: night-shift jokes recur across forums.'},[pscustomobject]@{id='fixture-note-2';niche_id='fixture-niche-welders';topic='Safety';conclusion='Fixture: welders value safety pride.'},[pscustomobject]@{id='fixture-note-3';topic='Unlinked';conclusion='Fixture: note without niche link must not be attached.'})
        sources=@([pscustomobject]@{id='fixture-src-1';name='Fixture source A';source_class='forum'},[pscustomobject]@{id='fixture-src-2';name='Fixture source B';source_class='marketplace'})}
}
function Find-QueueItem([string]$Key){ foreach($i in @($script:Queue)){ if([string]$i.concept_key -eq $Key){return $i} }; return $null }
$script:KeyFile = Join-Path $StateRoot 'selftest-keys.json'

# ---------------- phase: create ----------------
if($Phase -eq 'create'){
    Check 'draft_module_present' $hasDraftModule
    $null=Read-LocalCoreState
    $snap=Get-Fixture; $rows=@(Add-DiscoverDisplayProperties @($snap.niches)); $loaded=[DateTime]::UtcNow
    # 1) no fabrication without live research
    $threw=$false; try{ $null=New-ResearchConceptDraft $rows[0] $null $loaded '0.2.70' }catch{ $threw=($_.Exception.Message -like 'NO_LIVE_RESEARCH*') }
    Check 'refuses_without_live_snapshot' $threw
    # 2) create from niche 1 via the real Discover button handler
    $DiscoverNicheList.SelectedItem=$rows[0]; $script:DiscoverSnapshot=$snap; $script:DiscoverLoadedAt=$loaded
    $script:Queue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue @(Read-QueueSnapshotFile $script:EmbeddedIdeasPath)))
    $serverCount=@($script:Queue).Count
    Update-DiscoverDraftControls
    Check 'discover_button_enabled_with_selection' ([bool]$DiscoverCreateDraftButton.IsEnabled)
    Invoke-DiscoverCreateDraft
    Check 'no_errors_on_create' ($script:Errors.Count -eq 0) (($script:Errors) -join ' | ')
    $s=Read-LocalCoreState; $drafts=@(Get-ResearchDraftList $s)
    Check 'draft_persisted' ($drafts.Count -eq 1)
    $d=$drafts[0]; $key=[string]$d.concept_key; $p=$d.provenance
    Check 'draft_key_prefix' ($key -like 'rd-*') $key
    Check 'provenance_niche_identity' ([string]$p.niche_identity -eq 'fixture-niche-nurses' -and [string]$p.niche_identity_field -eq 'niche_id')
    Check 'provenance_row_hash' ([string]$p.niche_row_sha256 -match '^[0-9a-f]{64}$')
    Check 'provenance_contract' ([string]$p.contract -eq 'forge.discover_snapshot.v1')
    Check 'provenance_snapshot_time' (-not [string]::IsNullOrWhiteSpace([string]$p.snapshot_loaded_at))
    Check 'evidence_only_explicitly_linked_notes' (@($p.evidence_notes).Count -eq 1 -and [string]@($p.evidence_notes)[0].note_id -eq 'fixture-note-1')
    Check 'creative_fields_not_invented' ([string]::IsNullOrEmpty([string]$d.revisions[0].hook) -and [string]::IsNullOrEmpty([string]$d.revisions[0].visual_direction_text))
    Check 'authority_all_false' (-not [bool]$d.authority.generation_authorized -and -not [bool]$d.authority.paid_provider_authorized -and -not [bool]$d.authority.accept_authorized -and -not [bool]$d.authority.publication_authorized -and -not [bool]$d.authority.backend_mutation)
    # 3) appears in the normal concept list and filter
    $qi=Find-QueueItem $key
    Check 'draft_in_ideas_queue' ($null -ne $qi -and @($script:Queue).Count -eq $serverCount+1)
    Check 'queue_label_research_draft' ($null -ne $qi -and [string]$qi.workflow_label -eq 'Research draft')
    $FilterBox.SelectedItem=[pscustomobject]@{Tag='research_draft'}; Apply-Filter
    Check 'filter_research_draft' (@($ConceptList.ItemsSource).Count -eq 1)
    $FilterBox.SelectedItem=[pscustomobject]@{Tag=''}; Apply-Filter
    # 4) opened as current concept, routed into Ideas, owner review ready
    Check 'draft_opened_as_current' ((Test-CurrentIsResearchDraft) -and [string]$script:Current.concept.concept_key -eq $key)
    Check 'routed_to_ideas' ($script:ProductSection -eq 'ideas')
    Check 'overview_flags_missing_creative' ([string]$OverviewNext.Text -like '*hook*' -and [string]$OverviewNext.Text -like '*visual direction*')
    $lc=Get-LocalCoreConcept $key
    Check 'localcore_mirror_bound_to_revision' ($null -ne $lc -and [string]$lc.source_revision_id -eq [string]$d.current_revision_id)
    Check 'edit_boxes_editable_for_draft' (-not [bool]$TitleBox.IsReadOnly -and [bool]$SpecBox.IsReadOnly)
    # 5) idempotent second click on identical research
    Invoke-DiscoverCreateDraft
    Check 'second_click_same_research_reuses' (@(Get-ResearchDraftList (Read-LocalCoreState)).Count -eq 1)
    # 6) 052 regression: owner buttons follow Busy transitions
    Set-Busy $true 'busy'
    $disabled=(-not $OwnerKeepButton.IsEnabled -and -not $OwnerSkipButton.IsEnabled)
    Set-Busy $false 'idle'
    Check 'owner_buttons_disabled_while_busy' $disabled
    Check 'owner_buttons_enabled_after_busy_052' ([bool]$OwnerKeepButton.IsEnabled -and [bool]$OwnerEditDecisionButton.IsEnabled -and [bool]$OwnerRegenButton.IsEnabled -and [bool]$OwnerSkipButton.IsEnabled)
    # 7) KEEP on draft 1
    Check 'keep_saved' (Set-LocalOwnerDecision 'KEEP')
    Check 'keep_visible' ([string]$OwnerKeepButton.FontWeight -eq 'Bold')
    # 8) second niche -> second draft, SKIP, then switch back
    $DiscoverNicheList.SelectedItem=$rows[1]; Invoke-DiscoverCreateDraft
    $key2=[string]$script:Current.concept.concept_key
    Check 'second_draft_created' ($key2 -ne $key -and @(Get-ResearchDraftList (Read-LocalCoreState)).Count -eq 2)
    Check 'second_draft_has_no_decision' ([string]$OwnerDecisionStatusText.Text -eq 'No decision yet')
    Check 'skip_saved' (Set-LocalOwnerDecision 'SKIP')
    Open-ConceptItem (Find-QueueItem $key)
    Check 'switch_back_keeps_keep' ([string]$OwnerKeepButton.FontWeight -eq 'Bold' -and [string]$OwnerSkipButton.FontWeight -ne 'Bold')
    $prog=Get-LocalOwnerDecisionProgress
    Check 'progress_counts_drafts' ([int]$prog.keep -ge 1 -and [int]$prog.skip -ge 1)
    # 9) Russian labels
    $script:Locale='ru'; Check 'ru_state_label' ((Show-WorkflowState 'research_draft') -eq 'Черновик исследования'); $script:Locale='en'
    @{key=$key;key2=$key2;rev1=[string]$d.current_revision_id} | ConvertTo-Json | Set-Content -LiteralPath $script:KeyFile -Encoding UTF8
}

# ---------------- phase: restart ----------------
if($Phase -eq 'restart'){
    $k=Get-Content -LiteralPath $script:KeyFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $script:Queue=@(Add-QueueDisplayProperties @(Merge-ResearchDraftsIntoQueue @()))
    Check 'drafts_survive_restart' ($null -ne (Find-QueueItem $k.key) -and $null -ne (Find-QueueItem $k.key2))
    $d=Get-ResearchDraft $k.key
    Check 'provenance_survives_restart' ([string]$d.provenance.niche_identity -eq 'fixture-niche-nurses' -and @($d.provenance.evidence_notes).Count -eq 1)
    Check 'state_envelope_valid' (Test-LocalCorePersistedStateEnvelope (Get-Content -LiteralPath $script:LocalCoreStatePath -Raw -Encoding UTF8 | ConvertFrom-Json))
    Check 'backup_written' (Test-Path -LiteralPath $script:LocalCoreBackupPath)
    $rawState=Get-Content -LiteralPath $script:LocalCoreStatePath -Raw -Encoding UTF8
    Check 'state_research_drafts_plain_json_array' ($rawState -match '"research_drafts":\s*\[' -and $rawState -notmatch '"research_drafts":\s*\{')
    $rawJson=$rawState | ConvertFrom-Json; $revOk=$true; foreach($x in @($rawJson.research_drafts)){ if(-not ($x.revisions -is [array])){$revOk=$false} }
    Check 'state_revisions_plain_json_array' $revOk
    Open-ConceptItem (Find-QueueItem $k.key)
    Check 'keep_survives_restart' ([string]$OwnerKeepButton.FontWeight -eq 'Bold' -and [bool]$OwnerKeepButton.IsEnabled)
    Open-ConceptItem (Find-QueueItem $k.key2)
    Check 'skip_survives_restart' ([string]$OwnerSkipButton.FontWeight -eq 'Bold')
    Open-ConceptItem (Find-QueueItem $k.key)
    # EDIT -> new revision invalidates stale decision
    $HookBox.Text='Fixture hook: Running on caffeine and charting'; $VisualBox.Text='Fixture visual: bold typographic stack, coffee cup icon'; $ReasonBox.Text='selftest edit'
    $script:Dirty=$true
    Save-Revision
    $d2=Get-ResearchDraft $k.key
    Check 'edit_creates_revision_2' ([int]$d2.current_revision_no -eq 2 -and @($d2.revisions).Count -eq 2 -and [string]$d2.current_revision_id -ne [string]$k.rev1)
    Check 'revision_1_preserved' ([string]$d2.revisions[0].revision_id -eq [string]$k.rev1 -and [string]::IsNullOrEmpty([string]$d2.revisions[0].hook))
    $rec=Get-LocalOwnerDecisionRecord $k.key
    Check 'stale_keep_invalidated' ([string]$rec.decision -eq 'UNDECIDED')
    Check 'ui_shows_no_decision_after_edit' ([string]$OwnerDecisionStatusText.Text -eq 'No decision yet')
    Check 'overview_no_missing_after_edit' (-not ([string]$OverviewNext.Text -like 'Still missing*'))
    $threw=$false; try{ $null=Save-ResearchDraftRevision $k.key ([ordered]@{title='x'}) 'stale' $k.rev1 }catch{ $threw=($_.Exception.Message -like 'DRAFT_STALE*') }
    Check 'stale_save_rejected' $threw
    $before=@(Get-ResearchDraft $k.key).revisions.Count; $HookBox.Text=$HookBox.Text; $script:Dirty=$true; Save-Revision
    Check 'unchanged_save_no_revision' (@((Get-ResearchDraft $k.key).revisions).Count -eq $before)
    Check 'keep_on_revision_2' (Set-LocalOwnerDecision 'KEEP')
    # no-dispatch artwork preparation
    Export-LocalGenerationBrief
    $dir=Join-Path $script:LocalCoreExportRoot (Get-LocalCoreSafeKey $k.key); $bj=@(Get-ChildItem -LiteralPath $dir -Filter 'generation-brief-*.json')
    $brief=$null; if($bj.Count){$brief=Get-Content -LiteralPath $bj[0].FullName -Raw -Encoding UTF8 | ConvertFrom-Json}
    Check 'brief_exported' ($null -ne $brief)
    Check 'brief_bound_to_revision_2' ($null -ne $brief -and [string]$brief.source_revision_id -eq [string](Get-ResearchDraft $k.key).current_revision_id)
    Check 'brief_no_external_generation' ($null -ne $brief -and -not [bool]$brief.external_generation_authorized)
    # authority guards
    $script:Errors.Clear(); Queue-Generation
    Check 'generate_blocked_for_draft' ($script:Errors.Count -eq 1 -and $script:Errors[0] -like 'Research drafts cannot be generated*')
    foreach($a in @('Prepare-DeliveryPackage','Start-NewIteration','Reopen-CurrentAcceptance','Cancel-Generation')){ $script:Errors.Clear(); & $a; Check ("live_action_blocked_$a") ($script:Errors.Count -eq 1 -and $script:Errors[0] -like 'This is a local research draft*') }
    $s=Read-LocalCoreState; $lc=Get-LocalCoreConcept $k.key $s
    Check 'no_acceptance_created' ($null -eq $lc.active_acceptance)
    Check 'no_package_created' (@($lc.packages).Count -eq 0)
    $script:Errors.Clear(); $missing=Load-Concept 'rd-000000000000000000000000' $true
    Check 'missing_draft_key_never_hits_api' (-not [bool]$missing -and $script:Errors.Count -eq 1 -and $script:R.api_calls -eq 0)
    $script:Errors.Clear(); $script:Current=$null; Open-ResearchDraftItem ([pscustomobject]@{concept_key=$k.key}) $true
    $VariantList.ItemsSource=@('stale-live-variant'); $AnalysisScores.Text='stale live scores'
    Open-ResearchDraftItem ([pscustomobject]@{concept_key=$k.key2}) $true
    Check 'stale_live_surfaces_cleared' ((@($VariantList.ItemsSource) -notcontains 'stale-live-variant') -and [string]$AnalysisScores.Text -eq '')
    $saved=${function:Ensure-LocalCoreConceptFromCurrent}; Set-Item function:Ensure-LocalCoreConceptFromCurrent { throw 'Local Forge state changed in another window. (injected)' }
    $script:Errors.Clear(); $crashed=$false; try{ Open-ResearchDraftItem ([pscustomobject]@{concept_key=$k.key}) $true }catch{ $crashed=$true }
    Set-Item function:Ensure-LocalCoreConceptFromCurrent $saved
    Check 'open_error_is_contained' (-not $crashed -and $script:Errors.Count -eq 1)
    $script:Errors.Clear(); $reloaded=Load-Concept $k.key $true
    Check 'reload_draft_stays_local' ([bool]$reloaded -and (Test-CurrentIsResearchDraft) -and $script:Errors.Count -eq 0 -and [string]$script:Current.concept.concept_key -eq [string]$k.key)
    Check 'draft_still_not_server_concept' (-not [bool](Get-ResearchDraft $k.key).authority.server_concept)
}

# ---------------- phase: legacy054 (rollback compatibility) ----------------
if($Phase -eq 'legacy054'){
    Check 'legacy_has_no_draft_module' (-not $hasDraftModule)
    $s=$null; $err=''; try{$s=Read-LocalCoreState}catch{$err=$_.Exception.Message}
    Check 'legacy_054_reads_055_state' ($null -ne $s) $err
    $k=Get-Content -LiteralPath $script:KeyFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $lc=$null; if($null -ne $s){$lc=Get-LocalCoreConcept $k.key $s}
    Check 'legacy_sees_owner_decision_mirror' ($null -ne $lc -and [string]$lc.owner_decision -eq 'KEEP')
    $err=''; try{ Write-LocalCoreState $s; $s2=Read-LocalCoreState }catch{$err=$_.Exception.Message}
    $kept=$false; if($err -eq ''){ $p=$s2.PSObject.Properties['research_drafts']; $kept=($null -ne $p -and @($p.Value).Count -eq 2) }
    Check 'legacy_write_preserves_drafts' $kept $err
}
} catch {
    $script:R['fatal']=($_.Exception.Message+' @ '+$_.InvocationInfo.PositionMessage)
}
if($OutputPath){ [IO.File]::WriteAllText($OutputPath,($script:R | ConvertTo-Json -Depth 12),(New-Object Text.UTF8Encoding($false))) }
