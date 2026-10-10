# Merch Forge · Research -> concept draft (local-first)
# Turns a selected Discover niche into a LOCAL concept draft bound to its research provenance.
# Boundaries: no backend mutation, no paid provider call, no Generate/Accept/Submit authority.
# Drafts live in the LocalCore state (research_drafts[]) and appear in the normal Ideas list.

$script:ResearchDraftSchema = 'forge.research_concept_draft.v1'
$script:ResearchDraftKeyPrefix = 'rd-'
$script:ResearchDraftWorkflowState = 'research_draft'
$script:ResearchDraftContentFields = @('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')

function Register-ResearchDraftUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{
            'draft.create'='Create concept draft'; 'draft.create.hint'='Creates a local draft in Ideas, bound to this niche''s research. No generation, no publishing.';
            'draft.created'='Draft created: {0}'; 'draft.exists'='A draft from this exact research already exists: {0}'; 'draft.count'='{0} local draft(s) from this niche';
            'draft.state'='Research draft'; 'draft.meta'='Local research draft · revision {0} · not on the server';
            'draft.next'='Review this draft: write or fix the hook and visual direction in Edit, then choose KEEP / EDIT / REGEN / SKIP. Artwork: Export brief (no dispatch), then import the finished image.';
            'draft.missing'='Still missing before artwork: {0}.'; 'draft.missing.hook'='hook'; 'draft.missing.visual'='visual direction';
            'draft.provenance'='Research provenance: {0} · score {1} · confidence {2}% · snapshot {3} · {4} matched note(s)';
            'draft.generate.blocked'='Research drafts cannot be generated from Forge yet. Use Export brief (no dispatch) and import the finished artwork. Paid generation stays a separate owner-authorized gate.';
            'draft.saved'='Draft revision {0} saved locally. Earlier owner decisions for this draft no longer apply.'; 'draft.unchanged'='No changes to save.';
            'draft.need.niche'='Select a niche first.'; 'draft.need.live'='Live research is required. No draft is created from missing data.'; 'draft.need.title'='Title cannot be empty.';
            'queue.draft'='Research draft'; 'draft.live.blocked'='This is a local research draft. Live server actions are not available for it.'
        }
        ru=@{
            'draft.create'='Создать черновик концепта'; 'draft.create.hint'='Создаёт локальный черновик в «Идеях», привязанный к исследованию этой ниши. Без генерации и публикации.';
            'draft.created'='Черновик создан: {0}'; 'draft.exists'='Черновик из этого же исследования уже есть: {0}'; 'draft.count'='Локальных черновиков из этой ниши: {0}';
            'draft.state'='Черновик исследования'; 'draft.meta'='Локальный черновик исследования · ревизия {0} · не на сервере';
            'draft.next'='Проверьте черновик: допишите хук и визуальное направление во вкладке «Правка», затем выберите ОСТАВИТЬ / ПРАВКА / ЗАНОВО / ПРОПУСТИТЬ. Артворк: «Экспорт брифа» (без отправки), затем импорт готового изображения.';
            'draft.missing'='До артворка не хватает: {0}.'; 'draft.missing.hook'='хука'; 'draft.missing.visual'='визуального направления';
            'draft.provenance'='Источник исследования: {0} · оценка {1} · уверенность {2}% · снимок {3} · связанных заметок: {4}';
            'draft.generate.blocked'='Черновики исследования пока нельзя генерировать из Forge. Используйте «Экспорт брифа» (без отправки) и импортируйте готовый артворк. Платная генерация остаётся отдельным шагом с разрешения владельца.';
            'draft.saved'='Ревизия черновика {0} сохранена локально. Прежние решения владельца по черновику больше не действуют.'; 'draft.unchanged'='Изменений нет.';
            'draft.need.niche'='Сначала выберите нишу.'; 'draft.need.live'='Нужны живые данные исследования. Из отсутствующих данных черновик не создаётся.'; 'draft.need.title'='Название не может быть пустым.';
            'queue.draft'='Черновик исследования'; 'draft.live.blocked'='Это локальный черновик исследования. Действия на сервере для него недоступны.'
        }
        es=@{
            'draft.create'='Crear borrador de concepto'; 'draft.create.hint'='Crea un borrador local en Ideas, vinculado a la investigación de este nicho. Sin generación ni publicación.';
            'draft.created'='Borrador creado: {0}'; 'draft.exists'='Ya existe un borrador de esta misma investigación: {0}'; 'draft.count'='{0} borrador(es) local(es) de este nicho';
            'draft.state'='Borrador de investigación'; 'draft.meta'='Borrador local de investigación · revisión {0} · no está en el servidor';
            'draft.next'='Revisa el borrador: escribe el gancho y la dirección visual en Editar y luego elige MANTENER / EDITAR / REGENERAR / OMITIR. Arte: Exportar brief (sin envío) e importar la imagen final.';
            'draft.missing'='Falta antes del arte: {0}.'; 'draft.missing.hook'='gancho'; 'draft.missing.visual'='dirección visual';
            'draft.provenance'='Procedencia: {0} · puntuación {1} · confianza {2}% · instantánea {3} · {4} nota(s) vinculada(s)';
            'draft.generate.blocked'='Los borradores de investigación aún no se pueden generar desde Forge. Usa Exportar brief (sin envío) e importa el arte final. La generación de pago sigue siendo un paso autorizado por el propietario.';
            'draft.saved'='Revisión {0} del borrador guardada localmente. Las decisiones anteriores del propietario ya no aplican.'; 'draft.unchanged'='No hay cambios.';
            'draft.need.niche'='Selecciona un nicho primero.'; 'draft.need.live'='Se requiere investigación en vivo. No se crea un borrador con datos ausentes.'; 'draft.need.title'='El título no puede estar vacío.';
            'queue.draft'='Borrador de investigación'; 'draft.live.blocked'='Este es un borrador local de investigación. Las acciones del servidor no están disponibles.'
        }
    }
    foreach($loc in $texts.Keys){
        if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}
        foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]}
    }
}

# ---------- pure state helpers (headless-testable) ----------
function Get-ResearchDraftList($State) {
    if($null -eq $State){return @()}
    $p=$State.PSObject.Properties['research_drafts']; if($null -eq $p -or $null -eq $p.Value){return @()}
    return @($p.Value)
}
function ConvertTo-PlainArray($Items) { $list=New-Object System.Collections.ArrayList; foreach($i in @($Items)){if($null -ne $i){[void]$list.Add($i)}}; return ,($list.ToArray()) }
function Set-PlainArrayProperty($Object,[string]$Name,$Items) {
    $arr=ConvertTo-PlainArray $Items
    if($null -eq $Object.PSObject.Properties[$Name]){$Object|Add-Member -NotePropertyName $Name -NotePropertyValue $null -Force}
    $Object.PSObject.Properties[$Name].Value=$arr
}
function Set-ResearchDraftList($State,$Drafts) { Set-PlainArrayProperty $State 'research_drafts' $Drafts }
function Get-ResearchDraft([string]$ConceptKey,$State=$null) {
    if([string]::IsNullOrWhiteSpace($ConceptKey)){return $null}
    if($null -eq $State){$State=Read-LocalCoreState}
    foreach($d in (Get-ResearchDraftList $State)){if([string](Get-PropertyValue $d 'concept_key') -eq $ConceptKey -and [string](Get-PropertyValue $d 'status') -eq 'draft'){return $d}}
    return $null
}
function Test-ResearchDraftKey([string]$ConceptKey) { return (-not [string]::IsNullOrWhiteSpace($ConceptKey) -and $ConceptKey.StartsWith($script:ResearchDraftKeyPrefix)) }
function Test-CurrentIsResearchDraft {
    if($null -eq $script:Current){return $false}
    return [bool](Get-PropertyValue $script:Current 'local_research_draft')
}
function Get-DiscoverNicheIdentity($Niche) {
    foreach($f in @('niche_id','id','niche_key','key','slug')){
        $v=Get-PropertyValue $Niche $f
        if($null -ne $v -and -not [string]::IsNullOrWhiteSpace([string]$v)){return [pscustomobject]@{field=$f;value=[string]$v;name=[string](Get-PropertyValue $Niche 'name')}}
    }
    $name=([string](Get-PropertyValue $Niche 'name')).Trim()
    if([string]::IsNullOrWhiteSpace($name)){return $null}
    return [pscustomobject]@{field='name_sha256';value=(Get-StringSha256Hex $name.ToLowerInvariant());name=$name}
}
function Get-ResearchDraftStableJson($Object) {
    # Display-only properties are UI decorations, not research evidence.
    if($null -eq $Object){return 'null'}
    $copy=[ordered]@{}
    foreach($p in ($Object.PSObject.Properties | Sort-Object Name)){if($p.Name -in @('score_label','meta_label')){continue};$copy[$p.Name]=$p.Value}
    return ($copy | ConvertTo-Json -Depth 12 -Compress)
}
function Get-DiscoverNotesForNiche($Snapshot,$Niche,$Identity) {
    # Only notes that the snapshot explicitly links to this niche count as evidence. No fuzzy matching.
    $out=@(); if($null -eq $Snapshot -or $null -eq $Identity){return @()}
    $nameLc=([string]$Identity.name).Trim().ToLowerInvariant()
    foreach($n in @(Get-PropertyValue $Snapshot 'notes')){
        if($null -eq $n){continue}; $hit=$false
        foreach($f in @('niche_id','niche_key','niche_slug')){$v=[string](Get-PropertyValue $n $f);if($v -and $Identity.field -ne 'name_sha256' -and $v -eq [string]$Identity.value){$hit=$true}}
        foreach($f in @('niche_name','niche')){$v=([string](Get-PropertyValue $n $f)).Trim().ToLowerInvariant();if($v -and $nameLc -and $v -eq $nameLc){$hit=$true}}
        if($hit){$out+=[pscustomobject]@{note_id=[string](Get-PropertyValue $n 'id');topic=[string](Get-PropertyValue $n 'topic');conclusion=[string](Get-PropertyValue $n 'conclusion');created_at=[string](Get-PropertyValue $n 'created_at');note_sha256=(Get-StringSha256Hex (Get-ResearchDraftStableJson $n))}}
    }
    return @($out | Select-Object -First 8)
}
function New-ResearchDraftContent($Niche,$Notes) {
    $name=([string](Get-PropertyValue $Niche 'name')).Trim()
    $summary=([string](Get-PropertyValue $Niche 'research_summary')).Trim()
    $audience=([string](Get-PropertyValue $Niche 'audience')).Trim()
    $count=0;try{$count=[int](Get-PropertyValue $Niche 'concept_count')}catch{}
    $dims=Get-PropertyValue $Niche 'dimensions'; $top=@()
    if($null -ne $dims){$top=@($dims.PSObject.Properties | Where-Object {$null -ne $_.Value} | Sort-Object @{Expression={[double]$_.Value};Descending=$true} | Select-Object -First 3 | ForEach-Object {[string]::Format([Globalization.CultureInfo]::InvariantCulture,'{0} {1:0.#}',($_.Name -replace '_',' '),[double]$_.Value)})}
    $conclusions=@($Notes | Where-Object {-not [string]::IsNullOrWhiteSpace($_.conclusion)} | Select-Object -First 3 | ForEach-Object {('- '+$_.topic+': '+$_.conclusion)})
    $conceptText=$summary; if($conclusions.Count){$conceptText=($summary+"`n`nResearch notes:`n"+($conclusions -join "`n")).Trim()}
    $purchase=if($top.Count){'Strongest research signals: '+($top -join ', ')+'.'}else{''}
    $diff=('Forge already holds {0} concept(s) in this niche. Differentiate from them before artwork.' -f $count)
    # Hook and visual direction are creative choices; they are intentionally left empty, never invented here.
    return [ordered]@{title=$name;hook='';concept_text=$conceptText;target_buyer=$audience;purchase_reason=$purchase;differentiation=$diff;visual_direction_text=''}
}
function Get-ResearchDraftContentHash([string]$ConceptKey,$Fields) {
    $m=[ordered]@{concept_key=$ConceptKey}; foreach($f in $script:ResearchDraftContentFields){$m[$f]=[string](Get-PropertyValue ([pscustomobject]$Fields) $f)}
    return (Get-StringSha256Hex ($m | ConvertTo-Json -Depth 4 -Compress))
}
function New-ResearchDraftRevision([string]$ConceptKey,[int]$RevisionNo,$Fields,[string]$Reason) {
    $hash=Get-ResearchDraftContentHash $ConceptKey $Fields
    $rev=[ordered]@{revision_no=$RevisionNo;revision_id=('rdrev-{0}-{1}-{2}' -f $ConceptKey.Substring($script:ResearchDraftKeyPrefix.Length),$RevisionNo,$hash.Substring(0,12));revision_hash=$hash;created_at=[DateTime]::UtcNow.ToString('o');reason=$Reason}
    foreach($f in $script:ResearchDraftContentFields){$rev[$f]=[string](Get-PropertyValue ([pscustomobject]$Fields) $f)}
    return [pscustomobject]$rev
}
function New-ResearchConceptDraft($Niche,$Snapshot,$LoadedAtUtc,[string]$BackendVersion='') {
    if($null -eq $Niche){throw 'NO_NICHE: Select a niche first.'}
    if($null -eq $Snapshot){throw 'NO_LIVE_RESEARCH: Live research snapshot is required.'}
    $identity=Get-DiscoverNicheIdentity $Niche; if($null -eq $identity){throw 'NO_NICHE_IDENTITY: The selected niche has no id or name.'}
    $rowJson=Get-ResearchDraftStableJson $Niche; $rowSha=Get-StringSha256Hex $rowJson
    $s=Read-LocalCoreState
    foreach($d in (Get-ResearchDraftList $s)){
        $p=Get-PropertyValue $d 'provenance'
        if([string](Get-PropertyValue $d 'status') -eq 'draft' -and [string](Get-PropertyValue $p 'niche_row_sha256') -eq $rowSha){return [pscustomobject]@{created=$false;draft=$d}}
    }
    $notes=@(Get-DiscoverNotesForNiche $Snapshot $Niche $identity)
    $fields=New-ResearchDraftContent $Niche $notes
    $key=$script:ResearchDraftKeyPrefix+([Guid]::NewGuid().ToString('N').Substring(0,24))
    $rev=New-ResearchDraftRevision $key 1 $fields 'created_from_discover_research'
    $loaded=''; if($null -ne $LoadedAtUtc){try{$loaded=([datetime]$LoadedAtUtc).ToUniversalTime().ToString('o')}catch{$loaded=[string]$LoadedAtUtc}}
    $sources=@(); foreach($x in @(Get-PropertyValue $Snapshot 'sources') | Select-Object -First 16){if($null -eq $x){continue};$sources+=[pscustomobject]@{source_id=[string](Get-PropertyValue $x 'id');name=[string](Get-PropertyValue $x 'name');source_class=[string](Get-PropertyValue $x 'source_class')}}
    $provenance=[pscustomobject]@{
        origin='discover_research'; contract=[string]$(if(Get-PropertyValue $Snapshot 'contract'){Get-PropertyValue $Snapshot 'contract'}else{'forge.discover_snapshot.v1'})
        snapshot_loaded_at=$loaded; backend_version=$BackendVersion
        niche_identity_field=$identity.field; niche_identity=$identity.value; niche_name=$identity.name
        niche_row_sha256=$rowSha; niche_row=($rowJson | ConvertFrom-Json)
        score_total=(Get-PropertyValue $Niche 'score_total'); score_confidence=(Get-PropertyValue $Niche 'score_confidence'); category=[string](Get-PropertyValue $Niche 'category'); audience=[string](Get-PropertyValue $Niche 'audience'); concept_count_at_snapshot=(Get-PropertyValue $Niche 'concept_count')
        evidence_notes=@($notes); evidence_note_match='explicit_niche_link_only'
        snapshot_sources=@($sources); snapshot_sources_scope='snapshot_wide_context_not_niche_specific'
    }
    $draft=[pscustomobject]@{
        schema=$script:ResearchDraftSchema; concept_key=$key; status='draft'; created_at=$rev.created_at; updated_at=$rev.created_at
        niche_name=$identity.name; current_revision_no=1; current_revision_id=$rev.revision_id; current_revision_hash=$rev.revision_hash
        revisions=@($rev); provenance=$provenance
        authority=[pscustomobject]@{scope='server_and_paid_actions_only; local owner gates (exact local accept, local package) keep their own existing checks';server_concept=$false;backend_mutation=$false;generation_authorized=$false;paid_provider_authorized=$false;accept_authorized=$false;publication_authorized=$false;external_submission_authorized=$false}
    }
    Set-ResearchDraftList $s (@(Get-ResearchDraftList $s)+@($draft))
    Write-LocalCoreState $s
    return [pscustomobject]@{created=$true;draft=$draft}
}
function Get-ResearchDraftCurrentFields($Draft) {
    $revs=@(Get-PropertyValue $Draft 'revisions'); $no=[int](Get-PropertyValue $Draft 'current_revision_no')
    foreach($r in $revs){if([int](Get-PropertyValue $r 'revision_no') -eq $no){return $r}}
    if($revs.Count){return $revs[$revs.Count-1]}; return $null
}
function Save-ResearchDraftRevision([string]$ConceptKey,$Fields,[string]$Reason,[string]$ExpectedRevisionId) {
    $s=Read-LocalCoreState; $d=Get-ResearchDraft $ConceptKey $s; if($null -eq $d){throw 'DRAFT_NOT_FOUND: The research draft no longer exists.'}
    if([string](Get-PropertyValue $d 'current_revision_id') -ne $ExpectedRevisionId){throw 'DRAFT_STALE: This draft changed in another window. Reopen it before saving.'}
    $t=([string](Get-PropertyValue ([pscustomobject]$Fields) 'title')).Trim(); if([string]::IsNullOrWhiteSpace($t)){throw 'DRAFT_TITLE_REQUIRED: Title cannot be empty.'}
    $newHash=Get-ResearchDraftContentHash $ConceptKey $Fields
    if($newHash -eq [string](Get-PropertyValue $d 'current_revision_hash')){return [pscustomobject]@{saved=$false;draft=$d}}
    $no=[int](Get-PropertyValue $d 'current_revision_no')+1
    $rev=New-ResearchDraftRevision $ConceptKey $no $Fields $(if([string]::IsNullOrWhiteSpace($Reason)){'owner_edit'}else{$Reason})
    Set-PlainArrayProperty $d 'revisions' (@(Get-PropertyValue $d 'revisions')+@($rev))
    Add-OrSetProperty $d 'current_revision_no' $no; Add-OrSetProperty $d 'current_revision_id' $rev.revision_id; Add-OrSetProperty $d 'current_revision_hash' $rev.revision_hash; Add-OrSetProperty $d 'updated_at' $rev.created_at
    Write-LocalCoreState $s
    return [pscustomobject]@{saved=$true;draft=$d}
}
function ConvertTo-ResearchDraftConcept($Draft) {
    $r=Get-ResearchDraftCurrentFields $Draft; $p=Get-PropertyValue $Draft 'provenance'
    return [pscustomobject]@{
        concept_key=[string](Get-PropertyValue $Draft 'concept_key'); title=[string](Get-PropertyValue $r 'title'); hook=[string](Get-PropertyValue $r 'hook')
        niche_name=[string](Get-PropertyValue $p 'niche_name'); concept_text=[string](Get-PropertyValue $r 'concept_text'); target_buyer=[string](Get-PropertyValue $r 'target_buyer')
        purchase_reason=[string](Get-PropertyValue $r 'purchase_reason'); differentiation=[string](Get-PropertyValue $r 'differentiation'); visual_direction_text=[string](Get-PropertyValue $r 'visual_direction_text')
        current_revision_no=[int](Get-PropertyValue $Draft 'current_revision_no'); current_revision_id=[string](Get-PropertyValue $Draft 'current_revision_id'); current_content_hash=[string](Get-PropertyValue $Draft 'current_revision_hash')
        current_revision_accepted=$false; workflow_state=$script:ResearchDraftWorkflowState; production_spec=[pscustomobject]@{}; concept_status='draft'
        score_total=(Get-PropertyValue $p 'score_total'); is_local_draft=$true
    }
}
function Get-ResearchDraftQueueItems($State=$null) {
    if($null -eq $State){try{$State=Read-LocalCoreState}catch{Write-AppLog 'WARN' ('Research drafts unavailable: '+$_.Exception.Message);return @()}}
    $items=@()
    foreach($d in (Get-ResearchDraftList $State)){
        if([string](Get-PropertyValue $d 'status') -ne 'draft'){continue}
        $c=ConvertTo-ResearchDraftConcept $d
        $items+=[pscustomobject]@{concept_key=$c.concept_key;title=$c.title;hook=$c.hook;niche_name=$c.niche_name;concept_text=$c.concept_text;target_buyer=$c.target_buyer;purchase_reason=$c.purchase_reason;differentiation=$c.differentiation;visual_direction_text=$c.visual_direction_text;workflow_state=$script:ResearchDraftWorkflowState;score_total=$(if($null -ne $c.score_total){[double]$c.score_total}else{0});is_local_draft=$true;meaning=''}
    }
    return @($items)
}
function Merge-ResearchDraftsIntoQueue($Items) {
    $base=@($Items | Where-Object {$null -ne $_}); $seen=@{}; foreach($i in $base){$seen[[string](Get-PropertyValue $i 'concept_key')]=$true}
    $out=@($base); foreach($d in (Get-ResearchDraftQueueItems)){if(-not $seen.ContainsKey([string]$d.concept_key)){$out+=$d}}
    return @($out)
}
function Get-ResearchDraftMissing($Concept) {
    $m=@(); if([string]::IsNullOrWhiteSpace([string](Get-PropertyValue $Concept 'hook'))){$m+=(Get-UiText 'draft.missing.hook' 'hook')}
    if([string]::IsNullOrWhiteSpace([string](Get-PropertyValue $Concept 'visual_direction_text'))){$m+=(Get-UiText 'draft.missing.visual' 'visual direction')}
    return @($m)
}
function Get-ResearchDraftProvenanceText($Draft) {
    $p=Get-PropertyValue $Draft 'provenance'; $score=Get-PropertyValue $p 'score_total'; $conf=Get-PropertyValue $p 'score_confidence'
    $inv=[Globalization.CultureInfo]::InvariantCulture; $scoreText=if($null -ne $score){([double]$score).ToString('0.0',$inv)}else{'—'}; $confText=if($null -ne $conf){([double]$conf).ToString('0.#',$inv)}else{'—'}
    return ((Get-UiText 'draft.provenance' 'Research provenance: {0} · score {1} · confidence {2}% · snapshot {3} · {4} matched note(s)') -f [string](Get-PropertyValue $p 'niche_name'),$scoreText,$confText,[string](Get-PropertyValue $p 'snapshot_loaded_at'),@(Get-PropertyValue $p 'evidence_notes').Count)
}

# ---------- UI glue (WPF; exercised natively only) ----------
function Set-DraftEditBoxesEditable([bool]$Editable) {
    foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$ReasonBox)){if($null -ne $box){$box.IsReadOnly=(-not $Editable)}}
    if($null -ne $SpecBox){$SpecBox.IsReadOnly=$true}
}
function Restore-RoleEditability {
    $canEdit=Has-Cap 'edit'
    foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox,$ReasonBox)){if($null -ne $box){$box.IsReadOnly=(-not $canEdit)}}
}
function Enter-ResearchDraftSection([string]$Section) {
    Enter-LocalCoreSection $Section
    foreach($tab in @($MainTabs.Items)){if($tab -is [Windows.Controls.TabItem]){if((Get-MainTabKey $tab) -eq 'edit'){$tab.IsEnabled=$true}}}
    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
    if($null -ne $script:Current -and $null -ne $ConceptMeta){$ConceptMeta.Text=(Get-UiText 'draft.meta' 'Local research draft · revision {0} · not on the server') -f [int](Get-PropertyValue $script:Current.concept 'current_revision_no')}
}
function Clear-DraftStaleConceptSurfaces {
    # A draft has no server variants, generation requests, analysis, publication or delivery state.
    foreach($l in @($VariantList,$GenerationRequestList,$RevisionList)){if($null -ne $l){try{$l.ItemsSource=@()}catch{}}}
    foreach($tb in @($AnalysisPurchase,$AnalysisContext,$AnalysisMeaning,$AnalysisEvidence,$AnalysisScores,$AnalysisAdvanced,$AnalysisWarnings,$CurrentRevisionPreview,$SelectedRevisionPreview,$RevisionAdvanced,$AuditAdvanced,$DeliveryStatus)){if($null -ne $tb){try{$tb.Text=''}catch{}}}
}
function Open-ResearchDraftItem($Item,[bool]$Force=$false) {
    if($null -eq $Item){return}
    $key=[string](Get-PropertyValue $Item 'concept_key')
    if(-not $Force -and $null -ne $script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq $key){return}
    if(-not $Force -and ($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')){return}
    try {
        $d=Get-ResearchDraft $key; if($null -eq $d){Show-Error 'This research draft no longer exists. Refresh the Ideas list.';return}
        $c=ConvertTo-ResearchDraftConcept $d
        $script:Dirty=$false; $script:PublicationDirty=$false; $script:ReviewWorkspace=$null; $script:RestoreSourceRevisionId=$null; $script:Delivery=$null; $script:Publication=$null
        $script:Current=[pscustomobject]@{concept=$c;local_research_draft=$true;draft=$d;variants=@();revisions=@();scores=@();analysis_warnings=@()}
        if(@('home','discover','portfolio','performance') -contains $script:ProductSection){$script:ProductSection='ideas'}
        $wasBusy=$script:Busy; $script:Busy=$true
        try {
            Clear-DraftStaleConceptSurfaces
            $TitleBox.Text=$c.title;$HookBox.Text=$c.hook;$ConceptTextBox.Text=$c.concept_text;$BuyerBox.Text=$c.target_buyer;$PurchaseBox.Text=$c.purchase_reason;$DifferentiationBox.Text=$c.differentiation;$VisualBox.Text=$c.visual_direction_text;$SpecBox.Text='{}';$ReasonBox.Text=''
            if($null -ne $GenerationBriefText){$GenerationBriefText.Text=Get-GenerationBriefSummary $c}
            $ConceptTitle.Text=$c.title
            $OverviewHook.Text=$c.hook;$OverviewConcept.Text=$c.concept_text;$OverviewBuyer.Text=$c.target_buyer;$OverviewWhy.Text=$c.purchase_reason;$OverviewDifferent.Text=$c.differentiation;$OverviewVisual.Text=$c.visual_direction_text;$OverviewMeaning.Text=''
            $OverviewStatus.Text=Get-UiText 'draft.state' 'Research draft'
            $OverviewWarnings.Text=Get-ResearchDraftProvenanceText $d
            $missing=@(Get-ResearchDraftMissing $c); $next=Get-UiText 'draft.next' 'Review this draft.'
            if($missing.Count){$next=((Get-UiText 'draft.missing' 'Still missing before artwork: {0}.') -f ($missing -join ', '))+' '+$next}
            $OverviewNext.Text=$next
            $OverviewVisualButton.IsEnabled=$true; $OverviewEditButton.IsEnabled=$true
        } finally { $script:Busy=$wasBusy }
        Set-DraftEditBoxesEditable $true
        $null=Ensure-LocalCoreConceptFromCurrent
        # Fill local tabs now so no surface keeps the previous concept's data.
        try{Refresh-LocalArtworkUi}catch{Write-AppLog 'WARN' ('Draft artwork surface refresh failed: '+$_.Exception.Message)}
        try{Load-LocalChecksUi}catch{Write-AppLog 'WARN' ('Draft checks surface refresh failed: '+$_.Exception.Message)}
        try{Load-LocalPublicationUi}catch{Write-AppLog 'WARN' ('Draft publication surface refresh failed: '+$_.Exception.Message)}
        Show-ProductSection $script:ProductSection
        Set-Dirty $false
        Update-OwnerDecisionControls
    } catch {
        Write-AppLog 'ERROR' ('Research draft open failed for '+$key+': '+$_.Exception.Message)
        Show-Error ('Research draft could not be opened: '+$_.Exception.Message)
        if($null -ne $StatusText){$StatusText.Text='Draft open failed'}
    }
}
function Save-CurrentResearchDraftRevision {
    if(-not (Test-CurrentIsResearchDraft)){return}
    $c=$script:Current.concept
    $fields=[ordered]@{title=([string]$TitleBox.Text).Trim();hook=[string]$HookBox.Text;concept_text=[string]$ConceptTextBox.Text;target_buyer=[string]$BuyerBox.Text;purchase_reason=[string]$PurchaseBox.Text;differentiation=[string]$DifferentiationBox.Text;visual_direction_text=[string]$VisualBox.Text}
    if([string]::IsNullOrWhiteSpace($fields.title)){Show-Error (Get-UiText 'draft.need.title' 'Title cannot be empty.');return}
    try {
        $r=Save-ResearchDraftRevision ([string]$c.concept_key) $fields ([string]$ReasonBox.Text) ([string]$c.current_revision_id)
        Set-Dirty $false
        if(-not $r.saved){$StatusText.Text=Get-UiText 'draft.unchanged' 'No changes to save.';return}
        Refresh-ResearchDraftQueue
        Open-ResearchDraftItem ([pscustomobject]@{concept_key=[string]$c.concept_key}) $true
        Select-MainTab 'Overview'; Update-MainTabUi
        $StatusText.Text=(Get-UiText 'draft.saved' 'Draft revision {0} saved locally.') -f [int](Get-PropertyValue $r.draft 'current_revision_no')
    } catch { Show-Error $_.Exception.Message; $StatusText.Text='Draft save failed' }
}
function Refresh-ResearchDraftQueue {
    $server=@($script:Queue | Where-Object {-not [bool](Get-PropertyValue $_ 'is_local_draft')})
    $script:Queue=@(Add-QueueDisplayProperties (Merge-ResearchDraftsIntoQueue $server))
    Apply-Filter
}
function Update-DiscoverDraftControls {
    if($null -eq $DiscoverCreateDraftButton){return}
    $DiscoverCreateDraftButton.Content=Get-UiText 'draft.create' 'Create concept draft'
    $DiscoverCreateDraftButton.ToolTip=Get-UiText 'draft.create.hint' 'Creates a local draft in Ideas, bound to this niche''s research.'
    $n=$null; if($null -ne $DiscoverNicheList){$n=$DiscoverNicheList.SelectedItem}
    $DiscoverCreateDraftButton.IsEnabled=($null -ne $n -and $null -ne $script:DiscoverSnapshot -and -not $script:Busy -and -not $script:OfflineMode)
    if($null -ne $DiscoverDraftStatusText){
        if($null -eq $n){$DiscoverDraftStatusText.Text='';return}
        $count=0; try{$id=Get-DiscoverNicheIdentity $n; foreach($d in (Get-ResearchDraftList (Read-LocalCoreState))){$p=Get-PropertyValue $d 'provenance';if([string](Get-PropertyValue $d 'status') -eq 'draft' -and [string](Get-PropertyValue $p 'niche_identity') -eq [string]$id.value){$count++}}}catch{}
        $DiscoverDraftStatusText.Text=if($count -gt 0){(Get-UiText 'draft.count' '{0} local draft(s) from this niche') -f $count}else{Get-UiText 'draft.create.hint' ''}
    }
}
function Invoke-DiscoverCreateDraft {
    $n=$null; if($null -ne $DiscoverNicheList){$n=$DiscoverNicheList.SelectedItem}
    if($null -eq $n){Show-Error (Get-UiText 'draft.need.niche' 'Select a niche first.');return}
    if($null -eq $script:DiscoverSnapshot -or $script:OfflineMode){Show-Error (Get-UiText 'draft.need.live' 'Live research is required.');return}
    if(($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')){return}
    try {
        $r=New-ResearchConceptDraft $n $script:DiscoverSnapshot $script:DiscoverLoadedAt ([string]$script:BackendVersion)
        $key=[string](Get-PropertyValue $r.draft 'concept_key')
        Write-AppLog 'INFO' ('Research draft '+$(if($r.created){'created'}else{'reused'})+': '+$key+' niche='+[string](Get-PropertyValue (Get-PropertyValue $r.draft 'provenance') 'niche_identity'))
        Refresh-ResearchDraftQueue
        $script:Dirty=$false; $script:PublicationDirty=$false
        $script:ProductSection='ideas'
        Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true
        $StatusText.Text=if($r.created){(Get-UiText 'draft.created' 'Draft created: {0}') -f [string](Get-PropertyValue $r.draft 'niche_name')}else{(Get-UiText 'draft.exists' 'A draft from this exact research already exists: {0}') -f [string](Get-PropertyValue $r.draft 'niche_name')}
    } catch { Write-AppLog 'ERROR' ('Research draft creation failed: '+$_.Exception.Message); Show-Error ('Draft was not created: '+$_.Exception.Message) }
}

function Restore-DynamicSurfacesAfterLocale {
    if($script:ProductSection -eq 'portfolio'){try{Update-PortfolioPipelineSurface}catch{}}
    # Apply-StaticLocaleUi rewrites every TextBlock with the text captured at startup ("—", "Select a niche"...).
    # Re-render the live surfaces from current data so a language switch never shows stale placeholders.
    if($null -ne $script:DiscoverSnapshot -and $null -ne $DiscoverNicheList){
        $selId=''; try{$cur=$DiscoverNicheList.SelectedItem;if($null -ne $cur){$i=Get-DiscoverNicheIdentity $cur;if($null -ne $i){$selId=[string]$i.value}}}catch{}
        Render-DiscoverSnapshot $script:DiscoverSnapshot $selId
        if($null -ne $DiscoverStatusText -and $null -ne $script:DiscoverLoadedAt){$DiscoverStatusText.Text=('{0} · {1:HH:mm} UTC' -f (Get-UiText 'discover.ready' 'Live research loaded'),[datetime]$script:DiscoverLoadedAt)}
        Update-DiscoverDraftControls
    }
    if((Test-CurrentIsResearchDraft) -and -not $script:Dirty){
        $key=[string](Get-PropertyValue $script:Current.concept 'concept_key'); $section=$script:ProductSection
        Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true
        if($section -ne $script:ProductSection -and $section -in @('discover','home','portfolio','performance')){Show-ProductSection $section}
    }
}
